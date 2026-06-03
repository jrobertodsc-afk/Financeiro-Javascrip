import os
import json
import config

print("Recuperando histórico alimentado...")

caminho_ultimo = os.path.join(config.PASTA_ATUAL, "_ultimo_relatorio_autorizacao.json")

if not os.path.exists(caminho_ultimo):
    print("Nenhum relatório anterior encontrado.")
    exit()

with open(caminho_ultimo, 'r', encoding='utf-8') as f:
    estado = json.load(f)
    
dados = estado.get('dados', [])
count = 0

for item in dados:
    nome = item.get("nome", "").strip().upper()
    cnpj = item.get("cnpj", "").strip()
    cat = item.get("categoria", "")
    resp = item.get("responsavel", "")
    desc = item.get("descricao", "")
    
    if cat and cat != "A CLASSIFICAR":
        if cnpj:
            if cnpj not in config.DB_FORNECEDORES_CATEGORIA:
                config.DB_FORNECEDORES_CATEGORIA[cnpj] = [resp, cat, desc]
                count += 1
            else:
                # Atualiza se a descricao for vazia no banco
                vals = config.DB_FORNECEDORES_CATEGORIA[cnpj]
                if len(vals) < 3 or (not vals[2] and desc):
                    config.DB_FORNECEDORES_CATEGORIA[cnpj] = [resp, cat, desc]
                    count += 1
        elif nome:
            if nome not in config.DB_FORNECEDORES_NOME:
                config.DB_FORNECEDORES_NOME[nome] = [resp, cat, desc]
                count += 1
            else:
                vals = config.DB_FORNECEDORES_NOME[nome]
                if len(vals) < 3 or (not vals[2] and desc):
                    config.DB_FORNECEDORES_NOME[nome] = [resp, cat, desc]
                    count += 1

if count > 0:
    cat_path = os.path.join(config.DATA_DIR, 'fornecedores_categoria.json')
    nome_path = os.path.join(config.DATA_DIR, 'fornecedores_nome.json')
    
    with open(cat_path, 'w', encoding='utf-8') as f:
        json.dump(config.DB_FORNECEDORES_CATEGORIA, f, ensure_ascii=False, indent=4)
        
    with open(nome_path, 'w', encoding='utf-8') as f:
        json.dump(config.DB_FORNECEDORES_NOME, f, ensure_ascii=False, indent=4)
        
    print(f"Sucesso! {count} novas regras (com descrição) foram aprendidas do seu preenchimento anterior!")
else:
    print("O banco já estava atualizado.")
