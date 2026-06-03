import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Permite importar do projeto raiz
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import listar_notas
import config

app = FastAPI(title="Boah ERP API")

# Habilitar CORS para o Frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Na produção, usar a URL do Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "API do ERP Boah/Solar rodando com sucesso!"}

@app.get("/api/status")
def status():
    return {
        "supabase_connected": config.USE_SUPABASE,
        "env": "development"
    }

@app.get("/api/notas")
def get_notas():
    notas = listar_notas()
    return {"notas": notas}

from datetime import datetime, timedelta

@app.get("/api/cockpit")
def get_cockpit():
    notas = listar_notas()
    hoje_dt = datetime.strptime(datetime.now().strftime("%d/%m/%Y"), "%d/%m/%Y")
    
    vencem_hoje_qtd, vencem_hoje_val = 0, 0.0
    atrasados_qtd, atrasados_val = 0, 0.0
    proximos_qtd, proximos_val = 0, 0.0
    urgentes = []
    
    for r in notas:
        if r["status"] in ("PAGA", "CANCELADA"):
            continue
            
        try:
            dt_venc = datetime.strptime(r["dt_vencimento"], "%d/%m/%Y")
        except:
            continue
            
        val = r["valor_bruto"]
        
        if dt_venc < hoje_dt:
            atrasados_qtd += 1
            atrasados_val += val
            urgentes.append(r)
        elif dt_venc == hoje_dt:
            vencem_hoje_qtd += 1
            vencem_hoje_val += val
            urgentes.append(r)
        elif hoje_dt < dt_venc <= (hoje_dt + timedelta(days=3)):
            proximos_qtd += 1
            proximos_val += val
            
    # Ordena urgentes pela data (mais antigo primeiro)
    urgentes.sort(key=lambda x: datetime.strptime(x["dt_vencimento"], "%d/%m/%Y"))
            
    return {
        "cards": {
            "hoje": {"qtd": vencem_hoje_qtd, "valor": vencem_hoje_val},
            "atrasados": {"qtd": atrasados_qtd, "valor": atrasados_val},
            "proximos": {"qtd": proximos_qtd, "valor": proximos_val}
        },
        "urgentes": urgentes
    }

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from services.database import salvar_nota, buscar_fornecedor_por_cnpj
from services.sefaz_service import extract_info_from_key

class SefazQuery(BaseModel):
    chave: str

@app.post("/api/sefaz/consultar")
def api_sefaz_consultar(query: SefazQuery):
    try:
        info = extract_info_from_key(query.chave.strip())
        
        # Tenta buscar fornecedor
        forn = buscar_fornecedor_por_cnpj(info["cnpj"])
        if forn:
            info["razao_social"] = forn["razao_social"]
            info["categoria"] = forn.get("categoria", "")
        else:
            info["razao_social"] = ""
            info["categoria"] = ""
            
        return {"success": True, "info": info}
    except Exception as e:
        return {"success": False, "error": str(e)}

class NotaPayload(BaseModel):
    dados_base: Dict[str, Any]
    impostos: List[Dict[str, Any]] = []
    parcelas: List[Dict[str, Any]] = []
    rateio: List[Dict[str, Any]] = []
    itens: List[Dict[str, Any]] = []

