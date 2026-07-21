# Documentação do Domínio Financeiro - Requisitos e Casos de Uso

Esta documentação consolida as regras de negócio, a estrutura do domínio e os fluxos fundamentais da aplicação de finanças familiares. O foco está em manter a integridade contábil estrita através dos conceitos de Regime de Caixa, Regime de Competência e Partidas Dobradas.

---

## 1. Requisitos Funcionais e Não Funcionais

Abaixo estão consolidados os requisitos de negócios, restrições tecnológicas e as funcionalidades que a aplicação proverá.

### 1.1. Requisitos Funcionais

#### Gestão de Transações e Domínio Contábil
- O sistema deve permitir o cadastro manual e edição de transações (receitas e despesas).
- **Tipagem Contábil:** Suporte a diferentes tipos de contas patrimoniais (Bancária/Ativo, Carteira/Ativo, Cartão de Crédito/Passivo e Fiado/Passivo).
- **Regime de Competência (DRE):** As transações devem ser registradas na data exata em que o fato gerador (despesa ou receita) ocorreu, independentemente de seu pagamento.
- **Previsibilidade e Convergência Projetada:** Separar transações consolidadas de projetadas (orçamentos) sem misturar saldos. A projeção de saldos em meses futuros deve obrigatoriamente ter como ponto de partida o **saldo real (caixa residual consolidado)** do último mês fechado. O histórico de projeções passadas é mantido apenas para fins de auditoria; o futuro financeiro projeta-se estritamente sobre a realidade financeira atual, mitigando o "descolamento" de projeções irreais (*Projected Drift*).
- **Movimentação sem Custo (Transferências):** O sistema deve tratar movimentações entre contas (inclusive pagamentos de passivos) puramente como transferência de liquidez, sem gerar despesas falsas no DRE.
- **Consistência de Fechamento (O(1) Balance):** Gerar fotografias periódicas de saldos (`MonthlyBalance`), real e projetado, evitando cálculo infinito desde o "Big Bang".

#### Importação, Classificação Automática e IA
- O usuário poderá realizar upload de extratos bancários e de cartão de crédito para contabilização total.
- Classificar transações automaticamente por categorias globais (ex: Alimentação, Transporte).
- Utilizar Inteligência Artificial para mapeamento e classificação de despesas.
- Integrar Visão Computacional / OCR para extrair digitalmente despesas de PDFs (escaneados/imagens).

#### Estrutura Organizacional e Multi-família
- **Multi-Tenancy Isolado:** A aplicação deve suportar múltiplas famílias isoladas.
- Cada família pode possuir múltiplos membros. O controle financeiro é gerido em nível de Família.
- Diferenciar contexto de acesso e financeiro: **Usuário** (autenticação) vs **Membro** (domínio, vinculado à Família).

#### Instrumentos Financeiros, Cartões e Orçamento
- **Contas Bancárias:** Obrigatoriamente associadas a um membro (titular principal).
- **Cartão de Crédito e Faturas:** O cartão, enquanto entidade controladora de limite, possui titular único. O sistema deve compilar compras em uma fatura (`CreditCardBill`), suportando cálculos de dívida pendente e juros.
- **Hierarquia de Cartões (Instâncias):** Um cartão pode ter múltiplas instâncias (titular e dependentes). 
- **Receitas e Dinheiro em Espécie (Caixa):** Receitas podem ser de um titular ou da família. Suporte ao controle de dinheiro vivo.

### 1.2. Requisitos Não Funcionais

- **Arquitetura e Design:** Foco na **Clean Architecture** (Arquitetura Limpa / Hexagonal) isolando o núcleo. Implementação do **Strategy Pattern** para parsers de ingestão (`CsvParser`, `PdfParserStrategy`, etc.). Interação de fora para dentro via adaptadores e Portas.
- **Plataforma e Linguagem:** Python 3.12+ e gerenciador de projetos `uv`.
- **Operabilidade e Deployment:** Suporte a múltiplos formatos (PDF, imagem, TXT, CSV) para ingestão. Aplicação containerizada (*Docker*) garantindo portabilidade.
- **Persistência:** SQLAlchemy com Alembic. Banco SQLite em dev e PostgreSQL em produção.
- **Flexibilidade de IA:** Capacidade de chamar APIs na Nuvem ou integrar LLMs/Modelos menores locais.
- **Segurança e Proteção de Dados:** Uso de algoritmos de hashing (Argon2/Bcrypt) para senhas. Autenticação baseada em tokens JWT.
- **Gestão de Mudanças:** Uso de *Git* e manutenção evolutiva contínua de documentação em `/docs`.

