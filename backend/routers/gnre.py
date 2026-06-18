import os
import time
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from fastapi.responses import StreamingResponse, FileResponse
from services.database import (
    listar_gnre_guias, salvar_gnre_guia, atualizar_status_gnre_guia, listar_notas,
    listar_gnre_lotes, salvar_gnre_lote, get_gnre_lote
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


@router.get("/pdf/{numero_tx}")
def api_baixar_pdf_guia(numero_tx: str):
    try:
        # Busca a guia no banco
        todas_guias = listar_gnre_guias()
        guia = next((g for g in todas_guias if g["numero_tx"] == numero_tx), None)
        
        if not guia:
            raise HTTPException(status_code=404, detail="Guia GNRE não encontrada.")
            
        from backend.services.pdf_service import gerar_pdf_gnre
        from fastapi.responses import FileResponse
        caminho_pdf = gerar_pdf_gnre(guia)
        
        return FileResponse(
            caminho_pdf,
            media_type="application/pdf",
            filename=os.path.basename(caminho_pdf),
            headers={"Access-Control-Expose-Headers": "Content-Disposition"}
        )
    except Exception as e:
        logger.error(f"Erro ao gerar PDF da guia GNRE: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/processar_lote_xmls")
async def api_processar_lote_xmls(
    files: Optional[List[UploadFile]] = File(None),
    payment_date: Optional[str] = Form(None),
    simulado: bool = Form(True),
    ambiente: int = Form(2),
    empresa: str = Form("LALUA"),
    processar_pasta_local: bool = Form(False)
):
    """
    Processa um lote de arquivos XML de NFe (enviados ou da pasta local),
    extrai os dados da guia (DIFAL + FCP), realiza a transmissão real ou simulada,
    gera a remessa SISPAG (CNAB 240) e cria o registro de lote com streaming de logs em tempo real.
    """
    async def event_generator():
        import shutil
        import tempfile
        import json
        import xml.etree.ElementTree as ET
        from utils.xml_utils import ler_xml_nfe

        def log_event(status: str, msg: str, progress: int = None, **kwargs):
            timestamp = datetime.now().strftime("%H:%M:%S")
            data = {"status": status, "message": f"[{timestamp}] {msg}"}
            if progress is not None:
                data["progress"] = progress
            data.update(kwargs)
            return f"data: {json.dumps(data)}\n\n"

        yield log_event("info", "Iniciando processamento de lote GNRE...", progress=0)
        
        temp_dir = tempfile.mkdtemp()
        xml_paths = []
        
        try:
            if processar_pasta_local:
                # Ler da pasta local
                nf_dir = os.getenv("NF_DIR") or os.path.join(os.path.dirname(config.BASE_DIR), "NF")
                yield log_event("info", f"Escaneando pasta local: {nf_dir}")
                if not os.path.exists(nf_dir):
                    os.makedirs(nf_dir, exist_ok=True)
                
                local_files = [f for f in os.listdir(nf_dir) if f.lower().endswith(".xml")]
                yield log_event("info", f"Encontrados {len(local_files)} arquivos XML na pasta local.")
                
                for f in local_files:
                    src_path = os.path.join(nf_dir, f)
                    dest_path = os.path.join(temp_dir, f)
                    shutil.copy(src_path, dest_path)
                    xml_paths.append(dest_path)
            else:
                # Ler dos arquivos enviados
                if not files:
                    yield log_event("error", "Nenhum arquivo XML enviado e processamento local desativado.")
                    yield f"data: {json.dumps({'status': 'done', 'success': False})}\n\n"
                    return
                
                yield log_event("info", f"Processando {len(files)} arquivos XML enviados...")
                for idx, file in enumerate(files):
                    temp_file_path = os.path.join(temp_dir, f"upload_{idx}_{file.filename}")
                    with open(temp_file_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    xml_paths.append(temp_file_path)
            
            # Helper to parse emitter CNPJ
            def extrair_cnpj_emitente(caminho_xml):
                try:
                    tree = ET.parse(caminho_xml)
                    root = tree.getroot()
                    for el in root.iter():
                        if el.tag.split('}')[-1] == 'emit':
                            for sub in el.iter():
                                if sub.tag.split('}')[-1] == 'CNPJ':
                                    return sub.text
                except:
                    pass
                return None

            guias_validas = []
            yield log_event("info", "Iniciando parsing dos arquivos XML NFe...", progress=10)
            
            for path in xml_paths:
                filename = os.path.basename(path)
                yield log_event("info", f"Analisando arquivo: {filename}")
                
                # Executa parser
                nfe_data = ler_xml_nfe(path)
                if not nfe_data:
                    yield log_event("warning", f"Arquivo {filename} não pôde ser lido como NFe válida. Ignorando.")
                    continue
                
                nNF = nfe_data.get("nf_numero", "0")
                chave = nfe_data.get("chave_acesso", "")
                uf_destino = nfe_data.get("uf_destino", "PE")
                
                # Extrai cnpj emitente ou usa o padrão
                cnpj_emitente = extrair_cnpj_emitente(path)
                if not cnpj_emitente:
                    cnpj_emitente = "10436619000105" if empresa == "LALUA" else "12345678000199"
                
                vICMSUFDest = nfe_data.get("valor_difal", 0.0)
                vFCPUFDest = nfe_data.get("valor_fcp", 0.0)
                valor_guia = round(vICMSUFDest + vFCPUFDest, 2)
                
                if valor_guia <= 0:
                    yield log_event("warning", f"NF {nNF} não possui valores de DIFAL ({vICMSUFDest}) ou FCP ({vFCPUFDest}) calculados. Ignorando.")
                    continue
                
                yield log_event("info", f"NF {nNF} identificada (UF: {uf_destino}) - DIFAL: R$ {vICMSUFDest:.2f} + FCP: R$ {vFCPUFDest:.2f} = R$ {valor_guia:.2f}")
                
                guias_validas.append({
                    "nota_ref_tx": f"TX{nNF}_{int(time.time())}",
                    "uf_favorecida": uf_destino,
                    "cnpj_emitente": cnpj_emitente,
                    "codigo_receita": "100102",  # DIFAL Consumidor Final
                    "valor": valor_guia,
                    "data_vencimento": nfe_data.get("data_emissao") or datetime.now().strftime("%Y-%m-%d"),
                    "documento_origem": nNF,
                    "tipo_documento_origem": "10",
                    "chave_acesso_nfe": chave,
                    "status": "PENDENTE"
                })
            
            if not guias_validas:
                yield log_event("error", "Nenhuma NFe com valores de DIFAL/FCP pendente de GNRE foi encontrada.")
                yield f"data: {json.dumps({'status': 'done', 'success': False})}\n\n"
                return
            
            yield log_event("info", f"Total de {len(guias_validas)} guias válidas extraídas com sucesso do lote.", progress=30)
            
            # Salvando no banco
            for guia in guias_validas:
                salvar_gnre_guia(guia)
            
            # Transmissão
            recibo = ""
            if simulado:
                yield log_event("info", "[Simulado] Transmitindo lote de guias para SEFAZ...", progress=40)
                yield log_event("info", f"[Simulado] Enviando {len(guias_validas)} guias via protocolo SOAP mTLS...")
                await asyncio.sleep(1.5)
                recibo = f"REC{int(time.time()*1000)}"
                yield log_event("info", f"[Simulado] Lote aceito pela SEFAZ. Recibo retornado: {recibo}", progress=60)
                yield log_event("info", "[Simulado] Aguardando 3s para consulta de processamento...", progress=70)
                await asyncio.sleep(1.5)
                yield log_event("info", f"[Simulado] Consultando resultado do recibo {recibo} na SEFAZ...")
                await asyncio.sleep(1.0)
                
                # Atualiza guias para SUCESSO com cod barras
                for idx, guia in enumerate(guias_validas):
                    valor_str = f"{int(round(guia['valor'] * 100)):011}"
                    cod_barras_simulado = f"85890000001{valor_str}202607151043661900010500"
                    
                    atualizar_status_gnre_guia(
                        guia["nota_ref_tx"],
                        "SUCESSO",
                        {
                            "codigo_barras": cod_barras_simulado,
                            "linha_digitavel": cod_barras_simulado,
                            "numero_recibo": recibo,
                            "status": "SUCESSO"
                        }
                    )
                    guia["status"] = "SUCESSO"
                    guia["codigo_barras"] = cod_barras_simulado
                    guia["linha_digitavel"] = cod_barras_simulado
                    guia["numero_recibo"] = recibo
                    yield log_event("info", f"Guia NF {guia['documento_origem']} gerada com SUCESSO! Código de Barras: {cod_barras_simulado}")
                
            else:
                # Transmissão Real
                yield log_event("info", f"Transmitindo lote real para a SEFAZ (Empresa: {empresa}, Ambiente: {'Produção' if ambiente == 1 else 'Homologação'})...", progress=40)
                
                guias_xml_payload = []
                for g in guias_validas:
                    guias_xml_payload.append({
                        "uf_favorecida": g["uf_favorecida"],
                        "cnpj_emitente": g["cnpj_emitente"],
                        "codigo_receita": g["codigo_receita"],
                        "valor": str(g["valor"]),
                        "data_vencimento": g["data_vencimento"],
                        "tipo_documento_origem": g["tipo_documento_origem"],
                        "documento_origem": g["documento_origem"],
                        "chave_acesso_nfe": g["chave_acesso_nfe"]
                    })
                
                try:
                    recibo = transmitir_lote_sefaz(guias_xml_payload, empresa, ambiente)
                    yield log_event("info", f"Lote transmitido com sucesso! Recibo retornado: {recibo}", progress=55)
                    
                    # Atualiza guias para TRANSMITIDO
                    for g in guias_validas:
                        atualizar_status_gnre_guia(g["nota_ref_tx"], "TRANSMITIDO", {"numero_recibo": recibo})
                    
                    yield log_event("info", "Aguardando 8 segundos para processamento da SEFAZ...", progress=65)
                    for wait_sec in range(1, 9):
                        await asyncio.sleep(1.0)
                        yield log_event("info", f"Processando... {wait_sec}s/8s")
                    
                    yield log_event("info", f"Consultando resultado para o recibo {recibo}...", progress=75)
                    xml_resposta = consultar_lote_sefaz(recibo, empresa, ambiente)
                    
                    # Parser do XML de retorno da consulta
                    dados_guias_recebidas = extrair_dados_guia_xml(xml_resposta)
                    
                    for dados in dados_guias_recebidas:
                        doc_origem = dados.get("documento_origem")
                        guia_banco = next((g for g in guias_validas if g["documento_origem"] == doc_origem), None)
                        
                        if guia_banco:
                            if dados["status"] == "SUCESSO":
                                atualizar_status_gnre_guia(
                                    guia_banco["nota_ref_tx"],
                                    "SUCESSO",
                                    {
                                        "codigo_barras": dados["codigo_barras"],
                                        "linha_digitavel": dados["linha_digitavel"],
                                        "status": "SUCESSO",
                                        "xml_retorno": xml_resposta,
                                        "numero_recibo": recibo
                                    }
                                )
                                guia_banco["status"] = "SUCESSO"
                                guia_banco["codigo_barras"] = dados["codigo_barras"]
                                guia_banco["linha_digitavel"] = dados["linha_digitavel"]
                                guia_banco["numero_recibo"] = recibo
                                yield log_event("info", f"Guia NF {doc_origem} gerada com SUCESSO! Código de Barras: {dados['codigo_barras']}")
                            else:
                                atualizar_status_gnre_guia(
                                    guia_banco["nota_ref_tx"],
                                    "REJEITADO",
                                    {
                                        "status": "REJEITADO",
                                        "motivo_rejeicao": dados["motivo_rejeicao"],
                                        "xml_retorno": xml_resposta,
                                        "numero_recibo": recibo
                                    }
                                )
                                guia_banco["status"] = "REJEITADO"
                                guia_banco["motivo_rejeicao"] = dados["motivo_rejeicao"]
                                guia_banco["numero_recibo"] = recibo
                                yield log_event("error", f"Guia NF {doc_origem} REJEITADA pela SEFAZ: {dados['motivo_rejeicao']}")
                except Exception as e:
                    yield log_event("error", f"Erro na comunicação real com a SEFAZ: {str(e)}")
                    yield f"data: {json.dumps({'status': 'done', 'success': False})}\n\n"
                    return
            
            # CNAB e ZIP
            guias_sucesso = [g for g in guias_validas if g["status"] == "SUCESSO"]
            
            lote_id = f"LOTE{int(time.time()*1000)}"
            data_hora_lote = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            ambiente_nome = "producao" if ambiente == 1 else "homologacao"
            
            if not guias_sucesso:
                yield log_event("warning", "Nenhuma guia foi processada com sucesso no lote. O arquivo CNAB não será gerado.", progress=90)
                
                # Salva lote com falha
                lote_dados = {
                    "lote_id": lote_id,
                    "data_hora": data_hora_lote,
                    "ambiente": ambiente_nome,
                    "status": "Falha",
                    "recibos": recibo,
                    "xml_guias": json.dumps(guias_validas),
                    "cnab_filename": "",
                    "cnab_content": "",
                    "log_terminal": "Lote processado sem guias de sucesso."
                }
                salvar_gnre_lote(lote_dados)
                yield log_event("info", "Lote finalizado com erros.", progress=100)
                yield f"data: {json.dumps({'status': 'done', 'success': True, 'lote_id': lote_id})}\n\n"
                return
            
            yield log_event("info", f"Gerando remessa CNAB 240 v086 Itaú SISPAG para as {len(guias_sucesso)} guias...", progress=90)
            
            dados_empresa_dict = {
                "cnpj": "10436619000105" if empresa == "LALUA" else "12345678000199",
                "razao_social": "BOAH COMERCIO VAREJISTA" if empresa == "LALUA" else "SOLAR DISTRIBUIDORA LTDA",
                "agencia": "01234",
                "conta": "0012345",
                "dac": "6"
            }
            
            # Chama o gerador
            conteudo_cnab = gerar_remessa_sispag_tributos(dados_empresa_dict, guias_sucesso, payment_date)
            
            # Salva o arquivo localmente
            config.ensure_directories()
            cnab_filename = f"SISPAG_GNRE_{int(time.time())}.REM"
            caminho_arquivo = os.path.join(config.PASTA_SAIDA, cnab_filename)
            
            with open(caminho_arquivo, "w", encoding="ascii", errors="replace") as f:
                f.write(conteudo_cnab)
                
            yield log_event("info", f"CNAB salvo em: {caminho_arquivo}")
            
            # Salva lote no histórico
            lote_dados = {
                "lote_id": lote_id,
                "data_hora": data_hora_lote,
                "ambiente": ambiente_nome,
                "status": "Sucesso",
                "recibos": recibo,
                "xml_guias": json.dumps(guias_validas),
                "cnab_filename": cnab_filename,
                "cnab_content": conteudo_cnab,
                "log_terminal": "Processamento concluído com sucesso."
            }
            salvar_gnre_lote(lote_dados)
            
            yield log_event("info", f"Histórico de Lote salvo com ID: {lote_id}")
            yield log_event("info", "Processamento finalizado com sucesso!", progress=100)
            yield f"data: {json.dumps({'status': 'done', 'success': True, 'lote_id': lote_id})}\n\n"
            
        except Exception as err:
            logger.error(f"Erro no processamento do lote: {err}")
            yield log_event("error", f"Erro crítico: {str(err)}")
            yield f"data: {json.dumps({'status': 'done', 'success': False})}\n\n"
            
        finally:
            # Limpa pasta temporária
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    from datetime import datetime
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/lotes")
def api_listar_lotes():
    try:
        lotes = listar_gnre_lotes()
        return {"success": True, "lotes": lotes}
    except Exception as e:
        logger.error(f"Erro ao listar lotes GNRE: {e}")
        return {"success": False, "error": str(e)}


@router.get("/lotes/{lote_id}")
def api_get_lote_detalhes(lote_id: str):
    try:
        lote = get_gnre_lote(lote_id)
        if not lote:
            raise HTTPException(status_code=404, detail="Lote não encontrado.")
        return {"success": True, "lote": lote}
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do lote {lote_id}: {e}")
        return {"success": False, "error": str(e)}


@router.get("/lotes/{lote_id}/zip")
def api_baixar_zip_lote(lote_id: str):
    try:
        lote = get_gnre_lote(lote_id)
        if not lote:
            raise HTTPException(status_code=404, detail="Lote não encontrado.")
            
        import zipfile
        import io
        from backend.services.pdf_service import gerar_pdf_gnre
        from fastapi.responses import StreamingResponse
        
        guias = json.loads(lote.get("xml_guias", "[]"))
        guias_sucesso = [g for g in guias if g.get("status") == "SUCESSO"]
        if not guias_sucesso:
            raise HTTPException(status_code=400, detail="Este lote não possui guias geradas com sucesso.")
            
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for g in guias_sucesso:
                caminho_pdf = gerar_pdf_gnre(g)
                zip_file.write(caminho_pdf, arcname=os.path.basename(caminho_pdf))
                
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/x-zip-compressed",
            headers={
                "Content-Disposition": f"attachment; filename=guias_lote_{lote_id}.zip",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        logger.error(f"Erro ao gerar ZIP do lote {lote_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lotes/{lote_id}/cnab")
def api_baixar_cnab_lote(lote_id: str):
    try:
        lote = get_gnre_lote(lote_id)
        if not lote:
            raise HTTPException(status_code=404, detail="Lote não encontrado.")
            
        cnab_content = lote.get("cnab_content", "")
        if not cnab_content:
            raise HTTPException(status_code=400, detail="Este lote não possui arquivo CNAB gerado.")
            
        from fastapi.responses import StreamingResponse
        import io
        
        bio = io.BytesIO(cnab_content.encode("ascii", errors="replace"))
        filename = lote.get("cnab_filename") or f"SISPAG_GNRE_{lote_id}.REM"
        
        return StreamingResponse(
            bio,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        logger.error(f"Erro ao baixar CNAB do lote {lote_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

