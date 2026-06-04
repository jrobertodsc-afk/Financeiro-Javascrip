
@app.post("/api/conciliacao/ofx")
async def api_conciliacao_ofx(file: UploadFile = File(...)):
    """Lê um arquivo OFX, extrai os débitos e faz o cruzamento com as notas pendentes."""
    try:
        import re
        from services.database import _get_local_conn, USE_SUPABASE
        content = await file.read()
        text = content.decode("utf-8", errors="ignore")
        
        # Parse básico de OFX via regex (OFX usa tags SGML sem fechamento estrito às vezes)
        transactions = []
        blocks = re.split(r'<STMTTRN>', text, flags=re.IGNORECASE)[1:]
        
        for b in blocks:
            b = b.split('</STMTTRN>')[0] if '</STMTTRN>' in b.upper() else b
            
            trnamt_m = re.search(r'<TRNAMT>([-\d\.]+)', b, re.IGNORECASE)
            dtposted_m = re.search(r'<DTPOSTED>(\d{8})', b, re.IGNORECASE)
            fitid_m = re.search(r'<FITID>([^<]+)', b, re.IGNORECASE)
            memo_m = re.search(r'<MEMO>([^<\r\n]+)', b, re.IGNORECASE)
            
            if trnamt_m and dtposted_m:
                amt = float(trnamt_m.group(1))
                if amt < 0: # Apenas saídas de caixa (débitos)
                    dt_raw = dtposted_m.group(1)
                    dt_str = f"{dt_raw[6:8]}/{dt_raw[4:6]}/{dt_raw[0:4]}"
                    transactions.append({
                        "tx_id": fitid_m.group(1).strip() if fitid_m else "OFX",
                        "tx_data": dt_str,
                        "tx_valor": abs(amt),
                        "tx_memo": memo_m.group(1).strip() if memo_m else ""
                    })
                    
        # Buscar notas pendentes e aprovadas
        conn = _get_local_conn()
        notas = [dict(r) for r in conn.execute("SELECT * FROM notas WHERE status IN ('PENDENTE', 'APROVADA')").fetchall()]
        
        matched = []
        unmatched = []
        
        for tx in transactions:
            found_nota = None
            for n in notas:
                val = float(n.get("valor_bruto", 0) or 0)
                # Aceita diferença de até 2 centavos
                if abs(val - tx["tx_valor"]) <= 0.02:
                    found_nota = n
                    break
                    
            if found_nota:
                if USE_SUPABASE:
                    from supabase import create_client
                    import config
                    sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                    sb.table("notas").update({"status": "PAGO"}).eq("id", found_nota["id"]).execute()
                
                conn.execute("UPDATE notas SET status='PAGO' WHERE id=?", (found_nota["id"],))
                notas.remove(found_nota) # Evita associar a mesma nota a duas transações do mesmo valor
                
                matched.append({
                    "tx_id": tx["tx_id"],
                    "tx_data": tx["tx_data"],
                    "tx_valor": tx["tx_valor"],
                    "nota_id": found_nota["id"],
                    "nota_fornecedor": found_nota.get("fornecedor", "Desconhecido")
                })
            else:
                unmatched.append(tx)
                
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "matched": matched,
            "unmatched": unmatched
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
