"""
routers/relatorios.py — Endpoints de relatórios e BI do ERP.

Inclui:
- /api/relatorios/avancado    → Relatório filtrado por data/categoria/fornecedor
- /api/relatorios/tributos    → Tributos retidos por período
- /api/relatorios/rateio      → Centro de custo (rateio)
- /api/relatorios/analise_fiscal → Guias de imposto geradas
- /api/relatorios/dre         → DRE Gerencial (NOVO — orçado vs realizado)
- /api/relatorios/fluxo_caixa → Fluxo de caixa projetado 90 dias (NOVO)
"""
import os
import sys
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.database import listar_notas, _get_local_conn

router = APIRouter(prefix="/api/relatorios", tags=["Relatórios"])


@router.get("/avancado")
def relatorios_avancado(
    dt_inicio: Optional[str] = None,
    dt_fim: Optional[str] = None,
    tipo_data: Optional[str] = "vencimento",
    status: Optional[str] = None,
    empresa: Optional[str] = None,
    fornecedor: Optional[str] = None,
    categoria: Optional[str] = None,
):
    try:
        notas = listar_notas(status=status, empresa=empresa)
        filtradas = []
        for n in notas:
            if fornecedor and fornecedor.lower() not in (n.get("fornecedor") or "").lower():
                continue
            if categoria and categoria.lower() not in (n.get("categoria") or "").lower():
                continue
            if dt_inicio and dt_fim:
                campo = "dt_vencimento" if tipo_data == "vencimento" else "dt_emissao"
                data_str = n.get(campo)
                if data_str:
                    try:
                        d = datetime.strptime(data_str, "%d/%m/%Y")
                        d_ini = datetime.strptime(dt_inicio, "%Y-%m-%d")
                        d_fim = datetime.strptime(dt_fim, "%Y-%m-%d")
                        if not (d_ini <= d <= d_fim):
                            continue
                    except Exception:
                        pass
            filtradas.append(n)
        return {"success": True, "notas": filtradas}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/dre")
