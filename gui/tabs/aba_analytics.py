from gui.tabs.base import BaseTab
import tkinter as tk
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from datetime import datetime, timedelta
import os

class AbaAnalytics(BaseTab):
    
    def build(self, parent, bg, surface, border, accent, green, yellow, text, muted):
        # ── TÍTULO ──
        topo = ctk.CTkFrame(parent, fg_color="transparent")
        topo.pack(fill="x", padx=25, pady=(20, 5))
        
        titulo_frame = ctk.CTkFrame(topo, fg_color="transparent")
        titulo_frame.pack(side="left")
        ctk.CTkLabel(titulo_frame, text="📈 DATA VIZ & ANALYTICS", font=("Segoe UI", 16, "bold"), text_color=accent).pack(anchor="w")
        ctk.CTkLabel(titulo_frame, text="Módulo de dashboards de Controle Financeiro e Orçamento.", font=("Segoe UI", 11), text_color=muted).pack(anchor="w", pady=(0, 5))
        
        btn_frame = ctk.CTkFrame(topo, fg_color="transparent")
        btn_frame.pack(side="right", anchor="e")
        
        ctk.CTkButton(btn_frame, text="📥 Importar Receitas (CSV)", command=self._importar_csv_receitas,
                      font=("Segoe UI", 11, "bold"), fg_color="#10b981", text_color="#000000", hover_color="#059669",
                      width=180, height=30).pack(side="right", padx=5)
                      
        ctk.CTkButton(btn_frame, text="⚙️ Configurar Orçamento", command=self._configurar_orcamento,
                      font=("Segoe UI", 11, "bold"), fg_color="#3b82f6", text_color="#ffffff", hover_color="#2563eb",
                      width=180, height=30).pack(side="right", padx=5)
        
        # ── CONTAINER DE GRÁFICOS ──
        self.graphs_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.graphs_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.bg = bg
        self.surface = surface
        self.border = border
        self.accent = accent
        self.green = green
        self.yellow = yellow
        self.text = text
        self.muted = muted
        
        self._carregar_dashboards()
        
    def _carregar_dashboards(self):
        for w in self.graphs_container.winfo_children():
            w.destroy()
            
        self.graphs_container.grid_columnconfigure(0, weight=6)
        self.graphs_container.grid_columnconfigure(1, weight=4)
        self.graphs_container.grid_rowconfigure(0, weight=1)
        self.graphs_container.grid_rowconfigure(1, weight=1)
        
        # Frame Gráfico 1 (Linha - Fluxo de Caixa)
        frame_linha = ctk.CTkFrame(self.graphs_container, fg_color=self.surface, corner_radius=12, border_width=1, border_color=self.border)
        frame_linha.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ctk.CTkLabel(frame_linha, text="FLUXO DE CAIXA PREDITIVO: PRÓXIMOS 15 DIAS", font=("Segoe UI", 11, "bold"), text_color=self.text).pack(anchor="w", padx=15, pady=10)
        self._render_line_chart(frame_linha)
        
        # Frame Gráfico 2 (Pizza - Despesas)
        frame_pizza = ctk.CTkFrame(self.graphs_container, fg_color=self.surface, corner_radius=12, border_width=1, border_color=self.border)
        frame_pizza.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        ctk.CTkLabel(frame_pizza, text="DESPESAS POR CATEGORIA (MÊS)", font=("Segoe UI", 11, "bold"), text_color=self.text).pack(anchor="w", padx=15, pady=10)
        self._render_pie_chart(frame_pizza)
        
        # Frame Termômetro de Orçamento
        frame_orcamento = ctk.CTkFrame(self.graphs_container, fg_color=self.surface, corner_radius=12, border_width=1, border_color=self.border)
        frame_orcamento.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        ctk.CTkLabel(frame_orcamento, text="🌡️ TERMÔMETRO DE ORÇAMENTO (BUDGET vs GASTO)", font=("Segoe UI", 11, "bold"), text_color=self.text).pack(anchor="w", padx=15, pady=10)
        self._render_termometro(frame_orcamento)
        
    def _render_line_chart(self, parent):
        fig, ax = plt.subplots(figsize=(6, 3), facecolor=self.bg)
        ax.set_facecolor(self.bg)
        
        try:
            from services.database import db_conn
            with db_conn() as conn:
                rec_rows = conn.execute("SELECT data, sum(valor) as t FROM receitas GROUP BY data").fetchall()
                desp_rows = conn.execute("SELECT dt_vencimento, sum(valor_bruto) as t FROM notas WHERE status != 'PAGA' AND status != 'CANCELADA' GROUP BY dt_vencimento").fetchall()
            
            hoje = datetime.now()
            dias_str = [(hoje + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(15)]
            
            rec_map = {r[0]: r[1] for r in rec_rows}
            desp_map = {r[0]: r[1] for r in desp_rows}
            
            saldo = 50000 
            valores = []
            
            for d in dias_str:
                saldo += rec_map.get(d, 0)
                saldo -= desp_map.get(d, 0)
                valores.append(saldo)
                
            dias = np.arange(1, 16)
        except Exception:
            dias = np.arange(1, 16)
            valores = 50000 + np.random.randn(15).cumsum() * 1000
            
        ax.plot(dias, valores, color=self.green, linewidth=2, marker="o")
        ax.fill_between(dias, valores, alpha=0.2, color=self.green)
        
        ax.tick_params(colors=self.text, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#141414")
            
        ax.grid(True, linestyle="--", alpha=0.3, color="#141414")
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _render_pie_chart(self, parent):
        fig, ax = plt.subplots(figsize=(4, 3), facecolor=self.bg)
        
        try:
            from services.database import db_conn
            with db_conn() as conn:
                rows = conn.execute("SELECT categoria, sum(valor_bruto) FROM notas WHERE categoria != '' GROUP BY categoria ORDER BY sum(valor_bruto) DESC LIMIT 5").fetchall()
                if rows:
                    labels = [r[0][:15] for r in rows]
                    sizes = [r[1] for r in rows]
                else:
                    labels = ['Nenhuma', 'Despesa']
                    sizes = [50, 50]
        except:
            labels = ['Compras', 'RH', 'Impostos', 'Mkt']
            sizes = [40, 30, 20, 10]
            
        colors = [self.accent, self.yellow, self.green, "#f59e0b", "#3b82f6"]
        
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct='%1.1f%%', startangle=90,
            colors=colors, textprops=dict(color=self.text, fontsize=8)
        )
        
        centre_circle = plt.Circle((0,0), 0.70, fc=self.bg)
        fig.gca().add_artist(centre_circle)
        
        ax.axis('equal')  
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
    def _render_termometro(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=5)
        
        try:
            from services.database import db_conn
            with db_conn() as conn:
                orcamentos = conn.execute("SELECT categoria, limite FROM orcamentos").fetchall()
                if not orcamentos:
                    ctk.CTkLabel(scroll, text="Nenhum orçamento configurado ainda. Clique em 'Configurar Orçamento' acima.", text_color=self.muted).pack(pady=20)
                    return
                
                gastos = conn.execute("SELECT categoria, sum(valor_bruto) FROM notas WHERE status != 'CANCELADA' GROUP BY categoria").fetchall()
                gasto_map = {r[0]: r[1] for r in gastos}
                
                for cat, limite in orcamentos:
                    gasto = gasto_map.get(cat, 0)
                    pct = (gasto / limite) if limite > 0 else 0
                    
                    row = ctk.CTkFrame(scroll, fg_color="transparent")
                    row.pack(fill="x", pady=4)
                    
                    lbl_cat = ctk.CTkLabel(row, text=cat, width=150, anchor="w", font=("Segoe UI", 11, "bold"), text_color=self.text)
                    lbl_cat.pack(side="left")
                    
                    bar_bg = ctk.CTkFrame(row, fg_color="#1e293b", height=12, corner_radius=6)
                    bar_bg.pack(side="left", fill="x", expand=True, padx=10)
                    bar_bg.pack_propagate(False)
                    
                    cor_bar = self.green if pct < 0.7 else (self.yellow if pct < 0.9 else "#ef4444")
                    pct_width = min(pct, 1.0)
                    
                    if pct_width > 0:
                        bar_fg = ctk.CTkFrame(bar_bg, fg_color=cor_bar, height=12, corner_radius=6)
                        bar_fg.place(relwidth=pct_width, relheight=1.0)
                    
                    ctk.CTkLabel(row, text=f"R$ {gasto:,.2f} / R$ {limite:,.2f} ({pct*100:.1f}%)", width=180, anchor="e", text_color=cor_bar).pack(side="right")
                    
        except Exception as e:
            ctk.CTkLabel(scroll, text=f"Erro ao carregar orçamentos: {e}").pack()
            
    def _importar_csv_receitas(self):
        from tkinter import filedialog, messagebox
        import csv
        from datetime import datetime
        from services.database import db_conn
        
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All", "*.*")])
        if not path: return
        
        count = 0
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=';')
                with db_conn() as conn:
                    for row in reader:
                        if not row or len(row) < 3 or row[0].lower() == 'data': continue
                        data = row[0]
                        desc = row[1]
                        val_str = row[2].replace("R$", "").replace(".", "").replace(",", ".").strip()
                        try:
                            valor = float(val_str)
                            conn.execute("INSERT INTO receitas (data, descricao, valor) VALUES (?, ?, ?)", (data, desc, valor))
                            count += 1
                        except: pass
                    conn.commit()
            messagebox.showinfo("Sucesso", f"{count} receitas importadas do CSV!")
            self._carregar_dashboards()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao importar: {e}")
            
    def _configurar_orcamento(self):
        import tkinter.simpledialog as sd
        cat = sd.askstring("Orçamento", "Qual categoria deseja configurar?")
        if not cat: return
        
        limite_str = sd.askstring("Orçamento", f"Qual o limite mensal (R$) para '{cat}'?")
        if not limite_str: return
        
        try:
            limite = float(limite_str.replace(".", "").replace(",", "."))
            from services.database import db_conn
            with db_conn() as conn:
                conn.execute("INSERT OR REPLACE INTO orcamentos (categoria, limite) VALUES (?, ?)", (cat, limite))
                conn.commit()
            self._carregar_dashboards()
        except Exception as e:
            tk.messagebox.showerror("Erro", f"Valor inválido: {e}")
