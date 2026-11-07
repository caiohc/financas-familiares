# Documentação de Segurança — Contas, Acesso e Autenticação

Esta documentação descreve como o sistema protege o acesso e as contas das pessoas que o usam. Ela está dividida em duas partes.

- **Parte I (Seções 1 a 5), para quem usa o sistema.** As seções crescem em privilégio: cada uma assume que a pessoa já leu as anteriores. Para orientar alguém, entregue as seções **até** a do papel dela:

  | Papel da pessoa | Entregue as Seções |
  |---|---|
  | Usuário de família | 1 e 2 |
  | Administrador de família | 1, 2 e 3 |
  | Administrador do sistema | 1, 2, 3 e 4 |
  | Root | 1, 2, 3, 4 e 5 |

  Cada seção da Parte I é escrita em linguagem simples, sem termos técnicos.

- **Parte II (Seções 6 a 18), para quem desenvolve** (pessoa ou IA). Explica os mecanismos de segurança adotados, o que já está implementado e o que ainda está planejado.

> **Atenção ao estado de implementação.** A Parte I descreve o sistema com a funcionalidade de autenticação
> concluída. O que já está pronto no código, e o que ainda não, está na Seção 6.2. Em particular, o **envio real de
> e-mail (SMTP) ainda não existe**: em desenvolvimento a mensagem vai para o log do servidor, e em produção a
> aplicação ainda não sobe. Não entregue uma seção a um usuário antes de a funcionalidade que ela descreve estar
> disponível.

Última atualização: 08/11/2026.

---

# PARTE I — PARA QUEM USA O SISTEMA

---

## 1. Conceitos básicos (todos os papéis)

### 1.1 Sua conta é pessoal

Cada pessoa tem uma conta própria, formada por **nome de usuário**, **e-mail** e **senha**. A conta identifica quem fez cada coisa no sistema, por isso **nunca é compartilhada**: nem com o cônjuge, nem com um colega, nem com um administrador.

### 1.2 Os tipos de usuário

| Tipo | Para que serve |
|---|---|
| **Usuário de família** | Usa o sistema dentro de uma família. |
| **Administrador de família** | Também cuida do acesso das pessoas da sua família (Seção 3). |
| **Administrador do sistema** | Cuida das famílias e dos administradores (Seção 4). |
| **Root** | Acesso inicial do sistema, criado uma única vez na instalação (Seção 5). |

Quem é usuário de família ou administrador de família pertence a **uma** família. Administradores do sistema e o root não pertencem a nenhuma.

### 1.3 Ninguém se cadastra sozinho

Não existe tela de "criar conta". **Toda conta é criada por um administrador**, e a pessoa a ativa pelo próprio e-mail (Seção 2.1). Isso garante que só entra no sistema quem foi convidado.

### 1.4 Senhas

- Use **pelo menos 8 caracteres**. Quanto mais longa, melhor: uma frase com várias palavras é mais forte e mais fácil de lembrar do que uma sequência curta cheia de símbolos.
- Pode **colar** a senha, inclusive de um gerenciador de senhas. Ele é recomendado.
- Use uma senha **exclusiva** para este sistema, que você não use em nenhum outro lugar.
- Ao definir ou trocar a senha, digite-a **duas vezes**. O sistema só aceita se as duas forem idênticas. O botão com o desenho de um olho, ao lado do campo, mostra ou oculta o que foi digitado.
- Ninguém, nem administrador, nem o desenvolvedor do sistema, consegue ler a sua senha. Ela é guardada de forma que não pode ser desfeita.

### 1.5 Seu e-mail

Seu e-mail é **único**: nenhuma outra conta pode usar o mesmo. Ele é o canal pelo qual você recebe o convite para ativar a conta e as instruções para recuperar a senha. Quem controla o seu e-mail consegue recuperar a sua conta, então proteja a sua caixa de entrada com uma boa senha.

### 1.6 O código de ativação

Para ativar a conta você precisa de duas coisas, que chegam por **canais diferentes**:

- o **link** enviado ao seu e-mail;
- um **código** que o administrador lhe passa por outro meio (pessoalmente, telefone, mensagem etc.).

Só com as duas a ativação funciona. Quem tiver acesso apenas ao e-mail, ou apenas ao código, não consegue ativar a conta.

---

## 2. Usuário de família: o seu acesso no dia a dia

*Leitores: usuários de família. Pressupõe a Seção 1.*

### 2.1 Ativar a sua conta

1. O administrador cadastra você e informa o seu e-mail.
2. Você recebe um **e-mail com um link** e, por outro meio, o administrador lhe passa um **código**.
3. Abra o link. Na página, informe o **código** e escolha a **senha** (duas vezes, conforme a Seção 1.4).
4. Pronto: a conta está ativa e você já pode entrar.

Se algo der errado:

- **O link venceu.** Ele vale por **24 horas** e só funciona uma vez. Peça ao administrador um novo link; ele também
  gera um novo código, e o convite anterior deixa de valer.
- **Errou o código várias vezes.** Depois de **5 códigos errados** o convite é bloqueado, mesmo que você acerte em
  seguida. Peça um novo ao administrador.
- **Não recebeu o e-mail.** Confira a caixa de spam e confirme com o administrador se o endereço está correto. Enquanto
  a conta não for ativada, ele pode corrigir o e-mail e reenviar o convite.

### 2.2 Entrar no sistema

Informe o **nome de usuário ou o e-mail** e a senha. Se algo estiver errado, o sistema diz apenas **"Usuário ou senha
inválidos"**, sem informar qual dos dois falhou (nem se a conta existe, está pendente ou foi desativada). Isso é
proposital: protege contas de quem tenta descobrir quem usa o sistema.

Depois de **5 tentativas erradas em um minuto** para a mesma conta, o sistema faz você **esperar um pouco** antes de
tentar de novo, mesmo que você acerte a senha na tentativa seguinte. Também é proposital.

### 2.3 Sair do sistema

Use o botão **Sair** quando terminar, principalmente em computador ou celular compartilhado. Por segurança, o acesso
também **expira sozinho**: depois de **30 minutos sem uso**, e no máximo **8 horas** depois de você entrar, mesmo que
você continue usando. Quando isso acontece, é só entrar de novo.

### 2.4 Trocar a sua senha

