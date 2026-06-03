import os
import re
import sys
import shutil
import time
import threading
import sqlite3
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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
from gui.design_system import COLORS, FONTS, SPACING, RADIUS, apply_treeview_style
from gui.sidebar import Sidebar
from gui.components import StatCard, ActionButton, SectionHeader

from gui.tabs.aba_robo import AbaRobo
from gui.tabs.aba_busca import AbaBusca
from gui.tabs.aba_extrato import AbaExtrato
from gui.tabs.aba_contas_pagar import AbaContasPagar
from gui.tabs.aba_recebiveis import AbaRecebiveis
from gui.tabs.aba_autorizacao import AbaAutorizacao
from gui.tabs.aba_restituicoes import AbaRestituicoes
from gui.tabs.aba_manual import AbaManual
from gui.mixins.utils_mixin import AppUtilsMixin
from gui.tabs.aba_analytics import AbaAnalytics


class ComSystemApp(ctk.CTk, AppUtilsMixin):
    def __init__(self):
        super().__init__()

        # ── Compatibilidade com mixins antigos ────────────────────────────────
        self.root = self

        # Mantém colors dict legado para mixins que ainda o referenciam
        self.colors = {
            "bg":          COLORS["bg"],
            "surface":     COLORS["surface"],
            "card":        COLORS["card"],
            "border":      COLORS["border"],
            "accent":      COLORS["accent"],
            "accent_glow": COLORS["accent_glow"],
            "text":        COLORS["text"],
            "muted":       COLORS["muted"],
            "error":       COLORS["error"],
            "warning":     COLORS["warning"],
        }

        # ── Janela principal ──────────────────────────────────────────────────
        self.title("Com System Dashboard")
        self.geometry("1200x720")
        self.minsize(1000, 600)
        self.configure(fg_color=COLORS["bg"])
        self.state("zoomed")

        # ── Estado global ─────────────────────────────────────────────────────
        self.rodando = False
        self._log_historico = []
        self._resultados_busca = []

        # ── Construção da UI ──────────────────────────────────────────────────
        self._build_ui()

        # Garante pastas de operação em background após o render inicial
        self.after(1000, config.ensure_directories)
        
        # Inicia a fila de logs (lê da thread global do logger e renderiza na GUI)
        self.after(100, self._process_log_queue)

    # ══════════════════════════════════════════════════════════════════════════
    # ── BUILD UI PRINCIPAL ────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # Estilo TTK global
        style = ttk.Style()
        apply_treeview_style(style)

        # ── Header ────────────────────────────────────────────────────────────
        self._build_header()

        # ── Separador header/conteúdo ─────────────────────────────────────────
        ctk.CTkFrame(self, fg_color=COLORS["border"], height=1).pack(fill="x")

        # ── Corpo principal (sidebar + conteúdo) ──────────────────────────────
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True)
        self._body.grid_rowconfigure(0, weight=1)
        # Removido grid_columnconfigure(1, weight=1) que esticava o separador

        # ── Configuração das abas ─────────────────────────────────────────────
        from gui.tabs.aba_cockpit import AbaCockpit
        self.tab_configs = {
            "Cockpit":        AbaCockpit,
            "Organizador":    AbaRobo,
            "Buscar":         AbaBusca,
            "Fluxo":          AbaExtrato,
            
            "Contas a Pagar": AbaContasPagar,
            "Lançamento Manual": AbaManual,
            "Adiantamentos":  self._build_solo_adiantamentos,
            "Fornecedores":   self._build_solo_fornecedores,
            "Autorização":    AbaAutorizacao,
            "Restituições":   AbaRestituicoes,
            
            "Analytics":      AbaAnalytics,
        }
        self.tabs_built   = set()
        self._tab_frames  = {}   # tab_name → CTkFrame (container)
        self._tab_instances = {} # tab_name -> class instance
        self._active_tab  = None

        # Args legados passados para os mixins antigos
        self.aba_args = (
            COLORS["bg"], COLORS["surface"], COLORS["border"],
            COLORS["accent"], COLORS["accent"], COLORS["warning"],
            COLORS["text"], COLORS["muted"],
        )

        # ── Sidebar ───────────────────────────────────────────────────────────
        self._sidebar = Sidebar(
            self._body,
            tabs=[], # Now hardcoded inside sidebar.py
            on_navigate=self._navigate_to
        )
        self._sidebar.grid(row=0, column=0, sticky="ns")

        # Separador sidebar/conteúdo
        ctk.CTkFrame(self._body, fg_color=COLORS["border"],
                     width=1).grid(row=0, column=1, sticky="ns")

        # ── Área de conteúdo ──────────────────────────────────────────────────
        self._content_area = ctk.CTkFrame(self._body, fg_color=COLORS["bg"],
                                           corner_radius=0)
        self._content_area.grid(row=0, column=2, sticky="nsew")
        self._body.grid_columnconfigure(2, weight=1)

        # Cria os frames container para cada aba (vazios por ora)
        for name in self.tab_configs:
            frame = ctk.CTkFrame(self._content_area, fg_color=COLORS["bg"],
                                  corner_radius=0)
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            frame.lower()  # Esconde todos inicialmente
            self._tab_frames[name] = frame

        # Navega para o Organizador imediatamente
        self._navigate_to("Organizador", animate=False)

    # ══════════════════════════════════════════════════════════════════════════
    # ── HEADER ────────────────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _build_header(self):
        self.header = ctk.CTkFrame(self, fg_color=COLORS["surface"],
                                    height=58, corner_radius=0)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        # Esquerda: breadcrumb / título da aba ativa
        left = ctk.CTkFrame(self.header, fg_color="transparent")
        left.pack(side="left", padx=SPACING["xl"], fill="y")

        lbl_system = ctk.CTkLabel(left, text="Com System", font=FONTS["h4"],
                                   text_color=COLORS["muted"])
        lbl_system.pack(side="left", anchor="center")

        ctk.CTkLabel(left, text="  /  ", font=FONTS["body"],
                     text_color=COLORS["border_light"]).pack(side="left", anchor="center")

        self._breadcrumb_lbl = ctk.CTkLabel(left, text="Dashboard",
                                             font=FONTS["h4"],
                                             text_color=COLORS["accent"])
        self._breadcrumb_lbl.pack(side="left", anchor="center")

        # Direita: status + relógio
        right = ctk.CTkFrame(self.header, fg_color="transparent")
        right.pack(side="right", padx=SPACING["xl"], fill="y")

        # Status dot animado
        self._status_canvas = tk.Canvas(right, width=10, height=10,
                                         bg=COLORS["surface"], highlightthickness=0)
        self._status_canvas.pack(side="left", padx=(0, 6), anchor="center")
        self._status_dot = self._status_canvas.create_oval(
            1, 1, 9, 9, fill=COLORS["accent"], outline=""
        )

        ctk.CTkLabel(right, text="OPERATIONAL", font=FONTS["label"],
                     text_color=COLORS["accent"]).pack(side="left",
                                                        padx=(0, SPACING["lg"]),
                                                        anchor="center")

        # Separador
        ctk.CTkFrame(right, fg_color=COLORS["border"], width=1,
                     height=24).pack(side="left", padx=SPACING["md"])

        # Relógio
        self._clock_lbl = ctk.CTkLabel(right, text="--:--:--",
                                        font=FONTS["mono"],
                                        text_color=COLORS["muted"])
        self._clock_lbl.pack(side="left", padx=SPACING["md"], anchor="center")

        # Inicia animações do header
        self._update_clock()
        self._pulse_status_dot()

    def _update_clock(self):
        self._clock_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.after(1000, self._update_clock)

    def _pulse_status_dot(self):
        """Animação de pulse no status dot (tamanho oscila)."""
        sizes = [(1, 1, 9, 9), (2, 2, 8, 8), (1, 1, 9, 9)]
        self._pulse_step = getattr(self, "_pulse_step", 0)
        coords = sizes[self._pulse_step % len(sizes)]
        self._status_canvas.coords(self._status_dot, *coords)
        self._pulse_step += 1
        self.after(800, self._pulse_status_dot)

    # ══════════════════════════════════════════════════════════════════════════
    # ── NAVEGAÇÃO ─────────────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _navigate_to(self, tab_name: str, animate: bool = True):
        """Navega para a aba indicada, construindo-a se necessário."""
        if tab_name == self._active_tab:
            return

        # Lazy build
        if tab_name not in self.tabs_built:
            self._build_tab(tab_name)

        # Transição: oculta atual, exibe nova
        if self._active_tab and self._active_tab in self._tab_frames:
            self._tab_frames[self._active_tab].lower()

        self._tab_frames[tab_name].lift()
        self._active_tab = tab_name

        # Atualiza breadcrumb e sidebar
        self._breadcrumb_lbl.configure(text=tab_name)
        self._sidebar.set_active(tab_name)

        # Fade suave (opcional, 150ms)
        if animate:
            self._fade_in(self._tab_frames[tab_name])

    def _fade_in(self, frame, step: int = 0):
        """Efeito de fade-in via atributo de alpha — compatível com CTk."""
        # CustomTkinter não suporta alpha por frame, mas podemos simular
        # com uma sequência de updates visuais rápida
        pass

    def _build_solo_adiantamentos(self, parent, *args):
        tab = AbaContasPagar(self)
        tab._cap_build_adiantamentos(
            parent,
            self.aba_args[0],  # bg
            self.aba_args[1],  # surface
            self.aba_args[3],  # accent
            self.aba_args[4],  # green (accent)
            self.aba_args[5],  # yellow (warning)
            self.aba_args[6],  # text
            self.aba_args[7]   # muted
        )

    def _build_solo_fornecedores(self, parent, *args):
        tab = AbaContasPagar(self)
        tab._cap_build_fornecedores(
            parent,
            self.aba_args[0],  # bg
            self.aba_args[1],  # surface
            self.aba_args[3],  # accent
            self.aba_args[4],  # green (accent)
            self.aba_args[5],  # yellow (warning)
            self.aba_args[6],  # text
            self.aba_args[7]   # muted
        )

    def _build_tab(self, tab_name: str):
        """Constrói o conteúdo de uma aba no seu frame container."""
        if tab_name in self.tabs_built:
            return

        frame = self._tab_frames[tab_name]
        handler = self.tab_configs[tab_name]

        # Indicador de carregamento
        spinner_lbl = ctk.CTkLabel(frame, text=f"⟳  Carregando {tab_name}...",
                                    font=FONTS["h3"], text_color=COLORS["muted"])
        spinner_lbl.place(relx=0.5, rely=0.5, anchor="center")
        self.update_idletasks()
        spinner_lbl.destroy()

        if isinstance(handler, type):
            # It's a class
            tab_instance = handler(self)
            self._tab_instances[tab_name] = tab_instance
            tab_instance.build(frame, *self.aba_args)
        else:
            # It's a method
            handler(frame, *self.aba_args)

        self.tabs_built.add(tab_name)


if __name__ == "__main__":
    app = ComSystemApp()
    app.mainloop()
