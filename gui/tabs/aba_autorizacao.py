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
from datetime import datetime, date
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
class AbaAutorizacao(BaseTab):

    # ==========================================================================
    # ── ABA 7: AUTORIZAÇÃO DE PAGAMENTOS ──────────────────────────────────
    # ==========================================================================

    def build(self, parent, bg, surface, border, accent, green, yellow, text, muted):
        self._aut_pagamentos = []
        self._aut_itens_tree = []

        # ── Paleta interna moderna ──
        BG      = "#020617"
        CARD    = "#0f172a"
        BORDER  = "#1e293b"
        BORDER_L= "#334155"
        ACCENT  = "#f8fafc"
        MUTED   = "#64748b"
        TEXT    = "#f8fafc"
        GREEN   = "#10b981"
        YELLOW  = "#eab308"
        BLUE    = "#3b82f6"

        # ══════════════════════════════════════════════════════
        # HEADER — título + badge de período
        # ══════════════════════════════════════════════════════
        hdr = ctk.CTkFrame(parent, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 12))

        ctk.CTkLabel(
            hdr, text="Autorização de Pagamentos",
            font=("Segoe UI", 22, "bold"), text_color=ACCENT
        ).pack(side="left")

        self._aut_lbl_periodo = ctk.CTkLabel(
            hdr, text="", font=("Segoe UI", 11), text_color=YELLOW
        )
        self._aut_lbl_periodo.pack(side="left", padx=(16, 0), pady=4)

        # ══════════════════════════════════════════════════════
        # CARD ÚNICO COMPACTO: ARQUIVOS & PERÍODO
        # ══════════════════════════════════════════════════════
        card_top = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8,
                                 border_width=1, border_color=BORDER)
        card_top.pack(fill="x", padx=16, pady=(8, 8))

        # LINHA 1: ARQUIVOS
        row1 = ctk.CTkFrame(card_top, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(8, 4))

        self._aut_path_forn  = tk.StringVar()
        self._aut_path_solar = tk.StringVar()
        self._aut_path_folha = tk.StringVar()

        def _file_block(parent_frame, lbl, var):
            f = ctk.CTkFrame(parent_frame, fg_color="transparent")
            f.pack(side="left", expand=True, fill="x", padx=(0, 16))
            ctk.CTkLabel(f, text=lbl, font=("Segoe UI", 9, "bold"),
                         text_color=MUTED).pack(side="left", padx=(0,6))
            ctk.CTkEntry(f, textvariable=var, font=("Consolas", 9), height=26,
                         fg_color=BG, border_color=BORDER, border_width=1,
                         text_color=TEXT).pack(side="left", expand=True, fill="x", padx=(0,4))
            ctk.CTkButton(f, text="📂", width=28, height=26, fg_color=BORDER,
                          hover_color="#333333", text_color=ACCENT,
                          command=lambda v=var: self._aut_selecionar_arquivo(v)
                          ).pack(side="left")

        _file_block(row1, "LALUA:", self._aut_path_forn)
        _file_block(row1, "SOLAR:", self._aut_path_solar)
        _file_block(row1, "FOLHA:", self._aut_path_folha)

        # LINHA 2: PERÍODO E BOTÕES
        row2 = ctk.CTkFrame(card_top, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(4, 8))

        self._aut_lbl_status = ctk.CTkLabel(row2, text="", font=("Segoe UI", 10), text_color=MUTED)
        self._aut_lbl_status.pack(side="left", padx=(0, 16))

        ctrls = ctk.CTkFrame(row2, fg_color="transparent")
        ctrls.pack(side="right")

        ctk.CTkLabel(ctrls, text="PERÍODO:", font=("Segoe UI", 9, "bold"),
                     text_color=MUTED).pack(side="left", padx=(0,6))
        
        self._aut_de = ctk.CTkEntry(ctrls, font=("Segoe UI", 10), width=90, height=28,
                                     fg_color=BG, border_color=BORDER, border_width=1)
        self._aut_de.pack(side="left")
        
        ctk.CTkLabel(ctrls, text="→", font=("Segoe UI", 10), text_color=MUTED).pack(side="left", padx=4)
        
        self._aut_ate = ctk.CTkEntry(ctrls, font=("Segoe UI", 10), width=90, height=28,
                                      fg_color=BG, border_color=BORDER, border_width=1)
        self._aut_ate.pack(side="left", padx=(0,12))

        ctk.CTkButton(ctrls, text="📅 Auto", width=80, height=28, fg_color="#1e293b",
                      hover_color="#334155", text_color=ACCENT, font=("Segoe UI", 9),
                      command=self._aut_sugerir_periodo).pack(side="left", padx=(0,6))
                      
        ctk.CTkButton(ctrls, text="📂 Histórico", width=90, height=28, fg_color="#0f172a",
                      hover_color="#1e293b", text_color=ACCENT, font=("Segoe UI", 9),
                      command=self._aut_abrir_historico).pack(side="left", padx=(0,12))
        
        ctk.CTkButton(ctrls, text="⚡ Carregar & Classificar", width=150, height=28,
                      fg_color=ACCENT, hover_color="#d4d4d4", text_color="#000000",
                      font=("Segoe UI", 9, "bold"), command=self._aut_carregar).pack(side="left")

        # Os botões de PDF foram movidos para a barra de resumo/totais.

        # ══════════════════════════════════════════════════════
        # PAINEL DE EDIÇÃO RÁPIDA (bottom)
        # ══════════════════════════════════════════════════════
        frame_ed = ctk.CTkFrame(parent, fg_color="#0f0f0f", corner_radius=0,
                                 border_width=1, border_color=BORDER, height=56)
        frame_ed.pack(fill="x", padx=0, side="bottom")
        frame_ed.pack_propagate(False)

        inner_ed = ctk.CTkFrame(frame_ed, fg_color="transparent")
        inner_ed.pack(fill="both", expand=True, padx=16, pady=8)

        ctk.CTkLabel(inner_ed, text="✏️  EDITAR SELECIONADO",
                     font=("Segoe UI", 9, "bold"), text_color=MUTED
                     ).pack(side="left", padx=(0, 16))

        def _ed_label(t):
            ctk.CTkLabel(inner_ed, text=t, font=("Segoe UI", 9),
                         text_color=MUTED).pack(side="left", padx=(0, 4))

        # Responsável
        _ed_label("Responsável:")
        self._aut_edit_resp = ctk.CTkComboBox(inner_ed, values=config.RESPONSAVEIS_LISTA,
                                              width=120, height=30, font=("Segoe UI", 10),
                                              fg_color=BG, border_color=BORDER, border_width=1,
                                              button_color=BORDER, button_hover_color=MUTED,
                                              dropdown_fg_color=CARD, dropdown_text_color=TEXT,
                                              text_color=TEXT, state="readonly")
        self._aut_edit_resp.pack(side="left", padx=(0, 12))

        # Categoria — com filtro
        _ed_label("Categoria:")
        
        self._aut_busca_cat = tk.StringVar()
        entry_busca = ctk.CTkEntry(inner_ed, textvariable=self._aut_busca_cat,
                                   font=("Segoe UI", 9), width=100, height=26,
                                   fg_color=BG, border_color=BORDER, border_width=1,
                                   corner_radius=4, placeholder_text="🔍 filtrar...")
        entry_busca.pack(side="left", padx=(0, 4))

        self._aut_edit_cat = ctk.CTkComboBox(inner_ed, values=config.CATEGORIAS_LISTA,
                                             width=220, height=30, font=("Segoe UI", 10),
                                             fg_color=BG, border_color=BORDER, border_width=1,
                                             button_color=BORDER, button_hover_color=MUTED,
                                             dropdown_fg_color=CARD, dropdown_text_color=TEXT,
                                             text_color=TEXT, state="readonly")
        self._aut_edit_cat.pack(side="left", padx=(0, 12))

        def _filtrar_cats(*args):
            termo = self._aut_busca_cat.get().upper()
            if not termo:
                self._aut_edit_cat.configure(values=config.CATEGORIAS_LISTA)
            else:
                filtradas = [c for c in config.CATEGORIAS_LISTA if termo in c.upper()]
                self._aut_edit_cat.configure(values=filtradas)
                if filtradas:
                    self._aut_edit_cat.set(filtradas[0])

        self._aut_busca_cat.trace_add("write", _filtrar_cats)

        # Empresa
        _ed_label("Empresa:")
        self._aut_edit_emp = ctk.CTkComboBox(inner_ed, values=["LALUA", "SOLAR"],
                                             width=90, height=30, font=("Segoe UI", 10),
                                             fg_color=BG, border_color=BORDER, border_width=1,
                                             button_color=BORDER, button_hover_color=MUTED,
                                             dropdown_fg_color=CARD, dropdown_text_color=TEXT,
                                             text_color=TEXT, state="readonly")
        self._aut_edit_emp.pack(side="left", padx=(0, 12))

        # Descrição
        _ed_label("Descrição:")
        self._aut_edit_desc = ctk.CTkEntry(inner_ed, font=("Segoe UI", 9), width=200,
                                            height=30, fg_color=BG, border_color=BORDER,
                                            border_width=1, corner_radius=6, text_color=TEXT,
                                            placeholder_text="observação sobre o item...")
        self._aut_edit_desc.pack(side="left", padx=(0, 12))

        # Botões de ação
        ctk.CTkButton(inner_ed, text="✅  Aplicar", width=90, height=30,
                      fg_color=GREEN, hover_color="#16a34a",
                      text_color="#000000", corner_radius=8,
                      font=("Segoe UI", 9, "bold"),
                      command=self._aut_aplicar_edicao).pack(side="left", padx=(0, 6))

        ctk.CTkButton(inner_ed, text="🗑  Remover", width=90, height=30,
                      fg_color="#3f1010", hover_color="#7f1d1d",
                      text_color="#fca5a5", corner_radius=8,
                      font=("Segoe UI", 9),
                      command=self._aut_remover_linha).pack(side="left")

        # ══════════════════════════════════════════════════════
        # BARRA DE TOTAIS E AÇÕES (bottom)
        # ══════════════════════════════════════════════════════
        frame_resumo_fixo = ctk.CTkFrame(parent, fg_color="#050505", corner_radius=0,
                                          border_width=1, border_color=BORDER, height=56)
        frame_resumo_fixo.pack(side="bottom", fill="x")
        frame_resumo_fixo.pack_propagate(False)

        self._aut_lbl_resumo = ctk.CTkLabel(
            frame_resumo_fixo,
            text="💰  TOTAL: R$ 0,00   |   📦  0 itens",
            font=("Segoe UI", 11, "bold"), text_color=ACCENT
        )
        self._aut_lbl_resumo.pack(side="left", padx=20, pady=16)

        inner_bot = ctk.CTkFrame(frame_resumo_fixo, fg_color="transparent")
        inner_bot.pack(side="right", padx=16, pady=11)

        def _pdf_btn(txt, color, hover, cmd, side="right", text_color="#ffffff"):
            ctk.CTkButton(inner_bot, text=txt, height=34, corner_radius=8,
                          fg_color=color, hover_color=hover,
                          text_color=text_color, font=("Segoe UI", 9, "bold"),
                          command=cmd).pack(side=side, padx=4)

        _pdf_btn("📄 GERAR PDF",            "#ffffff",  "#d4d4d4",  self._aut_gerar_pdf, text_color="#000000")
        _pdf_btn("📊 Excel",                "#16a34a",  "#15803d",  self._gerar_relatorio_pagamentos_excel)
        _pdf_btn("🏢 PDF Filial→Matriz",    "#7c3aed",  "#6d28d9",  self._gerar_pdf_transferencia_filial)
        _pdf_btn("🏦 PDF Transferências",   "#0c4a6e",  "#075985",  self._gerar_pdf_transferencias)
        _pdf_btn("💸 Trans. Filiais",       "#1e293b",  "#334155",  self._gerar_pdf_transferencias_filiais)
        _pdf_btn("🔄 Reclassificar",        "#27272a",  "#3f3f46",  self._aut_popular_treeview)
        _pdf_btn("🕰️ Histórico",          "#b45309",  "#78350f",  self._aut_abrir_historico, side="left")

        # ══════════════════════════════════════════════════════
        # TREEVIEW
        # ══════════════════════════════════════════════════════
        tree_wrap = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0)
        tree_wrap.pack(fill="both", expand=True, padx=0, pady=0)

        cols = ("Favorecido", "CNPJ", "Tipo", "Data", "Valor",
                "Descrição", "Categoria", "Responsável", "Empresa")
        self._aut_tree = ttk.Treeview(tree_wrap, style="DS.Treeview",
                                       columns=cols, show="headings", height=20)
        larguras = [240, 130, 110, 85, 100, 160, 180, 130, 80]
        for col, w in zip(cols, larguras):
            self._aut_tree.heading(col, text=col,
                                    command=lambda c=col: self._aut_ordenar(c))
            self._aut_tree.column(col, width=w, anchor="w")
        self._aut_tree.column("Valor", anchor="e")

        self._aut_tree.tag_configure("ok",           background="#0f2d1a", foreground="#86efac")
        self._aut_tree.tag_configure("pendente",     background="#2d2a0f", foreground="#fde68a")
        self._aut_tree.tag_configure("a_classificar",background="#1a0f0f", foreground="#fca5a5")
        self._aut_tree.tag_configure("manual",       background="#0a0a0a", foreground="#818cf8")

        scroll_aut = ctk.CTkScrollbar(tree_wrap, orientation="vertical",
                                       command=self._aut_tree.yview)
        self._aut_tree.configure(yscrollcommand=scroll_aut.set)

        self._aut_tree.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=8)
        scroll_aut.pack(side="right", fill="y", padx=(0, 8), pady=8)

        self._aut_tree.bind("<Double-1>",        self._aut_editar_linha)
        self._aut_tree.bind("<<TreeviewSelect>>", self._aut_editar_linha)

        # Sugere período ao iniciar e recupera último relatório
        self._aut_sugerir_periodo()
        self._aut_carregar_ultimo_relatorio()





    def _aut_atualizar_resumo(self):
        """Atualiza o label de total no rodapé."""
        total = sum(p.get("valor", 0) for p in self._aut_itens_tree)
        count = len(self._aut_itens_tree)
        self._aut_lbl_resumo.configure(
            text=f"💰 TOTAL DO PERÍODO: R$ {total:,.2f} | 📦 {count} itens",
            text_color="#ffffff" if total > 0 else "#a1a1aa"
        )


    def _aut_remover_linha(self):
        """Remove linha(s) selecionada(s) da lista."""
        sels = self._aut_tree.selection()
        if not sels:
            return
        indices = sorted([self._aut_tree.index(s) for s in sels], reverse=True)
        for idx in indices:
            if 0 <= idx < len(self._aut_itens_tree):
                self._aut_itens_tree.pop(idx)
        self._aut_pagamentos = list(self._aut_itens_tree)
        self._aut_popular_treeview()


    def _aut_ordenar(self, coluna):
        """Ordena a treeview ao clicar no cabeçalho."""
        mapa = {
            "Favorecido": "nome", "CNPJ": "cnpj", "Tipo": "tipo",
            "Data": "data", "Valor": "valor", "Responsável": "responsavel",
            "Categoria": "categoria", "Empresa": "empresa"
        }
        chave = mapa.get(coluna, "nome")
        if not hasattr(self, "_aut_sort_col"):
            self._aut_sort_col = None
            self._aut_sort_rev = False
        if self._aut_sort_col == chave:
            self._aut_sort_rev = not self._aut_sort_rev
        else:
            self._aut_sort_col = chave
            self._aut_sort_rev = False
        self._aut_itens_tree.sort(
            key=lambda x: str(x.get(chave, "")),
            reverse=self._aut_sort_rev
        )
        self._aut_pagamentos = list(self._aut_itens_tree)
        self._aut_popular_treeview()


    def _aut_selecionar_arquivo(self, var):
        from tkinter import filedialog
        caminho = filedialog.askopenfilename(
            filetypes=[("Excel/XLS", "*.xls *.xlsx"), ("Todos", "*.*")]
        )
        if caminho:
            var.set(caminho)


    def _aut_sugerir_periodo(self):
        ini, fim, label = calcular_periodo_sugerido()
        self._aut_de.delete(0, "end")
        self._aut_de.insert(0, ini.strftime("%d/%m/%Y"))
        self._aut_ate.delete(0, "end")
        self._aut_ate.insert(0, fim.strftime("%d/%m/%Y"))
        self._aut_lbl_periodo.configure(text=f"📅 Sugerido: {label}")


    def _aut_carregar(self):
        path_forn  = self._aut_path_forn.get().strip()
        path_solar = self._aut_path_solar.get().strip()
        path_folha = self._aut_path_folha.get().strip()

        if not path_forn and not path_solar:
            self._aut_lbl_status.configure(text="⚠️ Selecione ao menos um arquivo.", text_color="#ffffff")
            return

        try:
            de_str  = self._aut_de.get().strip()
            ate_str = self._aut_ate.get().strip()
            dt_de   = datetime.strptime(de_str,  "%d/%m/%Y") if de_str  else datetime(2000,1,1)
            dt_ate  = datetime.strptime(ate_str, "%d/%m/%Y") if ate_str else datetime(2099,1,1)
        except:
            self._aut_lbl_status.configure(text="⚠️ Data inválida.", text_color="#ffffff")
            return

        self._aut_lbl_status.configure(text="⏳ Carregando...", text_color="#ffffff")
        self.root.update_idletasks()

        def carregar():
            try:
                pagamentos = []

                # LALUA
                if path_forn and os.path.exists(path_forn):
                    itens = ler_itau_pagamentos(path_forn)
                    for p in itens: p["empresa"] = "LALUA"
                    pagamentos += itens

                # SOLAR
                if path_solar and os.path.exists(path_solar):
                    itens_solar = ler_itau_pagamentos(path_solar)
                    for p in itens_solar: p["empresa"] = "SOLAR"
                    pagamentos += itens_solar

                # Folha
                if path_folha and os.path.exists(path_folha):
                    pagamentos += ler_itau_folha(path_folha)

                # Filtra
                filtrados = []
                for p in pagamentos:
                    if p.get("data_obj"):
                        if dt_de <= p["data_obj"] <= dt_ate:
                            filtrados.append(p)
                    else:
                        filtrados.append(p)

                self._aut_pagamentos = filtrados
                pre_count = len(pagamentos)
                
                def finalizar():
                    self._aut_lbl_status.configure(
                        text=f"✅ {pre_count} total | {len(filtrados)} no período", text_color="#ffffff")
                    self._aut_popular_treeview()
                
                self.root.after(0, finalizar)

            except Exception as e:
                self.root.after(0, lambda: self._aut_lbl_status.configure(
                    text=f"❌ Erro: {str(e)}", text_color="#a1a1aa"))

        threading.Thread(target=carregar, daemon=True).start()


    def _aut_popular_treeview(self):
        for row in self._aut_tree.get_children():
            self._aut_tree.delete(row)

        self._aut_itens_tree = list(self._aut_pagamentos)
        sem_cat = 0
        total   = 0.0

        for p in self._aut_itens_tree:
            cat  = p.get("categoria", "")
            resp = p.get("responsavel", "")
            desc = p.get("descricao", "")
            tag = "ok" if (cat and cat != "A CLASSIFICAR" and resp) else \
                  "a_classificar" if cat == "A CLASSIFICAR" else "pendente"
            if tag != "ok":
                sem_cat += 1
            total += p["valor"]

            self._aut_tree.insert("", "end", tags=(tag,), values=(
                p["nome"][:35],
                p["cnpj"],
                p["tipo"],
                p["data"],
                f"R$ {p['valor']:,.2f}",
                desc[:30],
                cat[:40],
                resp,
                p.get("empresa", "LALUA"),
            ))

        self._aut_lbl_resumo.configure(
            text=f"💰 TOTAL: R$ {total:,.2f}   |   📦 {len(self._aut_itens_tree)} itens   |   ⚠️ {sem_cat} pendentes",
            text_color="#ffffff" if sem_cat == 0 else "#ffffff"
        )
        # Salva o estado atual automaticamente
        self._aut_salvar_relatorio()


    def _aut_editar_linha(self, event=None):
        """Preenche o painel de edição com os valores da linha clicada."""
        sel = self._aut_tree.selection()
        if not sel:
            return
        idx = self._aut_tree.index(sel[0])
        p   = self._aut_itens_tree[idx]
        self._aut_edit_resp.set(p.get("responsavel", ""))
        self._aut_edit_cat.set(p.get("categoria", ""))
        self._aut_edit_emp.set(p.get("empresa", "LALUA"))
        self._aut_edit_desc.delete(0, "end")
        self._aut_edit_desc.insert(0, p.get("descricao", ""))


    def _aut_aplicar_edicao(self):
        """Aplica a edição do painel ao(s) item(ns) selecionado(s)."""
        sels = self._aut_tree.selection()
        if not sels:
            return
        resp = self._aut_edit_resp.get().strip()
        cat  = self._aut_edit_cat.get().strip()
        emp  = self._aut_edit_emp.get().strip()
        desc = self._aut_edit_desc.get().strip()

        for sel in sels:
            idx = self._aut_tree.index(sel)
            if resp: self._aut_itens_tree[idx]["responsavel"] = resp
            if cat:  self._aut_itens_tree[idx]["categoria"]   = cat
            if emp:  self._aut_itens_tree[idx]["empresa"]      = emp
            if desc: self._aut_itens_tree[idx]["descricao"]    = desc

            cnpj = self._aut_itens_tree[idx].get("cnpj", "").strip()
            nome = self._aut_itens_tree[idx].get("nome", "").strip().upper()
            
            if cat or resp:
                current_resp = self._aut_itens_tree[idx].get("responsavel", "")
                current_cat  = self._aut_itens_tree[idx].get("categoria", "")
                current_desc = self._aut_itens_tree[idx].get("descricao", "")
                
                try:
                    import config
                    import json
                    import os
                    os.makedirs(config.DATA_DIR, exist_ok=True)
                    
                    if cnpj:
                        if not hasattr(config, "DB_FORNECEDORES_CATEGORIA"):
                            config.DB_FORNECEDORES_CATEGORIA = {}
                        config.DB_FORNECEDORES_CATEGORIA[cnpj] = [current_resp, current_cat, current_desc]
                        cat_path = os.path.join(config.DATA_DIR, 'fornecedores_categoria.json')
                        with open(cat_path, 'w', encoding='utf-8') as f:
                            json.dump(config.DB_FORNECEDORES_CATEGORIA, f, ensure_ascii=False, indent=4)
                    elif nome:
                        if not hasattr(config, "DB_FORNECEDORES_NOME"):
                            config.DB_FORNECEDORES_NOME = {}
                        config.DB_FORNECEDORES_NOME[nome] = [current_resp, current_cat, current_desc]
                        nome_path = os.path.join(config.DATA_DIR, 'fornecedores_nome.json')
                        with open(nome_path, 'w', encoding='utf-8') as f:
                            json.dump(config.DB_FORNECEDORES_NOME, f, ensure_ascii=False, indent=4)
                            
                except Exception as e:
                    import config
                    config.logger.error(f"Erro ao salvar regra: {e}")

        # Sincroniza com _aut_pagamentos
        self._aut_pagamentos = list(self._aut_itens_tree)
        self._aut_popular_treeview()


    # ────────────────────────────────────────────────────────────────────────────────
    # SALVAR / CARREGAR RELATÓRIO AUTOMÁTICO
    # ────────────────────────────────────────────────────────────────────────────────

    def _aut_salvar_relatorio(self):
        """Salva o relatório atual em JSON na pasta relatorios_autorizacao."""
        try:
            import json
            import config
            relatorios_dir = os.path.join(config.DATA_DIR, "relatorios_autorizacao")
            os.makedirs(relatorios_dir, exist_ok=True)
            
            data_atual = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            caminho = os.path.join(relatorios_dir, f"relatorio_autorizacao_{data_atual}.json")
            
            # Também mantemos o '_ultimo' para auto-load ao abrir o programa
            caminho_ultimo = os.path.join(config.PASTA_ATUAL, "_ultimo_relatorio_autorizacao.json")
            dados = []
            for p in self._aut_pagamentos:
                d = dict(p)
                # Serializa data_obj se presente
                if 'data_obj' in d and hasattr(d['data_obj'], 'isoformat'):
                    d['data_obj'] = d['data_obj'].isoformat()
                dados.append(d)
            
            conteudo = {
                'periodo_de':  self._aut_de.get() if hasattr(self, '_aut_de') else '',
                'periodo_ate': self._aut_ate.get() if hasattr(self, '_aut_ate') else '',
                'dados': dados,
                'salvo_em': datetime.now().isoformat()
            }
            
            with open(caminho, 'w', encoding='utf-8') as f:
                json.dump(conteudo, f, ensure_ascii=False, indent=2)
                
            with open(caminho_ultimo, 'w', encoding='utf-8') as f:
                json.dump(conteudo, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # Não bloqueia a operação principal

    def _aut_carregar_ultimo_relatorio(self):
        """Recupera o último relatório salvo e exibe na treeview."""
        try:
            import json
            caminho = os.path.join(config.PASTA_ATUAL, "_ultimo_relatorio_autorizacao.json")
            if not os.path.exists(caminho):
                return
            with open(caminho, 'r', encoding='utf-8') as f:
                estado = json.load(f)
            dados = estado.get('dados', [])
            if not dados:
                return
            # Restaura data_obj
            for d in dados:
                if 'data_obj' in d and isinstance(d['data_obj'], str):
                    try:
                        d['data_obj'] = datetime.fromisoformat(d['data_obj'])
                    except Exception:
                        d.pop('data_obj', None)
            self._aut_pagamentos = dados
            # Restaura período
            de  = estado.get('periodo_de', '')
            ate = estado.get('periodo_ate', '')
            if de and hasattr(self, '_aut_de'):
                self._aut_de.delete(0, 'end')
                self._aut_de.insert(0, de)
            if ate and hasattr(self, '_aut_ate'):
                self._aut_ate.delete(0, 'end')
                self._aut_ate.insert(0, ate)
            self._aut_popular_treeview()
            salvo_em = estado.get('salvo_em', '')[:16]
            if hasattr(self, '_aut_lbl_status'):
                self._aut_lbl_status.configure(
                    text=f"✅ Relatório restaurado (salvo em {salvo_em})", text_color="#4ade80")
        except Exception:
            pass  # Arquivo corrompido ou ausente, sem problema

    def _aut_abrir_historico(self):
        """Abre caixa de diálogo para carregar um relatório antigo."""
        import config
        from tkinter import filedialog
        import json
        
        relatorios_dir = os.path.join(config.DATA_DIR, "relatorios_autorizacao")
        os.makedirs(relatorios_dir, exist_ok=True)
        
        caminho = filedialog.askopenfilename(
            initialdir=relatorios_dir,
            title="Selecione o Relatório Anteriore",
            filetypes=[("Relatórios JSON", "*.json")]
        )
        
        if not caminho:
            return
            
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                estado = json.load(f)
            dados = estado.get('dados', [])
            if not dados:
                return
            # Restaura data_obj
            for d in dados:
                if 'data_obj' in d and isinstance(d['data_obj'], str):
                    try:
                        d['data_obj'] = datetime.fromisoformat(d['data_obj'])
                    except Exception:
                        d.pop('data_obj', None)
            self._aut_pagamentos = dados
            # Restaura período
            de  = estado.get('periodo_de', '')
            ate = estado.get('periodo_ate', '')
            if de and hasattr(self, '_aut_de'):
                self._aut_de.delete(0, 'end')
                self._aut_de.insert(0, de)
            if ate and hasattr(self, '_aut_ate'):
                self._aut_ate.delete(0, 'end')
                self._aut_ate.insert(0, ate)
            self._aut_popular_treeview()
            
            nome_arq = os.path.basename(caminho)
            if hasattr(self, '_aut_lbl_status'):
                self._aut_lbl_status.configure(
                    text=f"✅ {nome_arq} carregado", text_color="#4ade80")
        except Exception as e:
            config.logger.error(f"Erro ao carregar relatório antigo: {e}")


    def _gerar_pdf_transferencias(self):
        """PDF de transferências de filiais para a matriz — padrão BOAH."""
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import cm, mm
            from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                            Paragraph, Spacer, HRFlowable,
                                            KeepTogether, PageBreak)
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        except ImportError:
            self._aut_lbl_resumo.configure(
                text="❌ pip install reportlab", text_color="#a1a1aa")
            return

        # Coleta transferências filial→matriz dos pagamentos carregados
        transferencias = [p for p in self._aut_pagamentos
                          if "FILIAL" in p.get("tipo","").upper()
                          or "TRANSFERENCIA MATRIZ" in p.get("categoria","").upper()
                          or "FILIAL" in p.get("categoria","").upper()]

        # Se não houver, abre formulário para informar manualmente
        if not transferencias:
            self._aut_lbl_resumo.configure(
                text="ℹ️ Nenhuma transferência filial→matriz. "
                     "Use '➕ Inserção Manual' com tipo 'PIX FILIAL→MATRIZ'.",
                text_color="#ffffff")
            return

        # ── PALETA BOAH ──
        PRETO     = colors.HexColor("#141414")
        CREME     = colors.HexColor("#ffffff")
        VINHO     = colors.HexColor("#a1a1aa")
        VINHO_CLR = colors.HexColor("#a1a1aa")
        BEGE      = colors.HexColor("#D4C5A9")
        CINZA_CLR = colors.HexColor("#ffffff")
        CINZA_HDR = colors.HexColor("#141414")
        AZUL_FILIAL = colors.HexColor("#0c4a6e")
        AZUL_CLR  = colors.HexColor("#ffffff")
        BRANCO    = colors.white

        PAGE = landscape(A4)
        os.makedirs(config.PASTA_ATUAL, exist_ok=True)
        data_hoje = datetime.now().strftime("%d_%m_%Y_%H%M")
        caminho_pdf = os.path.join(config.PASTA_ATUAL,
                                   f"TRANSFERENCIAS_FILIAIS_{data_hoje}.pdf")

        doc = SimpleDocTemplate(
            caminho_pdf,
            pagesize=PAGE,
            leftMargin=1.8*cm, rightMargin=1.8*cm,
            topMargin=1.4*cm,  bottomMargin=1.4*cm,
            title="BOAH — Transferências Filiais → Matriz"
        )

        de_str  = self._aut_de.get().strip()
        ate_str = self._aut_ate.get().strip()

        def P(txt, fs=8, bold=False, cor=None, align=TA_LEFT):
            fn  = "Helvetica-Bold" if bold else "Helvetica"
            clr = cor or PRETO
            return Paragraph(str(txt),
                ParagraphStyle(f"p{abs(hash(str(txt)+str(fs)+str(bold))%999999)}",
                    fontSize=fs, fontName=fn, textColor=clr,
                    alignment=align, leading=fs+2))

        def _cabecalho():
            cab = [[
                Table([[
                    [P("BOAH", fs=26, bold=True)],
                    [P("LALUA COMERCIO DE MODAS LTDA  ·  SOLAR SERVIÇOS DE APOIO ADMIN",
                       fs=7.5, cor=colors.HexColor("#555"))],
                ]], colWidths=[doc.width*0.5]),
                Table([[
                    [P("TRANSFERÊNCIAS FILIAIS → MATRIZ", fs=10, bold=True,
                       cor=AZUL_FILIAL, align=TA_RIGHT)],
                    [P(f"Período: {de_str}  a  {ate_str}", fs=8,
                       cor=colors.HexColor("#555"), align=TA_RIGHT)],
                    [P(f"Emitido em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
                       fs=7, cor=colors.HexColor("#888"), align=TA_RIGHT)],
                ]], colWidths=[doc.width*0.5]),
            ]]
            t = Table(cab, colWidths=[doc.width*0.5, doc.width*0.5])
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), CREME),
                ("TOPPADDING",    (0,0), (-1,-1), 10),
                ("BOTTOMPADDING", (0,0), (-1,-1), 10),
                ("LEFTPADDING",   (0,0), (0,-1),  14),
                ("RIGHTPADDING",  (1,0), (1,-1),  14),
                ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ]))
            return [t, HRFlowable(width="100%", thickness=2,
                                   color=AZUL_CLR, spaceAfter=8)]

        # Agrupa por filial (nome do beneficiário contém a filial)
        # Tenta extrair nome da filial do nome do pagamento
        FILIAIS_CONHECIDAS = [
            "BARRA", "HORTO", "VILAS", "PASEO", "SDB",
            "PARALELA", "MATRIZ", "ONLINE", "ECOMMERCE"
        ]

        from collections import defaultdict
        por_filial = defaultdict(list)
        for p in transferencias:
            nome_up = p.get("nome","").upper()
            filial = "FILIAL NÃO IDENTIFICADA"
            for f in FILIAIS_CONHECIDAS:
                if f in nome_up:
                    filial = f
                    break
            # Fallback — usa o próprio nome
            if filial == "FILIAL NÃO IDENTIFICADA":
                filial = p.get("nome","FILIAL").upper()
            por_filial[filial].append(p)

        story = []
        story.extend(_cabecalho())

        total_geral = 0.0
        cw = [doc.width*p for p in [0.22, 0.10, 0.08, 0.12, 0.12, 0.18, 0.18]]
        HDRS = ["Favorecido / Identificação", "Data", "Valor (R$)",
                "Responsável", "Empresa", "Categoria", "Observação"]

        for filial_nome in sorted(por_filial.keys()):
            itens = por_filial[filial_nome]
            subtotal = sum(i["valor"] for i in itens)
            total_geral += subtotal

            # Cabeçalho da filial
            cab_filial = [[
                P(f"  🏢  FILIAL: {filial_nome}", fs=9, bold=True,
                  cor=BRANCO, align=TA_LEFT),
                P(f"{len(itens)} transferência(s)  ·  R$ {subtotal:,.2f}",
                  fs=8.5, bold=True, cor=CREME, align=TA_RIGHT),
            ]]
            tbl_cf = Table(cab_filial,
                           colWidths=[doc.width*0.6, doc.width*0.4])
            tbl_cf.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), AZUL_FILIAL),
                ("TOPPADDING",    (0,0), (-1,-1), 7),
                ("BOTTOMPADDING", (0,0), (-1,-1), 7),
                ("LEFTPADDING",   (0,0), (0,-1),  10),
                ("RIGHTPADDING",  (1,0), (1,-1),  10),
                ("LINEBELOW",     (0,0), (-1,-1), 2.5, AZUL_CLR),
                ("LINEBEFORE",    (0,0), (0,-1),  4, AZUL_CLR),
            ]))
            story.append(tbl_cf)

            # Linhas de dados
            hdr_r = [P(h, fs=6.5, bold=True, cor=BRANCO) for h in HDRS]
            rows  = [hdr_r]
            for item in sorted(itens, key=lambda x: x.get("data","")):
                rows.append([
                    P(item["nome"][:40], fs=7.5),
                    P(item.get("data",""), fs=7, align=TA_CENTER),
                    P(f"R$ {item['valor']:,.2f}", fs=7.5, bold=True,
                      cor=AZUL_FILIAL, align=TA_RIGHT),
                    P(item.get("responsavel",""), fs=7, align=TA_CENTER),
                    P(item.get("empresa",""), fs=7, align=TA_CENTER),
                    P(item.get("categoria",""), fs=7),
                    P(item.get("observacao",""), fs=7),
                ])

            # Subtotal da filial
            nr = len(rows)
            rows.append([
                P(f"SUBTOTAL  {filial_nome}", fs=8, bold=True),
                "", "",
                P(f"R$ {subtotal:,.2f}", fs=9, bold=True,
                  cor=AZUL_FILIAL, align=TA_RIGHT),
                "", "", "",
            ])

            tbl = Table(rows, colWidths=cw, repeatRows=1)
            nrr = len(rows)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),      (-1,0),      CINZA_HDR),
                ("TEXTCOLOR",     (0,0),      (-1,0),      BRANCO),
                ("ROWBACKGROUNDS",(0,1),      (-1,nrr-2),  [BRANCO, CINZA_CLR]),
                ("ALIGN",         (1,1),      (1,nrr-2),   "CENTER"),
                ("ALIGN",         (2,1),      (2,nrr-2),   "RIGHT"),
                ("ALIGN",         (3,1),      (4,nrr-2),   "CENTER"),
                ("BACKGROUND",    (0,nrr-1),  (-1,nrr-1),  BEGE),
                ("FONTNAME",      (0,nrr-1),  (-1,nrr-1),  "Helvetica-Bold"),
                ("SPAN",          (0,nrr-1),  (2,nrr-1)),
                ("SPAN",          (3,nrr-1),  (6,nrr-1)),
                ("ALIGN",         (3,nrr-1),  (6,nrr-1),   "RIGHT"),
                ("LINEBEFORE",    (0,0),      (0,-1),       3, AZUL_CLR),
                ("LINEBELOW",     (0,0),      (-1,0),       0.5, BEGE),
                ("LINEBELOW",     (0,1),      (-1,nrr-2),   0.3, BEGE),
                ("TOPPADDING",    (0,0),      (-1,-1),      3),
                ("BOTTOMPADDING", (0,0),      (-1,-1),      3),
                ("LEFTPADDING",   (0,0),      (-1,-1),      4),
                ("RIGHTPADDING",  (0,0),      (-1,-1),      4),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 10))

        # ── TOTAL GERAL ──
        story.append(HRFlowable(width="100%", thickness=1.5,
                                 color=AZUL_CLR, spaceBefore=4, spaceAfter=4))
        tgd = [[
            P("TOTAL GERAL TRANSFERÊNCIAS", fs=11, bold=True, cor=BRANCO),
            P(f"R$ {total_geral:,.2f}", fs=12, bold=True,
              cor=CREME, align=TA_RIGHT),
        ]]
        tbl_tg = Table(tgd, colWidths=[doc.width*0.6, doc.width*0.4])
        tbl_tg.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), AZUL_FILIAL),
            ("ALIGN",         (1,0), (1,-1),  "RIGHT"),
            ("TOPPADDING",    (0,0), (-1,-1),  10),
            ("BOTTOMPADDING", (0,0), (-1,-1),  10),
            ("LEFTPADDING",   (0,0), (-1,-1),  12),
            ("RIGHTPADDING",  (1,0), (1,-1),   12),
        ]))
        story.append(tbl_tg)
        story.append(Spacer(1, 8))
        story.append(P(
            f"Documento interno · Uso exclusivo Contas a Pagar BOAH/SOLAR  ·  "
            f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            fs=6.5, cor=colors.HexColor("#141414"), align=TA_CENTER))

        doc.build(story)
        self._aut_lbl_resumo.configure(
            text=f"✅ PDF gerado: {os.path.basename(caminho_pdf)}", text_color="#ffffff")
        try:
            os.startfile(caminho_pdf)
        except: pass


    def _gerar_pdf_transferencia_filial(self):
        """PDF individual por filial — uma página por filial com
        tabela de conferência de fornecedores (20 linhas) e área de assinatura."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import cm, mm
            from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                            Paragraph, Spacer, HRFlowable, PageBreak)
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        except ImportError:
            self._aut_lbl_resumo.configure(
                text="❌ pip install reportlab", text_color="#a1a1aa")
            return

        # Coleta transferências
        transferencias = [p for p in self._aut_pagamentos
                          if "FILIAL" in p.get("tipo","").upper()
                          or "TRANSFERENCIA MATRIZ" in p.get("categoria","").upper()]

        if not transferencias:
            self._aut_lbl_resumo.configure(
                text="ℹ️ Nenhuma transferência filial→matriz registrada.",
                text_color="#ffffff")
            return

        # ── PALETA ──
        PRETO     = colors.HexColor("#141414")
        CREME     = colors.HexColor("#ffffff")
        VINHO     = colors.HexColor("#a1a1aa")
        VINHO_CLR = colors.HexColor("#a1a1aa")
        BEGE      = colors.HexColor("#D4C5A9")
        CINZA_CLR = colors.HexColor("#ffffff")
        CINZA_HDR = colors.HexColor("#141414")
        AZUL      = colors.HexColor("#0c4a6e")
        AZUL_CLR  = colors.HexColor("#ffffff")
        BRANCO    = colors.white

        PAGE = A4  # Retrato para caber na impressora de qualquer filial
        os.makedirs(config.PASTA_ATUAL, exist_ok=True)
        data_hoje = datetime.now().strftime("%d_%m_%Y_%H%M")
        caminho_pdf = os.path.join(config.PASTA_ATUAL,
                                   f"TRANSFERENCIA_FILIAL_{data_hoje}.pdf")

        doc = SimpleDocTemplate(
            caminho_pdf,
            pagesize=PAGE,
            leftMargin=1.8*cm, rightMargin=1.8*cm,
            topMargin=1.4*cm,  bottomMargin=1.4*cm,
            title="BOAH — Transferência Filial → Matriz"
        )

        de_str  = self._aut_de.get().strip()
        ate_str = self._aut_ate.get().strip()

        def P(txt, fs=8, bold=False, cor=None, align=TA_LEFT):
            fn  = "Helvetica-Bold" if bold else "Helvetica"
            clr = cor or PRETO
            return Paragraph(str(txt),
                ParagraphStyle(f"p{abs(hash(str(txt)+str(fs)+str(bold))%999999)}",
                    fontSize=fs, fontName=fn, textColor=clr,
                    alignment=align, leading=fs+2))

        # Agrupa por filial
        FILIAIS_CONHECIDAS = [
            "BARRA","HORTO","VILAS","PASEO","SDB","PARALELA",
            "MATRIZ","ONLINE","ECOMMERCE"
        ]
        from collections import defaultdict
        por_filial = defaultdict(list)
        for p in transferencias:
            nome_up = p.get("nome","").upper()
            filial  = "NÃO IDENTIFICADA"
            for f in FILIAIS_CONHECIDAS:
                if f in nome_up:
                    filial = f
                    break
            if filial == "NÃO IDENTIFICADA":
                filial = p.get("nome","FILIAL").upper()
            por_filial[filial].append(p)

        story  = []
        pagina = 0

        for filial_nome in sorted(por_filial.keys()):
            itens    = por_filial[filial_nome]
            subtotal = sum(i["valor"] for i in itens)

            if pagina > 0:
                story.append(PageBreak())
            pagina += 1

            # ── CABEÇALHO ──
            cab = [[
                Table([[
                    [P("BOAH", fs=22, bold=True)],
                    [P("LALUA COMERCIO DE MODAS LTDA  ·  SOLAR SERVIÇOS DE APOIO ADMIN",
                       fs=7)],
                ]], colWidths=[doc.width*0.5]),
                Table([[
                    [P("COMPROVANTE DE TRANSFERÊNCIA", fs=9, bold=True,
                       cor=AZUL, align=TA_RIGHT)],
                    [P(f"Filial Remetente: {filial_nome}", fs=10, bold=True,
                       cor=VINHO, align=TA_RIGHT)],
                    [P(f"Período: {de_str}  a  {ate_str} | "
                       f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
                       fs=7, cor=colors.HexColor("#888"), align=TA_RIGHT)],
                ]], colWidths=[doc.width*0.5]),
            ]]
            t_cab = Table(cab, colWidths=[doc.width*0.5, doc.width*0.5])
            t_cab.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), CREME),
                ("TOPPADDING",    (0,0), (-1,-1), 10),
                ("BOTTOMPADDING", (0,0), (-1,-1), 10),
                ("LEFTPADDING",   (0,0), (0,-1),  14),
                ("RIGHTPADDING",  (1,0), (1,-1),  14),
                ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ]))
            story.append(t_cab)
            story.append(HRFlowable(width="100%", thickness=3,
                                     color=VINHO_CLR, spaceAfter=8))

            # ── IDENTIFICAÇÃO DA FILIAL ──
            id_filial = [[
                P(f"FILIAL REMETENTE:", fs=8, bold=True, cor=AZUL),
                P(filial_nome, fs=14, bold=True, cor=VINHO),
                P("DATA DO ENVIO:", fs=8, bold=True, cor=AZUL, align=TA_RIGHT),
                P(itens[0].get("data","__/__/____"), fs=11, bold=True,
                  cor=PRETO, align=TA_RIGHT),
            ]]
            t_id = Table(id_filial,
                         colWidths=[doc.width*0.2, doc.width*0.4,
                                     doc.width*0.2, doc.width*0.2])
            t_id.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), BEGE),
                ("TOPPADDING",    (0,0), (-1,-1), 10),
                ("BOTTOMPADDING", (0,0), (-1,-1), 10),
                ("LEFTPADDING",   (0,0), (-1,-1), 10),
                ("RIGHTPADDING",  (0,0), (-1,-1), 10),
                ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                ("BOX",           (0,0), (-1,-1), 1.5, VINHO),
            ]))
            story.append(t_id)
            story.append(Spacer(1, 8))

            # ── TABELA DE TRANSFERÊNCIAS ──
            story.append(P("DETALHAMENTO DAS TRANSFERÊNCIAS", fs=8,
                           bold=True, cor=AZUL))
            story.append(Spacer(1, 4))

            cw_t = [doc.width*p for p in [0.34, 0.12, 0.14, 0.18, 0.22]]
            HDRS_T = ["Favorecido / Descrição", "Data", "Valor (R$)",
                      "Responsável", "Categoria"]
            hdr_r = [P(h, fs=7, bold=True, cor=BRANCO) for h in HDRS_T]
            rows  = [hdr_r]
            for item in sorted(itens, key=lambda x: x.get("data","")):
                rows.append([
                    P(item["nome"][:50], fs=8),
                    P(item.get("data",""), fs=8, align=TA_CENTER),
                    P(f"R$ {item['valor']:,.2f}", fs=8, bold=True,
                      cor=AZUL, align=TA_RIGHT),
                    P(item.get("responsavel",""), fs=7.5, align=TA_CENTER),
                    P(item.get("categoria",""), fs=7.5),
                ])

            # Linha total
            nr  = len(rows)
            rows.append([
                P("TOTAL TRANSFERIDO", fs=9, bold=True),
                "",
                P(f"R$ {subtotal:,.2f}", fs=10, bold=True,
                  cor=VINHO, align=TA_RIGHT),
                "", "",
            ])
            nrr = len(rows)

            tbl_t = Table(rows, colWidths=cw_t, repeatRows=1)
            tbl_t.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),     (-1,0),     CINZA_HDR),
                ("ROWBACKGROUNDS",(0,1),     (-1,nr-1),  [BRANCO, CINZA_CLR]),
                ("ALIGN",         (1,1),     (1,nr-1),   "CENTER"),
                ("ALIGN",         (2,1),     (2,nr-1),   "RIGHT"),
                ("ALIGN",         (3,1),     (3,nr-1),   "CENTER"),
                ("BACKGROUND",    (0,nrr-1), (-1,nrr-1), CREME),
                ("FONTNAME",      (0,nrr-1), (-1,nrr-1), "Helvetica-Bold"),
                ("SPAN",          (0,nrr-1), (1,nrr-1)),
                ("SPAN",          (2,nrr-1), (4,nrr-1)),
                ("ALIGN",         (2,nrr-1), (4,nrr-1),  "RIGHT"),
                ("BOX",           (0,0),     (-1,-1),     1, BEGE),
                ("LINEBELOW",     (0,0),     (-1,0),      0.5, BEGE),
                ("LINEBELOW",     (0,1),     (-1,nr-1),   0.3, BEGE),
                ("TOPPADDING",    (0,0),     (-1,-1),     4),
                ("BOTTOMPADDING", (0,0),     (-1,-1),     4),
                ("LEFTPADDING",   (0,0),     (-1,-1),     5),
                ("RIGHTPADDING",  (0,0),     (-1,-1),     5),
                ("RIGHTPADDING",  (2,nrr-1), (4,nrr-1),  8),
            ]))
            story.append(tbl_t)
            story.append(Spacer(1, 12))

            # ── CONFERÊNCIA DE FORNECEDORES (20 linhas) ──
            story.append(P("CONFERÊNCIA DE FORNECEDORES / PAGAMENTOS DA FILIAL",
                           fs=8, bold=True, cor=AZUL))
            story.append(Spacer(1, 4))

            cw_c = [doc.width*p for p in [0.05, 0.35, 0.14, 0.13, 0.13, 0.20]]
            HDRS_C = ["Nº", "Fornecedor / Beneficiário", "CNPJ/CPF",
                      "Vencimento", "Valor (R$)", "Categoria"]
            hdr_c = [P(h, fs=7, bold=True, cor=BRANCO) for h in HDRS_C]
            rows_c = [hdr_c]

            # 20 linhas em branco para preenchimento manual
            for i in range(1, 21):
                bg_linha = BRANCO if i % 2 == 0 else CINZA_CLR
                rows_c.append([
                    P(str(i), fs=7.5, cor=colors.HexColor("#999"),
                      align=TA_CENTER),
                    P("", fs=8), P("", fs=8), P("", fs=8),
                    P("", fs=8), P("", fs=8),
                ])

            # Linha total conferência
            rows_c.append([
                P("TOTAL", fs=8, bold=True), "", "",
                P("", fs=8),
                P("R$", fs=8, bold=True, align=TA_RIGHT),
                "",
            ])

            tbl_c = Table(rows_c, colWidths=cw_c, repeatRows=1)
            nr_c  = len(rows_c)
            tbl_c.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),      (-1,0),       CINZA_HDR),
                ("TEXTCOLOR",     (0,0),      (-1,0),       BRANCO),
                ("ROWBACKGROUNDS",(0,1),      (-1,nr_c-2),
                                  [BRANCO, CINZA_CLR]),
                ("ALIGN",         (0,0),      (0,-1),       "CENTER"),
                ("ALIGN",         (3,1),      (4,nr_c-2),   "CENTER"),
                ("BACKGROUND",    (0,nr_c-1), (-1,nr_c-1),  BEGE),
                ("FONTNAME",      (0,nr_c-1), (-1,nr_c-1),  "Helvetica-Bold"),
                ("SPAN",          (0,nr_c-1), (3,nr_c-1)),
                ("BOX",           (0,0),      (-1,-1),       1, BEGE),
                ("LINEBELOW",     (0,0),      (-1,-1),       0.3, BEGE),
                ("TOPPADDING",    (0,0),      (-1,-1),       5),
                ("BOTTOMPADDING", (0,0),      (-1,-1),       5),
                ("LEFTPADDING",   (0,0),      (-1,-1),       5),
                ("RIGHTPADDING",  (0,0),      (-1,-1),       5),
            ]))
            story.append(tbl_c)
            story.append(Spacer(1, 14))

            # ── ÁREA DE ASSINATURAS ──
            linha_ass = "_" * 35
            ass = [[
                Table([[
                    [P(linha_ass, fs=8, cor=colors.HexColor("#999"))],
                    [P(f"Responsável — {filial_nome}", fs=7.5, bold=True,
                       cor=AZUL, align=TA_CENTER)],
                    [P("Data: ____/____/________", fs=7.5,
                       cor=colors.HexColor("#666"), align=TA_CENTER)],
                ]], colWidths=[doc.width*0.32]),
                Table([[
                    [P(linha_ass, fs=8, cor=colors.HexColor("#999"))],
                    [P("Conferido por — Contas a Pagar BOAH", fs=7.5,
                       bold=True, cor=AZUL, align=TA_CENTER)],
                    [P("Data: ____/____/________", fs=7.5,
                       cor=colors.HexColor("#666"), align=TA_CENTER)],
                ]], colWidths=[doc.width*0.32]),
                Table([[
                    [P(linha_ass, fs=8, cor=colors.HexColor("#999"))],
                    [P("Aprovado por — Financeiro BOAH", fs=7.5,
                       bold=True, cor=VINHO, align=TA_CENTER)],
                    [P("Data: ____/____/________", fs=7.5,
                       cor=colors.HexColor("#666"), align=TA_CENTER)],
                ]], colWidths=[doc.width*0.32]),
            ]]
            t_ass = Table(ass, colWidths=[doc.width*0.34]*3)
            t_ass.setStyle(TableStyle([
                ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                ("VALIGN",        (0,0), (-1,-1), "BOTTOM"),
                ("TOPPADDING",    (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]))
            story.append(t_ass)
            story.append(Spacer(1, 6))
            story.append(HRFlowable(width="100%", thickness=0.5, color=BEGE))
            story.append(P(
                f"Documento interno · BOAH/SOLAR  ·  "
                f"Filial: {filial_nome}  ·  "
                f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                fs=6.5, cor=colors.HexColor("#999"), align=TA_CENTER))

        doc.build(story)
        n = len(por_filial)
        self._aut_lbl_resumo.configure(
            text=f"✅ PDF gerado — {n} filial(is) | "
                 f"R$ {sum(i['valor'] for i in transferencias):,.2f}",
            text_color="#ffffff")
        try:
            os.startfile(caminho_pdf)
        except: pass


    def _aut_gerar_pdf(self):
        """Gera o PDF de autorização de pagamentos no estilo BOAH."""
        if not self._aut_pagamentos:
            self._aut_lbl_status.configure(text="⚠️ Carregue os pagamentos primeiro.", text_color="#ffffff")
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                            Paragraph, Spacer, HRFlowable)
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        except ImportError:
            self._aut_lbl_status.configure(
                text="❌ reportlab não instalado. Execute: pip install reportlab", text_color="#a1a1aa")
            return

        de_str  = self._aut_de.get().strip()
        ate_str = self._aut_ate.get().strip()

        # Agrupa por empresa → data → tipo de pagamento
        from collections import defaultdict
        # estrutura: empresas[emp][data_str][tipo] = [itens]
        empresas = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for p in self._aut_pagamentos:
            emp  = p.get("empresa", "LALUA")
            data = p.get("data", "")
            tipo = p.get("tipo", "Outros")
            empresas[emp][data][tipo].append(p)

        ORDEM_TIPO = [
            "Boleto Itaú",
            "Boleto outros bancos",
            "Boletos ouros bancos",       # variação de digitação do Itaú
            "Concessionária",
            "Tributos com código de barras",
            "DARF código de barras",      # Receita Federal
            "DAS código barras",          # Simples Nacional
            "IPTU/ISS e outros tributos",
            "PIX Transferências",
            "Pix Transferencia",          # variação
            "PIX Qr Code",
            "TED",
            "Folha de pagamento",
            "Folha de pagamentos",
            "Outros",
        ]

        os.makedirs(config.PASTA_ATUAL, exist_ok=True)
        data_hoje = datetime.now().strftime("%d_%m_%Y")
        nome_arq  = f"AUTORIZACAO_PAGAMENTOS_{data_hoje}.pdf"
        caminho_pdf = os.path.join(config.PASTA_ATUAL, nome_arq)

        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import cm, mm
            from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                            Paragraph, Spacer, HRFlowable,
                                            KeepTogether, PageBreak)
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        except ImportError:
            self._aut_lbl_status.configure(
                text="❌ reportlab não instalado. Execute: pip install reportlab", text_color="#a1a1aa")
            return

        de_str  = self._aut_de.get().strip()
        ate_str = self._aut_ate.get().strip()

        from collections import defaultdict
        empresas = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for p in self._aut_pagamentos:
            emp  = p.get("empresa", "LALUA")
            data = p.get("data", "")
            tipo = p.get("tipo", "Outros")
            empresas[emp][data][tipo].append(p)

        ORDEM_TIPO = [
            "Boleto Itaú", "Boleto outros bancos", "Boletos ouros bancos",
            "Concessionária", "Tributos com código de barras",
            "DARF código de barras", "DAS código barras",
            "IPTU/ISS e outros tributos",
            "PIX Transferências", "Pix Transferencia",
            "PIX Qr Code", "TED",
            "Folha de pagamento", "Folha de pagamentos", "Outros",
        ]

        os.makedirs(config.PASTA_ATUAL, exist_ok=True)
        data_hoje = datetime.now().strftime("%d_%m_%Y")
        nome_arq  = f"AUTORIZACAO_PAGAMENTOS_{data_hoje}.pdf"
        caminho_pdf = os.path.join(config.PASTA_ATUAL, nome_arq)

        try:
            # ── PAISAGEM A4 ──
            PAGE = landscape(A4)
            doc = SimpleDocTemplate(
                caminho_pdf,
                pagesize=PAGE,
                leftMargin=1.8*cm, rightMargin=1.8*cm,
                topMargin=1.4*cm,  bottomMargin=1.4*cm,
                title=f"BOAH — Autorização de Pagamentos {de_str}"
            )

            # ══ PALETA BOAH ══
            PRETO     = colors.HexColor("#141414")
            CREME     = colors.HexColor("#ffffff")
            VINHO     = colors.HexColor("#a1a1aa")
            VINHO_CLR = colors.HexColor("#a1a1aa")
            BEGE      = colors.HexColor("#D4C5A9")
            CINZA_CLR = colors.HexColor("#ffffff")
            CINZA_HDR = colors.HexColor("#141414")
            BRANCO    = colors.white

            # ── ESTILOS ──
            st_logo = ParagraphStyle("logo", fontSize=28, fontName="Times-Bold",
                                      textColor=PRETO, alignment=TA_LEFT, leading=30)
            st_emp  = ParagraphStyle("emp",  fontSize=8,  fontName="Helvetica",
                                      textColor=colors.HexColor("#141414"), alignment=TA_LEFT)
            st_td   = ParagraphStyle("td",   fontSize=7.5,fontName="Helvetica",
                                      textColor=PRETO, alignment=TA_LEFT)
            st_td_sm= ParagraphStyle("tdsm", fontSize=7,  fontName="Helvetica",
                                      textColor=PRETO, alignment=TA_LEFT)
            st_th   = ParagraphStyle("th",   fontSize=6.5,fontName="Helvetica-Bold",
                                      textColor=BRANCO, alignment=TA_CENTER)

            def P(txt, st=None, fs=7.5, bold=False, cor=None, align=TA_LEFT):
                if st: return Paragraph(str(txt), st)
                fn  = "Helvetica-Bold" if bold else "Helvetica"
                clr = cor or PRETO
                return Paragraph(str(txt),
                                  ParagraphStyle(f"x{abs(hash(str(txt)+str(fs)+str(bold)))%999999}",
                                                  fontSize=fs, fontName=fn,
                                                  textColor=clr, alignment=align))

            # 7 colunas — Tipo fica no cabeçalho do bloco, não na tabela
            col_props = [0.20, 0.12, 0.07, 0.09, 0.15, 0.17, 0.20]
            HDRS = ["Favorecido / Beneficiário", "CPF/CNPJ",
                    "Data", "Valor (R$)", "Responsável", "Categoria", "Descrição"]

            def _cabecalho_boah():
                cab = [[
                    Table([[
                        [P("BOAH", st=st_logo)],
                        [P("LALUA COMERCIO DE MODAS LTDA  ·  SOLAR SERVIÇOS DE APOIO ADMIN",
                           st=st_emp)],
                    ]], colWidths=[doc.width * 0.5]),
                    Table([[
                        [P("AUTORIZAÇÃO DE PAGAMENTOS", bold=True, fs=10,
                           cor=PRETO, align=TA_RIGHT)],
                        [P(f"Período: {de_str}  a  {ate_str}", fs=8,
                           cor=colors.HexColor("#141414"), align=TA_RIGHT)],
                        [P(f"Emitido em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
                           fs=7, cor=colors.HexColor("#141414"), align=TA_RIGHT)],
                    ]], colWidths=[doc.width * 0.5]),
                ]]
                t = Table(cab, colWidths=[doc.width*0.5, doc.width*0.5])
                t.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (-1,-1), CREME),
                    ("TOPPADDING",    (0,0), (-1,-1), 10),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 10),
                    ("LEFTPADDING",   (0,0), (0,-1),  14),
                    ("RIGHTPADDING",  (1,0), (1,-1),  14),
                    ("VALIGN",        (0,0), (-1,-1),  "MIDDLE"),
                ]))
                return [t, HRFlowable(width="100%", thickness=2,
                                       color=VINHO_CLR, spaceAfter=6)]

            def _linha_total(label, valor, bg, txt_cor=BRANCO, fs=8):
                cw = [doc.width*x for x in col_props]
                d  = [[P(label, bold=True, cor=txt_cor, fs=fs),
                        "", "",
                        P(f"R$ {valor:,.2f}", bold=True, cor=txt_cor,
                          fs=fs+0.5, align=TA_RIGHT),
                        "", "", ""]]
                t = Table(d, colWidths=cw)
                t.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (-1,-1), bg),
                    ("SPAN",          (0,0), (2,0)),
                    ("SPAN",          (3,0), (6,0)),
                    ("ALIGN",         (3,0), (6,0), "RIGHT"),
                    ("TOPPADDING",    (0,0), (-1,-1), 5),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                    ("LEFTPADDING",   (0,0), (-1,-1), 8),
                    ("RIGHTPADDING",  (3,0), (6,0),   8),
                ]))
                return t

            story = []
            total_geral    = 0.0
            primeira_emp   = True
            empresas_lista = [e for e in ["LALUA", "SOLAR"] if e in empresas]

            for emp_nome in empresas_lista:
                nome_emp_full = ("LALUA COMERCIO DE MODAS LTDA" if emp_nome == "LALUA"
                                 else "SOLAR SERVIÇOS DE APOIO ADMIN")

                # Quebra de página entre empresas — cada uma começa numa página nova
                if not primeira_emp:
                    story.append(PageBreak())
                primeira_emp = False

                # Cabeçalho BOAH no topo de cada página de empresa
                story.extend(_cabecalho_boah())

                total_empresa = 0.0

                datas_ord = sorted(
                    empresas[emp_nome].keys(),
                    key=lambda d: (datetime.strptime(d, "%d/%m/%Y")
                                   if re.match(r'\d{2}/\d{2}/\d{4}', d)
                                   else datetime.max)
                )

                for data_dia in datas_ord:
                    tipos_dia = empresas[emp_nome][data_dia]
                    total_dia = 0.0

                    for tipo in ORDEM_TIPO:
                        if tipo not in tipos_dia:
                            continue
                        itens    = tipos_dia[tipo]
                        subtotal = sum(i["valor"] for i in itens)
                        total_dia     += subtotal
                        total_empresa += subtotal
                        total_geral   += subtotal

                        # Cabeçalho do bloco: empresa (esq) + data · tipo (dir) — LINHA ÚNICA
                        cab_bloco = [[
                            P(f"  {nome_emp_full}", bold=True, fs=8.5,
                              cor=BRANCO, align=TA_LEFT),
                            P(f"{data_dia}  ·  {tipo}", bold=True, fs=8.5,
                              cor=CREME, align=TA_RIGHT),
                        ]]
                        tbl_cb = Table(cab_bloco,
                                       colWidths=[doc.width*0.55, doc.width*0.45])
                        tbl_cb.setStyle(TableStyle([
                            ("BACKGROUND",    (0,0), (-1,-1), CINZA_HDR),
                            ("TOPPADDING",    (0,0), (-1,-1), 5),
                            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                            ("LEFTPADDING",   (0,0), (0,-1),  8),
                            ("RIGHTPADDING",  (1,0), (1,-1),  8),
                            ("LINEBELOW",     (0,0), (-1,-1), 2, VINHO_CLR),
                            ("LINEBEFORE",    (0,0), (0,-1),  3, VINHO_CLR),
                        ]))
                        story.append(tbl_cb)

                        # Cabeçalho das colunas
                        hdr_r = [P(h, st=st_th) for h in HDRS]
                        rows  = [hdr_r]

                        for item in sorted(itens, key=lambda x: x["nome"]):
                            rows.append([
                                P(item["nome"][:55], st=st_td),
                                P(item["cnpj"],              fs=7),
                                P(item["data"],              fs=7,   align=TA_CENTER),
                                P(f"R$ {item['valor']:,.2f}",fs=7.5, bold=True, align=TA_RIGHT),
                                P(item.get("responsavel",""),fs=7,   align=TA_CENTER),
                                P(item.get("categoria",""),  st=st_td_sm),
                                P(item.get("descricao","")[:40], st=st_td_sm),
                            ])

                        # Linha subtotal
                        nr = len(rows)
                        rows.append([
                            P(tipo, bold=True, cor=PRETO, fs=7.5),
                            "", "",
                            P(f"R$ {subtotal:,.2f}", bold=True,
                              cor=VINHO, fs=8.5, align=TA_RIGHT),
                            "", "", "",
                        ])

                        cw  = [doc.width*x for x in col_props]
                        tbl = Table(rows, colWidths=cw, repeatRows=1)
                        nrr = len(rows)
                        tbl.setStyle(TableStyle([
                            # Cabeçalho colunas
                            ("BACKGROUND",    (0,0), (-1,0), CINZA_HDR),
                            ("TEXTCOLOR",     (0,0), (-1,0), BRANCO),
                            ("ALIGN",         (0,0), (-1,0), "CENTER"),
                            ("FONTSIZE",      (0,0), (-1,0), 6.5),
                            # Dados — linhas alternadas
                            ("FONTSIZE",      (0,1), (-1,nrr-2), 7.5),
                            ("ROWBACKGROUNDS",(0,1), (-1,nrr-2), [BRANCO, CINZA_CLR]),
                            # Alinhamentos
                            ("ALIGN",         (2,1), (2,nrr-2), "CENTER"),  # Data
                            ("ALIGN",         (3,1), (3,nrr-2), "RIGHT"),   # Valor
                            ("ALIGN",         (4,1), (4,nrr-2), "CENTER"),  # Responsável
                            # Subtotal
                            ("BACKGROUND",    (0,nrr-1), (-1,nrr-1), CREME),
                            ("FONTNAME",      (0,nrr-1), (-1,nrr-1), "Helvetica-Bold"),
                            ("FONTSIZE",      (0,nrr-1), (-1,nrr-1), 7.5),
                            ("SPAN",          (0,nrr-1), (2,nrr-1)),
                            ("SPAN",          (3,nrr-1), (5,nrr-1)),
                            ("ALIGN",         (3,nrr-1), (5,nrr-1), "RIGHT"),
                            ("LINEBEFORE",    (0,0),     (0,-1),     3, VINHO_CLR),
                            # Grid elegante
                            ("LINEBELOW",     (0,0), (-1,0),      0.5, BEGE),
                            ("LINEBELOW",     (0,1), (-1,nrr-2),  0.3, BEGE),
                            # Padding
                            ("TOPPADDING",    (0,0), (-1,-1), 3),
                            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                            ("LEFTPADDING",   (0,0), (-1,-1), 4),
                            ("RIGHTPADDING",  (0,0), (-1,-1), 4),
                            ("RIGHTPADDING",  (3,nrr-1), (5,nrr-1), 6),
                        ]))
                        story.append(tbl)
                        story.append(Spacer(1, 3))

                    # Total do dia
                    story.append(_linha_total(
                        f"Total  {data_dia}", total_dia, BEGE, txt_cor=PRETO, fs=8))
                    story.append(Spacer(1, 6))

                # Total da empresa
                story.append(_linha_total(
                    f"Total  {nome_emp_full}", total_empresa, PRETO, txt_cor=BRANCO, fs=9))
                story.append(Spacer(1, 10))

            # ── TOTAL GERAL (última página) ─────────────────────────────────
            story.append(HRFlowable(width="100%", thickness=1.5,
                                     color=VINHO_CLR, spaceBefore=2, spaceAfter=2))
            cw  = [doc.width*x for x in col_props]
            tgd = [[
                P("TOTAL GERAL", bold=True, fs=11, cor=BRANCO),
                "", "",
                P(f"R$ {total_geral:,.2f}", bold=True, fs=12,
                  cor=CREME, align=TA_RIGHT),
                "", "",
            ]]
            tbl_tg = Table(tgd, colWidths=cw)
            tbl_tg.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), VINHO),
                ("SPAN",          (0,0), (2,0)),
                ("SPAN",          (3,0), (5,0)),
                ("ALIGN",         (3,0), (5,0), "RIGHT"),
                ("TOPPADDING",    (0,0), (-1,-1), 10),
                ("BOTTOMPADDING", (0,0), (-1,-1), 10),
                ("LEFTPADDING",   (0,0), (-1,-1), 10),
                ("RIGHTPADDING",  (3,0), (5,0),   10),
            ]))
            story.append(tbl_tg)
            story.append(Spacer(1, 8))
            story.append(HRFlowable(width="100%", thickness=0.5, color=BEGE))
            story.append(P(
                "Documento interno · Uso exclusivo Contas a Pagar BOAH/SOLAR  ·  "
                f"Gerado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M')}  ·  "
                "Robô Financeiro BOAH v17 — Roberto Cerqueira",
                fs=6, cor=colors.HexColor("#141414"), align=TA_CENTER
            ))

            doc.build(story)

            salvos = salvar_pagamentos_autorizados(self._aut_pagamentos)
            self._aut_lbl_status.configure(
                text=f"✅ PDF gerado e {salvos} pagamentos salvos!", text_color="#ffffff")
            os.startfile(caminho_pdf)

        except Exception as e:
            self._aut_lbl_status.configure(text=f"❌ Erro ao gerar PDF: {e}", text_color="#a1a1aa")


    def _gerar_pdf_transferencias_filiais(self):
        """Gera PDF de Transferências Filiais → Matriz no padrão BOAH."""
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import cm, mm
            from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                            Paragraph, Spacer, HRFlowable,
                                            KeepTogether, PageBreak)
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        except ImportError:
            from tkinter import messagebox
            messagebox.showerror("Erro",
                "reportlab não instalado.\nExecute: pip install reportlab")
            return

        # ── PALETA BOAH (mesma da Autorização) ──
        PRETO     = colors.HexColor("#141414")
        CREME     = colors.HexColor("#ffffff")
        VINHO     = colors.HexColor("#a1a1aa")
        VINHO_CLR = colors.HexColor("#a1a1aa")
        BEGE      = colors.HexColor("#D4C5A9")
        CINZA_CLR = colors.HexColor("#ffffff")
        CINZA_HDR = colors.HexColor("#141414")
        BRANCO    = colors.white
        VERDE     = colors.HexColor("#ffffff")
        AZUL_PIX  = colors.HexColor("#141414")

        def P(txt, fs=8, bold=False, cor=None, align=TA_LEFT):
            fn  = "Helvetica-Bold" if bold else "Helvetica"
            clr = cor or PRETO
            return Paragraph(str(txt),
                ParagraphStyle(f"p{abs(hash(str(txt)+str(fs)+str(bold)))%999999}",
                               fontSize=fs, fontName=fn,
                               textColor=clr, alignment=align,
                               leading=fs*1.3))

        # Coleta transferências da aba autorização (tipo PIX FILIAL→MATRIZ)
        # e também do campo manual marcado como transferência
        filiais_map = {
            "LALUA - Barra":   "BARRA",
            "LALUA - Horto":   "HORTO",
            "LALUA - Vilas":   "VILAS",
            "LALUA - Paseo":   "PASEO",
            "LALUA - SDB":     "SDB",
            "LALUA - Matriz":  "MATRIZ",
            "SOLAR - Geral":   "SOLAR",
        }

        # Pede dados via janela modal
        from tkinter import Toplevel, StringVar, BooleanVar
        win = Toplevel(self.root)
        win.title("Relatório de Transferências Filiais → Matriz")
        win.geometry("560x460")
        win.configure(bg="#0a0a0a")
        win.grab_set()

        bg_w    = "#000000"
        surf_w  = "#111111"
        acc_w   = "#ffffff"
        txt_w   = "#e5e5e5"
        muted_w = "#a1a1aa"

        tk.Label(win, text="💸  Relatório de Transferências Filiais → Matriz",
                 font=("Segoe UI",11,"bold"), text_color=acc_w, bg=bg_w
                 ).pack(anchor="w", padx=20, pady=(14,4))
        tk.Label(win,
                 text="Preencha os dados de cada filial que enviou PIX para a matriz.",
                 font=("Segoe UI",8), fg=muted_w, bg=bg_w
                 ).pack(anchor="w", padx=20, pady=(0,8))

        frm_campos = tk.Frame(win, bg=surf_w, padx=16, pady=12)
        frm_campos.pack(fill="x", padx=20)

        def lbl(t, r, c):
            tk.Label(frm_campos, text=t, fg=muted_w, bg=surf_w,
                     font=("Segoe UI",8)).grid(row=r, column=c, sticky="w", pady=3, padx=(0,6))

        def ent(r, c, w=14, val=""):
            e = tk.Entry(frm_campos, font=("Segoe UI",9),
                         bg="#0a0a0a", fg=txt_w,
                         insertbackground=acc_w, relief="flat", bd=2, width=w)
            e.grid(row=r, column=c, sticky="w", padx=(0,10))
            if val: e.insert(0, val)
            return e

        # Cabeçalho
        for i, h in enumerate(["Filial","Data","Valor Transferido","Referência/Obs"]):
            tk.Label(frm_campos, text=h, fg=acc_w, bg=surf_w,
                     font=("Segoe UI",7,"bold")).grid(row=0, column=i, sticky="w", padx=(0,10))

        FILIAIS_PADRAO = [
            "LALUA - Barra", "LALUA - Horto", "LALUA - Vilas",
            "LALUA - Paseo", "LALUA - SDB",
        ]

        linhas_filial = []
        data_hoje = datetime.now().strftime("%d/%m/%Y")

        for i, fil in enumerate(FILIAIS_PADRAO):
            fil_var  = tk.StringVar(value=fil)
            ttk.Combobox(frm_campos, textvariable=fil_var,
                         values=list(filiais_map.keys()),
                         state="normal", width=16, font=("Segoe UI",8)
                         ).grid(row=i+1, column=0, sticky="w", padx=(0,10), pady=2)
            dt_e   = ent(i+1, 1, 11, data_hoje)
            _aplicar_mascara_data(dt_e)
            val_e  = ent(i+1, 2, 13)
            _aplicar_mascara_valor(val_e)
            obs_e  = ent(i+1, 3, 20)
            linhas_filial.append((fil_var, dt_e, val_e, obs_e))

        # Campos gerais
        frm_geral = tk.Frame(win, bg=surf_w, padx=16, pady=8)
        frm_geral.pack(fill="x", padx=20, pady=(6,0))

        tk.Label(frm_geral, text="Período referência:", fg=muted_w, bg=surf_w,
                 font=("Segoe UI",8)).grid(row=0, column=0, sticky="w")
        de_var  = tk.StringVar(value=self._aut_de.get() if hasattr(self,"_aut_de") else data_hoje)
        ate_var = tk.StringVar(value=self._aut_ate.get() if hasattr(self,"_aut_ate") else data_hoje)
        tk.Entry(frm_geral, textvariable=de_var, font=("Segoe UI",9),
                 bg="#0a0a0a", fg=txt_w, insertbackground=acc_w,
                 relief="flat", bd=2, width=11).grid(row=0, column=1, padx=(4,8))
        tk.Label(frm_geral, text="até", fg=muted_w, bg=surf_w,
                 font=("Segoe UI",8)).grid(row=0, column=2)
        tk.Entry(frm_geral, textvariable=ate_var, font=("Segoe UI",9),
                 bg="#0a0a0a", fg=txt_w, insertbackground=acc_w,
                 relief="flat", bd=2, width=11).grid(row=0, column=3, padx=(4,0))

        lbl_status = tk.Label(win, text="", font=("Segoe UI",9),
                               fg="#ffffff", bg=bg_w)
        lbl_status.pack(anchor="w", padx=20, pady=4)

        def _gerar():
            try:
                # Coleta dados das linhas da modal
                transferencias = []
                for (fil_var, dt_e, val_e, obs_e) in linhas_filial:
                    filial = fil_var.get().strip()
                    dt     = dt_e.get().strip()
                    val_s  = val_e.get().strip()
                    obs    = obs_e.get().strip()
                    if not filial or not val_s:
                        continue
                    try:
                        valor = _parse_valor(val_s)
                        if valor <= 0: continue
                    except: continue
                    transferencias.append({
                        "filial": filial,
                        "data":   dt,
                        "valor":  valor,
                        "obs":    obs,
                    })

                if not transferencias:
                    lbl_status.config(text="⚠️ Informe ao menos uma transferência.",
                                      fg="#ffffff")
                    return

                de_str  = de_var.get().strip()
                ate_str = ate_var.get().strip()
                total   = sum(t["valor"] for t in transferencias)

                # ── GERA O PDF ──
                data_hoje_str = datetime.now().strftime("%d_%m_%Y")
                nome_arq = f"TRANSFERENCIAS_FILIAIS_{data_hoje_str}.pdf"
                caminho  = os.path.join(config.PASTA_ATUAL, nome_arq)

                PAGE = landscape(A4)
                doc  = SimpleDocTemplate(
                    caminho, pagesize=PAGE,
                    leftMargin=1.8*cm, rightMargin=1.8*cm,
                    topMargin=1.4*cm,  bottomMargin=1.4*cm,
                    title=f"BOAH — Transferências Filiais → Matriz {de_str}"
                )

                story = []

                # ── CABEÇALHO ──
                cab = [[
                    Table([[
                        [P("BOAH", fs=28, bold=True, cor=PRETO)],
                        [P("LALUA COMERCIO DE MODAS LTDA  ·  SOLAR SERVIÇOS DE APOIO ADMIN",
                           fs=8, cor=colors.HexColor("#141414"))],
                    ]], colWidths=[doc.width*0.5]),
                    Table([[
                        [P("TRANSFERÊNCIAS FILIAIS → MATRIZ", bold=True, fs=10,
                           cor=PRETO, align=TA_RIGHT)],
                        [P(f"Período: {de_str}  a  {ate_str}", fs=8,
                           cor=colors.HexColor("#141414"), align=TA_RIGHT)],
                        [P(f"Emitido em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
                           fs=7, cor=colors.HexColor("#141414"), align=TA_RIGHT)],
                    ]], colWidths=[doc.width*0.5]),
                ]]
                t_cab = Table(cab, colWidths=[doc.width*0.5, doc.width*0.5])
                t_cab.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (-1,-1), CREME),
                    ("TOPPADDING",    (0,0), (-1,-1), 10),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 10),
                    ("LEFTPADDING",   (0,0), (0,-1),  14),
                    ("RIGHTPADDING",  (1,0), (1,-1),  14),
                    ("VALIGN",        (0,0), (-1,-1),  "MIDDLE"),
                ]))
                story.append(t_cab)
                story.append(HRFlowable(width="100%", thickness=2,
                                         color=VINHO_CLR, spaceAfter=8))

                # ── BLOCO: RESUMO DAS TRANSFERÊNCIAS RECEBIDAS ──
                cb_bloco = [[
                    P("  DETALHAMENTO DAS TRANSFERÊNCIAS RECEBIDAS", bold=True,
                      fs=10, cor=BRANCO, align=TA_LEFT),
                    P("Filiais → Conta Matriz LALUA · Ag. 0334 · Cc. 98775-7",
                      fs=8.5, cor=CREME, align=TA_RIGHT),
                ]]
                t_cb = Table(cb_bloco, colWidths=[doc.width*0.55, doc.width*0.45])
                t_cb.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (-1,-1), CINZA_HDR),
                    ("TOPPADDING",    (0,0), (-1,-1), 8),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                    ("LEFTPADDING",   (0,0), (0,-1),  10),
                    ("RIGHTPADDING",  (1,0), (1,-1),  10),
                    ("LINEBELOW",     (0,0), (-1,-1), 2, VINHO_CLR),
                    ("LINEBEFORE",    (0,0), (0,-1),  4, VINHO_CLR),
                ]))
                story.append(t_cb)

                # Tabela de transferências (Expandida)
                cw_transf = [doc.width*0.28, doc.width*0.12,
                              doc.width*0.15, doc.width*0.25, doc.width*0.20]
                hdrs_t = ["Filial Remetente", "Data", "Valor (R$)",
                          "Referência / Observação", "Status Conferência"]
                rows_t = [[P(h, fs=8.5, bold=True, cor=BRANCO, align=TA_CENTER)
                           for h in hdrs_t]]

                for tr in sorted(transferencias, key=lambda x: x["filial"]):
                    rows_t.append([
                        P(f"  {tr['filial']}", fs=10, bold=True, cor=AZUL_PIX),
                        P(tr["data"], fs=10, align=TA_CENTER),
                        P(f"R$ {tr['valor']:,.2f}", fs=11, bold=True,
                          cor=VERDE, align=TA_RIGHT),
                        P(tr["obs"] or "—", fs=9),
                        P("( )", fs=11, align=TA_CENTER),
                    ])

                # Linha total transferido
                rows_t.append([
                    P("TOTAL GERAL TRANSFERIDO", bold=True, fs=11, cor=BRANCO),
                    "", "",
                    P(f"R$ {total:,.2f}", bold=True, fs=12.5,
                      cor=CREME, align=TA_RIGHT),
                    "",
                ])

                nr = len(rows_t)
                # Altura das linhas para preencher melhor o espaço (mínimo 30pt por linha de dados)
                h_rows = [None] + [32]*(nr-2) + [38] 
                
                tbl_t = Table(rows_t, colWidths=cw_transf, rowHeights=h_rows, repeatRows=1)
                tbl_t.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (-1,0), CINZA_HDR),
                    ("TEXTCOLOR",     (0,0), (-1,0), BRANCO),
                    ("ROWBACKGROUNDS",(0,1), (-1,nr-2), [BRANCO, CINZA_CLR]),
                    ("BACKGROUND",    (0,nr-1), (-1,nr-1), PRETO),
                    ("TEXTCOLOR",     (0,nr-1), (-1,nr-1), BRANCO),
                    ("SPAN",          (0,nr-1), (2,nr-1)),
                    ("SPAN",          (3,nr-1), (4,nr-1)),
                    ("ALIGN",         (3,nr-1), (4,nr-1), "RIGHT"),
                    ("ALIGN",         (1,1), (1,nr-2), "CENTER"),
                    ("ALIGN",         (2,1), (2,nr-2), "RIGHT"),
                    ("ALIGN",         (4,1), (4,nr-2), "CENTER"),
                    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                    ("LINEBEFORE",    (0,0), (0,-1), 4, VINHO_CLR),
                    ("LINEBELOW",     (0,0), (-1,0), 0.5, BEGE),
                    ("LINEBELOW",     (0,1), (-1,nr-2), 0.3, BEGE),
                    ("TOPPADDING",    (0,0), (-1,-1), 8),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                    ("LEFTPADDING",   (0,0), (-1,-1), 8),
                    ("RIGHTPADDING",  (0,0), (-1,-1), 8),
                ]))
                story.append(tbl_t)
                story.append(Spacer(1, 25))

                # ── ÁREA DE OBSERVAÇÕES (Opcional, para preenchimento manual) ──
                story.append(HRFlowable(width="100%", thickness=1, color=BEGE))
                story.append(P("OBSERVAÇÕES ADICIONAIS:", fs=8, bold=True, cor=colors.HexColor("#141414")))
                story.append(Spacer(1, 40)) # Espaço em branco para anotação manual
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#141414")))
                story.append(Spacer(1, 25))

                # ── ASSINATURAS ──
                story.append(HRFlowable(width="100%", thickness=0.5, color=BEGE))
                story.append(Spacer(1, 15))

                cw_ass = [doc.width*0.25] * 4
                ass_data = [[
                    Table([[P("_"*28, fs=8), P("Conferido por / Matriz",
                              fs=7.5, cor=colors.HexColor("#141414"), align=TA_CENTER)]],
                           colWidths=[doc.width*0.25]),
                    Table([[P("_"*28, fs=8), P("Aprovado por / Financeiro",
                              fs=7.5, cor=colors.HexColor("#141414"), align=TA_CENTER)]],
                           colWidths=[doc.width*0.25]),
                    Table([[P("_"*28, fs=8), P("Responsável / Filial",
                              fs=7.5, cor=colors.HexColor("#141414"), align=TA_CENTER)]],
                           colWidths=[doc.width*0.25]),
                    Table([[P("_"*28, fs=8), P(f"Data: ____/____/______",
                              fs=7.5, cor=colors.HexColor("#141414"), align=TA_CENTER)]],
                           colWidths=[doc.width*0.25]),
                ]]
                tbl_ass = Table(ass_data, colWidths=cw_ass)
                tbl_ass.setStyle(TableStyle([
                    ("ALIGN",  (0,0), (-1,-1), "CENTER"),
                    ("VALIGN", (0,0), (-1,-1), "BOTTOM"),
                ]))
                story.append(tbl_ass)
                story.append(Spacer(1, 10))

                # ── RODAPÉ ──
                story.append(HRFlowable(width="100%", thickness=0.5, color=BEGE))
                story.append(P(
                    "Documento interno · Uso exclusivo Contas a Pagar BOAH/SOLAR  ·  "
                    f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}  ·  "
                    "Robô Financeiro BOAH v17 — Roberto Cerqueira",
                    fs=6, cor=colors.HexColor("#141414"), align=TA_CENTER
                ))

                doc.build(story)

                lbl_status.config(
                    text=f"✅ PDF gerado: {nome_arq}", fg="#ffffff")
                win.after(1200, win.destroy)
                os.startfile(caminho)

            except Exception as e:
                lbl_status.config(text=f"❌ Erro: {e}", fg="#a1a1aa")

        # Botões da janela modal
        frm_btns = tk.Frame(win, bg=bg_w)
        frm_btns.pack(fill="x", padx=20, pady=(8,12))
        tk.Button(frm_btns, text="📄 Gerar PDF",
                  font=("Segoe UI",10,"bold"), bg="#ffffff", fg="white",
                  relief="flat", bd=0, padx=18, pady=7, cursor="hand2",
                  command=_gerar).pack(side="right")
        tk.Button(frm_btns, text="Cancelar",
                  font=("Segoe UI",9), bg=surf_w, fg=muted_w,
                  relief="flat", bd=0, padx=12, pady=7, cursor="hand2",
                  command=win.destroy).pack(side="right", padx=(0,8))


    def _enviar_para_autorizacao(self):
        """Abre a aba de Autorização com os comprovantes selecionados como referência."""
        selecionados = self.tree.selection()
        if not selecionados:
            itens = self._resultados_busca[:50]  # máx 50
        else:
            indices = [self.tree.index(s) for s in selecionados]
            itens = [self._resultados_busca[i] for i in indices]

        if not itens:
            self.lbl_status_envio.config(
                text="⚠️ Nenhum item selecionado.", fg="#ffffff")
            return

        # Converte para o formato da aba autorização e injeta
        pgtos = []
        for item in itens:
            pgtos.append({
                "nome":        item['nome'],
                "cnpj":        "",
                "tipo":        "Comprovante",
                "data":        item['data'].strftime("%d/%m/%Y"),
                "data_obj":    item['data'],
                "valor":       item['valor'],
                "status":      "Aprovada",
                "responsavel": "",
                "categoria":   item['categoria'],
                "empresa":     item.get('empresa','LALUA'),
            })

        self._aut_pagamentos = pgtos
        self.root.after(0, self._aut_popular_treeview)

        # Vai para aba Autorização
        try:
            self.notebook.select(6)  # índice da aba Autorização
        except: pass

        self.lbl_status_envio.config(
            text=f"✅ {len(pgtos)} item(ns) enviados para Autorização de Pagamentos",
            fg="#a1a1aa")

    def _gerar_relatorio_pagamentos_excel(self):
        """Gera e salva o relatório analítico dos pagamentos no banco de dados."""
        from utils.relatorios_processor import gerar_excel_pagamentos_autorizados
        
        caminho_saida = filedialog.asksaveasfilename(
            title="Salvar Relatório Analítico de Pagamentos",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"Relatorio_Pagamentos_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
        
        if not caminho_saida:
            return
            
        sucesso, msg = gerar_excel_pagamentos_autorizados(caminho_saida)
        
        if sucesso:
            self._aut_lbl_resumo.configure(text=f"✅ Relatório salvo: {os.path.basename(caminho_saida)}", text_color="#ffffff")
            os.startfile(caminho_saida)
        else:
            self._aut_lbl_resumo.configure(text=f"❌ Erro: {msg}", text_color="#a1a1aa")


    def _build_aba_manual(self, parent, bg, surface, border, accent, green, yellow, text, muted):
        """Aba dedicada para lançamentos manuais."""
        hdr = tk.Frame(parent, bg=bg)
        hdr.pack(fill="x", padx=20, pady=(12, 10))
        tk.Label(hdr, text="➕ Novo Lançamento Manual",
                 font=("Segoe UI", 13, "bold"), fg=accent, bg=bg).pack(side="left")

        frame_manual = tk.Frame(parent, bg=surface, padx=20, pady=20)
        frame_manual.pack(fill="x", padx=20, pady=10)

        def _lbl(t):
            return tk.Label(frame_manual, text=t, fg=muted, bg=surface, font=("Segoe UI", 10))
        def _ent(w=30):
            return tk.Entry(frame_manual, font=("Segoe UI", 10), bg="#0a0a0a", fg=text,
                            insertbackground=accent, relief="flat", bd=4, width=w)

        _lbl("Nome do Beneficiário:").grid(row=0, column=0, sticky="w", pady=8)
        self._man_nome = _ent(40)
        self._man_nome.grid(row=0, column=1, sticky="w", padx=10, columnspan=3)

        _lbl("Empresa:").grid(row=1, column=0, sticky="w", pady=8)
        self._man_emp_var = tk.StringVar(value="LALUA")
        ttk.Combobox(frame_manual, textvariable=self._man_emp_var, values=["LALUA","SOLAR"],
                     state="readonly", width=15).grid(row=1, column=1, sticky="w", padx=10)

        _lbl("Tipo de Pagamento:").grid(row=1, column=2, sticky="w", pady=8)
        self._man_tipo_var = tk.StringVar(value="PIX")
        ttk.Combobox(frame_manual, textvariable=self._man_tipo_var,
                     values=["PIX","TED","BOLETO","DARF","GPS","DAS","CONCESSIONÁRIA","PIX FILIAL→MATRIZ"],
                     state="readonly", width=25).grid(row=1, column=3, sticky="w", padx=10)

        _lbl("Data:").grid(row=2, column=0, sticky="w", pady=8)
        self._man_data = _ent(15)
        self._man_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self._man_data.grid(row=2, column=1, sticky="w", padx=10)

        _lbl("Valor (R$):").grid(row=2, column=2, sticky="w", pady=8)
        self._man_valor = _ent(15)
        self._man_valor.grid(row=2, column=3, sticky="w", padx=10)

        _lbl("Categoria:").grid(row=3, column=0, sticky="w", pady=8)
        self._man_cat_var = tk.StringVar()
        ttk.Combobox(frame_manual, textvariable=self._man_cat_var, values=config.CATEGORIAS_LISTA,
                     state="normal", width=38).grid(row=3, column=1, sticky="w", padx=10, columnspan=2)

        _lbl("Responsável:").grid(row=4, column=0, sticky="w", pady=8)
        self._man_resp_var = tk.StringVar()
        ttk.Combobox(frame_manual, textvariable=self._man_resp_var, values=config.RESPONSAVEIS_LISTA,
                     state="readonly", width=20).grid(row=4, column=1, sticky="w", padx=10)

        _lbl("Observação:").grid(row=5, column=0, sticky="w", pady=8)
        self._man_obs = _ent(40)
        self._man_obs.grid(row=5, column=1, sticky="w", padx=10, columnspan=3)

        self._man_status = tk.Label(frame_manual, text="", font=("Segoe UI", 9), fg=yellow, bg=surface)
        self._man_status.grid(row=6, column=0, columnspan=4, pady=15)

        def _adicionar():
            nome = self._man_nome.get().strip()
            valor_s = self._man_valor.get().strip()
            data = self._man_data.get().strip()
            if not nome or not valor_s:
                self._man_status.config(text="⚠️ Nome e Valor são obrigatórios!", fg=yellow)
                return
            try:
                valor = _parse_valor(valor_s)
                data_obj = datetime.strptime(data, "%d/%m/%Y")
                self._aut_pagamentos.append({
                    "nome": nome, "cnpj": "", "tipo": self._man_tipo_var.get(),
                    "data": data, "data_obj": data_obj, "valor": valor,
                    "status": "Aprovada", "responsavel": self._man_resp_var.get() or "ADM/FINANCEIRO",
                    "categoria": self._man_cat_var.get() or "A CLASSIFICAR",
                    "empresa": self._man_emp_var.get(), "observacao": self._man_obs.get(), "manual": True
                })
                self._man_status.config(text=f"✅ Adicionado: {nome} - R$ {valor:,.2f}", fg=green)
                self._man_nome.delete(0, "end")
                self._man_valor.delete(0, "end")
                self._man_obs.delete(0, "end")
                self._aut_popular_treeview()
            except Exception as e:
                self._man_status.config(text=f"❌ Erro: {str(e)}", fg="#a1a1aa")

        tk.Button(frame_manual, text="➕ ADICIONAR AO RELATÓRIO", font=("Segoe UI", 10, "bold"),
                  bg=green, fg="#0a0a0a", relief="flat", bd=0, padx=25, pady=10, cursor="hand2",
                  command=_adicionar).grid(row=7, column=0, columnspan=4, pady=10)