Em qualquer momento você pode trocar a senha informando a **senha atual**, a **nova senha** (duas vezes). Ao trocar, **todos os outros acessos abertos com a senha antiga são encerrados** (por exemplo, um celular em que você esqueceu a conta aberta). Troque a senha sempre que suspeitar que alguém a conhece.

### 2.5 Esqueci minha senha

Disponível para **usuários de família e administradores de família que já ativaram a conta**. Quem já entrou uma vez
redefine a própria senha sozinho, sem depender de ninguém.

1. Na tela de entrada, escolha **"Esqueci minha senha"** e informe o seu e-mail.
2. A resposta é sempre a mesma, exista ou não uma conta com esse e-mail: *"Se o e-mail estiver cadastrado, enviamos as
   instruções."*
3. Se existir uma conta ativa, você recebe um **link de uso único que vale por 15 minutos**. Abra-o e escolha uma nova
   senha (duas vezes). Não há código nesse caso: o e-mail é a prova.
4. Você recebe um **aviso por e-mail** de que a senha foi alterada. Se não foi você, avise o administrador
   imediatamente.

Pedir o link muitas vezes seguidas é limitado (no máximo 3 por hora para o mesmo e-mail). Um pedido novo invalida o
link anterior.

**Administradores do sistema não usam esta opção**: a senha deles é redefinida por outro administrador do sistema
(Seção 4.3), com link e código. A recuperação só funciona para contas **já ativadas**.

### 2.6 O seu e-mail

- **Antes de ativar a conta**, só o administrador pode corrigir o e-mail, caso tenha sido cadastrado com erro.
- **Depois de ativar**, só **você** pode alterá-lo, pelo seu perfil. O sistema pede a **senha atual** e o novo e-mail **duas vezes**, e mostra uma janela para você conferir o endereço antes de salvar. O e-mail antigo recebe um aviso da mudança.

Nenhum administrador consegue alterar o seu e-mail depois que a sua conta foi ativada. Isso impede que alguém use a recuperação de senha para tomar a sua conta.

### 2.7 Conta desativada

Um administrador pode **desativar** a sua conta, por exemplo se você deixar a família. Com a conta desativada, não é possível entrar. Os dados que você registrou continuam no sistema. Se for um engano, fale com o administrador.

### 2.8 Boas práticas e sinais de alerta

- **Nunca informe a sua senha a ninguém.** Nenhum administrador e nenhuma mensagem legítima vai pedi-la.
- **O sistema nunca envia a sua senha por e-mail.** Qualquer mensagem que peça a senha é golpe.
- Informe o **código de ativação** apenas na página aberta pelo link recebido, nunca por e-mail nem mensagem.
- Receber um aviso de **troca de senha ou de e-mail que você não fez**: troque a senha, se ainda conseguir entrar, e avise o administrador.
- Em computador alheio, use sempre **Sair** ao terminar.

---

## 3. Administrador de família: o acesso das pessoas da sua família

*Leitores: administradores de família. Pressupõe as Seções 1 e 2.*

Além de tudo o que um usuário de família faz, você cuida do acesso das pessoas da **sua** família. Você só enxerga e age sobre usuários da sua própria família.

### 3.1 Cadastrar um usuário da família

Informe **nome**, **nome de usuário**, **e-mail** e o **tipo** (usuário de família ou administrador de família).

- O **e-mail é digitado duas vezes**, e os dois campos precisam ser idênticos. Pode colar.
- Antes de salvar, uma **janela pede que você confirme o endereço** de e-mail. Confira com cuidado: é para esse endereço que o convite será enviado.
- Você **não define senha**. A própria pessoa a escolhe ao ativar a conta.

Ao salvar, o sistema envia o convite por e-mail e **mostra um código de ativação uma única vez**. Anote-o e **repasse à pessoa por outro meio**, nunca no mesmo canal do convite: telefone, mensagem, pessoalmente. Depois de sair da tela, o código não pode ser visto de novo (se perder, gere outro; ver 3.2).

O usuário fica **pendente** até ativar a conta. Enquanto estiver pendente, não consegue entrar.

### 3.2 Usuários pendentes: reenviar e corrigir

Para um usuário que ainda não ativou a conta, você pode:

- **Reenviar a ativação:** gera um novo link e um novo código, e o convite anterior deixa de valer.
- **Corrigir o e-mail**, caso tenha sido digitado errado. Isso reenvia o convite ao endereço correto.

### 3.3 Quem esqueceu a senha

Você **não redefine** a senha de quem já ativou a conta, nem a de outro administrador de família: cada pessoa redefine
a própria em **"Esqueci minha senha"** (Seção 2.5), sem depender de você e sem que você precise conhecer ou escolher
nada. Para quem ainda **não ativou** a conta, o caminho é reenviar o convite (Seção 3.2).

### 3.4 Desativar um usuário

Desative a conta de quem deixou a família ou não deve mais ter acesso. A pessoa perde o acesso na hora, e os dados que registrou são mantidos.

### 3.5 O que você não pode fazer

- Ver ou escolher a senha de alguém, ou redefinir a senha de quem já ativou a conta.
- Alterar o e-mail de quem **já ativou** a conta.
- Cadastrar ou alterar administradores do sistema, o root, ou usuários de **outra** família. Para você, usuários de
  outras famílias simplesmente não existem.
- Desativar ou excluir a sua própria conta.

### 3.6 Nenhuma ação sua é silenciosa

Redefinir senha, desativar uma conta e outras ações sensíveis **geram aviso por e-mail** ao usuário afetado e ficam **registradas** com quem fez, o quê e quando. Isso protege também você: o registro mostra que a ação foi sua e foi legítima.

---

## 4. Administrador do sistema: famílias e administradores

*Leitores: administradores do sistema. Pressupõe as Seções 1, 2 e 3.*

Você não pertence a nenhuma família e cuida do acesso ao sistema como um todo. **É obrigatório informar o seu nome** na conta, porque, diferente do root, você é uma pessoa identificada.

### 4.1 Cadastrar usuários de qualquer família

Você faz o que o administrador de família faz (Seção 3), mas **em qualquer família**. Ao cadastrar o **primeiro administrador de uma família** nova, escolha o tipo "administrador de família": a partir daí, ele passa a cadastrar os demais usuários da própria família.

### 4.2 Cadastrar outro administrador do sistema