---

## 2. Exemplos de Casos de Uso do Domínio (Mapeamento para Classes)

Para facilitar a compreensão do comportamento do domínio, os casos de uso abaixo seguem uma linha do tempo contínua. As tabelas ilustram o estado (histórico e saldo real) de cada conta após a execução daquele caso de uso, bem como a evolução do **Patrimônio Líquido** (Ativos - Passivos).

### UC01: Setup do Ecossistema Familiar e Injeção de Capital
**Resumo:** Criação do ambiente base para operação financeira e recebimento de saldo inicial.
**Exemplo do Mundo Real:** João cria sua conta e cadastra a "Família Silva", adicionando sua esposa Maria. Ele cria uma conta bancária do **Itaú**, uma **Carteira** (dinheiro vivo), um cartão **Nubank** e uma conta fiado na **Padaria do Zé**. Logo após, João registra o recebimento do seu salário de R$ 5.000,00 no Itaú e realiza um saque de R$ 200,00 para a Carteira.
**Mapeamento de Classes:**
- `Family` e `Member`: Criadas.
- `BankAccount` (Itaú), `Wallet` (Carteira): Criadas como `AccountType.ASSET`.
- `CreditCard` (Nubank), `Tab` (Padaria): Criadas como `AccountType.LIABILITY`.
- `Transaction`: Salário criado como `INCOME` de R$ 5.000,00 no Itaú.
- `Transfer`: Saque de R$ 200,00 do Itaú para a Carteira.

| Ativo/Passivo | Conta | Saldo Atual | Histórico da Operação |
|---|---|---|---|
| Ativo | Itaú (Banco) | R$ 4.800,00 | + R$ 5.000,00 (Salário) <br> - R$ 200,00 (Saque) |
| Ativo | Carteira (Dinheiro) | R$ 200,00 | + R$ 200,00 (Saque recebido) |
| Passivo | Nubank (Cartão) | R$ 0,00 | - |
| Passivo | Padaria do Zé (Fiado)| R$ 0,00 | - |
| **Geral** | **Patrimônio Líquido**| **R$ 5.000,00** | R$ 5.000,00 (Ativos) - R$ 0,00 (Passivos) |

### UC02: Gasto Corrente (Débito/Pix)
**Resumo:** Registro de despesa em regime de caixa imediato.
**Exemplo do Mundo Real:** Maria vai ao supermercado e gasta R$ 150 pagando via Pix usando o saldo do Itaú.
**Mapeamento de Classes:**
- `Transaction`: Instanciada com `amount=150.00`, `type=TransactionType.EXPENSE`, e `account_id` apontando para o Itaú. Entra imediatamente no DRE e reduz o Fluxo de Caixa.

| Ativo/Passivo | Conta | Saldo Atual | Histórico da Operação |
|---|---|---|---|
| Ativo | Itaú (Banco) | R$ 4.650,00 | - R$ 150,00 (Supermercado) |
| Ativo | Carteira (Dinheiro) | R$ 200,00 | - |
| Passivo | Nubank (Cartão) | R$ 0,00 | - |
| Passivo | Padaria do Zé (Fiado)| R$ 0,00 | - |
| **Geral** | **Patrimônio Líquido**| **R$ 4.850,00** | R$ 4.850,00 (Ativos) - R$ 0,00 (Passivos) |

### UC03: Compra no Cartão de Crédito
**Resumo:** Gasto gerador de passivo, atrelado a um ciclo de cobrança futuro.
**Exemplo do Mundo Real:** João compra um micro-ondas de R$ 500 no Nubank.
**Mapeamento de Classes:**
- `CreditCardBill`: O cliente do domínio (camada de aplicação/usuário) especifica de forma explícita em qual fatura (ex: ciclo '2026-05') a transação será lançada. Delegar ao sistema a dedução automática com base na data da transação é uma prática frágil (devido à oscilação das datas de corte). O sistema, então, recupera ou cria essa fatura especificada.
- `Transaction`: Criada com `type=EXPENSE`, `amount=500.00`, vinculada ao Nubank e à Fatura (através do `credit_card_bill_id`). A despesa entra no DRE atual, impacta o patrimônio, mas **não** reduz o saldo do Itaú (caixa atual).

