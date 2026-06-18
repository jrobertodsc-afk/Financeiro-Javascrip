import os
import re
import ssl
import tempfile
import contextlib
import unicodedata
from datetime import datetime
import xml.etree.ElementTree as ET
import requests
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Endpoints SOAP 1.2
URL_RECEPCAO_TESTE = "https://www.testegnre.pe.gov.br/gnreWS/services/GnreLoteRecepcao"
URL_CONSULTA_TESTE = "https://www.testegnre.pe.gov.br/gnreWS/services/GnreResultadoLote"

URL_RECEPCAO_PROD = "https://www.gnre.pe.gov.br/gnreWS/services/GnreLoteRecepcao"
URL_CONSULTA_PROD = "https://www.gnre.pe.gov.br/gnreWS/services/GnreResultadoLote"

# Senha padrão do certificado digital PFX
PFX_PASSPHRASE = "dmf1977"

# Pasta padrão de certificados carregada do .env com fallbacks relativos
CERT_DIR = os.getenv("CERT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "CERTIFICADOS"))
PASTA_LOGS = os.getenv("PASTA_LOGS", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "WEBSERVICE", "xml_logs"))

# ==========================================
# EXTRAÇÃO DE CERTIFICADOS A1 (PFX -> PEM)
# ==========================================

def extrair_pfx_para_pem_temp(pfx_path: str, passphrase: str):
    """
    Extrai o certificado e a chave privada do arquivo PFX e salva em arquivos PEM temporários.
    Retorna (cert_path, key_path).
    O chamador deve excluir esses arquivos temporários quando terminar.
    """
    logger.info(f"[mTLS] Extraindo PFX de: {pfx_path}")
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()

    # Descriptografa PFX
    private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
        pfx_data, passphrase.encode()
    )

    # Serializa chave privada em PEM sem criptografia
    key_pem = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption()
    )

    # Serializa certificado público em PEM
    cert_pem = certificate.public_bytes(
        encoding=Encoding.PEM
    )

    # Adiciona certificados intermediários se houver
    if additional_certificates:
        for ac in additional_certificates:
            cert_pem += b"\n" + ac.public_bytes(Encoding.PEM)

    # Grava em arquivos temporários
    cert_file = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    cert_file.write(cert_pem)
    cert_file.close()

    key_file = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    key_file.write(key_pem)
    key_file.close()

    return cert_file.name, key_file.name


@contextlib.contextmanager
def mtls_cert_context(empresa: str):
    """
    Context Manager que localiza o certificado PFX correto para a empresa,
    extrai os arquivos PEM temporários e os remove automaticamente ao final.
    """
    cert_path, key_path = None, None
    try:
        if not os.path.exists(CERT_DIR):
            os.makedirs(CERT_DIR, exist_ok=True)
            
        arquivos = os.listdir(CERT_DIR)
        arquivos_pfx = [f for f in arquivos if f.lower().endswith('.pfx')]
        
        if not arquivos_pfx:
            raise FileNotFoundError(f"Nenhum arquivo de certificado (.pfx) encontrado em {CERT_DIR}")
            
        # Tenta casar o nome da empresa com o nome do arquivo
        arquivo_selecionado = arquivos_pfx[0]
        empresa_upper = empresa.upper()
        for f in arquivos_pfx:
            if empresa_upper in f.upper():
                arquivo_selecionado = f
                break
                
        pfx_full_path = os.path.join(CERT_DIR, arquivo_selecionado)
        cert_path, key_path = extrair_pfx_para_pem_temp(pfx_full_path, PFX_PASSPHRASE)
        yield cert_path, key_path
    finally:
        # Garante a exclusão dos arquivos temporários
        if cert_path and os.path.exists(cert_path):
            try: os.remove(cert_path)
            except: pass
        if key_path and os.path.exists(key_path):
            try: os.remove(key_path)
            except: pass


# ==========================================
# PARSE E SALVAMENTO DE LOGS
# ==========================================