O cadastro segue o mesmo fluxo (e-mail em dois campos com confirmação, convite por e-mail, código por outro canal, Seção 3.1), sem escolher família.

### 4.3 Redefinir senhas e desativar contas

- **Outro administrador do sistema:** você pode redefinir a senha dele, e ele a sua. A redefinição usa o mesmo
  mecanismo da ativação: a senha atual deixa de valer na hora, a pessoa recebe um **link por e-mail** (24 horas) e você
  recebe um **código** para repassar por outro meio. Só administradores do sistema (e o root, Seção 5) podem iniciar
  esse fluxo para um administrador do sistema; administradores de família não.
- **Usuários de família já ativados:** você **não** redefine a senha deles. Cada um usa "Esqueci minha senha"
  (Seção 2.5). Para quem ainda não ativou a conta, reenvie o convite.
- **A sua própria senha:** nenhum administrador do sistema inicia a redefinição para si mesmo; se esquecer a senha,
  peça a outro administrador do sistema (ou ao root).
- **Desativar:** você pode desativar (e reativar) usuários de **qualquer** família e outros administradores do
  sistema, nunca a si mesmo nem o root.

### 4.4 O que você não pode fazer

- Alterar, desativar ou excluir o **root**.
- Ver ou escolher a senha de qualquer pessoa.
- Alterar o e-mail de quem **já ativou** a conta (Seção 2.6).

### 4.5 Responsabilidades

Sua conta tem o maior alcance entre as contas que pertencem a pessoas. Por isso:

- use uma senha **longa e exclusiva**, de preferência guardada em um gerenciador de senhas;
- nunca compartilhe a conta, mesmo com outro administrador;
- confira o e-mail do convite antes de confirmar (um endereço errado leva o convite a um desconhecido);
- ao notar uma ação suspeita, avise o root ou outro administrador e consulte os registros de ações sensíveis.

---

## 5. Root: o acesso inicial

*Leitores: quem instala e mantém o sistema. Pressupõe as Seções 1 a 4.*

O **root** é o acesso inicial do sistema. **Não representa uma pessoa**, por isso não tem nome nem família. Existe **um único** root.

### 5.1 O que o root faz

O root serve para **criar os primeiros administradores do sistema** e para emergências. Depois que existirem administradores do sistema, o uso do root deve ser raro. Ele **só administra administradores do sistema** (cadastrar e redefinir); não cuida de famílias nem de usuários de família.

### 5.2 Criar o root (uma única vez)

No servidor, execute:

```bash
uv run flask create-root
```

O comando pede o **nome de usuário**, o **e-mail** e a **senha** (digitada duas vezes, sem aparecer na tela). A senha precisa ter pelo menos 8 caracteres.

O root **não representa uma pessoa**: use para ele um e-mail só dele, **diferente do e-mail das contas pessoais** (nenhum e-mail pode repetir).

> **Quem é root e também usa o sistema como pessoa** (caso de quem desenvolve e administra): use um **alias** do mesmo
> provedor para o root. No Gmail, `nome+root@gmail.com` é, para o sistema, um endereço diferente (a unicidade continua
> valendo) e, para o Gmail, a mesma caixa de entrada. Confirme que o seu provedor aceita o `+`.

O comando avisa com clareza, em vermelho e dizendo o que fazer, quando algo impede a criação:

- **Já existe um root.** O sistema permite um único root, então um segundo não pode ser criado. O aviso vem **antes** de
  qualquer pergunta, não revela o nome nem o e-mail do root atual e indica os comandos de trocar a senha e o e-mail dele.
- **O nome de usuário ou o e-mail já estão cadastrados**, sem dizer a qual conta pertencem (revelar isso exporia quem tem conta no sistema). Se você
  digitou o valor, o comando pergunta de novo; se ele veio de uma opção da linha de comando, o comando termina.

### 5.3 Esqueci a senha do root

O root **não tem recuperação por e-mail**, de propósito: o e-mail do root é um alvo valioso para quem quiser tomar o sistema. A senha é redefinida **no servidor**, por quem tem acesso a ele:

```bash
uv run flask reset-root-password
```

Quem consegue executar o comando já tem acesso ao servidor e ao banco de dados, por isso esse é um canal confiável. Os
acessos abertos do root são encerrados.

### 5.4 Trocar o e-mail do root

Pela aplicação **ninguém** altera o e-mail do root (nem os administradores do sistema). Ele só muda no servidor:

```bash
uv run flask change-root-email
```

O comando mostra o e-mail atual, pede o novo e-mail **duas vezes** e recusa um endereço inválido, igual ao atual ou já
cadastrado (sem dizer de quem). A senha e o acesso do root não mudam.

### 5.5 Cuidados

- Guarde a senha do root em local seguro, separado do uso diário.
- O root **não pode ser excluído** pela aplicação.
- Quem tem acesso ao servidor tem, na prática, o controle do sistema. Restrinja esse acesso.

---

# PARTE II — PARA QUEM DESENVOLVE (PESSOA OU IA)

Esta parte explica **por que e como** a segurança é construída. Ela separa com clareza o que **já está implementado** do que está **planejado**. Material de apoio conceitual: `docs/tutorial_seguranca_autenticacao_autorizacao.md`.

---

## 6. Visão geral e estado de implementação

### 6.1 Princípios

1. **Negar por padrão e falhar fechado.** Uma rota nova nasce protegida; liberar é decisão explícita.
2. **Defesa em profundidade.** Regra no domínio, restrição no banco, validação no serviço e proteção na rota.
3. **Nunca confiar no cliente.** O que vem de formulário, URL ou cabeçalho é dado não confiável.
4. **Não inventar criptografia.** Bibliotecas consolidadas para sessão, CSRF, limites de tentativa, hash e tokens.
5. **Segredos nunca em código, log ou resposta.** Senhas, tokens e códigos não são registrados.
6. **Nenhuma ação sensível é silenciosa.** Avisa o usuário afetado e deixa registro.
7. **Administradores também são parte do modelo de ameaças.**

### 6.2 Estado de implementação

