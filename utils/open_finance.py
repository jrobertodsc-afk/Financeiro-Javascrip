"""
Módulo Open Finance - Com System ERP
Prepara a fundação estrutural para conexões reais com APIs bancárias
(Itaú, Santander, etc) para substituição da leitura de PDFs de extrato.
Por enquanto, opera como uma Mock API para validação arquitetural.
"""

from datetime import datetime, timedelta
import random

class BankAPIInterface:
    def autenticar(self):
        raise NotImplementedError
        
    def buscar_extrato(self, data_ini: str, data_fim: str):
        raise NotImplementedError
        
    def iniciar_pagamento(self, dados: dict):
        raise NotImplementedError

class ItauOpenFinance(BankAPIInterface):
    """
    Mock da API do Itaú Empresas (Open Finance / Pix).
    Pronto para receber Client ID e Secret reais no futuro.
    """
    
    def __init__(self, client_id=None, client_secret=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        
    def autenticar(self):
        # Aqui aconteceria o POST para https://sts.itau.com.br/api/oauth/token
        self.token = "MOCK_BEARER_TOKEN_12345"
        return True
        
    def buscar_extrato(self, data_ini: str, data_fim: str):
        """
        Retorna extrato consolidado simulando o formato real JSON da Febraban.
        """
        if not self.token:
            self.autenticar()
            
        # Simula resposta de API
        hoje = datetime.now()
        transacoes = []
        
        # Gera 5 a 10 transações mockadas
        for i in range(random.randint(5, 10)):
            dia_offset = random.randint(0, 5)
            data_tx = hoje - timedelta(days=dia_offset)
            
            valor = round(random.uniform(50.0, 5000.0), 2)
            is_entrada = random.choice([True, False])
            
            if not is_entrada: valor = -valor
            
            descricoes_saida = ["PIX ENVIADO", "TED ENVIADO", "PAG BOLETO", "TARIFA BANCARIA"]
            descricoes_entrada = ["PIX RECEBIDO", "TED RECEBIDO", "CREDITO TEF"]
            
            desc = random.choice(descricoes_entrada) if is_entrada else random.choice(descricoes_saida)
            
            tx = {
                "idTransacao": f"ITAU{random.randint(100000, 999999)}",
                "dataTransacao": data_tx.strftime("%Y-%m-%d"),
                "tipoTransacao": "CREDITO" if is_entrada else "DEBITO",
                "valor": abs(valor),
                "descricao": desc,
                "favorecido": "MOCK FORNECEDOR S/A" if not is_entrada else "CLIENTE MOCK"
            }
            transacoes.append(tx)
            
        return {
            "status": "SUCESSO",
            "banco": "ITAÚ UNIBANCO S.A.",
            "agencia": "0000",
            "conta": "00000-0",
            "periodo": {"inicio": data_ini, "fim": data_fim},
            "transacoes": sorted(transacoes, key=lambda x: x["dataTransacao"], reverse=True)
        }

    def iniciar_pagamento(self, dados: dict):
        """
        Simula a Iniciação de Pagamentos via API.
        """
        if not self.token:
            self.autenticar()
            
        return {
            "status": "PROCESSANDO",
            "idPagamento": f"PAY{random.randint(10000, 99999)}",
            "mensagem": "Pagamento enviado com sucesso para a fila de processamento."
        }
