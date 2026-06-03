import time
import random
from datetime import datetime, timedelta

def obter_transacoes_open_finance(banco: str) -> list[dict]:
    """
    Simula uma chamada de API REST ao gateway Open Finance para obter transações em tempo real.
    Retorna uma lista de dicionários contendo transações bancárias estruturadas.
    """
    # Simula latência de rede realista para um gateway de API bancária
    time.sleep(1.2)
    
    banco = (banco or "").upper()
    hoje = datetime.now()
    ontem = hoje - timedelta(days=1)
    tres_dias_atras = hoje - timedelta(days=3)
    
    # Gera datas no formato dd/mm/yyyy
    dt_hoje = hoje.strftime("%d/%m/%Y")
    dt_ontem = ontem.strftime("%d/%m/%Y")
    dt_tres = tres_dias_atras.strftime("%d/%m/%Y")
    
    transacoes = []
    
    if banco == "ITAÚ":
        transacoes = [
            {
                "data": dt_hoje,
                "descricao": "PAGTO PIX CASA FERRO LTDA",
                "tipo": "PIX",
                "valor": 1250.00,  # Valor típico de aviamento / insumos
                "debito": True
            },
            {
                "data": dt_hoje,
                "descricao": "TARIFA MENSALIDADE CONTA ITAU UNIBANCO",
                "tipo": "TARIFA",
                "valor": 69.90,
                "debito": True
            },
            {
                "data": dt_ontem,
                "descricao": "PAGTO FORNECEDOR FELICITY INDUSTRIA TEXTIL",
                "tipo": "TED",
                "valor": 3200.00,  # Valor típico de frete/produção
                "debito": True
            },
            {
                "data": dt_ontem,
                "descricao": "PIX RECEBIDO CLIENTE LALUA VAREJO MATRIZ",
                "tipo": "PIX",
                "valor": 4500.00,
                "debito": False
            },
            {
                "data": dt_tres,
                "descricao": "TED ENVIADO KAIQUE RAMOS SERVICOS",
                "tipo": "TED",
                "valor": 450.00,
                "debito": True
            },
            {
                "data": dt_tres,
                "descricao": "PAGTO VIVO TELEFONICA BRASIL S.A.",
                "tipo": "BOLETO",
                "valor": 289.50,
                "debito": True
            }
        ]
        
    elif banco == "STONE":
        transacoes = [
            {
                "data": dt_hoje,
                "descricao": "SAQUE MATRIZ STONE CONTAS",
                "tipo": "SAQUE",
                "valor": 500.00,
                "debito": True
            },
            {
                "data": dt_hoje,
                "descricao": "DOC ENVIADO GOOGLE TECNOLOGIA BRASIL ERP",
                "tipo": "DOC",
                "valor": 450.00,
                "debito": True
            },
            {
                "data": dt_ontem,
                "descricao": "LIQUIDAÇÃO ADQUIRENTE STONE CREDITO",
                "tipo": "CARTAO",
                "valor": 8450.20,
                "debito": False
            },
            {
                "data": dt_ontem,
                "descricao": "TAXA DE ANTECIPAÇÃO RECEBIVEIS STONE",
                "tipo": "TAXA",
                "valor": 120.50,
                "debito": True
            }
        ]
        
    elif banco == "INTER":
        transacoes = [
            {
                "data": dt_hoje,
                "descricao": "TED ENVIADO NAESON GOMES INSTALAÇÃO",
                "tipo": "TED",
                "valor": 350.00,
                "debito": True
            },
            {
                "data": dt_ontem,
                "descricao": "PIX ENVIADO EDUARDO NASCIMENTO PREDIAL",
                "tipo": "PIX",
                "valor": 600.00,
                "debito": True
            },
            {
                "data": dt_ontem,
                "descricao": "DEVOLUÇÃO PIX CLIENTE DUPLICADO",
                "tipo": "PIX",
                "valor": 150.00,
                "debito": True
            },
            {
                "data": dt_tres,
                "descricao": "RENDIMENTO AUTOMÁTICO CDB INTER LIQUIDEZ",
                "tipo": "JUROS",
                "valor": 12.80,
                "debito": False
            }
        ]
        
    else:  # BRADESCO ou Banco do Brasil (Qualquer outro)
        transacoes = [
            {
                "data": dt_hoje,
                "descricao": "PAGTO BOLETO BANCO BRADESCO S.A.",
                "tipo": "BOLETO",
                "valor": 180.00,
                "debito": True
            },
            {
                "data": dt_ontem,
                "descricao": "DEBITO AUTOMÁTICO SEGURO PATRIMONIAL",
                "tipo": "DEBITO",
                "valor": 320.00,
                "debito": True
            },
            {
                "data": dt_ontem,
                "descricao": "RECEBIMENTO TED BOAH DISTRIBUIDORA",
                "tipo": "TED",
                "valor": 12000.00,
                "debito": False
            }
        ]
        
    return transacoes
