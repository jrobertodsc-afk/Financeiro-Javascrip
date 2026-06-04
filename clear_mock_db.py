import sqlite3
conn = sqlite3.connect('d:/ROBO/robo_boah.db')
conn.execute("DELETE FROM notas WHERE status NOT IN ('PAGO', 'PAGA', 'CANCELADO', 'CANCELADA')")
conn.commit()
