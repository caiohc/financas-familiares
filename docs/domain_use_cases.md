# Documentação do Domínio Financeiro - Requisitos e Casos de Uso

Esta documentação consolida as regras de negócio, a estrutura do domínio e os fluxos fundamentais da aplicação de finanças familiares. O foco está em manter a integridade contábil estrita através dos conceitos de Regime de Caixa, Regime de Competência e Partidas Dobradas.

---

## 1. Requisitos Funcionais (RF)

Os requisitos a seguir definem o que o núcleo do sistema é capaz de entregar.

* **RF01 - Multi-Tenancy Isolado:** O sistema deve garantir que todos os dados, contas e transações estejam encapsulados no escopo de uma Família.
* **RF02 - Tipagem Contábil:** O sistema deve suportar diferentes tipos de contas patrimoniais (Bancária/Ativo, Carteira/Ativo, Cartão de Crédito/Passivo e Fiado/Passivo).
* **RF03 - Regime de Competência (DRE):** As transações devem ser registradas na data exata em que o fato gerador (despesa ou receita) ocorreu, independentemente de seu pagamento.
* **RF04 - Ciclo de Cartão de Crédito:** O sistema deve compilar compras de crédito em uma fatura (`CreditCardBill`), suportando cálculos de dívida pendente (rolagem de fatura) e juros.
* **RF05 - Movimentação sem Custo (Transferências):** O sistema deve tratar movimentações entre contas (inclusive pagamentos de passivos) puramente como transferência de liquidez, sem gerar despesas falsas no DRE.
* **RF06 - Consistência de Fechamento (O(1) Balance):** O sistema deve gerar "fotografias" periódicas de saldos (`MonthlyBalance`), divididas em real e projetado, evitando o cálculo infinito desde o "Big Bang" (primeira transação).
* **RF07 - Previsibilidade:** O sistema deve separar transações consolidadas de transações projetadas (orçamentos), sem misturar os saldos.

---

## 2. Casos de Uso do Domínio (UC)

### UC01: Setup do Ecossistema Familiar
**Resumo:** Criação do ambiente base para operação financeira.
**Exemplo do Mundo Real:** João cria sua conta no aplicativo e cadastra o nome da sua família, adicionando sua esposa Maria como membro. Em seguida, João cadastra a conta bancária conjunta do Itaú.
**Mapeamento de Classes:**
- `Family`: Criada com `name="Família Silva"`.
- `Member`: Criado vinculado à `Family`.
- `BankAccount`: Instanciada herdando de `Account`. O atributo `account_type` é automaticamente injetado como `AccountType.ASSET` pelas validações internas do construtor abstrato.

### UC02: Gasto Corrente (Débito/Pix)
**Resumo:** Registro de despesa em regime de caixa imediato.
**Exemplo do Mundo Real:** Maria vai ao supermercado e gasta R$ 150 pagando via Pix usando o saldo da conta do Itaú.
**Mapeamento de Classes:**
- `Transaction`: Instanciada com `amount=150.00`, `type=TransactionType.EXPENSE`, `date=Hoje`, e `account_id` apontando para a `BankAccount`.
- **Comportamento:** Essa transação entra tanto no DRE do mês quanto no Fluxo de Caixa do mês imediatamente.

### UC03: Compra no Cartão de Crédito
**Resumo:** Gasto gerador de passivo, atrelado a um ciclo de cobrança futuro.
**Exemplo do Mundo Real:** João compra um micro-ondas de R$ 500 no cartão Nubank da família.
**Mapeamento de Classes:**
- `CreditCard`: Conta passiva pai.
- `CreditCardBill`: O sistema localiza (ou cria) a fatura aberta cujo ciclo (Ex: '2026-05') engloba a data da compra.
- `Transaction`: Criada com `amount=500.00`, `type=TransactionType.EXPENSE`, `account_id` (ID do Nubank), e vitalmente, o atributo `credit_card_bill_id` preenchido com a Fatura.
- **Comportamento:** A compra entra no DRE de Maio, porém NÃO impacta o fluxo de caixa de Maio.

