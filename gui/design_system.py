from services.logger_service import logger
"""
design_system.py — Design System centralizado do Com System.

Todos os tokens visuais, paleta de cores, escala tipográfica,
espaçamentos e helpers de componentes estão aqui.
"""

# ==============================================================================
# ── PALETA DE CORES ────────────────────────────────────────────────────────────
# ==============================================================================

COLORS = {
    # Fundos (Deep Space UI)
    "bg":          "#05080F",   # Fundo global (mais escuro e profundo)
    "surface":     "#0A101C",   # Superfícies secundárias
    "card":        "#0F172A",   # Cards e painéis (Slate 900)
    "sidebar":     "#070B14",   # Sidebar (quase preto)

    # Bordas
    "border":      "#1E293B",   # Borda padrão (Slate 800)
    "border_light":"#334155",   # Borda hover / ativa (Slate 700)

    # Accent / Primária
    "accent":      "#CCFF00",   # Lima neon (ação primária, assinatura visual)
    "accent_dim":  "#A3CC00",   # Lima escurecida (hover)
    "accent_glow": "#D9FF33",   # Lima claro (glow / destaque)
    "accent_soft": "#1A2600",   # Fundo sutil com tom lime

    # Semânticas
    "success":     "#10B981",   # Verde Esmeralda
    "warning":     "#F59E0B",   # Âmbar
    "error":       "#EF4444",   # Vermelho vibrante
    "info":        "#3B82F6",   # Azul royal

    # Texto
    "text":        "#F8FAFC",   # Slate 50 (brilhante)
    "muted":       "#94A3B8",   # Slate 400
    "text_inv":    "#020617",   # Slate 950 (para contrastar com neon)
}

# ==============================================================================
# ── TIPOGRAFIA ─────────────────────────────────────────────────────────────────
# ==============================================================================

FONT_FAMILY   = "Inter"    # Fonte principal moderna (se não houver, ctk usa fallback)
FONT_MONO     = "JetBrains Mono" # Fonte mono moderna

FONTS = {
    "h1":       (FONT_FAMILY, 28, "bold"),
    "h2":       (FONT_FAMILY, 20, "bold"),
    "h3":       (FONT_FAMILY, 16, "bold"),
    "h4":       (FONT_FAMILY, 13, "bold"),
    "body":     (FONT_FAMILY, 13),
    "body_sm":  (FONT_FAMILY, 11),
    "caption":  (FONT_FAMILY, 10),
    "label":    (FONT_FAMILY, 10, "bold"),
    "mono":     (FONT_MONO,   11),
    "nav":      (FONT_FAMILY, 12, "bold"),
    "nav_sm":   (FONT_FAMILY, 10),
    "stat":     (FONT_FAMILY, 34, "bold"),
    "badge":    (FONT_FAMILY,  9, "bold"),
}

# ==============================================================================
# ── ESPAÇAMENTOS ───────────────────────────────────────────────────────────────
# ==============================================================================

SPACING = {
    "xs":  4,
    "sm":  8,
    "md": 16,
    "lg": 24,
    "xl": 40,
}

RADIUS = {
    "sm":  6,
    "md": 10,
    "lg": 16,
    "xl": 24,
}

# ==============================================================================
# ── ÍCONES SVG (como strings base64 / data URI para CTkImage) ─────────────────
# Formato: dicionário nome → SVG string (para renderização via PIL/CTkImage)
# ==============================================================================

# Ícones como paths SVG simples (estilo outline/tech)
SVG_ICONS = {
    "dashboard": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="3" width="7" height="7" rx="1.5"/>
        <rect x="14" y="3" width="7" height="7" rx="1.5"/>
        <rect x="3" y="14" width="7" height="7" rx="1.5"/>
        <rect x="14" y="14" width="7" height="7" rx="1.5"/>
    </svg>""",

    "search": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="11" cy="11" r="7"/>
        <line x1="16.5" y1="16.5" x2="22" y2="22"/>
    </svg>""",

    "flow": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>""",

    "logs": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10 9 9 9 8 9"/>
    </svg>""",

    "history": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <polyline points="12 8 12 12 14 14"/>
        <path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5"/>
    </svg>""",

    "cards": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
        <line x1="1" y1="10" x2="23" y2="10"/>
    </svg>""",

    "auth": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        <polyline points="9 12 11 14 15 10"/>
    </svg>""",

    "manual": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
    </svg>""",

    "bills": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <line x1="12" y1="1" x2="12" y2="23"/>
        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
    </svg>""",

    "refund": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <polyline points="1 4 1 10 7 10"/>
        <path d="M3.51 15a9 9 0 1 0 .49-3"/>
    </svg>""",

    "chevron_left": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="15 18 9 12 15 6"/>
    </svg>""",

    "chevron_right": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="9 18 15 12 9 6"/>
    </svg>""",

    "settings": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>""",

    "pie": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21.21 15.89A10 10 0 1 1 8 2.83M22 12A10 10 0 0 0 12 2v10z"/>
    </svg>""",
}

