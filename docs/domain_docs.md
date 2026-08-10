# Documentação do Domínio Financeiro - Regras e Casos de Uso

Esta documentação consolida as regras de negócio, a estrutura do domínio e os fluxos fundamentais da aplicação de finanças familiares. O foco está em manter a integridade contábil estrita através dos conceitos de Regime de Caixa, Regime de Competência e Partidas Dobradas.

---

## 1. Fundamentação Teórica Contábil

Para garantir que o sistema não sofra problemas arquiteturais comuns a aplicativos de finanças pessoais (saldos inconsistentes, relatórios enganosos), o domínio baseia-se nos seguintes pilares da contabilidade corporativa:

- **Conta (Ativos e Passivos):** O sistema divide o dinheiro em duas naturezas. **Ativos** (`ASSET`) representam o dinheiro que você possui (Conta Bancária, Carteira). **Passivos** (`LIABILITY`) representam as suas obrigações (Dívidas, Cartão de Crédito, Contas a Pagar). O seu Patrimônio Líquido é sempre a diferença entre Ativos e Passivos.
- **Partidas Dobradas (Double-Entry):** Cada transação financeira impacta o sistema de forma dual. Uma receita aumenta o Ativo e aumenta o Lucro. Uma despesa paga diminui o Ativo e reduz o Lucro. Uma compra a prazo diminui o Lucro, mas em vez de diminuir o Ativo (pois o dinheiro ainda não saiu da conta bancária), ela aumenta o Passivo (dívida).
- **Regime de Competência e DRE:** O Demonstrativo de Resultados do Exercício (DRE) responde à pergunta: *"As minhas decisões me deram lucro ou prejuízo este mês?"*. Ele é pautado pela data do fato gerador (`accrual_date`). Se você usou energia elétrica em Julho, a despesa pertence a Julho, mesmo que a conta só seja paga em Agosto.
- **Regime de Caixa e Fluxo de Caixa:** O Relatório de Fluxo de Caixa responde à pergunta: *"Terei liquidez (dinheiro na conta) para pagar minhas obrigações?"*. Ele foca estritamente na data de movimentação real de dinheiro dos Ativos. Isso ocorre de duas formas: através da data de liquidação de um passivo (`Transfer.date`) ou, no caso de despesas à vista (Pix, Débito) lançadas diretamente em contas de Ativo, através da data de vencimento/competência da própria transação (`due_date`/`accrual_date`).
- **Relatório Patrimonial (Balanço):** Tira uma "fotografia" de todos os saldos no dia atual. Se uma conta venceu hoje e não foi paga, a dívida (Passivo) continua constando no seu Balanço, corroendo o seu Patrimônio Líquido até ser efetivamente quitada.
- **Balanço Mensal (O(1)):** Estratégia computacional onde, ao fim de cada mês, o sistema "congela" o saldo real da conta em uma entidade (`MonthlyBalance`). Isso evita que um relatório de Dezembro precise somar transações desde Janeiro de 2010 para descobrir o saldo, garantindo performance $O(1)$.
- **Conciliação e Baixa (Clearing):** Quando uma dívida (Passivo) é paga por uma conta bancária (Ativo), o dinheiro é "transferido" para a dívida (`Transfer`). Para que o sistema não perca o rastro de *qual* boleto foi pago, o processo de "Clearing" insere o ID dessa Transferência na transação original da dívida (via campo `settled_by_transfer_id`).

---

## 2. Requisitos do Domínio Financeiro

### 2.1. Regras de Negócio e Contabilidade

- **Tipagem Contábil:** O domínio deve dar suporte lógico às naturezas de contas patrimoniais (Bancária/Ativo, Carteira/Ativo, Cartão de Crédito/Passivo e Contas a Pagar/Passivo).
- **DRE vs Fluxo de Caixa:** As transações (`Transaction`) possuem duas datas fundamentais: a `accrual_date` (Data de Competência) que pauta o DRE, e a `due_date` (Data de Vencimento esperada).
- **Rastreabilidade (Clearing):** Boletos e dívidas informais lançadas na conta `AccountsPayable` recebem, no momento do pagamento, o vínculo para a Transferência real que os quitou (`settled_by_transfer_id`).
- **Previsibilidade e Convergência:** O domínio permite a identificação de previsões. Previsões não realizadas cuja data expirou perdem validade e o domínio deve refletir as informações para notificação de "Previsão Obsoleta".

