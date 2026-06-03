from gui.tabs.base import BaseTab
import os
import re
import sys
import shutil
import time
import threading
import sqlite3
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import customtkinter as ctk
from datetime import datetime, date, timedelta
import zipfile
import tempfile
import smtplib

import config
from utils.data_processing import *
from utils.ocr_utils import *
from utils.email_service import *
from utils.file_manager import *
from utils.integrations_utils import *
from utils.extratos_processor import *
from utils.dashboard_service import *
from utils.formatters import *
from services.database import *
from cnab_generator import *
import xml.etree.ElementTree as ET
import xml.etree.ElementTree as ET_SAFE  # Para compatibilidade com o código de consulta
from services.logger_service import logger


class AbaContasPagar(BaseTab):

    # ══════════════════════════════════════════════════════════════════════════
    # ABA CONTAS A PAGAR
    # ══════════════════════════════════════════════════════════════════════════

    def build(self, parent, bg, surface, border, accent, green, yellow, text, muted):
        db_init()
        self._cap_cert_passwords = {}  # Cache de senhas por arquivo {caminho: senha}
        self._cap_editando_id    = None  # ID da nota em edição (None = nova nota)
        self._cap_parc_data      = []    # Inicializa antes de qualquer uso
        # Guarda cores para uso nos métodos
        self._cap_colors = dict(bg="#020617", surface=surface, accent=accent,
                                green=green, yellow=yellow, text=text, muted=muted)

        from gui.design_system import COLORS, FONTS
        self.cap_tabs = ctk.CTkTabview(
            parent, 
            fg_color="transparent",
            segmented_button_fg_color=COLORS["surface"],
            segmented_button_selected_color=COLORS["border_light"],
            segmented_button_selected_hover_color=COLORS["border_light"],
            segmented_button_unselected_color=COLORS["surface"],
            segmented_button_unselected_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=8
        )
        self.cap_tabs.pack(fill="both", expand=True, padx=10, pady=10)

        sub_lista   = self.cap_tabs.add("  📋 LISTA DE NOTAS  ")
        sub_nota    = self.cap_tabs.add("  LANÇAR NOTA  ")
        sub_alertas = self.cap_tabs.add("  🔔 ALERTAS  ")
        sub_prest   = self.cap_tabs.add("  PRESTAÇÃO  ")
        sub_imp     = self.cap_tabs.add("  🏛️ IMPOSTOS  ")
        sub_cnab    = self.cap_tabs.add("  🏦 CNAB 240  ")

        self._cap_build_lista(sub_lista, bg, surface, accent, green, yellow, text, muted, self.cap_tabs)
        self._cap_build_nova_nota(sub_nota, bg, surface, accent, green, yellow, text, muted, self.cap_tabs)
        self._cap_build_alertas(sub_alertas, bg, surface, accent, green, yellow, text, muted)
        self._cap_build_prestacao(sub_prest, bg, surface, accent, green, yellow, text, muted)
        self._cap_build_impostos(sub_imp, bg, surface, accent, green, yellow, text, muted)
        self._cap_build_cnab(sub_cnab, bg, surface, accent, green, yellow, text, muted)

        # Atualiza badge de alertas após build
        self._cap_atualizar_badge_alertas()

    def _cap_select_tab(self, idx):
        tabs = [
            "  📋 LISTA DE NOTAS  ",
            "  LANÇAR NOTA  ",
            "  🔔 ALERTAS  ",
            "  PRESTAÇÃO  ",
            "  🏛️ IMPOSTOS  ",
            "  🏦 CNAB 240  "
        ]
        if 0 <= idx < len(tabs):
            try:
                self.cap_tabs.set(tabs[idx])
            except Exception as e:
                logger.error(f"Erro ao trocar aba: {e}")


    # ── SUB-ABA: LISTA DE NOTAS ───────────────────────────────────────────────
    def _cap_consultar_sefaz(self):
        """Consulta NF-e pela chave de acesso (Refatorado para usar sefaz_service)."""
        from services.sefaz_service import extract_info_from_key, consult_sefaz
        import threading
        import tempfile
        
        chave = self._cap_chave_var.get().strip()
        try:
            info = extract_info_from_key(chave)
        except ValueError as e:
            self._cap_lbl_xml.config(text=f"⚠️ {e}", fg="#fbbf24")
            return
            
        self._cap_lbl_xml.config(
            text=f"Chave válida — NF {info['num_nf']} | {info['uf_sigla']} | {info['mes']}/{info['ano']} | CNPJ {info['cnpj']}",
            fg="#4ade80")

        # Preenche campos básicos
        self._cap_cnpj.delete(0, "end")
        self._cap_cnpj.insert(0, info["cnpj"])
        self._cap_desc.delete(0, "end")
        self._cap_desc.insert(0, f"NF {info['num_nf']}")

        # Tenta auto-completar pelo CNPJ no banco
        f = buscar_fornecedor_por_cnpj(info["cnpj"])
        if f:
            self._cap_forn.delete(0, "end")
            self._cap_forn.insert(0, f["razao_social"])
            if f["categoria"]: self._cap_cat_var.set(f["categoria"])
            if f["responsavel"]: self._cap_resp.set(f["responsavel"])
            if hasattr(self, "_cap_preencher_banco"):
                self._cap_preencher_banco(dict(f))
                
        # ── CAMADA 2: consulta SEFAZ com certificado A1 ──
        pfx_paths = [os.path.join(config.PASTA_ATUAL, fname) for fname in os.listdir(config.PASTA_ATUAL) if fname.lower().endswith(".pfx")]
        
        if not pfx_paths:
            self._cap_lbl_xml.config(
                text="Dados da chave extraídos. Para consultar XML completo, exporte o certificado .pfx para a pasta FINANCEIRO.",
                fg="#fbbf24")
            return

        for p in pfx_paths:
            if p not in self._cap_cert_passwords:
                from tkinter import simpledialog
                s = simpledialog.askstring("Certificado Digital", f"Digite a senha para o certificado:\n{os.path.basename(p)}", show="*", parent=self.root)
                if s: self._cap_cert_passwords[p] = s

        if not self._cap_cert_passwords:
            self._cap_lbl_xml.config(text="⚠️ Nenhuma senha de certificado informada.", fg="#fbbf24")
            return
            
        mapa_senhas = self._cap_cert_passwords.copy()

        def _consultar_bg():
            last_err = "Nenhum certificado funcionou"
            for pfx_path in pfx_paths:
                fname = os.path.basename(pfx_path)
                s_atual = mapa_senhas.get(pfx_path)
                if not s_atual: continue
                
                self.root.after(0, lambda f=fname: self._cap_lbl_xml.config(text=f"⏳ Tentando certificado: {f}...", fg="#38bdf8"))
                
                try:
                    xml_nfe = consult_sefaz(info['chave'], pfx_path, s_atual, info['uf'])
                    
                    tmp_name = f"NF_{info['chave']}.xml"
                    tmp_path = os.path.join(tempfile.gettempdir(), tmp_name)
                    with open(tmp_path, "w", encoding="utf-8") as file:
                        file.write(xml_nfe)
                        
                    self.root.after(0, lambda: (
                        self._cap_importar_xml_path(tmp_path),
                        self._cap_lbl_xml.config(text=f"XML baixado da SEFAZ com sucesso!", fg="#4ade80")
                    ))
                    return
                except Exception as e:
                    last_err = str(e)
                    continue
                    
            self.root.after(0, lambda: self._cap_lbl_xml.config(text=f"⚠️ Falha SEFAZ: {last_err}", fg="#fbbf24"))

        threading.Thread(target=_consultar_bg, daemon=True).start()
        self._cap_lbl_xml.config(text="⏳ Consultando SEFAZ...", fg="#38bdf8")


    def _cap_importar_xml(self):
        """Abre diálogo para selecionar XML e importa."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Selecionar XML da NF-e",
            filetypes=[("XML NF-e", "*.xml"), ("Todos", "*.*")]
        )
        if path:
            self._cap_importar_xml_path(path)


    def _cap_importar_xml_path(self, path):
        """Lê XML de NF-e e preenche o formulário de nova nota (Refatorado)."""
        from services.xml_parser_service import parse_nfe_for_ui
        try:
            data = parse_nfe_for_ui(path)
            
            # Preenche os campos
            self._cap_forn.delete(0, "end")
            self._cap_forn.insert(0, data["emitente"]["razao"])
            
            cnpj = data["emitente"]["cnpj"]
            cnpj_fmt = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}" if cnpj else ""
            if cnpj_fmt:
                self._cap_cnpj.delete(0, "end")
                self._cap_cnpj.insert(0, cnpj_fmt)
                
            finNFe = data["identificacao"]["finNFe"]
            self._cap_natureza_var.set("DEVOLUÇÃO" if finNFe == "4" else "VENDA")
            
            if data["identificacao"]["chave_ref"]:
                self._cap_chave_ref.delete(0, "end")
                self._cap_chave_ref.insert(0, data["identificacao"]["chave_ref"])
                
            num_nf = data["identificacao"]["num_nf"]
            self._cap_desc.delete(0, "end")
            self._cap_desc.insert(0, f"NF {num_nf}" if num_nf else "")
            
            try:
                self._cap_numero_nf.delete(0, "end")
                self._cap_numero_nf.insert(0, num_nf)
            except Exception: pass
            
            if data["identificacao"]["dt_emissao"]:
                self._cap_dt_emissao.delete(0, "end")
                self._cap_dt_emissao.insert(0, data["identificacao"]["dt_emissao"])
                
            self._cap_valor.delete(0, "end")
            self._cap_valor.insert(0, f"{data['valores']['vNF']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            self._cap_difal.delete(0, "end")
            self._cap_difal.insert(0, f"{data['valores']['difal']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            self._cap_fcp.delete(0, "end")
            self._cap_fcp.insert(0, f"{data['valores']['fcp']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            parcelas_xml = data["parcelas"]
            if parcelas_xml:
                self._cap_dt_venc.delete(0, "end")
                self._cap_dt_venc.insert(0, parcelas_xml[0]["d_venc"])
                
            for ir in self._cap_item_rows:
                for w in ir.get("widgets", []): w.destroy()
            self._cap_item_rows = []
            
            itens_xml = data["itens"]
            if itens_xml:
                for it in itens_xml:
                    self._cap_add_item_row(it["desc"], f"{it['valor']:.2f}")
            else:
                self._cap_add_item_row()
                
            self._cap_check_restituicao()
            if hasattr(self, "_cap_update_scroll"):
                self._cap_update_scroll()
                
            v = data["valores"]
            impostos_nf = [
                ("ICMS", 0, v["vICMS"]),
                ("IBS", 0, v["vIBS"]),
                ("CBS", 0, v["vCBS"]),
                ("PIS", config.ALIQUOTAS_PADRAO.get("PIS", 0), v["vPIS"]),
                ("COFINS", config.ALIQUOTAS_PADRAO.get("COFINS", 0), v["vCOFINS"]),
                ("IRRF", config.ALIQUOTAS_PADRAO.get("IRRF", 0), v["vIR"]),
                ("INSS retido", config.ALIQUOTAS_PADRAO.get("INSS retido", 0), v["vINSS"]),
                ("ISS", config.ALIQUOTAS_PADRAO.get("ISS", 0), v["vISS"]),
            ]
            imp_validos = [(tp, a, val) for tp, a, val in impostos_nf if val > 0]
            
            for i, row in enumerate(self._cap_imp_rows):
                if i < len(imp_validos):
                    tp, aliq, val = imp_validos[i]
                    row["tipo"].set(tp)
                    row["aliq"].set(str(aliq))
                    row["val"].set(f"{val:.2f}")
                else:
                    row["tipo"].set("")
                    row["aliq"].set("")
                    row["val"].set("")
                    
            if len(parcelas_xml) > 1:
                import tkinter as tk
                for w in self._cap_parc_widgets: w.destroy()
                self._cap_parc_widgets = []
                self._cap_parc_data = []
                
                self._cap_nparc.delete(0, "end")
                self._cap_nparc.insert(0, str(len(parcelas_xml)))
                
                bg_s = "#0a0f1e"
                hdr = tk.Frame(self._cap_frm_parcelas, bg="#0a0f1e")
                hdr.pack(fill="x", pady=(0, 2))
                for h, w in [("Parcela", 60), ("Vencimento", 110), ("Valor", 100)]:
                    tk.Label(hdr, text=h, fg="#94a3b8", bg="#0a0f1e", font=("Segoe UI", 7, "bold"), width=w//7).pack(side="left", padx=4)
                self._cap_parc_widgets.append(hdr)
                
                for i, p in enumerate(parcelas_xml):
                    row_f = tk.Frame(self._cap_frm_parcelas, bg="#111827")
                    row_f.pack(fill="x", pady=1)
                    tk.Label(row_f, text=f"{i+1}/{len(parcelas_xml)}", fg="#94a3b8", bg="#111827", font=("Segoe UI", 8), width=6).pack(side="left", padx=4)
                    dt_var = tk.StringVar(value=p["d_venc"])
                    tk.Entry(row_f, textvariable=dt_var, width=11, font=("Segoe UI", 8), bg=bg_s, fg="white", insertbackground="#38bdf8", relief="flat", bd=2).pack(side="left", padx=4)
                    val_var = tk.StringVar(value=f"{p['v_dup']:.2f}")
                    tk.Entry(row_f, textvariable=val_var, width=10, font=("Segoe UI", 8), bg=bg_s, fg="#4ade80", insertbackground="#38bdf8", relief="flat", bd=2).pack(side="left", padx=4)
                    self._cap_parc_data.append({"dt": dt_var, "val": val_var, "num": i+1, "total": len(parcelas_xml)})
                    self._cap_parc_widgets.append(row_f)

            if cnpj_fmt:
                f = buscar_fornecedor_por_cnpj(cnpj_fmt)
                if f and hasattr(self, "_cap_preencher_banco"):
                    self._cap_preencher_banco(dict(f))
                    if f["categoria"]: self._cap_cat_var.set(f["categoria"])
                    if f["responsavel"]: self._cap_resp.set(f["responsavel"])
                elif data["emitente"]["razao"]:
                    salvar_fornecedor({
                        "razao_social": data["emitente"]["razao"],
                        "nome_fantasia": data["emitente"]["fantasia"],
                        "cnpj_cpf": cnpj_fmt,
                        "tipo": "FORNECEDOR",
                        "empresa": self._cap_emp_var.get(),
                        "ativo": 1,
                    })
                    self._cap_lbl_xml.config(text=f"NF {num_nf} importada — fornecedor cadastrado automaticamente")
                    return
            
            self._cap_lbl_xml.config(text=f"NF {num_nf} importada")
            
        except Exception as e:
            self._cap_lbl_xml.config(text=f"Erro ao ler XML: {e}", fg="#dc2626")

    def _cap_atualizar_badge_alertas(self):
        """Atualiza o texto da aba de Alertas com contagem de pendências urgentes."""
        try:
            hoje = date.today()
            notas = listar_notas(status="PENDENTE") or []
            urgentes = sum(1 for n in notas if n.get("dt_vencimento") and
                          datetime.strptime(n["dt_vencimento"], "%d/%m/%Y").date() <= hoje)
            label = f"  🔔 ALERTAS{f' ({urgentes})' if urgentes else ''}  "
            # Tenta renomear a aba — CTkTabview não expõe rename, usamos workaround via _segmented_button
            try:
                sb = self.cap_tabs._segmented_button
                for btn in sb._buttons_dict:
                    if "ALERTA" in btn:
                        sb._buttons_dict[btn].configure(text=label)
                        break
            except Exception:
                pass
        except Exception:
            pass

    def _cap_build_lista(self, parent, bg, surface, accent, green, yellow, text, muted, nb_pai):
        from gui.design_system import COLORS, FONTS, create_btn, create_input, create_combo, create_label

        # ── TOOLBAR ──────────────────────────────────────────────────────────
        tb = ctk.CTkFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=16, pady=10)

        self._cap_filtro_status = ctk.StringVar(value="PENDENTE")
        seg_status = ctk.CTkSegmentedButton(
            tb,
            variable=self._cap_filtro_status,
            values=["TODOS", "PENDENTE", "PREVISÃO", "PAGA", "CANCELADA"],
            selected_color=COLORS["border_light"],
            selected_hover_color=COLORS["border_light"],
            unselected_color=COLORS["surface"],
            unselected_hover_color=COLORS["border"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            command=lambda _: self._cap_carregar_lista()
        )
        seg_status.pack(side="left", padx=(0, 20))

        create_label(tb, "Empresa:", type="caption").pack(side="left", padx=(0, 5))
        self._cap_filtro_emp = create_combo(tb, values=["TODOS","LALUA","SOLAR"], width=100)
        self._cap_filtro_emp.set("TODOS")
        self._cap_filtro_emp.pack(side="left", padx=(0, 15))

        create_label(tb, "Venc. De:", type="caption").pack(side="left", padx=(0, 5))
        self._cap_dt_de_var = tk.StringVar()
        ent_de = create_input(tb, width=90)
        ent_de.configure(textvariable=self._cap_dt_de_var)
        ent_de.pack(side="left", padx=(0, 5))
        _aplicar_mascara_data(ent_de)

        create_label(tb, "Até:", type="caption").pack(side="left", padx=(5, 5))
        self._cap_dt_ate_var = tk.StringVar()
        ent_ate = create_input(tb, width=90)
        ent_ate.configure(textvariable=self._cap_dt_ate_var)
        ent_ate.pack(side="left", padx=(0, 15))
        _aplicar_mascara_data(ent_ate)

        self._cap_busca_var = tk.StringVar()
        ent_busca = create_input(tb, width=150, placeholder_text="Buscar...")
        ent_busca.configure(textvariable=self._cap_busca_var)
        ent_busca.pack(side="left", padx=(0, 5))

        create_btn(tb, "🔄 Filtrar", width=80, style="secondary", command=self._cap_carregar_lista).pack(side="left", padx=5)
        create_btn(tb, "✨ Nova Nota", width=100, style="primary", command=lambda: [self._cap_limpar_form(), self._cap_select_tab(1)]).pack(side="left", padx=5)

        create_btn(tb, "📊 CSV", width=80, style="secondary", command=self._cap_exportar_csv).pack(side="right")

        # ── TREEVIEW ──────────────────────────────────────────────────────────
        cols = ("Nº TX","Nº NF","Tipo","Fornecedor","Empresa","Emissão",
                "Vencimento","Atraso","Bruto","Líquido","Status","Categoria")
        self._cap_tree = ttk.Treeview(parent, columns=cols,
                                       style="DS.Treeview", show="headings", height=13)
        largs = [110,70,70,180,65,75,80,60,100,100,75,160]
        for c, w in zip(cols, largs):
            self._cap_tree.heading(c, text=c,
                command=lambda _c=c: self._cap_ordenar_coluna(_c))
            self._cap_tree.column(c, width=w,
                anchor="e" if c in ("Bruto","Líquido","Atraso") else "w")

        self._cap_tree.tag_configure("PENDENTE",  foreground="#fbbf24")
        self._cap_tree.tag_configure("APROVADA",  foreground="#38bdf8")
        self._cap_tree.tag_configure("PAGA",      foreground="#4ade80")
        self._cap_tree.tag_configure("VENCIDA",   foreground="#f87171")
        self._cap_tree.tag_configure("CANCELADA", foreground="#64748b")
        self._cap_tree.tag_configure("ATRASADA",  foreground="#f87171",
                                      background="#1a0000")
        self._cap_tree.tag_configure("PREVISAO",  foreground="#fbbf24", background="#291a00")
        self._cap_tree.tag_configure("CONCILIADA", foreground="#10b981", font=("Segoe UI", 9, "bold"))

        sb = ttk.Scrollbar(parent, orient="vertical", command=self._cap_tree.yview)
        self._cap_tree.configure(yscrollcommand=sb.set)

        # Double-click → editar nota
        self._cap_tree.bind("<Double-1>",
                            lambda e: self._cap_abrir_edicao(nb_pai))
        # F5 → recarregar
        self._cap_tree.bind("<F5>", lambda e: self._cap_carregar_lista())

        # ── RODAPÉ ────────────────────────────────────────────────────────────
        rod = tk.Frame(parent, bg="#0a0f1e", pady=8, padx=16)
        rod.pack(fill="x", side="bottom")

        self._cap_lbl_totais = tk.Label(rod, text="", font=("Segoe UI",10,"bold"),
                                         fg="#f8fafc", bg="#0a0f1e")
        self._cap_lbl_totais.pack(side="left")

        ctk.CTkButton(rod, text="✅ Conciliar", font=("Segoe UI", 10, "bold"),
                      fg_color="#10b981", hover_color="#059669", text_color="white", width=100, height=28,
                      command=self._cap_conciliar_selecionada).pack(side="right", padx=(8,0))
                      
        ctk.CTkButton(rod, text="Marcar PAGA", font=("Segoe UI", 10, "bold"),
                      fg_color="#7c3aed", hover_color="#6d28d9", text_color="white", width=100, height=28,
                      command=lambda: self._cap_mudar_status("PAGA")).pack(side="right", padx=(8,0))
                      
        ctk.CTkButton(rod, text="📋 Aprovar", font=("Segoe UI", 10, "bold"),
                      fg_color=accent, hover_color="#a3e635", text_color="#1a1a1a", width=100, height=28,
                      command=lambda: self._cap_mudar_status("APROVADA")).pack(side="right", padx=(8,0))
                      
        ctk.CTkButton(rod, text="✏️ Editar", font=("Segoe UI", 10, "bold"),
                      fg_color=accent, hover_color="#a3e635", text_color="#1a1a1a", width=100, height=28,
                      command=lambda: self._cap_abrir_edicao(nb_pai)).pack(side="right", padx=(8,0))
                      
        ctk.CTkButton(rod, text="❌ Cancelar", font=("Segoe UI", 10, "bold"),
                      fg_color="#fee2e2", hover_color="#fca5a5", text_color="#dc2626", width=100, height=28,
                      command=lambda: self._cap_mudar_status("CANCELADA")).pack(side="right", padx=(8,0))

        # ── CONTAINERS ────────────────────────────────────────────────────────
        self._cap_main_wrap = tk.Frame(parent, bg="#0a0f1e")
        self._cap_main_wrap.pack(side="top", fill="both", expand=True)

        self._cap_tree_container = tk.Frame(self._cap_main_wrap, bg="#0a0f1e")
        self._cap_tree_container.pack(side="left", fill="both", expand=True)

        self._cap_tree.pack(in_=self._cap_tree_container, side="left", fill="both", expand=True)
        sb.pack(in_=self._cap_tree_container, side="left", fill="y")

        # ── GED PANEL ────────────────────────────────────────────────────────
        self._cap_ged_panel = tk.Frame(self._cap_main_wrap, bg="#1e293b", width=320)
        self._cap_ged_panel.pack_propagate(False)
        self._cap_ged_panel.pack_forget() # Oculto por padrão

        ged_topo = tk.Frame(self._cap_ged_panel, bg="#1e293b")
        ged_topo.pack(fill="x", pady=8, padx=10)
        tk.Label(ged_topo, text="📄 Comprovante / NF", fg="white", bg="#1e293b", font=("Segoe UI", 10, "bold")).pack(side="left")
        
        def _cap_ged_close():
            self._cap_ged_panel.pack_forget()
            
        tk.Button(ged_topo, text="✕", command=_cap_ged_close, bg="#1e293b", fg="#94a3b8", bd=0, font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="right")

        self._cap_ged_img_lbl = tk.Frame(self._cap_ged_panel, bg="#0f172a")
        self._cap_ged_img_lbl.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._cap_tree.bind("<<TreeviewSelect>>", self._cap_on_select_tree)

        self._cap_sort_col = None
        self._cap_sort_rev = False
        self._cap_carregar_lista()



    def _cap_on_select_tree(self, event):
        sel = self._cap_tree.selection()
        if not sel:
            self._cap_ged_panel.pack_forget()
            return
            
        nota_id = int(sel[0])
        try:
            from services.database import db_conn
            with db_conn() as conn:
                row = conn.execute("SELECT arquivo_path FROM notas WHERE id=?", (nota_id,)).fetchone()
                path = row[0] if row else ""
        except Exception:
            path = ""
            
        if path and os.path.exists(path):
            self._cap_ged_panel.pack(side="right", fill="y", padx=(10, 0))
            self._cap_ged_mostrar_arquivo(path)
        else:
            self._cap_ged_panel.pack_forget()
            
    def _cap_ged_mostrar_arquivo(self, path):
        import os, customtkinter as ctk
        for w in self._cap_ged_img_lbl.winfo_children(): w.destroy()
        
        ext = path.lower().split('.')[-1]
        try:
            if ext in ('png', 'jpg', 'jpeg'):
                from PIL import Image
                img = Image.open(path)
                img.thumbnail((300, 400), Image.Resampling.LANCZOS)
                c_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                lbl = ctk.CTkLabel(self._cap_ged_img_lbl, image=c_img, text="")
                lbl.pack(expand=True, pady=10)
            elif ext == 'pdf':
                import fitz
                from PIL import Image
                import io
                doc = fitz.open(path)
                page = doc[0]
                mat = fitz.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                img.thumbnail((300, 400), Image.Resampling.LANCZOS)
                c_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                lbl = ctk.CTkLabel(self._cap_ged_img_lbl, image=c_img, text="")
                lbl.pack(expand=True, pady=10)
            else:
                tk.Label(self._cap_ged_img_lbl, text="Formato não suportado para pré-visualização.", 
                         fg="white", bg="#0f172a", wraplength=200).pack(pady=50)
        except Exception as e:
            tk.Label(self._cap_ged_img_lbl, text=f"Erro ao carregar pré-visualização:\n{e}", 
                     fg="#f87171", bg="#0f172a", wraplength=200).pack(pady=50)
                     
        ctk.CTkButton(self._cap_ged_img_lbl, text="Abrir Arquivo Original", 
                      command=lambda: os.startfile(path), fg_color="#3b82f6", hover_color="#2563eb",
                      width=180, height=32).pack(pady=(0, 10))

    def _cap_ordenar_coluna(self, col):
        """Ordena treeview pela coluna clicada (toggle asc/desc)."""
        try:
            items = [(self._cap_tree.set(k, col), k)
                     for k in self._cap_tree.get_children("")]
            rev = (self._cap_sort_col == col and not self._cap_sort_rev)
            items.sort(reverse=rev)
            for idx, (_, k) in enumerate(items):
                self._cap_tree.move(k, "", idx)
            self._cap_sort_col = col
            self._cap_sort_rev = rev
        except Exception:
            pass

    def _cap_exportar_csv(self):
        """Exporta a lista atual para CSV."""
        from tkinter import filedialog
        import csv
        path = filedialog.asksaveasfilename(
            title="Salvar CSV",
            defaultextension=".csv",
            filetypes=[("CSV","*.csv"),("Todos","*.*")],
            initialfile=f"notas_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
        if not path: return
        cols = [self._cap_tree.heading(c)["text"]
                for c in self._cap_tree["columns"]]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(cols)
                for iid in self._cap_tree.get_children():
                    w.writerow(self._cap_tree.item(iid, "values"))
            messagebox.showinfo("Exportado",
                f"CSV salvo com sucesso:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def _cap_abrir_edicao(self, nb_pai):
        """Carrega a nota selecionada no formulario para edicao."""
        sel = self._cap_tree.selection()
        if not sel: return
        nota_id = int(sel[0])
        try:
            with db_conn() as conn:
                conn.row_factory = __import__('sqlite3').Row
                row = conn.execute(
                    "SELECT * FROM notas WHERE id=?", (nota_id,)).fetchone()
            if not row: return
            n = dict(row)
        except Exception:
            # Fallback: busca via listar_notas
            todas = listar_notas() or []
            ns = [x for x in todas if x.get("id") == nota_id]
            if not ns: return
            n = ns[0]

        # Marca modo edicao
        self._cap_editando_id = nota_id
        self._cap_limpar_form()

        # Preenche campos
        self._cap_forn.insert(0, n.get("fornecedor",""))
        self._cap_cnpj.insert(0, n.get("cnpj",""))
        self._cap_desc.insert(0, n.get("descricao",""))
        self._cap_dt_emissao.delete(0,"end")
        self._cap_dt_emissao.insert(0, n.get("dt_emissao",""))
        self._cap_dt_venc.insert(0, n.get("dt_vencimento",""))
        vb = n.get("valor_bruto", 0)
        self._cap_valor.insert(0,
            f"{vb:,.2f}".replace(",","X").replace(".",",").replace("X","."))
        self._cap_obs.insert(0, n.get("observacao","") or "")
        if n.get("categoria"): self._cap_cat_var.set(n["categoria"])
        if n.get("responsavel"): self._cap_resp.set(n["responsavel"])
        if n.get("empresa"): self._cap_emp_var.set(n["empresa"])
        if n.get("natureza"): self._cap_natureza_var.set(n["natureza"])
        if n.get("forma_pgto"): self._cap_forma_pgto.set(n["forma_pgto"])
        difal = n.get("valor_difal", 0) or 0
        self._cap_difal.delete(0,"end")
        self._cap_difal.insert(0, f"{difal:,.2f}".replace(",","X").replace(".",",").replace("X","."))
        
        # Anexo
        arq = n.get("arquivo_path","")
        if hasattr(self, "_cap_arquivo_path_var"):
            self._cap_arquivo_path_var.set(arq)
            try:
                import os
                self._cap_lbl_anexo.config(text=f"{os.path.basename(arq)}" if arq else "")
            except: pass

        # Atualiza titulo do formulario
        try:
            self._cap_lbl_form_titulo.config(
                text=f"✏️  Editando Nota #{nota_id}")
        except Exception:
            pass

        self._cap_select_tab(1)

    def _cap_limpar_form(self):
        """Reseta o formulario para nova nota."""
        self._cap_editando_id = None
        for w in [self._cap_forn, self._cap_cnpj, self._cap_desc,
                  self._cap_valor, self._cap_obs, self._cap_dt_venc,
                  self._cap_cod_barras, self._cap_pix_chave,
                  self._cap_banco_dest, self._cap_ag_dest,
                  self._cap_conta_dest, self._cap_cpf_cnpj_dest,
                  self._cap_chave_ref]:
            try: w.delete(0,"end")
            except Exception: pass
        try:
            self._cap_difal.delete(0,"end"); self._cap_difal.insert(0,"0,00")
            self._cap_fcp.delete(0,"end");   self._cap_fcp.insert(0,"0,00")
            self._cap_dt_emissao.delete(0,"end")
            self._cap_dt_emissao.insert(0, datetime.now().strftime("%d/%m/%Y"))
            self._cap_cat_var.set("")
            self._cap_lbl_form_titulo.config(text=" Nova Nota / Despesa")
            self._cap_arquivo_path_var.set("")
            self._cap_lbl_anexo.config(text="")
            self._cap_lbl_alerta_imposto.config(text="")
        except Exception:
            pass

    def _cap_validar_aliquotas(self):
        """Avisa se PIS for maior que COFINS (erro comum)."""
        if not hasattr(self, "_cap_imp_rows"): return
        pis_val = 0
        cofins_val = 0
        for r in self._cap_imp_rows:
            tp = r["tipo"].get()
            try:
                al = _parse_valor(r["aliq"].get())
                if tp == "PIS": pis_val = al
                elif tp == "COFINS": cofins_val = al
            except: pass
        try:
            if pis_val > 0 and cofins_val > 0 and pis_val >= cofins_val:
                self._cap_lbl_alerta_imposto.config(
                    text="⚠️ Atenção: A alíquota de PIS geralmente é menor que a de COFINS.",
                    fg="#dc2626")
            else:
                self._cap_lbl_alerta_imposto.config(text="")
        except: pass

    def _cap_anexar_comprovante(self):
        """Abre dialogo para selecionar arquivo e copia para a pasta da aplicacao."""
        from tkinter import filedialog
        import shutil
        import os
        from datetime import datetime
        
        path = filedialog.askopenfilename(
            title="Selecionar Anexo",
            filetypes=[("PDF/XML", "*.pdf *.xml"), ("Todos os Arquivos", "*.*")]
        )
        if not path: return

        # Salva o path temporariamente (será copiado de verdade no _cap_salvar_nota)
        self._cap_arquivo_path_var.set(path)
        try:
            self._cap_lbl_anexo.config(text=f"{os.path.basename(path)}")
        except Exception: pass

    def _cap_carregar_lista(self):
        for r in self._cap_tree.get_children():
            self._cap_tree.delete(r)

        st  = self._cap_filtro_status.get()
        emp = self._cap_filtro_emp.get()
        bsc = self._cap_busca_var.get().strip()
        dt_de_str  = getattr(self, "_cap_dt_de_var",  tk.StringVar()).get().strip()
        dt_ate_str = getattr(self, "_cap_dt_ate_var", tk.StringVar()).get().strip()

        notas = listar_notas(
            status=None if st=="TODOS" else st,
            empresa=None if emp=="TODOS" else emp,
            busca=bsc
        ) or []

        # Filtra por periodo de vencimento
        hoje = date.today()
        if dt_de_str or dt_ate_str:
            filtradas = []
            try:
                d_de  = datetime.strptime(dt_de_str,  "%d/%m/%Y").date() if dt_de_str  else None
                d_ate = datetime.strptime(dt_ate_str, "%d/%m/%Y").date() if dt_ate_str else None
                for n in notas:
                    try:
                        dv = datetime.strptime(n["dt_vencimento"], "%d/%m/%Y").date()
                        if d_de  and dv < d_de:  continue
                        if d_ate and dv > d_ate: continue
                        filtradas.append(n)
                    except Exception:
                        filtradas.append(n)
                notas = filtradas
            except Exception:
                pass

        total_receita = 0.0
        total_despesa = 0.0
        # Acumuladores para dashboard
        v_venc=v_hoje=v_sem=v_paga=0.0
        c_venc=c_hoje=c_sem=c_paga=0
        prox7 = hoje + timedelta(days=7)
        ini_mes = hoje.replace(day=1)

        # Inteligência: Pegar médias de fornecedores para detector de anomalia
        medias_forn = {}
        try:
            from services.database import db_conn
            with db_conn() as conn:
                rows_avg = conn.execute("SELECT fornecedor, AVG(valor_bruto) FROM notas WHERE status NOT IN ('CANCELADA', 'PREVISÃO') GROUP BY fornecedor").fetchall()
                medias_forn = {r[0]: r[1] for r in rows_avg if r[0]}
        except: pass

        for n in notas:
            status = n.get("status","PENDENTE")
            is_prev = n.get("is_previsao", 0)
            conciliada = n.get("conciliada", 0)
            
            if is_prev:
                status = "PREVISÃO"
                tag = "PREVISAO"
            elif conciliada:
                status = "CONCILIADA"
                tag = "CONCILIADA"
            else:
                tag = status if status in config.STATUS_NOTA else "PENDENTE"

            tipo_op = n.get("tipo_operacao", "DESPESA")
            valor = n.get("valor_bruto", 0) or 0
            if tipo_op == "RECEITA":
                total_receita += valor; op_prefix = "(+) "
            else:
                total_despesa += valor; op_prefix = "(-) "

            # Calcula atraso
            atraso_txt = ""
            try:
                dv = datetime.strptime(n["dt_vencimento"], "%d/%m/%Y").date()
                if status in ("PENDENTE","APROVADA","VENCIDA") and dv < hoje:
                    dias = (hoje - dv).days
                    atraso_txt = f"-{dias}d"
                    tag = "ATRASADA"
                # Acumuladores dashboard
                if status in ("PENDENTE","APROVADA","VENCIDA"):
                    if dv < hoje:
                        v_venc += valor; c_venc += 1
                    elif dv == hoje:
                        v_hoje += valor; c_hoje += 1
                    elif hoje < dv <= prox7:
                        v_sem += valor; c_sem += 1
                if status == "PAGA" and dv >= ini_mes:
                    v_paga += valor; c_paga += 1
            except Exception:
                pass

            num_nf = n.get("numero_nf","") or ""
            alerta = ""
            forn_nome = n.get("fornecedor", "")
            if not is_prev and forn_nome in medias_forn and medias_forn[forn_nome] > 0:
                media = medias_forn[forn_nome]
                if valor > media * 1.3:
                    alerta = " 🚩"

            self._cap_tree.insert("", "end", iid=str(n["id"]), tags=(tag,),
                values=(
                    n["numero_tx"],
                    num_nf,
                    f"{op_prefix}{n.get('natureza','NOTA')}",
                    n["fornecedor"][:28] + alerta,
                    n["empresa"],
                    n.get("dt_emissao",""),
                    n["dt_vencimento"],
                    atraso_txt,
                    f"R$ {valor:,.2f}",
                    f"R$ {n.get('valor_liquido',valor):,.2f}",
                    status,
                    (n.get("categoria") or "")[:25]
                ))

        saldo = total_receita - total_despesa
        cor_saldo = "#4ade80" if saldo >= 0 else "#f87171"
        self._cap_lbl_totais.config(
            text=f"{len(notas)} nota(s)  |  "
                 f"Receitas: R$ {total_receita:,.2f}  |  "
                 f"Despesas: R$ {total_despesa:,.2f}  |  "
                 f"SALDO: R$ {saldo:,.2f}",
            fg=cor_saldo)

        # Atualiza dashboard cards
        try:
            self._cap_dash_venc_val.config(text=f"R$ {v_venc:,.2f}")
            self._cap_dash_venc_cnt.config(text=f"{c_venc} nota(s)")
            self._cap_dash_hoje_val.config(text=f"R$ {v_hoje:,.2f}")
            self._cap_dash_hoje_cnt.config(text=f"{c_hoje} nota(s)")
            self._cap_dash_sem_val.config(text=f"R$ {v_sem:,.2f}")
            self._cap_dash_sem_cnt.config(text=f"{c_sem} nota(s)")
            self._cap_dash_paga_val.config(text=f"R$ {v_paga:,.2f}")
            self._cap_dash_paga_cnt.config(text=f"{c_paga} nota(s)")
        except Exception:
            pass

        # Atualiza badge de alertas
        self._cap_atualizar_badge_alertas()
    def _cap_conciliar_selecionada(self):
        sel = self._cap_tree.selection()
        if not sel:
            tk.messagebox.showwarning("Atenção", "Selecione uma nota para conciliar.")
            return
        try:
            from services.database import db_conn
            from tkinter import messagebox
            nota_id = int(sel[0])
            with db_conn() as conn:
                status = conn.execute("SELECT status FROM notas WHERE id=?", (nota_id,)).fetchone()[0]
                if status != "PAGA":
                    messagebox.showwarning("Atenção", "Apenas contas com status 'PAGA' podem ser conciliadas.")
                    return
                conn.execute("UPDATE notas SET conciliada=1 WHERE id=?", (nota_id,))
                conn.commit()
            self._cap_carregar_lista()
            messagebox.showinfo("Sucesso", "Conta marcada como CONCILIADA com sucesso!")
        except Exception as e:
            tk.messagebox.showerror("Erro", f"Falha ao conciliar: {e}")


    def _cap_mudar_status(self, novo_status):
        sel = self._cap_tree.selection()
        if not sel:
            return
        for iid in sel:
            atualizar_status_nota(int(iid), novo_status)
        self._cap_carregar_lista()


    # ── SUB-ABA: NOVA NOTA ────────────────────────────────────────────────────
    def _cap_build_nova_nota(self, parent, bg, surface, accent, green, yellow, text, muted, nb_pai):

        # Canvas + scrollbar para caber tudo
        canvas = tk.Canvas(parent, bg="#020617", highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        frm = tk.Frame(canvas, bg="#020617")
        win = canvas.create_window((0,0), window=frm, anchor="nw")

        def _resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win, width=e.width)
        canvas.bind("<Configure>", _resize)
        def _update_scroll(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        frm.bind("<Configure>", _update_scroll)
        self._cap_update_scroll = _update_scroll # Guarda referência

        def _scroll(e):
            canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _scroll)

        pad = dict(padx=20, pady=4)

        # ── TÍTULO + BOTÕES ──
        frm_tit = tk.Frame(frm, bg="#020617")
        frm_tit.pack(fill="x", padx=20, pady=10)
        self._cap_lbl_form_titulo = tk.Label(
            frm_tit, text=" Nova Nota / Despesa",
            font=("Segoe UI",16,"bold"), fg="#f8fafc", bg="#020617")
        self._cap_lbl_form_titulo.pack(side="left")

        ctk.CTkButton(frm_tit, text="📎 Importar XML (NF-e)",
                      font=("Segoe UI", 11, "bold"), fg_color=accent, hover_color="#a3e635", text_color="#1a1a1a",
                      width=160, height=32, command=lambda: self._cap_importar_xml()
                      ).pack(side="right")

        self._cap_lbl_xml = tk.Label(frm_tit, text="",
                                      font=("Segoe UI",8), fg="#f8fafc", bg="#020617")
        self._cap_lbl_xml.pack(side="right", padx=8)

        # Botão Salvar (Topo)
        ctk.CTkButton(frm_tit, text="💾 Salvar",
                      font=("Segoe UI", 11, "bold"), fg_color="#7c3aed", hover_color="#6d28d9", text_color="white",
                      width=100, height=32, command=lambda: self._cap_salvar_nota(nb_pai)
                      ).pack(side="right", padx=10)

        # Botão Nova Nota / Limpar
        ctk.CTkButton(frm_tit, text="➕ Nova",
                      font=("Segoe UI", 11), fg_color="#1e293b", hover_color="#334155", text_color="#f8fafc",
                      width=80, height=32, command=self._cap_limpar_form
                      ).pack(side="right", padx=4)

        # Botão Anexar
        ctk.CTkButton(frm_tit, text="📎 Anexar PDF",
                      font=("Segoe UI", 11), fg_color="#475569", hover_color="#334155", text_color="white",
                      width=120, height=32, command=self._cap_anexar_comprovante
                      ).pack(side="right", padx=10)

        # Atalho Ctrl+Enter = Salvar
        frm.bind_all("<Control-Return>",
                     lambda e: self._cap_salvar_nota(nb_pai))

        # Variável para armazenar o anexo
        self._cap_arquivo_path_var = tk.StringVar()
        self._cap_lbl_anexo = tk.Label(frm_tit, text="", font=("Segoe UI",8), fg="#f8fafc", bg="#020617")
        self._cap_lbl_anexo.pack(side="right", padx=5)

        # ── CARDS E HELPERS ──
        def lbl(parent, t): 
            return tk.Label(parent, text=t, fg="#94a3b8", bg=parent.cget("bg") if isinstance(parent, tk.Frame) else "#0f172a", font=("Segoe UI", 10, "bold"), anchor="w")
        
        def ent(parent, w=200, **kw):
            defaults = {
                "font": ("Segoe UI", 12),
                "fg_color": "#1e293b",
                "border_color": "#334155",
                "border_width": 1,
                "text_color": "#f8fafc"
            }
            defaults.update(kw)
            return ctk.CTkEntry(parent, width=w, height=32, **defaults)

        # CARD 1: IDENTIFICAÇÃO DO DOCUMENTO
        card1 = ctk.CTkFrame(frm, fg_color="#0f172a", corner_radius=8, border_width=1, border_color="#1e293b")
        card1.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(card1, text="📄 Identificação do Documento", font=("Segoe UI", 14, "bold"), text_color="#f8fafc").pack(anchor="w", padx=15, pady=(10, 0))
        
        frm_chave = tk.Frame(card1, bg="#0f172a")
        frm_chave.pack(fill="x", padx=15, pady=(10, 5))

        lbl(frm_chave, "🔑 Chave de Acesso NF-e:").pack(side="left", padx=(0,10))

        self._cap_chave_var = tk.StringVar()
        ent_chave = ent(frm_chave, w=350, textvariable=self._cap_chave_var)
        ent_chave.pack(side="left", padx=(0,10))
        tk.Label(frm_chave, text="(44 dígitos — pode bipar ou colar)", fg="#64748b", bg="#0f172a", font=("Consolas",9)).pack(side="left", padx=(0,10))

        ctk.CTkButton(frm_chave, text="🔍 Consultar SEFAZ", font=("Segoe UI", 11, "bold"), fg_color="#7c3aed", hover_color="#6d28d9", text_color="white", width=140, height=32, command=lambda: self._cap_consultar_sefaz()).pack(side="left")

        b1 = tk.Frame(card1, bg="#0f172a")
        b1.pack(fill="x", padx=15, pady=(5, 15))

        # Linha 0 — Tipo e Operação
        frm_tipo_op = tk.Frame(b1, bg="#0f172a")
        frm_tipo_op.grid(row=0,column=0,columnspan=6,sticky="w",pady=8)

        lbl(frm_tipo_op,"Tipo:").pack(side="left", padx=(0,8))
        self._cap_tipo_var = tk.StringVar(value="NOTA")
        for val,lbl_t in [("NOTA","Nota Fiscal"),("ADIANTAMENTO","Adiantamento")]:
            ctk.CTkRadioButton(frm_tipo_op, text=lbl_t, variable=self._cap_tipo_var,
                               value=val, font=("Segoe UI",12), text_color="#f8fafc",
                               fg_color=accent, hover_color="#a3e635").pack(side="left", padx=8)

        tk.Label(frm_tipo_op, text="  |  ", fg="#334155", bg="#0f172a", font=("Segoe UI",12)).pack(side="left", padx=10)

        lbl(frm_tipo_op,"Operação:").pack(side="left", padx=(0,8))
        self._cap_operacao_var = tk.StringVar(value="DESPESA")
        for val,lbl_o in [("DESPESA","Despesa (-)"),("RECEITA","Receita (+)")]:
            ctk.CTkRadioButton(frm_tipo_op, text=lbl_o, variable=self._cap_operacao_var,
                               value=val, font=("Segoe UI",12), text_color="#f8fafc",
                               fg_color=accent, hover_color="#a3e635").pack(side="left", padx=8)

        # Linha 1 — Fornecedor / CNPJ
        lbl(b1,"Fornecedor:").grid(row=1,column=0,sticky="w",pady=6)
        frm_forn = tk.Frame(b1, bg="#0f172a")
        frm_forn.grid(row=1,column=1,columnspan=2,sticky="w",padx=(0,15))
        self._cap_forn = ent(frm_forn, w=280)
        self._cap_forn.pack(side="left")
        ctk.CTkButton(frm_forn, text="🔍 Buscar", font=("Segoe UI", 11, "bold"),
                      fg_color="#334155", hover_color="#475569", text_color="white",
                      width=80, height=32, command=lambda: _abrir_busca_forn()
                      ).pack(side="left", padx=(5,0))

        lbl(b1,"CNPJ/CPF:").grid(row=1,column=3,sticky="w", padx=(15,0))
        self._cap_cnpj = ent(b1, w=200)
        self._cap_cnpj.grid(row=1,column=4,sticky="w")
        self._cap_lbl_cnpj_status = tk.Label(b1, text="", fg="#f8fafc", bg="#0f172a",
                                              font=("Segoe UI",8))
        self._cap_lbl_cnpj_status.grid(row=1, column=5, sticky="w", padx=(6,0))

        def _validar_cnpj_api(event=None):
            """Valida CNPJ e consulta BrasilAPI em background."""
            cnpj_raw = re.sub(r'\D', '', self._cap_cnpj.get())
            # Formata CNPJ automaticamente
            if len(cnpj_raw) == 14:
                fmt = f"{cnpj_raw[:2]}.{cnpj_raw[2:5]}.{cnpj_raw[5:8]}/{cnpj_raw[8:12]}-{cnpj_raw[12:14]}"
                self._cap_cnpj.delete(0,"end")
                self._cap_cnpj.insert(0, fmt)
                # Valida dígito verificador localmente
                def _dv_ok(c):
                    pesos = [5,4,3,2,9,8,7,6,5,4,3,2]
                    s = sum(int(c[i])*pesos[i] for i in range(12))
                    r = 0 if s%11<2 else 11-s%11
                    if r != int(c[12]): return False
                    pesos2 = [6]+pesos
                    s2 = sum(int(c[i])*pesos2[i] for i in range(13))
                    r2 = 0 if s2%11<2 else 11-s2%11
                    return r2 == int(c[13])
                if not _dv_ok(cnpj_raw):
                    self._cap_lbl_cnpj_status.config(
                        text="CNPJ inválido", fg="#dc2626")
                    return
                self._cap_lbl_cnpj_status.config(
                    text="⏳ Consultando...", fg="#94a3b8")
                def _bg():
                    try:
                        import requests as _req
                        r = _req.get(
                            f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_raw}",
                            timeout=8)
                        if r.status_code == 200:
                            d = r.json()
                            sit = d.get("descricao_situacao_cadastral","").upper()
                            nome = d.get("razao_social","")
                            cor = "#4ade80" if sit == "ATIVA" else "#f87171"
                            self.root.after(0, lambda: [
                                self._cap_lbl_cnpj_status.config(
                                    text=f"⬤ {sit}", fg=cor),
                                (self._cap_forn.delete(0,"end") or
                                 self._cap_forn.insert(0, nome))
                                if not self._cap_forn.get().strip() else None
                            ])
                        else:
                            self.root.after(0, lambda: self._cap_lbl_cnpj_status.config(
                                text="⚠️ não encontrado", fg="#fbbf24"))
                    except Exception:
                        self.root.after(0, lambda: self._cap_lbl_cnpj_status.config(
                            text="⚠️ offline", fg="#fbbf24"))
                threading.Thread(target=_bg, daemon=True).start()
            elif len(cnpj_raw) == 11:
                # CPF — apenas formata
                fmt = f"{cnpj_raw[:3]}.{cnpj_raw[3:6]}.{cnpj_raw[6:9]}-{cnpj_raw[9:11]}"
                self._cap_cnpj.delete(0,"end")
                self._cap_cnpj.insert(0, fmt)
                self._cap_lbl_cnpj_status.config(text="👤 CPF", fg="#94a3b8")

        self._cap_cnpj.bind("<FocusOut>", _validar_cnpj_api)


        # Linha 2 — Empresa / Categoria
        lbl(b1,"Empresa:").grid(row=2,column=0,sticky="w",pady=6)
        frm_emp = tk.Frame(b1, bg="#0f172a")
        frm_emp.grid(row=2,column=1,sticky="w",padx=(0,15))
        
        self._cap_emp_var = tk.StringVar(value="LALUA")
        cb_emp = ctk.CTkComboBox(frm_emp, variable=self._cap_emp_var,
                        values=["LALUA","SOLAR"], state="readonly",
                        width=100, height=32, font=("Segoe UI",12), fg_color="#1e293b",
                        border_color="#334155", button_color="#334155", dropdown_font=("Segoe UI", 12))
        cb_emp.pack(side="left", padx=(0,5))
        
        self._cap_filial_var = tk.StringVar(value="LALUA MATRIZ")
        self._cap_filial_cb = ctk.CTkComboBox(frm_emp, variable=self._cap_filial_var,
                        values=["LALUA MATRIZ", "BOAH BARRA", "PASEO", "VILAS", "SDB", "HORTO", "ONLINE"], state="readonly",
                        width=150, height=32, font=("Segoe UI",12), fg_color="#1e293b",
                        border_color="#334155", button_color="#334155", dropdown_font=("Segoe UI", 12))
        self._cap_filial_cb.pack(side="left")

        def _update_filial(*args):
            if self._cap_emp_var.get() == "LALUA":
                self._cap_filial_cb.configure(values=["LALUA MATRIZ", "BOAH BARRA", "PASEO", "VILAS", "SDB", "HORTO", "ONLINE"])
                self._cap_filial_var.set("LALUA MATRIZ")
            else:
                self._cap_filial_cb.configure(values=["SOLAR MATRIZ"])
                self._cap_filial_var.set("SOLAR MATRIZ")
        self._cap_emp_var.trace_add("write", _update_filial)

        lbl(b1,"Categoria:").grid(row=2,column=2,sticky="w")
        self._cap_cat_var = tk.StringVar()
        self._cap_cat_cb = ctk.CTkComboBox(b1, variable=self._cap_cat_var,
                                           values=config.CATEGORIAS_LISTA,
                                           width=350, height=32, font=("Segoe UI",12), fg_color="#1e293b",
                                           border_color="#334155", button_color="#334155", dropdown_font=("Segoe UI", 12))
        self._cap_cat_cb.grid(row=2,column=3,columnspan=2,sticky="w")

        # Linha 3 — Natureza / Responsável
        lbl(b1,"Natureza:").grid(row=3,column=0,sticky="w",pady=6)
        self._cap_natureza_var = tk.StringVar(value="VENDA")
        self._cap_nat_cb = ctk.CTkComboBox(b1, variable=self._cap_natureza_var,
            values=["VENDA","SERVIÇO","DEVOLUÇÃO","SALÁRIO","BENEFÍCIO","IMPOSTO","FIXA"],
            state="readonly", width=180, height=32, font=("Segoe UI",12), fg_color="#1e293b", border_color="#334155", button_color="#334155", dropdown_font=("Segoe UI", 12))
        self._cap_nat_cb.grid(row=3,column=1,sticky="w",padx=(0,15))

        lbl(b1,"Responsável:").grid(row=3,column=2,sticky="w")
        self._cap_resp = ctk.CTkComboBox(b1, values=config.RESPONSAVEIS_LISTA,
                                       state="readonly", width=250, height=32, font=("Segoe UI",12), fg_color="#1e293b", border_color="#334155", button_color="#334155", dropdown_font=("Segoe UI", 12))
        self._cap_resp.grid(row=3,column=3,sticky="w")

        # Linha 4 — Descrição / Nº NF
        lbl(b1,"Descrição:").grid(row=4,column=0,sticky="w",pady=6)
        self._cap_desc = ent(b1, w=400)
        self._cap_desc.grid(row=4,column=1,columnspan=3,sticky="w")
        lbl(b1,"Nº NF:").grid(row=4,column=4,sticky="w", padx=(8,0))
        self._cap_numero_nf = ent(b1, w=120)
        self._cap_numero_nf.grid(row=4,column=5,sticky="w")

        # CARD 2: VALORES E IMPOSTOS
        card2 = ctk.CTkFrame(frm, fg_color="#0f172a", corner_radius=8, border_width=1, border_color="#1e293b")
        card2.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(card2, text="💰 Valores e Impostos", font=("Segoe UI", 14, "bold"), text_color="#f8fafc").pack(anchor="w", padx=15, pady=(10, 0))
        
        b2_val = tk.Frame(card2, bg="#0f172a")
        b2_val.pack(fill="x", padx=15, pady=(5, 15))

        # Linha 5 — Datas / Valor
        lbl(b2_val,"Emissão:").grid(row=0,column=0,sticky="w",pady=6)
        self._cap_dt_emissao = ent(b2_val, w=140)
        self._cap_dt_emissao.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self._cap_dt_emissao.grid(row=0,column=1,sticky="w",padx=(0,15))
        _aplicar_mascara_data(self._cap_dt_emissao)

        lbl(b2_val,"Vencimento:").grid(row=0,column=2,sticky="w")
        self._cap_dt_venc = ent(b2_val, w=140)
        self._cap_dt_venc.grid(row=0,column=3,sticky="w",padx=(0,15))
        _aplicar_mascara_data(self._cap_dt_venc)

        lbl(b2_val,"Valor Bruto:").grid(row=0,column=4,sticky="w")
        self._cap_valor = ent(b2_val, w=180, font=("Segoe UI", 14, "bold"), text_color="#a3e635")
        self._cap_valor.grid(row=0,column=5,sticky="w")
        _aplicar_mascara_valor(self._cap_valor)

        # Linha 6 — DIFAL / FCP / Chave Ref (Específico ERP)
        lbl(b2_val,"DIFAL (R$):").grid(row=1,column=0,sticky="w",pady=6)
        self._cap_difal = ent(b2_val, w=140)
        self._cap_difal.insert(0, "0,00")
        self._cap_difal.grid(row=1,column=1,sticky="w",padx=(0,15))
        _aplicar_mascara_valor(self._cap_difal)

        lbl(b2_val,"FCP (R$):").grid(row=1,column=2,sticky="w")
        self._cap_fcp = ent(b2_val, w=140)
        self._cap_fcp.insert(0, "0,00")
        self._cap_fcp.grid(row=1,column=3,sticky="w",padx=(0,15))
        _aplicar_mascara_valor(self._cap_fcp)

        lbl(b2_val,"Chave/NF Ref:").grid(row=1,column=4,sticky="w")
        self._cap_chave_ref = ent(b2_val, w=280)
        self._cap_chave_ref.grid(row=1,column=5,sticky="w")

        # CARD 3: REGRAS DE PAGAMENTO E PREVISÕES
        card3 = ctk.CTkFrame(frm, fg_color="#0f172a", corner_radius=8, border_width=1, border_color="#1e293b")
        card3.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(card3, text="💳 Pagamento e Previsões", font=("Segoe UI", 14, "bold"), text_color="#f8fafc").pack(anchor="w", padx=15, pady=(10, 0))
        
        b3_pgto = tk.Frame(card3, bg="#0f172a")
        b3_pgto.pack(fill="x", padx=15, pady=(5, 15))
        b1b = b3_pgto  # Alias para compatibilidade com o resto do código

        # Linha 0 — Observação
        lbl(b3_pgto,"Observação:").grid(row=0,column=0,sticky="w",pady=2)
        self._cap_obs = ent(b3_pgto, w=600)
        self._cap_obs.grid(row=0,column=1,columnspan=5,sticky="w")

        # Linha 1 — Código de Barras
        lbl(b3_pgto,"Cód. Barras:").grid(row=1,column=0,sticky="w",pady=6)
        frm_cb = tk.Frame(b3_pgto, bg="#0f172a")
        frm_cb.grid(row=1,column=1,columnspan=5,sticky="w")
        self._cap_cod_barras = ent(frm_cb, w=500, font=("Consolas", 12), text_color=accent)
        self._cap_cod_barras.pack(side="left")
        lbl(frm_cb, "← bipe aqui com a pistola").pack(side="left", padx=6)

        # Linha 2 — Recorrência / Alertas
        lbl(b3_pgto,"Repetir:").grid(row=2,column=0,sticky="w",pady=6)
        self._cap_recorr_var = tk.BooleanVar(value=False)
        ctk.CTkSwitch(b3_pgto, text="Despesa Fixa Mensal", variable=self._cap_recorr_var,
                       font=("Segoe UI", 12), text_color="#f8fafc").grid(row=2,column=1,columnspan=2,sticky="w")
        
        lbl(b3_pgto,"Meses:").grid(row=2,column=3,sticky="w")
        self._cap_recorr_meses = tk.Spinbox(b3_pgto, from_=2, to=36, width=5, font=("Segoe UI",12),
                                            bg="#1e293b", fg="#f8fafc", relief="flat", bd=0)
        self._cap_recorr_meses.grid(row=2,column=4,sticky="w")

        # Alerta de Restituição DIFAL
        frm_prev_restit = tk.Frame(b3_pgto, bg="#0f172a")
        frm_prev_restit.grid(row=2,column=5,sticky="w", padx=(10,0))

        self._cap_lbl_alerta_restit = tk.Label(frm_prev_restit, text="", font=("Segoe UI",8,"bold"),
                                               fg="#f8fafc", bg="#0f172a")
        self._cap_lbl_alerta_restit.pack(side="left")
        
        self._cap_is_previsao_var = tk.BooleanVar(value=False)
        ctk.CTkSwitch(frm_prev_restit, text="🔮 Lançar como Previsão (Sem Nota)", variable=self._cap_is_previsao_var,
                       font=("Segoe UI", 12, "bold"), text_color="#fbbf24", progress_color="#fbbf24").pack(side="left", padx=10)

        self._cap_nat_cb.configure(command=lambda e: self._cap_check_restituicao())
        self._cap_chave_ref.bind("<FocusOut>", self._cap_check_restituicao)

        # Ao bipar, detecta automaticamente o tipo de pagamento
        def _detectar_tipo_barras(event=None):
            cb = self._cap_cod_barras.get().strip()
            if not cb: return
            if cb.startswith("858") or cb.startswith("859"): tipo_hint = "DARF"
            elif cb.startswith("856"): tipo_hint = "GPS"
            elif cb.startswith("858") and "DAS" in cb: tipo_hint = "DAS"
            elif len(cb) == 44 and cb[0] in "01234": tipo_hint = "BOLETO"
            elif len(cb) in (44, 47, 48): tipo_hint = "BOLETO"
            else: tipo_hint = ""
            if tipo_hint:
                if not self._cap_desc.get().strip():
                    self._cap_desc.delete(0,"end")
                    self._cap_desc.insert(0, tipo_hint)
                self._cap_forma_pgto.set(tipo_hint)
                _toggle_campos_pgto()
                
        self._cap_cod_barras.bind("<Return>",   _detectar_tipo_barras)
        self._cap_cod_barras.bind("<FocusOut>", _detectar_tipo_barras)

        # Forma de pagamento
        lbl(b3_pgto,"Forma:").grid(row=3,column=0,sticky="w",pady=10)
        self._cap_forma_pgto = ctk.CTkComboBox(b3_pgto,
            values=["BOLETO","PIX","TED","DARF","GPS","DAS","CONCESSIONÁRIA"],
            state="readonly", width=180, height=32, font=("Segoe UI",12), fg_color="#1e293b", border_color="#334155", button_color="#334155", dropdown_font=("Segoe UI", 12))
        self._cap_forma_pgto.set("BOLETO")
        self._cap_forma_pgto.grid(row=3,column=1,sticky="w",padx=(0,20))

        def _toggle_campos_pgto(event=None):
            forma = self._cap_forma_pgto.get()
            # Mostra/esconde campos conforme forma
            if forma in ("PIX","TED"):
                frm_boleto.grid_remove()
                frm_pix.grid()
                frm_banco.grid()
            elif forma in ("DARF","GPS","DAS","CONCESSIONÁRIA","BOLETO"):
                frm_pix.grid_remove()
                frm_banco.grid_remove()
                frm_boleto.grid()
            else:
                frm_pix.grid_remove()
                frm_boleto.grid_remove()
                frm_banco.grid_remove()
        self._cap_forma_pgto.configure(command=lambda e: _toggle_campos_pgto())

        # Linha PIX (escondida inicialmente)
        frm_pix = tk.Frame(b3_pgto, bg="#0f172a")
        frm_pix.grid(row=4,column=0,columnspan=6,sticky="w",pady=2)

        lbl(frm_pix,"Tipo chave:").pack(side="left",padx=(0,4))
        self._cap_pix_tipo = ctk.CTkComboBox(frm_pix,
            values=["CPF","CNPJ","TELEFONE","EMAIL","ALEATÓRIA"],
            state="readonly", width=120, height=32, font=("Segoe UI",10), fg_color="#1e293b", border_color="#334155", button_color="#334155")
        self._cap_pix_tipo.set("CNPJ")
        self._cap_pix_tipo.pack(side="left",padx=(0,10))

        lbl(frm_pix,"Chave PIX:").pack(side="left",padx=(0,4))
        self._cap_pix_chave = ent(frm_pix, w=280)
        self._cap_pix_chave.pack(side="left")
        frm_pix.grid_remove()

        # Linha dados bancários TED
        frm_banco = tk.Frame(b3_pgto, bg="#0f172a")
        frm_banco.grid(row=5,column=0,columnspan=6,sticky="w",pady=2)

        lbl(frm_banco,"Banco:").pack(side="left",padx=(0,4))
        self._cap_banco_dest = ent(frm_banco, w=80)
        self._cap_banco_dest.pack(side="left",padx=(0,10))

        lbl(frm_banco,"Agência:").pack(side="left",padx=(0,4))
        self._cap_ag_dest = ent(frm_banco, w=80)
        self._cap_ag_dest.pack(side="left",padx=(0,10))

        lbl(frm_banco,"Conta:").pack(side="left",padx=(0,4))
        self._cap_conta_dest = ent(frm_banco, w=120)
        self._cap_conta_dest.pack(side="left",padx=(0,10))

        lbl(frm_banco,"CPF/CNPJ dest:").pack(side="left",padx=(0,4))
        self._cap_cpf_cnpj_dest = ent(frm_banco, w=160)
        self._cap_cpf_cnpj_dest.pack(side="left")
        frm_banco.grid_remove()

        # Linha boleto (visível por padrão)
        frm_boleto = tk.Frame(b3_pgto, bg="#0f172a")
        frm_boleto.grid(row=6,column=0,columnspan=6,sticky="w",pady=2)
        tk.Label(frm_boleto,
                 text="ℹ️  Bipe o código de barras no campo acima. "
                      "Para PIX ou TED, selecione a forma e preencha os dados bancários.",
                 fg="#94a3b8", bg="#0f172a", font=("Consolas",9)
                 ).pack(side="left")

        # Auto-preenche dados bancários do fornecedor quando selecionado
        def _preencher_dados_banco(f_dict):
            """Chamado pelo autocomplete quando fornecedor é selecionado."""
            if f_dict.get("pix_chave"):
                self._cap_forma_pgto.set("PIX")
                self._cap_pix_chave.delete(0,"end")
                self._cap_pix_chave.insert(0, f_dict["pix_chave"])
                # Tipo da chave PIX baseado no formato
                chave = f_dict["pix_chave"]
                digits = "".join(c for c in chave if c.isdigit())
                if "@" in chave:
                    self._cap_pix_tipo.set("EMAIL")
                elif chave.startswith("+") or (chave.isdigit() and len(digits) == 11 and chave[0] in "67889"):
                    self._cap_pix_tipo.set("TELEFONE")
                elif len(digits) == 11:
                    self._cap_pix_tipo.set("CPF")
                elif len(digits) == 14:
                    self._cap_pix_tipo.set("CNPJ")
                else:
                    self._cap_pix_tipo.set("ALEATÓRIA")
                _toggle_campos_pgto()
            elif f_dict.get("conta"):
                self._cap_forma_pgto.set("TED")
                self._cap_banco_dest.delete(0,"end")
                self._cap_banco_dest.insert(0, f_dict.get("banco",""))
                self._cap_ag_dest.delete(0,"end")
                self._cap_ag_dest.insert(0, f_dict.get("agencia",""))
                self._cap_conta_dest.delete(0,"end")
                self._cap_conta_dest.insert(0, f_dict.get("conta",""))
                self._cap_cpf_cnpj_dest.delete(0,"end")
                self._cap_cpf_cnpj_dest.insert(0, f_dict.get("cnpj_cpf",""))
                _toggle_campos_pgto()

        # CARD 4: ITENS DA NOTA
        card4 = ctk.CTkFrame(frm, fg_color="#0f172a", corner_radius=8, border_width=1, border_color="#1e293b")
        card4.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(card4, text="🛒 Itens da Nota / Serviço", font=("Segoe UI", 14, "bold"), text_color="#f8fafc").pack(anchor="w", padx=15, pady=(10, 0))
        
        b1c = tk.Frame(card4, bg="#0f172a")
        b1c.pack(fill="x", padx=15, pady=(5, 15))

        self._cap_item_rows = []
        self._cap_frm_items = tk.Frame(b1c, bg="#0f172a")
        self._cap_frm_items.pack(fill="x")

        # Cabeçalho itens
        for i, (h, w) in enumerate([("Descrição / Produto", 70), ("Valor Total", 20)]):
            tk.Label(self._cap_frm_items, text=h, fg="#f8fafc", bg="#0f172a",
                     font=("Segoe UI",10,"bold")).grid(row=0, column=i*2, sticky="w", padx=6, pady=(0,5))

        self._cap_add_item_row() # Começa com uma linha

        ctk.CTkButton(b1c, text="+ Adicionar Rateio", font=("Segoe UI", 11, "bold"),
                      fg_color="#334155", hover_color="#475569", text_color="white",
                      width=140, height=28, command=self._cap_add_item_row).pack(anchor="w", pady=(8,0))

        # Guarda referência para o autocomplete usar
        self._cap_preencher_banco = _preencher_dados_banco

        # ── IMPOSTOS (Agora dentro do Card 2 de Valores) ──
        ctk.CTkLabel(card2, text="Impostos Retidos (Opcional)", font=("Segoe UI", 12, "bold"), text_color="#94a3b8").pack(anchor="w", padx=15, pady=(5, 5))
        
        b2 = tk.Frame(card2, bg="#0f172a")
        b2.pack(fill="x", padx=15, pady=(0, 15))

        tk.Label(b2, text="Valor Bruto de referência é preenchido automaticamente ao digitar acima.",
                 fg="#64748b", bg="#0f172a", font=("Consolas",9)).pack(anchor="w", pady=(0,8))

        self._cap_imp_rows = []
        frm_imps = tk.Frame(b2, bg="#0f172a")
        frm_imps.pack(fill="x")

        # Cabeçalho impostos
        for i, h in enumerate(["Imposto","Alíquota %","Valor R$","Venc. DARF/GPS"]):
            tk.Label(frm_imps, text=h, fg="#f8fafc", bg="#0f172a",
                     font=("Segoe UI",9,"bold")).grid(row=0,column=i*2,sticky="w",padx=6,pady=(0,5))

        def _add_imposto(tipo="", aliq="", venc=""):
            row_i = len(self._cap_imp_rows) + 1
            tipo_var = tk.StringVar(value=tipo)
            aliq_var = tk.StringVar(value=str(aliq))
            val_var  = tk.StringVar(value="")
            venc_var = tk.StringVar(value=venc)

            cb = ctk.CTkComboBox(frm_imps, variable=tipo_var,
                               values=config.TIPOS_IMPOSTO, state="readonly",
                               width=150, height=32, font=("Segoe UI",12), fg_color="#1e293b", border_color="#334155", button_color="#334155")
            cb.grid(row=row_i, column=0, padx=6, pady=4)

            aliq_e = ent(frm_imps, w=100, textvariable=aliq_var)
            aliq_e.grid(row=row_i, column=2, padx=6)

            val_e = ent(frm_imps, w=140, textvariable=val_var)
            val_e.grid(row=row_i, column=4, padx=6)

            venc_e = ent(frm_imps, w=140, textvariable=venc_var)
            venc_e.grid(row=row_i, column=6, padx=6)

            # Auto-calcula valor quando alíquota ou tipo muda
            def _calc(*args):
                try:
                    vb = _parse_valor(self._cap_valor.get())
                    al = _parse_valor(aliq_var.get())
                    val_var.set(f"{vb * al / 100:.2f}")
                except: pass
                # Validação de alíquotas invertidas
                self._cap_validar_aliquotas()

            def _preenche_aliq(*args):
                tp = tipo_var.get()
                if tp in config.ALIQUOTAS_PADRAO and not aliq_var.get():
                    aliq_var.set(str(config.ALIQUOTAS_PADRAO[tp]))
                _calc()

            tipo_var.trace_add("write", _preenche_aliq)
            aliq_var.trace_add("write", _calc)
            self._cap_valor.bind("<FocusOut>", lambda e: [_calc() for _ in [1]], add="+")

            self._cap_imp_rows.append({
                "tipo": tipo_var, "aliq": aliq_var,
                "val": val_var,   "venc": venc_var
            })

        for tp in ["PIS","COFINS","IRRF"]:  # 3 linhas padrão
            _add_imposto(tp, config.ALIQUOTAS_PADRAO.get(tp,""))

        self._cap_lbl_alerta_imposto = tk.Label(b2, text="", fg="#fbbf24", bg="#0f172a", font=("Segoe UI",9,"bold"))
        self._cap_lbl_alerta_imposto.pack(anchor="w", pady=(4,0))

        ctk.CTkButton(b2, text="+ Adicionar Imposto", font=("Segoe UI", 11, "bold"),
                      fg_color="#334155", hover_color="#475569", text_color="white",
                      width=140, height=28, command=_add_imposto).pack(anchor="w", pady=(8,0))

        # Label valor líquido
        self._cap_lbl_liq = tk.Label(b2, text="Valor líquido a pagar:  R$ 0,00",
                                      font=("Segoe UI",12,"bold"), fg="#a3e635", bg="#0f172a")
        self._cap_lbl_liq.pack(anchor="e", pady=(8,0))

        def _atualiza_liquido(*args):
            try:
                vb = _parse_valor(self._cap_valor.get())
                ti = sum(float(r["val"].get() or 0) for r in self._cap_imp_rows)
                liq = vb - ti
                self._cap_lbl_liq.config(
                    text=f"Valor líquido a pagar:  R$ {liq:,.2f}")
            except: pass
        self._cap_valor.bind("<KeyRelease>", _atualiza_liquido)

        # CARD 5: PARCELAMENTO
        card5 = ctk.CTkFrame(frm, fg_color="#0f172a", corner_radius=8, border_width=1, border_color="#1e293b")
        card5.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(card5, text="🗓️ Parcelamento", font=("Segoe UI", 14, "bold"), text_color="#f8fafc").pack(anchor="w", padx=15, pady=(10, 0))

        frame_parc_ctrl = tk.Frame(card5, bg="#0f172a")
        frame_parc_ctrl.pack(fill="x", padx=15, pady=(5, 15))

        lbl(frame_parc_ctrl, "Nº parcelas:").pack(side="left", pady=6)
        self._cap_nparc = tk.Spinbox(frame_parc_ctrl, from_=1, to=48, width=6,
                                      font=("Segoe UI",12), bg="#1e293b", fg="#f8fafc", relief="flat", bd=0)
        self._cap_nparc.pack(side="left", padx=(6,15))

        lbl(frame_parc_ctrl, "1ª parcela:").pack(side="left")
        self._cap_dt_1parc = ent(frame_parc_ctrl, w=140)
        self._cap_dt_1parc.pack(side="left", padx=(6,15))
        _aplicar_mascara_data(self._cap_dt_1parc)

        lbl(frame_parc_ctrl, "Intervalo (dias):").pack(side="left")
        self._cap_intervalo = tk.Spinbox(frame_parc_ctrl, from_=1, to=90,
                                          width=6, font=("Segoe UI",12),
                                          bg="#1e293b", fg="#f8fafc", relief="flat", bd=0)
        self._cap_intervalo.delete(0,"end"); self._cap_intervalo.insert(0,"30")
        self._cap_intervalo.pack(side="left", padx=(6,15))

        ctk.CTkButton(frame_parc_ctrl, text="⚡ Calcular parcelas",
                      font=("Segoe UI",11,"bold"), fg_color="#7c3aed", hover_color="#6d28d9", text_color="white",
                      command=self._cap_calcular_parcelas).pack(side="left")

        self._cap_frm_parcelas = tk.Frame(card5, bg="#0f172a")
        self._cap_frm_parcelas.pack(fill="x", padx=15, pady=(0,15))
        self._cap_parc_widgets = []

        # CARD 6: RATEIO (CENTRO DE CUSTO)
        card6 = ctk.CTkFrame(frm, fg_color="#0f172a", corner_radius=8, border_width=1, border_color="#1e293b")
        card6.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(card6, text="📋 Rateio (Centro de Custo)", font=("Segoe UI", 14, "bold"), text_color="#f8fafc").pack(anchor="w", padx=15, pady=(10, 0))

        tk.Label(card6, text="Soma dos percentuais deve ser 100%",
                 fg="#64748b", bg="#0f172a", font=("Consolas",9)).pack(anchor="w", padx=15, pady=(0,8))

        self._cap_rat_rows = []
        frm_rats = tk.Frame(card6, bg="#0f172a")
        frm_rats.pack(fill="x", padx=15, pady=(5, 15))

        for i,h in enumerate(["Filial","% Rateio","Categoria","Valor R$"]):
            tk.Label(frm_rats, text=h, fg="#f8fafc", bg="#0f172a",
                     font=("Segoe UI",9,"bold")).grid(row=0,column=i*2,sticky="w",padx=6,pady=(0,5))

        def _add_rateio():
            ri = len(self._cap_rat_rows) + 1
            fil_var  = tk.StringVar()
            pct_var  = tk.StringVar()
            cat_var  = tk.StringVar()
            val_var  = tk.StringVar()

            cb_f = ctk.CTkComboBox(frm_rats, variable=fil_var,
                         values=config.FILIAIS_RATEIO, state="readonly",
                         width=200, height=32, font=("Segoe UI",12), fg_color="#1e293b", border_color="#334155", button_color="#334155")
            cb_f.grid(row=ri, column=0, padx=6, pady=4)

            pct_e = ent(frm_rats, w=100, textvariable=pct_var)
            pct_e.grid(row=ri, column=2, padx=6)

            cb_c = ctk.CTkComboBox(frm_rats, variable=cat_var,
                         values=config.CATEGORIAS_LISTA,
                         width=300, height=32, font=("Segoe UI",12), fg_color="#1e293b", border_color="#334155", button_color="#334155")
            cb_c.grid(row=ri, column=4, padx=6)

            val_lbl = tk.Label(frm_rats, textvariable=val_var,
                               fg="#a3e635", bg="#0f172a", font=("Consolas",11,"bold"), width=15)
            val_lbl.grid(row=ri, column=6, padx=6)

            def _calc_rat(*args):
                try:
                    vb  = _parse_valor(self._cap_valor.get())
                    pct = _parse_valor(pct_var.get())
                    val_var.set(f"R$ {vb*pct/100:,.2f}")
                except: val_var.set("")
            pct_var.trace_add("write", _calc_rat)
            self._cap_valor.bind("<KeyRelease>",
                                  lambda e: [_calc_rat() for _ in [1]])

            self._cap_rat_rows.append({
                "filial":fil_var,"pct":pct_var,
                "cat":cat_var,"val":val_var
            })

        _add_rateio(); _add_rateio()  # 2 linhas iniciais
        self._cap_rat_rows[0]["pct"].set("100")

        ctk.CTkButton(card6, text="+ Adicionar Filial", font=("Segoe UI", 11, "bold"),
                      fg_color="#334155", hover_color="#475569", text_color="white",
                      width=140, height=28, command=_add_rateio).pack(anchor="w", padx=15, pady=(0, 10))

        self._cap_lbl_pct_total = tk.Label(card6, text="Total rateio: 0%",
                                            font=("Segoe UI",12,"bold"), fg="#f8fafc", bg="#0f172a")
        self._cap_lbl_pct_total.pack(anchor="e", padx=15, pady=5)

        # ── BOTÃO SALVAR ──
        ctk.CTkButton(frm, text="💾 SALVAR NOTA / PREVISÃO",
                      font=("Segoe UI", 14, "bold"), fg_color="#10b981", hover_color="#059669", text_color="white",
                      width=250, height=45, command=lambda: self._cap_salvar_nota(nb_pai)
                      ).pack(padx=20, pady=(10,25), anchor="e")

        self._cap_lbl_save = tk.Label(frm, text="", font=("Segoe UI",9),
                                       fg="#f8fafc", bg="#020617")
        self._cap_lbl_save.pack(padx=20, anchor="e")

    def _cap_check_restituicao(self, event=None):
        nat = self._cap_natureza_var.get()
        ref = self._cap_chave_ref.get().strip()
        if nat == "DEVOLUÇÃO" and ref:
            with db_conn() as conn:
                row = conn.execute("SELECT valor_difal FROM notas WHERE (numero_tx=? OR chave_ref=?) AND valor_difal > 0", 
                                   (ref, ref)).fetchone()
                if row:
                    self._cap_lbl_alerta_restit.config(text="⚠️ CRÉDITO DIFAL: Solicitar Restituição!")
                else:
                    self._cap_lbl_alerta_restit.config(text="")
        else:
            self._cap_lbl_alerta_restit.config(text="")

    def _cap_add_item_row(self, desc="", total=""):
        ri = len(self._cap_item_rows) + 1
        desc_var = tk.StringVar(value=desc)
        tot_var = tk.StringVar(value=total)

        desc_e = ctk.CTkEntry(self._cap_frm_items, width=600, height=32, font=("Segoe UI", 12),
                              fg_color="#1e293b", border_color="#334155", text_color="#f8fafc", textvariable=desc_var)
        desc_e.grid(row=ri, column=0, padx=6, pady=4, sticky="w")

        tot_e = ctk.CTkEntry(self._cap_frm_items, width=140, height=32, font=("Segoe UI", 12),
                             fg_color="#1e293b", border_color="#334155", text_color="#a3e635", textvariable=tot_var)
        tot_e.grid(row=ri, column=2, padx=6, sticky="w")

        self._cap_item_rows.append({"desc": desc_var, "total": tot_var, "widgets": (desc_e, tot_e)})



    def _cap_calcular_parcelas(self):
        """Gera as linhas de parcelas na tela."""
        for w in self._cap_parc_widgets:
            w.destroy()
        self._cap_parc_widgets = []

        try:
            n       = int(self._cap_nparc.get())
            vb      = _parse_valor(self._cap_valor.get())
            ti      = sum(float(r["val"].get() or 0) for r in self._cap_imp_rows)
            liq     = vb - ti
            dt_str  = self._cap_dt_1parc.get().strip()
            interv  = int(self._cap_intervalo.get())

            if not dt_str:
                dt_str = self._cap_dt_venc.get().strip()
            dt_base = datetime.strptime(dt_str, "%d/%m/%Y")
        except Exception as e:
            return

        valor_parc = round(liq / n, 2)
        resto      = round(liq - valor_parc * n, 2)

        self._cap_parc_data = []
        bg_s = "#0a0f1e"
        text_c = "white"

        hdr = tk.Frame(self._cap_frm_parcelas, bg="#0a0f1e")
        hdr.pack(fill="x", pady=(0,2))
        for h, w in [("Parcela",60),("Vencimento",110),("Valor",100)]:
            tk.Label(hdr, text=h, fg="#94a3b8", bg="#0a0f1e",
                     font=("Segoe UI",7,"bold"), width=w//7).pack(side="left", padx=4)
        self._cap_parc_widgets.append(hdr)

        from datetime import timedelta
        for i in range(n):
            dt_parc = dt_base + timedelta(days=interv*i)
            val_p   = valor_parc + (resto if i == n-1 else 0)

            row_f = tk.Frame(self._cap_frm_parcelas, bg="#111827")
            row_f.pack(fill="x", pady=1)

            tk.Label(row_f, text=f"{i+1}/{n}", fg="#94a3b8",
                     bg="#111827", font=("Segoe UI",8), width=6).pack(side="left", padx=4)

            dt_var = tk.StringVar(value=dt_parc.strftime("%d/%m/%Y"))
            tk.Entry(row_f, textvariable=dt_var, width=11,
                     font=("Segoe UI",8), bg=bg_s, fg=text_c,
                     insertbackground="#38bdf8", relief="flat", bd=2
                     ).pack(side="left", padx=4)

            val_var = tk.StringVar(value=f"{val_p:.2f}")
            tk.Entry(row_f, textvariable=val_var, width=10,
                     font=("Segoe UI",8), bg=bg_s, fg="#4ade80",
                     insertbackground="#38bdf8", relief="flat", bd=2
                     ).pack(side="left", padx=4)

            self._cap_parc_data.append({"dt": dt_var, "val": val_var,
                                         "num": i+1, "total": n})
            self._cap_parc_widgets.append(row_f)


    def _cap_salvar_nota(self, nb_pai):
        """Valida e salva a nota no banco SQLite."""
        try:
            forn = self._cap_forn.get().strip()
            if not forn:
                self._cap_lbl_save.config(text="⚠️ Informe o fornecedor.", fg="#fbbf24")
                return
            vb_str = self._cap_valor.get().strip()
            if not vb_str:
                self._cap_lbl_save.config(text="⚠️ Informe o valor.", fg="#fbbf24")
                return
            valor_bruto = _parse_valor(vb_str)

            impostos = []
            for r in self._cap_imp_rows:
                tp = r["tipo"].get().strip()
                if not tp: continue
                try: val = _parse_valor(r["val"].get())
                except: val = 0.0
                try: aliq = _parse_valor(r["aliq"].get())
                except: aliq = 0.0
                if val > 0:
                    impostos.append({
                        "tipo": tp, "aliquota": aliq,
                        "valor": val,
                        "dt_venc_imp": r["venc"].get().strip()
                    })

            parcelas = []
            if hasattr(self, "_cap_parc_data") and self._cap_parc_data:
                for p in self._cap_parc_data:
                    try: vp = _parse_valor(p["val"].get())
                    except: vp = 0.0
                    parcelas.append({
                        "numero": p["num"], "total": p["total"],
                        "dt_vencimento": p["dt"].get().strip(),
                        "valor": vp
                    })
            else:
                # Sem parcelamento — 1 parcela no vencimento
                ti = sum(i["valor"] for i in impostos)
                parcelas = [{
                    "numero": 1, "total": 1,
                    "dt_vencimento": self._cap_dt_venc.get().strip(),
                    "valor": valor_bruto - ti
                }]

            rateio = []
            total_pct = 0.0
            for r in self._cap_rat_rows:
                fil = r["filial"].get().strip()
                cat = r["cat"].get().strip()
                if not fil: continue
                try: pct = _parse_valor(r["pct"].get())
                except: pct = 0.0
                if pct > 0:
                    ti = sum(i["valor"] for i in impostos)
                    rateio.append({
                        "filial": fil, "categoria": cat,
                        "percentual": pct,
                        "valor": round((valor_bruto-ti)*pct/100, 2)
                    })
                    total_pct += pct

            # Dados base para salvar
            dados_base = {
                "tipo":          self._cap_tipo_var.get(),
                "fornecedor":    forn,
                "cnpj":          self._cap_cnpj.get().strip(),
                "empresa":       self._cap_emp_var.get(),
                "filial":        self._cap_filial_var.get(),
                "descricao":     self._cap_desc.get().strip(),
                "dt_emissao":    self._cap_dt_emissao.get().strip(),
                "dt_vencimento": self._cap_dt_venc.get().strip(),
                "valor_bruto":   valor_bruto,
                "valor_liquido": valor_bruto - sum(i["valor"] for i in impostos),
                "categoria":     self._cap_cat_var.get().strip(),
                "responsavel":   self._cap_resp.get().strip(),
                "observacao":    self._cap_obs.get().strip(),
                "cod_barras":    self._cap_cod_barras.get().strip(),
                "forma_pgto":    self._cap_forma_pgto.get().strip(),
                "banco_dest":    self._cap_banco_dest.get().strip(),
                "agencia_dest":  self._cap_ag_dest.get().strip(),
                "conta_dest":    self._cap_conta_dest.get().strip(),
                "pix_chave":     self._cap_pix_chave.get().strip(),
                "cpf_cnpj_dest": self._cap_cpf_cnpj_dest.get().strip(),
                
                # ERP Fields
                "tipo_operacao": self._cap_operacao_var.get(),
                "natureza":      self._cap_natureza_var.get(),
                "valor_difal":   _parse_valor(self._cap_difal.get()),
                "valor_fcp":     _parse_valor(self._cap_fcp.get()),
                "chave_ref":     self._cap_chave_ref.get().strip(),

                # Campo Nº NF separado
                "numero_nf":     getattr(self, "_cap_numero_nf", type('',(),{"get":lambda s: ""})()).get().strip(),
                "is_previsao":   1 if getattr(self, "_cap_is_previsao_var", tk.BooleanVar(value=False)).get() else 0,
                "conciliada":    0,

                "impostos":      impostos,
                "parcelas":      parcelas,
                "rateio":        rateio,
                "itens":         []
            }

            # ── CÓPIA DO ANEXO ──
            arq_path = getattr(self, "_cap_arquivo_path_var", tk.StringVar()).get()
            if arq_path and __import__('os').path.exists(arq_path):
                import os, shutil
                # Gera numero tx se nao tiver
                if not dados_base.get("numero_tx"):
                    dados_base["numero_tx"] = getattr(self, "_cap_editando_id", None) and f"TX_{getattr(self, '_cap_editando_id')}" or f"TX{int(time.time()*100)}"
                dt_venc = datetime.strptime(dados_base["dt_vencimento"], "%d/%m/%Y")
                dir_dest = os.path.join(config.BASE_DIR, "FINANCEIRO", "NOTAS", dt_venc.strftime("%Y_%m"))
                os.makedirs(dir_dest, exist_ok=True)
                # Não copia se já estiver na pasta
                if not arq_path.startswith(dir_dest):
                    ext = os.path.splitext(arq_path)[1]
                    new_path = os.path.join(dir_dest, f"{dados_base['numero_tx']}{ext}")
                    try:
                        shutil.copy2(arq_path, new_path)
                        dados_base["arquivo_path"] = new_path
                    except Exception as e:
                        logger.error(f"Erro ao copiar anexo: {e}")
                        dados_base["arquivo_path"] = arq_path
                else:
                    dados_base["arquivo_path"] = arq_path
            else:
                dados_base["arquivo_path"] = arq_path


            # Coleta Itens
            for ir in self._cap_item_rows:
                d = ir["desc"].get().strip()
                t = ir["total"].get().strip()
                if d or t:
                    dados_base["itens"].append({
                        "descricao": d,
                        "valor_total": _parse_valor(t)
                    })

            # ── DETECÇÃO DE DUPLICIDADE (HEURÍSTICA/FUZZY) ──
            if not getattr(self, "_cap_editando_id", None):
                cnpj_check = dados_base.get("cnpj","").strip()
                num_nf_check = dados_base.get("numero_nf","").strip()
                forn_check = dados_base.get("fornecedor","").strip().upper()
                valor_check = float(dados_base.get("valor_bruto", 0.0))
                
                try:
                    import difflib
                    from datetime import datetime
                    
                    todas = listar_notas() or []
                    dup_exata = None
                    dup_heuristica = None
                    
                    for n in todas:
                        if n.get("status","") == "CANCELADA":
                            continue
                            
                        n_cnpj = n.get("cnpj","").strip()
                        n_forn = n.get("fornecedor","").strip().upper()
                        n_num = n.get("numero_nf","").strip()
                        n_val = float(n.get("valor_bruto", 0.0) or 0.0)
                        
                        # 1. Match Exato (CNPJ + Num NF)
                        if cnpj_check and num_nf_check and n_cnpj == cnpj_check and n_num == num_nf_check:
                            dup_exata = n
                            break
                            
                        # 2. Match Heurístico (Valor Exato + CNPJ ou Nome Parecido) num curto período
                        if valor_check > 0 and n_val == valor_check:
                            # Tenta parsear datas para ver se estao próximas (ex: mesmo mes)
                            try:
                                dt1 = datetime.strptime(dados_base.get("dt_emissao",""), "%d/%m/%Y")
                                dt2 = datetime.strptime(n.get("dt_emissao","") or n.get("dt_vencimento",""), "%d/%m/%Y")
                                diff_dias = abs((dt1 - dt2).days)
                            except:
                                diff_dias = 0
                                
                            if diff_dias <= 45:
                                # CNPJ igual
                                if cnpj_check and n_cnpj == cnpj_check:
                                    dup_heuristica = n
                                # Ou Fornecedor Fuzzy (>85% de similaridade)
                                elif forn_check and n_forn:
                                    ratio = difflib.SequenceMatcher(None, forn_check, n_forn).ratio()
                                    if ratio > 0.85:
                                        dup_heuristica = n
                    
                    dup = dup_exata or dup_heuristica
                    if dup:
                        tipo_alerta = "Duplicidade EXATA" if dup_exata else "Possível Duplicidade (Valor e Fornecedor)"
                        resp = messagebox.askyesno(
                            f"⚠️ {tipo_alerta}",
                            f"O sistema detectou um lançamento muito similar:\n\n"
                            f"  Nº TX: {dup.get('numero_tx','')}\n"
                            f"  Fornecedor: {dup.get('fornecedor','')}\n"
                            f"  Data Base:  {dup.get('dt_vencimento','')}\n"
                            f"  Valor: R$ {dup.get('valor_bruto',0):,.2f}\n"
                            f"  Status: {dup.get('status','')}\n\n"
                            f"Deseja salvar a nova nota mesmo assim?")
                        if not resp:
                            self._cap_lbl_save.config(
                                text="⚠️ Salvamento cancelado — duplicidade detectada.",
                                fg="#fbbf24")
                            return
                except Exception as e:
                    logger.error(f"Erro no motor anti-duplicidade: {e}")

            # ── MODO EDICAO (UPDATE) ──
            editando_id = getattr(self, "_cap_editando_id", None)
            if editando_id:
                try:
                    with db_conn() as conn:
                        conn.execute("""
                            UPDATE notas SET
                                fornecedor=?, cnpj=?, descricao=?, numero_nf=?, arquivo_path=?,
                                dt_emissao=?, dt_vencimento=?, valor_bruto=?, valor_liquido=?,
                                categoria=?, responsavel=?, empresa=?, observacao=?,
                                natureza=?, tipo_operacao=?, valor_difal=?,
                                forma_pgto=?, banco_dest=?, agencia_dest=?,
                                conta_dest=?, pix_chave=?, cpf_cnpj_dest=?, chave_ref=?
                            WHERE id=?""",
                            (dados_base["fornecedor"],  dados_base["cnpj"],
                             dados_base["descricao"],   dados_base.get("numero_nf",""), dados_base.get("arquivo_path",""),
                             dados_base["dt_emissao"],  dados_base["dt_vencimento"],
                             dados_base["valor_bruto"], dados_base["valor_liquido"],
                             dados_base["categoria"],   dados_base["responsavel"],
                             dados_base["empresa"],     dados_base["observacao"],
                             dados_base.get("natureza",""),
                             dados_base.get("tipo_operacao","DESPESA"),
                             dados_base.get("valor_difal",0),
                             dados_base.get("forma_pgto",""),
                             dados_base.get("banco_dest",""),
                             dados_base.get("agencia_dest",""),
                             dados_base.get("conta_dest",""),
                             dados_base.get("pix_chave",""),
                             dados_base.get("cpf_cnpj_dest",""),
                             dados_base.get("chave_ref",""),
                             editando_id)
                        )
                    self._cap_editando_id = None
                    self._cap_lbl_save.config(
                        text=f"Nota #{editando_id} atualizada!", fg="#4ade80")
                    try: self._cap_lbl_form_titulo.config(text=" Nova Nota / Despesa")
                    except: pass
                except Exception as e_upd:
                    self._cap_lbl_save.config(
                        text=f"Erro ao atualizar: {e_upd}", fg="#dc2626")
                    return
            # ── MODO INSERÇÃO (padrão) ──
            elif self._cap_recorr_var.get():
                meses = int(self._cap_recorr_meses.get())
                id_recorr = f"REC_{int(time.time())}"
                
                from dateutil.relativedelta import relativedelta
                dt_base = datetime.strptime(dados_base["dt_vencimento"], "%d/%m/%Y")
                
                for m in range(meses):
                    d_mes = dados_base.copy()
                    dt_venc = dt_base + relativedelta(months=m)
                    d_mes["dt_vencimento"] = dt_venc.strftime("%d/%m/%Y")
                    d_mes["numero_tx"] = f"{d_mes.get('numero_tx','')}_{m+1}" if m > 0 else d_mes.get('numero_tx')
                    d_mes["recorrente"] = 1
                    d_mes["id_recorrencia"] = id_recorr
                    
                    # Ajusta vencimento das parcelas se houver
                    if d_mes["parcelas"]:
                        for p in d_mes["parcelas"]:
                            dt_p = datetime.strptime(p["dt_vencimento"], "%d/%m/%Y") + relativedelta(months=m)
                            p["dt_vencimento"] = dt_p.strftime("%d/%m/%Y")
                    
                    salvar_nota(d_mes)
                
                self._cap_lbl_save.config(
                    text=f"{meses} Notas recorrentes salvas!", fg="#4ade80")
            else:
                numero_tx = salvar_nota(dados_base)
                self._cap_lbl_save.config(
                    text=f"Nota salva com sucesso! Nº: {numero_tx}", fg="#4ade80")

            # Limpa campos
            for w in [self._cap_forn, self._cap_cnpj, self._cap_desc,
                       self._cap_valor, self._cap_obs, self._cap_dt_venc,
                       self._cap_cod_barras, self._cap_pix_chave,
                       self._cap_banco_dest, self._cap_ag_dest,
                       self._cap_conta_dest, self._cap_cpf_cnpj_dest,
                       self._cap_difal, self._cap_fcp, self._cap_chave_ref]:
                w.delete(0,"end")
            self._cap_difal.insert(0,"0,00")
            self._cap_fcp.insert(0,"0,00")
            self._cap_cat_var.set("")
            self._cap_recorr_var.set(False)
            for r in self._cap_imp_rows:
                r["val"].set(""); r["aliq"].set("")
            for w in self._cap_parc_widgets:
                w.destroy()
            self._cap_parc_widgets = []
            
            # Limpa Itens
            for row in self._cap_item_rows:
                row["desc"].set(""); row["total"].set("")
            # Deixa apenas uma linha limpa se houver muitas
            if len(self._cap_item_rows) > 1:
                # Aqui precisaria destruir os widgets, mas para simplificar vamos apenas limpar as vars
                pass

            if hasattr(self,"_cap_parc_data"):
                self._cap_parc_data = []

            # Volta para a lista e atualiza
            self._cap_select_tab(0)
            self._cap_carregar_lista()

        except Exception as e:
            self._cap_lbl_save.config(text=f"Erro: {e}", fg="#dc2626")


    # ── SUB-ABA: ADIANTAMENTOS ────────────────────────────────────────────────
    def _cap_build_adiantamentos(self, parent, bg, surface, accent, green, yellow, text, muted):

        tk.Label(parent, text="💰  Adiantamentos",
                 font=("Segoe UI",16,"bold"), fg="#f8fafc", bg="#020617"
                 ).pack(anchor="w", padx=20, pady=(15,8))

        # Formulário
        frm = tk.LabelFrame(parent, text="  Novo Adiantamento  ", bg="#0a0f1e",
                             fg="#f8fafc", font=("Segoe UI",11,"bold"), padx=15, pady=12)
        frm.pack(fill="x", padx=20, pady=(0,10))

        def lbl(t): return tk.Label(frm, text=t, fg="#f8fafc", bg="#0a0f1e",
                                     font=("Segoe UI",11))
        def ent(w=20):
            return ctk.CTkEntry(frm, font=("Segoe UI",12), fg_color="#0a0a0a", text_color="#ffffff",
                         border_color="#27272a", border_width=1, corner_radius=6, width=w*9, height=32)

        lbl("Beneficiário:").grid(row=0,column=0,sticky="w",pady=6)
        self._ad_benef = ent(35)
        self._ad_benef.grid(row=0,column=1,padx=(0,15),sticky="w")

        lbl("CPF/CNPJ:").grid(row=0,column=2,sticky="w")
        self._ad_cpf = ent(22)
        self._ad_cpf.grid(row=0,column=3,sticky="w")

        lbl("Tipo:").grid(row=1,column=0,sticky="w",pady=6)
        self._ad_tipo = ctk.CTkComboBox(frm,
            values=["FUNCIONARIO","FORNECEDOR"],
            state="readonly", width=162, height=32, font=("Segoe UI",12), fg_color="#0a0a0a", border_color="#27272a", border_width=1, button_color="#27272a", dropdown_fg_color="#141414")
        self._ad_tipo.set("FUNCIONARIO")
        self._ad_tipo.grid(row=1,column=1,sticky="w",padx=(0,15))

        lbl("Empresa:").grid(row=1,column=2,sticky="w")
        self._ad_emp = ctk.CTkComboBox(frm,
            values=["LALUA","SOLAR"],
            state="readonly", width=108, height=32, font=("Segoe UI",12), fg_color="#0a0a0a", border_color="#27272a", border_width=1, button_color="#27272a", dropdown_fg_color="#141414")
        self._ad_emp.set("LALUA")
        self._ad_emp.grid(row=1,column=3,sticky="w")

        lbl("Finalidade:").grid(row=2,column=0,sticky="w",pady=3)
        self._ad_final = ent(40)
        self._ad_final.grid(row=2,column=1,columnspan=3,sticky="w")

        lbl("Valor:").grid(row=3,column=0,sticky="w",pady=3)
        self._ad_valor = ent(14)
        self._ad_valor.grid(row=3,column=1,sticky="w",padx=(0,12))
        _aplicar_mascara_valor(self._ad_valor)

        lbl("Data:").grid(row=3,column=2,sticky="w")
        self._ad_dt = ent(11)
        self._ad_dt.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self._ad_dt.grid(row=3,column=3,sticky="w")
        _aplicar_mascara_data(self._ad_dt)

        self._ad_lbl = tk.Label(frm, text="", fg="#f8fafc", bg="#0a0f1e", font=("Segoe UI",9))
        self._ad_lbl.grid(row=4,column=0,columnspan=4,sticky="w",pady=4)

        def _salvar_ad():
            try:
                benef = self._ad_benef.get().strip()
                valor = _parse_valor(self._ad_valor.get())
                if not benef:
                    self._ad_lbl.config(text="⚠️ Informe o beneficiário.", fg="#fbbf24")
                    return
                tx = salvar_adiantamento({
                    "beneficiario": benef,
                    "cpf_cnpj":     self._ad_cpf.get().strip(),
                    "tipo":         self._ad_tipo.get(),
                    "finalidade":   self._ad_final.get().strip(),
                    "empresa":      self._ad_emp.get(),
                    "valor":        valor,
                    "dt_adiantamento": self._ad_dt.get().strip(),
                })
                self._ad_lbl.config(text=f"Adiantamento salvo: {tx}", fg="#f8fafc")
                self._ad_benef.delete(0,"end")
                self._ad_valor.delete(0,"end")
                self._ad_final.delete(0,"end")
                _reload_ad()
            except Exception as e:
                self._ad_lbl.config(text=f"{e}", fg="#dc2626")

        tk.Button(frm, text="Salvar Adiantamento",
                  font=("Segoe UI",9,"bold"), bg=accent, fg="white",
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
                  command=_salvar_ad).grid(row=5,column=0,columnspan=4,
                                            sticky="e", pady=(4,0))

        # Lista de adiantamentos
        tk.Label(parent, text="📋 Adiantamentos em aberto",
                 font=("Segoe UI",9,"bold"), fg="#f8fafc", bg="#020617"
                 ).pack(anchor="w", padx=20, pady=(4,2))

        cols = ("Nº TX","Beneficiário","Tipo","Empresa","Data","Valor","Saldo","Status","Finalidade")
        self._ad_tree = ttk.Treeview(parent, style="DS.Treeview", columns=cols, show="headings", height=8)
        largs = [100,180,100,70,90,100,100,80,200]
        for c,w in zip(cols,largs):
            self._ad_tree.heading(c,text=c)
            self._ad_tree.column(c,width=w,
                anchor="e" if c in ("Valor","Saldo") else "w")
        self._ad_tree.tag_configure("ABERTO",  foreground="#fbbf24")
        self._ad_tree.tag_configure("PARCIAL", foreground="#38bdf8")
        self._ad_tree.tag_configure("QUITADO", foreground="#4ade80")

        sb_ad = ttk.Scrollbar(parent, orient="vertical", command=self._ad_tree.yview)
        self._ad_tree.configure(yscrollcommand=sb_ad.set)
        self._ad_tree.pack(side="left", fill="both", expand=True, padx=(20,0), pady=(0,10))
        sb_ad.pack(side="left", fill="y", pady=(0,10))

        def _reload_ad():
            for r in self._ad_tree.get_children():
                self._ad_tree.delete(r)
            for a in listar_adiantamentos():
                self._ad_tree.insert("", "end", iid=str(a["id"]),
                    tags=(a["status"],),
                    values=(a["numero_tx"], a["beneficiario"],
                            a["tipo"], a["empresa"],
                            a["dt_adiantamento"],
                            f"R$ {a['valor']:,.2f}",
                            f"R$ {a['saldo_aberto']:,.2f}",
                            a["status"], a["finalidade"]))

        self._ad_reload = _reload_ad
        _reload_ad()


    # ── SUB-ABA: PRESTAÇÃO DE CONTAS ─────────────────────────────────────────
    def _cap_build_prestacao(self, parent, bg, surface, accent, green, yellow, text, muted):

        tk.Label(parent, text=" Prestação de Contas",
                 font=("Segoe UI",12,"bold"), fg="#f8fafc", bg="#020617"
                 ).pack(anchor="w", padx=20, pady=(12,4))
        tk.Label(parent, text="Selecione o adiantamento e vincule as despesas realizadas.",
                 font=("Segoe UI",9), fg="#64748b", bg="#020617"
                 ).pack(anchor="w", padx=20, pady=(0,8))

        frm = tk.LabelFrame(parent, text="  Registrar Prestação  ", bg="#0a0f1e",
                             fg="#f8fafc", font=("Segoe UI",9,"bold"), padx=14, pady=10)
        frm.pack(fill="x", padx=20, pady=(0,8))

        def lbl(t): return tk.Label(frm, text=t, fg="#94a3b8", bg="#0a0f1e",
                                     font=("Segoe UI",8))
        def ent(w=20):
            return ctk.CTkEntry(frm, font=("Segoe UI",12), fg_color="#0a0a0a", text_color="#ffffff",
                         border_color="#27272a", border_width=1, corner_radius=6, width=w*9, height=32)

        lbl("Adiantamento (Nº TX):").grid(row=0,column=0,sticky="w",pady=3)
        self._pr_ad_var = tk.StringVar()
        ads = listar_adiantamentos(status="ABERTO")
        opts = [f"{a['numero_tx']} — {a['beneficiario']} (R$ {a['saldo_aberto']:,.2f})"
                for a in ads] + \
               [f"{a['numero_tx']} — {a['beneficiario']} (R$ {a['saldo_aberto']:,.2f})"
                for a in listar_adiantamentos(status="PARCIAL")]
        self._pr_ad_ids = {f"{a['numero_tx']} — {a['beneficiario']} (R$ {a['saldo_aberto']:,.2f})":
                            a["id"] for a in ads}
        self._pr_ad_ids.update({
            f"{a['numero_tx']} — {a['beneficiario']} (R$ {a['saldo_aberto']:,.2f})":
            a["id"] for a in listar_adiantamentos(status="PARCIAL")
        })
        self._pr_ad_cb = ctk.CTkComboBox(frm, variable=self._pr_ad_var,
                     values=opts or [""], state="readonly",
                     width=405, height=32, font=("Segoe UI",12),
                     fg_color="#0a0a0a", border_color="#27272a", border_width=1, button_color="#27272a", dropdown_fg_color="#141414")
        self._pr_ad_cb.grid(row=0,column=1,columnspan=3,sticky="w",padx=(0,8))

        lbl("Descrição despesa:").grid(row=1,column=0,sticky="w",pady=3)
        self._pr_desc = ent(35)
        self._pr_desc.grid(row=1,column=1,columnspan=2,sticky="w",padx=(0,8))

        lbl("Nº Nota (opcional):").grid(row=1,column=3,sticky="w")
        self._pr_nota_var = tk.StringVar()
        self._pr_nota_cb = ctk.CTkComboBox(frm, variable=self._pr_nota_var,
                     values=[f"{n['numero_tx']} - {n['fornecedor']}"
                             for n in listar_notas(status="PENDENTE")] or ["Nenhuma"],
                     state="normal", width=198, height=32, font=("Segoe UI",12),
                     fg_color="#0a0a0a", border_color="#27272a", border_width=1, button_color="#27272a", dropdown_fg_color="#141414")
        self._pr_nota_cb.grid(row=1,column=4,sticky="w")

        lbl("Valor aplicado:").grid(row=2,column=0,sticky="w",pady=3)
        self._pr_val_ap = ent(12)
        self._pr_val_ap.grid(row=2,column=1,sticky="w",padx=(0,12))

        lbl("Valor devolvido:").grid(row=2,column=2,sticky="w")
        self._pr_val_dev = ent(12)
        self._pr_val_dev.insert(0,"0,00")
        self._pr_val_dev.grid(row=2,column=3,sticky="w",padx=(0,12))

        lbl("Observação:").grid(row=3,column=0,sticky="w",pady=3)
        self._pr_obs = ent(50)
        self._pr_obs.grid(row=3,column=1,columnspan=4,sticky="w")

        self._pr_lbl = tk.Label(frm, text="", fg="#f8fafc", bg="#0a0f1e", font=("Segoe UI",9))
        self._pr_lbl.grid(row=4,column=0,columnspan=5,sticky="w",pady=4)

        def _salvar_pr():
            try:
                sel = self._pr_ad_var.get()
                if not sel:
                    self._pr_lbl.config(text="⚠️ Selecione o adiantamento.", fg="#fbbf24")
                    return
                ad_id = self._pr_ad_ids.get(sel)
                val_ap  = _parse_valor(self._pr_val_ap.get())
                val_dev = _parse_valor(self._pr_val_dev.get() or "0")

                nota_id = None
                nota_str = self._pr_nota_var.get().strip()
                if nota_str:
                    tx = nota_str.split(" - ")[0].strip()
                    with db_conn() as conn:
                        row = conn.execute(
                            "SELECT id FROM notas WHERE numero_tx=?", (tx,)
                        ).fetchone()
                        if row: nota_id = row[0]

                registrar_prestacao(ad_id, nota_id, val_ap, val_dev,
                                     self._pr_desc.get().strip(),
                                     self._pr_obs.get().strip())
                self._pr_lbl.config(text="Prestação registrada!", fg="#f8fafc")
                for w in [self._pr_desc, self._pr_val_ap, self._pr_obs]:
                    w.delete(0,"end")
                self._pr_val_dev.delete(0,"end")
                self._pr_val_dev.insert(0,"0,00")
            except Exception as e:
                self._pr_lbl.config(text=f"{e}", fg="#dc2626")

        tk.Button(frm, text="Registrar Prestação",
                  font=("Segoe UI",9,"bold"), bg="#7c3aed", fg="white",
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
                  command=_salvar_pr).grid(row=5,column=0,columnspan=5,
                                            sticky="e", pady=(4,0))


    # ── SUB-ABA: IMPOSTOS RETIDOS ─────────────────────────────────────────────
    def _cap_build_impostos(self, parent, bg, surface, accent, green, yellow, text, muted):

        tk.Label(parent, text="🏛️  Impostos Retidos — Conferência e Baixa",
                 font=("Segoe UI",12,"bold"), fg="#f8fafc", bg="#020617"
                 ).pack(anchor="w", padx=20, pady=(12,4))
        tk.Label(parent,
                 text="Todos os impostos destacados nas notas aparecem aqui para conferência e baixa.",
                 font=("Segoe UI",9), fg="#64748b", bg="#020617"
                 ).pack(anchor="w", padx=20, pady=(0,8))

        # Toolbar
        tb = tk.Frame(parent, bg="#0a0f1e", pady=6, padx=14)
        tb.pack(fill="x", padx=0)

        tk.Label(tb, text="Status:", fg="#94a3b8", bg="#0a0f1e",
                 font=("Segoe UI",8)).pack(side="left")
        self._imp_filtro = ttk.Combobox(tb,
            values=["TODOS","PENDENTE","PAGO"],
            state="readonly", width=9, font=("Segoe UI",8))
        self._imp_filtro.set("PENDENTE")
        self._imp_filtro.pack(side="left", padx=(2,10))

        tk.Button(tb, text="Atualizar",
                  font=("Segoe UI",8), bg="#0a0f1e", fg="#f8fafc",
                  relief="flat", bd=0, padx=8, pady=3, cursor="hand2",
                  command=self._imp_carregar).pack(side="left", padx=(0,8))

        tk.Button(tb, text="Marcar PAGO",
                  font=("Segoe UI",8,"bold"), bg="#7c3aed", fg="white",
                  relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
                  command=self._imp_marcar_pago).pack(side="right")

        # Treeview
        cols = ("ID Imp","Nº TX","Fornecedor","Tipo Imp","Alíquota",
                "Valor","Venc. DARF","Status","Nº Doc")
        self._imp_tree = ttk.Treeview(parent, style="DS.Treeview", columns=cols,
                                       show="headings", height=12)
        largs = [60,110,200,100,80,100,100,80,120]
        for c,w in zip(cols,largs):
            self._imp_tree.heading(c,text=c)
            self._imp_tree.column(c,width=w,
                anchor="e" if c in ("Valor","Alíquota") else "w")
        self._imp_tree.tag_configure("PENDENTE", foreground="#fbbf24")
        self._imp_tree.tag_configure("PAGO",     foreground="#4ade80")

        sb_i = ttk.Scrollbar(parent, orient="vertical", command=self._imp_tree.yview)
        self._imp_tree.configure(yscrollcommand=sb_i.set)

        # Rodapé totais
        rod = tk.Frame(parent, bg="#0a0f1e", pady=4, padx=14)
        rod.pack(fill="x", side="bottom")
        self._imp_lbl_total = tk.Label(rod, text="", font=("Consolas",8),
                                        fg="#94a3b8", bg="#0a0f1e")
        self._imp_lbl_total.pack(side="left")

        self._imp_tree.pack(side="left", fill="both", expand=True,
                             padx=(20,0), pady=(0,0))
        sb_i.pack(side="left", fill="y")
        self._imp_carregar()


    def _imp_carregar(self):
        for r in self._imp_tree.get_children():
            self._imp_tree.delete(r)

        st = self._imp_filtro.get()
        sql = """
            SELECT ni.id, n.numero_tx, n.fornecedor,
                   ni.tipo, ni.aliquota, ni.valor,
                   ni.dt_venc_imp, ni.status, ni.numero_doc
            FROM nota_impostos ni
            JOIN notas n ON n.id = ni.nota_id
            WHERE 1=1
        """
        params = []
        if st != "TODOS":
            sql += " AND ni.status=?"; params.append(st)
        sql += " ORDER BY ni.dt_venc_imp ASC"

        total = 0.0
        with db_conn() as conn:
            for row in conn.execute(sql, params).fetchall():
                tag = row[7] if row[7] in ("PENDENTE","PAGO") else "PENDENTE"
                self._imp_tree.insert("", "end", iid=str(row[0]), tags=(tag,),
                    values=(row[0], row[1], row[2][:28],
                            row[3], f"{row[4]:.2f}%",
                            f"R$ {row[5]:,.2f}",
                            row[6] or "", row[7], row[8] or ""))
                if tag == "PENDENTE":
                    total += row[5]

        self._imp_lbl_total.config(
            text=f"Total pendente: R$ {total:,.2f}")


    def _imp_marcar_pago(self):
        sel = self._imp_tree.selection()
        if not sel: return
        with db_conn() as conn:
            for iid in sel:
                conn.execute(
                    "UPDATE nota_impostos SET status='PAGO' WHERE id=?",
                    (int(iid),))
        self._imp_carregar()


    # ── SUB-ABA: FORNECEDORES ────────────────────────────────────────────────
    def _cap_build_fornecedores(self, parent, bg, surface, accent, green, yellow, text, muted):

        # ── TOOLBAR ──
        tb = tk.Frame(parent, bg="#0a0f1e", pady=6, padx=14)
        tb.pack(fill="x")

        tk.Label(tb, text="🏢 Cadastro de Fornecedores",
                 font=("Segoe UI",12,"bold"), fg="#f8fafc", bg="#0a0f1e"
                 ).pack(side="left", padx=(0,16))

        self._forn_busca_var = tk.StringVar()
        tk.Entry(tb, textvariable=self._forn_busca_var,
                 font=("Segoe UI",8), bg="#0a0f1e", fg="#f8fafc",
                         insertbackground=accent, relief="flat", bd=2, width=22
                 ).pack(side="left", padx=(0,4))

        tk.Button(tb, text="🔍", font=("Segoe UI",9),
                  bg="#0a0f1e", fg="#f8fafc", relief="flat", bd=0,
                  padx=6, pady=3, cursor="hand2",
                  command=self._forn_carregar).pack(side="left", padx=(0,10))

        self._forn_filtro_ativo = tk.BooleanVar(value=True)
        tk.Checkbutton(tb, text="Só ativos", variable=self._forn_filtro_ativo,
                       bg="#0a0f1e", fg="#94a3b8", font=("Segoe UI",8),
                       selectcolor="#0a0f1e",
                       command=self._forn_carregar).pack(side="left", padx=(0,10))

        tk.Button(tb, text="Novo Fornecedor",
                  font=("Segoe UI",8,"bold"), bg=accent, fg="#0f172a",
                  relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
                  command=self._forn_novo).pack(side="right")

        # ── TREEVIEW ──
        cols = ("ID","Razão Social","Nome Fantasia","CNPJ/CPF","Tipo",
                "Empresa","Categoria","Responsável","PIX","Contato")
        self._forn_tree = ttk.Treeview(parent, columns=cols,
                                        style="DS.Treeview", show="headings", height=12)
        largs = [40,220,140,130,90,70,170,120,160,130]
        for c, w in zip(cols, largs):
            self._forn_tree.heading(c, text=c)
            self._forn_tree.column(c, width=w, anchor="w")

        self._forn_tree.tag_configure("ativo",   foreground="#e2e8f0")
        self._forn_tree.tag_configure("inativo",  foreground="#475569")

        sb = ttk.Scrollbar(parent, orient="vertical", command=self._forn_tree.yview)
        sbx = ttk.Scrollbar(parent, orient="horizontal", command=self._forn_tree.xview)
        self._forn_tree.configure(yscrollcommand=sb.set, xscrollcommand=sbx.set)

        self._forn_tree.bind("<Double-1>", self._forn_editar)

        # ── RODAPÉ ──
        rod = tk.Frame(parent, bg="#0a0f1e", pady=5, padx=14)
        rod.pack(fill="x", side="bottom")
        self._forn_lbl_count = tk.Label(rod, text="", font=("Consolas",8),
                                         fg="#94a3b8", bg="#0a0f1e")
        self._forn_lbl_count.pack(side="left")
        tk.Button(rod, text="✏️ Editar", font=("Segoe UI",8),
                  bg="#0a0f1e", fg="#f8fafc", relief="flat", bd=0,
                  padx=8, pady=3, cursor="hand2",
                  command=self._forn_editar).pack(side="right", padx=(4,0))
        tk.Button(rod, text="🚫 Inativar", font=("Segoe UI",8),
                  bg="#fee2e2", fg="#dc2626", relief="flat", bd=0,
                  padx=8, pady=3, cursor="hand2",
                  command=self._forn_inativar).pack(side="right", padx=(4,0))
        tk.Button(rod, text="🗑 Excluir", font=("Segoe UI",8),
                  bg="#450a0a", fg="#dc2626", relief="flat", bd=0,
                  padx=8, pady=3, cursor="hand2",
                  command=self._forn_excluir).pack(side="right", padx=(4,0))

        sbx.pack(side="bottom", fill="x", padx=20)
        self._forn_tree.pack(side="left", fill="both", expand=True, padx=(20,0))
        sb.pack(side="left", fill="y")

        self._forn_carregar()


    def _forn_carregar(self):
        for r in self._forn_tree.get_children():
            self._forn_tree.delete(r)

        busca   = self._forn_busca_var.get().strip()
        ativos  = self._forn_filtro_ativo.get()
        fornecs = listar_fornecedores(busca=busca, ativo_only=ativos)

        for f in fornecs:
            tag = "ativo" if f["ativo"] else "inativo"
            self._forn_tree.insert("", "end", iid=str(f["id"]), tags=(tag,),
                values=(f["id"], f["razao_social"], f["nome_fantasia"] or "",
                        f["cnpj_cpf"] or "", f["tipo"], f["empresa"],
                        f["categoria"] or "", f["responsavel"] or "",
                        f["pix_chave"] or "", f["contato"] or ""))

        self._forn_lbl_count.config(text=f"{len(fornecs)} fornecedor(es)")


    def _forn_novo(self):
        self._forn_abrir_form(None)


    def _forn_editar(self, event=None):
        sel = self._forn_tree.selection()
        if not sel: return
        forn_id = int(sel[0])
        with db_conn() as conn:
            conn.row_factory = sqlite3.Row
            f = conn.execute("SELECT * FROM fornecedores WHERE id=?",
                             (forn_id,)).fetchone()
        if f:
            self._forn_abrir_form(dict(f))


    def _forn_inativar(self):
        sel = self._forn_tree.selection()
        if not sel: return
        with db_conn() as conn:
            for iid in sel:
                conn.execute("UPDATE fornecedores SET ativo=0 WHERE id=?",
                             (int(iid),))
        self._forn_carregar()


    def _forn_excluir(self):
        sel = self._forn_tree.selection()
        if not sel: return

        # Pega nome(s) para mostrar na confirmação
        nomes = []
        for iid in sel:
            vals = self._forn_tree.item(iid, "values")
            nomes.append(vals[1] if vals else f"ID {iid}")

        from tkinter import messagebox
        msg = f"Excluir permanentemente:\n\n" + "\n".join(nomes)
        if len(nomes) > 1:
            msg += f"\n\n({len(nomes)} fornecedores)"
        msg += "\n\nEsta ação não pode ser desfeita."

        if not messagebox.askyesno("Confirmar exclusão", msg,
                                    icon="warning", default="no"):
            return

        with db_conn() as conn:
            for iid in sel:
                conn.execute("DELETE FROM fornecedores WHERE id=?", (int(iid),))
        self._forn_carregar()


    def _forn_abrir_form(self, dados=None):
        """Abre janela modal para cadastro/edição de fornecedor."""
        win = tk.Toplevel(self.root)
        win.title("Fornecedor" if not dados else f"Editar — {dados.get('razao_social','')}")
        win.geometry("620x580")
        win.configure(bg="#0f172a")
        win.grab_set()

        bg    = "#000000"
        surf  = "#111111"
        acc   = "#a3e635"
        txt   = "#e2e8f0"
        mut   = "#94a3b8"

        tk.Label(win, text="🏢  Cadastro de Fornecedor",
                 font=("Segoe UI",12,"bold"), fg=acc, bg="#020617"
                 ).pack(anchor="w", padx=20, pady=(14,8))

        frm = tk.Frame(win, bg=surf, padx=16, pady=12)
        frm.pack(fill="x", padx=20)

        def lbl(t, r, c):
            tk.Label(frm, text=t, fg=mut, bg=surf,
                     font=("Segoe UI",8), anchor="w"
                     ).grid(row=r, column=c, sticky="w", pady=3, padx=(0,4))

        def ent(r, c, w=25, val="", cs=1):
            e = tk.Entry(frm, font=("Segoe UI",9), bg="#0a0f1e", fg=txt,
                         insertbackground=acc, relief="flat", bd=2, width=w)
            e.grid(row=r, column=c, columnspan=cs, sticky="w", padx=(0,8))
            if val: e.insert(0, val)
            return e

        def cbx(r, c, values, val="", w=14):
            v = tk.StringVar(value=val)
            cb = ttk.Combobox(frm, textvariable=v, values=values,
                              state="readonly", width=w, font=("Segoe UI",8))
            cb.grid(row=r, column=c, sticky="w", padx=(0,8), pady=3)
            return v

        d = dados or {}

        lbl("Razão Social *", 0, 0)
        e_rs = ent(0, 1, 30, d.get("razao_social",""), cs=3)

        lbl("Nome Fantasia", 1, 0)
        e_nf = ent(1, 1, 30, d.get("nome_fantasia",""), cs=3)

        lbl("CNPJ/CPF *", 2, 0)
        e_cnpj = ent(2, 1, 18, d.get("cnpj_cpf",""))

        lbl("Tipo", 2, 2)
        v_tipo = cbx(2, 3, ["FORNECEDOR","PRESTADOR","FUNCIONARIO"],
                     d.get("tipo","FORNECEDOR"), w=13)

        lbl("Empresa", 3, 0)
        v_emp = cbx(3, 1, ["LALUA","SOLAR"], d.get("empresa","LALUA"), w=8)

        lbl("Filial Padrão", 3, 2)
        v_filial = tk.StringVar(value=d.get("filial_padrao",""))
        ttk.Combobox(frm, textvariable=v_filial, values=config.FILIAIS_RATEIO,
                     state="normal", width=16, font=("Segoe UI",8)
                     ).grid(row=3, column=3, sticky="w", padx=(0,8), pady=3)

        lbl("Categoria Padrão", 4, 0)
        v_cat = tk.StringVar(value=d.get("categoria",""))
        ttk.Combobox(frm, textvariable=v_cat, values=config.CATEGORIAS_LISTA,
                     state="normal", width=32, font=("Segoe UI",8)
                     ).grid(row=4, column=1, columnspan=3, sticky="w", pady=3)

        lbl("Responsável Padrão", 5, 0)
        v_resp = tk.StringVar(value=d.get("responsavel",""))
        ttk.Combobox(frm, textvariable=v_resp, values=config.RESPONSAVEIS_LISTA,
                     state="readonly", width=16, font=("Segoe UI",8)
                     ).grid(row=5, column=1, sticky="w", pady=3)

        lbl("Contato", 5, 2)
        e_contato = ent(5, 3, 20, d.get("contato",""))

        lbl("E-mail", 6, 0)
        e_email = ent(6, 1, 28, d.get("email",""), cs=3)

        # Dados bancários
        tk.Label(frm, text="── Dados Bancários ──", fg="#94a3b8", bg=surf,
                 font=("Segoe UI",7)).grid(row=7, column=0, columnspan=4,
                                            sticky="w", pady=(8,2))

        lbl("Banco", 8, 0)
        e_banco = ent(8, 1, 20, d.get("banco",""))

        lbl("Agência", 8, 2)
        e_ag = ent(8, 3, 10, d.get("agencia",""))

        lbl("Conta", 9, 0)
        e_ct = ent(9, 1, 16, d.get("conta",""))

        lbl("Chave PIX", 9, 2)
        e_pix = ent(9, 3, 22, d.get("pix_chave",""))

        # Status
        v_ativo = tk.BooleanVar(value=bool(d.get("ativo", 1)))
        tk.Checkbutton(frm, text="Fornecedor ativo",
                       variable=v_ativo, bg=surf, fg=txt,
                       selectcolor="#0a0f1e", font=("Segoe UI",8)
                       ).grid(row=10, column=0, columnspan=2,
                               sticky="w", pady=(8,0))

        lbl_save = tk.Label(win, text="", font=("Segoe UI",9),
                            fg=acc, bg="#020617")
        lbl_save.pack(anchor="w", padx=20, pady=4)

        def _salvar():
            rs = e_rs.get().strip()
            if not rs:
                lbl_save.config(text="⚠️ Razão Social obrigatória.", fg="#fbbf24")
                return
            payload = {
                "razao_social":  rs,
                "nome_fantasia": e_nf.get().strip(),
                "cnpj_cpf":      e_cnpj.get().strip(),
                "tipo":          v_tipo.get(),
                "empresa":       v_emp.get(),
                "filial_padrao": v_filial.get(),
                "categoria":     v_cat.get(),
                "responsavel":   v_resp.get(),
                "contato":       e_contato.get().strip(),
                "email":         e_email.get().strip(),
                "banco":         e_banco.get().strip(),
                "agencia":       e_ag.get().strip(),
                "conta":         e_ct.get().strip(),
                "pix_chave":     e_pix.get().strip(),
                "ativo":         int(v_ativo.get()),
            }
            forn_id = dados.get("id") if dados else None
            salvar_fornecedor(payload, forn_id)
            lbl_save.config(text="Salvo com sucesso!", fg="#4ade80")
            self._forn_carregar()
            win.after(800, win.destroy)

        btn_f = tk.Frame(win, bg="#020617")
        btn_f.pack(fill="x", padx=20, pady=(0,12))
        tk.Button(btn_f, text="💾 Salvar",
                  font=("Segoe UI",10,"bold"), bg="#7c3aed", fg="white",
                  relief="flat", bd=0, padx=16, pady=7, cursor="hand2",
                  command=_salvar).pack(side="right", padx=(6,0))
        tk.Button(btn_f, text="❌ Cancelar",
                  font=("Segoe UI",9), bg=surf, fg=mut,
                  relief="flat", bd=0, padx=12, pady=7, cursor="hand2",
                  command=win.destroy).pack(side="right")


    # ── SUB-ABA: CNAB 240 ────────────────────────────────────────────────────
    def _cap_build_cnab(self, parent, bg, surface, accent, green, yellow, text, muted):

        tk.Label(parent, text="🏦  Gerador CNAB 240 — Itaú",
                 font=("Segoe UI",12,"bold"), fg="#f8fafc", bg="#020617"
                 ).pack(anchor="w", padx=20, pady=(12,2))
        tk.Label(parent,
                 text="Gera arquivo de remessa para envio ao Itaú Empresas. "
                      "Um arquivo por empresa. Suba no Sispag → Cobrança/Pagamento → Remessa.",
                 font=("Segoe UI",8), fg="#94a3b8", bg="#020617"
                 ).pack(anchor="w", padx=20, pady=(0,8))

        # ── CONFIGURAÇÕES ──
        cfg = tk.LabelFrame(parent, text="  Configurações  ", bg="#0a0f1e",
                             fg="#f8fafc", font=("Segoe UI",9,"bold"),
                             padx=14, pady=10)
        cfg.pack(fill="x", padx=20, pady=(0,8))

        def lbl(t): return tk.Label(cfg, text=t, fg="#94a3b8", bg="#0a0f1e",
                                     font=("Segoe UI",8))

        lbl("Empresa:").grid(row=0, column=0, sticky="w", pady=3)
        self._cnab_empresa = ttk.Combobox(cfg,
            values=["LALUA","SOLAR","AS DUAS (arquivos separados)"],
            state="readonly", width=28, font=("Segoe UI",9))
        self._cnab_empresa.set("LALUA")
        self._cnab_empresa.grid(row=0, column=1, sticky="w", padx=(0,20))

        lbl("Fonte dos pagamentos:").grid(row=0, column=2, sticky="w")
        self._cnab_fonte = ttk.Combobox(cfg,
            values=["Notas lançadas (Contas a Pagar)",
                    "Autorização de Pagamentos (carregada)"],
            state="readonly", width=35, font=("Segoe UI",9))
        self._cnab_fonte.set("Notas lançadas (Contas a Pagar)")
        self._cnab_fonte.grid(row=0, column=3, sticky="w")

        lbl("Filtrar vencimento:").grid(row=1, column=0, sticky="w", pady=3)
        self._cnab_dt_de = tk.Entry(cfg, font=("Segoe UI",9),
                                     bg="#0a0f1e", fg="#f8fafc",
                         insertbackground=accent,
                                     relief="flat", bd=2, width=11)
        self._cnab_dt_de.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self._cnab_dt_de.grid(row=1, column=1, sticky="w", padx=(0,6))
        _aplicar_mascara_data(self._cnab_dt_de)

        lbl("até:").grid(row=1, column=2, sticky="w")
        self._cnab_dt_ate = tk.Entry(cfg, font=("Segoe UI",9),
                                      bg="#0a0f1e", fg="#f8fafc",
                         insertbackground=accent,
                                      relief="flat", bd=2, width=11)
        self._cnab_dt_ate.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self._cnab_dt_ate.grid(row=1, column=3, sticky="w")
        _aplicar_mascara_data(self._cnab_dt_ate)

        lbl("Nº Remessa:").grid(row=2, column=0, sticky="w", pady=3)
        self._cnab_num_rem = tk.Spinbox(cfg, from_=1, to=9999,
                                         width=6, font=("Segoe UI",9),
                                         bg="#0a0f1e", fg="#f8fafc",
                         insertbackground=accent,
                                         relief="flat", bd=2)
        self._cnab_num_rem.grid(row=2, column=1, sticky="w")

        lbl("Pasta de saída:").grid(row=2, column=2, sticky="w")
        self._cnab_pasta_var = tk.StringVar(value=config.PASTA_ATUAL)
        tk.Entry(cfg, textvariable=self._cnab_pasta_var,
                 font=("Consolas",8), bg="#0a0f1e", fg="#f8fafc",
                         insertbackground=accent, relief="flat", bd=2, width=35
                 ).grid(row=2, column=3, sticky="w", padx=(0,6))
        tk.Button(cfg, text="📂", font=("Segoe UI",8),
                  bg="#0a0f1e", fg="#f8fafc", relief="flat", bd=0, cursor="hand2",
                  command=self._cnab_selecionar_pasta
                  ).grid(row=2, column=4, padx=(0,4))

        # ── PREVIEW DE PAGAMENTOS ──
        tk.Label(parent, text="📋 Pagamentos que serão incluídos no arquivo:",
                 font=("Segoe UI",9,"bold"), fg="#f8fafc", bg="#020617"
                 ).pack(anchor="w", padx=20, pady=(4,2))

        cols = ("Tipo","Fornecedor/Beneficiário","CNPJ","Vencimento",
                "Valor","Empresa","Código Barras / Chave")
        self._cnab_tree = ttk.Treeview(parent, style="DS.Treeview", columns=cols,
                                        show="headings", height=12)
        largs = [80,200,130,90,100,70,220]
        for c, w in zip(cols, largs):
            self._cnab_tree.heading(c, text=c)
            self._cnab_tree.column(c, width=w,
                anchor="e" if c=="Valor" else "w")

        self._cnab_tree.tag_configure("BOLETO", foreground="#38bdf8")
        self._cnab_tree.tag_configure("PIX",    foreground="#4ade80")
        self._cnab_tree.tag_configure("TED",    foreground="#a78bfa")
        self._cnab_tree.tag_configure("DARF",   foreground="#fbbf24")
        self._cnab_tree.tag_configure("GPS",    foreground="#fb923c")
        self._cnab_tree.tag_configure("DAS",    foreground="#f472b6")
        self._cnab_tree.tag_configure("CONC",   foreground="#94a3b8")

        sb = ttk.Scrollbar(parent, orient="vertical",
                            command=self._cnab_tree.yview)
        self._cnab_tree.configure(yscrollcommand=sb.set)

        # Rodapé
        rod = tk.Frame(parent, bg="#0a0f1e", pady=6, padx=14)
        rod.pack(fill="x", side="bottom")

        self._cnab_lbl_status = tk.Label(rod, text="",
                                          font=("Segoe UI",9,"bold"),
                                          fg="#94a3b8", bg="#0a0f1e")
        self._cnab_lbl_status.pack(side="left")

        tk.Button(rod, text="📄 GERAR CNAB 240",
                  font=("Segoe UI",10,"bold"), bg=accent, fg="white",
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2",
                  command=self._cnab_gerar).pack(side="right", padx=(6,0))

        tk.Button(rod, text="Carregar preview",
                  font=("Segoe UI",9), bg="#0a0f1e", fg="#f8fafc",
                  relief="flat", bd=0, padx=12, pady=7, cursor="hand2",
                  command=self._cnab_carregar_preview).pack(side="right")

        self._cnab_tree.pack(side="left", fill="both", expand=True,
                              padx=(20,0), pady=(0,0))
        sb.pack(side="left", fill="y")

        # Guarda pagamentos carregados
        self._cnab_pagamentos = []


    def _cnab_selecionar_pasta(self):
        from tkinter import filedialog
        p = filedialog.askdirectory(title="Pasta para o arquivo CNAB")
        if p:
            self._cnab_pasta_var.set(p)


    def _cnab_carregar_preview(self):
        """Carrega os pagamentos conforme filtros e mostra na treeview."""
        for r in self._cnab_tree.get_children():
            self._cnab_tree.delete(r)
        self._cnab_pagamentos = []

        empresa = self._cnab_empresa.get()
        fonte   = self._cnab_fonte.get()
        dt_de   = self._cnab_dt_de.get().strip()
        dt_ate  = self._cnab_dt_ate.get().strip()

        try:
            from datetime import datetime as dt_cls
            d_de  = dt_cls.strptime(dt_de,  "%d/%m/%Y") if dt_de  else None
            d_ate = dt_cls.strptime(dt_ate, "%d/%m/%Y") if dt_ate else None
        except:
            self._cnab_lbl_status.config(
                text="⚠️ Data inválida.", fg="#fbbf24")
            return

        emps = ["LALUA","SOLAR"] if "DUAS" in empresa else [empresa]
        pgtos = []

        if "Notas" in fonte:
            # Carrega das notas aprovadas/pendentes no banco
            for emp in emps:
                notas = listar_notas(status=None, empresa=emp)
                for n in notas:
                    if n["status"] in ("CANCELADA","PAGA"):
                        continue
                    # Filtra por vencimento
                    try:
                        dv = datetime.strptime(n["dt_vencimento"], "%d/%m/%Y")
                        if d_de  and dv < d_de:  continue
                        if d_ate and dv > d_ate: continue
                    except: pass

                    # Determina tipo de pagamento
                    cat = (n["categoria"] or "").upper()
                    desc = (n["descricao"] or "").upper()
                    if "DARF" in desc or "IRRF" in cat or "IRRF" in desc:
                        tp = "DARF"
                    elif "GPS" in desc or "INSS" in cat:
                        tp = "GPS"
                    elif "DAS" in desc or "SIMPLES" in desc:
                        tp = "DAS"
                    elif "ENERGIA" in cat or "ÁGUA" in cat or "CONCESS" in cat:
                        tp = "CONC"
                    elif "PIX" in desc:
                        tp = "PIX"
                    else:
                        tp = "BOLETO"

                    # Busca dados do fornecedor
                    forn = buscar_fornecedor_por_cnpj(n["cnpj"]) or {}
                    pix_chave = dict(forn).get("pix_chave","") if forn else ""
                    banco     = dict(forn).get("banco","") if forn else ""
                    agencia   = dict(forn).get("agencia","") if forn else ""
                    conta     = dict(forn).get("conta","") if forn else ""

                    pgto = {
                        "tipo_pgto":      tp,
                        "nome":           n["fornecedor"],
                        "cpf_cnpj_dest":  n["cpf_cnpj_dest"] or n["cnpj"],
                        "cnpj_pagador":   config.CNAB_CONTAS[emp]["cnpj"],
                        "nome_benef":     n["fornecedor"],
                        "valor":          n["valor_liquido"],
                        "dt_vencimento":  n["dt_vencimento"],
                        "dt_pagamento":   n["dt_vencimento"],
                        "empresa":        emp,
                        "nota_id":        n["id"],
                        "numero_tx":      n["numero_tx"],
                        "banco_dest":     n["banco_dest"] or banco or "341",
                        "agencia_dest":   n["agencia_dest"] or agencia or "0",
                        "conta_dest":     n["conta_dest"] or conta or "0",
                        "chave_pix":      n["pix_chave"] or pix_chave,
                        "cod_barras":     n["cod_barras"] or "",
                    }
                    pgtos.append(pgto)

        else:
            # Carrega da autorização de pagamentos já carregada na aba
            if hasattr(self, "_aut_pagamentos") and self._aut_pagamentos:
                for p in self._aut_pagamentos:
                    emp = p.get("empresa","LALUA")
                    if emp not in emps:
                        continue
                    try:
                        dv = datetime.strptime(p.get("data",""), "%d/%m/%Y")
                        if d_de  and dv < d_de:  continue
                        if d_ate and dv > d_ate: continue
                    except: pass

                    tipo_raw = p.get("tipo","").upper()
                    if "BOLETO" in tipo_raw:
                        tp = "BOLETO"
                    elif "PIX QR" in tipo_raw:
                        tp = "BOLETO"
                    elif "PIX" in tipo_raw:
                        tp = "PIX"
                    elif "TED" in tipo_raw:
                        tp = "TED"
                    elif "DARF" in tipo_raw:
                        tp = "DARF"
                    elif "DAS" in tipo_raw:
                        tp = "DAS"
                    elif "CONCESS" in tipo_raw or "TRIBUTO" in tipo_raw:
                        tp = "CONC"
                    else:
                        tp = "BOLETO"

                    forn = buscar_fornecedor_por_cnpj(p.get("cnpj","")) or {}
                    pgto = {
                        "tipo_pgto":      tp,
                        "nome":           p.get("nome",""),
                        "cpf_cnpj_dest":  p.get("cnpj",""),
                        "cnpj_pagador":   config.CNAB_CONTAS[emp]["cnpj"],
                        "nome_benef":     p.get("nome",""),
                        "valor":          p.get("valor",0),
                        "dt_vencimento":  p.get("data",""),
                        "dt_pagamento":   p.get("data",""),
                        "empresa":        emp,
                        "banco_dest":     dict(forn).get("banco","341") if forn else "341",
                        "agencia_dest":   dict(forn).get("agencia","0") if forn else "0",
                        "conta_dest":     dict(forn).get("conta","0") if forn else "0",
                        "chave_pix":      dict(forn).get("pix_chave","") if forn else "",
                        "cod_barras":     "",
                    }
                    pgtos.append(pgto)

        # Preenche treeview
        total = 0.0
        for p in pgtos:
            val = _parse_valor(p.get("valor",0))
            total += val
            self._cnab_tree.insert("", "end", tags=(p["tipo_pgto"],),
                values=(
                    p["tipo_pgto"],
                    p["nome"][:30],
                    p.get("cpf_cnpj_dest","")[:18],
                    p.get("dt_vencimento",""),
                    f"R$ {val:,.2f}",
                    p.get("empresa",""),
                    p.get("cod_barras","") or p.get("chave_pix",""),
                ))

        self._cnab_pagamentos = pgtos
        self._cnab_lbl_status.config(
            text=f"{len(pgtos)} pagamento(s)  |  "
                 f"Total: R$ {total:,.2f}",
            fg="#4ade80" if pgtos else "#fbbf24")


    def _cnab_gerar(self):
        if not self._cnab_pagamentos:
            self._cnab_lbl_status.config(
                text="⚠️ Carregue o preview primeiro.", fg="#fbbf24")
            return

        empresa  = self._cnab_empresa.get()
        pasta    = self._cnab_pasta_var.get().strip()
        num_rem  = int(self._cnab_num_rem.get())

        try:
            num_rem = int(self._cnab_num_rem.get())
        except:
            num_rem = 1

        os.makedirs(pasta, exist_ok=True)
        emps = ["LALUA","SOLAR"] if "DUAS" in empresa else [empresa]
        arquivos_gerados = []

        for emp in emps:
            pgtos_emp = [p for p in self._cnab_pagamentos
                         if p.get("empresa","LALUA") == emp]
            if not pgtos_emp:
                continue

            dt_str   = datetime.now().strftime("%Y%m%d_%H%M")
            # Nome máximo 8 chars + .rem (padrão Sispag Itaú)
            # Ex: LAL00001.rem / SOL00001.rem
            prefixo = "LAL" if emp == "LALUA" else "SOL"
            nome_arq = f"{prefixo}{str(num_rem).zfill(5)}.rem"
            caminho  = os.path.join(pasta, nome_arq)

            ok, resultado = gerar_cnab240(pgtos_emp, emp, caminho, num_rem)
            if ok:
                arquivos_gerados.append(nome_arq)
            else:
                self._cnab_lbl_status.config(
                    text=f"Erro {emp}: {resultado}", fg="#dc2626")
                return

        if arquivos_gerados:
            msg = f"Gerado: {', '.join(arquivos_gerados)}"
            self._cnab_lbl_status.config(text=msg, fg="#4ade80")
            # Abre a pasta
            try:
                os.startfile(pasta)
            except: pass


    def _cap_build_alertas(self, parent, bg, surface, accent, green, yellow, text, muted):
        """Constrói a interface da central de alertas de vencimentos."""
        
        frm_topo = tk.Frame(parent, bg="#020617", pady=15)
        frm_topo.pack(fill="x", padx=20)
        
        tk.Label(frm_topo, text="🔔 Central de Alertas e Vencimentos",
                 font=("Segoe UI",16,"bold"), fg="#f8fafc", bg="#020617"
                 ).pack(side="left")
        
        tk.Button(frm_topo, text="🔄 Atualizar Alertas",
                  font=("Segoe UI",11,"bold"), bg="#0a0f1e", fg="#f8fafc",
                  relief="flat", bd=0, padx=15, pady=6, cursor="hand2",
                  command=self._cap_carregar_alertas).pack(side="right")

        # Container para os cards de resumo
        frm_resumo = tk.Frame(parent, bg="#020617")
        frm_resumo.pack(fill="x", padx=20, pady=10)
        
        def card(parent, title, color):
            f = tk.Frame(parent, bg="#0a0f1e", highlightbackground=color, highlightthickness=2, padx=20, pady=15)
            f.pack(side="left", padx=(0,20), expand=True, fill="both")
            tk.Label(f, text=title, fg="#f8fafc", bg="#0a0f1e", font=("Segoe UI",10,"bold")).pack(anchor="w")
            v = tk.Label(f, text="R$ 0,00", fg=color, bg="#0a0f1e", font=("Segoe UI",16,"bold"))
            v.pack(anchor="w", pady=(4,0))
            n = tk.Label(f, text="0 itens", fg="#94a3b8", bg="#0a0f1e", font=("Segoe UI",9))
            n.pack(anchor="w")
            return v, n

        self._lbl_alerta_atrasado_val, self._lbl_alerta_atrasado_cnt = card(frm_resumo, "ATRASADOS", "#f87171")
        self._lbl_alerta_hoje_val, self._lbl_alerta_hoje_cnt = card(frm_resumo, "VENCENDO HOJE", "#fb923c")
        self._lbl_alerta_semana_val, self._lbl_alerta_semana_cnt = card(frm_resumo, "PRÓX. 7 DIAS", "#fbbf24")

        # Tabela de alertas detalhados
        tk.Label(parent, text="📋 Detalhamento de Pendências:",
                 font=("Segoe UI",11,"bold"), fg="#f8fafc", bg="#020617"
                 ).pack(anchor="w", padx=20, pady=(20,8))

        cols = ("Vencimento","Natureza","Fornecedor/Imposto","Descrição","Valor","Empresa","Nº TX")
        self._alerta_tree = ttk.Treeview(parent, style="DS.Treeview", columns=cols, show="headings", height=15)
        largs = [100,100,200,250,120,80,120]
        for c, w in zip(cols, largs):
            self._alerta_tree.heading(c, text=c)
            self._alerta_tree.column(c, width=w, anchor="e" if c=="Valor" else "w")

        self._alerta_tree.tag_configure("ATRASADO", foreground="#f87171")
        self._alerta_tree.tag_configure("HOJE",     foreground="#fb923c")
        self._alerta_tree.tag_configure("SEMANA",   foreground="#fbbf24")

        sb = ttk.Scrollbar(parent, orient="vertical", command=self._alerta_tree.yview)
        self._alerta_tree.configure(yscrollcommand=sb.set)
        
        self._alerta_tree.pack(side="left", fill="both", expand=True, padx=(20,0), pady=(0,15))
        sb.pack(side="left", fill="y", pady=(0,15), padx=(0,20))

        # Ação rápida
        rod = tk.Frame(parent, bg="#0a0f1e", pady=10, padx=16)
        rod.pack(fill="x", side="bottom")
        tk.Button(rod, text="✅ Marcar Selecionados como PAGO",
                  font=("Segoe UI",11,"bold"), bg="#7c3aed", fg="white",
                  relief="flat", bd=0, padx=20, pady=8, cursor="hand2",
                  command=lambda: self._cap_mudar_status_alerta("PAGA")).pack(side="right")

        self._cap_carregar_alertas()

    def _cap_carregar_alertas(self):
        """Busca no banco todas as notas pendentes e classifica para os alertas."""
        for r in self._alerta_tree.get_children():
            self._alerta_tree.delete(r)
            
        hoje = date.today()
        proximos_7 = hoje + timedelta(days=7)
        
        v_atrasado = v_hoje = v_semana = 0.0
        c_atrasado = c_hoje = c_semana = 0
        
        # Busca todas as pendentes
        notas = listar_notas(status="PENDENTE")
        
        for n in notas:
            try:
                dt_venc = datetime.strptime(n["dt_vencimento"], "%d/%m/%Y").date()
            except: continue
            
            valor = n["valor_bruto"]
            tag = ""
            
            if dt_venc < hoje:
                tag = "ATRASADO"
                v_atrasado += valor
                c_atrasado += 1
            elif dt_venc == hoje:
                tag = "HOJE"
                v_hoje += valor
                c_hoje += 1
            elif hoje < dt_venc <= proximos_7:
                tag = "SEMANA"
                v_semana += valor
                c_semana += 1
            else:
                continue # Fora do range de alertas imediatos
                
            self._alerta_tree.insert("", "end", iid=str(n["id"]), tags=(tag,),
                values=(
                    n["dt_vencimento"],
                    n.get("natureza","VENDA"),
                    n["fornecedor"][:25],
                    (n.get("descricao") or "")[:35],
                    f"R$ {valor:,.2f}",
                    n["empresa"],
                    n["numero_tx"]
                ))
        
        # Atualiza Cards
        self._lbl_alerta_atrasado_val.config(text=f"R$ {v_atrasado:,.2f}")
        self._lbl_alerta_atrasado_cnt.config(text=f"{c_atrasado} itens")
        
        self._lbl_alerta_hoje_val.config(text=f"R$ {v_hoje:,.2f}")
        self._lbl_alerta_hoje_cnt.config(text=f"{c_hoje} itens")
        
        self._lbl_alerta_semana_val.config(text=f"R$ {v_semana:,.2f}")
        self._lbl_alerta_semana_cnt.config(text=f"{c_semana} itens")

    def _cap_mudar_status_alerta(self, status):
        sel = self._alerta_tree.selection()
        if not sel: return
        for iid in sel:
            atualizar_status_nota(int(iid), status)
        self._cap_carregar_alertas()
        self._cap_carregar_lista()
