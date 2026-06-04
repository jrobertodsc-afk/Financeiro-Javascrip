import sys
import os
from datetime import datetime

sys.path.append('d:/ROBO')
from services.database import listar_notas

notas = listar_notas()
hoje_dt = datetime.strptime(datetime.now().strftime("%d/%m/%Y"), "%d/%m/%Y")
print(f"hoje_dt: {hoje_dt} type: {type(hoje_dt)}")

a = 0
h = 0
for r in notas:
    if r.get("status", "") in ("PAGO", "PAGA", "CANCELADO", "CANCELADA"):
        continue
    try:
        dt_venc = datetime.strptime(r["dt_vencimento"], "%d/%m/%Y")
    except Exception as e:
        continue
    
    if dt_venc < hoje_dt:
        a += 1
    elif dt_venc == hoje_dt:
        h += 1

print(f"Atrasados: {a}, Hoje: {h}")
