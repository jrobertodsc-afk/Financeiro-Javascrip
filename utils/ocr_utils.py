"""
utils/ocr_utils.py — Extração de texto e OCR de comprovantes PDF.

Usa PyMuPDF (fitz) como primária (melhor qualidade) com fallback para pypdf.
Para PDFs de imagem escaneada usa pytesseract se disponível.
"""
from __future__ import annotations

import re
import os
from typing import Optional


def extrair_texto_pdf(caminho: str, pagina: int = 0) -> str:
    """
    Extrai o texto de um PDF usando PyMuPDF (fitz) ou pypdf como fallback.

    Args:
        caminho: caminho absoluto do arquivo PDF
        pagina: índice da página (0 = primeira). Se -1, extrai todas.

    Returns:
        Texto extraído como string (vazia em caso de falha).
    """
    if not caminho or not os.path.exists(caminho):
        return ""

    # ── Tentativa 1: PyMuPDF (fitz) ──────────────────────────────────────────
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(caminho)

        if pagina == -1:
            # Todas as páginas
            texto = ""
            for pg in doc:
                texto += pg.get_text("text") + "\n"
        else:
            idx = min(pagina, len(doc) - 1)
            texto = doc[idx].get_text("text")

        doc.close()

        if texto.strip():
            return texto

        # PDF de imagem — tenta OCR
        return _ocr_com_tesseract(caminho, pagina)

    except ImportError:
        pass
    except Exception as e:
        print(f"[extrair_texto_pdf] fitz erro: {e}")

    # ── Tentativa 2: pypdf ────────────────────────────────────────────────────
    try:
        import pypdf
        reader = pypdf.PdfReader(caminho)
        if pagina == -1:
            texto = ""
            for pg in reader.pages:
                texto += (pg.extract_text() or "") + "\n"
        else:
            idx = min(pagina, len(reader.pages) - 1)
            texto = reader.pages[idx].extract_text() or ""

        if texto.strip():
            return texto

        return _ocr_com_tesseract(caminho, pagina)

    except ImportError:
        pass
    except Exception as e:
        print(f"[extrair_texto_pdf] pypdf erro: {e}")

    # ── Tentativa 3: PyPDF2 (legado) ──────────────────────────────────────────
    try:
        import PyPDF2
        with open(caminho, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            if pagina == -1:
                return "".join(
                    pg.extract_text() or "" for pg in reader.pages
                )
            idx = min(pagina, len(reader.pages) - 1)
            return reader.pages[idx].extract_text() or ""
    except Exception:
        pass

    return ""


def _ocr_com_tesseract(caminho: str, pagina: int = 0) -> str:
    """
    Tenta fazer OCR em um PDF de imagem usando pytesseract + PIL.
    Retorna string vazia se tesseract não estiver instalado.
    """
    try:
        import fitz
        import pytesseract
        from PIL import Image
        import io

        doc = fitz.open(caminho)
        paginas = [pagina] if pagina >= 0 else range(len(doc))

        textos = []
        for pg_idx in paginas:
            if pg_idx >= len(doc):
                break
            pg = doc[pg_idx]
            # Renderiza em alta resolução para melhor OCR
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom = ~144 DPI
            pix = pg.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            # Tesseract com configuração otimizada para documentos financeiros
            config = "--oem 3 --psm 6 -l por"
            texto = pytesseract.image_to_string(img, config=config)
            textos.append(texto)

        doc.close()
        return "\n".join(textos)

    except ImportError:
        return ""  # tesseract/fitz não disponível
    except Exception as e:
        print(f"[_ocr_com_tesseract] Erro: {e}")
        return ""


def processar_ocr_comprovante(caminho: str) -> dict:
    """
    Extrai e interpreta dados de um comprovante de pagamento PDF.

    Retorna dicionário com:
        - empresa:    "LALUA" | "SOLAR" | "BOAH" | ""
        - tipo:       "PIX" | "TED" | "BOLETO" | "GNRE" | "DARF" | ...
        - favorecido: nome do beneficiário/fornecedor
        - valor:      float
        - data:       "DD/MM/YYYY" ou ""
        - categoria:  classificação contábil sugerida
        - detalhes:   informações adicionais
        - texto_raw:  texto bruto extraído
    """
    texto = extrair_texto_pdf(caminho, pagina=-1)

    result = {
        "empresa":    "",
        "tipo":       "COMPROVANTE",
        "favorecido": "",
        "valor":      0.0,
        "data":       "",
        "categoria":  "A CLASSIFICAR",
        "detalhes":   "",
        "texto_raw":  texto,
    }

    if not texto:
        return result

    texto_upper = " ".join(texto.upper().split())

    # ── Empresa ───────────────────────────────────────────────────────────────
    if any(x in texto_upper for x in ["LALUA", "L A L U A", "98775", "10.436.619"]):
        result["empresa"] = "LALUA"
    elif any(x in texto_upper for x in ["SOLAR", "S O L A R"]):
        result["empresa"] = "SOLAR"
    elif "BOAH" in texto_upper:
        result["empresa"] = "BOAH"

    # ── Valor ─────────────────────────────────────────────────────────────────
    # Padrão: R$ 1.234,56 ou 1.234,56 precedido de palavra-chave
    m_valor = re.search(
        r"(?:valor|total|pagamento|pago|montante)[^\d]{0,20}R?\$?\s*([\d.,]{3,})",
        texto, re.IGNORECASE
    )
    if not m_valor:
        # Pega o maior valor encontrado no texto como fallback
        valores = re.findall(r"R?\$\s*([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})", texto)
        if valores:
            vals_float = []
            for v in valores:
                try:
                    vals_float.append(float(v.replace(".", "").replace(",", ".")))
                except ValueError:
                    pass
            if vals_float:
                result["valor"] = max(vals_float)
    else:
        val_str = m_valor.group(1).replace(".", "").replace(",", ".")
        try:
            result["valor"] = float(val_str)
        except ValueError:
            pass

    # ── Data ─────────────────────────────────────────────────────────────────
    m_data = re.search(
        r"(?:pagamento|data|efetuad[ao]|vencimento|emiss[aã]o)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        texto, re.IGNORECASE
    )
    if not m_data:
        m_data = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
    if m_data:
        result["data"] = m_data.group(1)

    # ── Tipo e Categoria ──────────────────────────────────────────────────────
    if any(x in texto_upper for x in ["GNRE", "GUIA NACIONAL DE RECOLHIMENTO"]):
        result["tipo"]      = "GNRE"
        result["categoria"] = "22309 - GNRE"
        m_uf = re.search(r"\bUF\b\s*[:\-]?\s*([A-Z]{2})\b", texto_upper)
        if m_uf:
            result["detalhes"] = m_uf.group(1)

    elif any(x in texto_upper for x in ["DARF", "SIMPLES NACIONAL", "RECEITA FEDERAL"]):
        result["tipo"]      = "DARF"
        result["categoria"] = "22308 - Simples Nacional"

    elif any(x in texto_upper for x in ["GPS", "INSS", "PREVIDÊNCIA"]):
        result["tipo"]      = "GPS"
        result["categoria"] = "12205 - INSS"

    elif "FGTS" in texto_upper:
        result["tipo"]      = "FGTS"
        result["categoria"] = "12205 - FGTS"

    elif any(x in texto_upper for x in ["BOLETO", "COBRANÇA", "BANCO"]):
        result["tipo"] = "BOLETO"

    elif "PIX" in texto_upper:
        result["tipo"] = "PIX"

    elif "TED" in texto_upper:
        result["tipo"] = "TED"

    elif "DOC" in texto_upper:
        result["tipo"] = "DOC"

    # ── Favorecido ────────────────────────────────────────────────────────────
    m_fav = re.search(
        r"(?:favorecido|benefici[aá]rio|raz[aã]o social|nome do recebedor|recebedor)"
        r"\s*[:\-]?\s*([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][^\n\r\d]{3,60})",
        texto, re.IGNORECASE
    )
    if m_fav:
        nome = m_fav.group(1).strip()
        # Remove labels residuais
        nome = re.split(r"\b(CNPJ|CPF|AGÊNCIA|BANCO|DATA|VALOR)\b", nome, flags=re.I)[0]
        nome = re.sub(r"[\s\-_:]+$", "", nome).strip()
        result["favorecido"] = nome.upper()
        if not result["detalhes"]:
            result["detalhes"] = result["favorecido"]

    # ── Classificação automática com base no favorecido ───────────────────────
    if result["favorecido"] and result["categoria"] == "A CLASSIFICAR":
        try:
            from utils.data_processing import auto_classificar
            _, cat = auto_classificar(result["favorecido"], result["valor"])
            if cat and cat != "A CLASSIFICAR":
                result["categoria"] = cat
        except Exception:
            pass

    return result


def contar_paginas_pdf(caminho: str) -> int:
    """Retorna o número de páginas do PDF."""
    try:
        import fitz
        doc = fitz.open(caminho)
        n = len(doc)
        doc.close()
        return n
    except Exception:
        pass

    try:
        import pypdf
        return len(pypdf.PdfReader(caminho).pages)
    except Exception:
        return 1


def separar_pdf_paginas(caminho: str, pasta_destino: Optional[str] = None) -> list[str]:
    """
    Separa um PDF multi-página em arquivos individuais.

    Retorna lista de caminhos dos arquivos gerados.
    Se o PDF tiver apenas 1 página, retorna [caminho] sem modificação.
    """
    import time

    n = contar_paginas_pdf(caminho)
    if n <= 1:
        return [caminho]

    base_dir = pasta_destino or os.path.join(
        os.path.dirname(caminho), f"SPLIT_{int(time.time())}"
    )
    os.makedirs(base_dir, exist_ok=True)

    nome_base = os.path.splitext(os.path.basename(caminho))[0]
    gerados = []

    # Tenta com fitz primeiro (mais rápido)
    try:
        import fitz
        doc = fitz.open(caminho)
        for i in range(n):
            pg_doc = fitz.open()
            pg_doc.insert_pdf(doc, from_page=i, to_page=i)
            out_path = os.path.join(base_dir, f"{nome_base}_pg{i+1:03d}.pdf")
            pg_doc.save(out_path)
            pg_doc.close()
            gerados.append(out_path)
        doc.close()
        return gerados
    except ImportError:
        pass

    # Fallback: pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(caminho)
        for i, page in enumerate(reader.pages):
            writer = pypdf.PdfWriter()
            writer.add_page(page)
            out_path = os.path.join(base_dir, f"{nome_base}_pg{i+1:03d}.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)
            gerados.append(out_path)
        return gerados
    except Exception as e:
        print(f"[separar_pdf_paginas] Erro: {e}")
        return [caminho]
