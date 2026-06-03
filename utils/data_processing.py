import re
from datetime import datetime

__all__ = ['_parse_valor', '_aplicar_mascara_valor', 'calcular_periodo_sugerido', 'auto_classificar', 'extrair_info_comprovante']

def _parse_valor(texto):
    """Converte string '1.234,56' ou '1234.56' em float."""
    if not texto: return 0.0
    # Remove R$, espaços e converte formato brasileiro
    limpo = texto.replace("R$", "").replace(" ", "")
    if "," in limpo and "." in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif "," in limpo:
        limpo = limpo.replace(",", ".")
    try:
        return float(limpo)
    except:
        return 0.0

def _aplicar_mascara_valor(entry):
    """Aplica máscara de valor monetário em tempo real a um tk.Entry."""
    def formatar(event):
        if event.keysym in ("BackSpace", "Delete", "Left", "Right"): return
        texto = entry.get().replace(",", "").replace(".", "").replace("R$", "").strip()
        if not texto: return
        try:
            val = float(texto) / 100
            entry.delete(0, "end")
            entry.insert(0, f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        except: pass
    entry.bind("<KeyRelease>", formatar)

def calcular_periodo_sugerido():
    """Sugere o período de ontem ou do mês atual."""
    hoje = datetime.now()
    ontem = hoje
    # Se for segunda, sugere sexta a domingo? Não, simplificar:
    return hoje, hoje, "Hoje"

def auto_classificar(nome_fornecedor, valor=0.0, cnpj=""):
    """
    Inteligência de classificação baseada na base de dados real do ERP.
    Prioridade: 1. CNPJ exato | 2. Nome do Colaborador | 3. Nome do Fornecedor | 4. Regras Genéricas
    """
    from config import (DB_FORNECEDORES_CATEGORIA, DB_FORNECEDORES_NOME, 
                        DB_COLABORADORES, DB_FORNECEDORES_FIXOS)
    
    nome = nome_fornecedor.upper().strip()
    cnpj_clean = cnpj.strip()

    # 0. Busca na Memória Aprendida (categorias_aprendidas.json)
    import json
    import os
    try:
        mem_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "categorias_aprendidas.json")
        if os.path.exists(mem_path):
            with open(mem_path, "r", encoding="utf-8") as f:
                mem_data = json.load(f)
                
            if cnpj_clean and cnpj_clean in mem_data.get("cnpj_mappings", {}):
                m = mem_data["cnpj_mappings"][cnpj_clean]
                return m.get("responsavel", "ADM/FINANCEIRO"), m.get("categoria", "A CLASSIFICAR"), m.get("observacao", "")
                
            if nome in mem_data.get("nome_mappings", {}):
                m = mem_data["nome_mappings"][nome]
                return m.get("responsavel", "ADM/FINANCEIRO"), m.get("categoria", "A CLASSIFICAR"), m.get("observacao", "")
    except Exception as e:
        pass

    # 1. Busca por CNPJ exato na base de 266 fornecedores
    if cnpj_clean in DB_FORNECEDORES_CATEGORIA:
        vals = DB_FORNECEDORES_CATEGORIA[cnpj_clean]
        r = vals[0] if len(vals) > 0 else "ADM/FINANCEIRO"
        c = vals[1] if len(vals) > 1 else "A CLASSIFICAR"
        desc = vals[2] if len(vals) > 2 else ""
        # Regra especial: GNRE sempre GERENTE ONLINE
        if "GNRE" in c.upper():
            return "GERENTE ONLINE", c, desc
        return r, c, desc

    # 2. Busca por Nome do Colaborador (RH)
    if nome in DB_COLABORADORES:
        return "RH", "12201 - Salários", ""

    # 3. Regra especial por nome (GNRE)
    if "GNRE" in nome:
        return "GERENTE ONLINE", "22309 - GNRE", ""

    # 4. Busca por Nome do Fornecedor (Base DB_FORNECEDORES_NOME)
    for chave_nome, vals in DB_FORNECEDORES_NOME.items():
        if chave_nome.upper() in nome:
            r = vals[0] if len(vals) > 0 else "ADM/FINANCEIRO"
            c = vals[1] if len(vals) > 1 else "A CLASSIFICAR"
            desc = vals[2] if len(vals) > 2 else ""
            return r, c, desc

    # 4. Regras Genéricas de Categoria (Fallback)
    if any(x in nome for x in ["FGTS", "GRRF"]):
        return "RH", "12205 - FGTS", ""
    if any(x in nome for x in ["INSS", "IRRF", "DARF", "GPS", "SIMPLES NACIONAL", "DAS", "PIS", "COFINS"]):
        return "ADM/FINANCEIRO", "22308 - Simples Nacional", ""
    if any(x in nome for x in ["SALARIO", "FOLHA", "PROVENTO", "FERIAS", "RESCISAO"]):
        return "RH", "12201 - Salários", ""
    if any(x in nome for x in ["ALUGUEL", "CONDOMINIO"]):
        return "ADM/FINANCEIRO", "21101 - Aluguel", ""
    if any(x in nome for x in ["ENERGIA", "COELBA", "AGUA", "EMBASA", "TELEFONE", "INTERNET"]):
        return "ADM/FINANCEIRO", "21104 - Energia Eletrica", ""
    if any(x in nome for x in ["MARKETING", "FACEBOOK", "GOOGLE", "ADS", "INSTAGRAM"]):
        return "MARKETING", "21701 - Comunicação/Mídia Digital", ""
    if any(x in nome for x in ["TRANSF", "PIX FILIAL", "MATRIZ"]):
        return "ADM/FINANCEIRO", "TRANSFERENCIA", ""
    if any(x in nome for x in ["FRETE", "LOGISTICA", "TRANSPORTE"]):
        return "LOGISTICA", "12112 - Frete/Transporte - Produção", ""

    # Fornecedores (fallback por valor)
    if valor > 500:
        return "ADM/FINANCEIRO", "12104 - Produtos Para Revenda", ""

    return "ADM/FINANCEIRO", "A CLASSIFICAR", ""