@app.post("/api/salvar_nota")
def api_salvar_nota(payload: NotaPayload):
    try:
        dados = payload.dados_base
        impostos = payload.impostos
        
        # 1. Calcula o total retido
        total_retido = 0.0
        for imp in impostos:
            total_retido += float(imp.get("valor", 0))
            
        # 2. Desconta do valor bruto do fornecedor
        valor_original = float(dados.get("valor_bruto", 0))
        dados["valor_bruto"] = round(valor_original - total_retido, 2)
        
        # 3. Salva a nota principal (com os rateios e itens vinculados a ela)
        dados["impostos"] = impostos  # Apenas para registro histórico se o DB suportar
        dados["parcelas"] = payload.parcelas
        dados["rateio"] = payload.rateio
        dados["itens"] = payload.itens
        
        numero_tx_principal = dados.get("numero_tx", "")
        # A função salvar_nota retorna ou injeta o numero_tx
        import time
        if not numero_tx_principal:
            numero_tx_principal = f"TX{int(time.time()*100)}"
            dados["numero_tx"] = numero_tx_principal
            
        salvar_nota(dados)
        
        # 4. Gera as Guias (Notas) independentes para os impostos retidos
        for imp in impostos:
            valor_imp = float(imp.get("valor", 0))
            if valor_imp <= 0:
                continue
                
            dt_venc_imp = imp.get("dt_venc_imp") or dados.get("dt_vencimento")
            tipo_imp = imp.get("tipo", "IMPOSTO")
            
            dados_guia = {
                "fornecedor": f"GUIA {tipo_imp} - {dados.get('fornecedor', '')}",
                "numero_nf": f"{dados.get('numero_nf', '')}-{tipo_imp}",
                "dt_emissao": dados.get("dt_emissao"),
                "dt_vencimento": dt_venc_imp,
                "valor_bruto": valor_imp,
                "descricao": f"Retenção de {tipo_imp} referente NF {dados.get('numero_nf', '')} do fornecedor {dados.get('fornecedor', '')}",
                "categoria": "Impostos, Taxas e Contribuições",
                "natureza": "Despesa Fixa",
                "empresa": dados.get("empresa", ""),
                "filial": dados.get("filial", ""),
                "status": "PENDENTE",
                "is_previsao": dados.get("is_previsao", 0),
                "chave_ref": numero_tx_principal # Link com a nota mãe
            }
            salvar_nota(dados_guia)
            
        return {"success": True}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

from services.database import listar_notas, atualizar_status_nota, get_nota_completa

