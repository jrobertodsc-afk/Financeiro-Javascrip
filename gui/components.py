"""
components.py — Biblioteca de componentes reutilizáveis do Com System.

Todos os widgets padronizados são definidos aqui, usando os tokens
do design_system.py para garantir consistência visual.
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from gui.design_system import COLORS, FONTS, SPACING, RADIUS, STATUS_COLORS


# ==============================================================================
# ── STAT CARD ─────────────────────────────────────────────────────────────────
# ==============================================================================

class StatCard(ctk.CTkFrame):
    """Card de métrica com título, valor grande e subtítulo."""

    def __init__(self, parent, title: str, value: str = "—",
                 subtitle: str = "", accent_color: str = None, **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["card"],
            corner_radius=RADIUS["md"],
            border_width=1,
            border_color=COLORS["border"],
            **kwargs
        )
        self._accent = accent_color or COLORS["accent"]

        # Barra de destaque superior
        accent_bar = ctk.CTkFrame(self, fg_color=self._accent, height=3, corner_radius=0)
        accent_bar.pack(fill="x", side="top")

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SPACING["md"], pady=SPACING["md"])

        ctk.CTkLabel(inner, text=title, font=FONTS["label"],
                     text_color=COLORS["muted"]).pack(anchor="w")

        self._val_lbl = ctk.CTkLabel(inner, text=value, font=FONTS["stat"],
                                     text_color=self._accent)
        self._val_lbl.pack(anchor="w", pady=(2, 0))

        if subtitle:
            ctk.CTkLabel(inner, text=subtitle, font=FONTS["caption"],
                         text_color=COLORS["muted"]).pack(anchor="w")

    def set_value(self, value: str):
        self._val_lbl.configure(text=value)


# ==============================================================================
# ── STATUS BADGE ──────────────────────────────────────────────────────────────
# ==============================================================================

class StatusBadge(ctk.CTkLabel):
    """Badge colorido para status de nota/pagamento."""

    def __init__(self, parent, status: str = "PENDENTE", **kwargs):
        fg, bg = STATUS_COLORS.get(status, (COLORS["muted"], COLORS["surface"]))
        super().__init__(
            parent,
            text=f"  {status}  ",
            font=FONTS["badge"],
            text_color=fg,
            fg_color=bg,
            corner_radius=RADIUS["sm"],
            **kwargs
        )

    def set_status(self, status: str):
        fg, bg = STATUS_COLORS.get(status, (COLORS["muted"], COLORS["surface"]))
        self.configure(text=f"  {status}  ", text_color=fg, fg_color=bg)


# ==============================================================================
# ── ACTION BUTTON ─────────────────────────────────────────────────────────────
# ==============================================================================

class ActionButton(ctk.CTkButton):
    """Botão padronizado com variantes: primary, ghost, danger."""

    VARIANTS = {
        "primary": {
            "fg_color":    COLORS["accent"],
            "hover_color": COLORS["accent_dim"],
            "text_color":  COLORS["text_inv"],
            "border_width": 0,
        },
        "ghost": {
            "fg_color":    "transparent",
            "hover_color": COLORS["border"],
            "text_color":  COLORS["text"],
            "border_width": 1,
            "border_color": COLORS["border_light"],
        },
        "danger": {
            "fg_color":    COLORS["error"],
            "hover_color": "#cc2222",
            "text_color":  COLORS["text"],
            "border_width": 0,
        },
        "success": {
            "fg_color":    COLORS["success"],
            "hover_color": "#16a34a",
            "text_color":  COLORS["text_inv"],
            "border_width": 0,
        },
    }

    def __init__(self, parent, text: str, variant: str = "primary",
                 icon_text: str = "", height: int = 36, **kwargs):
        style = self.VARIANTS.get(variant, self.VARIANTS["primary"]).copy()
        style.update(kwargs)
        display = f"{icon_text}  {text}" if icon_text else text
        super().__init__(
            parent,
            text=display,
            font=FONTS["h4"],
            height=height,
            corner_radius=RADIUS["sm"],
            **style
        )


# ==============================================================================
# ── SECTION HEADER ────────────────────────────────────────────────────────────
# ==============================================================================

class SectionHeader(ctk.CTkFrame):
    """Título de seção com linha separadora."""

    def __init__(self, parent, title: str, subtitle: str = "", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")

        ctk.CTkLabel(row, text=title, font=FONTS["h3"],
                     text_color=COLORS["text"]).pack(side="left")

        if subtitle:
            ctk.CTkLabel(row, text=f"  {subtitle}", font=FONTS["body_sm"],
                         text_color=COLORS["muted"]).pack(side="left", pady=(4, 0))

        # Linha separadora
        ctk.CTkFrame(self, fg_color=COLORS["border"], height=1).pack(
            fill="x", pady=(SPACING["sm"], 0))


# ==============================================================================
# ── SEARCH BAR ────────────────────────────────────────────────────────────────
# ==============================================================================

class SearchBar(ctk.CTkFrame):
    """Campo de busca com ícone e botão de limpar."""

    def __init__(self, parent, placeholder: str = "Buscar...",
                 on_search=None, **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["card"],
            corner_radius=RADIUS["sm"],
            border_width=1,
            border_color=COLORS["border"],
            **kwargs
        )
        self._on_search = on_search

        # Ícone lupa (texto)
        ctk.CTkLabel(self, text="⌕", font=(FONTS["h3"][0], 18),
                     text_color=COLORS["muted"], width=30).pack(side="left", padx=(8, 0))

        self._var = tk.StringVar()
        self._var.trace_add("write", self._on_change)

        self._entry = ctk.CTkEntry(
            self,
            textvariable=self._var,
            placeholder_text=placeholder,
            fg_color="transparent",
            border_width=0,
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["muted"],
            font=FONTS["body"],
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=4)

        self._btn_clear = ctk.CTkButton(
            self, text="✕", width=28, height=28,
            fg_color="transparent", hover_color=COLORS["border"],
            text_color=COLORS["muted"], font=FONTS["caption"],
            command=self.clear
        )
        self._btn_clear.pack(side="right", padx=4)

    def _on_change(self, *_):
        if self._on_search:
            self._on_search(self._var.get())

    def get(self) -> str:
        return self._var.get()

    def clear(self):
        self._var.set("")

    def bind_enter(self, callback):
        self._entry.bind("<Return>", lambda e: callback(self.get()))


# ==============================================================================
# ── FORM FIELD ────────────────────────────────────────────────────────────────
# ==============================================================================

class FormField(ctk.CTkFrame):
    """Label + Entry com validação visual."""

    def __init__(self, parent, label: str, placeholder: str = "",
                 required: bool = False, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        lbl_text = f"{label} *" if required else label
        ctk.CTkLabel(self, text=lbl_text, font=FONTS["label"],
                     text_color=COLORS["muted"]).pack(anchor="w", pady=(0, 4))

        self._entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            fg_color=COLORS["card"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["muted"],
            font=FONTS["body"],
            height=36,
        )
        self._entry.pack(fill="x")
        self._error_lbl = None

    def get(self) -> str:
        return self._entry.get()

    def set(self, value: str):
        self._entry.delete(0, "end")
        self._entry.insert(0, value)

    def set_error(self, msg: str = ""):
        if msg:
            self._entry.configure(border_color=COLORS["error"])
            if not self._error_lbl:
                self._error_lbl = ctk.CTkLabel(self, text=msg, font=FONTS["caption"],
                                                text_color=COLORS["error"])
                self._error_lbl.pack(anchor="w", pady=(2, 0))
        else:
            self._entry.configure(border_color=COLORS["border"])
            if self._error_lbl:
                self._error_lbl.destroy()
                self._error_lbl = None

    def configure_entry(self, **kwargs):
        self._entry.configure(**kwargs)


# ==============================================================================
# ── DATA TABLE ────────────────────────────────────────────────────────────────
# ==============================================================================

class DataTable(ctk.CTkFrame):
    """
    Wrapper do ttk.Treeview com estilo do Design System.
    Inclui scrollbar vertical e linhas alternadas (zebra stripe).
    """

    def __init__(self, parent, columns: list[tuple], show_index: bool = False, **kwargs):
        """
        columns: lista de tuplas (id, header_text, width, anchor)
          ex: [("nome", "Nome", 200, "w"), ("valor", "Valor", 100, "e")]
        """
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        col_ids = [c[0] for c in columns]
        show = "headings" if not show_index else "tree headings"

        self.tree = ttk.Treeview(self, columns=col_ids, show=show,
                                  style="DS.Treeview", selectmode="browse")

        for col_id, header, width, anchor in columns:
            self.tree.heading(col_id, text=header,
                              command=lambda c=col_id: self._sort_by(c))
            self.tree.column(col_id, width=width, anchor=anchor, minwidth=40)

        # Scrollbar
        vsb = ttk.Scrollbar(self, orient="vertical",
                             command=self.tree.yview, style="DS.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Zebra stripe tags
        self.tree.tag_configure("odd",  background=COLORS["card"])
        self.tree.tag_configure("even", background=COLORS["surface"])
        self.tree.tag_configure("highlight", background=COLORS["border_light"],
                                foreground=COLORS["accent"])

        self._sort_reverse = {}

    def insert(self, values: tuple, tags=(), iid=None):
        idx = len(self.tree.get_children())
        stripe = "even" if idx % 2 == 0 else "odd"
        final_tags = (stripe,) + tuple(tags)
        return self.tree.insert("", "end", values=values, tags=final_tags, iid=iid)

    def clear(self):
        self.tree.delete(*self.tree.get_children())

    def get_selected(self):
        sel = self.tree.selection()
        if sel:
            return self.tree.item(sel[0])["values"]
        return None

    def _sort_by(self, col):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        reverse = self._sort_reverse.get(col, False)
        try:
            data.sort(key=lambda x: float(x[0].replace("R$", "").replace(".", "").replace(",", ".")),
                      reverse=reverse)
        except (ValueError, AttributeError):
            data.sort(key=lambda x: x[0].lower(), reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.item(k, tags=(tag,))
        self._sort_reverse[col] = not reverse


# ==============================================================================
# ── LOADING SPINNER ───────────────────────────────────────────────────────────
# ==============================================================================

class LoadingSpinner(ctk.CTkFrame):
    """Indicador de carregamento animado via canvas."""

    def __init__(self, parent, size: int = 32, color: str = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._color = color or COLORS["accent"]
        self._size = size
        self._angle = 0
        self._running = False

        self._canvas = tk.Canvas(self, width=size, height=size,
                                  bg=COLORS["bg"], highlightthickness=0)
        self._canvas.pack()
        self._arc = self._canvas.create_arc(
            4, 4, size - 4, size - 4,
            start=0, extent=270,
            outline=self._color, width=3, style="arc"
        )

    def start(self):
        self._running = True
        self._animate()

    def stop(self):
        self._running = False

    def _animate(self):
        if not self._running:
            return
        self._angle = (self._angle + 8) % 360
        self._canvas.itemconfig(self._arc, start=self._angle)
        self.after(16, self._animate)


# ==============================================================================
# ── PANEL CARD ────────────────────────────────────────────────────────────────
# ==============================================================================

class PanelCard(ctk.CTkFrame):
    """Card de painel com cabeçalho opcional e área de conteúdo."""

    def __init__(self, parent, title: str = "", icon: str = "", **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["card"],
            corner_radius=RADIUS["md"],
            border_width=1,
            border_color=COLORS["border"],
            **kwargs
        )
        if title:
            header = ctk.CTkFrame(self, fg_color=COLORS["surface"],
                                   corner_radius=0, height=40)
            header.pack(fill="x", side="top")
            header.pack_propagate(False)

            lbl = f"{icon}  {title}" if icon else title
            ctk.CTkLabel(header, text=lbl, font=FONTS["h4"],
                         text_color=COLORS["accent"]).pack(side="left",
                                                            padx=SPACING["md"])

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True,
                          padx=SPACING["md"], pady=SPACING["md"])