def salvar_log_xml(nome_arquivo: str, conteudo: str):
    try:
        os.makedirs(PASTA_LOGS, exist_ok=True)
        full_path = os.path.join(PASTA_LOGS, nome_arquivo)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(conteudo)
        logger.info(f"💾 Log salvo: {full_path}")
    except Exception as e:
        logger.error(f"Falha ao salvar log XML: {e}")


# ==========================================
# PARSER DE GUIAS EMITIDAS (XML)
# ==========================================

def extrair_dados_guia_xml(conteudo_xml: str) -> list[dict]:
    """
    Analisa o XML de retorno da SEFAZ (consultar lote resultado) e extrai
    os dados das guias processadas.
    """
    # 1. Tratamento de Rejeições Gerais do Lote
    if "<ns1:codigo>102</ns1:codigo>" in conteudo_xml or "<motivoRejeicao>" in conteudo_xml:
        desc_match = re.search(r"<descricao>([^<]+)</descricao>", conteudo_xml)
        desc_erro = desc_match.group(1) if desc_match else "Rejeição geral do lote"
        raise Exception(f"Rejeição geral do governo: {desc_erro}")

    guias_extraidas = []

    # O retorno pode conter múltiplas tags <guia>
    # Usaremos regex para isolar cada bloco <guia> de forma robusta a namespaces
    blocos_guia = re.findall(r"<guia[^>]*>(.*?)</guia>", conteudo_xml, re.DOTALL)
    
    if not blocos_guia:
        # Se não há tags guia isoladas, tenta ver se há uma estrutura de erro geral
        if "<situacaoProcess>" in conteudo_xml:
            desc_match = re.search(r"<descricao>([^<]+)</descricao>", conteudo_xml)
            if desc_match:
                raise Exception(f"Lote não processado: {desc_match.group(1)}")
        raise Exception("Nenhuma guia encontrada na estrutura de retorno do XML.")

    for bloco in blocos_guia:
        # Verifica a situação da guia (0 = Processada com Sucesso)
        situacao_match = re.search(r"<situacaoGuia>([^<]+)</situacaoGuia>", bloco)
        situacao = situacao_match.group(1) if situacao_match else "9"
        
        # Coleta campos de erro/rejeição se houver
        motivos = []
        if situacao != "0":
            motivos_regex = re.findall(r"<descricao>([^<]+)</descricao>", bloco)
            motivo_erro = " | ".join(motivos_regex) if motivos_regex else "Guia rejeitada pela SEFAZ"
            # Extrai o documento origem para referenciar
            doc_origem_match = re.search(r"<documentoOrigem[^>]*>([^<]+)</documentoOrigem>", bloco)
            doc_origem = doc_origem_match.group(1) if doc_origem_match else "Desconhecido"
            guias_extraidas.append({
                "status": "REJEITADO",
                "motivo_rejeicao": motivo_erro,
                "documento_origem": doc_origem
            })
            continue

        # Coleta campos de sucesso
        cod_barras_match = re.search(r"<codigoBarras>([^<]+)</codigoBarras>", bloco) or \
                           re.search(r"<linhaDigitavel>([^<]+)</linhaDigitavel>", bloco)
        
        valor_match = re.search(r"<valorGNRE>([^<]+)</valorGNRE>", bloco) or \
                      re.search(r"<c10_valorTotal>([^<]+)</c10_valorTotal>", bloco) or \
                      re.search(r"<valor[^>]*>([^<]+)</valor>", bloco)
        
        venc_match = re.search(r"<dataVencimento>([^<]+)</dataVencimento>", bloco) or \
                     re.search(r"<c14_dataVencimento>([^<]+)</c14_dataVencimento>", bloco)

        doc_origem_match = re.search(r"<documentoOrigem[^>]*>([^<]+)</documentoOrigem>", bloco)

        if not cod_barras_match or not valor_match:
            continue

        cod_barras = re.sub(r"[^0-9]", "", cod_barras_match.group(1))
        
        guias_extraidas.append({
            "status": "SUCESSO",
            "codigo_barras": cod_barras,
            "linha_digitavel": cod_barras, # sefaz retorna a linha digitável igual ao código de barras
            "valor": float(valor_match.group(1)),
            "data_vencimento": venc_match.group(1) if venc_match else "",
            "documento_origem": doc_origem_match.group(1) if doc_origem_match else ""
        })

    return guias_extraidas