### 2.2. Estrutura Organizacional e Instrumentos

- **Multi-Tenancy:** A estrutura do domínio baseia-se em suportar múltiplas Famílias e Membros independentes.
- **Centros de Custo (Subfamílias/Propriedades):** A entidade `FamilyCostCenter` permite que transações sejam alocadas a um agrupador lógico (ex: "Núcleo Sogra", "Casa de Praia", "Filho"), permitindo a geração de relatórios de DRE e Fluxo de Caixa individuais para o centro de custo sem violar a liquidez global da conta bancária da família.
- **Cartões e Faturas:** O domínio garante que múltiplas instâncias de cartão rodam sobre o mesmo limite, compilando-se matematicamente em Faturas Mensais (`CreditCardBill`).

### 2.3. Requisitos Não Funcionais do Domínio
- **Arquitetura Base:** O modelo do domínio deve seguir rigidamente os princípios de **Domain-Driven Design (DDD)**, isolando-se completamente das regras de UI, banco de dados ou frameworks externos, escrito puramente em Python.

---

## 3. Casos de Uso do Domínio e Mapeamento

Para facilitar a compreensão do comportamento estrito do domínio (sem levar em conta o Banco de Dados ou a Interface de Usuário), os casos de uso abaixo seguem uma linha do tempo contínua. As tabelas ilustram o estado (histórico e saldo real) de cada conta após a execução daquele caso de uso, bem como a evolução do **Patrimônio Líquido**.

### UC01: Setup do Ecossistema e Injeção de Capital
**Resumo:** Criação do ambiente base e recebimento de saldo.
**Exemplo:** João cria a "Família Silva". Ele cria uma conta do **Itaú**, uma **Carteira**, um cartão **Nubank** e uma "Conta a Pagar" para Boletos/Fiados. João registra o seu salário de R$ 5.000,00 no Itaú e realiza um saque de R$ 200,00.
**Classes:** `BankAccount` (Ativo), `Wallet` (Ativo), `CreditCard` (Passivo), `AccountsPayable` (Passivo).
- Transação 1: `INCOME`, R$ 5000 (Itaú).
- Transferência: R$ 200 (Itaú -> Carteira).

| Conta | Tipo | Saldo Atual | Histórico |
|---|---|---|---|
| Itaú | Ativo | R$ 4.800,00 | + R$ 5.000,00 (Salário) <br> - R$ 200,00 (Saque) |
| Carteira | Ativo | R$ 200,00 | + R$ 200,00 (Saque recebido) |
| Nubank | Passivo | R$ 0,00 | - |
| Contas a Pagar | Passivo | R$ 0,00 | - |
| **Geral** | **Patrimônio**| **R$ 5.000,00** | R$ 5.000,00 (Ativos) - R$ 0,00 (Passivos) |

### UC02: Gasto Corrente (Débito/Pix)
**Resumo:** Despesa em regime de caixa imediato.
**Exemplo:** Maria vai ao supermercado e gasta R$ 150 pagando via Pix do Itaú.
**Classes:** `Transaction` (`EXPENSE`, `accrual_date=Hoje`, `due_date=Hoje`, `account_id=Itaú`). Entra imediatamente no DRE e reduz o Fluxo de Caixa. (O Patrimônio Líquido vai para R$ 4.850,00).

| Conta | Tipo | Saldo Atual | Histórico |
|---|---|---|---|
| Itaú | Ativo | R$ 4.650,00 | - R$ 150,00 (Supermercado) |
| Carteira | Ativo | R$ 200,00 | - |
| Nubank | Passivo | R$ 0,00 | - |
| Contas a Pagar | Passivo | R$ 0,00 | - |
| **Geral** | **Patrimônio**| **R$ 4.850,00** | R$ 4.850,00 (Ativos) - R$ 0,00 (Passivos) |

### UC02.5: Gasto Diferido (Boleto Futuro / Conta a Pagar)
**Resumo:** O fato gerador e o desembolso ocorrem em momentos distintos.
**Exemplo:** João recebe um boleto do condomínio (Julho) no valor de R$ 1.000, vencimento para o mês seguinte.
**Classes:** 
- `Transaction`: `EXPENSE`, `account_id=AccountsPayable`, `accrual_date=Julho`, `due_date=10 de Agosto`, `settled_by_transfer_id=None` (Não Pago).
- **Comportamento:** O DRE de Julho absorve a despesa. O Patrimônio de Julho cai para R$ 3.850,00 devido à dívida recém-criada no Passivo, embora o dinheiro no banco permaneça intacto.

