
"""
database.py — Gerenciamento do banco de dados (SQLite + Supabase) do Robô BOAH.
"""
import sqlite3
import os
import time
from datetime import datetime
from supabase import create_client, Client
import config
from services.logger_service import logger

# Configurações do Supabase
SUPABASE_URL = config.SUPABASE_URL
SUPABASE_KEY = config.SUPABASE_KEY
USE_SUPABASE = config.USE_SUPABASE

supabase: Client = None
if USE_SUPABASE:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Erro ao conectar no Supabase: {e}")
        USE_SUPABASE = False

# Caminho padrão do banco de dados local (como fallback)
DB_PATH = config.DB_PATH

def _get_local_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def db_conn():
    # Para compatibilidade com código que usa cursor SQL direto
    return _get_local_conn()

# ── FUNÇÕES DE INTERFACE (SUPABASE PREFERENCIAL) ──────────────────────────

def listar_pagamentos_autorizados(data_de=None, data_ate=None, empresa=None):
    if USE_SUPABASE:
        try:
            query = supabase.table("pagamentos_autorizados").select("*").order("data")
            if empresa:
                query = query.eq("empresa", empresa)
            res = query.execute()
            data = res.data
            
            # Filtro de data em Python (mesmo formato do original)
            resultado = []
            for r in data:
                try:
                    dt = datetime.strptime(r["data"], "%d/%m/%Y")
                    if data_de:
                        dt_de = datetime.strptime(data_de, "%d/%m/%Y")
                        if dt < dt_de: continue
                    if data_ate:
                        dt_ate = datetime.strptime(data_ate, "%d/%m/%Y")
                        if dt > dt_ate: continue
                except: pass
                resultado.append(r)
            return resultado
        except Exception as e:
            logger.error(f"Erro Supabase (listar_pagamentos): {e}")

    # Fallback SQLite
    conn = _get_local_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pagamentos_autorizados ORDER BY data ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def salvar_nota(dados):
    # Separa listas aninhadas
    impostos = dados.pop("impostos", [])
    parcelas = dados.pop("parcelas", [])
    rateio   = dados.pop("rateio",   [])
    itens    = dados.pop("itens",    [])

    if not dados.get("numero_tx"):
        dados["numero_tx"] = f"TX{int(time.time()*100)}"

    nota_id = None
    if USE_SUPABASE:
        try:
            # Salva Nota principal (UPSERT por numero_tx)
            res = supabase.table("notas").upsert(dados, on_conflict="numero_tx").execute()
            if res.data:
                nota_id = res.data[0]["id"]
                
                # Limpa e reinsere dependentes
                supabase.table("nota_impostos").delete().eq("nota_id", nota_id).execute()
                if impostos:
                    for i in impostos: i["nota_id"] = nota_id
                    supabase.table("nota_impostos").insert(impostos).execute()
                
                supabase.table("nota_parcelas").delete().eq("nota_id", nota_id).execute()
                if parcelas:
                    for p in parcelas: p["nota_id"] = nota_id
                    supabase.table("nota_parcelas").insert(parcelas).execute()

                supabase.table("nota_rateio").delete().eq("nota_id", nota_id).execute()
                if rateio:
                    for r in rateio: r["nota_id"] = nota_id
                    supabase.table("nota_rateio").insert(rateio).execute()

                supabase.table("nota_itens").delete().eq("nota_id", nota_id).execute()
                if itens:
                    for it in itens: it["nota_id"] = nota_id
                    supabase.table("nota_itens").insert(itens).execute()
                
                return dados["numero_tx"]
        except Exception as e:
            logger.error(f"Erro Supabase (salvar_nota): {e}")

    # Fallback SQLite (se Supabase falhar ou estiver desativado)
    conn = _get_local_conn()
    cursor = conn.cursor()
    keys = dados.keys()
    vals = [dados[k] for k in keys]
    query = f"INSERT OR REPLACE INTO notas ({','.join(keys)}) VALUES ({','.join(['?']*len(keys))})"
    cursor.execute(query, vals)
    row = cursor.execute("SELECT id FROM notas WHERE numero_tx=?", (dados["numero_tx"],)).fetchone()
    if row:
        nota_id = row[0]
        cursor.execute("DELETE FROM nota_impostos WHERE nota_id=?", (nota_id,))
        for imp in impostos:
            cursor.execute("INSERT INTO nota_impostos (nota_id, tipo, aliquota, valor, dt_venc_imp) VALUES (?,?,?,?,?)",
                           (nota_id, imp.get("tipo"), imp.get("aliquota",0), imp.get("valor"), imp.get("dt_venc_imp")))
        
        cursor.execute("DELETE FROM nota_parcelas WHERE nota_id=?", (nota_id,))
        for p in parcelas:
            cursor.execute("INSERT INTO nota_parcelas (nota_id, parcela, valor, dt_vencimento, status) VALUES (?,?,?,?,?)",
                           (nota_id, p.get("parcela", 1), p.get("valor"), p.get("vencimento", ""), p.get("status", "PENDENTE")))
                           
        cursor.execute("DELETE FROM nota_rateio WHERE nota_id=?", (nota_id,))
        for r in rateio:
            cursor.execute("INSERT INTO nota_rateio (nota_id, filial, percentual, valor) VALUES (?,?,?,?)",
                           (nota_id, r.get("centro_custo", ""), r.get("percentual", 100), r.get("valor", 0)))
                           
        cursor.execute("DELETE FROM nota_itens WHERE nota_id=?", (nota_id,))
        for it in itens:
            cursor.execute("INSERT INTO nota_itens (nota_id, descricao, valor_unitario, valor_total, quantidade) VALUES (?,?,?,?,?)",
                           (nota_id, it.get("descricao", ""), it.get("valor_unit", it.get("valor_total", 0)), it.get("valor_total", 0), it.get("qtd", 1)))
    conn.commit()
    conn.close()
    return dados["numero_tx"]

