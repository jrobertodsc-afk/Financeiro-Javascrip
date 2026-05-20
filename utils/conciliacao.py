"""
utils/conciliacao.py — Módulo de Conciliação Bancária Inteligente (Fuzzy Matching).

Realiza o matching automático entre lançamentos do extrato bancário
e pagamentos registrados/autorizados no sistema usando fuzzy logic (difflib/ML).
"""
from __future__ import annotations

import difflib
from datetime import datetime, timedelta

def _calcular_similaridade(str1: str, str2: str) -> float:
    """Calcula similaridade entre duas strings usando SequenceMatcher."""
    s1 = str(str1).strip().upper()
    s2 = str(str2).strip().upper()
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, s1, s2).ratio()

def conciliar_lancamentos(
    extrato: list[dict],
    pagamentos: list[dict],
    limiar_fuzzy: float = 0.7,
    dias_tolerancia: int = 3
) -> dict:
    """
    Concilia lançamentos do extrato com registros de contas a pagar/pagamentos.
    
    Retorna dicionário:
        "conciliados": [ (lancamento_extrato, pagamento_banco, confianca) ],
        "nao_conciliados_extrato": [ lancamento_extrato ],
        "nao_conciliados_pagamentos": [ pagamento_banco ]
    """
    conciliados = []
    extrato_restante = list(extrato)
    pagamentos_restante = list(pagamentos)
    
    # Passos da conciliação:
    # 1. Match exato (Valor + Data Exata + Similaridade alta no nome)
    # 2. Match fuzzy (Valor Exato + Diferença de até X dias + Similaridade razoável)
    # 3. Match valor e data (Sem nome claro no extrato, ex: tarifas/TEDs em lote)

    # Função auxiliar para converter string de data em objeto date
    def _to_date(d_str: str) -> datetime:
        try:
            return datetime.strptime(d_str, "%d/%m/%Y")
        except:
            return datetime.min
    
    # PASS 1: Valor exato, data exata
    # Para cada pagamento, busca o melhor match no extrato
    for pag in list(pagamentos_restante):
        val_pag = abs(float(pag.get("valor", 0)))
        dt_pag = _to_date(pag.get("data", ""))
        nome_pag = pag.get("nome", "") or pag.get("favorecido", "")
        
        melhor_match = None
        melhor_score = 0.0
        
        for ext in extrato_restante:
            val_ext = abs(float(ext.get("valor", 0)))
            if abs(val_pag - val_ext) > 0.01:
                continue  # valores não batem
                
            dt_ext = _to_date(ext.get("data", ""))
            
            # Tolerância de data
            diff_dias = abs((dt_pag - dt_ext).days)
            if diff_dias > dias_tolerancia:
                continue
                
            # Verifica similaridade de nome
            nome_ext = ext.get("descricao", "")
            score = _calcular_similaridade(nome_pag, nome_ext)
            
            # Bônus por bater o dia exato
            if diff_dias == 0:
                score += 0.2
                
            # Bônus se houver palavras-chave da categoria
            if pag.get("tipo", "") in nome_ext:
                score += 0.1
                
            if score > melhor_score:
                melhor_score = score
                melhor_match = ext
                
        # Se atingiu o limiar, considera conciliado
        # Se for o mesmo valor e mesma data exata, a confiança é aceita mesmo com limiar menor,
        # desde que seja um valor não muito genérico (ex: tarifa de 10 reais pode ter colisão).
        if melhor_match:
            # Confiança calculada (limitada a 1.0)
            confianca = min(1.0, melhor_score)
            
            # Regras de aceite
            aceite = False
            dt_ext = _to_date(melhor_match.get("data", ""))
            diff_dias = abs((dt_pag - dt_ext).days)
            
            if confianca >= limiar_fuzzy:
                aceite = True
            elif diff_dias == 0 and confianca >= 0.4:
                # Mesma data e valor, aceita com nome minimamente similar
                aceite = True
            elif diff_dias <= 1 and confianca >= 0.5:
                aceite = True
                
            if aceite:
                conciliados.append({
                    "extrato": melhor_match,
                    "pagamento": pag,
                    "confianca": confianca,
                    "diff_dias": diff_dias
                })
                extrato_restante.remove(melhor_match)
                pagamentos_restante.remove(pag)
                
    return {
        "conciliados": conciliados,
        "nao_conciliados_extrato": extrato_restante,
        "nao_conciliados_pagamentos": pagamentos_restante
    }
