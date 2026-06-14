import os
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.database import (
    listar_gnre_guias, salvar_gnre_guia, atualizar_status_gnre_guia, listar_notas
)
from backend.services.gnre_service import (
    transmitir_lote_sefaz, consultar_lote_sefaz, extrair_dados_guia_xml,
    gerar_remessa_sispag_tributos
)
import config
from loguru import logger

router = APIRouter(prefix="/api/gnre", tags=["GNRE"])

# Modelos Pydantic para payloads
class GuiaPayload(BaseModel):
    numero_tx: Optional[str] = None
    nota_ref_tx: Optional[str] = ""
    uf_favorecida: str = "PE"
    cnpj_emitente: str = ""
    codigo_receita: str = "100102"
    valor: float
    data_vencimento: str
    documento_origem: Optional[str] = ""
    tipo_documento_origem: str = "10"
    chave_acesso_nfe: Optional[str] = ""
    linha_digitavel: Optional[str] = ""
    codigo_barras: Optional[str] = ""
    numero_recibo: Optional[str] = ""
    status: str = "PENDENTE"
    motivo_rejeicao: Optional[str] = ""

class TransmitirPayload(BaseModel):
    numero_tx_list: List[str]
    empresa: str = "LALUA"
    ambiente: int = 2 # 2=Homologação, 1=Produção
    simulado: bool = True

class ConsultarPayload(BaseModel):
    numero_recibo: str
    empresa: str = "LALUA"
    ambiente: int = 2
    simulado: bool = True

class DadosEmpresaPayload(BaseModel):
    cnpj: str = "10436619000105"
    razao_social: str = "BOAH COMERCIO VAREJISTA"
    agencia: str = "01234"
    conta: str = "0012345"
    dac: str = "6"

class GerarRemessaPayload(BaseModel):
    numero_tx_list: List[str]
    dados_empresa: DadosEmpresaPayload


@router.get("/guias")
def api_listar_guias(status: Optional[str] = None, busca: Optional[str] = None):
    try:
        guias = listar_gnre_guias(status=status, busca=busca)
        return {"success": True, "guias": guias}
    except Exception as e:
        logger.error(f"Erro ao listar guias GNRE: {e}")
        return {"success": False, "error": str(e)}


@router.post("/salvar")
def api_salvar_guia(payload: GuiaPayload):
    try:
        dados = payload.model_dump()
        tx = salvar_gnre_guia(dados)
        return {"success": True, "numero_tx": tx}
    except Exception as e:
        logger.error(f"Erro ao salvar guia GNRE: {e}")
        return {"success": False, "error": str(e)}


@router.post("/transmitir")
def api_transmitir_lote(payload: TransmitirPayload):
    try:
        logger.info(f"Transmitindo lote GNRE. Simulado: {payload.simulado}")
        
        # 1. Carrega as guias do banco correspondentes aos IDs enviados
        todas_guias = listar_gnre_guias()
        guias_para_envio = [g for g in todas_guias if g["numero_tx"] in payload.numero_tx_list]
        
        if not guias_para_envio:
            raise HTTPException(status_code=400, detail="Nenhuma guia válida encontrada para transmissão.")

        if payload.simulado:
            # Fluxo Simulado
            recibo_simulado = f"REC{int(time.time()*1000)}"
            for guia in guias_para_envio:
                atualizar_status_gnre_guia(
                    guia["numero_tx"], 
                    "TRANSMITIDO", 
                    {"numero_recibo": recibo_simulado, "motivo_rejeicao": ""}
                )
            return {
                "success": True, 
                "simulado": True, 
                "numero_recibo": recibo_simulado, 
                "mensagem": "Lote transmitido com sucesso (Simulado)."
            }
        else:
            # Fluxo Real com SEFAZ
            # Ajusta campos para o formato do XML
            guias_xml = []
            for g in guias_para_envio:
                guias_xml.append({
                    "uf_favorecida": g["uf_favorecida"],
                    "cnpj_emitente": g["cnpj_emitente"],
                    "codigo_receita": g["codigo_receita"],
                    "valor": str(g["valor"]),
                    "data_vencimento": g["data_vencimento"],
                    "tipo_documento_origem": g["tipo_documento_origem"],
                    "documento_origem": g["documento_origem"],
                    "chave_acesso_nfe": g["chave_acesso_nfe"]
                })
            
            recibo = transmitir_lote_sefaz(guias_xml, payload.empresa, payload.ambiente)
            
            # Atualiza no banco
            for g in guias_para_envio:
                atualizar_status_gnre_guia(g["numero_tx"], "TRANSMITIDO", {"numero_recibo": recibo, "motivo_rejeicao": ""})
                
            return {
                "success": True,
                "simulado": False,
                "numero_recibo": recibo,
                "mensagem": f"Lote transmitido com sucesso. Recibo: {recibo}"
            }
            
    except Exception as e:
        logger.error(f"Erro na transmissão do lote GNRE: {e}")
        return {"success": False, "error": str(e)}