| Mecanismo | Estado |
|---|---|
| Papéis (`Role`) e invariantes de `User`; `CHECK` no banco (família/papel, nome, ciclo de vida da conta) | **Implementado** |
| Unicidade global de `username` e `email` (sem diferenciar caixa) | **Implementado** |
| Estados da conta: pendente, ativa, aguardando nova senha, desativada (`is_active`, `activated_at`) | **Implementado** |
| Cadastro sem senha: convite com link por e-mail + código por outro canal; tabela `user_invitations` | **Implementado** |
| Ativação (token + código, uso único, 24 h, 5 tentativas) e redefinição de administrador do sistema | **Implementado** |
| Recuperação autônoma de senha (família: link de 15 min, sem código) | **Implementado** |
| E-mail em dois campos no cadastro, com janela de confirmação | **Implementado** |
| Login/logout (Flask-Login), sessão com impressão digital da senha, 30 min de inatividade e 8 h absolutas | **Implementado** |
| Troca da própria senha (derruba as demais sessões e revoga links de recuperação pendentes) | **Implementado** |
| Proteção de rotas "negar por padrão" + teste que percorre todas as rotas | **Implementado** |
| CSRF (Flask-WTF) em todos os POST | **Implementado** |
| Limite de tentativas (Flask-Limiter): login, recuperação, definição de senha, troca de senha | **Implementado** (em memória: ver 10.5) |
| Argon2id atrás da porta de hash, com migração dos hashes antigos no login | **Implementado** |
| Cabeçalhos de segurança (`X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Cache-Control: no-store`) | **Implementado** |
| `APP_ENV`, `AUTH_ENABLED` e usuário de desenvolvimento; validação no startup; `APP_BASE_URL` | **Implementado** |
| Comandos `flask create-root`, `flask reset-root-password` e `flask change-root-email` | **Implementado** |
| Autorização das **contas** (quem cadastra, edita, convida, desativa, exclui; escopo por família) | **Implementado** |
| Desativação e reativação de usuário | **Implementado** |
| **Envio de e-mail por SMTP** (hoje só o envio para o log, em desenvolvimento) | **Pendente** (depende da escolha do provedor) |
| Troca do **próprio** e-mail (senha atual, dois campos, confirmação no endereço novo) | Planejado |
| Registro de auditoria e avisos por e-mail de ações administrativas | Planejado |
| Cabeçalhos CSP e HSTS (Flask-Talisman) | Planejado |
| Revogação de uma sessão copiada ao sair (ver 10.3) | Limitação conhecida |
| **Autorização** das demais operações (membros, centros de custo, contas financeiras...) | **Fora do escopo desta versão** (Seção 17) |

### 6.3 Onde cada peça fica

| Peça | Camada |
|---|---|
| `Role`, `User`, invariantes, política de senha | domínio (`src/domain/identity`) |
| `UserService`, DTOs, portas (`AbstractPasswordHasher`, futuras `AbstractEmailSender`) | aplicação (`src/application`) |
| Hasher, repositório, UoW, futuro envio de e-mail | infraestrutura (`src/infrastructure`) |
| Rotas, templates, Flask-Login, CSRF, limites | interface web (`src/interface/web`) |
| Comandos `flask create-root`, `reset-root-password` | interface CLI (`src/interface/cli`) |

O domínio e a aplicação **não importam Flask nem SQLAlchemy**. O acoplamento com Flask (sessão, cookies, decoradores) fica na interface web.

---

## 7. Modelo de identidade

### 7.1 Papéis e invariantes (implementado)

`Role`: `ROOT`, `SYSTEM_ADMIN`, `FAMILY_ADMIN`, `FAMILY_USER`. Invariantes validadas em `User.__post_init__` (`src/domain/identity/entities.py`):

- `family_id` é nulo **se e somente se** o papel é `ROOT` ou `SYSTEM_ADMIN`;
- `name` é obrigatório para todos, **exceto** `ROOT` (que não representa uma pessoa e pode ter nome nulo);
- `username` e `email` são obrigatórios e aparados;
- o usuário **não tem relação com `Member`**: pode nem pertencer à família na vida real.

As mesmas regras valem no banco como `CHECK` (`ck_users_role_family`, `ck_users_name_required`), como rede de segurança contra um bug na aplicação.

### 7.2 Unicidade

Índices únicos de expressão (`ix_users_username_lower`, `ix_users_email_lower`): `username` e `email` são únicos **globalmente** (não por família) e **sem diferenciar maiúsculas de minúsculas**. O repositório converte colisão em `EntityAlreadyExistsError`, descobrindo qual campo colidiu.

**As mensagens de conflito não revelam de quem é o valor.** Nome de usuário ou e-mail repetido produz apenas "já está
cadastrado no sistema", sem citar a conta que o usa (isso exporia quem tem acesso). Vale para o cadastro pela
aplicação e para os três comandos de CLI. A senha nunca é conferida contra as de outras contas.

> **Cuidado em migrações no SQLite.** O `batch_alter_table` recria a tabela e **perde índices de expressão em silêncio** (o SQLAlchemy não os reflete). Toda migração que altere `users` deve derrubar e recriar esses índices, como faz a `4b7c1e9a2d55`, e deve ser testada em `upgrade`, `downgrade` e `upgrade`.

### 7.3 Mass assignment

`UpdateUserDTO` contém só `name`, `username` e `email`. Papel, família e senha **nunca** são alterados pelo CRUD de edição, e há teste garantindo que a rota ignora esses campos se vierem no POST.

### 7.4 Estados da conta (implementado)

```
PENDENTE  --(ativação: link + código)-->  ATIVA  --(redefinição por administrador do sistema)-->  AGUARDANDO NOVA SENHA
                                           ^                                                            |
                                           +----------------(link + código)----------------------------+

qualquer estágio  --(desativação)-->  DESATIVADA  --(reativação)-->  o estágio anterior
```

- `PENDENTE` (`password_hash` e `activated_at` nulos): criada sem senha; não autentica; o e-mail ainda **não é
  confiável** e o administrador pode corrigi-lo.
- `ATIVA`: tem senha; autentica; o e-mail passou a ser confiável (a ativação provou o controle da caixa) e só o próprio
  usuário poderá alterá-lo.
- `AGUARDANDO NOVA SENHA` (`password_hash` nulo, `activated_at` preenchido): a senha antiga foi revogada por uma
  redefinição de administrador do sistema; não autentica até a pessoa definir outra. O e-mail continua travado.
- `DESATIVADA` (`is_active` falso): não autentica; as sessões abertas caem na requisição seguinte; os dados são
  preservados; não recebe convite nem recuperação.