def listar_notas(status=None, empresa=None, busca=None):
    if USE_SUPABASE:
        try:
            query = supabase.table("notas").select("*")
            if status: query = query.eq("status", status)
            if empresa: query = query.eq("empresa", empresa)
            if busca: query = query.or_(f"fornecedor.ilike.%{busca}%,numero_tx.ilike.%{busca}%,numero_nf.ilike.%{busca}%,descricao.ilike.%{busca}%,categoria.ilike.%{busca}%,observacao.ilike.%{busca}%")
            res = query.order("dt_vencimento").execute()
            return res.data
        except Exception as e:
            logger.error(f"Erro Supabase (listar_notas): {e}")

    # Fallback SQLite
    conn = _get_local_conn()
    cursor = conn.cursor()
    sql  = "SELECT * FROM notas WHERE 1=1"
    args = []
    if status:  sql += " AND status=?";          args.append(status)
    if empresa: sql += " AND empresa=?";          args.append(empresa)
    if busca:
        sql += " AND (fornecedor LIKE ? OR numero_tx LIKE ? OR COALESCE(numero_nf,'') LIKE ? OR COALESCE(descricao,'') LIKE ? OR COALESCE(categoria,'') LIKE ? OR COALESCE(observacao,'') LIKE ?)"
        like = f"%{busca}%"
        args += [like, like, like, like, like, like]
    sql += " ORDER BY dt_vencimento ASC"
    cursor.execute(sql, args)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def listar_notas_com_parcelas(status=None, empresa=None, busca=None):
    if USE_SUPABASE:
        try:
            # Em Supabase real teríamos que fazer query de foreign key. Por simplicidade, faremos duas queries ou select embutido.
            query = supabase.table("notas").select("*, parcelas:nota_parcelas(*)")
            if status: query = query.eq("status", status)
            if empresa: query = query.eq("empresa", empresa)
            if busca: query = query.or_(f"fornecedor.ilike.%{busca}%,numero_tx.ilike.%{busca}%,numero_nf.ilike.%{busca}%,descricao.ilike.%{busca}%,categoria.ilike.%{busca}%,observacao.ilike.%{busca}%")
            res = query.order("dt_vencimento").execute()
            return res.data
        except Exception as e:
            logger.error(f"Erro Supabase (listar_notas_com_parcelas): {e}")

    # Fallback SQLite
    conn = _get_local_conn()
    cursor = conn.cursor()
    sql  = "SELECT * FROM notas WHERE 1=1"
    args = []
    if status:  sql += " AND status=?";          args.append(status)
    if empresa: sql += " AND empresa=?";          args.append(empresa)
    if busca:
        sql += " AND (fornecedor LIKE ? OR numero_tx LIKE ? OR COALESCE(numero_nf,'') LIKE ? OR COALESCE(descricao,'') LIKE ? OR COALESCE(categoria,'') LIKE ? OR COALESCE(observacao,'') LIKE ?)"
        like = f"%{busca}%"
        args += [like, like, like, like, like, like]
    sql += " ORDER BY dt_vencimento ASC"
    cursor.execute(sql, args)
    notas = [dict(r) for r in cursor.fetchall()]
    
    # Busca parcelas para as notas
    if notas:
        nota_ids = [n['id'] for n in notas]
        placeholders = ','.join(['?'] * len(nota_ids))
        cursor.execute(f"SELECT * FROM nota_parcelas WHERE nota_id IN ({placeholders}) ORDER BY parcela ASC", nota_ids)
        todas_parcelas = [dict(r) for r in cursor.fetchall()]
        
        # Agrupa
        for n in notas:
            n['parcelas'] = [p for p in todas_parcelas if p['nota_id'] == n['id']]
            # Se não tem parcela, simula uma parcela única com o total para não quebrar a UI
            if not n['parcelas']:
                n['parcelas'] = [{
                    'id': f"mock_{n['id']}",
                    'nota_id': n['id'],
                    'parcela': 1,
                    'dt_vencimento': n['dt_vencimento'],
                    'valor': n['valor_bruto'],
                    'status': n['status']
                }]
    
    conn.close()
    return notas

