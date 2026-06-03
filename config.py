"""
config.py — Configurações e constantes globais do Robô Financeiro BOAH/SOLAR.
"""
import os
import json
from dotenv import load_dotenv
from services.logger_service import logger

# --- FLAGS DE BIBLIOTECAS ---
try:
    import openpyxl
    import xlrd
    EXCEL_OK = True
except ImportError:
    EXCEL_OK = False

try:
    import fitz  # PyMuPDF
    PDF_OK = True
except ImportError:
    PDF_OK = False

# ==============================================================================
# ── PASTAS PRINCIPAIS ──────────────────────────────────────────────────────────
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
load_dotenv(os.path.join(BASE_DIR, ".env"))

DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
PASTA_ATUAL = os.path.join(DESKTOP_PATH, "FINANCEIRO")
PASTA_ENTRADA = os.path.join(PASTA_ATUAL, "ENTRADA")
PASTA_SAIDA = os.path.join(PASTA_ATUAL, "SAIDA_ORGANIZADA")
PASTA_EXTRATOS = os.path.join(PASTA_ATUAL, "EXTRATOS")
PASTA_BACKUP_EXTRATOS = os.path.join(PASTA_ATUAL, "BACKUP_EXTRATOS")
PASTA_LOGS = os.path.join(PASTA_ATUAL, "LOGS")
PASTA_RESTITUICOES = os.path.join(PASTA_ATUAL, "RESTITUICOES")
PASTA_RESTITUICOES_XML = os.path.join(PASTA_RESTITUICOES, "XML_NOTAS")
PASTA_RESTITUICOES_PDF = os.path.join(PASTA_RESTITUICOES, "PDF_GUIAS")
PASTA_BIBLIOTECA_GNRE  = os.path.join(PASTA_RESTITUICOES, "BIBLIOTECA_GNRE")
PASTA_MODELOS_GNRE     = os.path.join(DESKTOP_PATH, "MODELOS_GNRE")
PASTA_SERVIDOR = r"Y:\01-Administrativo\02-Financeiro\04-Comprovantes"
PASTA_BACKUP_PDF = os.path.join(PASTA_ATUAL, "BACKUP_COMPROVANTES")
PASTA_INPUT_SMART = os.path.join(PASTA_ATUAL, "IMPORTACAO_AUTOMATICA")
PASTA_DOSSIES     = os.path.join(PASTA_RESTITUICOES, "DOSSIES_FINAIS")

LOG_RETENCAO_DIAS = 30
DB_PATH = os.path.join(BASE_DIR, "robo_boah.db")

def ensure_directories():
    for _p in (PASTA_ATUAL, PASTA_ENTRADA, PASTA_SAIDA,
               PASTA_EXTRATOS, PASTA_BACKUP_EXTRATOS,
               PASTA_LOGS, PASTA_BACKUP_PDF,
               PASTA_RESTITUICOES, PASTA_RESTITUICOES_XML, 
               PASTA_RESTITUICOES_PDF, PASTA_BIBLIOTECA_GNRE,
               PASTA_MODELOS_GNRE, PASTA_INPUT_SMART, PASTA_DOSSIES):
        try:
            os.makedirs(_p, exist_ok=True)
        except Exception as e:
            logger.error(f"Erro ao criar pasta {_p}: {e}")

# ==============================================================================
# ── CARREGAMENTO DE DADOS (JSON) ──────────────────────────────────────────────
# ==============================================================================
def load_json(filename, default=None):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}

DB_COLABORADORES = load_json('colaboradores.json')
DB_FORNECEDORES_FIXOS = load_json('fornecedores_fixos.json')
DB_FORNECEDORES_CATEGORIA = {k: tuple(v) if isinstance(v, list) else v for k, v in load_json('fornecedores_categoria.json').items()}
DB_FORNECEDORES_NOME = {k: tuple(v) if isinstance(v, list) else v for k, v in load_json('fornecedores_nome.json').items()}
CATEGORIAS_LISTA = load_json('categorias_lista.json', [])
CATEGORIAS_DP = load_json('categorias_dp.json', [])
DE_PARA_FILIAL_MAP = load_json('de_para_filial_map.json')
RESPONSAVEIS_LISTA = load_json('responsaveis_lista.json', [])

# ==============================================================================
# ── PARÂMETROS FINANCEIROS MENORES ────────────────────────────────────────────
# ==============================================================================
VALORES_DOMINGO = [33.75, 32.20, 65.95, 68.00]
MESES = {
    1:"01_Janeiro", 2:"02_Fevereiro", 3:"03_Marco", 4:"04_Abril",
    5:"05_Maio", 6:"06_Junho", 7:"07_Julho", 8:"08_Agosto",
    9:"09_Setembro", 10:"10_Outubro", 11:"11_Novembro", 12:"12_Dezembro"
}
TIPOS_IMPOSTO = ["PIS", "COFINS", "IRRF", "INSS retido", "ISS", "CSLL"]
STATUS_NOTA = ["PENDENTE", "APROVADA", "PAGA", "VENCIDA", "CANCELADA"]
ALIQUOTAS_PADRAO = {
    "PIS": 0.65, "COFINS": 3.0, "IRRF": 1.5, "INSS retido": 11.0, "ISS": 5.0,
}
CNAB_CONTAS = {
    "ITAÚ": {"agencia": "0000", "conta": "00000-0"},
    "SANTANDER": {"agencia": "1111", "conta": "11111-1"},
}
FILIAIS_RATEIO = ["LALUA MATRIZ", "LALUA FILIAL 1", "LALUA FILIAL 2", "SOLAR MATRIZ"]
DE_PARA_FILIAL = {
    "LALUA": "LALUA MATRIZ",
    "SOLAR": "SOLAR MATRIZ",
}

# ==============================================================================
# ── CREDENCIAIS (via .env) ────────────────────────────────────────────────────
# ==============================================================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

EMAIL_DESTINO_DP = os.getenv("EMAIL_DESTINO_DP", "")
EMAIL_DESTINO_EXTRATO = os.getenv("EMAIL_DESTINO_EXTRATO", "")
EMAIL_DESTINO_CONTAB = os.getenv("EMAIL_DESTINO_CONTAB", "")
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "")
EMAIL_SENHA = os.getenv("EMAIL_SENHA", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))

PAGARME_API_URL = "https://api.pagar.me/1"
PAGARME_API_KEY = os.getenv("PAGARME_API_KEY", "")

REDE_API_URL = "https://api.userede.com.br"
REDE_CLIENT_ID = os.getenv("REDE_CLIENT_ID", "")
REDE_CLIENT_SECRET = os.getenv("REDE_CLIENT_SECRET", "")
REDE_PV = os.getenv("REDE_PV", "")

GETNET_API_URL = "https://api.getnet.com.br"
GETNET_CLIENT_ID = os.getenv("GETNET_CLIENT_ID", "")
GETNET_CLIENT_SECRET = os.getenv("GETNET_CLIENT_SECRET", "")
GETNET_SELLER_ID = os.getenv("GETNET_SELLER_ID", "")

MICROVIX_API_URL = "https://api.microvix.com.br"
MICROVIX_USUARIO = os.getenv("MICROVIX_USUARIO", "")
MICROVIX_SENHA   = os.getenv("MICROVIX_SENHA", "")
MICROVIX_CNPJ    = os.getenv("MICROVIX_CNPJ", "")
MICROVIX_CHAVE   = os.getenv("MICROVIX_CHAVE", "")
