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
    allow_origins=["*"], # Na produ├º├úo, usar a URL do Vercel
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
        if r.get("status", "") in ("PAGO", "PAGA", "CANCELADO", "CANCELADA"):
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
        
        # Remove campos do frontend que não existem na tabela
        chave_acesso = dados.pop("chave_acesso", None)
        if chave_acesso:
            obs = dados.get("observacao") or ""
            dados["observacao"] = f"[Sefaz: {chave_acesso}] {obs}".strip()
        
        is_recorrente = dados.pop("recorrente", 0)
        meses = dados.pop("meses_recorrencia", 1)
        
        numero_tx_principal = dados.get("numero_tx", "")
        import time
        import uuid
        from datetime import datetime
        from dateutil.relativedelta import relativedelta

        # Função auxiliar interna para não repetir código
        def processar_e_salvar(d_nota, idx_recorrencia=0):
            d_atual = dict(d_nota) # copia para evitar mutações indesejadas
            
            def avancar_mes(data_str, meses):
                if not data_str: return data_str
                fmt1, fmt2 = "%Y-%m-%d", "%d/%m/%Y"
                for fmt in (fmt1, fmt2):
                    try:
                        dt = datetime.strptime(data_str, fmt) + relativedelta(months=meses)
                        return dt.strftime(fmt)
                    except:
                        pass
                return data_str

            # Se for parcela recorrente, avança a data
            if idx_recorrencia > 0:
                d_atual["dt_emissao"] = avancar_mes(d_atual.get("dt_emissao"), idx_recorrencia)
                d_atual["dt_vencimento"] = avancar_mes(d_atual.get("dt_vencimento"), idx_recorrencia)
            
            # Garante um numero_tx único
            if not d_atual.get("numero_tx"):
                d_atual["numero_tx"] = f"TX{int(time.time()*1000) + idx_recorrencia}"
            
            tx_principal = d_atual["numero_tx"]
            salvar_nota(d_atual)
            
            # Gera as Guias (Notas) independentes para os impostos retidos
            for imp in impostos:
                valor_imp = float(imp.get("valor", 0))
                if valor_imp <= 0:
                    continue
                dt_venc_imp = imp.get("dt_venc_imp") or d_atual.get("dt_vencimento")
                # Se for recorrente, precisa avançar o imposto também se ele tiver data fixa informada
                if idx_recorrencia > 0 and imp.get("dt_venc_imp"):
                    dt_venc_imp = avancar_mes(imp["dt_venc_imp"], idx_recorrencia)
                tipo_imp = imp.get("tipo", "IMPOSTO")
                
                dados_guia = {
                    "fornecedor": f"GUIA {tipo_imp} - {d_atual.get('fornecedor', '')}",
                    "numero_nf": f"{d_atual.get('numero_nf', '')}-{tipo_imp}",
                    "dt_emissao": d_atual.get("dt_emissao"),
                    "dt_vencimento": dt_venc_imp,
                    "valor_bruto": valor_imp,
                    "descricao": f"Retenção de {tipo_imp} referente NF {d_atual.get('numero_nf', '')} do fornecedor {d_atual.get('fornecedor', '')}",
                    "categoria": "Impostos, Taxas e Contribuições",
                    "natureza": "Despesa Fixa",
                    "empresa": d_atual.get("empresa", ""),
                    "filial": d_atual.get("filial", ""),
                    "status": "PENDENTE",
                    "is_previsao": d_atual.get("is_previsao", 0),
                    "chave_ref": tx_principal # Link com a nota mãe
                }
                salvar_nota(dados_guia)

        # Lógica de fluxo principal
        if numero_tx_principal:
            # Edição normal
            processar_e_salvar(dados, 0)
        else:
            # Novo lançamento (pode ser único ou recorrente)
            if is_recorrente and meses > 1:
                id_recorrencia = str(uuid.uuid4())
                dados["recorrente"] = 1
                dados["id_recorrencia"] = id_recorrencia
                for i in range(meses):
                    dados["numero_tx"] = "" # Força gerar um novo por mês
                    processar_e_salvar(dados, i)
            else:
                processar_e_salvar(dados, 0)
                
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
        return {"success": False, "error": "Nota n├úo encontrada"}
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
    data_pagamento: Optional[str] = None