# ==========================================
# MONTAGEM DE TEMPLATES SOAP 1.2
# ==========================================

def montar_xml_envio(lista_guias: list[dict]) -> str:
    xml_guias = ""
    for guia in lista_guias:
        xml_campos_extras = ""
        if guia.get("chave_acesso_nfe"):
            xml_campos_extras = f"""
                <camposExtras>
                  <campoExtra>
                    <codigo>55</codigo>
                    <valor>{guia["chave_acesso_nfe"]}</valor>
                  </campoExtra>
                </camposExtras>"""

        xml_doc_origem = ""
        if guia.get("documento_origem"):
            xml_doc_origem = f"""<documentoOrigem tipo="{guia.get('tipo_documento_origem', '10')}">{guia["documento_origem"]}</documentoOrigem>"""

        xml_guias += f"""
          <TDadosGNRE versao="2.00">
            <ufFavorecida>{guia.get("uf_favorecida", "PE")}</ufFavorecida>
            <tipoGnre>0</tipoGnre> <!-- 0 = GNRE Simples -->
            <contribuinteEmitente>
              <identificacao>
                <CNPJ>{guia.get("cnpj_emitente", "")}</CNPJ>
              </identificacao>
            </contribuinteEmitente>
            <itensGNRE>
              <item>
                <receita>{guia.get("codigo_receita", "100102")}</receita>
                {xml_doc_origem}
                <dataVencimento>{guia.get("data_vencimento", "")}</dataVencimento>
                <valor tipo="11">{guia.get("valor", 0)}</valor> <!-- 11 = Valor Principal ICMS -->
                <valor tipo="21">{guia.get("valor", 0)}</valor> <!-- 21 = Valor Total ICMS -->
                {xml_campos_extras}
              </item>
            </itensGNRE>
            <valorGNRE>{guia.get("valor", 0)}</valorGNRE>
          </TDadosGNRE>"""

    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <gnreCabecMsg xmlns="http://www.gnre.pe.gov.br/webservice/GnreLoteRecepcao">
      <versaoDados>2.00</versaoDados>
    </gnreCabecMsg>
  </soap12:Header>
  <soap12:Body>
    <gnreDadosMsg xmlns="http://www.gnre.pe.gov.br/webservice/GnreLoteRecepcao">
      <TLote_GNRE xmlns="http://www.gnre.pe.gov.br" versao="2.00">
        <guias>{xml_guias}
        </guias>
      </TLote_GNRE>
    </gnreDadosMsg>
  </soap12:Body>
</soap12:Envelope>""".strip()


def montar_xml_consulta(numero_recibo: str, ambiente: int = 2) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <gnreCabecMsg xmlns="http://www.gnre.pe.gov.br/webservice/GnreResultadoLote">
      <versaoDados>2.00</versaoDados>
    </gnreCabecMsg>
  </soap12:Header>
  <soap12:Body>
    <gnreDadosMsg xmlns="http://www.gnre.pe.gov.br/webservice/GnreResultadoLote">
      <TConsLote_GNRE xmlns="http://www.gnre.pe.gov.br" versao="2.00">
        <ambiente>{ambiente}</ambiente>
        <numeroRecibo>{numero_recibo}</numeroRecibo>
      </TConsLote_GNRE>
    </gnreDadosMsg>
  </soap12:Body>
</soap12:Envelope>""".strip()


# ==========================================
# ENVIO FISCAL (SEFAZ MTLS)
# ==========================================

