"""
utils/integrations_utils.py — Integrações externas do Robô Financeiro BOAH/SOLAR.

Responsável por:
  - Leitura de extrato bancário Itaú (PDF)
  - Leitura de relatórios Getnet (XLSX)
  - Leitura de relatórios de pagamentos Itaú (XLSX)
  - Envio de e-mail de relatório de comprovantes RH
  - Busca de fornecedor por nome no banco de dados
"""
from __future__ import annotations

import os
import re
import smtplib
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Callable, Optional

# ── LEITURA DO EXTRATO ITAÚ (PDF) ────────────────────────────────────────────

def ler_extrato_pdf(caminho_pdf: str) -> tuple[dict, str]:
    """
    Lê o extrato bancário do Itaú em formato PDF e retorna um dicionário
    com as contas e seus lançamentos, além do período do extrato.

    Retorna:
        (contas, periodo)
        contas = { "0334/98775-7": {"nome": "LALUA", "lancamentos": [...]} }
        periodo = "01/05/2026 a 31/05/2026"
    """
    try:
        import pypdf
    except ImportError:
        try:
            import PyPDF2 as pypdf
        except ImportError:
            return {}, datetime.now().strftime("%d/%m/%Y")

    contas: dict = {}
    periodo: str = datetime.now().strftime("%d/%m/%Y")

    try:
        reader = pypdf.PdfReader(caminho_pdf)
        texto_total = ""
        for page in reader.pages:
            texto_total += (page.extract_text() or "") + "\n"
    except Exception as e:
        print(f"[ler_extrato_pdf] Erro ao ler PDF: {e}")
        return {}, periodo

    # ── Detecta período do extrato ────────────────────────────────────────────
    m_periodo = re.search(
        r"per[íi]odo[:\s]+(\d{2}/\d{2}/\d{4})\s*(?:a|até|–|-)\s*(\d{2}/\d{2}/\d{4})",
        texto_total, re.IGNORECASE
    )
    if m_periodo:
        periodo = f"{m_periodo.group(1)} a {m_periodo.group(2)}"

    # ── Detecta contas e agências ─────────────────────────────────────────────
    # Padrão Itaú: "Agência 0334 / Conta 98775-7" ou similar
    m_contas = re.findall(
        r"ag[eê]ncia\s+(\d{4})\s*/?\s*conta\s+([\d\-]+)",
        texto_total, re.IGNORECASE
    )

    conta_key = "principal"
    if m_contas:
        ag, ct = m_contas[0]
        conta_key = f"{ag}/{ct}"

    # Detecta nome da empresa
    nome_empresa = "BOAH"
    if "LALUA" in texto_total.upper() or "98775" in texto_total:
        nome_empresa = "LALUA"
    elif "SOLAR" in texto_total.upper():
        nome_empresa = "SOLAR"

    lancamentos = _parsear_lancamentos_itau(texto_total)

    contas[conta_key] = {
        "nome": nome_empresa,
        "agencia": m_contas[0][0] if m_contas else "0000",
        "conta": m_contas[0][1] if m_contas else "00000-0",
        "lancamentos": lancamentos,
        "saldo_inicial": _extrair_saldo(texto_total, "anterior"),
        "saldo_final": _extrair_saldo(texto_total, "final"),
    }

    return contas, periodo


def _parsear_lancamentos_itau(texto: str) -> list[dict]:
    """
    Extrai lançamentos do texto do extrato Itaú.
    Formato típico: DD/MM  DESCRIÇÃO  VALOR  SALDO
    Débitos: valor negativo ou precedido por 'D'
    Créditos: valor positivo ou precedido por 'C'
    """
    lancamentos = []

    # Padrão: data + descrição + valor (com D ou C no final, ou sinal)
    padrao = re.compile(
        r"(\d{2}/\d{2}(?:/\d{4})?)\s+"        # data
        r"(.+?)\s+"                             # descrição
        r"([\d.,]+)\s*([DC]?)\s*"              # valor + D/C
        r"([\d.,]+)?",                          # saldo (opcional)
        re.MULTILINE
    )

    ano_atual = datetime.now().year

    for m in padrao.finditer(texto):
        data_str = m.group(1)
        descricao = m.group(2).strip()
        valor_str = m.group(3)
        tipo_dc = m.group(4).upper()

        # Pula linhas que parecem cabeçalhos ou rodapés
        if len(descricao) < 3 or any(x in descricao.upper() for x in [
            "SALDO", "TOTAL", "PERÍODO", "AGÊNCIA", "CONTA", "EXTRATO"
        ]):
            continue

        try:
            valor = float(valor_str.replace(".", "").replace(",", "."))
        except ValueError:
            continue

        if valor == 0:
            continue

        # Determina débito/crédito
        eh_debito = tipo_dc == "D" or descricao.upper().startswith("DEB")
        if not tipo_dc:
            # Heurística: algumas descrições tipicamente são débito
            eh_debito = any(kw in descricao.upper() for kw in [
                "PAG", "TRF", "PIX ENV", "SAQUE", "TARIFA", "DOC",
                "COMPRA", "DEBITO", "BOLETO"
            ])

        # Normaliza data
        try:
            if len(data_str) <= 5:  # DD/MM
                data_obj = datetime.strptime(f"{data_str}/{ano_atual}", "%d/%m/%Y")
            else:
                data_obj = datetime.strptime(data_str, "%d/%m/%Y")
            data_fmt = data_obj.strftime("%d/%m/%Y")
        except ValueError:
            data_fmt = data_str

        # Classifica tipo de lançamento
        tipo = _classificar_tipo_lancamento(descricao)

        lancamentos.append({
            "data": data_fmt,
            "descricao": descricao,
            "valor": valor,
            "debito": eh_debito,
            "tipo": tipo,
            "categoria": "",
        })

    return lancamentos


