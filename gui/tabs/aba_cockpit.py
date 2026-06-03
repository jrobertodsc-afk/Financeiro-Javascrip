from gui.tabs.base import BaseTab
import tkinter as tk
import customtkinter as ctk
from datetime import datetime, timedelta

class AbaCockpit(BaseTab):
    
    def build(self, parent, bg, surface, border, accent, green, yellow, text, muted):
        # ── TÍTULO ──
        topo = ctk.CTkFrame(parent, fg_color="transparent")
        topo.pack(fill="x", padx=30, pady=(30, 10))
        
        ctk.CTkLabel(topo, text="🚀 COCKPIT: O SEU RESUMO DO DIA", font=("Segoe UI", 24, "bold"), text_color=accent).pack(anchor="w")
        ctk.CTkLabel(topo, text="Bem-vindo de volta! Aqui está o panorama da sua rotina de Contas a Pagar.", font=("Segoe UI", 14), text_color=muted).pack(anchor="w", pady=(0, 20))
        
        # ── CARDS DE RESUMO ──
        cards_container = ctk.CTkFrame(parent, fg_color="transparent")
        cards_container.pack(fill="x", padx=25, pady=10)
        
        cards_container.grid_columnconfigure((0, 1, 2), weight=1, uniform="card")
        
        self.bg = bg
        self.surface = surface
        self.border = border
        self.accent = accent
        self.green = green
        self.yellow = yellow
        self.text = text
        self.muted = muted
        
        self._frame_hoje = ctk.CTkFrame(cards_container, fg_color=surface, corner_radius=15, border_width=1, border_color=border)
        self._frame_hoje.grid(row=0, column=0, sticky="nsew", padx=8)
        
        self._frame_atrasado = ctk.CTkFrame(cards_container, fg_color=surface, corner_radius=15, border_width=1, border_color=border)
        self._frame_atrasado.grid(row=0, column=1, sticky="nsew", padx=8)
        
        self._frame_proximos = ctk.CTkFrame(cards_container, fg_color=surface, corner_radius=15, border_width=1, border_color=border)
        self._frame_proximos.grid(row=0, column=2, sticky="nsew", padx=8)
        
        # ── LISTA DE ATENÇÃO IMEDIATA ──
        lista_container = ctk.CTkFrame(parent, fg_color="transparent")
        lista_container.pack(fill="both", expand=True, padx=30, pady=20)
        
        ctk.CTkLabel(lista_container, text="⚠️ CONTAS URGENTES (HOJE + ATRASADAS)", font=("Segoe UI", 12, "bold"), text_color=text).pack(anchor="w", pady=(0, 10))
        
        self.scroll_urgentes = ctk.CTkScrollableFrame(lista_container, fg_color=surface, corner_radius=10, border_width=1, border_color=border)
        self.scroll_urgentes.pack(fill="both", expand=True)
        
        # Carregar Dados
        self._carregar_dados()
        
    def _carregar_dados(self):
        try:
            from services.database import db_conn
            with db_conn() as conn:
                # Contas não pagas (Pendente ou Aprovada) e não canceladas
                rows = conn.execute("SELECT id, dt_vencimento, fornecedor, valor_bruto, status FROM notas WHERE status NOT IN ('PAGA', 'CANCELADA')").fetchall()
                
            hoje = datetime.now()
            hoje_str = hoje.strftime("%d/%m/%Y")
            
            hoje_dt = datetime.strptime(hoje_str, "%d/%m/%Y")
            
            vencem_hoje_qtd = 0
            vencem_hoje_val = 0.0
            
            atrasados_qtd = 0
            atrasados_val = 0.0
            
            proximos_qtd = 0
            proximos_val = 0.0
            
            urgentes = []
            
            for r in rows:
                try:
                    dt_venc = datetime.strptime(r[1], "%d/%m/%Y")
                except:
                    continue
                    
                val = r[3]
                
                if dt_venc < hoje_dt:
                    atrasados_qtd += 1
                    atrasados_val += val
                    urgentes.append(r)
                elif dt_venc == hoje_dt:
                    vencem_hoje_qtd += 1
                    vencem_hoje_val += val
                    urgentes.append(r)
                elif hoje_dt < dt_venc <= (hoje_dt + timedelta(days=3)):
                    proximos_qtd += 1
                    proximos_val += val
                    
            self._renderizar_card(self._frame_hoje, "🚨 VENCEM HOJE", vencem_hoje_qtd, vencem_hoje_val, self.yellow)
            self._renderizar_card(self._frame_atrasado, "⚠️ ATRASADOS", atrasados_qtd, atrasados_val, "#ef4444")
            self._renderizar_card(self._frame_proximos, "📅 PRÓXIMOS 3 DIAS", proximos_qtd, proximos_val, self.accent)
            
            self._renderizar_lista(urgentes)
            
        except Exception as e:
            print(f"Erro ao carregar cockpit: {e}")
            
    def _renderizar_card(self, parent, titulo, qtd, valor, cor):
        for w in parent.winfo_children(): w.destroy()
        
        ctk.CTkLabel(parent, text=titulo, font=("Segoe UI", 14, "bold"), text_color=cor).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(parent, text=f"{qtd} contas", font=("Segoe UI", 12), text_color=self.muted).pack(anchor="w", padx=20)
        ctk.CTkLabel(parent, text=f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 
                     font=("Segoe UI", 28, "bold"), text_color=self.text).pack(anchor="w", padx=20, pady=(10, 20))
                     
    def _renderizar_lista(self, urgentes):
        for w in self.scroll_urgentes.winfo_children(): w.destroy()
        
        if not urgentes:
            ctk.CTkLabel(self.scroll_urgentes, text="🎉 Tudo limpo! Nenhuma conta vencendo hoje ou atrasada.", font=("Segoe UI", 14), text_color=self.green).pack(pady=40)
            return
            
        for r in sorted(urgentes, key=lambda x: datetime.strptime(x[1], "%d/%m/%Y")):
            row = ctk.CTkFrame(self.scroll_urgentes, fg_color="transparent")
            row.pack(fill="x", pady=4, padx=10)
            
            # Status / Data
            data_venc = datetime.strptime(r[1], "%d/%m/%Y")
            hoje_dt = datetime.strptime(datetime.now().strftime("%d/%m/%Y"), "%d/%m/%Y")
            
            if data_venc < hoje_dt:
                badge_cor = "#ef4444"
                badge_text = "ATRASADA"
            else:
                badge_cor = self.yellow
                badge_text = "HOJE"
                
            badge = ctk.CTkFrame(row, fg_color=badge_cor, corner_radius=4, width=80, height=24)
            badge.pack(side="left", padx=(0, 15))
            badge.pack_propagate(False)
            ctk.CTkLabel(badge, text=badge_text, font=("Segoe UI", 10, "bold"), text_color="#1a1a1a").pack(expand=True)
            
            ctk.CTkLabel(row, text=f"Venc: {r[1]}", font=("Segoe UI", 12), text_color=self.muted, width=100, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=r[2][:40], font=("Segoe UI", 12, "bold"), text_color=self.text, width=350, anchor="w").pack(side="left", padx=10)
            
            val_fmt = f"R$ {r[3]:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            ctk.CTkLabel(row, text=val_fmt, font=("Segoe UI", 12, "bold"), text_color=self.accent, anchor="e").pack(side="right")