class BaixaLotePayload(BaseModel):
    ids: list[int]
    novo_status: str
    data_pagamento: Optional[str] = None

@app.post("/api/notas/dar_baixa")
def api_notas_dar_baixa(payload: BaixaPayload):
    try:
        atualizar_status_nota(payload.id, payload.novo_status, payload.data_pagamento)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/notas/dar_baixa_lote")
def api_notas_dar_baixa_lote(payload: BaixaLotePayload):
    try:
        for nota_id in payload.ids:
            atualizar_status_nota(nota_id, payload.novo_status, payload.data_pagamento)
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
    """Importa m├║ltiplos XMLs de NFe, extrai dados e salva no banco."""
    resultados = []
    importados = 0
    
    for f in files:
        try:
            content = await f.read()
            root = ET.fromstring(content)
            
            # Remove namespaces para facilitar a busca (NFe ou NFSe)
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]
            
            # Verifica se ├® uma NFSe (pode ter v├írias na lista)
            if root.tag == 'ConsultarNfseResposta' or root.find('.//CompNfse') is not None or root.tag == 'CompNfse':
                comp_nfses = root.findall('.//CompNfse')
                if not comp_nfses and root.tag == 'CompNfse':
                    comp_nfses = [root]
                
                for comp in comp_nfses:
                    inf = comp.find('.//InfNfse')
                    if inf is None: continue
                    
                    num_nf = inf.findtext('Numero', '')
                    
                    dt_raw = inf.findtext('DataEmissao', '')
                    dt_emissao = ""
                    if dt_raw:
                        parts = dt_raw[:10].split('-')
                        if len(parts) == 3: dt_emissao = f"{parts[2]}/{parts[1]}/{parts[0]}"
                    
                    fornecedor = inf.findtext('.//PrestadorServico/IdentificacaoPrestador/RazaoSocial', '')
                    if not fornecedor:
                        fornecedor = inf.findtext('.//PrestadorServico/RazaoSocial', '')
                        
                    cnpj_emit = inf.findtext('.//PrestadorServico/IdentificacaoPrestador/Cnpj', '')
                    
                    valor_bruto = 0.0
                    val_str = inf.findtext('.//Servico/Valores/ValorServicos', '0').replace(',', '.')
                    try: valor_bruto = float(val_str)
                    except: pass
                    
                    desc = inf.findtext('.//Servico/Discriminacao', '')
                    if desc: desc = "NFSe - " + desc[:150].replace('\n', ' ')
                    else: desc = f"NFSe Import - NF {num_nf}"
                    
                    impostos = []
                    def get_imp(path, tipo):
                        v = float(inf.findtext(path, '0').replace(',', '.'))
                        if v > 0: impostos.append({"tipo": tipo, "valor": v})
                        
                    get_imp('.//Servico/Valores/ValorIr', 'IRRF')
                    get_imp('.//Servico/Valores/ValorPis', 'PIS')
                    get_imp('.//Servico/Valores/ValorCofins', 'COFINS')
                    get_imp('.//Servico/Valores/ValorCsll', 'CSLL')
                    get_imp('.//Servico/Valores/ValorInss', 'INSS')
                    get_imp('.//Servico/Valores/ValorIssRetido', 'ISSQN')
                    
                    import time
                    numero_tx_principal = f"TX{int(time.time()*100)}"
                    
                    dados = {
                        "numero_tx": numero_tx_principal,
                        "fornecedor": fornecedor,
                        "cnpj": cnpj_emit,
                        "numero_nf": num_nf,
                        "dt_emissao": dt_emissao,
                        "dt_vencimento": dt_emissao,
                        "valor_bruto": valor_bruto,
                        "descricao": desc,
                        "empresa": "LALUA",
                        "filial": "LALUA MATRIZ",
                        "status": "PENDENTE",
                        "is_previsao": 0,
                        "impostos": list(impostos) # C├│pia para usar na gera├º├úo de guias depois do pop
                    }
                    
                    salvar_nota(dados)
                    
                    # Gera as Guias (Notas) independentes para os impostos retidos
                    for imp in impostos:
                        dados_guia = {
                            "numero_tx": f"TX{int(time.time()*1000)}_{imp['tipo']}",
                            "fornecedor": f"GUIA {imp['tipo']} - {fornecedor[:40]}",
                            "numero_nf": f"{num_nf}-{imp['tipo']}",
                            "dt_emissao": dt_emissao,
                            "dt_vencimento": dt_emissao,
                            "valor_bruto": imp['valor'],
                            "descricao": f"Reten├º├úo de {imp['tipo']} ref. NFSe {num_nf} - {fornecedor[:50]}",
                            "categoria": "Impostos, Taxas e Contribui├º├Áes",
                            "natureza": "Despesa Fixa",
                            "empresa": "LALUA",
                            "filial": "LALUA MATRIZ",
                            "status": "PENDENTE",
                            "is_previsao": 0,
                            "chave_ref": numero_tx_principal
                        }
                        salvar_nota(dados_guia)
                    
                    importados += 1
                    resultados.append({"arquivo": f.filename, "ok": True, "mensagem": f"NFSe {num_nf} - {fornecedor[:20]} - R$ {valor_bruto:.2f}"})
                continue # Vai para o pr├│ximo arquivo se for NFSe

            # Se n├úo for NFSe, tenta como NFe
            emit = root.find('.//emit')
            ide = root.find('.//ide')
            total = root.find('.//ICMSTot')
            
            fornecedor = ""
            cnpj_emit = ""
            num_nf = ""
            valor_nf = 0
            dt_emissao = ""
            
            if emit is not None:
                nome_el = emit.find('xNome')
                cnpj_el = emit.find('CNPJ')
                if nome_el is not None: fornecedor = nome_el.text
                if cnpj_el is not None: cnpj_emit = cnpj_el.text
            
            if ide is not None:
                nnf_el = ide.find('nNF')
                dt_el = ide.find('dhEmi')
                if nnf_el is not None: num_nf = nnf_el.text
                if dt_el is not None:
                    raw = dt_el.text[:10]  # 2024-01-15
                    parts = raw.split('-')
                    if len(parts) == 3:
                        dt_emissao = f"{parts[2]}/{parts[1]}/{parts[0]}"
            
            if total is not None:
                vnf_el = total.find('vNF')
                if vnf_el is not None: valor_nf = float(vnf_el.text)
            
            dados = {
                "fornecedor": fornecedor,
                "cnpj": cnpj_emit,
                "numero_nf": num_nf,
                "dt_emissao": dt_emissao,
                "dt_vencimento": dt_emissao,  # Pode ser ajustado depois
                "valor_bruto": valor_nf,
                "descricao": f"XML Import - NFe {num_nf}",
                "empresa": "LALUA",
                "filial": "LALUA MATRIZ",
                "status": "PENDENTE",
                "is_previsao": 0
            }
            
            salvar_nota(dados)
            importados += 1
            resultados.append({"arquivo": f.filename, "ok": True, "mensagem": f"NFe {num_nf} - {fornecedor[:20]} - R$ {valor_nf:.2f}"})
        except Exception as e:
            resultados.append({"arquivo": f.filename, "ok": False, "mensagem": str(e)})
    
    return {"success": True, "importados": importados, "resultados": resultados}

