import sqlite3

conn = sqlite3.connect('d:/ROBO/robo_boah.db')
conn.row_factory = sqlite3.Row

notas = conn.execute("SELECT dt_vencimento, COUNT(*) as c, SUM(valor_bruto) as v FROM notas WHERE status NOT IN ('PAGO', 'PAGA', 'CANCELADO', 'CANCELADA') GROUP BY dt_vencimento").fetchall()
print([dict(r) for r in notas])
