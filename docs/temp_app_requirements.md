# Requisitos da Aplicação e Infraestrutura (Temporário)

Este documento guarda temporariamente os requisitos funcionais e não funcionais que não pertencem à camada de Domínio, mas sim às camadas de Aplicação, Infraestrutura e Interface. Eles serão realocados quando construirmos essas camadas.

## 1. Requisitos Funcionais

### Gestão de Transações e Interface
- O sistema deve permitir o cadastro manual e edição de transações (receitas e despesas) pelo usuário na interface.
- **Recálculo Retroativo:** Se o usuário editar, adicionar ou remover uma transação pertencente a um mês passado, o sistema deve recalcular automaticamente o snapshot de saldo (`MonthlyBalance`) daquele mês e propagar as alterações para os meses subsequentes, garantindo que o fechamento nunca fique dessincronizado com o histórico de transações.

### Importação, Classificação Automática e IA
- O usuário poderá realizar upload de extratos bancários e faturas de cartão.
- **Upload Idempotente (Deduplicação Automática):** O usuário poderá realizar o upload de extratos parciais com sobreposição de datas ou upload do mesmo extrato várias vezes. O sistema utilizará identificadores de origem (IDs da transação no banco/cartão) para ignorar transações já cadastradas, identificando univocamente as transações da fonte.
- O sistema deve integrar-se com serviços de OCR e IA para extrair dados digitais e auto-classificar transações.

## 2. Requisitos Não Funcionais
- **Framework e Ferramentas:** Uso de Python 3.12+ e gerenciador de pacotes `uv`.
- **Persistência e Banco de Dados:** Uso de SQLAlchemy (ORM) com Alembic para migrações, suportando SQLite localmente e PostgreSQL em produção.
- **Segurança e Autenticação:** Algoritmos de hashing seguros para senhas e sistema de autenticação e sessão baseado em tokens JWT.