@router.post("/consultar")
def api_consultar_resultado(payload: ConsultarPayload):
    try:
        logger.info(f"Consultando recibo GNRE {payload.numero_recibo}. Simulado: {payload.simulado}")
        
        # Busca guias vinculadas a este recibo no banco
        todas_guias = listar_gnre_guias()
        guias_lote = [g for g in todas_guias if g["numero_recibo"] == payload.numero_recibo]

        if payload.simulado:
            # Simulação de processamento fiscal
            time.sleep(1) # Simula delay
            
            for index, guia in enumerate(guias_lote):
                # Gera um código de barras simulado (válido para SISPAG)
                # O formato do código de barras da GNRE com 48 dígitos
                valor_str = f"{int(round(guia['valor'] * 100)):011}"
                # Código de barras padrão de concessionárias (inicia com 8589...)
                cod_barras_simulado = f"85890000001{valor_str}202607151043661900010500"
                
                atualizar_status_gnre_guia(
                    guia["numero_tx"],
                    "SUCESSO",
                    {
                        "codigo_barras": cod_barras_simulado,
                        "linha_digitavel": cod_barras_simulado,
                        "status": "SUCESSO"
                    }
                )
            return {"success": True, "simulado": True, "mensagem": "Lote processado com sucesso (Simulado)."}
        else:
            # Consulta real à SEFAZ
            xml_resposta = consultar_lote_sefaz(payload.numero_recibo, payload.empresa, payload.ambiente)
            
            # Executa parser
            dados_guias_recebidas = extrair_dados_guia_xml(xml_resposta)
            
            # Atualiza cada guia correspondente no banco
            for dados in dados_guias_recebidas:
                # Localiza a guia no banco correspondente ao documento origem
                doc_origem = dados.get("documento_origem")
                
                guia_banco = None
                for g in guias_lote:
                    if g["documento_origem"] == doc_origem:
                        guia_banco = g
                        break
                
                if guia_banco:
                    if dados["status"] == "SUCESSO":
                        atualizar_status_gnre_guia(
                            guia_banco["numero_tx"],
                            "SUCESSO",
                            {
                                "codigo_barras": dados["codigo_barras"],
                                "linha_digitavel": dados["linha_digitavel"],
                                "status": "SUCESSO",
                                "xml_retorno": xml_resposta
                            }
                        )
                    else:
                        atualizar_status_gnre_guia(
                            guia_banco["numero_tx"],
                            "REJEITADO",
                            {
                                "status": "REJEITADO",
                                "motivo_rejeicao": dados["motivo_rejeicao"],
                                "xml_retorno": xml_resposta
                            }
                        )
            
            return {"success": True, "simulado": False, "mensagem": "Lote consultado e sincronizado com a SEFAZ."}
            
    except Exception as e:
        logger.error(f"Erro na consulta do lote GNRE: {e}")
        return {"success": False, "error": str(e)}


@router.post("/gerar_remessa")
def api_gerar_remessa(payload: GerarRemessaPayload):
    try:
        logger.info(f"Gerando remessa SISPAG para {len(payload.numero_tx_list)} guias.")
        
        # Busca as guias no banco
        todas_guias = listar_gnre_guias()
        guias_remessa = [g for g in todas_guias if g["numero_tx"] in payload.numero_tx_list]
        
        # Filtra apenas as de sucesso (processadas)
        guias_validas = [g for g in guias_remessa if g["status"] == "SUCESSO"]
        
        if not guias_validas:
            raise HTTPException(status_code=400, detail="Nenhuma guia com status SUCESSO selecionada.")

        # Prepara dados da empresa
        dados_empresa_dict = payload.dados_empresa.model_dump()
        
        # Gera o CNAB
        conteudo_cnab = gerar_remessa_sispag_tributos(dados_empresa_dict, guias_validas)
        
        # Salva o arquivo em PASTA_SAIDA
        config.ensure_directories()
        nome_arquivo = f"SISPAG_GNRE_{int(time.time())}.REM"
        caminho_arquivo = os.path.join(config.PASTA_SAIDA, nome_arquivo)
        
        with open(caminho_arquivo, "w", encoding="ascii", errors="replace") as f:
            f.write(conteudo_cnab)
            
        # Atualiza status das guias para PAGO (ou aguardando pagamento)
        for g in guias_validas:
            atualizar_status_gnre_guia(g["numero_tx"], "PAGO")

        return {
            "success": True,
            "arquivo": nome_arquivo,
            "caminho_completo": caminho_arquivo,
            "conteudo": conteudo_cnab
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar remessa SISPAG: {e}")
        return {"success": False, "error": str(e)}


@router.get("/notas_difal")
def api_listar_notas_difal():
    """
    Retorna as notas de despesa que possuem valor_difal > 0 para que possam
    ser importadas e transformadas em guias GNRE na interface.
    """
    try:
        notas = listar_notas()
        # Filtra notas pendentes com valor_difal
        notas_difal = []
        for n in notas:
            val_difal = float(n.get("valor_difal", 0) or 0)
            if val_difal > 0 and n.get("status") in ("PENDENTE", "APROVADA"):
                # Busca se já tem uma guia GNRE gerada para esta nota para evitar duplicidade
                todas_guias = listar_gnre_guias()
                guia_existente = any(g.get("nota_ref_tx") == n["numero_tx"] for g in todas_guias)
                if not guia_existente:
                    notas_difal.append(n)
                    
        return {"success": True, "notas": notas_difal}
    except Exception as e:
        logger.error(f"Erro ao listar notas com DIFAL: {e}")
        return {"success": False, "error": str(e)}
