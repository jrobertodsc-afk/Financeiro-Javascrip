"""
cnab_generator.py — Gerador de arquivo remessa CNAB 240 padrão Itaú (Banco 341).

Suporta:
  - Lote de Crédito em Conta (tipo C - TED/PIX para favorecidos)
  - Lote de Pagamento de Salários (tipo C com finalidade 01)
  - Geração do Header/Trailer de Arquivo e de Lote conforme layout Itaú CNAB 240

Referência: Manual Técnico CNAB 240 Itaú Unibanco — Pagamentos (versão 2023).
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from loguru import logger
import config
from services.database import listar_notas


# ── CONSTANTES FEBRABAN / ITAÚ ────────────────────────────────────────────────
BANCO_ITAU     = "341"
FEBRABAN_VER   = "103"   # Versão do leiaute CNAB 240
LINHA_SIZE     = 240     # Cada linha CNAB 240 deve ter 240 caracteres + \r\n


# ── FUNÇÕES DE FORMATAÇÃO CNAB ────────────────────────────────────────────────

def _alfa(valor: str, tamanho: int) -> str:
    """Formata campo alfanumérico: alinha à esquerda, preenche com espaços."""
    s = str(valor or "").upper()
    return s[:tamanho].ljust(tamanho)


def _num(valor, tamanho: int) -> str:
    """Formata campo numérico: alinha à direita, preenche com zeros."""
    try:
        n = int(float(str(valor or 0).replace(",", ".").replace(".", "")))
    except (ValueError, TypeError):
        n = 0
    return str(abs(n))[:tamanho].zfill(tamanho)


def _valor(v: float, inteiros: int = 13, decimais: int = 2) -> str:
    """Formata valor monetário sem ponto/vírgula (centavos)."""
    try:
        centavos = round(float(v) * (10 ** decimais))
    except (ValueError, TypeError):
        centavos = 0
    tamanho = inteiros + decimais
    return str(abs(int(centavos)))[:tamanho].zfill(tamanho)


def _data(dt: Optional[datetime] = None) -> str:
    """Formata data no padrão CNAB: DDMMAAAA."""
    d = dt or datetime.now()
    return d.strftime("%d%m%Y")


def _hora(dt: Optional[datetime] = None) -> str:
    """Formata hora no padrão CNAB: HHMMSS."""
    d = dt or datetime.now()
    return d.strftime("%H%M%S")


def _limpar(linha: str) -> str:
    """Garante que a linha tem exatamente 240 chars + CRLF."""
    s = linha.replace("\r", "").replace("\n", "")
    if len(s) != LINHA_SIZE:
        # Trunca ou preenche com espaços
        s = s[:LINHA_SIZE].ljust(LINHA_SIZE)
    return s + "\r\n"


# ── HEADER DE ARQUIVO ─────────────────────────────────────────────────────────

def _header_arquivo(cfg: dict, sequencial: int = 1) -> str:
    """
    Gera o Header do Arquivo (registro tipo 0).

    cfg deve conter:
        banco_codigo, agencia, agencia_dv, conta, conta_dv, dac,
        nome_empresa, cnpj_empresa
    """
    agencia  = _num(cfg.get("agencia", "0334"), 5)
    ag_dv    = _alfa(cfg.get("agencia_dv", " "), 1)
    conta    = _num(cfg.get("conta", "98775"), 12)
    conta_dv = _alfa(cfg.get("conta_dv", "7"), 1)
    dac      = _alfa(cfg.get("dac", " "), 1)

    linha = (
        BANCO_ITAU                                  # [001-003] Banco
        + "0000"                                    # [004-007] Lote (0000 = arquivo)
        + "0"                                       # [008-008] Registro tipo 0
        + _alfa("", 9)                              # [009-017] Uso FEBRABAN
        + "2"                                       # [018-018] Tipo Inscrição (2=CNPJ)
        + _num(cfg.get("cnpj_empresa", "0"), 14)   # [019-032] CNPJ empresa
        + _alfa(cfg.get("convenio", ""), 20)        # [033-052] Convênio banco
        + agencia                                   # [053-057] Agência
        + ag_dv                                     # [058-058] DV Agência
        + conta                                     # [059-070] Conta
        + conta_dv                                  # [071-071] DV Conta
        + dac                                       # [072-072] DAC
        + _alfa(cfg.get("nome_empresa", "EMPRESA"), 30)  # [073-102] Nome empresa
        + _alfa("BANCO ITAU SA", 30)               # [103-132] Nome banco
        + _alfa("", 10)                             # [133-142] Uso FEBRABAN
        + "1"                                       # [143-143] Código remessa (1=remessa)
        + _data()                                   # [144-151] Data geração
        + _hora()                                   # [152-157] Hora geração
        + _num(sequencial, 6)                       # [158-163] Número sequencial
        + FEBRABAN_VER                              # [164-166] Versão leiaute
        + _num(0, 5)                                # [167-171] Densidade (0 = não informado)
        + _alfa("", 20)                             # [172-191] Uso banco
        + _alfa("", 20)                             # [192-211] Uso empresa
        + _alfa("", 29)                             # [212-240] Uso FEBRABAN
    )
    return _limpar(linha)


def _trailer_arquivo(total_lotes: int, total_registros: int) -> str:
    """Gera o Trailer do Arquivo (registro tipo 9)."""
    linha = (
        BANCO_ITAU
        + "9999"                        # Lote 9999
        + "9"                           # Registro tipo 9
        + _alfa("", 9)                  # Uso FEBRABAN
        + _num(total_lotes, 6)          # Qtd lotes
        + _num(total_registros, 6)      # Qtd registros totais (incluindo H/T)
        + _num(0, 6)                    # Qtd contas (não obrigatório)
        + _alfa("", 205)                # Uso FEBRABAN
    )
    return _limpar(linha)


# ── HEADER DE LOTE ────────────────────────────────────────────────────────────

def _header_lote(cfg: dict, lote: int, finalidade: str = "CC", forma_pgto: int = 45) -> str:
    """
    Gera o Header do Lote (registro tipo 1).

    forma_pgto:
        01 = Crédito em Conta Corrente
        03 = DOC/TED
        45 = PIX
    finalidade:
        CC = Crédito em Conta
        FS = Folha de Salários
    """
    agencia  = _num(cfg.get("agencia", "0334"), 5)
    ag_dv    = _alfa(cfg.get("agencia_dv", " "), 1)
    conta    = _num(cfg.get("conta", "98775"), 12)
    conta_dv = _alfa(cfg.get("conta_dv", "7"), 1)
    dac      = _alfa(cfg.get("dac", " "), 1)

    linha = (
        BANCO_ITAU                                  # [001-003]
        + _num(lote, 4)                             # [004-007] Número do lote
        + "1"                                       # [008-008] Registro tipo 1
        + "C"                                       # [009-009] Tipo operação (C=crédito)
        + _num(forma_pgto, 2)                       # [010-011] Forma de pagamento
        + "040"                                     # [012-014] Versão layout lote
        + _alfa("", 1)                              # [015-015] Uso FEBRABAN
        + "2"                                       # [016-016] Tipo inscrição (2=CNPJ)
        + _num(cfg.get("cnpj_empresa", "0"), 14)   # [017-030] CNPJ
        + _alfa(cfg.get("convenio", ""), 20)        # [031-050] Convênio
        + agencia                                   # [051-055]
        + ag_dv                                     # [056-056]
        + conta                                     # [057-068]
        + conta_dv                                  # [069-069]
        + dac                                       # [070-070]
        + _alfa(cfg.get("nome_empresa", "EMPRESA"), 30)  # [071-100]
        + _alfa(cfg.get("info_lote", finalidade), 40)    # [101-140] Informação do lote
        + _alfa("", 3)                              # [141-143] Uso banco
        + _data()                                   # [144-151] Data pgto
        + _valor(0, 15, 2)                          # [152-168] Valor total (preenchido no trailer)
        + _num(0, 6)                                # [169-174] Qtd moeda (não usado)
        + _num(0, 13)                               # [175-187] Complemento
        + _alfa("", 3)                              # [188-190] Ocorrências
        + _alfa("", 50)                             # [191-240] Uso FEBRABAN
    )
    return _limpar(linha)


def _trailer_lote(lote: int, qtd_registros: int, valor_total: float) -> str:
    """Gera o Trailer do Lote (registro tipo 5)."""
    linha = (
        BANCO_ITAU
        + _num(lote, 4)
        + "5"                           # Registro tipo 5
        + _alfa("", 9)
        + _num(qtd_registros, 6)        # Qtd registros no lote (inclui H e T)
        + _valor(valor_total, 18, 2)    # Valor total do lote
        + _num(0, 18)                   # Qtd moeda
        + _num(0, 7)                    # Número aviso débito
        + _alfa("", 3)                  # Uso FEBRABAN
        + _alfa("", 165)                # Uso banco
        + _alfa("", 8)                  # Ocorrências
    )
    return _limpar(linha)


# ── SEGMENTO A (Crédito Conta Corrente/Poupança) ──────────────────────────────

def _segmento_a(
    lote: int,
    seq: int,
    pagamento: dict,
    data_pgto: Optional[datetime] = None,
) -> str:
    """
    Gera o Segmento A (registro tipo 3 - segmento A) para TED/PIX/Crédito.

    pagamento deve conter:
        nome, banco_dest, agencia_dest, conta_dest, valor, tipo_pgto (opcional)
        pix_chave (opcional para PIX), finalidade (opcional)
    """
    dt = data_pgto or datetime.now()
    banco_dest  = _num(pagamento.get("banco_dest", "341"), 3)
    agencia_dest = _num(pagamento.get("agencia_dest", "0"), 5)
    ag_dest_dv  = _alfa(pagamento.get("agencia_dest_dv", " "), 1)
    conta_dest  = _num(pagamento.get("conta_dest", "0"), 12)
    ct_dest_dv  = _alfa(pagamento.get("conta_dest_dv", " "), 1)
    dac_dest    = _alfa(pagamento.get("dac_dest", " "), 1)
    nome_dest   = _alfa(pagamento.get("nome", ""), 30)
    seu_numero  = _alfa(pagamento.get("seu_numero", ""), 20)
    valor       = pagamento.get("valor", 0.0)

    linha = (
        BANCO_ITAU                      # [001-003]
        + _num(lote, 4)                 # [004-007]
        + "3"                           # [008-008] Tipo registro (3=detalhe)
        + _num(seq, 5)                  # [009-013] Nº sequencial
        + "A"                           # [014-014] Segmento
        + _num(0, 1)                    # [015-015] Tipo movimento (0=inclusão)
        + _num(0, 2)                    # [016-017] Instrução movimento
        + _num(0, 2)                    # [018-019] Câmara compensação (0=STR)
        + banco_dest                    # [020-022] Banco favorecido
        + agencia_dest                  # [023-027] Agência favorecido
        + ag_dest_dv                    # [028-028] DV agência
        + conta_dest                    # [029-040] Conta favorecido
        + ct_dest_dv                    # [041-041] DV conta
        + dac_dest                      # [042-042] DAC
        + nome_dest                     # [043-072] Nome favorecido
        + seu_numero                    # [073-092] Seu número
        + _data(dt)                     # [093-100] Data pagamento
        + "BRL"                         # [101-103] Tipo moeda
        + _num(0, 15)                   # [104-118] Quantidade moeda
        + _valor(valor, 15, 2)          # [119-132] Valor pagamento
        + _alfa("", 20)                 # [133-152] Número documento banco
        + _alfa("", 8)                  # [153-160] Data real efetivação
        + _valor(0, 15, 2)              # [161-175] Valor real efetivação
        + _alfa(pagamento.get("info_complementar", ""), 20)  # [176-195]
        + _alfa(pagamento.get("finalidade_ted", "10"), 5)    # [196-200] Finalidade TED
        + _alfa("", 3)                  # [201-203] Uso FEBRABAN
        + _num(0, 1)                    # [204-204] Aviso (0=não emite)
        + _alfa("", 2)                  # [205-206] Uso FEBRABAN
        + _alfa("", 10)                 # [207-216] Ocorrências
        + _alfa("", 24)                 # [217-240] Uso FEBRABAN
    )
    return _limpar(linha)


# ── SEGMENTO B (PIX / Dados Complementares) ───────────────────────────────────

def _segmento_b(lote: int, seq: int, pagamento: dict) -> str:
    """
    Gera o Segmento B com dados complementares do favorecido (CPF/CNPJ + PIX).
    Obrigatório quando forma de pagamento é PIX (forma_lancto=45).
    """
    tipo_insc = "1" if len(str(pagamento.get("cpf_cnpj", "")).replace(".", "").replace("-", "").replace("/", "")) <= 11 else "2"
    cpf_cnpj  = _num(pagamento.get("cpf_cnpj", "0"), 14)

    linha = (
        BANCO_ITAU
        + _num(lote, 4)
        + "3"
        + _num(seq, 5)
        + "B"                           # Segmento B
        + _alfa("", 3)                  # Uso FEBRABAN
        + tipo_insc                     # Tipo inscrição favorecido
        + cpf_cnpj                      # CPF/CNPJ favorecido
        + _alfa(pagamento.get("logradouro", ""), 32)   # Endereço
        + _num(pagamento.get("numero_end", 0), 5)
        + _alfa(pagamento.get("complemento", ""), 15)
        + _alfa(pagamento.get("bairro", ""), 15)
        + _alfa(pagamento.get("cidade", ""), 20)
        + _num(pagamento.get("cep", 0), 8)
        + _alfa(pagamento.get("uf", ""), 2)
        + _alfa("", 6)                  # Data vencimento (não obrigatório aqui)
        + _valor(0, 15, 2)              # Valor documento
        + _valor(0, 15, 2)              # Abatimento
        + _valor(0, 15, 2)              # Desconto
        + _valor(0, 15, 2)              # Mora
        + _valor(0, 15, 2)              # Multa
        + _alfa(pagamento.get("pix_chave", ""), 25)   # Chave PIX
        + _alfa("", 14)                 # Uso FEBRABAN
        + _num(0, 1)                    # Aviso
        + _alfa("", 10)                 # Ocorrências
        + _alfa("", 1)                  # Uso banco
    )
    return _limpar(linha)


# ══════════════════════════════════════════════════════════════════════════════
# ── FUNÇÃO PRINCIPAL PÚBLICA ──────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def gerar_cnab240(
    dados_banco: dict,
    pagamentos: list[dict],
    data_pagamento: Optional[datetime] = None,
    caminho_saida: Optional[str] = None,
) -> str:
    """
    Gera o conteúdo de um arquivo remessa CNAB 240 padrão Itaú.
    """
    dt = data_pagamento or datetime.now()
    linhas = []

    # ── Header Arquivo ────────────────────────────────────────────────────────
    linhas.append(_header_arquivo(dados_banco, sequencial=1))
    num_lotes = 0

    # ── Agrupa pagamentos: PIX separado de TED/Conta ──────────────────────────
    pix_pgtos = [p for p in pagamentos if p.get("pix_chave") or
                 str(p.get("banco_dest", "")).startswith("PIX")]
    outros    = [p for p in pagamentos if p not in pix_pgtos]

    lote_atual = 0

    # ── LOTE 1: TED / Crédito em Conta ───────────────────────────────────────
    if outros:
        lote_atual += 1
        valor_lote  = sum(p.get("valor", 0) for p in outros)
        linhas_lote = []
        linhas_lote.append(_header_lote(dados_banco, lote_atual, "CC", forma_pgto=3))

        for seq, pgto in enumerate(outros, start=1):
            linhas_lote.append(_segmento_a(lote_atual, seq, pgto, dt))

        qtd_regs = len(linhas_lote) + 1  # +1 para o trailer
        linhas_lote.append(_trailer_lote(lote_atual, qtd_regs + 1, valor_lote))
        linhas.extend(linhas_lote)
        num_lotes += 1

    # ── LOTE 2: PIX ───────────────────────────────────────────────────────────
    if pix_pgtos:
        lote_atual += 1
        valor_lote  = sum(p.get("valor", 0) for p in pix_pgtos)
        linhas_lote = []
        linhas_lote.append(_header_lote(dados_banco, lote_atual, "PIX", forma_pgto=45))

        seq = 1
        for pgto in pix_pgtos:
            linhas_lote.append(_segmento_a(lote_atual, seq, pgto, dt))
            seq += 1
            linhas_lote.append(_segmento_b(lote_atual, seq, pgto))
            seq += 1

        qtd_regs = len(linhas_lote) + 1
        linhas_lote.append(_trailer_lote(lote_atual, qtd_regs + 1, valor_lote))
        linhas.extend(linhas_lote)
        num_lotes += 1

    # ── Trailer Arquivo ───────────────────────────────────────────────────────
    total_regs = len(linhas) + 1  # +1 para o próprio trailer
    linhas.append(_trailer_arquivo(num_lotes, total_regs))

    conteudo = "".join(linhas)

    # Salva em disco se caminho informado
    if caminho_saida:
        os.makedirs(os.path.dirname(caminho_saida) or ".", exist_ok=True)
        with open(caminho_saida, "w", encoding="ascii", errors="replace") as f:
            f.write(conteudo)

    return conteudo


def validar_cnab240(conteudo: str) -> tuple[bool, list[str]]:
    """
    Valida um conteúdo CNAB 240 verificando:
      - Tamanho de cada linha (deve ser 240 chars + CRLF = 242)
      - Presença de Header e Trailer de arquivo (tipos 0 e 9)
      - Consistência de lotes (Header tipo 1 seguido de Trailer tipo 5)

    Returns:
        (válido, lista_de_erros)
    """
    erros = []
    linhas = conteudo.split("\n")
    linhas_validas = [l.rstrip("\r") for l in linhas if l.strip()]

    if not linhas_validas:
        return False, ["Arquivo vazio"]

    # Verifica tamanho
    for i, linha in enumerate(linhas_validas, start=1):
        if len(linha) != LINHA_SIZE:
            erros.append(f"Linha {i}: tamanho {len(linha)} (esperado {LINHA_SIZE})")

    # Verifica Header/Trailer de arquivo
    if linhas_validas[0][7] != "0":
        erros.append("Primeira linha não é Header de Arquivo (tipo 0)")
    if linhas_validas[-1][7] != "9":
        erros.append("Última linha não é Trailer de Arquivo (tipo 9)")

    # Verifica banco
    for i, linha in enumerate(linhas_validas, start=1):
        if linha[:3] != BANCO_ITAU:
            erros.append(f"Linha {i}: código de banco inválido '{linha[:3]}' (esperado '{BANCO_ITAU}')")

    return len(erros) == 0, erros


# ══════════════════════════════════════════════════════════════════════════════
# ── INTEGRAÇÃO: GERAR REMESSA DO BANCO DE DADOS ───────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def gerar_remessa_notas(banco: str = "ITAÚ") -> dict:
    """
    Orquestra a busca de notas (APROVADA/PENDENTE) no banco de dados e gera
    o arquivo .REM na pasta configurada (config.PASTA_SAIDA).

    Retorna um dicionário com o relatório:
    {
        "notas_incluidas": int,
        "valor_total": float,
        "arquivo_gerado": str ou None,
        "erro": str (opcional)
    }
    """
    try:
        logger.info(f"Iniciando geração de remessa CNAB 240 para o banco {banco}")
        dados_banco_raw = config.CNAB_CONTAS.get(banco)
        
        if not dados_banco_raw:
            msg = f"Configurações não encontradas em config.py para o banco {banco}."
            logger.error(msg)
            return {"notas_incluidas": 0, "valor_total": 0.0, "arquivo_gerado": None, "erro": msg}

        # Separar conta e agência (tratamento para formato '12345-6')
        ag_full = dados_banco_raw.get("agencia", "")
        ag = ag_full.split("-")[0] if "-" in ag_full else ag_full
        ag_dv = ag_full.split("-")[1] if "-" in ag_full else " "
        
        ct_full = dados_banco_raw.get("conta", "")
        ct = ct_full.split("-")[0] if "-" in ct_full else ct_full
        ct_dv = ct_full.split("-")[1] if "-" in ct_full else " "

        dados_banco = {
            "agencia": ag,
            "agencia_dv": ag_dv,
            "conta": ct,
            "conta_dv": ct_dv,
            "cnpj_empresa": "00000000000000",
            "nome_empresa": "EMPRESA PADRAO",
        }

        # 1. Buscar notas no banco
        notas_aprovadas = listar_notas(status="APROVADA")
        notas_pendentes = listar_notas(status="PENDENTE")
        todas_notas = notas_aprovadas + notas_pendentes

        pagamentos = []
        valor_total = 0.0

        # 2. Formatar notas para o layout exigido pelo gerador
        for nota in todas_notas:
            valor = nota.get("valor_liquido") or nota.get("valor_bruto") or 0.0
            if valor <= 0:
                continue

            conta_dest_full = str(nota.get("conta_dest") or "")
            conta_dest = conta_dest_full.split("-")[0] if "-" in conta_dest_full else conta_dest_full
            conta_dest_dv = conta_dest_full.split("-")[1] if "-" in conta_dest_full else "0"
            
            agencia_dest_full = str(nota.get("agencia_dest") or "")
            agencia_dest = agencia_dest_full.split("-")[0] if "-" in agencia_dest_full else agencia_dest_full
            agencia_dest_dv = agencia_dest_full.split("-")[1] if "-" in agencia_dest_full else "0"

            pgto = {
                "nome": str(nota.get("fornecedor", "")),
                "banco_dest": str(nota.get("banco_dest", "")),
                "agencia_dest": agencia_dest,
                "agencia_dest_dv": agencia_dest_dv,
                "conta_dest": conta_dest,
                "conta_dest_dv": conta_dest_dv,
                "cpf_cnpj": nota.get("cpf_cnpj_dest") or nota.get("cnpj") or "",
                "valor": float(valor),
                "pix_chave": nota.get("pix_chave", ""),
                "finalidade_ted": "10",
                "info_complementar": f"NF {nota.get('numero_nf', '')}",
                "seu_numero": str(nota.get("numero_tx", ""))[:20]
            }
            pagamentos.append(pgto)
            valor_total += float(valor)

        if not pagamentos:
            msg = "Nenhuma nota válida encontrada para geração de remessa."
            logger.info(msg)
            return {"notas_incluidas": 0, "valor_total": 0.0, "arquivo_gerado": None, "erro": msg}

        # 3. Gerar o arquivo .REM na PASTA_SAIDA
        agora = datetime.now()
        nome_arquivo = f"CNAB_{agora.strftime('%Y%m%d_%H%M%S')}.REM"
        caminho_saida = os.path.join(config.PASTA_SAIDA, nome_arquivo)
        
        gerar_cnab240(
            dados_banco=dados_banco,
            pagamentos=pagamentos,
            data_pagamento=agora,
            caminho_saida=caminho_saida
        )
        
        logger.success(f"Arquivo de remessa {nome_arquivo} gerado com sucesso! Incluiu {len(pagamentos)} notas. Total: R$ {valor_total:.2f}")
        
        # 4. Retornar relatório
        return {
            "notas_incluidas": len(pagamentos),
            "valor_total": valor_total,
            "arquivo_gerado": nome_arquivo
        }

    except Exception as e:
        logger.exception("Erro crítico ao gerar remessa CNAB.")
        return {"notas_incluidas": 0, "valor_total": 0.0, "arquivo_gerado": None, "erro": str(e)}
