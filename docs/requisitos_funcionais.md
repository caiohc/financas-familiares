# Requisitos Funcionais

Abaixo estão descritos os requisitos de negócios e as funcionalidades que a aplicação proverá para o usuário final.

## 1. Gestão de Transações
- A aplicação deve permitir o cadastro de transações de forma manual (receitas e despesas).
- A aplicação deve permitir a edição de transações previamente cadastradas ou importadas.

## 2. Importação de Dados Bancários
- O usuário poderá realizar o upload de extratos bancários e de cartão de crédito.
- A aplicação deve realizar a contabilização (importação e processamento) de todas as transações contidas nos extratos importados.

## 3. Classificação Automática e Inteligência Artificial
- A aplicação deve classificar as transações listadas nos extratos por categorias de receita e despesa. As taxonomias das **Categorias** (ex: Alimentação, Transporte) são globais e uniformes em toda a plataforma para todas as famílias.
- A aplicação poderá utilizar tecnologias de Inteligência Artificial para realizar o mapeamento e classificação das despesas.
- Se o documento importado for um PDF contendo imagens/escaneado, a aplicação integrará serviços de IA com capacidade de Visão Computacional / OCR para extrair digitalmente as despesas ali contidas.

## 5. Estrutura Organizacional e Multi-família
- A aplicação deve suportar **múltiplas famílias**, funcionando de forma isolada (multi-tenant). Os dados de uma família não se misturam com os de outra.
- Cada família pode possuir **múltiplos membros**.
- A aplicação diferencia o contexto de acesso do contexto financeiro: **Usuário** é a entidade do sistema utilizada estritamente para autenticação e autorização (gestão de credenciais). **Membro** é a entidade de domínio que compõe a família.
- Cada Membro pertence obrigatoriamente a uma única Família e é vinculado a um único Usuário do sistema.
- O controle financeiro (transações, receitas, despesas, orçamentos e relatórios) é realizado em nível de Família e manipulado de acordo com a visão dos seus Membros. 
- Cada Membro tem acesso aos dados consolidados de sua respectiva família provando sua identidade no sistema por meio de seu Usuário.

## 6. Instrumentos Financeiros e Orçamento
### Contas e Cartões
- **Composição do Orçamento:** Cada membro de uma família pode ter múltiplas contas bancárias e múltiplos cartões de crédito. Consequentemente, como o controle financeiro é gerido por família, múltiplas contas e cartões de crédito (dos diversos membros) podem e devem compor o orçamento conjunto e unificado de uma família.
- **Contas Bancárias:** Cada conta é obrigatoriamente associada a um membro (titular principal da conta).
- **Cartões de Crédito:** O "Cartão de Crédito", enquanto entidade principal que detém e controla o limite de crédito global, possui obrigatoriamente um titular único e responsável (membro da família).
- **Hierarquia de Cartões (Instâncias):** Um cartão de crédito pode ter múltiplas instâncias ("plásticos" ou cartões virtuais). O titular está na raiz, e dependentes podem ter suas próprias instâncias vinculadas ao titular.
- **Transações:** Podem ser executadas em uma conta bancária ou em uma instância de cartão de crédito.

### Receitas e Dinheiro em Espécie
- **Receitas:** Podem ser atreladas a um titular específico ou diretamente à família (receitas compartilhadas/inerentes à família).
- **Dinheiro em Espécie (Caixa):** A aplicação deve suportar o controle de valores em espécie. Recebimentos e pagamentos em dinheiro vivo devem ser registrados e associados ao caixa da família, permitindo o fluxo completo de transações fora do sistema bancário.