### UC04: Pagamento Total de Fatura de Cartão
**Resumo:** Movimentação de liquidez (Ativo para Passivo) para quitação de dívida.
**Exemplo do Mundo Real:** Chega o dia 10 e João paga a fatura completa do Nubank de R$ 500 usando dinheiro do Itaú.
**Mapeamento de Classes:**
- `Transfer`: Instanciada com `origin_account_id` (Itaú), `destination_account_id` (Nubank) e `amount=500.00`.
- `CreditCardBill`: A fatura tem sua flag `is_closed=True` e, logicamente, os `payments_received=500.00`.
- **Comportamento:** O pagamento não gera uma `Transaction` de `EXPENSE`. O relatório de Fluxo de Caixa lerá a Transferência (ou a soma da fatura associada à data da transferência) para desenhar o gráfico.

### UC05: Pagamento Parcial, Rolagem e Juros
**Resumo:** Fatura paga parcialmente, gerando rolagem de dívida para o mês seguinte mais penalidades.
**Exemplo do Mundo Real:** Da fatura de R$ 500, João pagou apenas R$ 200. No mês seguinte, o Nubank cobrou R$ 30 de juros.
**Mapeamento de Classes:**
- Fatura Mês 1: Encerrada com `previous_balance=0`, `total_amount=500`, mas `payments_received=200`.
- Fatura Mês 2: 
  - Inicializada com `previous_balance=500` e `payments_received=200`. 
  - `Transaction` Nova: Criada com `amount=30`, `type=EXPENSE`, `description="Juros"`.
- O método de fábrica `CreditCardBill.calculate_total(...)` calcula: `(500 - 200) + 30 = R$ 330,00` como novo total da fatura Mês 2. A dívida acumulou matematicamente na fatura sem duplicar lançamentos na Conta.

### UC06: Consumo em Conta Fiado (Tab)
**Resumo:** Passivo não estruturado e sem data fixa de vencimento.
**Exemplo do Mundo Real:** João pegou pão na "Padaria do Zé" e marcou na caderneta. Dias depois ele foi lá e pagou via Pix.
**Mapeamento de Classes:**
- `Tab`: Criada herdando de `Account` (`AccountType.LIABILITY`).
- `Transaction`: Despesa de pão (`EXPENSE`) atrelada ao `account_id` da `Tab`. Saldo negativo.
- `Transfer`: João transfere dinheiro do Itaú para a `Tab`. O saldo da Padaria fica zero, o saldo do Itaú diminui.

### UC07: Injeção de Orçamento (Gastos Previstos)
**Resumo:** Projeção de fluxo de caixa futuro.
**Exemplo do Mundo Real:** João anota que pretende gastar R$ 300 de energia no mês que vem. O boleto ainda não chegou.
**Mapeamento de Classes:**
- `Transaction`: Instanciada com `is_forecast=True` (Previsão).
- **Comportamento:** O valor de R$ 300 reduzirá o `projected_balance` da conta bancária no fechamento do mês, avisando a João se ele terá dinheiro suficiente. O `real_balance` permanece intacto para bater centavo por centavo com o aplicativo do banco real.

### UC08: Fechamento Contábil Mensal
**Resumo:** Consolidação de saldo para busca O(1) nos relatórios, blindando o sistema contra o recálculo do "Big Bang".
**Exemplo do Mundo Real:** No dia 01 do mês seguinte, o sistema cria o registro de quanto ficou na conta Itaú no final do mês passado.
**Mapeamento de Classes:**
- `MonthlyBalance`: Entidade instanciada via `MonthlyBalance.create_from_history(...)`.
- O método recebe os saldos do mês anterior, mais a lista de `Transaction` do mês atual. 
- Ele varre as transações, alterando o `real_balance` apenas se `is_forecast==False`, mas altera o `projected_balance` para todas.
- Esse snapshot é imutável e será o ponto de partida matemático para o mês seguinte.

---
**Nota Arquitetural:** Com o domínio blindado cobrindo todos esses cenários, a próxima etapa estrutural do sistema será o desenvolvimento dos **Testes de Integração/Casos de Uso** para provar que a orquestração dessas entidades ocorre com fluidez e integridade.