@app.get("/api/nota/{nota_id}")
def api_nota_detalhes(nota_id: int):
    try:
        nota = get_nota_completa(nota_id)
        if nota:
            return {"success": True, "nota": nota}
        return {"success": False, "error": "Nota não encontrada"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/notas/pendentes")
def api_notas_pendentes(empresa: Optional[str] = None):
    try:
        # Busca as notas com status PENDENTE
        notas = listar_notas(status="PENDENTE", empresa=empresa)
        return {"success": True, "notas": notas}
    except Exception as e:
        return {"success": False, "error": str(e)}

class BaixaPayload(BaseModel):
    id: int
    novo_status: str

@app.post("/api/notas/dar_baixa")
def api_notas_dar_baixa(payload: BaixaPayload):
    try:
        atualizar_status_nota(payload.id, payload.novo_status)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/notas/busca")
def api_notas_busca(status: Optional[str] = None, empresa: Optional[str] = None, busca: Optional[str] = None):
    try:
        notas = listar_notas(status=status, empresa=empresa, busca=busca)
        return {"success": True, "notas": notas}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/boletim")
def api_boletim(empresa: Optional[str] = None):
    """Retorna notas PAGAS agrupadas por dt_vencimento para montar o boletim de caixa."""
    try:
        notas_pagas = listar_notas(status="PAGO", empresa=empresa)
        # Agrupa por data
        from collections import defaultdict
        por_data = defaultdict(lambda: {"notas": [], "total": 0})
        for n in notas_pagas:
            dt = n.get("dt_vencimento", "Sem Data")
            valor = float(n.get("valor_bruto", 0) or 0)
            por_data[dt]["notas"].append(n)
            por_data[dt]["total"] += valor
        
        # Converte para lista ordenada
        resultado = []
        for dt in sorted(por_data.keys(), reverse=True):
            resultado.append({
                "data": dt,
                "total": round(por_data[dt]["total"], 2),
                "qtd": len(por_data[dt]["notas"]),
                "notas": por_data[dt]["notas"]
            })
        
        return {"success": True, "boletim": resultado}
    except Exception as e:
        return {"success": False, "error": str(e)}

from fastapi import UploadFile, File
import xml.etree.ElementTree as ET

@app.post("/api/importar/xml")
async def api_importar_xml(files: list[UploadFile] = File(...)):
    """Importa múltiplos XMLs de NFe, extrai dados e salva no banco."""
    resultados = []
    importados = 0
    
    for f in files:
        try:
            content = await f.read()
            root = ET.fromstring(content)
            # Namespace padrão da NFe
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Tenta extrair dados básicos
            emit = root.find('.//nfe:emit', ns)
            ide = root.find('.//nfe:ide', ns)
            total = root.find('.//nfe:ICMSTot', ns)
            
            fornecedor = ""
            cnpj_emit = ""
            num_nf = ""
            valor_nf = 0
            dt_emissao = ""
            
            if emit is not None:
                nome_el = emit.find('nfe:xNome', ns)
                cnpj_el = emit.find('nfe:CNPJ', ns)
                if nome_el is not None: fornecedor = nome_el.text
                if cnpj_el is not None: cnpj_emit = cnpj_el.text
            
            if ide is not None:
                nnf_el = ide.find('nfe:nNF', ns)
                dt_el = ide.find('nfe:dhEmi', ns)
                if nnf_el is not None: num_nf = nnf_el.text
                if dt_el is not None:
                    raw = dt_el.text[:10]  # 2024-01-15
                    parts = raw.split('-')
                    if len(parts) == 3:
                        dt_emissao = f"{parts[2]}/{parts[1]}/{parts[0]}"
            
            if total is not None:
                vnf_el = total.find('nfe:vNF', ns)
                if vnf_el is not None: valor_nf = float(vnf_el.text)
            
            dados = {
                "fornecedor": fornecedor,
                "cnpj": cnpj_emit,
                "numero_nf": num_nf,
                "dt_emissao": dt_emissao,
                "dt_vencimento": dt_emissao,  # Pode ser ajustado depois
                "valor_bruto": valor_nf,
                "descricao": f"XML Import - NF {num_nf}",
                "empresa": "LALUA",
                "filial": "LALUA MATRIZ",
                "status": "PENDENTE",
                "is_previsao": 0
            }
            
            salvar_nota(dados)
            importados += 1
            resultados.append({"arquivo": f.filename, "ok": True, "mensagem": f"NF {num_nf} - {fornecedor} - R$ {valor_nf:.2f}"})
        except Exception as e:
            resultados.append({"arquivo": f.filename, "ok": False, "mensagem": str(e)})
    
    return {"success": True, "importados": importados, "resultados": resultados}

@app.get("/api/previsoes")
def api_previsoes(empresa: Optional[str] = None):
    try:
        # Busca todas as notas, filtra no Python as previsões (ou altera listar_notas depois)
        notas = listar_notas(empresa=empresa)
        previsoes = [n for n in notas if n.get("is_previsao") == 1]
        return {"success": True, "previsoes": previsoes}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/relatorios/rateio")
def api_relatorios_rateio(empresa: Optional[str] = None):
    try:
        # Pega todas as notas PAGAS ou PENDENTES para o relatorio
        notas = listar_notas(empresa=empresa)
        # Fallback para sqlite direto para simplificar o agrupamento de rateio
        import sqlite3
        conn = sqlite3.connect("banco.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = """
            SELECT r.centro_custo, SUM(r.valor) as total
            FROM nota_rateio r
            JOIN notas n ON r.nota_id = n.id
            WHERE 1=1
        """
        args = []
        if empresa:
            sql += " AND n.empresa = ?"
            args.append(empresa)
            
        sql += " GROUP BY r.centro_custo ORDER BY total DESC"
        cursor.execute(sql, args)
        rows = cursor.fetchall()
        
        resultado = [{"centro_custo": r["centro_custo"], "total": r["total"]} for r in rows]
        conn.close()
        
        return {"success": True, "rateio": resultado}
    except Exception as e:
        # Se falhar (ex: usando supabase e sem sqlite local), retorna vazio
        return {"success": False, "error": str(e), "rateio": []}

from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from utils.extratos_processor import ler_itau_pagamentos
import tempfile
import shutil
import json
from pydantic import BaseModel

class PagamentosPayload(BaseModel):
    pagamentos: list

@app.post("/api/importar_itau")
async def importar_itau(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xls', '.xlsx')):
        return {"error": "Formato inválido"}
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xls") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
            
        pagamentos = ler_itau_pagamentos(tmp_path)
        os.remove(tmp_path)
        return {"pagamentos": pagamentos}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/gerar_pdf_autorizacao")
async def gerar_pdf_autorizacao_endpoint(payload: PagamentosPayload):
    try:
        from backend.services.pdf_service import gerar_pdf_autorizacao
        caminho_pdf = gerar_pdf_autorizacao(payload.pagamentos)
        return FileResponse(
            caminho_pdf,
            media_type="application/pdf",
            filename=os.path.basename(caminho_pdf),
            headers={"Access-Control-Expose-Headers": "Content-Disposition"}
        )
    except Exception as e:
        return {"error": str(e)}

from typing import Optional

class TreinoPayload(BaseModel):
    cnpj: str
    nome: str
    responsavel: str
    categoria: str
    descricao: Optional[str] = ""

@app.post("/api/treinar_categorizacao")
async def treinar_categorizacao(payload: TreinoPayload):
    try:
        mem_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "categorias_aprendidas.json")
        mem_data = {"cnpj_mappings": {}, "nome_mappings": {}}
        if os.path.exists(mem_path):
            with open(mem_path, "r", encoding="utf-8") as f:
                mem_data = json.load(f)
                
        dados_treino = {
            "responsavel": payload.responsavel,
            "categoria": payload.categoria,
            "empresa": "LALUA",
            "observacao": payload.descricao if payload.descricao else "APRENDIDO PELO USUARIO"
        }
        
        if payload.cnpj and payload.cnpj != "00.000.000/0000-00":
            mem_data["cnpj_mappings"][payload.cnpj.strip()] = dados_treino
        else:
            mem_data["nome_mappings"][payload.nome.strip().upper()] = dados_treino
            
        with open(mem_path, "w", encoding="utf-8") as f:
            json.dump(mem_data, f, indent=4, ensure_ascii=False)
            
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

class HistoricoModernoPayload(BaseModel):
    pagamentos: list
    saldos: dict

@app.post("/api/salvar_historico_moderno")
async def salvar_historico_moderno(payload: HistoricoModernoPayload):
    try:
        from datetime import datetime
        historico_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "historico_autorizacoes")
        os.makedirs(historico_dir, exist_ok=True)
        data_hoje = datetime.now().strftime("%d_%m_%Y_%H%M%S")
        nome_arq = f"AUTORIZACAO_MODERNA_{data_hoje}.json"
        
        with open(os.path.join(historico_dir, nome_arq), "w", encoding="utf-8") as f:
            json.dump({
                "pagamentos": payload.pagamentos,
                "saldos": payload.saldos
            }, f, ensure_ascii=False)
            
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/historico_autorizacoes")
async def listar_historico():
    try:
        historico_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "historico_autorizacoes")
        if not os.path.exists(historico_dir):
            return {"arquivos": []}
            
        arquivos = []
        for f in os.listdir(historico_dir):
            if f.endswith(".pdf") or f.endswith(".json"):
                path = os.path.join(historico_dir, f)
                arquivos.append({
                    "nome": f,
                    "tamanho": os.path.getsize(path),
                    "data": os.path.getmtime(path),
                    "tipo": "moderno" if f.endswith(".json") else "padrao"
                })
        # Ordenar pelos mais recentes primeiro
        arquivos.sort(key=lambda x: x["data"], reverse=True)
        return {"arquivos": arquivos}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/download_autorizacao/{filename}")
async def download_historico(filename: str):
    historico_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "historico_autorizacoes")
    path = os.path.join(historico_dir, filename)
    if os.path.exists(path):
        is_json = filename.endswith(".json")
        return FileResponse(
            path,
            media_type="application/json" if is_json else "application/pdf",
            filename=filename,
            headers={"Access-Control-Expose-Headers": "Content-Disposition"}
        )
    return {"error": "Arquivo não encontrado"}

# Para rodar localmente de forma simples:
# uvicorn backend.main:app --reload --port 8000