| Ativo/Passivo | Conta | Saldo Atual | Histórico da Operação |
|---|---|---|---|
| Ativo | Itaú (Banco) | R$ 4.650,00 | - |
| Ativo | Carteira (Dinheiro) | R$ 200,00 | - |
| Passivo | Nubank (Cartão) | - R$ 500,00 | - R$ 500,00 (Micro-ondas) na Fatura Aberta |
| Passivo | Padaria do Zé (Fiado)| R$ 0,00 | - |
| **Geral** | **Patrimônio Líquido**| **R$ 4.350,00** | R$ 4.850,00 (Ativos) - R$ 500,00 (Passivos) |

### UC04: Consumo em Conta Fiado (Tab) e Quitação
**Resumo:** Gasto em passivo não estruturado e pagamento posterior em dinheiro.
**Exemplo do Mundo Real:** João compra pão fiado por R$ 30,00. No dia seguinte, ele usa R$ 30,00 em espécie da sua Carteira para quitar a conta na padaria.
**Mapeamento de Classes:**
- **Passo 1:** `Transaction` de despesa (`EXPENSE`) atrelada ao `account_id` da Padaria. O saldo da Padaria vai a -R$ 30,00 e o Patrimônio cai para R$ 4.320,00.
- **Passo 2:** `Transfer` da Carteira para a Padaria. O saldo da Carteira diminui para R$ 170,00 e o da Padaria zera. O Patrimônio Líquido se mantém estável, tratando-se apenas de movimentação de liquidez.

| Ativo/Passivo | Conta | Saldo Atual | Histórico da Operação |
|---|---|---|---|
| Ativo | Itaú (Banco) | R$ 4.650,00 | - |
| Ativo | Carteira (Dinheiro) | R$ 170,00 | - R$ 30,00 (Transferência p/ quitar fiado) |
| Passivo | Nubank (Cartão) | - R$ 500,00 | - |
| Passivo | Padaria do Zé (Fiado)| R$ 0,00 | - R$ 30,00 (Pão Fiado) <br> + R$ 30,00 (Dinheiro recebido) |
| **Geral** | **Patrimônio Líquido**| **R$ 4.320,00** | R$ 4.820,00 (Ativos) - R$ 500,00 (Passivos) |

### UC05: Pagamento Total de Fatura de Cartão
**Resumo:** Movimentação de liquidez (Ativo para Passivo) para quitação de dívida consolidada.
**Exemplo do Mundo Real:** Chega o dia do vencimento e João paga a fatura completa do Nubank (R$ 500) usando o dinheiro que estava no Itaú.
**Mapeamento de Classes:**
- `Transfer`: Instanciada com `origin_account_id` (Itaú), `destination_account_id` (Nubank) e `amount=500.00`.
- `CreditCardBill`: A fatura tem sua flag `is_closed=True` e `payments_received=500.00`.
- **Comportamento:** O pagamento **não** gera uma `EXPENSE` (o impacto no patrimônio já ocorreu no UC03 com a compra do micro-ondas). A liquidez apenas se transfere.

| Ativo/Passivo | Conta | Saldo Atual | Histórico da Operação |
|---|---|---|---|
| Ativo | Itaú (Banco) | R$ 4.150,00 | - R$ 500,00 (Pagto Fatura Nubank) |
| Ativo | Carteira (Dinheiro) | R$ 170,00 | - |
| Passivo | Nubank (Cartão) | R$ 0,00 | + R$ 500,00 (Recebimento Itaú) |
| Passivo | Padaria do Zé (Fiado)| R$ 0,00 | - |
| **Geral** | **Patrimônio Líquido**| **R$ 4.320,00** | R$ 4.320,00 (Ativos) - R$ 0,00 (Passivos) |

### UC06: Pagamento Parcial, Rolagem e Juros
**Resumo:** Fatura paga parcialmente, gerando rolagem de dívida para o mês seguinte atrelado a juros bancários.
**Exemplo do Mundo Real:** Dias depois, João faz uma nova compra de R$ 1.000 no Nubank e a fatura fecha. Sem caixa suficiente para o montante, ele opta por pagar apenas R$ 600 via Itaú, mantendo a diferença em aberto. No mês seguinte, o Nubank cobra R$ 40 de juros na fatura nova pela rolagem.
**Mapeamento de Classes:**
- `Transaction`: Despesa inicial de R$ 1.000 no Nubank. Patrimônio cai R$ 1.000.
- `Transfer`: Pagamento de R$ 600 (Itaú -> Nubank). Saldo Itaú cai para R$ 3.550. Dívida Nubank residual vai para -R$ 400.
- Fatura Seguinte: Inicializada já devendo R$ 400 (`previous_balance`).
- `Transaction` (Juros): Despesa (`EXPENSE`) gerada de `amount=40` vinculada à nova fatura. Dívida Nubank totaliza -R$ 440. Patrimônio é deduzido em mais R$ 40.