def get_nota_completa(nota_id):
    if USE_SUPABASE:
        try:
            res = supabase.table("notas").select("*").eq("id", nota_id).execute()
            if not res.data:
                return None
            nota = res.data[0]
            nota["impostos"] = supabase.table("nota_impostos").select("*").eq("nota_id", nota_id).execute().data
            nota["parcelas"] = supabase.table("nota_parcelas").select("*").eq("nota_id", nota_id).execute().data
            nota["rateio"] = supabase.table("nota_rateio").select("*").eq("nota_id", nota_id).execute().data
            nota["itens"] = supabase.table("nota_itens").select("*").eq("nota_id", nota_id).execute().data
            return nota
        except Exception as e:
            logger.error(f"Erro Supabase (get_nota_completa): {e}")

    conn = _get_local_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notas WHERE id=?", (nota_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    nota = dict(row)
    nota["impostos"] = [dict(r) for r in cursor.execute("SELECT * FROM nota_impostos WHERE nota_id=?", (nota_id,)).fetchall()]
    nota["parcelas"] = [dict(r) for r in cursor.execute("SELECT * FROM nota_parcelas WHERE nota_id=?", (nota_id,)).fetchall()]
    nota["rateio"] = [dict(r) for r in cursor.execute("SELECT * FROM nota_rateio WHERE nota_id=?", (nota_id,)).fetchall()]
    nota["itens"] = [dict(r) for r in cursor.execute("SELECT * FROM nota_itens WHERE nota_id=?", (nota_id,)).fetchall()]
    conn.close()
    return nota


def buscar_fornecedor_por_cnpj(cnpj):
    if USE_SUPABASE:
        try:
            res = supabase.table("fornecedores").select("*").eq("cnpj_cpf", cnpj).execute()
            return res.data[0] if res.data else None
        except: pass
    
    conn = _get_local_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fornecedores WHERE cnpj_cpf = ?", (cnpj,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def salvar_fornecedor(dados):
    if USE_SUPABASE:
        try:
            supabase.table("fornecedores").upsert(dados, on_conflict="cnpj_cpf").execute()
            return
        except: pass
    
    conn = _get_local_conn()
    cursor = conn.cursor()
    keys = dados.keys()
    vals = [dados[k] for k in keys]
    query = f"INSERT OR REPLACE INTO fornecedores ({','.join(keys)}) VALUES ({','.join(['?']*len(keys))})"
    cursor.execute(query, vals)
    conn.commit()
    conn.close()

