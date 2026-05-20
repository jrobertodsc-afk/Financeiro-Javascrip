"""
utils/nfe_processor.py — Processador de Notas Fiscais Eletrônicas (NF-e).

Realiza a leitura de arquivos XML de NF-e, extração de dados fiscais
(emitente, destinatário, valores, impostos, itens), e validação básica.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime

# Namespace padrão da NF-e
NS = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

def ler_nfe_xml(caminho_xml: str) -> dict:
    """
    Lê e extrai os principais dados de um arquivo XML de NF-e.
    Retorna um dicionário com os dados extraídos.
    """
    resultado = {
        "valida": False,
        "erros": [],
        "chave_acesso": "",
        "numero": "",
        "serie": "",
        "data_emissao": "",
        "emitente": {"nome": "", "cnpj": ""},
        "destinatario": {"nome": "", "cnpj": ""},
        "valor_total": 0.0,
        "impostos": {"icms": 0.0, "ipi": 0.0, "pis": 0.0, "cofins": 0.0},
        "itens": []
    }

    if not os.path.exists(caminho_xml):
        resultado["erros"].append("Arquivo não encontrado")
        return resultado

    try:
        tree = ET.parse(caminho_xml)
        root = tree.getroot()

        # Busca a tag infNFe
        inf_nfe = root.find('.//nfe:infNFe', NS)
        if inf_nfe is None:
            # Tenta sem namespace se não encontrar
            inf_nfe = root.find('.//infNFe')

        if inf_nfe is None:
            resultado["erros"].append("Tag infNFe não encontrada. Não é um XML de NF-e válido.")
            return resultado

        # Chave de Acesso (Id atributo da infNFe)
        chave = inf_nfe.attrib.get('Id', '')
        if chave.startswith('NFe'):
            resultado["chave_acesso"] = chave[3:]

        # Ide (Identificação)
        ide = inf_nfe.find('.//nfe:ide', NS) or inf_nfe.find('.//ide')
        if ide is not None:
            nNF = ide.find('./nfe:nNF', NS) or ide.find('./nNF')
            resultado["numero"] = nNF.text if nNF is not None else ""
            
            serie = ide.find('./nfe:serie', NS) or ide.find('./serie')
            resultado["serie"] = serie.text if serie is not None else ""
            
            dhEmi = ide.find('./nfe:dhEmi', NS) or ide.find('./dhEmi')
            if dhEmi is not None:
                # Formato ISO 8601: 2026-05-20T10:00:00-03:00
                dt_str = dhEmi.text[:10]
                try:
                    resultado["data_emissao"] = datetime.strptime(dt_str, "%Y-%m-%d").strftime("%d/%m/%Y")
                except Exception:
                    resultado["data_emissao"] = dt_str

        # Emitente
        emit = inf_nfe.find('.//nfe:emit', NS) or inf_nfe.find('.//emit')
        if emit is not None:
            xNome = emit.find('./nfe:xNome', NS) or emit.find('./xNome')
            resultado["emitente"]["nome"] = xNome.text if xNome is not None else ""
            CNPJ = emit.find('./nfe:CNPJ', NS) or emit.find('./CNPJ')
            resultado["emitente"]["cnpj"] = CNPJ.text if CNPJ is not None else ""

        # Destinatário
        dest = inf_nfe.find('.//nfe:dest', NS) or inf_nfe.find('.//dest')
        if dest is not None:
            xNome = dest.find('./nfe:xNome', NS) or dest.find('./xNome')
            resultado["destinatario"]["nome"] = xNome.text if xNome is not None else ""
            CNPJ = dest.find('./nfe:CNPJ', NS) or dest.find('./CNPJ')
            resultado["destinatario"]["cnpj"] = CNPJ.text if CNPJ is not None else ""

        # Total
        total = inf_nfe.find('.//nfe:total/nfe:ICMSTot', NS) or inf_nfe.find('.//total/ICMSTot')
        if total is not None:
            vNF = total.find('./nfe:vNF', NS) or total.find('./vNF')
            if vNF is not None:
                resultado["valor_total"] = float(vNF.text)

            vICMS = total.find('./nfe:vICMS', NS) or total.find('./vICMS')
            if vICMS is not None: resultado["impostos"]["icms"] = float(vICMS.text)
            
            vIPI = total.find('./nfe:vIPI', NS) or total.find('./vIPI')
            if vIPI is not None: resultado["impostos"]["ipi"] = float(vIPI.text)
            
            vPIS = total.find('./nfe:vPIS', NS) or total.find('./vPIS')
            if vPIS is not None: resultado["impostos"]["pis"] = float(vPIS.text)
            
            vCOFINS = total.find('./nfe:vCOFINS', NS) or total.find('./vCOFINS')
            if vCOFINS is not None: resultado["impostos"]["cofins"] = float(vCOFINS.text)

        # Itens (det)
        det_list = inf_nfe.findall('.//nfe:det', NS) or inf_nfe.findall('.//det')
        for det in det_list:
            prod = det.find('./nfe:prod', NS) or det.find('./prod')
            if prod is not None:
                xProd = prod.find('./nfe:xProd', NS) or prod.find('./xProd')
                qCom = prod.find('./nfe:qCom', NS) or prod.find('./qCom')
                vUnCom = prod.find('./nfe:vUnCom', NS) or prod.find('./vUnCom')
                vProd = prod.find('./nfe:vProd', NS) or prod.find('./vProd')
                
                resultado["itens"].append({
                    "descricao": xProd.text if xProd is not None else "",
                    "quantidade": float(qCom.text) if qCom is not None else 0.0,
                    "valor_unitario": float(vUnCom.text) if vUnCom is not None else 0.0,
                    "valor_total": float(vProd.text) if vProd is not None else 0.0,
                })

        resultado["valida"] = True

    except ET.ParseError:
        resultado["erros"].append("Erro ao fazer parse do XML. Arquivo corrompido.")
    except Exception as e:
        resultado["erros"].append(f"Erro inesperado: {str(e)}")

    return resultado

def validar_fiscal_nfe(nfe_dados: dict, cnpj_empresa: str) -> list[str]:
    """
    Realiza validações fiscais básicas da NF-e para a empresa.
    Retorna lista de alertas/erros.
    """
    alertas = []
    
    if not nfe_dados.get("valida"):
        return nfe_dados.get("erros", ["NF-e inválida"])

    destinatario_cnpj = nfe_dados["destinatario"]["cnpj"]
    
    # Verifica se a nota foi emitida contra o CNPJ da empresa
    if destinatario_cnpj and cnpj_empresa:
        cnpj_1 = ''.join(filter(str.isdigit, destinatario_cnpj))
        cnpj_2 = ''.join(filter(str.isdigit, cnpj_empresa))
        if cnpj_1 != cnpj_2:
            alertas.append(f"ALERTA: O CNPJ do destinatário ({cnpj_1}) não corresponde à empresa ({cnpj_2}).")

    if nfe_dados["valor_total"] <= 0:
        alertas.append("ALERTA: Valor total da nota é zero ou negativo.")

    # Simulação de verificação de impostos
    pis = nfe_dados["impostos"]["pis"]
    cofins = nfe_dados["impostos"]["cofins"]
    if pis == 0 and cofins == 0 and nfe_dados["valor_total"] > 0:
        alertas.append("AVISO: Nota não possui retenção/destaque de PIS/COFINS. Verifique a natureza da operação.")

    return alertas
