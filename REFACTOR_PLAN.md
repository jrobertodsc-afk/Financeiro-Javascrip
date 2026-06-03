# Plano de Refatoração do Com System

## Objetivo
Criar um plano claro e prático para refatorar o sistema atual, mantendo a interface existente e melhorando a organização, manutenibilidade e portabilidade.

## Principais pontos de refatoração

### 1. Separação de responsabilidades
- Manter `gui/` apenas para a interface e widgets.
- Extrair toda lógica de negócio e processamento para módulos separados (`services/`, `controllers/` ou `core/`).
- Evitar que `gui/app_main.py` importe e execute diretamente muitas funções de `utils`.

### 2. Redução de acoplamento em imports
- Substituir `from ... import *` por imports específicos.
- Evitar importações globais de configuração e utilidades no módulo principal da GUI.
- Usar nomes de módulo explícitos para clareza de origem.

### 3. Configuração e dados externos
- Remover caminhos hardcoded de `config.py`.
- Tornar diretórios configuráveis por:
  - arquivo `.env`
  - configuração JSON/YAML
  - interface de setup inicial
- Externalizar dados estáticos (colaboradores, fornecedores, categorias) para arquivos de dados:
  - `data/colaboradores.json`
  - `data/fornecedores.json`
  - `data/fornecedores_categoria.json`

### 4. Dependências e reprodutibilidade
- Criar `requirements.txt` ou `pyproject.toml` com as dependências reais:
  - `customtkinter`
  - `PyMuPDF` (`fitz`)
  - `Pillow`
  - `openpyxl`
  - `xlrd`
  - possivelmente `python-dotenv`
- Garantir ambiente previsível para desenvolvimento e deploy.

### 5. Logging e tratamento de erro
- Introduzir `logging` centralizado em vez de `print` esporádico.
- Capturar exceções críticas em operações de arquivo, PDF/XLSX e rede.
- Exibir mensagens amigáveis para o usuário na GUI.

### 6. Revisão da arquitetura de abas
- A classe `ComSystemApp` herda muitos mixins e acopla o estado global.
- Considerar a criação de componentes de aba independentes:
  - `gui/tabs/organizador.py`
  - `gui/tabs/busca.py`
  - `gui/tabs/contas_a_pagar.py`
  - etc.
- Reduzir herança múltipla usando composição e injeção de dependências.

### 7. Limpeza de código legado
- Remover ou revisar pontos como:
  - `self.root = self`
  - `self.colors` legado
  - métodos não implementados (`_fade_in`)
  - argumentos não utilizados e comentários obsoletos

## Sequência de arquivos para iniciar

### Fase 1: Preparação e ambiente
1. `requirements.txt` ou `pyproject.toml`
2. `config.py`
3. `main.py`

### Fase 2: Modularização de configuração e dados
4. `config.py` (transformar em configurável)
5. `data/` para arquivos estáticos
6. `database.py` (separar config do caminho DB)

### Fase 3: Refatoração inicial da GUI
7. `gui/app_main.py`
8. `gui/sidebar.py`
9. `gui/design_system.py`
10. `gui/components.py`

### Fase 4: Desacoplamento de mixins e lógica de abas
11. `gui/mixins/aba_robo.py`
12. `gui/mixins/aba_busca.py`
13. `gui/mixins/aba_extrato.py`
14. Demais mixins em `gui/mixins/*.py`

### Fase 5: Serviços e utilitários
15. `utils/file_manager.py`
16. `utils/ocr_utils.py`
17. `utils/email_service.py`
18. `utils/integrations_utils.py`
19. `utils/extratos_processor.py`
20. `utils/dashboard_service.py`
21. `utils/formatters.py`
22. `cnab_generator.py`

## Recomendações rápidas
- Começar pela configuração, pois define a base do projeto.
- Depois, limpar imports e modularizar `app_main.py` para simplificar a GUI.
- Em seguida, separar cada aba em um módulo independente.
- Por fim, mover as utilidades de `utils/` para serviços coerentes com responsabilidades claras.

## Resultado esperado
- Código mais fácil de manter
- Menos dependências implícitas
- Melhor portabilidade para outros computadores
- Maior capacidade de continuidade com modelos avançados ou frameworks externos
- Mais segurança para evolução futura do sistema