| Ativo/Passivo | Conta | Saldo Atual | Histórico da Operação |
|---|---|---|---|
| Ativo | Itaú (Banco) | R$ 3.550,00 | - R$ 600,00 (Pagto Parcial Fatura) |
| Ativo | Carteira (Dinheiro) | R$ 170,00 | - |
| Passivo | Nubank (Cartão) | - R$ 440,00 | - R$ 1.000,00 (Nova Compra) <br> + R$ 600,00 (Pagto Parcial Itaú) <br> - R$ 40,00 (Juros da Rolagem) |
| Passivo | Padaria do Zé (Fiado)| R$ 0,00 | - |
| **Geral** | **Patrimônio Líquido**| **R$ 3.280,00** | R$ 3.720,00 (Ativos) - R$ 440,00 (Passivos) |

### UC07: Injeção de Orçamento (Gastos Previstos)
**Resumo:** Projeção de fluxo de caixa e patrimônio futuro para fins de planejamento familiar.
**Exemplo do Mundo Real:** João anota no app que precisará pagar a mensalidade da escola de R$ 500 no mês que vem, e que usará o Itaú para o pagamento. O boleto ainda não chegou.
**Mapeamento de Classes:**
- `Transaction`: Instanciada com `amount=500.00`, `is_forecast=True` (Previsão).
- **Comportamento:** O valor de R$ 500 altera exclusivamente os **saldos projetados** (`projected_balance`). O saldo real (`real_balance`) contábil não muda, garantindo conciliação exata imediata com os extratos bancários.

| Ativo/Passivo | Conta | Saldo Real | Saldo Projetado | Histórico da Operação (Projetada) |
|---|---|---|---|---|
| Ativo | Itaú (Banco) | R$ 3.550,00 | R$ 3.050,00 | - R$ 500,00 (Previsão Escola Filho) |
| Ativo | Carteira (Dinheiro) | R$ 170,00 | R$ 170,00 | - |
| Passivo | Nubank (Cartão) | - R$ 440,00 | - R$ 440,00 | - |
| Passivo | Padaria do Zé (Fiado)| R$ 0,00 | R$ 0,00 | - |
| **Geral** | **Patrimônio Líquido**| **R$ 3.280,00** | **R$ 2.780,00** | (Redução baseada na previsão) |

### UC08: Fechamento Contábil Mensal
**Resumo:** Consolidação de saldo para busca de performance O(1) nos relatórios, blindando a arquitetura do sistema contra o recálculo eterno do "Big Bang".
**Exemplo do Mundo Real:** No dia 01 do mês seguinte, o sistema cristaliza o saldo exato que ficou em cada conta ao final do mês vigente, transformando as métricas atuais na base fixa de partida do mês futuro.
**Mapeamento de Classes:**
- `MonthlyBalance`: Entidade instanciada via `MonthlyBalance.create_from_history(...)`. Grava o instante onde o fechamento apurou as métricas reais da tabela do UC06/UC07 (Itaú = 3.550; Nubank = -440; etc).
- **Convergência de Projeção vs Realidade:** No momento do fechamento, ao construir a fundação matemática para o mês subsequente, o *saldo inicial projetado* do novo mês será exatamente igual ao *saldo residual real* que acaba de ser fechado. O histórico do que foi projetado e não ocorreu no passado fica no banco apenas para consultas de variação de orçamento.
- **Comportamento e Imutabilidade:** O snapshot é protegido (imutável). A inserção retroativa de uma transação esquecida exigirá o disparo de rotina controlada que recalcula os *snapshots* sequenciais, livrando a API de ler milhões de registros para atestar um saldo atual na tela do usuário.

---
**Nota Arquitetural:** Com o domínio blindado cobrindo todos esses cenários, a próxima etapa estrutural do sistema será o desenvolvimento dos **Testes de Integração/Casos de Uso** para provar que a orquestração dessas entidades ocorre com fluidez e integridade.