Invariantes no domínio **e** no banco: quem tem senha tem data de ativação; o **root sempre tem senha** e não pode ser
desativado.

## 8. Senhas

### 8.1 Hash (implementado)

O hash fica atrás de `AbstractPasswordHasher` (`hash`, `verify`, `needs_rehash`, `dummy_hash`), implementada por
`Argon2PasswordHasher` (`argon2-cffi`, **Argon2id**, a primeira recomendação do OWASP). Hashes antigos (scrypt/PBKDF2
do Werkzeug) continuam sendo aceitos na conferência e são **regravados em Argon2id** no próximo login bem-sucedido.
Um hash corrompido ou de método desconhecido vale como "senha que não confere": nunca vira erro 500 no login.

### 8.2 Política

- Mínimo de **8 caracteres** (`MIN_PASSWORD_LENGTH`), aplicado à senha em texto **antes** do hash.
- **Sem regras de composição** (maiúscula, símbolo) e **sem expiração periódica**, conforme o NIST SP 800-63B.
- **Colar é permitido** nos campos de senha (gerenciadores de senha).
- A senha **não é aparada** (espaços fazem parte dela).
- A confirmação em dois campos é validada **no serviço** (`User.validate_password_confirmation`), não só na tela. A comparação é exata.
- Futuro desejável: bloquear senhas comuns ou vazadas.

### 8.3 Regras de manuseio

- A resposta de serviço (`UserResponseDTO`) **nunca** inclui o hash.
- Senhas, hashes, tokens e códigos **não são registrados em log** nem ecoados de volta ao formulário.
- Comparação de segredos com `hmac.compare_digest`; geração de aleatórios com `secrets`, nunca `random`.

---

## 9. Convites: ativação e redefinição por link e código (implementado)

Decisão de projeto: o administrador **nunca define nem conhece** a senha de outra pessoa. A pessoa a escolhe por um
convite, e a prova exige **dois canais independentes**.

### 9.1 Fluxo de ativação

1. O administrador cadastra o usuário (sem senha). A conta nasce `PENDENTE`.
2. O sistema gera um **token** (enviado por **e-mail**, num link) e um **código** (mostrado **uma única vez** ao
   administrador, que o repassa por **outro canal**).
3. A pessoa abre o link, informa o **código** e define a senha (dois campos).
4. Com token **e** código válidos, o sistema grava o hash, ativa a conta, consome o convite e a pessoa entra com a nova
   senha. Uma senha inválida (curta, confirmação diferente) **não gasta** tentativa do código nem o convite.

### 9.2 Requisitos do token e do código

| Item | Como é |
|---|---|
| Token | `secrets.token_urlsafe(32)` (256 bits); só o **SHA-256** fica gravado |
| Código | 8 caracteres de um alfabeto sem ambiguidade (sem 0/O, 1/I/L), exibido como `ABCD-EFGH`; só o **hash Argon2id** fica gravado; ao digitar, aceita minúsculas, espaços e hífen |
| Validade | **24 horas** (ativação e redefinição de administrador); **15 minutos** (recuperação) |
| Uso | **Único**, consumido por um `UPDATE` condicional atômico |
| Tentativas | **5** códigos errados bloqueiam o convite (o contador é incrementado pelo banco e gravado mesmo na falha) |
| Reemissão | Emitir um convite novo **revoga** o anterior; um só convite ativo por usuário |
| Mensagem de erro | Sempre a mesma ("Convite ou código inválido, expirado ou já utilizado"), seja token inexistente, vencido, usado, revogado ou código errado |
| Página do link | Não revela nada sobre o usuário (nome, e-mail, papel) |
| Registro | Nunca em log (exceto o envio de desenvolvimento) nem em redirecionamento; o código não vai no e-mail |

### 9.3 Quem pode iniciar um convite

| Alvo | Quem pode |
|---|---|
| Conta **pendente** de usuário de família ou administrador de família | `FAMILY_ADMIN` da **mesma família** ou qualquer `SYSTEM_ADMIN` |
| Conta **pendente** de administrador do sistema | `SYSTEM_ADMIN` ou `ROOT` |
| **Redefinição** de administrador do sistema já ativo | outro `SYSTEM_ADMIN` ou o `ROOT` (a senha antiga deixa de valer **na hora**) |
| Usuário/administrador de família **já ativado** | **ninguém**: redefine a própria senha em "Esqueci minha senha" (recuperação autônoma) |
| `ROOT` | ninguém pela aplicação; usa `flask reset-root-password` |

Ninguém inicia um convite **para si mesmo**. O `ROOT` é, ele próprio, um administrador do sistema: por isso cadastra
outros administradores do sistema e inicia a ativação e a redefinição de senha deles (decidido).

### 9.4 Tabela `user_invitations`

| Coluna | Função |
|---|---|
| `id`, `user_id` | identificador e usuário-alvo (chave estrangeira, `ON DELETE CASCADE`) |
| `purpose` | `ACTIVATION`, `ADMIN_RESET` ou `RECOVERY` |
| `token_hash` | SHA-256 do token; índice único |
| `code_hash` | hash do código; **nulo na recuperação** (`CHECK` por finalidade) |
| `created_by_user_id`, `created_at` | quem emitiu (só informativo, sem chave estrangeira) e quando |
| `expires_at`, `attempts` | validade e tentativas erradas |
| `consumed_at`, `revoked_at` | uso único e revogação |

Um **índice único parcial** garante no máximo um convite ativo (nem consumido, nem revogado) por usuário. Excluir o
usuário apaga os convites dele (o serviço os remove antes de checar dependências, porque as chaves estrangeiras os
contariam como dependência).

### 9.5 Quando um convite deixa de valer

Ao vencer, ao ser usado, ao ser revogado por outro convite, ao exceder as tentativas, quando a conta é **desativada ou
excluída** e quando o próprio usuário **troca a senha** (um link de recuperação enviado antes morre).

## 10. Autenticação e sessão (implementado)

### 10.1 Pilha

| Necessidade | Biblioteca |
|---|---|
| Sessão e proteção de rotas | **Flask-Login** (o `User` de domínio **não** herda de `UserMixin`; `SessionUser`, na camada web, faz a ponte; **um** `LoginManager` por aplicação) |
| CSRF | **Flask-WTF** (`CSRFProtect`) |
| Limite de tentativas | **Flask-Limiter** |
| Hash de senha | **argon2-cffi**, atrás da porta |
| E-mail (formato) | **email-validator** (sem consulta de DNS) |