@app.get("/api/previsoes")
def api_previsoes(
    empresa: Optional[str] = None,
    dt_inicio: Optional[str] = None, 
    dt_fim: Optional[str] = None
):
    try:
        from datetime import datetime
        notas = listar_notas(empresa=empresa)
        previsoes = []
        for n in notas:
            if n.get("is_previsao") != 1:
                continue
            
            if dt_inicio and dt_fim:
                data_campo = n.get("dt_vencimento")
                if data_campo:
                    try:
                        d_obj = datetime.strptime(data_campo, "%d/%m/%Y")
                        d_ini = datetime.strptime(dt_inicio, "%Y-%m-%d")
                        d_fim = datetime.strptime(dt_fim, "%Y-%m-%d")
                        if not (d_ini <= d_obj <= d_fim):
                            continue
                    except:
                        pass
            
            previsoes.append(n)
            
        return {"success": True, "previsoes": previsoes}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/relatorios/rateio")
def api_relatorios_rateio(empresa: Optional[str] = None):
    try:
        # Pega todas as notas PAGAS ou PENDENTES para o relatorio
        notas = listar_notas(empresa=empresa)
        # Fallback para sqlite usando a configuração correta
        from services.database import _get_local_conn
        conn = _get_local_conn()
        conn.row_factory = __import__('sqlite3').Row
        cursor = conn.cursor()
        
        sql = """
            SELECT r.categoria, SUM(r.valor) as total
            FROM nota_rateio r
            JOIN notas n ON r.nota_id = n.id
            WHERE 1=1
        """
        args = []
        if empresa:
            sql += " AND n.empresa = ?"
            args.append(empresa)
            
        sql += " GROUP BY r.categoria ORDER BY total DESC"
        cursor.execute(sql, args)
        rows = cursor.fetchall()
        
        resultado = [{"centro_custo": r["categoria"] or "Geral", "total": r["total"]} for r in rows]
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
        return {"error": "Formato inv├ílido"}
    
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
    return {"error": "Arquivo n├úo encontrado"}

