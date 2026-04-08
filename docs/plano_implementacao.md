# Plano de Implementação: Controle Financeiro Familiar

Este documento detalha o plano macro, a arquitetura e as tecnologias que utilizaremos para construir o aplicativo de finanças familiares. Como o projeto possui um viés didático, o plano é **evolutivo**. A ideia é dominar uma camada da "Clean Architecture" antes de saltar para frameworks complexos.

## Arquitetura: Clean Architecture / Ports and Adapters

A aplicação será divida em camadas independentes.
1. **Entidades/Domínio:** Onde reside a lógica pura e o comportamento das estruturas (Família, Membros, Transações, Contas, Cartões).
2. **Casos de Uso:** Orquestração de negócio: cria contas, importa extratos, aloca transações na família correta, categoriza.
3. **Adapters:** Camada onde acoplaremos os tradutores de arquivo (PDF, CSV), o banco de dados via ORM e a interface (API).

## Tecnologias Alocadas

| Componente | Tecnologia | Fase de Inserção |
| :--- | :--- | :--- |
| **Linguagem & Gerenciador** | `Python 3.12+` / `uv` | Fase 1 |
| **Qualidade & Testes** | `pytest`, `Ruff`, `mypy` | Fase 1 |
| **Parsing de Texto/Planilhas**| `csv` (Built-in) e Expressões Regulares | Fase 2 |
| **OCR / Parsing PDF** | `pdfplumber` / IA Híbrida | Fase 2 |
| **Persistência / DDL** | `SQLAlchemy 2.0` / `Alembic` | Fase 3 |
| **Interface de Comunicação** | `FastAPI` (Proteção JWT) | Fase 4 |
| **Infraestrutura / Cloud** | `Docker` e `Docker Compose` | Fase 5 |

---

## Roteiro de Desenvolvimento (Roadmap)

### Fase 1: Setup e o Núcleo do Domínio (Bounded Contexts)
Foco: *Classes, Tipagem, Regras Limpas*. Sem bibliotecas web ou banco real.
- [ ] Inicializar o projeto com `uv`.
- [ ] Segregar o domínio de aplicação usando princípios *Domain-Driven Design* (Subpacotes).
- [ ] Construir Subdomínio `identity`: entidade `User` focada em segurança.
- [ ] Construir Subdomínio `financial`: conterá as regras core como `Family`, `Member` (Identidade Financeira), `BankAccount`, `CreditCard`, `CardInstance`, `Income`, `Transaction` e `Category`.
- [ ] Implementar a regra de multiplicidade: Um Membro pode possuir N Usuários.
- [ ] Modelar a hierarquia de cartões e o vínculo obrigatório de titularidade.

### Fase 2: Importação Múltipla (Motor de Extratos)
Foco: *Strategy Pattern e Parsing de Documentos.*
- [ ] Criar adaptadores de leitura (*Strategy Pattern*) para CSV/TSV e extratos PDF textuais (`pdfplumber`).
- [ ] Adicionar suporte a processamento OCR/IA quando o PDF for digitalizado/imagem (`OcrAiParserStrategy`).
- [ ] Implementar o Caso de Uso "Importar Extrato": traduz formatos opacos na nossa entidade `Transacao`.
- [ ] Implementar motor simples de categorização automática baseado em histórico (com possibilidade de expansão por IA futura).

### Fase 3: Adicionando o Banco de Dados Real
Foco: *Persistência Robusta e Versionamento de Banco.*
- [ ] Instalar o `SQLAlchemy` e `Alembic`.
- [ ] Mapear as Entidades em Tabelas, prevendo a estrutura multi-tenant separada por ID de Família.
- [ ] Escrever as migrações (Criação do Banco de Dados no SQLite).
- [ ] Substituir o repositório temporário da Fase 1 por implementações baseadas no SQLAlchemy, garantindo o total isolamento da *Clean Architecture*.

### Fase 4: Interface do Usuário e Segurança
Foco: *Autenticação, Proteção e API REST.*
- [ ] Instalar o `FastAPI`.
- [ ] Desenvolver um modelo abstrato de Segurança (Token JWT e Argon2/Bcrypt para Senhas).
- [ ] Expor os Casos de Uso através de Endpoints de rede.
- [ ] Garantir o isolamento de acessos (usuário só pode visualizar dados da sua `Familia`).

### Fase 5: Dockerização
Foco: *Empacotamento e Entrega.*
- [ ] Congelar as dependências seguras com o gerenciador `uv`.
- [ ] Escrever Multi-stage `Dockerfile` focado em otimização.
- [ ] Acoplar banco PostgreeSQL no ambiente via `docker-compose`.