Nada de código criptográfico próprio.

### 10.2 Login

- Identificador: **nome de usuário ou e-mail** (únicos, sem diferenciar caixa).
- Erro **genérico** sempre ("Usuário ou senha inválidos"): usuário inexistente, senha errada, conta pendente,
  desativada ou aguardando nova senha são indistinguíveis.
- **Tempo equalizado**: sem usuário (ou sem senha), confere-se um hash falso, para o tempo não denunciar a conta.
- Só autentica conta ativa **e** com senha.
- Ao autenticar, a sessão é **recriada** (`session.clear()` antes de gravar o usuário): sem fixação de sessão.
- O parâmetro `next` é **validado** (só caminhos relativos do próprio site; rejeita `//host`, `/\host`, esquemas,
  quebras de linha), contra redirecionamento aberto.
- Logout só por **POST** (com CSRF); `GET` devolve 405.

### 10.3 Sessão

- Cookie assinado (não criptografado), `HttpOnly`, `SameSite=Lax`, `Secure` (obrigatório em produção), com validade.
- O cookie guarda `id:versão`, onde a versão é um **HMAC da senha atual** com a `SECRET_KEY`. O usuário é **recarregado do
  banco a cada requisição**: trocar a senha, redefini-la, desativar ou excluir o usuário derruba as sessões abertas.
- **Prazos decididos:** **30 minutos sem uso** (o cookie é renovado a cada requisição) e **8 horas absolutas** desde o
  login (`login_at` na sessão, conferido a cada requisição; ausente ou inválido vale como expirado).
- **Limitação conhecida:** como o estado vive no cookie assinado, o logout apaga o cookie do navegador, mas um cookie
  **copiado antes** continua válido até expirar ou até a senha mudar / a conta ser desativada. Mitigações atuais: prazos
  curtos, `HttpOnly`, HTTPS obrigatório em produção. Há um teste `xfail` (estrito) que registra essa limitação.

### 10.4 Proteção de rotas: negar por padrão

Um `before_request` exige login em **toda** rota, exceto a lista explícita de rotas públicas (entrar, definir a senha
pelo convite, recuperar a senha e os estáticos). Um teste percorre `app.url_map`, exige que cada rota fora da lista
redirecione o visitante anônimo ao login e fixa a lista de públicas: uma rota nova sem proteção, ou uma pública nova
sem decisão registrada, quebra a suíte. A área de **usuários** exige ainda um papel de administrador (usuário de
família comum recebe 403).

### 10.5 Limite de tentativas e CSRF

- **CSRF:** todo POST exige o token da sessão (formulários e `X-CSRFToken`); o teste percorre todos os POST.
- **Limites (por minuto, salvo indicação):** login 5 por conta e 30 por endereço; recuperação 3 por hora por e-mail e 10
  por hora por endereço; definir senha pelo convite 10 por endereço e 20 por hora por link; redefinir pela recuperação 10
  por hora; trocar a própria senha 5 por usuário. A chave por conta ignora caixa e espaços.
- O armazenamento é **em memória** (vale por processo). Com vários processos, usar Redis. Bloquear por conta permite que
  alguém atrapalhe o login de outra pessoa por um minuto; é o preço de não bloquear definitivamente.

### 10.6 Cabeçalhos

Em toda resposta: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` (os links
de convite e recuperação trazem o token na URL) e, fora dos estáticos, `Cache-Control: no-store`. CSP e HSTS ficam para a
fase de endurecimento (Flask-Talisman). O CSP estrito exigirá mover o script inline do menu lateral para um arquivo.

### 10.7 Links por e-mail e o cabeçalho Host

Os links usam `APP_BASE_URL` (obrigatória em produção, `https://`). Sem ela, só em desenvolvimento, usam o cabeçalho
`Host` da requisição, que quem pede controla: um atacante poderia pedir a recuperação da senha de uma vítima com um `Host`
forjado e fazer o e-mail legítimo apontar para o site dele. Há teste desse ataque.

## 11. E-mail do usuário

O e-mail é a **chave-mestra** da conta, porque a recuperação o usa como "senha de reserva". Por isso é tratado como dado
sensível.

### 11.1 Regras

1. **Cadastro (implementado):** o e-mail é informado em **dois campos**, comparados **no serviço** (sem diferenciar caixa
   nem espaços nas pontas); **colar é permitido**; antes de salvar, uma **janela de confirmação** mostra o endereço
   (`<dialog>`, `email_confirm.js`; sem suporte do navegador, o formulário segue e o servidor valida do mesmo jeito).
2. **Formato e normalização (implementado):** `email-validator` (não expressão regular própria), domínio em minúsculas,
   unicidade sem diferenciar caixa. `+etiquetas` são mantidas como digitadas. Caracteres Unicode parecidos: decisão em
   aberto (Seção 18).
3. **Antes da ativação (implementado):** o administrador (inclusive de família) pode **corrigir** o e-mail.
4. **Depois da ativação (implementado):** **nenhum administrador altera mais o e-mail**; a tela de edição o mostra como
   somente leitura. Vale também para a conta aguardando nova senha.
5. **Troca do próprio e-mail (planejada):** senha atual, novo e-mail em dois campos, janela de confirmação, aviso ao
   endereço antigo e, com SMTP, confirmação por link no endereço novo.
6. **Recuperação por e-mail (implementada):** só para conta **ativada, ativa e com senha**, de **usuário ou administrador
   de família**. Um e-mail de conta pendente é só o que o administrador digitou e pode estar errado.
7. **`ROOT` e administradores do sistema** ficam fora da recuperação por e-mail (o root usa o CLI; o administrador do
   sistema, outro administrador).

### 11.2 Recuperação de senha

Convite do tipo `RECOVERY` (Seção 9): link de uso único, **15 minutos**, sem código. A resposta ao pedido é **sempre a
mesma** (existindo ou não conta elegível, inclusive para e-mails inválidos), com limite por endereço e por e-mail contra
*e-mail bombing*. Concluída a recuperação, a pessoa recebe o aviso de senha alterada e as sessões antigas caem. A senha
escolhida é definitiva.

