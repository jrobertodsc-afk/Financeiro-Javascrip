"""
gui/tabs/pagamentos_tab.py — Aba de Pagamentos Pendentes (padrão CTkFrame).
Lista notas com status PENDENTE e APROVADA + rodapé para geração de remessa CNAB 240.
"""
import os
import threading
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from datetime import datetime, date, timedelta
from loguru import logger

import config
from gui.design_system import COLORS, FONTS, apply_treeview_style


class PagamentosTab(ctk.CTkFrame):
    """
    Aba de Pagamentos Pendentes do ComSystem.

    Atributos de self.master (ComSystemApp) usados:
      - Nenhum: dados via db/listar_notas() importados diretamente
      - Cores via COLORS (design_system)

    Métodos externos chamados:
      - services.database.listar_notas()  — lista notas com filtro de status
      - cnab_generator.gerar_remessa_notas() — gera arquivo .REM
      - config.CNAB_CONTAS — lista de bancos disponíveis
      - config.PASTA_SAIDA  — pasta destino do arquivo
    """

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg"])
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)
        self.master = master
        self._build_ui()
        self.refresh()

    # ─────────────────────────────────────────────────────────────────────────
    # BUILD UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── TÍTULO ──
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=30, pady=(24, 8))

        ctk.CTkLabel(
            topo,
            text="💳 PAGAMENTOS PENDENTES",
            font=("Segoe UI", 22, "bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            topo,
            text="Notas com status PENDENTE e APROVADA aguardando pagamento.",
            font=("Segoe UI", 13),
            text_color=COLORS["muted"],
        ).pack(anchor="w", pady=(2, 0))

        # ── TOOLBAR ──
        tb = ctk.CTkFrame(self, fg_color="transparent")
        tb.pack(fill="x", padx=20, pady=(8, 4))

        self._filtro_status = ctk.StringVar(value="PENDENTE")
        seg = ctk.CTkSegmentedButton(
            tb,
            variable=self._filtro_status,
            values=["TODOS", "PENDENTE", "APROVADA"],
            selected_color=COLORS["border_light"],
            selected_hover_color=COLORS["border_light"],
            unselected_color=COLORS["surface"],
            unselected_hover_color=COLORS["border"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            command=lambda _: self.refresh(),
        )
        seg.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(tb, text="Empresa:", font=FONTS["caption"],
                     text_color=COLORS["muted"]).pack(side="left", padx=(0, 5))
        self._filtro_emp = ctk.CTkComboBox(
            tb, values=["TODOS", "LALUA", "SOLAR"], width=110,
            fg_color=COLORS["border"], border_color=COLORS["border_light"],
            button_color=COLORS["border_light"], text_color=COLORS["text"],
            command=lambda _: self.refresh(),
        )
        self._filtro_emp.set("TODOS")
        self._filtro_emp.pack(side="left", padx=(0, 20))

        ctk.CTkButton(
            tb, text="🔄 Atualizar", width=110, height=30,
            fg_color=COLORS["border_light"], hover_color="#475569",
            text_color=COLORS["text"], font=FONTS["label"],
            command=self.refresh,
        ).pack(side="left")

        self._lbl_total = ctk.CTkLabel(
            tb, text="", font=FONTS["body"], text_color=COLORS["muted"],
        )
        self._lbl_total.pack(side="right", padx=(0, 10))

        # ── TREEVIEW ──
        cols = ("Nº TX", "Fornecedor", "Empresa", "Vencimento",
                "Atraso", "Valor Bruto", "Valor Líquido", "Status", "Forma Pgto")

        tree_frame = tk.Frame(self, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(4, 0))

        self._tree = ttk.Treeview(
            tree_frame, columns=cols,
            style="DS.Treeview", show="headings", height=16,
        )
        col_widths = [110, 220, 70, 90, 60, 110, 110, 80, 110]
        for c, w in zip(cols, col_widths):
            self._tree.heading(c, text=c,
                               command=lambda _c=c: self._ordenar_coluna(_c))
            self._tree.column(
                c, width=w,
                anchor="e" if c in ("Valor Bruto", "Valor Líquido", "Atraso") else "w",
            )

        self._tree.tag_configure("PENDENTE",  foreground="#fbbf24")
        self._tree.tag_configure("APROVADA",  foreground="#38bdf8")
        self._tree.tag_configure("ATRASADA",  foreground="#f87171", background="#1a0000")

        sb_v = ttk.Scrollbar(tree_frame, orient="vertical",
                              command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb_v.set)
        sb_v.pack(side="right", fill="y")
        self._tree.pack(side="left", fill="both", expand=True)

        self._sort_col = None
        self._sort_rev = False

        # ── RODAPÉ CNAB ──
        self._build_cnab_footer()

    def _build_cnab_footer(self):
        """Rodapé com gerador de remessa CNAB 240."""
        rod = ctk.CTkFrame(
            self, fg_color=COLORS["surface"],
            corner_radius=0, border_width=1,
            border_color=COLORS["border"],
        )
        rod.pack(fill="x", side="bottom", padx=0, pady=0)

        inner = ctk.CTkFrame(rod, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            inner, text="Gerar remessa bancária:",
            font=FONTS["label"], text_color=COLORS["muted"],
        ).pack(side="left", padx=(0, 10))

        bancos = list(config.CNAB_CONTAS.keys()) if config.CNAB_CONTAS else ["ITAÚ"]
        self.combo_banco = ctk.CTkComboBox(
            inner, values=bancos, width=130, state="readonly",
            fg_color=COLORS["border"], border_color=COLORS["border_light"],
            button_color=COLORS["border_light"], text_color=COLORS["text"],
            font=FONTS["body"],
        )
        self.combo_banco.set(bancos[0])
        self.combo_banco.pack(side="left", padx=(0, 12))

        self.btn_cnab = ctk.CTkButton(
            inner, text="Gerar CNAB 240", width=140, height=30,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_dim"],
            text_color=COLORS["text_inv"], font=FONTS["label"],
            command=self._gerar_cnab,
        )
        self.btn_cnab.pack(side="left", padx=(0, 16))

        self.lbl_cnab_status = ctk.CTkLabel(
            inner, text="", font=FONTS["body"],
            text_color=COLORS["muted"],
        )
        self.lbl_cnab_status.pack(side="left", padx=(0, 10))

        # Botão "Abrir pasta" — criado sob demanda após sucesso
        self._btn_abrir = None

    # ─────────────────────────────────────────────────────────────────────────
    # REFRESH / DADOS
    # ─────────────────────────────────────────────────────────────────────────

    def refresh(self):
        """Recarrega a lista de notas do banco conforme filtros selecionados."""
        try:
            from services.database import listar_notas

            st  = self._filtro_status.get()
            emp = self._filtro_emp.get()

            status_arg  = None if st  == "TODOS" else st
            empresa_arg = None if emp == "TODOS" else emp

            if status_arg:
                notas = listar_notas(status=status_arg, empresa=empresa_arg) or []
            else:
                # TODOS: busca pendentes + aprovadas
                p = listar_notas(status="PENDENTE", empresa=empresa_arg) or []
                a = listar_notas(status="APROVADA", empresa=empresa_arg) or []
                notas = p + a

            self._popular_tree(notas)

        except Exception as e:
            logger.error(f"Erro ao carregar PagamentosTab: {e}")

    def _popular_tree(self, notas: list):
        """Preenche o Treeview com as notas recebidas."""
        for row in self._tree.get_children():
            self._tree.delete(row)

        hoje = date.today()
        total_bruto = 0.0
        total_liquido = 0.0

        for n in notas:
            status = n.get("status", "PENDENTE")
            vb = n.get("valor_bruto", 0) or 0.0
            vl = n.get("valor_liquido", 0) or 0.0
            total_bruto   += vb
            total_liquido += vl

            # Calcula atraso
            atraso_txt = ""
            tag = status
            try:
                dv = datetime.strptime(n["dt_vencimento"], "%d/%m/%Y").date()
                if status in ("PENDENTE", "APROVADA") and dv < hoje:
                    dias = (hoje - dv).days
                    atraso_txt = f"-{dias}d"
                    tag = "ATRASADA"
            except Exception:
                pass

            vb_fmt = f"R$ {vb:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            vl_fmt = f"R$ {vl:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            self._tree.insert(
                "", "end",
                iid=str(n.get("id", "")),
                values=(
                    n.get("numero_tx", ""),
                    n.get("fornecedor", "")[:45],
                    n.get("empresa", ""),
                    n.get("dt_vencimento", ""),
                    atraso_txt,
                    vb_fmt,
                    vl_fmt,
                    status,
                    n.get("forma_pgto", ""),
                ),
                tags=(tag,),
            )

        total_bruto_fmt   = f"R$ {total_bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        total_liquido_fmt = f"R$ {total_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self._lbl_total.configure(
            text=f"{len(notas)} notas | Bruto: {total_bruto_fmt} | Líquido: {total_liquido_fmt}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ORDENAÇÃO
    # ─────────────────────────────────────────────────────────────────────────

    def _ordenar_coluna(self, col: str):
        try:
            items = [(self._tree.set(k, col), k) for k in self._tree.get_children("")]
            rev = (self._sort_col == col and not self._sort_rev)
            items.sort(reverse=rev)
            for idx, (_, k) in enumerate(items):
                self._tree.move(k, "", idx)
            self._sort_col = col
            self._sort_rev = rev
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # GERAÇÃO CNAB
    # ─────────────────────────────────────────────────────────────────────────

    def _gerar_cnab(self):
        """Dispara a geração do arquivo CNAB 240 em thread de background."""
        banco = self.combo_banco.get()
        self.btn_cnab.configure(state="disabled", text="Gerando...")
        self.lbl_cnab_status.configure(text="⏳ Aguarde...", text_color=COLORS["muted"])
        if self._btn_abrir:
            self._btn_abrir.destroy()
            self._btn_abrir = None

        def _worker():
            try:
                from cnab_generator import gerar_remessa_notas
                resultado = gerar_remessa_notas(banco=banco)
            except Exception as e:
                resultado = {"notas_incluidas": 0, "valor_total": 0.0,
                             "arquivo_gerado": None, "erro": str(e)}
            self.after(0, lambda r=resultado: self._on_cnab_done(r))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_cnab_done(self, resultado: dict):
        """Callback na thread principal após geração do CNAB."""
        self.btn_cnab.configure(state="normal", text="Gerar CNAB 240")

        erro = resultado.get("erro")
        if not erro:
            qtd   = resultado.get("notas_incluidas", 0)
            total = resultado.get("valor_total", 0.0)
            arq   = resultado.get("arquivo_gerado", "")
            total_fmt = f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.lbl_cnab_status.configure(
                text=f"✓ {arq}  |  {qtd} notas  |  {total_fmt}",
                text_color=COLORS["success"],
            )
            # Botão "Abrir pasta"
            inner = self.lbl_cnab_status.master
            self._btn_abrir = ctk.CTkButton(
                inner, text="📂 Abrir pasta", width=110, height=28,
                fg_color=COLORS["border_light"], hover_color="#475569",
                text_color=COLORS["text"], font=FONTS["label"],
                command=lambda: os.startfile(config.PASTA_SAIDA),
            )
            self._btn_abrir.pack(side="left", padx=(12, 0))
        else:
            self.lbl_cnab_status.configure(
                text=f"Erro: {erro}",
                text_color=COLORS["error"],
            )