# Para rodar localmente de forma simples:
# uvicorn backend.main:app --reload --port 8000
@app.get("/api/vencimentos/semaforo")
def api_semaforo(empresa=None):
    notas = listar_notas(empresa=empresa)
    hoje = datetime.strptime(datetime.now().strftime("%d/%m/%Y"), "%d/%m/%Y")
    resultado = {"vencido": [], "hoje": [], "urgente": [], "proximo": []}
    totais    = {"vencido": 0.0, "hoje": 0.0, "urgente": 0.0, "proximo": 0.0}
    for n in notas:
        if n.get("status") in ("PAGO", "PAGA", "CANCELADO", "CANCELADA"):
            continue
        try:
            dt = datetime.strptime(n["dt_vencimento"], "%d/%m/%Y")
        except Exception:
            continue
        val  = float(n.get("valor_bruto", 0) or 0)
        diff = (dt - hoje).days
        if diff < 0:
            faixa = "vencido"
        elif diff == 0:
            faixa = "hoje"
        elif diff <= 3:
            faixa = "urgente"
        elif diff <= 30:
            faixa = "proximo"
        else:
            continue
        n["dias_para_vencer"] = diff
        n["faixa"] = faixa
        resultado[faixa].append(n)
        totais[faixa] += val
    for faixa in resultado:
        resultado[faixa].sort(key=lambda x: x["dias_para_vencer"])
    return {
        "success": True,
        "notas": resultado,
        "totais": {k: round(v, 2) for k, v in totais.items()},
        "contagens": {k: len(v) for k, v in resultado.items()}
    }


@app.get("/api/notas/verificar_duplicidade")
def api_verificar_duplicidade(cnpj: str, valor: float, mes: int, ano: int):
    notas = listar_notas()
    suspeitas = []
    def nc(c):
        return c.replace(".", "").replace("/", "").replace("-", "")
    for n in notas:
        if nc(n.get("cnpj", "")) != nc(cnpj):
            continue
        try:
            dt = datetime.strptime(n["dt_emissao"], "%d/%m/%Y")
            if dt.month != mes or dt.year != ano:
                continue
        except Exception:
            continue
        val_nota = float(n.get("valor_bruto", 0) or 0)
        if val_nota == 0:
            continue
        diff_pct = abs(val_nota - valor) / valor
        if diff_pct <= 0.02:
            confianca = 1.0 if diff_pct == 0 else round(1.0 - (diff_pct / 0.02) * 0.2, 2)
            n["confianca"] = confianca
            suspeitas.append(n)
    suspeitas.sort(key=lambda x: x["confianca"], reverse=True)
    return {"success": True, "is_duplicata": len(suspeitas) > 0, "suspeitas": suspeitas}