| Conta | Tipo | Saldo Atual | Histórico |
|---|---|---|---|
| Itaú | Ativo | R$ 4.650,00 | - |
| Carteira | Ativo | R$ 200,00 | - |
| Nubank | Passivo | R$ 0,00 | - |
| Contas a Pagar | Passivo | - R$ 1.000,00 | - R$ 1.000,00 (Boleto Condomínio) |
| **Geral** | **Patrimônio**| **R$ 3.850,00** | R$ 4.850,00 (Ativos) - R$ 1.000,00 (Passivos) |

### UC03: Compra no Cartão de Crédito
**Resumo:** Gasto gerador de passivo atrelado a ciclo futuro de fatura.
**Exemplo:** João compra um micro-ondas de R$ 500 no Nubank.
**Classes:** `CreditCardBill` e `Transaction` (`EXPENSE`, R$ 500 no Nubank). Entra no DRE, aumenta o passivo para R$ 500. Patrimônio cai para R$ 3.350,00.

| Conta | Tipo | Saldo Atual | Histórico |
|---|---|---|---|
| Itaú | Ativo | R$ 4.650,00 | - |
| Carteira | Ativo | R$ 200,00 | - |
| Nubank | Passivo | - R$ 500,00 | - R$ 500,00 (Micro-ondas) |
| Contas a Pagar | Passivo | - R$ 1.000,00 | - |
| **Geral** | **Patrimônio**| **R$ 3.350,00** | R$ 4.850,00 (Ativos) - R$ 1.500,00 (Passivos) |

### UC04: Quitação (Clearing) de Conta a Pagar / Boleto
**Resumo:** Pagamento de uma dívida consolidada (passivo).
**Exemplo:** Chega o dia 10 de Agosto e João paga o boleto do condomínio de R$ 1.000 usando a conta do Itaú.
**Classes:**
- `Transfer`: Instanciada (Itaú -> Contas a Pagar), no valor de R$ 1.000 na data de 10 de Agosto.
- **Conciliação (O Pulo do Gato):** O sistema vincula o ID dessa Transferência ao campo `settled_by_transfer_id` da Transação original (UC02.5). Agora sabemos que o boleto não só está pago, mas como e quando foi pago.

| Conta | Tipo | Saldo Atual | Histórico |
|---|---|---|---|
| Itaú | Ativo | R$ 3.650,00 | - R$ 1.000,00 (Pagto Condomínio) |
| Carteira | Ativo | R$ 200,00 | - |
| Nubank | Passivo | - R$ 500,00 | - |
| Contas a Pagar | Passivo | R$ 0,00 | + R$ 1.000,00 (Recebimento Itaú) |
| **Geral** | **Patrimônio**| **R$ 3.350,00** | R$ 3.850,00 (Ativos) - R$ 500,00 (Passivos) |

### UC05: Pagamento Total de Fatura de Cartão
**Resumo:** Movimentação de liquidez (Ativo para Passivo).
**Exemplo:** Chega o dia do vencimento e João paga a fatura completa do Nubank (R$ 500) usando o Itaú.
**Classes:** `Transfer` (Itaú -> Nubank). O pagamento **não** gera despesa extra. A fatura recebe `is_closed=True`. Saldo do Itaú cai para R$ 3.150 e Nubank zera. Patrimônio Líquido se mantém em R$ 3.350,00.

| Conta | Tipo | Saldo Atual | Histórico |
|---|---|---|---|
| Itaú | Ativo | R$ 3.150,00 | - R$ 500,00 (Pagto Fatura Nubank) |
| Carteira | Ativo | R$ 200,00 | - |
| Nubank | Passivo | R$ 0,00 | + R$ 500,00 (Recebimento Itaú) |
| Contas a Pagar | Passivo | R$ 0,00 | - |
| **Geral** | **Patrimônio**| **R$ 3.350,00** | R$ 3.350,00 (Ativos) - R$ 0,00 (Passivos) |

