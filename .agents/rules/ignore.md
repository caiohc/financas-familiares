# Regras de Exclusão de Contexto - Projeto Finanças

Para otimizar o consumo de tokens e garantir que o Agente foque apenas no código-fonte e na lógica de negócio, ignore os seguintes diretórios e arquivos:

## 1. Banco de Dados (SQLite)
- **IMPORTANTE:** Ignore todos os arquivos de banco de dados SQLite: `*.db`, `*.sqlite`, `*.sqlite3`.
- Ignore arquivos temporários de journaling do SQLite: `*.db-journal`, `*.db-shm`, `*.db-wal`.

## 2. Dependências e Ambiente Python
- Ignore a pasta `.venv/` (diretório de pacotes instalados pelo uv).
- Ignore arquivos de lock de pacotes que não sejam `uv.lock`.

## 3. Dados e Ingestão
- Ignore arquivos de extratos e planilhas: `*.csv`, `*.xls`, `*.xlsx`, `*.ofx`.
- Ignore arquivos JSON que contenham dados de exportação ou backups de transações.

## 4. Cache e Temporários
- Ignore as pastas de cache do Python: `**/__pycache__/`.
- Ignore arquivos compilados: `*.pyc`, `*.pyo`, `*.pyd`.
- Ignore a pasta de cache de testes: `.pytest_cache/`.

## 5. Controle de Versão e IDEs
- Ignore a pasta interna do Git: `.git/`.
- Ignore configurações de ambiente local: `.env` (para evitar vazamento de chaves de API no contexto).

## Instrução para o Agente:
Se precisar entender o esquema do banco de dados, procure por arquivos de definição de modelos (como `models.py`) ou scripts de migração/inicialização SQL, mas **nunca** tente abrir os arquivos binários `.db`.