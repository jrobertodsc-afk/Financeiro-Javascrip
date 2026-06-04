
@app.get("/api/relatorios/avancado")
def api_relatorios_avancado(
    dt_inicio: Optional[str] = None, 
    dt_fim: Optional[str] = None, 
    tipo_data: Optional[str] = "vencimento", 
    status: Optional[str] = None, 
    empresa: Optional[str] = None,
    fornecedor: Optional[str] = None,
    categoria: Optional[str] = None
):
    try:
        from services.database import _get_local_conn, USE_SUPABASE
        import config
        from datetime import datetime
        
        # 1. Obter base de notas
        notas = listar_notas(status=status, empresa=empresa)
        
        # 2. Filtrar localmente no python para suportar ambos os bancos e filtros complexos
        filtradas = []
        for n in notas:
            # Filtro fornecedor
            if fornecedor and fornecedor.lower() not in (n.get("fornecedor") or "").lower():
                continue
                
            # Filtro categoria
            if categoria and categoria.lower() not in (n.get("categoria") or "").lower():
                continue
                
            # Filtro data
            if dt_inicio and dt_fim:
                data_campo = n.get("dt_vencimento") if tipo_data == "vencimento" else n.get("dt_emissao")
                if data_campo:
                    try:
                        d_obj = datetime.strptime(data_campo, "%d/%m/%Y")
                        d_ini = datetime.strptime(dt_inicio, "%Y-%m-%d")
                        d_fim = datetime.strptime(dt_fim, "%Y-%m-%d")
                        if not (d_ini <= d_obj <= d_fim):
                            continue
                    except:
                        pass
                        
            filtradas.append(n)
            
        return {"success": True, "notas": filtradas}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/relatorios/tributos")
def api_relatorios_tributos(
    dt_inicio: Optional[str] = None, 
    dt_fim: Optional[str] = None
):
    try:
        from services.database import _get_local_conn, USE_SUPABASE, get_nota_completa
        import config
        from datetime import datetime
        
        notas = listar_notas()
        
        tributos_retorno = []
        for n in notas:
            # Filtrar data
            if dt_inicio and dt_fim:
                data_campo = n.get("dt_vencimento")
                if data_campo:
                    try:
                        d_obj = datetime.strptime(data_campo, "%d/%m/%Y")
                        d_ini = datetime.strptime(dt_inicio, "%Y-%m-%d")
                        d_fim = datetime.strptime(dt_fim, "%Y-%m-%d")
                        if not (d_ini <= d_obj <= d_fim):
                            continue
                    except:
                        pass
                        
            # Se for Supabase, precisariamos puxar os impostos. Como listar_notas no traz impostos, 
            # buscaremos apenas via get_nota_completa se a categoria for "Impostos, Taxas"
            # Ou podemos fazer um query direto
            # Vamos fazer query direto no SQLite local para impostos se no tiver Supabase.
            if not USE_SUPABASE: # Fallback SQLite
                conn = _get_local_conn()
                impostos = [dict(r) for r in conn.execute("SELECT * FROM nota_impostos WHERE nota_id=?", (n["id"],)).fetchall()]
                conn.close()
            else:
                try:
                    from supabase import create_client
                    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                    impostos = supabase.table("nota_impostos").select("*").eq("nota_id", n["id"]).execute().data
                except:
                    conn = _get_local_conn()
                    impostos = [dict(r) for r in conn.execute("SELECT * FROM nota_impostos WHERE nota_id=?", (n["id"],)).fetchall()]
                    conn.close()

            for imp in impostos:
                tributos_retorno.append({
                    "nota_id": n["id"],
                    "fornecedor_origem": n.get("fornecedor"),
                    "numero_nf": n.get("numero_nf"),
                    "dt_emissao": n.get("dt_emissao"),
                    "dt_vencimento": n.get("dt_vencimento"),
                    "imposto_tipo": imp.get("tipo"),
                    "imposto_valor": imp.get("valor"),
                    "imposto_vencimento": imp.get("dt_venc_imp"),
                    "status_pagamento": imp.get("status") or n.get("status")
                })
                
        return {"success": True, "tributos": tributos_retorno}
    except Exception as e:
        return {"success": False, "error": str(e)}

