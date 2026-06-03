import xml.etree.ElementTree as ET

def parse_nfe_for_ui(path: str) -> dict:
    """Lê XML de NF-e e extrai um dicionário estruturado para a UI."""
    tree = ET.parse(path)
    root = tree.getroot()

    def _strip_ns(tag):
        return tag.split('}')[1] if '}' in tag else tag

    def _find(root, *tags):
        for tag in tags:
            found = None
            for el in root.iter():
                if _strip_ns(el.tag) == tag:
                    found = el
                    break
            if found is None:
                return None
            root = found
        return root

    def _val(root, *tags):
        el = _find(root, *tags)
        return el.text.strip() if el is not None and el.text else ""

    # Emitente
    cnpj = _val(root, "emit", "CNPJ")
    razao = _val(root, "emit", "xNome")
    fantasia = _val(root, "emit", "xFant")
    num_nf = _val(root, "ide", "nNF")

    # Data Emissão
    dt_raw = _val(root, "ide", "dhEmi") or _val(root, "ide", "dEmi")
    dt_emissao = ""
    if dt_raw:
        try:
            from datetime import datetime as dt_cls
            dt_obj = dt_cls.fromisoformat(dt_raw[:10])
            dt_emissao = dt_obj.strftime("%d/%m/%Y")
        except:
            dt_emissao = dt_raw[:10]

    # Valores e Impostos
    vNF_val = (_val(root, "total", "ICMSTot", "vNF") or 
               _val(root, "retConsSitNFe", "vNF") or
               _val(root, "infProt", "vNF") or "0")
    vNF = float(vNF_val)
    
    vICMS = float(_val(root, "total", "ICMSTot", "vICMS") or 0)
    vPIS = float(_val(root, "total", "ICMSTot", "vPIS") or 0)
    vCOFINS = float(_val(root, "total", "ICMSTot", "vCOFINS") or 0)
    vIR = float(_val(root, "total", "ICMSTot", "vIR") or 0)
    vINSS = float(_val(root, "total", "ICMSTot", "vINSS") or 0)
    vISS = float(_val(root, "total", "ICMSTot", "vISS") or 0)
    vIBS = float(_val(root, "total", "IBSCBSTot", "vIBS") or 0)
    vCBS = float(_val(root, "total", "IBSCBSTot", "vCBS") or 0)
    vIBSUF = float(_val(root, "total", "IBSCBSTot", "gIBS", "gIBSUF", "vIBSUF") or 0)
    vICMSUFDest = float(_val(root, "total", "ICMSTot", "vICMSUFDest") or 0)
    vFCPUFDest = float(_val(root, "total", "ICMSTot", "vFCPUFDest") or 0)
    
    valor_difal_final = vICMSUFDest if vICMSUFDest > 0 else vIBSUF

    # Natureza e Referência
    finNFe = _val(root, "ide", "finNFe")
    chave_ref = ""
    if finNFe == "4":
        for el in root.iter():
            if _strip_ns(el.tag) == "refNFe":
                chave_ref = el.text or ""
                break

    # Parcelas
    parcelas = []
    for dup in root.iter():
        if _strip_ns(dup.tag) == "dup":
            n_dup, d_venc, v_dup = "", "", 0.0
            for child in dup:
                t = _strip_ns(child.tag)
                if t == "nDup": n_dup = child.text or ""
                if t == "dVenc":
                    try:
                        from datetime import datetime as dt_cls
                        d_venc = dt_cls.fromisoformat(child.text[:10]).strftime("%d/%m/%Y")
                    except:
                        d_venc = child.text or ""
                if t == "vDup":
                    try: v_dup = float(child.text or 0)
                    except: v_dup = 0.0
            parcelas.append({"n_dup": n_dup, "d_venc": d_venc, "v_dup": v_dup})

    # Itens
    itens = []
    for det in root.iter():
        if _strip_ns(det.tag) == "det":
            prod_desc, v_total_prod = "", 0.0
            for sub in det.iter():
                tag_sub = _strip_ns(sub.tag)
                if tag_sub == "xProd": prod_desc = sub.text or ""
                if tag_sub == "vProd": 
                    try: v_total_prod = float(sub.text or 0)
                    except: v_total_prod = 0.0
            if prod_desc:
                itens.append({"desc": prod_desc, "valor": v_total_prod})

    return {
        "emitente": {
            "cnpj": cnpj,
            "razao": razao,
            "fantasia": fantasia
        },
        "identificacao": {
            "num_nf": num_nf,
            "dt_emissao": dt_emissao,
            "finNFe": finNFe,
            "chave_ref": chave_ref
        },
        "valores": {
            "vNF": vNF,
            "vICMS": vICMS,
            "vPIS": vPIS,
            "vCOFINS": vCOFINS,
            "vIR": vIR,
            "vINSS": vINSS,
            "vISS": vISS,
            "vIBS": vIBS,
            "vCBS": vCBS,
            "difal": valor_difal_final,
            "fcp": vFCPUFDest
        },
        "parcelas": parcelas,
        "itens": itens
    }
