import tkinter as tk
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from datetime import datetime

class AbaAnalyticsMixin:
    
    def _build_aba_analytics(self, parent, bg, surface, border, accent, green, yellow, text, muted):
        # ── TÍTULO ──
        ctk.CTkLabel(parent, text="📈 DATA VIZ & ANALYTICS", font=("Segoe UI", 16, "bold"), text_color=accent).pack(anchor="w", padx=25, pady=(20, 5))
        ctk.CTkLabel(parent, text="Módulo de dashboards nativos gerados via Matplotlib (Renderização em Tempo Real).", font=("Segoe UI", 11), text_color=muted).pack(anchor="w", padx=25, pady=(0, 15))
        
        # ── CONTAINER DE GRÁFICOS ──
        graphs_container = ctk.CTkFrame(parent, fg_color="transparent")
        graphs_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        graphs_container.grid_columnconfigure(0, weight=6)
        graphs_container.grid_columnconfigure(1, weight=4)
        graphs_container.grid_rowconfigure(0, weight=1)
        
        # Frame Gráfico 1 (Linha - Fluxo de Caixa)
        frame_linha = ctk.CTkFrame(graphs_container, fg_color=surface, corner_radius=12, border_width=1, border_color=border)
        frame_linha.grid(row=0, column=0, sticky="nsew", padx=5)
        
        ctk.CTkLabel(frame_linha, text="FLUXO DE CAIXA: PROJEÇÃO 30 DIAS", font=("Segoe UI", 11, "bold"), text_color=text).pack(anchor="w", padx=15, pady=10)
        
        self._render_line_chart(frame_linha, bg, text, accent, green)
        
        # Frame Gráfico 2 (Pizza - Despesas)
        frame_pizza = ctk.CTkFrame(graphs_container, fg_color=surface, corner_radius=12, border_width=1, border_color=border)
        frame_pizza.grid(row=0, column=1, sticky="nsew", padx=5)
        
        ctk.CTkLabel(frame_pizza, text="DESPESAS POR DEPARTAMENTO", font=("Segoe UI", 11, "bold"), text_color=text).pack(anchor="w", padx=15, pady=10)
        
        self._render_pie_chart(frame_pizza, bg, text, accent, yellow, green)
        
    def _render_line_chart(self, parent, bg_color, text_color, color_line, color_fill):
        # Estilização do Matplotlib para bater com o "Deep Space UI"
        fig, ax = plt.subplots(figsize=(6, 4), facecolor=bg_color)
        ax.set_facecolor(bg_color)
        
        # Dados mockados
        dias = np.arange(1, 15)
        valores = 10000 + np.random.randn(14).cumsum() * 1000
        
        ax.plot(dias, valores, color=color_line, linewidth=2, marker="o")
        ax.fill_between(dias, valores, alpha=0.2, color=color_fill)
        
        ax.tick_params(colors=text_color, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#333333")
            
        ax.grid(True, linestyle="--", alpha=0.3, color="#555555")
        
        # Evitar sobreposição de UI
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _render_pie_chart(self, parent, bg_color, text_color, c1, c2, c3):
        fig, ax = plt.subplots(figsize=(4, 4), facecolor=bg_color)
        
        labels = ['Compras', 'RH', 'Impostos', 'Mkt']
        sizes = [40, 30, 20, 10]
        colors = [c1, c2, c3, "#6d28d9"]
        
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct='%1.1f%%', startangle=90,
            colors=colors, textprops=dict(color=text_color, fontsize=9)
        )
        
        # Donut hole
        centre_circle = plt.Circle((0,0), 0.70, fc=bg_color)
        fig.gca().add_artist(centre_circle)
        
        ax.axis('equal')  
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))