def _classificar_tipo_lancamento(descricao: str) -> str:
    """Classifica o tipo de lançamento pelo texto da descrição."""
    desc = descricao.upper()
    if "PIX" in desc:        return "PIX"
    if "TED" in desc:        return "TED"
    if "DOC" in desc:        return "DOC"
    if "BOLETO" in desc:     return "BOLETO"
    if "TARIFA" in desc:     return "TARIFA"
    if "SAQUE" in desc:      return "SAQUE"
    if "TRANSF" in desc:     return "TRANSFERÊNCIA"
    if "FOLHA" in desc or "SALARIO" in desc: return "FOLHA"
    if "DARF" in desc or "SIMPLES" in desc:  return "IMPOSTO"
    if "GNRE" in desc:       return "GNRE"
    if "FGTS" in desc:       return "FGTS"
    if "INSS" in desc:       return "INSS"
    if any(x in desc for x in ["RECEBIMENTO", "CREDITO", "DEP ", "DEPOSITO"]):
        return "CRÉDITO"
    return "OUTROS"


def _extrair_saldo(texto: str, tipo: str) -> float:
    """Extrai saldo inicial ou final do extrato."""
    patterns = {
        "anterior": r"saldo\s+anterior\s*[:\s]+R?\$?\s*([\d.,]+)",
        "final":    r"saldo\s+(?:final|disponível|atual)\s*[:\s]+R?\$?\s*([\d.,]+)",
    }
    m = re.search(patterns.get(tipo, ""), texto, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(".", "").replace(",", "."))
        except ValueError:
            pass
    return 0.0


# ── LEITURA DO RELATÓRIO GETNET (XLSX) ────────────────────────────────────────

