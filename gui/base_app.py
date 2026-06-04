"""
gui/base_app.py — Classe base do ComSystem.
Extraída de app_main.py para desacoplar configuração da janela da lógica de abas.
"""
import customtkinter as ctk
import tkinter as tk
from services.database import get_db
from loguru import logger
from gui.design_system import COLORS

class BaseApp(ctk.CTk):
    """
    Responsabilidades ÚNICAS desta classe:
    - Configurar a janela (título, tamanho, ícone, tema)
    - Expor self.db (conexão ao banco)
    - Expor self.current_empresa e self.current_filial
    - Prover show_notification(msg, tipo) para feedback visual
    """

    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_db()
        self.current_empresa = ""
        self.current_filial  = ""

    def _setup_window(self):
        self.title("Com System Dashboard")
        self.geometry("1200x720")
        self.minsize(1000, 600)
        self.configure(fg_color=COLORS["bg"])
        self.state("zoomed")

    def _setup_db(self):
        try:
            self.db = get_db()
            logger.info("Banco de dados conectado em BaseApp")
        except Exception as e:
            logger.error(f"Falha ao conectar banco: {e}")
            self.db = None

    def show_notification(self, msg: str, tipo: str = "info"):
        """
        Exibe feedback visual na interface.
        tipo: "info" | "success" | "error" | "warning"
        """
        cores = {
            "info":    "#378ADD",
            "success": "#639922",
            "error":   "#E24B4A",
            "warning": "#BA7517",
        }
        logger.info(f"[{tipo.upper()}] {msg}")
        
        toast = ctk.CTkFrame(self, fg_color=cores.get(tipo, cores["info"]), corner_radius=8)
        lbl = ctk.CTkLabel(toast, text=msg, text_color="white", font=("Arial", 14, "bold"))
        lbl.pack(padx=20, pady=10)
        toast.place(relx=0.5, rely=0.05, anchor="center")
        
        # Destruir após 3 segundos
        self.after(3000, toast.destroy)
