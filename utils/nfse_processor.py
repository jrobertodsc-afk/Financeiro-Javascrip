"""
utils/nfse_processor.py — Módulo de Integração NFS-e (Multi-Prefeitura).

Define a interface padrão de comunicação (layout ABRASF) para emissão de
Notas Fiscais de Serviço Eletrônicas em prefeituras, lidando com RPS 
(Recibo Provisório de Serviços).
"""
from __future__ import annotations

import json
from datetime import datetime

class EmissorNFSe:
    """
    Classe base para integração de emissão de NFS-e (Serviços).
    Padrão adotado: ABRASF (usado pela maioria das capitais, ex: Salvador).
    """

    def __init__(self, empresa_cnpj: str, inscricao_municipal: str, certificado_path: str, ambiente: str = "homologacao"):
        self.empresa_cnpj = ''.join(filter(str.isdigit, empresa_cnpj))
        self.inscricao_municipal = ''.join(filter(str.isdigit, inscricao_municipal))
        self.certificado_path = certificado_path
        self.ambiente = ambiente
        self.codigo_municipio = "2927408" # IBGE Salvador (default)

    def preparar_rps(self, dados_servico: dict, tomador: dict) -> dict:
        """
        Prepara o payload do RPS (Recibo Provisório de Serviços).
        
        dados_servico: {
            "valor_servicos": 1500.00,
            "item_lista_servico": "17.01",
            "codigo_tributacao_municipio": "123456",
            "discriminacao": "Consultoria em Gestão de TI",
            "iss_retido": False
        }
        tomador: {
            "cnpj_cpf": "12345678901234",
            "razao_social": "Cliente Teste LTDA",
            "email": "cliente@email.com",
            "endereco": {
                "logradouro": "Rua Teste", "numero": "123", "bairro": "Centro",
                "codigo_municipio": "2927408", "uf": "BA", "cep": "40000000"
            }
        }
        """
        rps = {
            "IdentificacaoRps": {
                "Numero": str(int(datetime.now().timestamp())), # Gerador de ID temporário
                "Serie": "1",
                "Tipo": "1" # 1 - RPS
            },
            "DataEmissao": datetime.now().isoformat(),
            "NaturezaOperacao": "1", # 1 - Tributação no município
            "OptanteSimplesNacional": "2", # 1 - Sim, 2 - Não
            "IncentivadorCultural": "2",
            "Status": "1", # 1 - Normal
            "Servico": {
                "Valores": {
                    "ValorServicos": dados_servico.get("valor_servicos", 0.0),
                    "IssRetido": "1" if dados_servico.get("iss_retido") else "2",
                    "ValorIss": 0.0,
                    "BaseCalculo": dados_servico.get("valor_servicos", 0.0),
                    "Aliquota": 0.05, # 5% default
                    "ValorLiquidoNfse": dados_servico.get("valor_servicos", 0.0)
                },
                "ItemListaServico": dados_servico.get("item_lista_servico", "01.01"),
                "CodigoTributacaoMunicipio": dados_servico.get("codigo_tributacao_municipio", ""),
                "Discriminacao": dados_servico.get("discriminacao", "Serviços prestados"),
                "CodigoMunicipio": self.codigo_municipio
            },
            "Prestador": {
                "Cnpj": self.empresa_cnpj,
                "InscricaoMunicipal": self.inscricao_municipal
            },
            "Tomador": {
                "IdentificacaoTomador": {
                    "CpfCnpj": {
                        "Cnpj" if len(tomador.get("cnpj_cpf", "")) > 11 else "Cpf": tomador.get("cnpj_cpf", "")
                    }
                },
                "RazaoSocial": tomador.get("razao_social", ""),
                "Contato": {
                    "Email": tomador.get("email", "")
                }
            }
        }
        return rps

    def emitir_nfse(self, dados_servico: dict, tomador: dict) -> dict:
        """
        Simula a transmissão do RPS e conversão em NFS-e.
        No mundo real, assinaria o XML com A1 e enviaria via SOAP.
        """
        rps = self.preparar_rps(dados_servico, tomador)
        
        # Simula resposta da Prefeitura
        numero_nfse = str(int(datetime.now().timestamp() * 1000))[-8:]
        codigo_verificacao = "ABCD-1234"
        
        return {
            "sucesso": True,
            "ambiente": self.ambiente,
            "nfse": {
                "numero": numero_nfse,
                "codigo_verificacao": codigo_verificacao,
                "data_emissao": rps["DataEmissao"],
                "rps_vinculado": rps["IdentificacaoRps"]["Numero"],
                "link_impressao": f"https://nfse.salvador.ba.gov.br/impressao/{numero_nfse}/{codigo_verificacao}"
            },
            "mensagens": ["NFS-e gerada com sucesso a partir do RPS."]
        }

    def cancelar_nfse(self, numero_nfse: str, codigo_cancelamento: str = "1", motivo: str = "Erro na emissão") -> dict:
        """Simula o cancelamento de uma NFS-e."""
        return {
            "sucesso": True,
            "numero_nfse": numero_nfse,
            "data_cancelamento": datetime.now().isoformat(),
            "mensagens": [f"NFS-e {numero_nfse} cancelada com sucesso."]
        }