def ler_getnet_excel(caminho_xlsx: str) -> list[dict]:
    """
    Lê o relatório de transações da Getnet em formato Excel (.xlsx).

    Colunas esperadas (Getnet padrão):
        Data Venda | Bandeira | Forma | Modalidade | Valor Bruto | Taxas | Valor Líquido | NSU/Autorização | PV/Filial

    Retorna lista de dicionários com os campos normalizados.
    """
    try:
        import openpyxl
    except ImportError:
        print("[ler_getnet_excel] openpyxl não instalado. Execute: pip install openpyxl")
        return []

    transacoes = []

    try:
        wb = openpyxl.load_workbook(caminho_xlsx, read_only=True, data_only=True)
        ws = wb.active

        # Detecta linha de cabeçalho (primeira linha com texto)
        header_row = None
        header_map = {}
        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if any(isinstance(c, str) and len(str(c)) > 2 for c in row):
                header_row = row_idx
                for col_idx, cell in enumerate(row):
                    if cell:
                        header_map[str(cell).strip().lower()] = col_idx
                break

        if not header_map:
            wb.close()
            return []

        # Mapeamento flexível de colunas
        def _col(keys: list[str]) -> int | None:
            for k in keys:
                for h, idx in header_map.items():
                    if k in h:
                        return idx
            return None

        idx_data     = _col(["data venda", "data", "dt venda"])
        idx_bandeira = _col(["bandeira", "brand"])
        idx_forma    = _col(["forma", "tipo pagto", "tipo pag"])
        idx_modal    = _col(["modalidade", "modal"])
        idx_bruto    = _col(["valor bruto", "bruto", "valor total"])
        idx_taxas    = _col(["taxa", "desconto", "tarifa"])
        idx_liquido  = _col(["valor líquido", "liquido", "valor liq", "líquido"])
        idx_filial   = _col(["filial", "pv", "estabelecimento", "loja"])
        idx_nsu      = _col(["nsu", "autorização", "autorizacao", "tid"])

        nome_arquivo = os.path.basename(caminho_xlsx)
        filial_padrao = _extrair_filial_getnet(nome_arquivo)

        skip_header = True
        for row in ws.iter_rows(values_only=True):
            if skip_header:
                skip_header = False
                continue

            def _val(idx):
                return row[idx] if idx is not None and idx < len(row) else None

            data_venda = _parse_data_getnet(_val(idx_data))
            bruto   = _parse_float_getnet(_val(idx_bruto))
            taxas   = _parse_float_getnet(_val(idx_taxas))
            liquido = _parse_float_getnet(_val(idx_liquido))

            if liquido == 0 and bruto == 0:
                continue  # linha vazia

            if liquido == 0 and bruto > 0:
                liquido = bruto - taxas

            bandeira  = str(_val(idx_bandeira) or "").strip()
            forma     = str(_val(idx_forma)    or "").strip()
            modal     = str(_val(idx_modal)    or "").strip()
            filial    = str(_val(idx_filial)   or filial_padrao).strip() or filial_padrao
            nsu       = str(_val(idx_nsu)      or "").strip()

            transacoes.append({
                "data_venda": data_venda,
                "bandeira":   bandeira,
                "forma":      forma,
                "modalidade": modal,
                "bruto":      bruto,
                "taxas":      taxas,
                "liquido":    liquido,
                "filial":     filial,
                "nsu":        nsu,
                "origem":     nome_arquivo,
            })

        wb.close()

    except Exception as e:
        print(f"[ler_getnet_excel] Erro ao ler {caminho_xlsx}: {e}")

    return transacoes


