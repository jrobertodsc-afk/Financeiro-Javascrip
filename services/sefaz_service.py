import re
import requests
import tempfile
import os
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
import xml.etree.ElementTree as ET_SAFE

def extract_info_from_key(chave: str) -> dict:
    """Extrai informações básicas diretamente da chave de acesso de 44 dígitos."""
    chave = re.sub(r'\D', '', chave.strip())
    if len(chave) != 44:
        raise ValueError(f"Chave inválida — {len(chave)} dígitos (precisa de 44)")

    c_uf    = chave[0:2]
    c_aamm  = chave[2:6]
    c_cnpj  = chave[6:20]
    c_nnf   = chave[25:34]

    ano  = "20" + c_aamm[0:2]
    mes  = c_aamm[2:4]
    cnpj_fmt = f"{c_cnpj[:2]}.{c_cnpj[2:5]}.{c_cnpj[5:8]}/{c_cnpj[8:12]}-{c_cnpj[12:14]}"
    num_nf = str(int(c_nnf))

    UF_NOMES = {
        "11":"RO","12":"AC","13":"AM","14":"RR","15":"PA","16":"AP","17":"TO",
        "21":"MA","22":"PI","23":"CE","24":"RN","25":"PB","26":"PE","27":"AL",
        "28":"SE","29":"BA","31":"MG","32":"ES","33":"RJ","35":"SP","41":"PR",
        "42":"SC","43":"RS","50":"MS","51":"MT","52":"GO","53":"DF",
    }
    uf_sigla = UF_NOMES.get(c_uf, c_uf)

    return {
        "chave": chave,
        "uf": c_uf,
        "uf_sigla": uf_sigla,
        "ano": ano,
        "mes": mes,
        "cnpj": cnpj_fmt,
        "num_nf": num_nf
    }

def consult_sefaz(chave: str, pfx_path: str, password: str, uf_code: str) -> str:
    """
    Consulta o webservice da SEFAZ usando certificado A1 (.pfx) e retorna o XML da NFe.
    Lança exceção em caso de erro.
    """
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()

    # Carrega certificado
    priv, cert, chain = pkcs12.load_key_and_certificates(pfx_data, password.encode())

    # Arquivos temporários para requisição (requests precisa de PEM)
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="wb") as fc:
        fc.write(cert.public_bytes(Encoding.PEM))
        cert_pem = fc.name
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="wb") as fk:
        fk.write(priv.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()))
        key_pem = fk.name

    try:
        # Webservice SEFAZ por UF (Prioriza SVRS para maior estabilidade)
        WS_URL = {
            "29": "https://nfe.sefaz.ba.gov.br/webservices/nfeconsultaprotocolo4/nfeconsultaprotocolo4.asmx",
            "32": "https://nfe.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
        }.get(uf_code, "https://nfe.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx")

        soap_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4">
      <consSitNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
        <tpAmb>1</tpAmb>
        <xServ>CONSULTAR</xServ>
        <chNFe>{chave}</chNFe>
      </consSitNFe>
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>'''

        resp = requests.post(
            WS_URL,
            data=soap_body.encode("utf-8"),
            headers={"Content-Type": "application/soap+xml;charset=UTF-8"},
            cert=(cert_pem, key_pem),
            verify=False, timeout=15
        )
        resp.raise_for_status()

        # Extrai XML da NF-e da resposta SOAP
        root_soap = ET_SAFE.fromstring(resp.text)
        xml_nfe = None
        for el in root_soap.iter():
            tag = el.tag.split('}')[1] if '}' in el.tag else el.tag
            if tag in ("nfeProc", "NFe", "retConsSitNFe"):
                import xml.etree.ElementTree as ET
                xml_nfe = ET.tostring(el, encoding="unicode")
                break

        if not xml_nfe:
            raise ValueError("XML da NF-e não encontrado na resposta da SEFAZ.")
            
        return xml_nfe

    finally:
        # Garante que os arquivos PEM temporários sejam apagados
        if os.path.exists(cert_pem):
            os.unlink(cert_pem)
        if os.path.exists(key_pem):
            os.unlink(key_pem)