# Mantém as funções originais para não quebrar a UI
def salvar_pagamentos_autorizados(lista):
    if not lista: return 0
    inseridos = 0
    for p in lista:
        if USE_SUPABASE:
            try:
                # Verifica duplicidade
                res = supabase.table("pagamentos_autorizados").select("id").match({
                    "nome": p["nome"], "valor": p["valor"], "data": p["data"], "empresa": p.get("empresa","LALUA")
                }).execute()
                if not res.data:
                    p["data_aprovacao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    supabase.table("pagamentos_autorizados").insert(p).execute()
                    inseridos += 1
                continue
            except: pass
        # Fallback opcional aqui...
    return inseridos

# Funções de inicialização
def db_init():
    """Cria as tabelas SQLite (se não existirem) e aplica migrations automáticas."""
    conn = _get_local_conn()
    cursor = conn.cursor()

    # ── Tabela principal de notas / contas a pagar ────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notas (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_tx        TEXT UNIQUE,
            numero_nf        TEXT DEFAULT '',
            fornecedor       TEXT DEFAULT '',
            cnpj             TEXT DEFAULT '',
            empresa          TEXT DEFAULT 'LALUA',
            filial           TEXT DEFAULT '',
            dt_emissao       TEXT DEFAULT '',
            dt_vencimento    TEXT DEFAULT '',
            dt_competencia   TEXT DEFAULT '',
            valor_bruto      REAL DEFAULT 0,
            valor_liquido    REAL DEFAULT 0,
            valor_desconto   REAL DEFAULT 0,
            valor_difal      REAL DEFAULT 0,
            categoria        TEXT DEFAULT '',
            responsavel      TEXT DEFAULT '',
            status           TEXT DEFAULT 'PENDENTE',
            observacao       TEXT DEFAULT '',
            arquivo_path     TEXT DEFAULT '',
            natureza         TEXT DEFAULT '',
            tipo_operacao    TEXT DEFAULT 'DESPESA',
            forma_pgto       TEXT DEFAULT '',
            banco_dest       TEXT DEFAULT '',
            agencia_dest     TEXT DEFAULT '',
            conta_dest       TEXT DEFAULT '',
            pix_chave        TEXT DEFAULT '',
            cpf_cnpj_dest    TEXT DEFAULT '',
            chave_ref        TEXT DEFAULT '',
            created_at       TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Impostos vinculados à nota ────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nota_impostos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_id     INTEGER NOT NULL REFERENCES notas(id) ON DELETE CASCADE,
            tipo        TEXT DEFAULT '',
            aliquota    REAL DEFAULT 0,
            valor       REAL DEFAULT 0,
            dt_venc_imp TEXT DEFAULT ''
        )
    """)

    # ── Parcelas da nota ──────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nota_parcelas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_id     INTEGER NOT NULL REFERENCES notas(id) ON DELETE CASCADE,
            parcela     INTEGER DEFAULT 1,
            dt_venc     TEXT DEFAULT '',
            valor       REAL DEFAULT 0,
            status      TEXT DEFAULT 'PENDENTE'
        )
    """)

    # ── Rateio de centro de custo ─────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nota_rateio (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_id     INTEGER NOT NULL REFERENCES notas(id) ON DELETE CASCADE,
            filial      TEXT DEFAULT '',
            percentual  REAL DEFAULT 100,
            valor       REAL DEFAULT 0
        )
    """)

    # ── Itens / produtos da nota ───────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nota_itens (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_id     INTEGER NOT NULL REFERENCES notas(id) ON DELETE CASCADE,
            descricao   TEXT DEFAULT '',
            ncm         TEXT DEFAULT '',
            cfop        TEXT DEFAULT '',
            quantidade  REAL DEFAULT 1,
            valor_unit  REAL DEFAULT 0,
            valor_total REAL DEFAULT 0
        )
    """)

    # ── Fornecedores / cadastro ───────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fornecedores (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj_cpf    TEXT UNIQUE,
            nome        TEXT DEFAULT '',
            fantasia    TEXT DEFAULT '',
            categoria   TEXT DEFAULT '',
            responsavel TEXT DEFAULT '',
            banco       TEXT DEFAULT '',
            agencia     TEXT DEFAULT '',
            conta       TEXT DEFAULT '',
            pix_chave   TEXT DEFAULT '',
            email       TEXT DEFAULT '',
            telefone    TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Pagamentos autorizados (histórico de autorização) ─────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos_autorizados (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            nome           TEXT DEFAULT '',
            cnpj           TEXT DEFAULT '',
            tipo           TEXT DEFAULT '',
            data           TEXT DEFAULT '',
            valor          REAL DEFAULT 0,
            status         TEXT DEFAULT 'AUTORIZADO',
            responsavel    TEXT DEFAULT '',
            categoria      TEXT DEFAULT '',
            empresa        TEXT DEFAULT 'LALUA',
            observacao     TEXT DEFAULT '',
            data_aprovacao TEXT DEFAULT '',
            anexo          TEXT DEFAULT ''
        )
    """)

    # ── Adiantamentos (Fase 5) ────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adiantamentos (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id          TEXT DEFAULT '',
            responsavel    TEXT DEFAULT '',
            empresa        TEXT DEFAULT '',
            valor          REAL DEFAULT 0,
            dt_adiantamento TEXT DEFAULT '',
            status         TEXT DEFAULT 'ABERTO',
            observacao     TEXT DEFAULT '',
            created_at     TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Orçamentos ────────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orcamentos (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria      TEXT DEFAULT '',
            mes            INTEGER DEFAULT 1,
            ano            INTEGER DEFAULT 2024,
            limite         REAL DEFAULT 0,
            alertado       INTEGER DEFAULT 0,
            created_at     TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Receitas (Importação CSV) ─────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receitas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            data           TEXT DEFAULT '',
            descricao      TEXT DEFAULT '',
            valor          REAL DEFAULT 0,
            fonte          TEXT DEFAULT 'CSV',
            arquivo_origem TEXT DEFAULT '',
            created_at     TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Guias GNRE ────────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gnre_guias (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_tx             TEXT UNIQUE,
            nota_ref_tx           TEXT DEFAULT '',
            uf_favorecida         TEXT DEFAULT 'PE',
            cnpj_emitente         TEXT DEFAULT '',
            codigo_receita        TEXT DEFAULT '100102',
            valor                 REAL DEFAULT 0,
            data_vencimento       TEXT DEFAULT '',
            documento_origem      TEXT DEFAULT '',
            tipo_documento_origem TEXT DEFAULT '10',
            chave_acesso_nfe      TEXT DEFAULT '',
            linha_digitavel       TEXT DEFAULT '',
            codigo_barras         TEXT DEFAULT '',
            numero_recibo         TEXT DEFAULT '',
            status                TEXT DEFAULT 'PENDENTE',
            motivo_rejeicao       TEXT DEFAULT '',
            xml_retorno           TEXT DEFAULT '',
            created_at            TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()

    # Tabela de lotes processados GNRE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gnre_lotes (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id               TEXT UNIQUE,
            data_hora             TEXT DEFAULT '',
            ambiente              TEXT DEFAULT 'homologacao',
            status                TEXT DEFAULT 'Pendente',
            recibos               TEXT DEFAULT '',
            xml_guias             TEXT DEFAULT '[]',
            cnab_filename         TEXT DEFAULT '',
            cnab_content          TEXT DEFAULT '',
            log_terminal          TEXT DEFAULT '',
            created_at            TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    # ── Migrations: adiciona colunas novas sem quebrar banco existente ─────────
    try:
        cursor.execute("ALTER TABLE notas ADD COLUMN pin TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE pagamentos_autorizados ADD COLUMN anexo TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    colunas_novas = [
        ("notas", "numero_nf",     "TEXT DEFAULT ''"),
        ("notas", "arquivo_path",  "TEXT DEFAULT ''"),
        ("notas", "natureza",      "TEXT DEFAULT ''"),
        ("notas", "tipo_operacao", "TEXT DEFAULT 'DESPESA'"),
        ("notas", "valor_difal",   "REAL DEFAULT 0"),
        ("notas", "forma_pgto",    "TEXT DEFAULT ''"),
        ("notas", "banco_dest",    "TEXT DEFAULT ''"),
        ("notas", "agencia_dest",  "TEXT DEFAULT ''"),
        ("notas", "conta_dest",    "TEXT DEFAULT ''"),
        ("notas", "pix_chave",     "TEXT DEFAULT ''"),
        ("notas", "cpf_cnpj_dest", "TEXT DEFAULT ''"),
        ("notas", "chave_ref",     "TEXT DEFAULT ''"),
        ("notas", "nivel_aprovacao", "INTEGER DEFAULT 1"),
        ("notas", "is_previsao", "INTEGER DEFAULT 0"),
        ("notas", "conciliada", "INTEGER DEFAULT 0"),
        ("notas", "filial", "TEXT DEFAULT ''"),
        ("notas", "dt_pagamento", "TEXT DEFAULT ''"),
    ]
    for tabela, col, tipo in colunas_novas:
        try:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {col} {tipo}")
            conn.commit()
        except Exception:
            pass  # Coluna já existe — ignorar

    conn.close()

def _db_init(conn): pass

# Exporta db_conn como alias
def get_db(): return db_conn()

def atualizar_status_nota(nota_id, status, data_pagamento=None):
    """Atualiza o status de uma nota no banco."""
    update_data = {"status": status}
    if data_pagamento:
        update_data["dt_pagamento"] = data_pagamento

    if USE_SUPABASE:
        try:
            supabase.table("notas").update(update_data).eq("id", nota_id).execute()
        except Exception as e:
            logger.error(f"Erro Supabase (atualizar_status_nota): {e}")

    conn = _get_local_conn()
    cursor = conn.cursor()
    if data_pagamento:
        cursor.execute("UPDATE notas SET status=?, dt_pagamento=? WHERE id=?", (status, data_pagamento, nota_id))
    else:
        cursor.execute("UPDATE notas SET status=? WHERE id=?", (status, nota_id))
    conn.commit()
    conn.close()

def baixar_parcela(parcela_id, valor_pago, data_pagamento):
    """Realiza a baixa (integral ou parcial) de uma parcela e atualiza o status da nota pai se necessário."""
    conn = _get_local_conn()
    cursor = conn.cursor()
    
    # Busca a parcela atual
    cursor.execute("SELECT * FROM nota_parcelas WHERE id=?", (parcela_id,))
    parcela_row = cursor.fetchone()
    if not parcela_row:
        conn.close()
        return False
        
    parcela = dict(parcela_row)
    valor_total = float(parcela.get("valor", 0))
    valor_pago = float(valor_pago)
    
    if valor_pago >= valor_total:
        # Baixa Integral
        cursor.execute("UPDATE nota_parcelas SET status='PAGO' WHERE id=?", (parcela_id,))
    else:
        # Baixa Parcial: Marca a atual como paga (com o valor pago) e cria uma nova para o saldo
        cursor.execute("UPDATE nota_parcelas SET status='PAGO', valor=? WHERE id=?", (valor_pago, parcela_id))
        saldo_remanescente = valor_total - valor_pago
        # Cria a parcela residual
        cursor.execute(
            "INSERT INTO nota_parcelas (nota_id, parcela, valor, dt_vencimento, status) VALUES (?,?,?,?,?)",
            (parcela["nota_id"], parcela["parcela"], saldo_remanescente, parcela["dt_vencimento"], "PENDENTE")
        )
        
    conn.commit()
    
    # Verifica se todas as parcelas da nota pai estão pagas
    nota_id = parcela["nota_id"]
    cursor.execute("SELECT status FROM nota_parcelas WHERE nota_id=?", (nota_id,))
    todas_parcelas = cursor.fetchall()
    
    todas_pagas = True
    for p in todas_parcelas:
        if p["status"] != "PAGO":
            todas_pagas = False
            break
            
    if todas_pagas:
        # Atualiza a nota pai para PAGO
        if data_pagamento:
            cursor.execute("UPDATE notas SET status='PAGO', dt_pagamento=? WHERE id=?", (data_pagamento, nota_id))
        else:
            cursor.execute("UPDATE notas SET status='PAGO' WHERE id=?", (nota_id,))
    
    conn.commit()
    conn.close()
    
    # Supabase (ignorado para simplificar, se fôssemos usar faríamos a mesma lógica via API Supabase)
    return True


def salvar_adiantamento(dados):
    if USE_SUPABASE:
        try:
            res = supabase.table("adiantamentos").insert(dados).execute()
            if res.data:
                return res.data[0].get("id")
        except Exception as e:
            logger.error(f"Erro Supabase (adiantamento): {e}")
            
    conn = _get_local_conn()
    cur = conn.cursor()
    colunas = ", ".join(dados.keys())
    valores = ", ".join(["?"] * len(dados))
    cur.execute(f"INSERT INTO adiantamentos ({colunas}) VALUES ({valores})", list(dados.values()))
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id

def listar_adiantamentos(status=None, empresa=None, busca=None):
    if USE_SUPABASE:
        try:
            q = supabase.table("adiantamentos").select("*")
            if status: q = q.eq("status", status)
            if empresa: q = q.eq("empresa", empresa)
            if busca: q = q.ilike("responsavel", f"%{busca}%")
            return q.execute().data
        except Exception as e:
            logger.error(f"Erro Supabase (listar adiantamentos): {e}")
            return []

    conn = _get_local_conn()
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM adiantamentos WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    if empresa:
        query += " AND empresa = ?"
        params.append(empresa)
    if busca:
        query += " AND responsavel LIKE ?"
        params.append(f"%{busca}%")
        
    query += " ORDER BY id DESC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def listar_fornecedores(busca=None, ativo_only=False):
    if USE_SUPABASE:
        try:
            q = supabase.table("fornecedores").select("*")
            if busca: q = q.ilike("nome", f"%{busca}%")
            return q.execute().data
        except Exception as e:
            logger.error(f"Erro Supabase (listar fornecedores): {e}")
            return []

    conn = _get_local_conn()
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM fornecedores"
    params = []
    
    if busca:
        query += " WHERE nome LIKE ? OR cnpj_cpf LIKE ?"
        params.extend([f"%{busca}%", f"%{busca}%"])
        
    query += " ORDER BY nome ASC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# == AUDIT TRAIL ==============================================================

def _garantir_tabela_auditoria():
    try:
        conn = _get_local_conn()
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario     TEXT DEFAULT '',
                acao        TEXT DEFAULT '',
                entidade    TEXT DEFAULT '',
                entidade_id TEXT DEFAULT '',
                descricao   TEXT DEFAULT '',
                valor       REAL DEFAULT 0,
                ip          TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now'))
            )"""
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f'Erro ao criar tabela audit_log: {e}')