def _parse_data_getnet(valor) -> date | None:
    """Converte valor de célula Excel para date."""
    if valor is None:
        return None
    if isinstance(valor, (datetime, date)):
        return valor.date() if isinstance(valor, datetime) else valor
    s = str(valor).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_float_getnet(valor) -> float:
    """Converte valor de célula Excel para float."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).replace("R$", "").replace(" ", "").strip()
    if not s:
        return 0.0
    # Formato BR: 1.234,56
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _extrair_filial_getnet(nome_arquivo: str) -> str:
    """Tenta extrair nome da filial do nome do arquivo Getnet."""
    filiais = ["BARRA", "HORTO", "PASEO", "SDB", "VILAS", "MATRIZ",
               "BELA VISTA", "PARALELA", "LAURO", "CAMAÇARI"]
    nome_upper = nome_arquivo.upper()
    for f in filiais:
        if f in nome_upper:
            return f
    return "FILIAL"


# ── LEITURA DO EXCEL DE PAGAMENTOS ITAÚ ──────────────────────────────────────

def ler_itau_pagamentos(caminho_xlsx: str) -> list[dict]:
    """
    Lê o relatório de pagamentos do Itaú (Gerenciador Financeiro / IB Empresas).

    Colunas típicas:
        Data | Favorecido/Beneficiário | CNPJ/CPF | Tipo (PIX/TED/DOC) | Valor | Status | Referência

    Retorna lista de dicionários.
    """
    try:
        import openpyxl
    except ImportError:
        return []

    pagamentos = []

    try:
        wb = openpyxl.load_workbook(caminho_xlsx, read_only=True, data_only=True)
        ws = wb.active

        header_map = {}
        skip = True
        for row in ws.iter_rows(values_only=True):
            if skip:
                # Detecta cabeçalho
                if any(isinstance(c, str) and any(kw in str(c).lower() for kw in [
                    "favorecido", "benefici", "data", "valor", "tipo"
                ]) for c in row):
                    for idx, cell in enumerate(row):
                        if cell:
                            header_map[str(cell).strip().lower()] = idx
                    skip = False
                continue

            def _col(*keys):
                for k in keys:
                    for h, i in header_map.items():
                        if k in h:
                            return row[i] if i < len(row) else None
                return None

            data    = _parse_data_getnet(_col("data", "dt pgto", "data pgto"))
            nome    = str(_col("favorecido", "benefici", "nome") or "").strip()
            cnpj    = str(_col("cnpj", "cpf", "documento") or "").strip()
            tipo    = str(_col("tipo", "forma", "canal") or "").strip()
            valor   = _parse_float_getnet(_col("valor"))
            status  = str(_col("status", "situação", "situacao") or "").strip()

            if not nome and valor == 0:
                continue

            pagamentos.append({
                "data":   data,
                "nome":   nome,
                "cnpj":   cnpj,
                "tipo":   tipo,
                "valor":  valor,
                "status": status,
            })

        wb.close()

    except Exception as e:
        print(f"[ler_itau_pagamentos] Erro: {e}")

    return pagamentos


def ler_itau_folha(caminho_xlsx: str) -> list[dict]:
    """
    Lê folha de pagamento de salários em formato Excel.

    Colunas típicas:
        Nome | CPF | Banco | Agência | Conta | Valor

    Retorna lista de colaboradores com dados bancários para CNAB.
    """
    try:
        import openpyxl
    except ImportError:
        return []

    colaboradores = []

    try:
        wb = openpyxl.load_workbook(caminho_xlsx, read_only=True, data_only=True)
        ws = wb.active

        header_map = {}
        skip = True
        for row in ws.iter_rows(values_only=True):
            if skip:
                if any(isinstance(c, str) and any(kw in str(c).lower() for kw in [
                    "nome", "cpf", "banco", "conta", "valor", "salario"
                ]) for c in row):
                    for idx, cell in enumerate(row):
                        if cell:
                            header_map[str(cell).strip().lower()] = idx
                    skip = False
                continue

            def _col(*keys):
                for k in keys:
                    for h, i in header_map.items():
                        if k in h:
                            return row[i] if i < len(row) else None
                return None

            nome   = str(_col("nome", "funcionário", "funcionario") or "").strip()
            cpf    = str(_col("cpf") or "").strip()
            banco  = str(_col("banco", "cod banco") or "").strip()
            agencia = str(_col("agência", "agencia") or "").strip()
            conta  = str(_col("conta") or "").strip()
            valor  = _parse_float_getnet(_col("valor", "salário", "salario", "líquido"))

            if not nome or valor == 0:
                continue

            colaboradores.append({
                "nome":    nome,
                "cpf":    cpf,
                "banco":  banco,
                "agencia": agencia,
                "conta":  conta,
                "valor":  valor,
            })

        wb.close()

    except Exception as e:
        print(f"[ler_itau_folha] Erro: {e}")

    return colaboradores


# ── ENVIO DE RELATÓRIO POR E-MAIL ─────────────────────────────────────────────

def enviar_email_relatorio(
    itens: list[dict],
    log_fn: Optional[Callable] = None,
    destino_override: Optional[str] = None,
) -> bool:
    """
    Envia relatório de comprovantes (RH ou outros) por e-mail.

    `itens` deve ser lista de dicts com:
        nome, valor, data, filial, caminho (caminho do PDF), categoria

    `destino_override`: se informado, usa este e-mail em vez do padrão.
    """
    try:
        from config import (
            SMTP_HOST, SMTP_PORT, EMAIL_REMETENTE, EMAIL_SENHA,
            EMAIL_DESTINO_DP
        )
    except ImportError as e:
        if log_fn:
            log_fn(f"❌ Erro ao importar config: {e}")
        return False

    destino = destino_override or EMAIL_DESTINO_DP

    if not EMAIL_REMETENTE or not EMAIL_SENHA:
        if log_fn:
            log_fn("❌ E-mail remetente ou senha não configurados.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"]    = EMAIL_REMETENTE
        msg["To"]      = destino
        msg["Subject"] = (
            f"Comprovantes — {len(itens)} arquivo(s) | "
            f"{datetime.now().strftime('%d/%m/%Y')}"
        )

        # ── Corpo HTML ──────────────────────────────────────────────────────
        total_valor = sum(item.get("valor", 0) or 0 for item in itens)
        linhas_html = ""
        for item in itens:
            data_str = (
                item["data"].strftime("%d/%m/%Y")
                if isinstance(item.get("data"), (datetime, date))
                else str(item.get("data") or "")
            )
            linhas_html += (
                f"<tr>"
                f"<td style='padding:6px 10px;border:1px solid #334155'>{data_str}</td>"
                f"<td style='padding:6px 10px;border:1px solid #334155'><b>{item.get('nome','')}</b></td>"
                f"<td style='padding:6px 10px;border:1px solid #334155'>{item.get('categoria','')}</td>"
                f"<td style='padding:6px 10px;border:1px solid #334155'>{item.get('filial','')}</td>"
                f"<td style='padding:6px 10px;border:1px solid #334155;text-align:right'>"
                f"R$ {item.get('valor',0):,.2f}</td>"
                f"</tr>"
            )

        corpo = f"""<html><body style='font-family:Arial,sans-serif;'>