TAB_ICONS = {
    "Organizador":  "dashboard",
    "Dashboard":    "dashboard",
    "Buscar":       "search",
    "Financeiro":   "bills",
    "Fluxo":        "flow",
    "Cartões":      "cards",
    "Autorização":  "auth",
    "Lançamento Manual": "manual",
    "Manual":       "manual",
    "Contas a Pagar": "bills",
    "Restituições": "refund",
    "Analytics":    "pie",
    "Fornecedores": "history",
    "Adiantamentos": "flow"
}

# ==============================================================================
# ── STATUS BADGE COLORS ────────────────────────────────────────────────────────
# ==============================================================================

STATUS_COLORS = {
    "PENDENTE":   ("#f59e0b", "#1a1200"),   # (fg, bg)
    "APROVADA":   ("#3b82f6", "#001020"),
    "PAGA":       ("#22c55e", "#001a08"),
    "VENCIDA":    ("#ef4444", "#1a0000"),
    "CANCELADA":  ("#6b82a8", "#0d1526"),
}

# ==============================================================================
# ── HELPER: render SVG → CTkImage ──────────────────────────────────────────────
# ==============================================================================

def _svg_to_ctk_image(svg_string: str, size: int = 20, color: str = "#CCFF00"):
    """
    Converte uma string SVG para CTkImage (PIL).
    Usa PyMuPDF (fitz) para renderização nativa de SVG.
    Fallback: retorna None.
    """
    try:
        import io
        import fitz
        from PIL import Image
        import customtkinter as ctk

        colored_svg = svg_string.replace('stroke="currentColor"', f'stroke="{color}"')
        
        # O fitz consegue ler SVG da memória
        doc = fitz.open("svg", colored_svg.encode('utf-8'))
        page = doc[0]
        # Multiplicador de escala para ficar nítido
        scale = 300 / 72  # dpi 300
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(alpha=True, matrix=mat)
        
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        
        # Redimensiona mantendo a proporção para o tamanho desejado
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        
        return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
    except Exception as e:
        logger.error(f"Erro SVG: {e}")
        return None


def get_icon(name: str, size: int = 18, color: str = None) -> object:
    """Retorna um CTkImage para o ícone ou None se não disponível."""
    if color is None:
        color = COLORS["muted"]
    svg_name = TAB_ICONS.get(name, name)
    svg = SVG_ICONS.get(svg_name)
    if not svg:
        return None
    return _svg_to_ctk_image(svg, size, color)


# ==============================================================================
# ── TTK STYLE SETUP ────────────────────────────────────────────────────────────
# ==============================================================================