> **Canal lateral conhecido:** quando a conta é elegível o servidor envia um e-mail, o que leva mais tempo do que não
> enviar. Com o SMTP real, o envio deve ir para uma fila/tarefa em segundo plano para igualar a resposta.

## 12. Configuração de ambiente e proteção de rotas (implementado)

### 12.1 Variáveis

| Variável | Papel | Valor padrão |
|---|---|---|
| `SECRET_KEY` | assina o cookie de sessão e a versão da credencial; trocá-la derruba todas as sessões | **obrigatória** |
| `APP_ENV` | `development` ou `production` | **obrigatória, sem padrão** |
| `AUTH_ENABLED` | `true` ou `false` (só `false` em `development`) | **obrigatória, sem padrão** |
| `DEV_AUTO_LOGIN_USERNAME` | usuário com o qual a aplicação autentica sozinha quando `AUTH_ENABLED=false` | obrigatória nesse caso |
| `APP_BASE_URL` | endereço público para os links de e-mail (`https://...`) | obrigatória em produção |
| `EMAIL_BACKEND` | `log` (desenvolvimento) ou `smtp` (ainda não implementado) | `log` |
| `SESSION_COOKIE_SECURE` | cookie só por HTTPS | `false` (obrigatória `true` em produção) |
| `FLASK_DEBUG` | depurador do Flask (não define "produção") | **`false`** |
| `SQL_ECHO` | mostra todo o SQL no terminal (separado do `FLASK_DEBUG`: ligado junto, enterrava as mensagens dos comandos de CLI) | **`false`** |

`DATABASE_URI` continua obrigatória. Há um modelo comentado em `.env.example`.

### 12.2 Validação no startup (falha fechada)

`validate_security_config`, chamada uma única vez em `create_app`, junta **todos** os problemas e impede a subida:
variável ausente ou inválida; `AUTH_ENABLED=false` fora de `development` ou sem `DEV_AUTO_LOGIN_USERNAME`; e, em
`production`: `AUTH_ENABLED` diferente de `true`, `DEBUG` ligado, `SECRET_KEY` com menos de 32 caracteres, cookie sem
`Secure`, `EMAIL_BACKEND` diferente de `smtp` ou `APP_BASE_URL` sem `https://`. Como o SMTP ainda não existe,
**hoje a aplicação não sobe em produção**, de propósito.

### 12.3 Proteção desligada em desenvolvimento

Com `AUTH_ENABLED=false`, a aplicação **autentica sozinha como o usuário configurado** (`request_loader`), em vez de ficar
sem identidade. A autorização continua valendo, porque há um usuário de verdade por trás: configurar um administrador de
família mostra a tela como ele a veria. Garantias: o cliente não escolhe o usuário (cabeçalhos, parâmetros e cookies são
ignorados); sem o usuário (inexistente, desativado ou pendente) ninguém entra; o carregador é **por aplicação** e confere
`AUTH_ENABLED` em tempo de execução, então um app seguro criado no mesmo processo nunca o herda; há **aviso no log** na
subida e **faixa em todas as telas**. Não se usa `LOGIN_DISABLED` do Flask-Login (deixaria `current_user` anônimo).

### 12.4 Testes

Os testes de CRUD usam `AUTH_ENABLED=false` com um usuário de desenvolvimento. Os testes de **segurança** (`tests/security`)
sempre usam a proteção **ligada**.

## 13. Comandos de CLI (implementado)

Os três comandos rodam no servidor, por quem tem acesso a ele: é o único caminho para mexer no root, que está fora da
recuperação por e-mail e do alcance dos administradores. Em comum: mensagens de erro em vermelho, sem traceback, dizendo o
que fazer a seguir; valores que faltam são perguntados; um valor inválido ou em uso é explicado e perguntado de novo (se
veio de uma opção, o comando termina com código 1, porque repetir não adiantaria).

### 13.1 `flask create-root`

- **Antes de perguntar qualquer coisa**, recusa se já existe um root, citando-o e indicando `reset-root-password` e
  `change-root-email`.
- Pergunta (ou recebe por `--username`/`--email`) o nome de usuário e o e-mail e **confere na hora** se estão livres: o aviso
  diz que o nome já está em uso, ou qual conta usa o e-mail. Só então pede a senha (`hide_input`, com confirmação; o serviço
  confere a confirmação de novo).
- Cria o `ROOT` **ativado**, sem nome e sem família, com a senha escolhida no terminal (não há senha temporária).
- O root **não** é criável nem excluível pelo CRUD.

### 13.2 `flask reset-root-password`

Redefine a senha do root (nova senha com confirmação; senha curta é explicada e perguntada de novo). Derruba as sessões
abertas do root. Se ainda não houver root, avisa e indica `flask create-root`, sem perguntar a senha.

### 13.3 `flask change-root-email`

Mostra o e-mail atual, pede o novo **duas vezes** (se a confirmação não confere, refaz os dois campos) e recusa endereço
inválido, igual ao atual ou já cadastrado (sem revelar de quem). Não altera senha, nem sessões, nem as outras contas. É a
única forma de trocar o e-mail do root: a trava de e-mail pós-ativação vale para a edição administrativa, não para a CLI.

## 14. Defesas nas demais camadas (implementado)