<div style='background:#1a1a2e;padding:16px;border-radius:8px;margin-bottom:16px;'>
  <h2 style='color:#38bdf8;margin:0;'>📄 Relatório de Comprovantes</h2>
  <p style='color:#94a3b8;margin:4px 0 0;'>Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
</div>
<p>Seguem os comprovantes solicitados:</p>
<table style='border-collapse:collapse;width:100%;font-size:12px;'>
  <tr style='background:#1a1a2e;color:#fff;'>
    <th style='padding:8px 10px;'>Data</th>
    <th style='padding:8px 10px;'>Nome</th>
    <th style='padding:8px 10px;'>Categoria</th>
    <th style='padding:8px 10px;'>Filial</th>
    <th style='padding:8px 10px;'>Valor</th>
  </tr>
  {linhas_html}
  <tr style='background:#064e3b;color:#4ade80;font-weight:bold;'>
    <td colspan='4' style='padding:8px 10px;border:1px solid #334155;'>TOTAL</td>
    <td style='padding:8px 10px;border:1px solid #334155;text-align:right'>
      R$ {total_valor:,.2f}</td>
  </tr>
</table>
<br>
<p style='font-size:11px;color:#888;'><i>Robô Financeiro BOAH/SOLAR — Com System</i></p>
</body></html>"""

        msg.attach(MIMEText(corpo, "html", "utf-8"))

        # ── Anexa PDFs ──────────────────────────────────────────────────────
        anexados = 0
        for item in itens:
            caminho = item.get("caminho", "")
            if caminho and os.path.exists(caminho):
                with open(caminho, "rb") as f:
                    parte = MIMEApplication(f.read(), _subtype="pdf")
                    parte.add_header(
                        "Content-Disposition", "attachment",
                        filename=os.path.basename(caminho)
                    )
                    msg.attach(parte)
                    anexados += 1

        # ── Envio ────────────────────────────────────────────────────────────
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as srv:
            srv.login(EMAIL_REMETENTE, EMAIL_SENHA)
            srv.sendmail(EMAIL_REMETENTE, destino, msg.as_bytes())

        if log_fn:
            log_fn(
                f"✅ E-mail enviado para {destino} com {anexados} PDF(s) | "
                f"Total: R$ {total_valor:,.2f}"
            )
        return True

    except Exception as e:
        if log_fn:
            log_fn(f"❌ Erro ao enviar e-mail: {e}")
        return False


# ── BUSCA DE FORNECEDOR POR NOME ──────────────────────────────────────────────

def buscar_fornecedor_por_nome(nome: str) -> dict | None:
    """
    Busca fornecedor no banco de dados pelo nome (busca parcial case-insensitive).

    Retorna o primeiro registro encontrado ou None.
    """
    if not nome:
        return None

    try:
        from database import buscar_fornecedor_por_cnpj
        from config import USE_SUPABASE

        nome_upper = nome.strip().upper()

        # Tenta via Supabase primeiro
        if USE_SUPABASE:
            try:
                from database import supabase
                if supabase:
                    res = (
                        supabase.table("fornecedores")
                        .select("*")
                        .ilike("nome", f"%{nome_upper}%")
                        .limit(1)
                        .execute()
                    )
                    if res.data:
                        return res.data[0]
            except Exception:
                pass

        # Fallback SQLite
        import sqlite3
        from config import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM fornecedores WHERE UPPER(nome) LIKE ? LIMIT 1",
            (f"%{nome_upper}%",)
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    except Exception as e:
        print(f"[buscar_fornecedor_por_nome] Erro: {e}")
        return None


# ── UTILITÁRIOS PÚBLICOS ───────────────────────────────────────────────────────

def calcular_periodo_sugerido() -> tuple[datetime, datetime, str]:
    """
    Sugere o período de processamento:
      - Segunda-feira: retorna sexta-feira anterior (período fin. de semana)
      - Outros dias: retorna ontem
    Retorna (data_inicio, data_fim, label).
    """
    from datetime import timedelta
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    dia_semana = hoje.weekday()  # 0=segunda, 6=domingo

    if dia_semana == 0:  # Segunda: processa sex+sáb+dom
        inicio = hoje - timedelta(days=3)
        fim = hoje - timedelta(days=1)
        label = f"Fim de semana ({inicio.strftime('%d/%m')} a {fim.strftime('%d/%m/%Y')})"
    else:
        ontem = hoje - timedelta(days=1)
        inicio = fim = ontem
        label = f"Ontem ({ontem.strftime('%d/%m/%Y')})"

    return inicio, fim, label
