"""
sidebar.py — Sidebar lateral colapsável do Com System.

Sidebar com 220px (expandida) ↔ 60px (colapsada, só ícones).
Implementa um Menu em Cascata (Accordion) para abas agrupadas como o "Financeiro".
Utiliza SVG Icons (via PyMuPDF).
"""

import tkinter as tk
import customtkinter as ctk
from gui.design_system import COLORS, FONTS, SPACING, RADIUS, get_icon

SIDEBAR_W_EXPANDED  = 230
SIDEBAR_W_COLLAPSED = 64
ANIM_STEPS          = 8
ANIM_INTERVAL       = 15

# Definição das Abas Principais e Sub-abas em Cascata
MAIN_TABS = ["Cockpit", "Organizador", "Buscar", "Financeiro", "Fluxo", "Analytics"]
SUB_TABS = {
    "Financeiro": ["Contas a Pagar", "Lançamento Manual", "Adiantamentos", "Fornecedores", "Autorização", "Restituições"]
}

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, tabs: list[str], on_navigate=None, **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["sidebar"],
            corner_radius=0,
            width=SIDEBAR_W_EXPANDED,
            **kwargs
        )
        self.pack_propagate(False)

        # 'tabs' no app_main contém todas as abas. Vamos usar MAIN_TABS para renderizar.
        self._on_navigate  = on_navigate
        self._active_tab   = MAIN_TABS[0]
        self._expanded     = True
        self._anim_target  = SIDEBAR_W_EXPANDED
        self._btn_refs     = {}   # tab_name → (btn_frame, lbl_icon, lbl_text, is_sub)
        
        # Estado do Accordion
        self._cascade_open = {"Financeiro": False}
        self._cascade_frames = {} # tab_name -> CTkFrame container for subtabs

        self._build()

    def _build(self):
        # ── Logo / Cabeçalho ──────────────────────────────────────────────────
        self._header = ctk.CTkFrame(self, fg_color="transparent", height=72)
        self._header.pack(fill="x", side="top")
        self._header.pack_propagate(False)

        self._logo_box = ctk.CTkFrame(
            self._header, fg_color=COLORS["accent"],
            width=38, height=38, corner_radius=RADIUS["sm"]
        )
        self._logo_box.pack(side="left", padx=(16, 10), pady=17)
        self._logo_box.pack_propagate(False)
        ctk.CTkLabel(self._logo_box, text="CS", font=FONTS["h4"],
                     text_color=COLORS["text_inv"]).pack(expand=True)

        self._brand_lbl = ctk.CTkLabel(
            self._header, text="Com System",
            font=FONTS["h4"], text_color=COLORS["text"]
        )
        self._brand_lbl.pack(side="left", anchor="w")

        # ── Botão Toggle (☰) ─────────────────────────────────────────────────
        self._toggle_btn = ctk.CTkButton(
            self._header, text="☰", width=32, height=32,
            fg_color="transparent", hover_color=COLORS["border"],
            text_color=COLORS["muted"], font=(FONTS["h3"][0], 16),
            command=self._toggle_collapse
        )
        self._toggle_btn.pack(side="right", padx=8)

        # ── Separador ────────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color=COLORS["border"], height=1).pack(fill="x")

        # ── Área de Navegação ─────────────────────────────────────────────────
        self._nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._nav_frame.pack(fill="both", expand=True, pady=(SPACING["sm"], 0))

        for tab in MAIN_TABS:
            self._create_nav_item(tab, is_main=True)
            
            # Se tiver sub-abas, criar container
            if tab in SUB_TABS:
                sub_frame = ctk.CTkFrame(self._nav_frame, fg_color="transparent")
                self._cascade_frames[tab] = sub_frame
                # Cria botões das sub-abas
                for sub in SUB_TABS[tab]:
                    self._create_nav_item(sub, is_main=False, parent_frame=sub_frame)

        # ── Rodapé ────────────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color=COLORS["border"], height=1).pack(fill="x")

        footer = ctk.CTkFrame(self, fg_color="transparent", height=56)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        self._version_lbl = ctk.CTkLabel(
            footer, text="v2.1  •  Deep Intelligence",
            font=FONTS["caption"], text_color=COLORS["muted"]
        )
        self._version_lbl.pack(side="left", padx=16, expand=True, anchor="w")

    def _create_nav_item(self, tab_name: str, is_main=True, parent_frame=None):
        if parent_frame is None:
            parent_frame = self._nav_frame
            
        is_active = (tab_name == self._active_tab)
        
        # Sub-abas são menores e mais indentadas
        h = 44 if is_main else 36
        px = SPACING["sm"] if is_main else SPACING["sm"] + 20
        fnt = FONTS["nav"] if is_main else FONTS["nav_sm"]

        item_frame = ctk.CTkFrame(
            parent_frame,
            fg_color=COLORS["accent"] if is_active else "transparent",
            corner_radius=RADIUS["sm"],
            height=h,
            cursor="hand2",
        )
        item_frame.pack(fill="x", padx=(px, SPACING["sm"]), pady=2)
        item_frame.pack_propagate(False)

        # Carregar ícone SVG
        icon_size = 20 if is_main else 16
        icon_color = COLORS["text_inv"] if is_active else COLORS["muted"]
        
        # Para abas principais sem ícone ou "Financeiro" e sub-abas
        icon_img = get_icon(tab_name, size=icon_size, color=icon_color)

        lbl_icon = ctk.CTkLabel(
            item_frame,
            text="" if icon_img else "•", # Fallback text
            image=icon_img,
            text_color=icon_color,
            width=36,
        )
        lbl_icon.pack(side="left", padx=(6, 0))
        
        # Texto principal
        lbl_text = ctk.CTkLabel(
            item_frame,
            text=tab_name,
            font=fnt,
            text_color=COLORS["text_inv"] if is_active else COLORS["text"],
            anchor="w",
        )
        lbl_text.pack(side="left", fill="x", expand=True, padx=(4, 8))
        
        # Seta indicadora para menus em cascata
        lbl_arrow = None
        if is_main and tab_name in SUB_TABS:
            lbl_arrow = ctk.CTkLabel(
                item_frame,
                text="▼" if self._cascade_open[tab_name] else "▶",
                font=(FONTS["body"][0], 10),
                text_color=COLORS["muted"],
                width=20
            )
            lbl_arrow.pack(side="right", padx=8)

        # Bind de eventos
        widgets = (item_frame, lbl_icon, lbl_text)
        if lbl_arrow: widgets += (lbl_arrow,)
        
        for widget in widgets:
            widget.bind("<Button-1>", lambda e, t=tab_name, arrow=lbl_arrow: self._on_click(t, arrow))
            widget.bind("<Enter>",    lambda e, f=item_frame, t=tab_name: self._on_hover_enter(f, t))
            widget.bind("<Leave>",    lambda e, f=item_frame, t=tab_name: self._on_hover_leave(f, t))

        self._btn_refs[tab_name] = (item_frame, lbl_icon, lbl_text, not is_main)

    # ──────────────────────────────────────────────────────────────────────────
    # NAVEGAÇÃO
    # ──────────────────────────────────────────────────────────────────────────

    def _on_click(self, tab_name: str, arrow_lbl=None):
        if tab_name in SUB_TABS:
            # Toggle cascade
            if not self._expanded:
                self._toggle_collapse() # Expande sidebar primeiro se estiver colapsada
                
            is_open = self._cascade_open[tab_name]
            self._cascade_open[tab_name] = not is_open
            if arrow_lbl:
                arrow_lbl.configure(text="▶" if is_open else "▼")
                
            frame = self._cascade_frames[tab_name]
            if is_open:
                frame.pack_forget()
            else:
                # Localizar posição do tab_name na ordem principal e fazer pack abaixo dele
                frame.pack(fill="x", after=self._btn_refs[tab_name][0])
            return

        # Navegação normal
        self.set_active(tab_name)
        if self._on_navigate:
            self._on_navigate(tab_name)

    def set_active(self, tab_name: str):
        self._active_tab = tab_name

        for t, (frame, icon_lbl, text_lbl, is_sub) in self._btn_refs.items():
            active = (t == tab_name)
            
            # Não pinta bg das abas "Cascata Pai" que foram ativadas, foca no sub-item
            bg_color = COLORS["accent"] if active and t not in SUB_TABS else "transparent"
            text_col = COLORS["text_inv"] if active else COLORS["text"]
            icon_col = COLORS["text_inv"] if active else COLORS["muted"]
            
            frame.configure(fg_color=bg_color)
            
            # Recarregar SVG com a cor correta (otimizado)
            icon_size = 16 if is_sub else 20
            new_img = get_icon(t, size=icon_size, color=icon_col)
            if new_img:
                icon_lbl.configure(image=new_img, text="")
            else:
                icon_lbl.configure(text_color=icon_col)
                
            text_lbl.configure(
                text_color=text_col,
                font=FONTS["nav"] if active else (FONTS["nav_sm"] if is_sub else FONTS["nav"]),
            )

    # ──────────────────────────────────────────────────────────────────────────
    # HOVER
    # ──────────────────────────────────────────────────────────────────────────

    def _on_hover_enter(self, frame, tab_name: str):
        if tab_name != self._active_tab and tab_name not in SUB_TABS:
            frame.configure(fg_color=COLORS["border"])

    def _on_hover_leave(self, frame, tab_name: str):
        if tab_name != self._active_tab or tab_name in SUB_TABS:
            frame.configure(fg_color="transparent")

    # ──────────────────────────────────────────────────────────────────────────
    # COLAPSO / EXPANSÃO ANIMADO
    # ──────────────────────────────────────────────────────────────────────────

    def _toggle_collapse(self):
        self._expanded = not self._expanded
        target = SIDEBAR_W_EXPANDED if self._expanded else SIDEBAR_W_COLLAPSED
        self._toggle_btn.configure(text="☰" if self._expanded else "▶")
        self.configure(width=target)
        self._update_labels_visibility()

    def _update_labels_visibility(self):
        if self._expanded:
            self._brand_lbl.pack(side="left", anchor="w")
            self._version_lbl.pack(side="left", padx=16, expand=True, anchor="w")
            for _, (_, _, text_lbl, _) in self._btn_refs.items():
                text_lbl.pack(side="left", fill="x", expand=True, padx=(4, 8))
                
            # Restaura cascatas abertas
            for t, frame in self._cascade_frames.items():
                if self._cascade_open[t]:
                    frame.pack(fill="x", after=self._btn_refs[t][0])
        else:
            self._brand_lbl.pack_forget()
            self._version_lbl.pack_forget()
            for _, (_, _, text_lbl, _) in self._btn_refs.items():
                text_lbl.pack_forget()
                
            # Fecha visualmente todas as cascatas se estiver colapsado
            for frame in self._cascade_frames.values():
                frame.pack_forget()