def extrair_info_comprovante(texto):
    """
    Analisa o texto extraído de um PDF para identificar dados do comprovante.
    Suporta Itaú e layouts genéricos de tributos/pagamentos.
    """
    info = {
        "empresa": "A Classificar",
        "categoria": "A CLASSIFICAR",
        "tipo": "COMPROVANTE",
        "data": None,
        "valor": 0.0,
        "favorecido": "",
        "detalhes": ""
    }
    
    if not texto: return info
    
    # Normalização básica para lidar com espaços extras entre letras
    # Ex: "L A L U A" -> "LALUA"
    texto_limpo = " ".join(texto.split())
    texto_upper = texto_limpo.upper()
    
    # 1. Identificar Empresa (Mais flexível + Conta Bancária)
    # LALUA: 0334/98775-7
    if any(x in texto_upper for x in ["LALUA", "L A L U A", "COMERCIO DE MODAS", "98775-7", "98775"]):
        info["empresa"] = "LALUA"
    elif any(x in texto_upper for x in ["SOLAR", "S O L A R"]):
        info["empresa"] = "SOLAR"
    elif any(x in texto_upper for x in ["BOAH", "B O A H"]):
        info["empresa"] = "BOAH"
    
    # Se não achou pelos nomes, tenta por CNPJ da LALUA (10.436.619/0001-05)
    if info["empresa"] == "A Classificar":
        if "10.436.619" in texto_upper or "10436619" in texto_upper:
            info["empresa"] = "LALUA"

    # 2. Identificar Valor
    # Regex mais abrangente para capturar valores em diferentes formatos
    match_valor = re.search(r"(?:Valor|pagamento|Total|valor de).*?R\$\s*([\d\.,]+)", texto_limpo, re.IGNORECASE)
    if match_valor:
        val_str = match_valor.group(1).replace(".", "").replace(",", ".")
        try:
            info["valor"] = float(val_str)
        except: pass

    # 3. Identificar Data
    match_data = re.search(r"(?:pagamento|Data|efetuada|em|Vencimento)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", texto_limpo, re.IGNORECASE)
    if not match_data:
        match_data = re.search(r"(\d{2}/\d{2}/\d{4})", texto_limpo)
    if match_data:
        info["data"] = match_data.group(1)

    # 4. Identificar Tipo / Categoria / Detalhes
    if any(x in texto_upper for x in ["TRIBUTOS MUNICIPAIS", "PM SALVADOR", "PREFEITURA"]):
        info["tipo"] = "TRIBUTO_MUNICIPAL"
        info["categoria"] = "21902 - Taxas Municipais"
        m_mun = re.search(r"(?:munic.pio|Cidade|Prefeitura)\s*[:\-]?\s*([A-Z\s]+?)(?:\r?\n|$|dados)", texto_limpo, re.IGNORECASE)
        if m_mun: info["detalhes"] = m_mun.group(1).strip()
    
    elif any(x in texto_upper for x in ["GNRE", "GUIA NACIONAL", "RECOLHIMENTO ESTADUAL"]):
        info["tipo"] = "GNRE"
        info["categoria"] = "22309 - GNRE"
        m_uf = re.search(r"UF\s*[:\-]?\s*([A-Z]{2})", texto_upper)
        if m_uf: info["detalhes"] = m_uf.group(1)

    elif any(x in texto_upper for x in ["DARF", "RECEITA FEDERAL", "SIMPLES NACIONAL"]):
        info["tipo"] = "DARF"
        info["categoria"] = "22308 - Simples Nacional"
    
    elif any(x in texto_upper for x in ["GPS", "INSS", "PREVIDENCIA"]):
        info["tipo"] = "GPS"
        info["categoria"] = "12205 - INSS"

    elif any(x in texto_upper for x in ["FGTS", "CAIXA ECONOMICA"]):
        info["tipo"] = "FGTS"
        info["categoria"] = "12205 - FGTS"

    elif any(x in texto_upper for x in ["TRANSFERENCIA", "PIX", "TED", "DOC", "SISPAG", "PAGAMENTO EFETUADO"]):
        info["tipo"] = "TRANSFERENCIA"
        info["categoria"] = "TRANSFERENCIA"
        
        # Lógica Expert para identificar Fornecedor/Beneficiário
        nome_encontrado = None
        # Tenta padrões específicos de recebedor primeiro
        # Ajustado para não capturar o resto da linha (limite de 60 chars e para em números/CNPJ)
        match_receb = re.search(r'(?:nome do recebedor|Benefici[aá]rio|favorecido|raz[aã]o social|razo social)\s*[:\-]?\s*([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][^0-9\n\r]{2,60})', texto_limpo, re.IGNORECASE)
        if match_receb:
            nome_encontrado = match_receb.group(1).strip()
        else:
            # Fallback para "nome", mas pula se for o nome da própria empresa (Lalua/Solar/Boah)
            matches_nome = re.finditer(r'\bnome\s*[:\-]?\s*([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][^0-9\n\r]{2,60})', texto_limpo, re.IGNORECASE)
            for m in matches_nome:
                candidato = m.group(1).strip().upper()
                if not any(x in candidato for x in ["LALUA", "SOLAR", "BOAH", "COMERCIO DE MODAS"]):
                    nome_encontrado = candidato
                    break
        
        if nome_encontrado:
            # Limpeza final (remove rótulos residuais)
            nome_limpo = nome_encontrado.upper()
            nome_limpo = re.sub(r'^(?:NOME|VALOR|DATA|RAZ[AÃ]O SOCIAL|RAZO SOCIAL)\b\s*[:\-]?\s*', '', nome_limpo).strip()
            # Remove labels que podem ter sido capturadas no final do nome
            nome_limpo = re.split(r'\b(?:CPF|CNPJ|DATA|VALOR|AGENCIA|CONTA|R\$)\b', nome_limpo, flags=re.I)[0].strip()
            # Remove traços ou espaços residuais no final
            nome_limpo = re.sub(r'[\s\-_:]+$', '', nome_limpo).strip()
            
            info["favorecido"] = nome_limpo
            info["detalhes"] = nome_limpo

    return info

