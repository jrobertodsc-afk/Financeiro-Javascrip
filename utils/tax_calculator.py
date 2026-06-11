from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def calcular_vencimento_imposto(data_emissao_str, tipo_imposto):
    """
    Calcula a data de vencimento do imposto baseado na data de emissão.
    Antecipa finais de semana para sexta-feira.
    Tipos mapeados:
    - ISS: Dia 05 do mês subsequente
    - ICMS_NORMAL: Dia 09 do mês subsequente
    - ICMS_ANTECIPACAO: Dia 25 do mês subsequente
    - FEDERAL (PIS, COFINS, CSLL, IRRF, INSS, ISSQN): Dia 20 do mês subsequente
    """
    if not data_emissao_str:
        return ""
        
    try:
        dt_emissao = datetime.strptime(data_emissao_str, "%d/%m/%Y")
    except ValueError:
        return data_emissao_str
        
    tipo_up = tipo_imposto.upper()
    
    if "ISS" in tipo_up and "QN" not in tipo_up: # ISS puro
        dia_vencimento = 5
    elif "ICMS_NORMAL" in tipo_up or "ICMS NORMAL" in tipo_up:
        dia_vencimento = 9
    elif "ANTECIPACAO" in tipo_up or "ANTECIPAÇÃO" in tipo_up:
        dia_vencimento = 25
    else:
        # PIS, COFINS, CSLL, IRRF, INSS, ISSQN, etc.
        dia_vencimento = 20
        
    # Mês subsequente
    dt_venc = dt_emissao + relativedelta(months=1)
    
    # Tratar meses que não têm dia 25 (Fevereiro) usando try
    try:
        dt_venc = dt_venc.replace(day=dia_vencimento)
    except ValueError:
        # Se for dia 29/30/31 e não existir no mês, pega o último dia do mês
        dt_venc = dt_venc + relativedelta(day=31)
        
    # Antecipar fim de semana
    if dt_venc.weekday() == 5: # Sábado
        dt_venc -= timedelta(days=1)
    elif dt_venc.weekday() == 6: # Domingo
        dt_venc -= timedelta(days=2)
        
    return dt_venc.strftime("%d/%m/%Y")