_garantir_tabela_auditoria()


def registrar_auditoria(usuario, acao, entidade, entidade_id='', descricao='', valor=0, ip=''):
    """Registra uma acao no audit trail do ERP."""
    try:
        conn = _get_local_conn()
        conn.execute(
            'INSERT INTO audit_log (usuario, acao, entidade, entidade_id, descricao, valor, ip) VALUES (?,?,?,?,?,?,?)',
            (usuario, acao.upper(), entidade, str(entidade_id), descricao, float(valor), ip)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f'Erro ao registrar auditoria: {e}')


def listar_auditoria(usuario=None, acao=None, entidade=None, limite=100):
    """Retorna registros do audit trail com filtros opcionais."""
    try:
        conn = _get_local_conn()
        sql = 'SELECT * FROM audit_log WHERE 1=1'
        args = []
        if usuario:
            sql += ' AND usuario LIKE ?'
            args.append(f'%{usuario}%')
        if acao:
            sql += ' AND acao = ?'
            args.append(acao.upper())
        if entidade:
            sql += ' AND entidade = ?'
            args.append(entidade)
        sql += f' ORDER BY id DESC LIMIT {min(limite, 500)}'
        rows = conn.execute(sql, args).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f'Erro ao listar auditoria: {e}')
        return []


# ── MÓDULO GNRE ───────────────────────────────────────────────────────────────