### UC06: Juros e Multas
**Resumo:** Injeção de custos financeiros sobre atrasos em Passivos.
**Exemplo:** João esquece de pagar um boleto de Internet de R$ 100, gerando uma multa de R$ 10. Ele paga o total de R$ 110 usando o Itaú.
**Classes:** Uma nova `Transaction` de `EXPENSE` no valor de R$ 10 (Categoria Juros/Multa) é inserida junto à original de R$ 100 na conta `AccountsPayable`. **Rastreabilidade Opcional:** Essa nova transação pode receber o ID da transação original (o boleto) no campo `originating_transaction_id`, permitindo análises ricas futuras sobre quais despesas mais geram encargos. O passivo total bate R$ -110. Ao realizar a `Transfer` de pagamento, R$ 110 saem do Itaú, zerando matematicamente o passivo (e ambos recebem o `settled_by_transfer_id`).

| Conta | Tipo | Saldo Atual | Histórico |
|---|---|---|---|
| Itaú | Ativo | R$ 3.040,00 | - R$ 110,00 (Pagto Boleto + Multa) |
| Carteira | Ativo | R$ 200,00 | - |
| Nubank | Passivo | R$ 0,00 | - |
| Contas a Pagar | Passivo | R$ 0,00 | - R$ 100 (Boleto) - R$ 10 (Multa) + R$ 110 (Pagto Itaú) |
| **Geral** | **Patrimônio**| **R$ 3.240,00** | R$ 3.240,00 (Ativos) - R$ 0,00 (Passivos) |

### UC07: Injeção de Orçamento (Gastos Previstos)
**Resumo:** Projeção de fluxo de caixa futuro.
**Exemplo:** João anota que vai gastar R$ 200 em gasolina na semana que vem.
**Classes:** `Transaction` (`is_forecast=True`). 
- **Comportamento:** Altera exclusivamente os **saldos projetados**. O **saldo real contábil não muda**, garantindo conciliação imediata com extratos bancários. A tabela de saldos reais abaixo permanece inalterada em relação ao passo anterior.

| Conta | Tipo | Saldo Real | Saldo Projetado (Futuro) |
|---|---|---|---|
| Itaú | Ativo | R$ 3.040,00 | R$ 2.840,00 (- R$ 200 de Gasolina) |
| Carteira | Ativo | R$ 200,00 | R$ 200,00 |
| Nubank | Passivo | R$ 0,00 | R$ 0,00 |
| Contas a Pagar | Passivo | R$ 0,00 | R$ 0,00 |
| **Geral** | **Patrimônio**| **R$ 3.240,00** | **R$ 3.040,00** |

### UC05: Fechamento e Pagamento Parcial de Fatura (CreditCardBill)
**Resumo:** Diferente de uma conta comum onde cada transação recebe a baixa individualmente, no cartão de crédito quem recebe o pagamento é a **Fatura** (um agregador lógico). A fatura engloba as transações do mês e a dívida rolada. Se o usuário decide pagar apenas um valor parcial, a diferença torna-se a nova dívida inicial da próxima fatura.
**Classes:** O sistema calcula o `total_amount` do `CreditCardBill` baseado no `previous_balance` e soma as despesas do mês. O pagamento é uma `Transfer` do Banco para o Cartão de Crédito. O id dessa transferência é adicionado na lista `settled_by_transfer_ids` da fatura (que suporta múltiplos pagamentos parciais). O que sobrar (Saldo devedor real final do mês) iniciará o mês seguinte.
**Encargos de Atraso:** Se essa rolagem de dívida gerar juros no mês seguinte, a transação de juros (`Transaction`) receberá no atributo `originating_bill_id` o UUID desta fatura que gerou a penalidade. O histórico projetado do mês passado fica obsoleto (apenas leitura), e a contabilidade do mês atual começa exatamente do saldo consolidado no snapshot anterior.

### UC08: Fechamento Contábil Mensal
**Resumo:** Consolidação de saldo `O(1)`.
**Exemplo:** Todo dia 01 do mês, o sistema salva um snapshot do saldo exato do mês encerrado para cada conta em `MonthlyBalance` (Os exatos valores da tabela Real acima). O histórico projetado do mês passado fica obsoleto (apenas leitura), e a contabilidade do mês atual começa exatamente do saldo consolidado no snapshot anterior.
