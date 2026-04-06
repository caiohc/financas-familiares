# Requisitos Não Funcionais

Requisitos relacionados ao comportamento do sistema, restrições tecnológicas, flexibilidade de uso arquitetural e gestão de infraestrutura.

## 1. Arquitetura e Design
- **Clean Architecture:** A fundação do projeto será desenvolvida com foco total nos princípios da **Clean Architecture** (Arquitetura Limpa / Hexagonal). O motor da aplicação e as regras de negócio estarão intrinsecamente isolados (Domain & Use Cases).
- **Strategy Pattern:** Implementação do padrão Strategy na absorção dos elementos passados para ingestão. Baseado no formato e condição da imagem, o domínio chamará um parser correspondente (ex: `CsvParser`, `PdfParserStrategy`, `OcrAiParserStrategy`).
- **Interfaces e Portas:** Bibliotecas do usuário, frameworks de web/API e ferramentas de bancos de dados interagirão de fora pra dentro com o núcleo através de adaptadores e *Ports*.

## 2. Plataforma e Linguagem
- **Linguagem Principal:** Python 3.12+ 
- **Gerenciador de Projetos de Ferramentas:** `uv` (para gerência ultrarrápida do motor e pacotes).

## 3. Operabilidade e Flexibilidade
- **Suporte a Múltiplos Formatos de Importação:** A *engine* de ingestão deve ser capaz de decodificar e extrair dados financeiros de formatos variados, como PDF nativo, formatos de imagem, TXT, CSV e TSV.
- **Portabilidade Plena (Deployment):** A aplicação será construída e executada em containers (via *Docker*) para garantir extrema flexibilidade técnica quanto a decisão do ambiente de produção.

## 4. Infraestrutura e Persistência
- **Persistência das Entidades:** SQLAlchemy mapeando o modelo transacional e Alembic para evolução paralela do banco de dados (DDL).
- **Banco de Dados:** Utilização de SQLite em desenvolvimento local e PostgreSQL em produção (via Docker).
- **Flexibilidade Híbrida de IA:** Ao lidar com OCR e classificação, a aplicação pode requisitar APIs na Nuvem ou integrar modelos pequenos locais, sendo uma configuração flexível.

## 5. Gestão e Controle de Mudanças
- **Controle de Versão:** Uso exclusivo de *Git* para código e gerenciamento de tarefas.
- **Documentação:** Manutenção evolutiva contínua de um sistema base de documentos em diretório interno (`/docs`).