def listar_gnre_guias(status=None, busca=None):
    if USE_SUPABASE:
        try:
            query = supabase.table("gnre_guias").select("*")
            if status: query = query.eq("status", status)
            if busca: query = query.or_(f"numero_tx.ilike.%{busca}%,documento_origem.ilike.%{busca}%,cnpj_emitente.ilike.%{busca}%")
            res = query.order("created_at", desc=True).execute()
            return res.data
        except Exception as e:
            logger.error(f"Erro Supabase (listar_gnre_guias): {e}")

    # Fallback SQLite
    conn = _get_local_conn()
    cursor = conn.cursor()
    sql = "SELECT * FROM gnre_guias WHERE 1=1"
    args = []
    if status:
        sql += " AND status=?"
        args.append(status)
    if busca:
        sql += " AND (numero_tx LIKE ? OR documento_origem LIKE ? OR cnpj_emitente LIKE ?)"
        like = f"%{busca}%"
        args += [like, like, like]
    sql += " ORDER BY created_at DESC"
    cursor.execute(sql, args)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def salvar_gnre_guia(dados):
    if not dados.get("numero_tx"):
        import time
        dados["numero_tx"] = f"GNRE{int(time.time()*1000)}"

    if USE_SUPABASE:
        try:
            res = supabase.table("gnre_guias").upsert(dados, on_conflict="numero_tx").execute()
            if res.data:
                return res.data[0]["numero_tx"]
        except Exception as e:
            logger.error(f"Erro Supabase (salvar_gnre_guia): {e}")

    # Fallback SQLite
    conn = _get_local_conn()
    cursor = conn.cursor()
    keys = dados.keys()
    vals = [dados[k] for k in keys]
    query = f"INSERT OR REPLACE INTO gnre_guias ({','.join(keys)}) VALUES ({','.join(['?']*len(keys))})"
    cursor.execute(query, vals)
    conn.commit()
    conn.close()
    return dados["numero_tx"]