def transmitir_lote_sefaz(lista_guias: list[dict], empresa: str, ambiente: int = 2) -> str:
    """
    Gera o XML e envia o lote de guias para a SEFAZ usando o certificado digital da empresa.
    Retorna o número do Recibo de processamento.
    """
    url_envio = URL_RECEPCAO_TESTE if ambiente == 2 else URL_RECEPCAO_PROD
    soap_xml = montar_xml_envio(lista_guias)
    timestamp = int(datetime.now().timestamp())
    
    salvar_log_xml(f"envio_lote_{timestamp}.xml", soap_xml)

    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8;',
        'SOAPAction': 'processar'
    }

    # Carrega mTLS dinamicamente e faz o POST
    with mtls_cert_context(empresa) as (cert_pem, key_pem):
        logger.info(f"[mTLS] Fazendo POST mTLS para {url_envio}...")
        response = requests.post(
            url_envio,
            data=soap_xml.encode('utf-8'),
            headers=headers,
            cert=(cert_pem, key_pem),
            verify=False,
            timeout=30
        )

    res_body = response.text
    salvar_log_xml(f"resposta_lote_{timestamp}.xml", res_body)

    if response.status_code != 200:
        raise Exception(f"Erro HTTP {response.status_code} na comunicação com a SEFAZ.")

    # Extrai o recibo
    recibo_match = re.search(r"<numero>([^<]+)</numero>", res_body)
    if not recibo_match:
        # Procura erro na descrição
        desc_match = re.search(r"<descricao>([^<]+)</descricao>", res_body)
        desc = desc_match.group(1) if desc_match else "Estrutura XML inválida."
        raise Exception(f"Lote rejeitado pela SEFAZ: {desc}")

    return recibo_match.group(1)


def consultar_lote_sefaz(numero_recibo: str, empresa: str, ambiente: int = 2) -> str:
    """
    Consulta a SEFAZ para obter o resultado do processamento das guias.
    Retorna o XML de resposta completo.
    """
    url_consulta = URL_CONSULTA_TESTE if ambiente == 2 else URL_CONSULTA_PROD
    soap_xml = montar_xml_consulta(numero_recibo, ambiente)
    
    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8;',
        'SOAPAction': 'consultar'
    }

    with mtls_cert_context(empresa) as (cert_pem, key_pem):
        logger.info(f"[mTLS] Consultando recibo {numero_recibo} em {url_consulta}...")
        response = requests.post(
            url_consulta,
            data=soap_xml.encode('utf-8'),
            headers=headers,
            cert=(cert_pem, key_pem),
            verify=False,
            timeout=30
        )

    res_body = response.text
    salvar_log_xml(f"resultado_consulta_{numero_recibo}.xml", res_body)

    if response.status_code != 200:
        raise Exception(f"Erro HTTP {response.status_code} na consulta do recibo.")

    return res_body


# ==========================================
# FORMATADORES POSICIONAIS CNAB 240
# ==========================================

def pad_zero(num, size: int) -> str:
    s = str(num or 0).replace('.', '').replace(',', '')
    return s.zfill(size)[:size]

def pad_space(val, size: int) -> str:
    s = str(val or '')
    return s.ljust(size)[:size]

def limpar_texto(txt: str) -> str:
    if not txt: return ""
    # Remove acentos
    nfkd = unicodedata.normalize('NFKD', str(txt))
    sem_acentos = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Filtra A-Z, 0-9 e espaço
    limpo = re.sub(r'[^a-zA-Z0-9 ]', '', sem_acentos)
    return limpo.upper()

def formatar_data_cnab(data_str: str) -> str:
    if not data_str:
        return datetime.now().strftime("%d%m%Y")
    if '-' in data_str:
        parts = data_str.split('-')
        if len(parts) == 3:
            # YYYY-MM-DD -> DD/MM/YYYY
            return f"{parts[2]}{parts[1]}{parts[0]}"
    return re.sub(r'[^0-9]', '', data_str)


# ==========================================
# GERADOR REMESSA ITAÚ SISPAG (CNAB 240)
# ==========================================