class DetectorDuplicidade:
    """
    Motor de Anti-Duplicidade Semântica (IA/Fuzzy Matching).
    Detecta anomalias cruzando valor exato, proximidade de datas e
    similaridade léxica (fuzzy) no nome do fornecedor/favorecido.
    """
    
    @staticmethod
    def _calcular_similaridade(str1: str, str2: str) -> float:
        import difflib
        if not str1 or not str2:
            return 0.0
        # Simplifica strings (remove espaços extras, converte pra maiúsculo)
        s1 = str1.upper().strip()
        s2 = str2.upper().strip()
        return difflib.SequenceMatcher(None, s1, s2).ratio()
    
    @classmethod
    def verificar_duplicidade(cls, novo_registro: dict, historico_registros: list, 
                              tolerancia_dias: int = 2, limiar_similaridade_nome: float = 0.8) -> dict:
        """
        Compara `novo_registro` contra uma lista de dicionários `historico_registros`.
        Espera-se que cada registro tenha as chaves: 'valor', 'data' (str DD/MM/AAAA) e 'favorecido'.
        Retorna um dicionário com os detalhes da duplicidade ou None se estiver limpo.
        """
        try:
            val_novo = float(novo_registro.get("valor", 0.0))
            if val_novo <= 0:
                return None
                
            from datetime import datetime
            data_nova_str = novo_registro.get("data", "")
            try:
                data_nova = datetime.strptime(data_nova_str, "%d/%m/%Y")
            except:
                return None
                
            nome_novo = novo_registro.get("favorecido", "")
            
            for reg_antigo in historico_registros:
                val_antigo = float(reg_antigo.get("valor", 0.0))
                # 1. Valor precisa ser idêntico
                if val_antigo != val_novo:
                    continue
                    
                # 2. Distância de datas
                data_antiga_str = reg_antigo.get("data", "")
                try:
                    data_antiga = datetime.strptime(data_antiga_str, "%d/%m/%Y")
                    delta_dias = abs((data_nova - data_antiga).days)
                except:
                    continue
                    
                if delta_dias > tolerancia_dias:
                    continue
                    
                # 3. Similaridade do nome (Fuzzy)
                nome_antigo = reg_antigo.get("favorecido", "")
                sim = cls._calcular_similaridade(nome_novo, nome_antigo)
                
                if sim >= limiar_similaridade_nome:
                    return {
                        "risco": "ALTO",
                        "score_similaridade": round(sim * 100, 1),
                        "motivo": f"Registro idêntico de R$ {val_novo:.2f} com '{nome_antigo}' encontrado com diferença de {delta_dias} dia(s).",
                        "registro_conflitante": reg_antigo
                    }
                    
        except Exception:
            pass
            
        return None