def atualizar_status_gnre_guia(numero_tx, status, extras=None):
    update_data = {"status": status}
    if extras:
        update_data.update(extras)

    if USE_SUPABASE:
        try:
            supabase.table("gnre_guias").update(update_data).eq("numero_tx", numero_tx).execute()
        except Exception as e:
            logger.error(f"Erro Supabase (atualizar_status_gnre_guia): {e}")

    conn = _get_local_conn()
    cursor = conn.cursor()
    # Constrói o SET dinamicamente para SQLite
    set_clause = ", ".join([f"{k}=?" for k in update_data.keys()])
    vals = list(update_data.values()) + [numero_tx]
    cursor.execute(f"UPDATE gnre_guias SET {set_clause} WHERE numero_tx=?", vals)
    conn.commit()
    conn.close()

def listar_gnre_lotes():
    if USE_SUPABASE:
        try:
            res = supabase.table("gnre_lotes").select("*").order("created_at", desc=True).execute()
            return res.data
        except Exception as e:
            logger.error(f"Erro Supabase (listar_gnre_lotes): {e}")

    # Fallback SQLite
    conn = _get_local_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gnre_lotes ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def salvar_gnre_lote(dados):
    if not dados.get("lote_id"):
        import time
        dados["lote_id"] = f"LOTE{int(time.time()*1000)}"

    if USE_SUPABASE:
        try:
            res = supabase.table("gnre_lotes").upsert(dados, on_conflict="lote_id").execute()
            if res.data:
                return res.data[0]["lote_id"]
        except Exception as e:
            logger.error(f"Erro Supabase (salvar_gnre_lote): {e}")

    # Fallback SQLite
    conn = _get_local_conn()
    cursor = conn.cursor()
    keys = dados.keys()
    vals = [dados[k] for k in keys]
    query = f"INSERT OR REPLACE INTO gnre_lotes ({','.join(keys)}) VALUES ({','.join(['?']*len(keys))})"
    cursor.execute(query, vals)
    conn.commit()
    conn.close()
    return dados["lote_id"]

def get_gnre_lote(lote_id):
    if USE_SUPABASE:
        try:
            res = supabase.table("gnre_lotes").select("*").eq("lote_id", lote_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Erro Supabase (get_gnre_lote): {e}")

    # Fallback SQLite
    conn = _get_local_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gnre_lotes WHERE lote_id=?", (lote_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
