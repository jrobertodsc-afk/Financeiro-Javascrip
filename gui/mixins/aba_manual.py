"""
gui/mixins/aba_manual.py — Módulo de Lançamento Manual de Comprovantes.

Permite registrar pagamentos avulsos sem PDF:
  - Formulário completo com validação em tempo real
  - Auto-classificação inteligente por nome/CNPJ
  - Histórico paginado com filtros
  - Exportação Excel e exclusão de registros
  - Integração com pagamentos_autorizados (banco SQLite + Supabase)
"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import customtkinter as ctk

from config import *
from utils.data_processing import _parse_valor, auto_classificar
from utils.formatters import _aplicar_mascara_data, _aplicar_mascara_valor
from database import salvar_pagamentos_autorizados, listar_pagamentos_autorizados


class AbaManualMixin:
    """
    Mixin que implementa a Aba de Lançamento Manual.
    Registra pagamentos/comprovantes avulsos sem necessidade de PDF.
    """

    # ══════════════════════════════════════════════════════════════════════════
    # ── BUILD PRINCIPAL ───────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _build_aba_manual(self, parent,
                          bg, surface, border, accent, green, yellow, text, muted):

        self._man_registros = []        # cache de registros carregados
        self._man_ordem_col = "data"
        self._man_ordem_rev = True
        self._man_anexo_path = None

        # ── SCROLLABLE CONTAINER ─────────────────────────────────────────────
        scroll_frame = ctk.CTkScrollableFrame(
            parent, fg_color=bg, scrollbar_button_color=border,
            scrollbar_button_hover_color=accent,
        )
        scroll_frame.pack(fill="both", expand=True)

        # ── CABEÇALHO ────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=25, pady=(20, 4))

        ctk.CTkLabel(
            hdr, text="✏️  LANÇAMENTO MANUAL",
            font=("Segoe UI", 16, "bold"), text_color=accent
        ).pack(side="left")

        ctk.CTkLabel(
            hdr,
            text="Registre pagamentos e comprovantes sem PDF",
            font=("Segoe UI", 11), text_color=muted
        ).pack(side="left", padx=(16, 0))

        # ── FORMULÁRIO ───────────────────────────────────────────────────────
        self._man_build_form(scroll_frame, bg, surface, border, accent, green, yellow, text, muted)

        # ── HISTÓRICO ────────────────────────────────────────────────────────
        self._man_build_historico(scroll_frame, bg, surface, border, accent, green, yellow, text, muted)

        # Carrega histórico ao abrir
        self.after(300, self._man_carregar_historico)

    # ══════════════════════════════════════════════════════════════════════════
    # ── FORMULÁRIO ───────────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _man_build_form(self, parent,
                        bg, surface, border, accent, green, yellow, text, muted):

        form_frame = ctk.CTkFrame(
            parent, fg_color=surface,
            corner_radius=12, border_width=1, border_color=border
        )
        form_frame.pack(fill="x", padx=25, pady=(0, 16))

        ctk.CTkLabel(
            form_frame, text="NOVO LANÇAMENTO",
            font=("Segoe UI", 10, "bold"), text_color=muted
        ).pack(anchor="w", padx=16, pady=(12, 4))

        # ── Templates Rápidos ────────────────────────────────────────────────
        qa_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        qa_frame.pack(fill="x", padx=16, pady=(0, 12))
        
        ctk.CTkButton(qa_frame, text="⚡ Tarifa Bancária", height=28, width=120, fg_color=surface, border_color=border, border_width=1, hover_color=border, text_color=text, command=lambda: self._man_template("TARIFA")).pack(side="left", padx=(0, 8))
        ctk.CTkButton(qa_frame, text="⚡ Retirada Sócio", height=28, width=120, fg_color=surface, border_color=border, border_width=1, hover_color=border, text_color=text, command=lambda: self._man_template("SOCIO")).pack(side="left", padx=(0, 8))
        ctk.CTkButton(qa_frame, text="⚡ PIX Avulso", height=28, width=100, fg_color=surface, border_color=border, border_width=1, hover_color=border, text_color=text, command=lambda: self._man_template("PIX")).pack(side="left", padx=(0, 8))

        # ── Linha 1: Nome / CNPJ / Empresa ───────────────────────────────────
        l1 = ctk.CTkFrame(form_frame, fg_color="transparent")
        l1.pack(fill="x", padx=16, pady=(0, 10))

        # Nome/Favorecido
        ctk.CTkLabel(l1, text="NOME / FAVORECIDO *", font=("Segoe UI", 9, "bold"),
                     text_color=muted).grid(row=0, column=0, sticky="w")
        self._man_nome = ctk.CTkEntry(
            l1, font=("Segoe UI", 12), fg_color=bg, border_color=border,
            placeholder_text="Ex: COELBA, Fornecedor XYZ...",
            width=320, height=38
        )
        self._man_nome.grid(row=1, column=0, padx=(0, 16), pady=(4, 0))
        self._man_nome.bind("<FocusOut>", self._man_auto_classificar)
        self._man_nome.bind("<Return>", self._man_auto_classificar)

        # CNPJ/CPF
        ctk.CTkLabel(l1, text="CNPJ / CPF", font=("Segoe UI", 9, "bold"),
                     text_color=muted).grid(row=0, column=1, sticky="w")
        self._man_cnpj = ctk.CTkEntry(
            l1, font=("Segoe UI", 12), fg_color=bg, border_color=border,
            placeholder_text="00.000.000/0001-00",
            width=180, height=38
        )
        self._man_cnpj.grid(row=1, column=1, padx=(0, 16), pady=(4, 0))
        self._man_cnpj.bind("<FocusOut>", self._man_auto_classificar)

        # Empresa
        ctk.CTkLabel(l1, text="EMPRESA *", font=("Segoe UI", 9, "bold"),
                     text_color=muted).grid(row=0, column=2, sticky="w")
        self._man_empresa_var = tk.StringVar(value="LALUA")
        self._man_empresa = ctk.CTkOptionMenu(
            l1, values=["LALUA", "SOLAR"],
            variable=self._man_empresa_var,
            fg_color=bg, button_color=border,
            button_hover_color=accent,
            dropdown_fg_color=surface,
            width=120, height=38
        )
        self._man_empresa.grid(row=1, column=2, padx=(0, 16), pady=(4, 0))

        # Filial
        ctk.CTkLabel(l1, text="FILIAL", font=("Segoe UI", 9, "bold"),
                     text_color=muted).grid(row=0, column=3, sticky="w")
        self._man_filial_var = tk.StringVar(value="MATRIZ")
        self._man_filial = ctk.CTkOptionMenu(
            l1,
            values=["MATRIZ", "BARRA", "HORTO", "PASEO",
                    "SDB", "VILAS", "BELA VISTA", "LAURO", "CAMAÇARI", "GERAL"],
            variable=self._man_filial_var,
            fg_color=bg, button_color=border,
            button_hover_color=accent,
            dropdown_fg_color=surface,
            width=140, height=38
        )
        self._man_filial.grid(row=1, column=3, pady=(4, 0))

        # ── Linha 2: Tipo / Data / Valor / Responsável ────────────────────────
        l2 = ctk.CTkFrame(form_frame, fg_color="transparent")
        l2.pack(fill="x", padx=16, pady=(0, 10))

        # Tipo
        ctk.CTkLabel(l2, text="TIPO *", font=("Segoe UI", 9, "bold"),
                     text_color=muted).grid(row=0, column=0, sticky="w")
        self._man_tipo_var = tk.StringVar(value="PIX")
        self._man_tipo = ctk.CTkOptionMenu(
            l2,
            values=["PIX", "TED", "DOC", "BOLETO", "DINHEIRO",
                    "CARTÃO", "TRANSFERÊNCIA", "CHEQUE", "OUTROS"],
            variable=self._man_tipo_var,
            fg_color=bg, button_color=border,
            button_hover_color=accent,
            dropdown_fg_color=surface,
            width=150, height=38
        )
        self._man_tipo.grid(row=1, column=0, padx=(0, 16), pady=(4, 0))

        # Data
        ctk.CTkLabel(l2, text="DATA DO PAGAMENTO *", font=("Segoe UI", 9, "bold"),
                     text_color=muted).grid(row=0, column=1, sticky="w")
        self._man_data = ctk.CTkEntry(
            l2, font=("Segoe UI", 12), fg_color=bg, border_color=border,
            width=140, height=38
        )
        self._man_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self._man_data.grid(row=1, column=1, padx=(0, 16), pady=(4, 0))
        _aplicar_mascara_data(self._man_data)

        # Valor
        ctk.CTkLabel(l2, text="VALOR (R$) *", font=("Segoe UI", 9, "bold"),
                     text_color=muted).grid(row=0, column=2, sticky="w")
        self._man_valor = ctk.CTkEntry(
            l2, font=("Segoe UI", 12), fg_color=bg, border_color=border,
            placeholder_text="0,00",
            width=150, height=38
        )
        self._man_valor.grid(row=1, column=2, padx=(0, 16), pady=(4, 0))

        # Responsável
        ctk.CTkLabel(l2, text="RESPONSÁVEL", font=("Segoe UI", 9, "bold"),
                     text_color=muted).grid(row=0, column=3, sticky="w")
        self._man_responsavel = ctk.CTkEntry(
            l2, font=("Segoe UI", 12), fg_color=bg, border_color=border,
            placeholder_text="Nome do aprovador",
            width=200, height=38
        )
        self._man_responsavel.grid(row=1, column=3, pady=(4, 0))

        # ── Linha 3: Categoria / Observação ──────────────────────────────────
        l3 = ctk.CTkFrame(form_frame, fg_color="transparent")
        l3.pack(fill="x", padx=16, pady=(0, 14))

        # Categoria (auto-preenchida mas editável)
        ctk.CTkLabel(l3, text="CATEGORIA CONTÁBIL", font=("Segoe UI", 9, "bold"),
                     text_color=muted).grid(row=0, column=0, sticky="w")

        # Usa lista de categorias do config
        cats = getattr(__import__('config'), 'CATEGORIAS_LISTA', [
            "ADM/FINANCEIRO", "FORNECEDORES", "RH", "IMPOSTOS",
            "LOGISTICA", "MARKETING", "TRANSFERENCIA"
        ])
        self._man_cat_var = tk.StringVar(value="A CLASSIFICAR")
        self._man_cat = ctk.CTkOptionMenu(
            l3,
            values=["A CLASSIFICAR"] + list(cats),
            variable=self._man_cat_var,
            fg_color=bg, button_color=border,
            button_hover_color=accent,
            dropdown_fg_color=surface,
            width=280, height=38
        )
        self._man_cat.grid(row=1, column=0, padx=(0, 16), pady=(4, 0))

        # Observação
        ctk.CTkLabel(l3, text="OBSERVAÇÃO", font=("Segoe UI", 9, "bold"),
                     text_color=muted).grid(row=0, column=1, sticky="w")
        self._man_obs = ctk.CTkEntry(
            l3, font=("Segoe UI", 12), fg_color=bg, border_color=border,
            placeholder_text="Nota, referência, nº doc...",
            width=320, height=38
        )
        self._man_obs.grid(row=1, column=1, pady=(4, 0))
        
        # Anexo
        self._man_btn_anexo = ctk.CTkButton(
            l3, text="📎 Anexar Comprovante", font=("Segoe UI", 11), fg_color=surface, text_color=text, border_width=1, border_color=border, hover_color=border, height=38, width=150, command=self._man_anexar
        )
        self._man_btn_anexo.grid(row=1, column=2, padx=(16, 0), pady=(4, 0))
        
        self._man_lbl_anexo = ctk.CTkLabel(l3, text="", font=("Segoe UI", 9), text_color=muted)
        self._man_lbl_anexo.grid(row=2, column=2, sticky="w", padx=(16, 0))

        # ── Indicador de auto-classificação ──────────────────────────────────
        self._man_lbl_class = ctk.CTkLabel(
            form_frame, text="",
            font=("Segoe UI", 10), text_color=accent
        )
        self._man_lbl_class.pack(anchor="w", padx=16, pady=(0, 4))

        # ── Botões de ação ────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(4, 16))

        self._man_btn_rascunho = ctk.CTkButton(
            btn_row,
            text="📝 SALVAR RASCUNHO",
            font=("Segoe UI", 11, "bold"),
            fg_color=surface, text_color=text,
            border_width=1, border_color=border, hover_color=border,
            height=42, width=160,
            command=lambda: self._man_salvar("RASCUNHO")
        )
        self._man_btn_rascunho.pack(side="left")

        self._man_btn_salvar = ctk.CTkButton(
            btn_row,
            text="✅ LANÇAR E APROVAR",
            font=("Segoe UI", 12, "bold"),
            fg_color=accent, text_color="#000000",
            hover_color=green,
            height=42, width=180,
            command=lambda: self._man_salvar("MANUAL")
        )
        self._man_btn_salvar.pack(side="left", padx=(12, 0))

        ctk.CTkButton(
            btn_row,
            text="🔄 Limpar Formulário",
            font=("Segoe UI", 11),
            fg_color=surface, text_color=text,
            border_width=1, border_color=border,
            hover_color=border,
            height=42, width=160,
            command=self._man_limpar_form
        ).pack(side="left", padx=12)

        self._man_lbl_status = ctk.CTkLabel(
            btn_row, text="", font=("Segoe UI", 11, "bold"), text_color=muted
        )
        self._man_lbl_status.pack(side="right", padx=8)

        # Guarda referência de cores para uso nos métodos
        self._man_colors = dict(
            bg=bg, surface=surface, border=border, accent=accent,
            green=green, yellow=yellow, text=text, muted=muted
        )

    # ══════════════════════════════════════════════════════════════════════════
    # ── HISTÓRICO ─────────────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _man_build_historico(self, parent,
                              bg, surface, border, accent, green, yellow, text, muted):

        # Separador
        ctk.CTkFrame(parent, fg_color=border, height=1).pack(
            fill="x", padx=25, pady=(0, 12)
        )

        # Cabeçalho histórico + filtros
        hdr = ctk.CTkFrame(parent, fg_color="transparent")
        hdr.pack(fill="x", padx=25, pady=(0, 8))

        ctk.CTkLabel(
            hdr, text="📋  HISTÓRICO DE LANÇAMENTOS",
            font=("Segoe UI", 13, "bold"), text_color=text
        ).pack(side="left")

        # Filtros inline
        self._man_filtro_nome = ctk.CTkEntry(
            hdr, font=("Segoe UI", 11), fg_color=bg, border_color=border,
            placeholder_text="🔍 Filtrar por nome...",
            width=200, height=32
        )
        self._man_filtro_nome.pack(side="left", padx=(20, 8))
        self._man_filtro_nome.bind("<KeyRelease>", lambda e: self._man_filtrar())

        self._man_filtro_empresa_var = tk.StringVar(value="Todas")
        ctk.CTkOptionMenu(
            hdr,
            values=["Todas", "LALUA", "SOLAR"],
            variable=self._man_filtro_empresa_var,
            fg_color=bg, button_color=border, button_hover_color=accent,
            dropdown_fg_color=surface,
            width=100, height=32,
            command=lambda v: self._man_filtrar()
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            hdr,
            text="🔄 Atualizar",
            font=("Segoe UI", 10, "bold"),
            fg_color=surface, text_color=accent,
            border_width=1, border_color=border,
            height=32, width=100,
            command=self._man_carregar_historico
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            hdr,
            text="📥 Exportar Excel",
            font=("Segoe UI", 10, "bold"),
            fg_color="transparent", text_color=yellow,
            border_width=1, border_color=yellow,
            hover_color="#2d2d00",
            height=32, width=130,
            command=self._man_exportar_excel
        ).pack(side="left", padx=4)

        self._man_lbl_total = ctk.CTkLabel(
            hdr, text="", font=("Segoe UI", 10, "bold"), text_color=muted
        )
        self._man_lbl_total.pack(side="right")

        # ── Treeview ─────────────────────────────────────────────────────────
        tree_frame = ctk.CTkFrame(
            parent, fg_color=bg, corner_radius=10,
            border_width=1, border_color=border
        )
        tree_frame.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        cols = ("Data", "Nome", "CNPJ", "Tipo", "Empresa", "Filial", "Categoria", "Valor", "Responsável", "Obs")
        self._man_tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                       style="DS.Treeview", selectmode="extended")

        larguras = [90, 240, 140, 80, 70, 100, 200, 110, 130, 180]
        for col, w in zip(cols, larguras):
            self._man_tree.heading(
                col, text=col.upper(),
                command=lambda c=col: self._man_ordenar(c)
            )
            self._man_tree.column(
                col, width=w,
                anchor="e" if col == "Valor" else "w"
            )

        # Tags de linha
        self._man_tree.tag_configure("par",   background="#0a0f1e", foreground="#e2e8f0")
        self._man_tree.tag_configure("impar", background="#111d35", foreground="#e2e8f0")
        self._man_tree.tag_configure("sel",   background="#1e3050", foreground="#CCFF00")

        scroll_y = ctk.CTkScrollbar(
            tree_frame, orientation="vertical", command=self._man_tree.yview,
            button_color=border, button_hover_color=accent
        )
        scroll_x = ctk.CTkScrollbar(
            tree_frame, orientation="horizontal", command=self._man_tree.xview,
            button_color=border, button_hover_color=accent
        )
        self._man_tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        self._man_tree.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        scroll_y.pack(side="right", fill="y", padx=(0, 5), pady=5)
        scroll_x.pack(side="bottom", fill="x", padx=5, pady=(0, 5))

        # Menu de contexto
        self._man_tree.bind("<Button-3>", self._man_menu_contexto)
        self._man_tree.bind("<Double-1>", self._man_editar_selecionado)

    # ══════════════════════════════════════════════════════════════════════════
    # ── LÓGICA DO FORMULÁRIO ──────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _man_template(self, tipo):
        self._man_limpar_form()
        if tipo == "TARIFA":
            self._man_nome.insert(0, "TARIFA BANCARIA")
            self._man_tipo_var.set("OUTROS")
            self._man_cat_var.set("ADM/FINANCEIRO")
            self._man_obs.insert(0, "Tarifa de manutenção/transferência")
        elif tipo == "SOCIO":
            self._man_nome.insert(0, "RETIRADA DE SOCIO")
            self._man_tipo_var.set("PIX")
            self._man_cat_var.set("TRANSFERENCIA")
        elif tipo == "PIX":
            self._man_tipo_var.set("PIX")
            
    def _man_anexar(self):
        f = filedialog.askopenfilename(title="Selecione um Comprovante", filetypes=[("Imagens/PDF", "*.png *.jpg *.jpeg *.pdf")])
        if f:
            self._man_anexo_path = f
            self._man_lbl_anexo.configure(text=f"📎 {os.path.basename(f)[:20]}")

    def _man_auto_classificar(self, event=None):
        """Auto-classifica ao sair do campo Nome ou CNPJ."""
        nome = self._man_nome.get().strip()
        cnpj = self._man_cnpj.get().strip()

        if not nome and not cnpj:
            return

        def classificar():
            try:
                resp, cat = auto_classificar(nome, 0, cnpj)
                if cat and cat != "A CLASSIFICAR":
                    self.after(0, lambda: self._man_cat_var.set(cat))
                    self.after(0, lambda: self._man_responsavel.delete(0, "end"))
                    self.after(0, lambda: self._man_responsavel.insert(0, resp))
                    self.after(0, lambda: self._man_lbl_class.configure(
                        text=f"✨ Auto-classificado: {cat} | {resp}",
                        text_color=self._man_colors.get("accent", "#CCFF00")
                    ))
                else:
                    self.after(0, lambda: self._man_lbl_class.configure(
                        text="⚠️ Não classificado automaticamente — selecione a categoria",
                        text_color=self._man_colors.get("yellow", "#f59e0b")
                    ))
            except Exception as e:
                pass

        threading.Thread(target=classificar, daemon=True).start()

    def _man_limpar_form(self):
        """Limpa todos os campos do formulário."""
        self._man_nome.delete(0, "end")
        self._man_cnpj.delete(0, "end")
        self._man_valor.delete(0, "end")
        self._man_obs.delete(0, "end")
        self._man_responsavel.delete(0, "end")
        self._man_data.delete(0, "end")
        self._man_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self._man_tipo_var.set("PIX")
        self._man_empresa_var.set("LALUA")
        self._man_filial_var.set("MATRIZ")
        self._man_cat_var.set("A CLASSIFICAR")
        self._man_lbl_class.configure(text="")
        self._man_lbl_status.configure(text="")
        self._man_anexo_path = None
        self._man_lbl_anexo.configure(text="")
        self._man_nome.focus()

    def _man_salvar(self, status_val="MANUAL"):
        """Valida e salva o lançamento manual no banco."""
        nome   = self._man_nome.get().strip()
        data   = self._man_data.get().strip()
        valor_str = self._man_valor.get().strip()

        # Validações obrigatórias
        erros = []
        if not nome:
            erros.append("Nome/Favorecido é obrigatório")
        if not data:
            erros.append("Data é obrigatória")
        else:
            try:
                datetime.strptime(data, "%d/%m/%Y")
            except ValueError:
                erros.append("Data inválida — use DD/MM/AAAA")
        if not valor_str:
            erros.append("Valor é obrigatório")
        else:
            valor = _parse_valor(valor_str)
            if valor <= 0:
                erros.append("Valor deve ser maior que zero")

        if erros:
            self._man_lbl_status.configure(
                text="⚠️ " + " | ".join(erros),
                text_color=self._man_colors.get("yellow", "#f59e0b")
            )
            return

        valor = _parse_valor(valor_str)

        registro = {
            "nome":        nome,
            "cnpj":        self._man_cnpj.get().strip(),
            "tipo":        self._man_tipo_var.get(),
            "data":        data,
            "valor":       valor,
            "status":      "MANUAL",
            "responsavel": self._man_responsavel.get().strip(),
            "categoria":   self._man_cat_var.get(),
            "empresa":     self._man_empresa_var.get(),
            "observacao":  f"[{self._man_filial_var.get()}] {self._man_obs.get().strip()}".strip(),
            "data_aprovacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "status":      status_val,
            "anexo":       self._man_anexo_path or ""
        }

        self._man_btn_salvar.configure(
            state="disabled", text="⏳ Salvando..."
        )
        self._man_btn_rascunho.configure(state="disabled")

        def salvar():
            try:
                n = salvar_pagamentos_autorizados([registro])
                def ok():
                    self._man_lbl_status.configure(
                        text=f"✅ Lançamento registrado com sucesso! R$ {valor:,.2f}",
                        text_color=self._man_colors.get("green", "#22c55e")
                    )
                    self._man_btn_salvar.configure(
                        state="normal", text="✅ LANÇAR E APROVAR"
                    )
                    self._man_btn_rascunho.configure(state="normal")
                    self._man_limpar_form()
                    self._man_carregar_historico()
                    # Log na aba principal se disponível
                    try:
                        self._log(f"✅ Manual: {nome} — R$ {valor:,.2f} ({data})")
                    except Exception:
                        pass
                self.after(0, ok)
            except Exception as e:
                def err():
                    self._man_lbl_status.configure(
                        text=f"❌ Erro: {e}",
                        text_color=self._man_colors.get("error", "#ef4444") if "error" in self._man_colors else "#ef4444"
                    )
                    self._man_btn_salvar.configure(
                        state="normal", text="✅ LANÇAR E APROVAR"
                    )
                    self._man_btn_rascunho.configure(state="normal")
                self.after(0, err)

        threading.Thread(target=salvar, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # ── HISTÓRICO / TREEVIEW ──────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _man_carregar_historico(self):
        """Carrega os registros do banco e popula a treeview."""
        def carregar():
            try:
                registros = listar_pagamentos_autorizados() or []
                # Filtra apenas lançamentos manuais ou todos
                self._man_registros = registros
                self.after(0, self._man_filtrar)
            except Exception as e:
                pass

        threading.Thread(target=carregar, daemon=True).start()

    def _man_filtrar(self, event=None):
        """Filtra os registros exibidos na treeview."""
        nome_filtro    = self._man_filtro_nome.get().strip().upper()
        empresa_filtro = self._man_filtro_empresa_var.get()

        filtrados = []
        for r in self._man_registros:
            if nome_filtro and nome_filtro not in str(r.get("nome", "")).upper():
                continue
            if empresa_filtro != "Todas" and r.get("empresa", "").upper() != empresa_filtro.upper():
                continue
            filtrados.append(r)

        # Ordena
        chaves = {
            "Data": "data", "Nome": "nome", "Valor": "valor",
            "Empresa": "empresa", "Categoria": "categoria",
        }
        chave = chaves.get(self._man_ordem_col, "data")
        try:
            filtrados.sort(key=lambda x: x.get(chave, "") or "", reverse=self._man_ordem_rev)
        except Exception:
            pass

        self._man_popular_tree(filtrados)

    def _man_popular_tree(self, registros: list):
        """Popula a treeview com a lista de registros."""
        for row in self._man_tree.get_children():
            self._man_tree.delete(row)

        total_valor = 0.0
        for i, r in enumerate(registros):
            tag = "par" if i % 2 == 0 else "impar"
            valor = float(r.get("valor") or 0)
            total_valor += valor

            obs = str(r.get("observacao") or "")
            self._man_tree.insert("", "end", tags=(tag,), values=(
                r.get("data", ""),
                r.get("nome", ""),
                r.get("cnpj", ""),
                r.get("tipo", ""),
                r.get("empresa", ""),
                # Extrai filial da observação se tiver "[FILIAL]"
                obs.split("]")[0].replace("[", "").strip() if obs.startswith("[") else "",
                r.get("categoria", ""),
                f"R$ {valor:,.2f}",
                r.get("responsavel", ""),
                obs.split("] ", 1)[-1] if "] " in obs else obs,
            ))

        n = len(registros)
        self._man_lbl_total.configure(
            text=f"{n} registro(s)  |  Total: R$ {total_valor:,.2f}"
        )

    def _man_ordenar(self, col: str):
        """Ordena a treeview pela coluna clicada."""
        if self._man_ordem_col == col:
            self._man_ordem_rev = not self._man_ordem_rev
        else:
            self._man_ordem_col = col
            self._man_ordem_rev = col == "Valor"
        self._man_filtrar()

    # ══════════════════════════════════════════════════════════════════════════
    # ── MENU DE CONTEXTO ──────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _man_menu_contexto(self, event):
        """Menu de contexto com clique direito na treeview."""
        menu = tk.Menu(self.root, tearoff=0, bg="#0d1526", fg="#e2e8f0",
                       activebackground="#1e3050", activeforeground="#CCFF00",
                       font=("Segoe UI", 10))
        menu.add_command(label="✏️  Editar registro",
                         command=self._man_editar_selecionado)
        menu.add_command(label="🗑️  Excluir selecionados",
                         command=self._man_excluir_selecionados)
        menu.add_separator()
        menu.add_command(label="📋  Copiar valor",
                         command=self._man_copiar_valor)
        menu.add_separator()
        menu.add_command(label="📥  Exportar Excel",
                         command=self._man_exportar_excel)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _man_editar_selecionado(self, event=None):
        """Preenche o formulário com o registro selecionado para edição."""
        sel = self._man_tree.selection()
        if not sel:
            return
        idx = self._man_tree.index(sel[0])
        # Filtra para pegar o registro correto
        filtrados = [
            r for r in self._man_registros
            if (self._man_filtro_empresa_var.get() == "Todas"
                or r.get("empresa", "").upper() == self._man_filtro_empresa_var.get().upper())
            and (not self._man_filtro_nome.get().strip()
                 or self._man_filtro_nome.get().strip().upper() in str(r.get("nome", "")).upper())
        ]
        if idx >= len(filtrados):
            return
        r = filtrados[idx]

        self._man_limpar_form()
        self._man_nome.insert(0, r.get("nome", ""))
        self._man_cnpj.insert(0, r.get("cnpj", ""))
        self._man_data.delete(0, "end")
        self._man_data.insert(0, r.get("data", ""))
        self._man_valor.insert(0, f"{float(r.get('valor') or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self._man_responsavel.insert(0, r.get("responsavel", ""))
        self._man_obs.insert(0, r.get("observacao", "").split("] ", 1)[-1]
                              if "] " in str(r.get("observacao", "")) else r.get("observacao", ""))
        self._man_tipo_var.set(r.get("tipo", "PIX"))
        self._man_empresa_var.set(r.get("empresa", "LALUA"))
        self._man_cat_var.set(r.get("categoria", "A CLASSIFICAR"))

        self._man_lbl_status.configure(
            text="📝 Dados carregados para edição — salve para atualizar.",
            text_color=self._man_colors.get("yellow", "#f59e0b")
        )

    def _man_excluir_selecionados(self):
        """Remove os registros selecionados (apenas localmente — não implementado no Supabase)."""
        sel = self._man_tree.selection()
        if not sel:
            messagebox.showwarning("Seleção", "Selecione ao menos um registro para excluir.")
            return
        n = len(sel)
        if not messagebox.askyesno(
            "Confirmar exclusão",
            f"Excluir {n} registro(s) selecionado(s)?\n\nEsta ação não pode ser desfeita.",
            default="no"
        ):
            return

        try:
            from database import db_conn
            conn = db_conn()
            indices = [self._man_tree.index(s) for s in sel]
            # Pega IDs dos registros
            filtrados = [
                r for r in self._man_registros
                if (self._man_filtro_empresa_var.get() == "Todas"
                    or r.get("empresa", "").upper() == self._man_filtro_empresa_var.get().upper())
            ]
            ids = [filtrados[i].get("id") for i in indices if i < len(filtrados)]
            ids = [i for i in ids if i]
            if ids:
                conn.executemany(
                    "DELETE FROM pagamentos_autorizados WHERE id=?",
                    [(i,) for i in ids]
                )
                conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao excluir: {e}")
            return

        self._man_carregar_historico()
        self._man_lbl_status.configure(
            text=f"✅ {n} registro(s) excluído(s).",
            text_color=self._man_colors.get("green", "#22c55e")
        )

    def _man_copiar_valor(self):
        """Copia o valor do registro selecionado para o clipboard."""
        sel = self._man_tree.selection()
        if not sel:
            return
        vals = self._man_tree.item(sel[0], "values")
        if vals:
            valor = str(vals[7])  # coluna Valor
            self.clipboard_clear()
            self.clipboard_append(valor)

    # ══════════════════════════════════════════════════════════════════════════
    # ── EXPORTAÇÃO ────────────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _man_exportar_excel(self):
        """Exporta os registros filtrados para Excel (.xlsx)."""
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
            from openpyxl.utils import get_column_letter
        except ImportError:
            messagebox.showerror("Erro", "openpyxl não instalado.\nExecute: pip install openpyxl")
            return

        caminho = filedialog.asksaveasfilename(
            title="Salvar relatório Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"lancamentos_manuais_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        )
        if not caminho:
            return

        # Pega registros filtrados
        filtrados = []
        for item in self._man_tree.get_children():
            filtrados.append(self._man_tree.item(item, "values"))

        if not filtrados:
            messagebox.showwarning("Exportar", "Nenhum registro para exportar.")
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Lançamentos Manuais"

        # Header
        cols = ["Data", "Nome/Favorecido", "CNPJ", "Tipo", "Empresa",
                "Filial", "Categoria", "Valor (R$)", "Responsável", "Observação"]
        larguras = [12, 35, 18, 12, 10, 14, 30, 14, 20, 35]

        for i, (col, w) in enumerate(zip(cols, larguras), start=1):
            cell = ws.cell(row=1, column=i, value=col)
            cell.font       = Font(color="E2E8F0", bold=True, name="Segoe UI", size=10)
            cell.fill       = PatternFill("solid", fgColor="0F172A")
            cell.alignment  = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.row_dimensions[1].height = 22

        for ri, row in enumerate(filtrados, start=2):
            bg = "0A0F1E" if ri % 2 == 0 else "1E293B"
            for ci, val in enumerate(row, start=1):
                cell = ws.cell(row=ri, column=ci, value=val)
                cell.font      = Font(color="E2E8F0", name="Segoe UI", size=9)
                cell.fill      = PatternFill("solid", fgColor=bg)
                cell.alignment = Alignment(vertical="center")

        ws.freeze_panes = "A2"
        ws.sheet_view.showGridLines = False

        # Total
        total = sum(
            _parse_valor(str(row[7]).replace("R$", "").strip())
            for row in filtrados
        )
        tot_row = len(filtrados) + 2
        ws.cell(row=tot_row, column=1, value="TOTAL").font = Font(
            color="4ADE80", bold=True, name="Segoe UI"
        )
        ws.cell(row=tot_row, column=1).fill = PatternFill("solid", fgColor="064E3B")
        ws.cell(row=tot_row, column=8, value=f"R$ {total:,.2f}").font = Font(
            color="4ADE80", bold=True, name="Segoe UI"
        )
        ws.cell(row=tot_row, column=8).fill = PatternFill("solid", fgColor="064E3B")

        # Rodapé
        ws.cell(row=tot_row + 2, column=1,
                value="Gerado por Com System — Agência de Atendimento Digital").font = Font(
            color="475569", size=8, italic=True, name="Segoe UI"
        )

        wb.save(caminho)
        self._man_lbl_status.configure(
            text=f"✅ Excel salvo: {os.path.basename(caminho)}",
            text_color=self._man_colors.get("green", "#22c55e")
        )
        try:
            os.startfile(caminho)
        except Exception:
            pass