@app.post("/api/cnab/gerar")
def api_gerar_cnab(banco: str = "ITAU"):
    try:
        from cnab_generator import gerar_remessa_notas
        resultado = gerar_remessa_notas(banco=banco)
        return {"success": True, **resultado}
    except Exception as e:
        return {"success": False, "error": str(e)}
@app.post("/api/conciliacao/ofx")
async def api_conciliacao_ofx(file: UploadFile = File(...)):
    """Lê um arquivo OFX, extrai os débitos e faz o cruzamento com as notas pendentes."""
    try:
        import re
        from services.database import _get_local_conn, USE_SUPABASE
        content = await file.read()
        text = content.decode("utf-8", errors="ignore")
        
        # Parse básico de OFX via regex (OFX usa tags SGML sem fechamento estrito às vezes)
        transactions = []
        blocks = re.split(r'<STMTTRN>', text, flags=re.IGNORECASE)[1:]
        
        for b in blocks:
            b = b.split('</STMTTRN>')[0] if '</STMTTRN>' in b.upper() else b
            
            trnamt_m = re.search(r'<TRNAMT>([-\d\.]+)', b, re.IGNORECASE)
            dtposted_m = re.search(r'<DTPOSTED>(\d{8})', b, re.IGNORECASE)
            fitid_m = re.search(r'<FITID>([^<]+)', b, re.IGNORECASE)
            memo_m = re.search(r'<MEMO>([^<\r\n]+)', b, re.IGNORECASE)
            
            if trnamt_m and dtposted_m:
                amt = float(trnamt_m.group(1))
                if amt < 0: # Apenas saídas de caixa (débitos)
                    dt_raw = dtposted_m.group(1)
                    dt_str = f"{dt_raw[6:8]}/{dt_raw[4:6]}/{dt_raw[0:4]}"
                    transactions.append({
                        "tx_id": fitid_m.group(1).strip() if fitid_m else "OFX",
                        "tx_data": dt_str,
                        "tx_valor": abs(amt),
                        "tx_memo": memo_m.group(1).strip() if memo_m else ""
                    })
                    
        # Buscar notas pendentes e aprovadas
        conn = _get_local_conn()
        notas = [dict(r) for r in conn.execute("SELECT * FROM notas WHERE status IN ('PENDENTE', 'APROVADA')").fetchall()]
        
        matched = []
        unmatched = []
        
        for tx in transactions:
            found_nota = None
            for n in notas:
                val = float(n.get("valor_bruto", 0) or 0)
                # Aceita diferença de até 2 centavos
                if abs(val - tx["tx_valor"]) <= 0.02:
                    found_nota = n
                    break
                    
            if found_nota:
                if USE_SUPABASE:
                    try:
                        from supabase import create_client
                        import config
                        sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                        sb.table("notas").update({"status": "PAGO"}).eq("id", found_nota["id"]).execute()
                    except Exception as sb_err:
                        print(f"Aviso: Falha ao sincronizar com Supabase: {sb_err}")
                
                conn.execute("UPDATE notas SET status='PAGO' WHERE id=?", (found_nota["id"],))
                notas.remove(found_nota) # Evita associar a mesma nota a duas transações do mesmo valor
                
                matched.append({
                    "tx_id": tx["tx_id"],
                    "tx_data": tx["tx_data"],
                    "tx_valor": tx["tx_valor"],
                    "nota_id": found_nota["id"],
                    "nota_fornecedor": found_nota.get("fornecedor", "Desconhecido")
                })
            else:
                unmatched.append(tx)
                
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "matched": matched,
            "unmatched": unmatched
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.get("/api/relatorios/avancado")
def api_relatorios_avancado(
    dt_inicio: Optional[str] = None, 
    dt_fim: Optional[str] = None, 
    tipo_data: Optional[str] = "vencimento", 
    status: Optional[str] = None, 
    empresa: Optional[str] = None,
    fornecedor: Optional[str] = None,
    categoria: Optional[str] = None
):
    try:
        from services.database import _get_local_conn, USE_SUPABASE
        import config
        from datetime import datetime
        
        # 1. Obter base de notas
        notas = listar_notas(status=status, empresa=empresa)
        
        # 2. Filtrar localmente no python para suportar ambos os bancos e filtros complexos
        filtradas = []
        for n in notas:
            # Filtro fornecedor
            if fornecedor and fornecedor.lower() not in (n.get("fornecedor") or "").lower():
                continue
                
            # Filtro categoria
            if categoria and categoria.lower() not in (n.get("categoria") or "").lower():
                continue
                
            # Filtro data
            if dt_inicio and dt_fim:
                data_campo = n.get("dt_vencimento") if tipo_data == "vencimento" else n.get("dt_emissao")
                if data_campo:
                    try:
                        d_obj = datetime.strptime(data_campo, "%d/%m/%Y")
                        d_ini = datetime.strptime(dt_inicio, "%Y-%m-%d")
                        d_fim = datetime.strptime(dt_fim, "%Y-%m-%d")
                        if not (d_ini <= d_obj <= d_fim):
                            continue
                    except:
                        pass
                        
            filtradas.append(n)
            
        return {"success": True, "notas": filtradas}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/relatorios/tributos")
