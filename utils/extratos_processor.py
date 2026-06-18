import os
import xlrd
from datetime import datetime
from utils.data_processing import auto_classificar
from services.logger_service import logger

def ler_extrato_pdf(caminho):
    """Stub para leitura de extrato PDF."""
    return {}, "Período não identificado"

def ler_getnet_excel(caminho):
    """Stub para leitura de excel Getnet."""
    return []

def ler_itau_pagamentos(caminho):
    """Lê pagamentos do Excel (.xls ou .xlsx) do Itaú de forma robusta."""
    pagamentos = []
    empresa_detectada = "LALUA"
    is_xlsx = caminho.lower().endswith(".xlsx")

    if is_xlsx:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(caminho, data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
        except Exception as e:
            logger.error(f"Erro ao abrir XLSX: {e}")
            return []

        if not rows:
            return []

        nrows = len(rows)

        # 1. Identifica a empresa
        for r in range(min(nrows, 20)):
            row_vals = [str(x) for x in rows[r] if x is not None]
            txt = " ".join(row_vals).upper()
            if "SOLAR" in txt:
                empresa_detectada = "SOLAR"
                break
            elif "LALUA" in txt:
                empresa_detectada = "LALUA"
                break

        # 2. Busca o cabeçalho e define mapeamento
        header_idx = -1
        col_map = {
            "nome": 0,
            "cnpj": 1,
            "tipo": 2,
            "data": 4,
            "valor": 5,
            "status": 6
        }

        for r in range(nrows):
            row_vals = [str(c).strip().lower() if c is not None else "" for c in rows[r]]
            if any("favorecido" in v or "benefici" in v or "recebedor" in v for v in row_vals):
                header_idx = r
                # Tenta mapear dinamicamente
                for idx, val in enumerate(row_vals):
                    if "favorecido" in val or "benefici" in val or "recebedor" in val or val == "nome":
                        col_map["nome"] = idx
                    elif "cnpj" in val or "cpf" in val or "documento" in val:
                        col_map["cnpj"] = idx
                    elif "tipo" in val or "forma" in val:
                        col_map["tipo"] = idx
                    elif "data" in val or "pgto" in val:
                        col_map["data"] = idx
                    elif "valor" in val:
                        col_map["valor"] = idx
                    elif "status" in val or "situação" in val or "situacao" in val:
                        col_map["status"] = idx
                break

        if header_idx == -1:
            wb.close()
            return []

        # 3. Processa as linhas
        for r in range(header_idx + 1, nrows):
            row = rows[r]
            if not row or len(row) <= col_map["nome"]:
                continue

            val_nome = row[col_map["nome"]]
            if val_nome is None or str(val_nome).strip().lower() == "" or str(val_nome).strip().lower() == "total:":
                continue

            try:
                nome = str(val_nome).strip()

                # CNPJ
                cnpj = ""
                if col_map["cnpj"] < len(row) and row[col_map["cnpj"]] is not None:
                    cnpj = str(row[col_map["cnpj"]]).strip()

                # Tipo
                tipo = ""
                if col_map["tipo"] < len(row) and row[col_map["tipo"]] is not None:
                    tipo = str(row[col_map["tipo"]]).strip()

                # Data
                data_str = ""
                data_obj = None
                if col_map["data"] < len(row) and row[col_map["data"]] is not None:
                    data_val = row[col_map["data"]]
                    if isinstance(data_val, datetime):
                        data_obj = data_val
                        data_str = data_val.strftime("%d/%m/%Y")
                    else:
                        data_str = str(data_val).strip()
                        try:
                            data_obj = datetime.strptime(data_str, "%d/%m/%Y")
                        except:
                            try:
                                # Tenta converter se for datetime em outro formato
                                data_obj = datetime.fromisoformat(data_str.split()[0])
                                data_str = data_obj.strftime("%d/%m/%Y")
                            except:
                                pass

                # Valor
                valor = 0.0
                if col_map["valor"] < len(row) and row[col_map["valor"]] is not None:
                    try:
                        valor = float(row[col_map["valor"]])
                    except:
                        pass

                # Status
                status = "Aprovada"
                if col_map["status"] < len(row) and row[col_map["status"]] is not None:
                    status = str(row[col_map["status"]]).strip()

                resp, cat, desc = auto_classificar(nome, valor, cnpj)

                dic = {
                    "nome": nome,
                    "favorecido": nome,
                    "cnpj": cnpj,
                    "tipo": tipo,
                    "data": data_str,
                    "data_obj": data_obj,
                    "valor": valor,
                    "status": status,
                    "responsavel": resp,
                    "categoria": cat,
                    "empresa": empresa_detectada,
                    "observacao": f"Importado de {os.path.basename(caminho)}",
                    "manual": False
                }
                if desc:
                    dic["descricao"] = desc

                pagamentos.append(dic)
            except Exception as ex:
                logger.error(f"Erro ao processar linha {r} do XLSX: {ex}")
                continue

        wb.close()

    else:
        # Modo clássico XLS
        try:
            workbook = xlrd.open_workbook(caminho)
            sheet = workbook.sheet_by_index(0)
        except Exception as e:
            logger.error(f"Erro ao abrir XLS: {e}")
            return []

        nrows = sheet.nrows

        # 1. Identifica a empresa
        for r in range(min(nrows, 20)):
            txt = " ".join([str(x) for x in sheet.row_values(r)]).upper()
            if "SOLAR" in txt:
                empresa_detectada = "SOLAR"
                break
            elif "LALUA" in txt:
                empresa_detectada = "LALUA"
                break

        # 2. Busca o cabeçalho e define mapeamento
        header_idx = -1
        col_map = {
            "nome": 0,
            "cnpj": 1,
            "tipo": 2,
            "data": 4,
            "valor": 5,
            "status": 6
        }

        for r in range(nrows):
            row_vals = [str(c).strip().lower() for c in sheet.row_values(r)]
            if any("favorecido" in v or "benefici" in v or "recebedor" in v for v in row_vals):
                header_idx = r
                # Tenta mapear dinamicamente
                for idx, val in enumerate(row_vals):
                    if "favorecido" in val or "benefici" in val or "recebedor" in val or val == "nome":
                        col_map["nome"] = idx
                    elif "cnpj" in val or "cpf" in val or "documento" in val:
                        col_map["cnpj"] = idx
                    elif "tipo" in val or "forma" in val:
                        col_map["tipo"] = idx
                    elif "data" in val or "pgto" in val:
                        col_map["data"] = idx
                    elif "valor" in val:
                        col_map["valor"] = idx
                    elif "status" in val or "situação" in val or "situacao" in val:
                        col_map["status"] = idx
                break

        if header_idx == -1:
            return []

        # 3. Processa as linhas
        for r in range(header_idx + 1, nrows):
            row = sheet.row_values(r)
            if not row or len(row) <= col_map["nome"]:
                continue

            val_nome = row[col_map["nome"]]
            if val_nome is None or str(val_nome).strip().lower() == "" or str(val_nome).strip().lower() == "total:":
                continue

            try:
                nome = str(val_nome).strip()

                cnpj = ""
                if col_map["cnpj"] < len(row) and row[col_map["cnpj"]] is not None:
                    cnpj = str(row[col_map["cnpj"]]).strip()

                tipo = ""
                if col_map["tipo"] < len(row) and row[col_map["tipo"]] is not None:
                    tipo = str(row[col_map["tipo"]]).strip()

                data_str = ""
                data_obj = None
                if col_map["data"] < len(row) and row[col_map["data"]] is not None:
                    data_val = row[col_map["data"]]
                    if isinstance(data_val, datetime):
                        data_obj = data_val
                        data_str = data_val.strftime("%d/%m/%Y")
                    elif isinstance(data_val, float):
                        try:
                            tuple_date = xlrd.xldate_as_tuple(data_val, workbook.datemode)
                            data_obj = datetime(*tuple_date[:6])
                            data_str = data_obj.strftime("%d/%m/%Y")
                        except:
                            data_str = str(data_val).strip()
                    else:
                        data_str = str(data_val).strip()
                        if data_str:
                            try:
                                data_obj = datetime.strptime(data_str, "%d/%m/%Y")
                            except:
                                try:
                                    data_obj = datetime.fromisoformat(data_str.split()[0])
                                    data_str = data_obj.strftime("%d/%m/%Y")
                                except:
                                    pass

                valor = 0.0
                if col_map["valor"] < len(row) and row[col_map["valor"]] is not None:
                    try:
                        valor = float(row[col_map["valor"]])
                    except:
                        pass

                status = "Aprovada"
                if col_map["status"] < len(row) and row[col_map["status"]] is not None:
                    status = str(row[col_map["status"]]).strip()

                resp, cat, desc = auto_classificar(nome, valor, cnpj)

                dic = {
                    "nome": nome,
                    "favorecido": nome,
                    "cnpj": cnpj,
                    "tipo": tipo,
                    "data": data_str,
                    "data_obj": data_obj,
                    "valor": valor,
                    "status": status,
                    "responsavel": resp,
                    "categoria": cat,
                    "empresa": empresa_detectada,
                    "observacao": f"Importado de {os.path.basename(caminho)}",
                    "manual": False
                }
                if desc:
                    dic["descricao"] = desc

                pagamentos.append(dic)
            except Exception as ex:
                logger.error(f"Erro ao processar linha {r} do XLS: {ex}")
                continue

    return pagamentos

def ler_itau_folha(caminho):
    """Lê folha de pagamentos do Itaú (simplificado)."""
    if caminho.lower().endswith((".xls", ".xlsx")):
        itens = ler_itau_pagamentos(caminho)
        for i in itens:
            i["categoria"] = "RH - SALARIOS"
        return itens
    return []