def gerar_remessa_sispag_tributos(dados_empresa: dict, guias: list[dict], data_pagamento: str = None) -> str:
    """
    Gera as linhas de texto formatadas no padrão CNAB 240 v086 do Banco Itaú (SISPAG)
    específico para pagamento de Tributos com Código de Barras (Segmento O).
    """
    linhas = []
    data_hoje = datetime.now().strftime("%d%m%Y")
    hora_hoje = datetime.now().strftime("%H%M%S")

    # Formata a data de pagamento
    if data_pagamento:
        data_pagamento_cnab = formatar_data_cnab(data_pagamento)
    else:
        data_pagamento_cnab = data_hoje

    # 1. REGISTRO 0: HEADER DE ARQUIVO
    header_arquivo = (
        pad_zero(341, 3)                              # 001-003: Banco Itaú
        + pad_zero(0, 4)                                # 004-007: Lote de Serviço
        + '0'                                          # 008-008: Tipo Registro (0=Header Arquivo)
        + pad_space('', 6)                              # 009-014: Brancos
        + pad_zero(80, 3)                               # 015-017: Layout Arquivo
        + '2'                                          # 018-018: Tipo Inscrição (2=CNPJ)
        + pad_zero(dados_empresa.get("cnpj"), 14)       # 019-032: Número CNPJ
        + pad_space('', 20)                             # 033-052: Brancos
        + pad_zero(dados_empresa.get("agencia"), 5)     # 053-057: Agência Débito
        + pad_space('', 1)                              # 058-058: Branco
        + pad_zero(dados_empresa.get("conta"), 12)      # 059-070: Conta Corrente
        + pad_space('', 1)                              # 071-071: Branco
        + pad_zero(dados_empresa.get("dac", "0"), 1)    # 072-072: DAC
        + pad_space(limpar_texto(dados_empresa.get("razao_social")), 30) # 073-102: Razão Social
        + pad_space("BANCO ITAU SA", 30)                # 103-132: Nome do Banco
        + pad_space('', 10)                             # 133-142: Brancos
        + '1'                                          # 143-143: Código Remessa (1)
        + pad_zero(data_hoje, 8)                        # 144-151: Data Geração
        + pad_zero(hora_hoje, 6)                        # 152-157: Hora Geração
        + pad_zero(0, 9)                                # 158-166: Zeros
        + pad_zero(0, 5)                                # 167-171: Densidade Grav.
        + pad_space('', 69)                             # 172-240: Brancos Complemento
    )
    linhas.append(header_arquivo)

    # 2. REGISTRO 1: HEADER DE LOTE (Layout 030 - Tributos)
    header_lote = (
        pad_zero(341, 3)                                 # 001-003: Banco
        + pad_zero(1, 4)                                   # 004-007: Lote Sequencial
        + '1'                                             # 008-008: Tipo Registro (1=Header Lote)
        + 'C'                                             # 009-009: Operação (C=Crédito)
        + pad_zero(22, 2)                                  # 010-011: Tipo de Serviço (22=Tributos)
        + pad_zero(91, 2)                                  # 012-013: Forma Lançamento (91=GNRE com Cód. Barras)
        + pad_zero(30, 3)                                  # 014-016: Layout do Lote
        + pad_space('', 1)                                 # 017-017: Branco
        + '2'                                             # 018-018: Tipo Inscrição
        + pad_zero(dados_empresa.get("cnpj"), 14)          # 019-032: CNPJ Empresa
        + pad_space('', 4)                                 # 033-036: Identificação Lançamento
        + pad_space('', 16)                                # 037-052: Brancos
        + pad_zero(dados_empresa.get("agencia"), 5)        # 053-057: Agência
        + pad_space('', 1)                                 # 058-058: Branco
        + pad_zero(dados_empresa.get("conta"), 12)         # 059-070: Conta
        + pad_space('', 1)                                 # 071-071: Branco
        + pad_zero(dados_empresa.get("dac", "0"), 1)       # 072-072: DAC
        + pad_space(limpar_texto(dados_empresa.get("razao_social")), 30) # 073-102: Empresa
        + pad_space('', 30)                                # 103-132: Finalidade Lote
        + pad_space('', 10)                                # 133-142: Histórico C/C
        + pad_space('', 98)                                # 143-240: Endereço e Complementos da Empresa
    )
    linhas.append(header_lote)

    total_lote_financeiro = 0.0
    contador_registros_lote = 1 # O lote inicia no Header de Lote (1)

    # 3. REGISTRO 3: DETALHE - SEGMENTO O
    for idx, guia in enumerate(guias):
        seq = idx + 1
        contador_registros_lote += 1
        valor_guia = float(guia.get("valor", 0))
        total_lote_financeiro += valor_guia

        seg_o = (
            pad_zero(341, 3)                                   # 001-003: Banco
            + pad_zero(1, 4)                                     # 004-007: Lote
            + '3'                                               # 008-008: Tipo Registro (3=Detalhe)
            + pad_zero(seq, 5)                                   # 009-013: Sequencial no Lote
            + 'O'                                               # 014-014: Segmento (O)
            + pad_zero(0, 3)                                     # 015-017: Tipo Movimento (000=Inclusão)
            + pad_space(guia.get("codigo_barras"), 48)           # 018-065: Código de Barras da Guia
            + pad_space("SEFAZ PE GNRE TRIBUTOS", 30)            # 066-095: Nome Concessionária/Órgão
            + pad_zero(formatar_data_cnab(guia.get("data_vencimento")), 8) # 096-103: Vencimento
            + 'REA'                                             # 104-106: Moeda (REA)
            + pad_zero(0, 15)                                    # 107-121: Qtd Moeda
            + pad_zero(int(round(valor_guia * 100)), 15)         # 122-136: Valor da Guia (em centavos)
            + pad_zero(data_pagamento_cnab, 8)                   # 137-144: Data de Pagamento
            + pad_zero(0, 15)                                    # 145-159: Valor Pago (preencher com zeros na remessa)
            + pad_space('', 3)                                   # 160-162: Brancos
            + pad_zero(0, 9)                                     # 163-171: Nota Fiscal / Complemento
            + pad_space('', 3)                                   # 172-174: Brancos
            + pad_space(f"GNRE-NF-{seq}", 20)                    # 175-194: Seu Número
            + pad_space('', 21)                                  # 195-215: Brancos
            + pad_space('', 15)                                  # 216-230: Nosso Número
            + pad_space('', 10)                                  # 231-240: Ocorrências de retorno
        )
        linhas.append(seg_o)

    # 4. REGISTRO 5: TRAILER DE LOTE
    contador_registros_lote += 1
    total_lote_centavos = int(round(total_lote_financeiro * 100))
    
    trailer_lote = (
        pad_zero(341, 3)                                # 001-003: Banco
        + pad_zero(1, 4)                                  # 004-007: Lote
        + '5'                                            # 008-008: Tipo Registro (5=Trailer Lote)
        + pad_space('', 9)                                # 009-017: Brancos
        + pad_zero(contador_registros_lote, 6)             # 018-023: Quantidade de registros do lote
        + pad_zero(total_lote_centavos, 18)               # 024-041: Somatória dos valores do lote
        + pad_zero(0, 15)                                 # 042-056: Soma quantidade de moeda
        + pad_space('', 174)                              # 057-230: Brancos Complemento
        + pad_space('', 10)                               # 231-240: Ocorrências
    )
    linhas.append(trailer_lote)

    # 5. REGISTRO 9: TRAILER DE ARQUIVO
    trailer_arquivo = (
        pad_zero(341, 3)                             # 001-003: Banco
        + pad_zero(9999, 4)                            # 004-007: Lote (9999 padrão)
        + '9'                                         # 008-008: Tipo Registro (9=Trailer Arquivo)
        + pad_space('', 9)                             # 009-017: Brancos
        + pad_zero(1, 6)                               # 018-023: Quantidade de lotes
        + pad_zero(len(linhas) + 1, 6)                 # 024-029: Quantidade de linhas
        + pad_space('', 211)                           # 030-240: Brancos
    )
    linhas.append(trailer_arquivo)

    # Validação rigorosa: cada linha deve conter exatamente 240 caracteres
    conteudo_final = ""
    for idx, l in enumerate(linhas):
        if len(l) != 240:
            raise ValueError(f"Linha {idx} gerada com tamanho inválido ({len(l)} bytes). Esperado 240.")
        conteudo_final += l + "\r\n"

    return conteudo_final