def api_relatorios_tributos(
    dt_inicio: Optional[str] = None, 
    dt_fim: Optional[str] = None
):
    try:
        from services.database import _get_local_conn, USE_SUPABASE, get_nota_completa
        import config
        from datetime import datetime
        
        notas = listar_notas()
        
        # Puxar todos os impostos de uma vez para não ter timeout dentro do loop
        impostos_map = {}
        if not USE_SUPABASE:
            conn = _get_local_conn()
            todos_impostos = [dict(r) for r in conn.execute("SELECT * FROM nota_impostos").fetchall()]
            conn.close()
        else:
            try:
                from supabase import create_client
                supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                todos_impostos = supabase.table("nota_impostos").select("*").execute().data
            except:
                conn = _get_local_conn()
                todos_impostos = [dict(r) for r in conn.execute("SELECT * FROM nota_impostos").fetchall()]
                conn.close()
                
        for imp in todos_impostos:
            impostos_map.setdefault(imp["nota_id"], []).append(imp)
        
        tributos_retorno = []
        for n in notas:
            # Filtrar data
            if dt_inicio and dt_fim:
                data_campo = n.get("dt_vencimento")
                if data_campo:
                    try:
                        d_obj = datetime.strptime(data_campo, "%d/%m/%Y")
                        d_ini = datetime.strptime(dt_inicio, "%Y-%m-%d")
                        d_fim = datetime.strptime(dt_fim, "%Y-%m-%d")
                        if not (d_ini <= d_obj <= d_fim):
                            continue
                    except:
                        pass
                        
            impostos = impostos_map.get(n["id"], [])

            for imp in impostos:
                tributos_retorno.append({
                    "nota_id": n["id"],
                    "fornecedor_origem": n.get("fornecedor"),
                    "numero_nf": n.get("numero_nf"),
                    "dt_emissao": n.get("dt_emissao"),
                    "dt_vencimento": n.get("dt_vencimento"),
                    "imposto_tipo": imp.get("tipo"),
                    "imposto_valor": imp.get("valor"),
                    "imposto_vencimento": imp.get("dt_venc_imp") or n.get("dt_vencimento"),
                    "status_pagamento": imp.get("status") or n.get("status")
                })
                
        return {"success": True, "tributos": tributos_retorno}
    except Exception as e:
        return {"success": False, "error": str(e)}

