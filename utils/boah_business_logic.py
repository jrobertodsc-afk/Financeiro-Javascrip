import os
import re
from datetime import datetime
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    POPPLER_PATH = r'C:\poppler\poppler-25.12.0\Library\bin'
    OCR_DISPONIVEL = True
except ImportError:
    OCR_DISPONIVEL = False

# Dicionários de Classificação
DE_PARA_FILIAL = {
    "Filial_Barra": "Boah - Barra", "Filial_Horto": "Boah - Horto",
    "Matriz": "Boah - Matriz", "Filial_Paseo": "Boah - Paseo",
    "Filial_SDB": "Boah - SDB", "Filial_Vilas": "Boah - Vilas",
    "Empresa_Solar": "Solar - Geral", "Geral": "A Classificar"
}

DB_COLABORADORES = {
    "CINDIA SANTOS SILVA": "Filial_Barra", "ELLEN KAYANNE VITOR DA SILVA": "Filial_SDB",
    "GEISA SACRAMENTO MARQUES": "Filial_Barra", "GILMARIA DOS SANTOS RIBEIRO": "Filial_Paseo",
    "ALEX FERREIRA": "Matriz", "AMARILDO FERREIRA": "Matriz",
    # Adicionar os demais colaboradores aos poucos depois ou puxar do banco
}

DB_FORNECEDORES_CATEGORIA = {
    "38.462.298/0001-24": ("ADM/FINANCEIRO", "12202 - Salários - Meis/PJ"),
    "03.165.536/0001-55": ("COMPRAS", "21707 - Material Gráfico"),
    # Outros mapeamentos...
}

DB_FORNECEDORES_NOME = {
    "LINX SIST": ("ADM/FINANCEIRO", "21120 - Sistemas e Softwares"),
    "CONSORCIO NACIGUAT": ("ADM/FINANCEIRO", "21101 - Aluguel"),
    "COELB": ("ADM/FINANCEIRO", "21104 - Energia Eletrica"),
    "EMBASA": ("ADM/FINANCEIRO", "21103 - Agua E Esgotos"),
    # Outros mapeamentos
}

VALORES_DOMINGO = [33.75, 32.20, 65.95, 68.00]

def auto_classificar(nome, cnpj=""):
    """Classifica pelo CNPJ (preciso) ou nome parcial (fallback)."""
    cnpj_limpo = cnpj.strip()
    if cnpj_limpo and cnpj_limpo != "-" and cnpj_limpo in DB_FORNECEDORES_CATEGORIA:
        return DB_FORNECEDORES_CATEGORIA[cnpj_limpo]
        
    nome_up = nome.upper()
    for chave, (resp, cat) in DB_FORNECEDORES_NOME.items():
        if chave.upper() in nome_up:
            return resp, cat
            
    if any(x in nome_up for x in ["TEXTIL","TECIDO","FIDC","FIOS","LINHAS","AVIAMENTO"]):
        return "COMPRAS", "12101 - Tecidos"
    if any(x in nome_up for x in ["TELEFON","TELECOM","INTERNET","TIM ","CLARO","VIVO"]):
        return "ADM/FINANCEIRO", "21114 - Telefonia Fixa/Internet"
    if any(x in nome_up for x in ["CONDOMIN","SHOPPING","ALUGUEL"]):
        return "ADM/FINANCEIRO", "21102 - Condominio"
    if any(x in nome_up for x in ["ENERGIA","ELETRIC","COELBA","EMBASA"]):
        return "ADM/FINANCEIRO", "21104 - Energia Eletrica"
    if any(x in nome_up for x in ["SEFAZ","RECEITA","TRIBUT","ICMS","DARF","DAE","GNRE","SIMPLES"]):
        return "ADM/FINANCEIRO", "22309 - GNRE"
    if any(x in nome_up for x in ["CAIXA ECONOMICA","CEF "]):
        return "ADM/FINANCEIRO", "12207 - Rescisão / FGTS"
    if any(x in nome_up for x in ["FACCIONISTA","MAO DE OBRA","COSTURA"]):
        return "PRODUCAO", "12111 - Faccionista - Mão de Obra"
    if any(x in nome_up for x in ["FRETE","TRANSPORTE","COURIER","LOG "]):
        return "COMPRAS", "12112 - Frete/Transporte - Produção"
        
    return "", "A CLASSIFICAR"

def definir_filial(nome):
    nome_upper = nome.upper()
    for nome_db, filial in DB_COLABORADORES.items():
        if nome_db in nome_upper: return filial
    return "Geral"

def eh_comprovante_bancario(texto):
    texto_up = texto.upper()
    marcas = [
        "COMPROVANTE DE", "TRANSFERÊNCIA EFETUADA", "PAGAMENTO EFETUADO",
        "SISPAG", "VIA SISPAG", "AUTENTICAÇÃO", "AUTENTICAÇÃO DO COMPROVANTE",
        "BANCO ITAÚ", "ITAÚ EMPRESAS", "ID DA TRANSAÇÃO", "PIX QR CODE",
    ]
    return sum(1 for m in marcas if m in texto_up) >= 2

def extrair_dados_expert(texto):
    dados = {"data": None, "nome": "Desconhecido", "valor": 0.0, "empresa": "LALUA", "filial": "Geral", "colaborador_ok": False}
    
    # 1. Data
    data_encontrada = None
    for padrao in [
        r'data (?:do pagamento|de pagamento|da transfer[eê]ncia|do vencimento):\s*(\d{2}/\d{2}/\d{4})',
        r'(?:Pagamento|Opera[çc][ãa]o|transa[çc][ãa]o) efetuad[ao] em (\d{2}/\d{2}/\d{4})',
        r'(\d{2}/\d{2}/\d{4})',
    ]:
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            try:
                dt = datetime.strptime(m.group(1), "%d/%m/%Y")
                if 2010 <= dt.year <= 2030:
                    data_encontrada = dt
                    break
            except:
                pass
    dados["data"] = data_encontrada
    
    # 2. Valor
    nums = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', texto)
    lista_valores = []
    for n in nums:
        try:
            v = float(n.replace('.', '').replace(',', '.'))
            if 0 < v < 1000000: lista_valores.append(v)
        except: pass
    if lista_valores: dados["valor"] = max(lista_valores)
    
    # 3. Nome
    nome_encontrado = None
    if not nome_encontrado and "Comprovante de Pagamento de concessionárias" in texto:
        match_conc = re.search(r'Benefici[aá]rio:\s*([^\n\r]+?)(?:\s+CPF|\s+CNPJ|\s+\d|$)', texto, re.IGNORECASE)
        if match_conc:
            nome_encontrado = match_conc.group(1).strip()
            
    if not nome_encontrado:
        match_sispag = re.search(r'Nome:\s*([^\n\r]+)', texto, re.IGNORECASE)
        if match_sispag: nome_encontrado = match_sispag.group(1).strip()
        
    if nome_encontrado:
        dados["nome"] = nome_encontrado
        
    # 4. Empresa e Filial
    if "SOLAR" in texto.upper():
        dados["empresa"] = "SOLAR"
        
    dados["filial"] = definir_filial(dados["nome"])
    dados["colaborador_ok"] = (dados["filial"] != "Geral")
    
    # Adicionar classificação usando auto_classificar
    resp, cat = auto_classificar(dados["nome"])
    dados["responsavel"] = resp
    dados["categoria"] = cat
    
    return dados