def relatorios_dre(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    empresa: Optional[str] = None,
):
    """
    DRE Gerencial — Despesas realizadas por categoria vs orçamento.
    Retorna: categoria, total_realizado, orcamento (se cadastrado), variacao, pct_variacao
    """
    try:
        agora = datetime.now()
        mes = mes or agora.month
        ano = ano or agora.year

        notas = listar_notas(empresa=empresa)

        # Agrupa por categoria apenas notas do mês/ano e status PAGO
        por_categoria = defaultdict(float)
        for n in notas:
            if n.get("status") not in ("PAGO", "PAGA"):
                continue
            data_str = n.get("dt_vencimento") or n.get("dt_emissao")
            if not data_str:
                continue
            try:
                d = datetime.strptime(data_str, "%d/%m/%Y")
                if d.month != mes or d.year != ano:
                    continue
            except Exception:
                continue
            cat = n.get("categoria") or "Sem Categoria"
            por_categoria[cat] += float(n.get("valor_bruto") or 0)

        # Busca orçamentos cadastrados
        orcamentos = {}
        try:
            conn = _get_local_conn()
            rows = conn.execute(
                "SELECT categoria, limite FROM orcamentos WHERE mes=? AND ano=?", (mes, ano)
            ).fetchall()
            conn.close()
            for r in rows:
                orcamentos[r["categoria"]] = float(r["limite"] or 0)
        except Exception:
            pass

        # Monta DRE
        dre = []
        todas_categorias = set(list(por_categoria.keys()) + list(orcamentos.keys()))
        for cat in sorted(todas_categorias):
            realizado = por_categoria.get(cat, 0)
            orcado = orcamentos.get(cat, 0)
            variacao = realizado - orcado if orcado > 0 else 0
            pct = round((variacao / orcado * 100), 1) if orcado > 0 else None
            dre.append({
                "categoria": cat,
                "realizado": round(realizado, 2),
                "orcado": round(orcado, 2),
                "variacao": round(variacao, 2),
                "pct_variacao": pct,
                "status": "acima" if variacao > 0 else "dentro" if variacao <= 0 else "sem_orcamento",
            })

        # Totais
        total_realizado = sum(d["realizado"] for d in dre)
        total_orcado = sum(d["orcado"] for d in dre)

        return {
            "success": True,
            "mes": mes,
            "ano": ano,
            "dre": dre,
            "totais": {
                "realizado": round(total_realizado, 2),
                "orcado": round(total_orcado, 2),
                "variacao": round(total_realizado - total_orcado, 2),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/fluxo_caixa")
def relatorios_fluxo_caixa(
    dias: int = 90,
    empresa: Optional[str] = None,
):
    """
    Fluxo de Caixa Projetado — próximos N dias.
    Agrupa despesas PENDENTES por data de vencimento, exibindo saldo acumulado projetado.
    """
    try:
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        limite = hoje + timedelta(days=dias)

        notas = listar_notas(empresa=empresa)

        # Agrupa por dia de vencimento
        por_dia: dict[str, float] = defaultdict(float)
        for n in notas:
            if n.get("status") in ("PAGO", "PAGA", "CANCELADO", "CANCELADA"):
                continue
            data_str = n.get("dt_vencimento")
            if not data_str:
                continue
            try:
                d = datetime.strptime(data_str, "%d/%m/%Y")
                if hoje <= d <= limite:
                    por_dia[data_str] += float(n.get("valor_bruto") or 0)
            except Exception:
                continue

        # Ordena por data e calcula saldo acumulado
        fluxo = []
        saldo_acumulado = 0.0
        datas_ordenadas = sorted(por_dia.keys(), key=lambda x: datetime.strptime(x, "%d/%m/%Y"))
        for data_str in datas_ordenadas:
            saida = por_dia[data_str]
            saldo_acumulado -= saida
            fluxo.append({
                "data": data_str,
                "saida": round(saida, 2),
                "saldo_acumulado": round(saldo_acumulado, 2),
                "alerta": saldo_acumulado < 0,
            })

        total_previsto = sum(v for v in por_dia.values())

        return {
            "success": True,
            "dias": dias,
            "fluxo": fluxo,
            "total_saidas_previstas": round(total_previsto, 2),
            "saldo_final_projetado": round(saldo_acumulado, 2),
            "tem_saldo_negativo": saldo_acumulado < 0,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/analise_fiscal")
def relatorios_analise_fiscal(mes: str = None, ano: str = None):
    try:
        todas_notas = listar_notas()
        guias = [n for n in todas_notas if n.get("chave_ref") and "Imposto" in n.get("categoria", "")]
        if mes and ano:
            guias = [n for n in guias if n.get("dt_emissao") and n["dt_emissao"][3:] == f"{mes.zfill(2)}/{ano}"]
        return {"success": True, "relatorio": guias, "total_impostos": sum(float(g.get("valor_bruto", 0) or 0) for g in guias)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/tributos")
def relatorios_tributos(dt_inicio: Optional[str] = None, dt_fim: Optional[str] = None):
    try:
        import config
        from services.database import USE_SUPABASE
        notas = listar_notas()
        impostos_map = {}
        if not USE_SUPABASE:
            conn = _get_local_conn()
            todos_impostos = [dict(r) for r in conn.execute("SELECT * FROM nota_impostos").fetchall()]
            conn.close()
        else:
            try:
                from supabase import create_client
                supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                todos_impostos = supabase.table("nota_impostos").select("*").execute().data
            except Exception:
                conn = _get_local_conn()
                todos_impostos = [dict(r) for r in conn.execute("SELECT * FROM nota_impostos").fetchall()]
                conn.close()

        for imp in todos_impostos:
            impostos_map.setdefault(imp["nota_id"], []).append(imp)

        tributos_retorno = []
        for n in notas:
            if dt_inicio and dt_fim:
                data_str = n.get("dt_vencimento")
                if data_str:
                    try:
                        d = datetime.strptime(data_str, "%d/%m/%Y")
                        d_ini = datetime.strptime(dt_inicio, "%Y-%m-%d")
                        d_fim = datetime.strptime(dt_fim, "%Y-%m-%d")
                        if not (d_ini <= d <= d_fim):
                            continue
                    except Exception:
                        pass
            for imp in impostos_map.get(n["id"], []):
                tributos_retorno.append({
                    "nota_id": n["id"],
                    "fornecedor_origem": n.get("fornecedor"),
                    "numero_nf": n.get("numero_nf"),
                    "dt_emissao": n.get("dt_emissao"),
                    "dt_vencimento": n.get("dt_vencimento"),
                    "imposto_tipo": imp.get("tipo"),
                    "imposto_valor": imp.get("valor"),
                    "imposto_vencimento": imp.get("dt_venc_imp") or n.get("dt_vencimento"),
                    "status_pagamento": imp.get("status") or n.get("status"),
                })

        return {"success": True, "tributos": tributos_retorno}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/rateio")
def relatorios_rateio(empresa: Optional[str] = None):
    try:
        conn = _get_local_conn()
        conn.row_factory = __import__("sqlite3").Row
        cursor = conn.cursor()
        sql = """
            SELECT r.filial as categoria, SUM(r.valor) as total
            FROM nota_rateio r
            JOIN notas n ON r.nota_id = n.id
            WHERE 1=1
        """
        args = []
        if empresa:
            sql += " AND n.empresa = ?"
            args.append(empresa)
        sql += " GROUP BY r.categoria ORDER BY total DESC"
        cursor.execute(sql, args)
        rows = cursor.fetchall()
        resultado = [{"centro_custo": r["categoria"] or "Geral", "total": r["total"]} for r in rows]
        conn.close()
        return {"success": True, "rateio": resultado}
    except Exception as e:
        return {"success": False, "error": str(e), "rateio": []}