| Ameaça | Defesa |
|---|---|
| XSS | Autoescape do Jinja; o realce de pesquisa escapa o texto antes de marcar (há testes de injeção de HTML) |
| Injeção de SQL | Somente consultas parametrizadas (SQLAlchemy); curingas de `LIKE` (`%`, `_`, `\`) do termo de pesquisa são tratados como texto; o campo de ordenação é validado contra uma lista |
| Mass assignment | DTOs com campos explícitos (a edição só recebe nome, usuário e e-mail; o cadastro ignora campos de senha) |
| Vazamento de dados | `UserResponseDTO` e `SessionUserDTO` sem `password_hash`; a listagem nunca renderiza hash nem código |
| Enumeração de contas | Erros genéricos, tempo equalizado, resposta única da recuperação, usuário de outra família = "não encontrado" |
| Escalada de privilégio | Política de contas no domínio, aplicada no serviço; ator vem **da sessão**, nunca do formulário; administrador de família sem família é negado por inteiro |
| CSRF, clickjacking, referer, cache | Seção 10 |
| Segredo ausente ou fraco | Validação no startup (Seção 12.2) |
| Eco de senha | Em erro de formulário, nenhuma senha volta para a página |
| Hash legado corrompido | Vale como "não confere"; nunca erro 500 |

Planejado: CSP e HSTS (Flask-Talisman).

## 15. Auditoria e avisos (planejado)

Registro **somente de inclusão** (append-only) de eventos de segurança, com data, ator, alvo, ação e IP, **sem segredos**:

- login com sucesso e falha, bloqueios por excesso de tentativas;
- ativação, troca e redefinição de senha (e quem redefiniu);
- criação, desativação, reativação e exclusão de usuário;
- alteração de e-mail.

Ações sensíveis feitas por administrador **avisam o usuário afetado por e-mail**.

---

## 16. Testes de segurança

A suíte de segurança vive em `tests/security` (pilha real: serviços, banco, Argon2 leve, Flask-Login, CSRF, limites e um
servidor de e-mail falso para ler os links) e nos testes de domínio, de serviço e de infraestrutura.

- **Negar por padrão:** percorre todas as rotas e confere o redirecionamento ao login; fixa a lista de rotas públicas.
- **Login e sessão:** erro idêntico para toda falha; injeção; `next` malicioso (12 variações); fixação de sessão; cookie
  adulterado, forjado ou de outra chave; marcas `HttpOnly`/`SameSite`/`Secure`; prazos de 30 min e 8 h (inclusive carimbo
  ausente ou lixo); queda da sessão ao trocar a senha, desativar ou excluir; **`xfail` estrito** da limitação do logout.
- **CSRF:** todos os POST sem token (anônimo e logado), token de outra sessão, lixo, formulários renderizados com token,
  ataque forjado sem efeito.
- **Limites:** login, recuperação, definição de senha e troca de senha; conta bloqueada recusa até a senha certa.
- **Convites:** código errado em série e bloqueio, convite vencido/usado/revogado/trocado de finalidade, link de outra
  pessoa, token e código isolados, mesma página para todo link morto, nada em texto puro no banco.
- **Autorização:** matriz de papéis (domínio), tentativas de escalada, acesso cruzado entre famílias (404 idêntico ao de um
  usuário inexistente), usuário comum na área de usuários, root intocável, administrador de família sem família.
- **Recuperação:** resposta idêntica para qualquer tipo de conta, só família elegível, 15 minutos, uso único, sessões antigas
  caem, link morre ao trocar a senha ou desativar.
- **Links e Host:** envenenamento do cabeçalho `Host` com e sem `APP_BASE_URL`.
- **Modo de desenvolvimento:** o cliente não escolhe o usuário; sem usuário ninguém entra; carregador não vaza para outro app.
- **Configuração:** cada exigência de produção, uma por vez; o app recusa subir.
- **Comandos de CLI** (`tests/e2e/test_root_cli.py`): recusa do segundo root antes de qualquer pergunta, perguntas de novo
  para valor digitado inválido ou em uso, término com código 1 para valor vindo de opção, troca de senha e de e-mail,
  eco de SQL independente do `FLASK_DEBUG` e mensagens que não nomeiam a conta dona de um nome ou e-mail.
- **Infraestrutura:** `CHECK`s do banco, índice único parcial de convite ativo, consumo atômico, hasher (inclusive hash legado
  e corrompido).

**Ainda a escrever, quando o SMTP existir:** testes do remetente SMTP (entrega, falha, TLS, timeout) e a igualdade de tempo
entre pedidos de recuperação elegíveis e inelegíveis.

## 17. Autorização

**Implementada, para as contas:** `domain/identity/policy.py` (funções puras) decide quem cadastra, vê, edita, convida,
desativa e exclui contas; o `UserService` a aplica a toda operação, recebendo o `Principal` da sessão; o repositório
filtra a listagem pela família do administrador de família (escopo do tenant). A área de usuários exige um papel de
administrador.

**Fora do escopo desta versão:** a autorização das demais operações (membros, centros de custo, contas financeiras,
transações...). Hoje essas telas exigem apenas **login**. Quando forem especificadas, partirão de que a Família é o tenant
e de que toda consulta de dados financeiros deve ser escopada por `family_id` vindo da sessão, nunca de formulário.

## 18. Decisões em aberto e pendências

| Tema | Situação |
|---|---|
| **Provedor de e-mail (SMTP)** | Em discussão. Pendentes: `SmtpEmailSender`, seus testes, e o envio em segundo plano (canal lateral de tempo). Até lá, `EMAIL_BACKEND=log` só em desenvolvimento e produção não sobe |
| Troca do **próprio** e-mail | Planejada; colar no segundo campo a definir |
| Revogação de sessão copiada no logout | Limitação conhecida; exigiria estado no servidor (por exemplo, época de sessão por usuário) |
| Armazenamento do limite de tentativas | Em memória; usar Redis com vários processos |
| Caracteres Unicode parecidos em e-mails | A definir (só ASCII ou confiar na normalização) |
| Auditoria e avisos por e-mail de ações administrativas | Planejados |
| CSP e HSTS (Flask-Talisman) | Planejados (exige mover o script inline do menu) |
| Usuário de família que perdeu o acesso ao próprio e-mail | Sem saída automática: hoje só excluir e recadastrar; a troca do próprio e-mail (acima) ajuda enquanto ele ainda entra |

## Regras para quem altera código de segurança (pessoa ou IA)

1. Não enfraqueça uma proteção para "fazer um teste passar". Corrija a causa ou ajuste o teste com justificativa.
2. Não implemente criptografia, geração de tokens ou comparação de segredos à mão: use `secrets`, `hmac.compare_digest` e as bibliotecas da Seção 10.1.
3. Nunca registre, ecoe ou devolva senhas, hashes, tokens ou códigos.
4. Uma rota nova nasce protegida. Se ela precisar ser pública, declare-a explicitamente e justifique.
5. Mutação só por `POST`, com CSRF.
6. Mensagens de erro de autenticação são **genéricas**; nada que revele se um usuário ou e-mail existe.
7. Mudanças de esquema em `users` seguem o cuidado da Seção 7.2.
8. Respeite as camadas: domínio e aplicação sem Flask nem SQLAlchemy.
9. Mudanças de comportamento de segurança (papéis, fluxos de credencial, regras de e-mail) são **propostas e confirmadas** antes de implementadas.
10. Atualize esta documentação e a tabela da Seção 6.2 junto com o código.
