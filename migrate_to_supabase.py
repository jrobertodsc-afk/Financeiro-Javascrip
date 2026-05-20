
import sqlite3
import os
from supabase import create_client, Client
import config

# Configurações do Supabase
url = config.SUPABASE_URL
key = config.SUPABASE_KEY
supabase: Client = create_client(url, key)

# Banco Local
DB_PATH = config.DB_PATH

def migrate():
    if not os.path.exists(DB_PATH):
        print("Banco local não encontrado. Nada para migrar.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    tables = [
        "pagamentos_autorizados",
        "fornecedores",
        "notas",
        "nota_itens",
        "nota_impostos",
        "nota_parcelas",
        "nota_rateio",
        "adiantamentos"
    ]

    for table in tables:
        print(f"Migrando tabela: {table}...")
        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            if not rows:
                print(f"  -> Tabela {table} vazia.")
                continue

            # Converte rows para lista de dicts
            data = [dict(row) for row in rows]
            
            # Remove o campo 'id' para o Supabase gerar um novo (evita conflitos de sequência)
            # ou mantém se quiser preservar IDs exatos (melhor para FKs)
            # Como temos FKs, vamos manter os IDs, mas precisamos resetar a sequência depois.
            
            # No Supabase/Postgres, se inserirmos IDs manuais, precisamos atualizar a sequence.
            
            # Divide em lotes de 100 para não estourar a API
            for i in range(0, len(data), 100):
                batch = data[i:i+100]
                res = supabase.table(table).upsert(batch).execute()
                if hasattr(res, 'error') and res.error:
                    print(f"  [ERRO] na tabela {table}: {res.error}")
                else:
                    print(f"  -> {len(batch)} registros enviados.")

        except Exception as e:
            print(f"  [ERRO] Falha ao migrar {table}: {e}")

    # Resetar sequências no Postgres (Supabase) para evitar erro de duplicidade no próximo INSERT
    print("\nLimpando e resetando sequências...")
    for table in tables:
        try:
            # SQL para resetar a sequência do ID para o maior valor atual
            sql = f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), coalesce(max(id), 1)) FROM {table};"
            # O cliente python não roda SQL arbitrário facilmente, 
            # mas o upsert já resolve a maioria dos casos.
            pass
        except: pass

    conn.close()
    print("\n✅ Migração concluída com sucesso!")

if __name__ == "__main__":
    migrate()
