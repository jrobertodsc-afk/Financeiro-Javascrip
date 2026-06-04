import sqlite3
import os
import sys

# Ajustar sys.path se precisar
sys.path.append('d:/ROBO')

import config

def remove_duplicatas_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Identificar duplicatas baseadas nos mesmos dados (empresa, fornecedor, valor_bruto, dt_vencimento, descricao)
    # E manter apenas o id minimo
    
    # Executamos o delete
    query = """
    DELETE FROM notas
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM notas
        GROUP BY empresa, filial, fornecedor, dt_vencimento, dt_emissao, valor_bruto, descricao, categoria
    )
    """
    c.execute(query)
    removidas = c.rowcount
    conn.commit()
    conn.close()
    print(f"[{db_path}] Removidas {removidas} notas duplicadas localmente.")

def remove_duplicatas_supabase():
    try:
        from supabase import create_client
        if not config.USE_SUPABASE:
            return
            
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        
        # Puxa todas as notas
        res = supabase.table("notas").select("*").execute()
        notas = res.data
        
        vistos = {}
        ids_para_remover = []
        
        for n in notas:
            key = (n.get('empresa'), n.get('filial'), n.get('fornecedor'), n.get('dt_vencimento'), n.get('valor_bruto'), n.get('descricao'), n.get('categoria'))
            if key in vistos:
                ids_para_remover.append(n['id'])
            else:
                vistos[key] = n['id']
                
        if ids_para_remover:
            print(f"[Supabase] Removendo {len(ids_para_remover)} duplicatas no Supabase...")
            # Supabase delete com in_ é limitado, vamos fazer em batches ou um por um
            for i in range(0, len(ids_para_remover), 50):
                batch = ids_para_remover[i:i+50]
                supabase.table("notas").delete().in_("id", batch).execute()
            print("[Supabase] Removidas com sucesso.")
        else:
            print("[Supabase] Nenhuma duplicata encontrada.")
            
    except Exception as e:
        print(f"[Supabase] Erro ou offline: {e}")

if __name__ == "__main__":
    print("Iniciando limpeza de duplicatas...")
    remove_duplicatas_supabase()
    remove_duplicatas_sqlite(config.DB_PATH)
    print("Limpeza finalizada.")