def apply_treeview_style(style):
    """Aplica o estilo do Design System ao ttk.Treeview."""
    style.theme_use("default")

    style.configure("DS.Treeview",
        background=COLORS["card"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["card"],
        rowheight=36,
        borderwidth=0,
        font=FONTS["body_sm"],
        selectmode="browse",
    )
    style.configure("DS.Treeview.Heading",
        background=COLORS["surface"],
        foreground=COLORS["accent"],
        relief="flat",
        font=FONTS["label"],
        padding=(8, 6),
    )
    style.map("DS.Treeview",
        background=[("selected", COLORS["border_light"])],
        foreground=[("selected", COLORS["accent"])],
    )

    # Scrollbar slim
    style.configure("DS.Vertical.TScrollbar",
        background=COLORS["surface"],
        troughcolor=COLORS["bg"],
        borderwidth=0,
        arrowsize=12,
    )

# ==============================================================================
# ── MICROINTERAÇÕES E ANIMAÇÕES ────────────────────────────────────────────────
# ==============================================================================

def apply_hover_animation(widget, color_base: str, color_hover: str, steps: int = 8, interval_ms: int = 15):
    """
    Aplica uma transição de cor suave de color_base para color_hover (Microinteração).
    Ideal para frames, cards e botões.
    """
    # Helper hex to RGB
    def h2rgb(h): return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    def rgb2h(rgb): return '#{:02x}{:02x}{:02x}'.format(*[int(c) for c in rgb])

    try:
        rgb_base = h2rgb(color_base)
        rgb_hover = h2rgb(color_hover)
    except:
        return # Fallback se falhar

    # Diferenças por step
    diffs = [(rgb_hover[i] - rgb_base[i]) / steps for i in range(3)]

    def animate(forward: bool, step: int = 0):
        if step > steps: return
        
        # Calcula cor atual
        if forward:
            cur_rgb = [rgb_base[i] + (diffs[i] * step) for i in range(3)]
        else:
            cur_rgb = [rgb_hover[i] - (diffs[i] * step) for i in range(3)]
            
        cur_hex = rgb2h(cur_rgb)
        
        # Tenta aplicar fg_color (ou text_color dependendo do widget)
        try:
            widget.configure(fg_color=cur_hex)
        except:
            pass
            
        # Agenda próximo step
        widget.after(interval_ms, lambda: animate(forward, step + 1))

    # Vincula os eventos (Enter = forward, Leave = backward)
    widget.bind("<Enter>", lambda e: animate(forward=True, step=1), add="+")
    widget.bind("<Leave>", lambda e: animate(forward=False, step=1), add="+")

# ==============================================================================
# ── UI COMPONENT HELPERS ────────────────────────────────────────────────────────
# ==============================================================================
import customtkinter as ctk
import tkinter as tk

def create_card(parent, **kw):
    """Cria um Card padrão."""
    defaults = {
        "fg_color": COLORS["card"],
        "corner_radius": 8,
        "border_width": 1,
        "border_color": COLORS["border"]
    }
    defaults.update(kw)
    return ctk.CTkFrame(parent, **defaults)

def create_label(parent, text, type="body", **kw):
    """Cria um Label padrão do Design System."""
    font = FONTS.get(type, FONTS["body"])
    color = COLORS.get("text", "#f8fafc")
    if type == "muted":
        color = COLORS["muted"]
    elif type == "h1" or type == "h2" or type == "h3" or type == "h4":
        color = COLORS["text"]
    
    defaults = {
        "text_color": color,
        "font": font
    }
    defaults.update(kw)
    
    # Se for em um frame do tkinter normal, usar tk.Label para evitar problemas com fundos do ctk
    is_pure_tk = isinstance(parent, tk.Frame) and not isinstance(parent, ctk.CTkFrame)
    if is_pure_tk or isinstance(parent, tk.LabelFrame):
        try:
            bg = parent.cget("bg") if parent.cget("bg") else COLORS["bg"]
        except:
            bg = COLORS["bg"]
        return tk.Label(parent, text=text, fg=defaults["text_color"], bg=bg, font=font)
    
    return ctk.CTkLabel(parent, text=text, **defaults)

def create_input(parent, w=200, **kw):
    """Cria um campo de texto estilizado (antigo ent())."""
    defaults = {
        "width": w,
        "height": 32,
        "font": FONTS["body"],
        "fg_color": COLORS["border"],
        "border_color": COLORS["border_light"],
        "border_width": 1,
        "text_color": COLORS["text"]
    }
    defaults.update(kw)
    return ctk.CTkEntry(parent, **defaults)

def create_combo(parent, w=200, **kw):
    """Cria um Dropdown estilizado."""
    defaults = {
        "width": w,
        "height": 32,
        "font": FONTS["body"],
        "fg_color": COLORS["border"],
        "border_color": COLORS["border_light"],
        "button_color": COLORS["border_light"],
        "text_color": COLORS["text"]
    }
    defaults.update(kw)
    return ctk.CTkComboBox(parent, **defaults)

def create_btn(parent, text, style="primary", **kw):
    """Cria um Botão estilizado."""
    colors = {
        "primary": {"fg_color": COLORS["accent"], "hover_color": COLORS["accent_dim"], "text_color": COLORS["text_inv"]},
        "success": {"fg_color": COLORS["success"], "hover_color": "#059669", "text_color": "#ffffff"},
        "secondary": {"fg_color": COLORS["border_light"], "hover_color": "#475569", "text_color": "#ffffff"},
        "danger": {"fg_color": COLORS["error"], "hover_color": "#b91c1c", "text_color": "#ffffff"}
    }
    
    c = colors.get(style, colors["primary"])
    
    defaults = {
        "font": FONTS["label"],
        "fg_color": c["fg_color"],
        "hover_color": c["hover_color"],
        "text_color": c["text_color"],
        "corner_radius": 6
    }
    defaults.update(kw)
    return ctk.CTkButton(parent, text=text, height=32, **defaults)

