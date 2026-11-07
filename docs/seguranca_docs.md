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

> **Atenção ao estado de implementação.** A Parte I descreve o comportamento do sistema com a funcionalidade de autenticação concluída. Hoje parte dela ainda não existe; a Seção 6.2 diz exatamente o que já está pronto. Não entregue uma seção a um usuário antes de a funcionalidade que ela descreve estar disponível.

Última atualização: 07/11/2026.

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

- **O link venceu.** Ele tem validade limitada e só funciona uma vez. Peça ao administrador um novo link; ele também gera um novo código.
- **Errou o código várias vezes.** Por segurança, o código é bloqueado depois de algumas tentativas erradas. Peça um novo ao administrador.
- **Não recebeu o e-mail.** Confira a caixa de spam e confirme com o administrador se o endereço está correto. Enquanto a conta não for ativada, ele pode corrigir o e-mail e reenviar o convite.

### 2.2 Entrar no sistema

Informe o **nome de usuário ou o e-mail** e a senha. Se algo estiver errado, o sistema diz apenas **"Usuário ou senha inválidos"**, sem informar qual dos dois falhou. Isso é proposital: protege contas de quem tenta descobrir quem usa o sistema.

Depois de várias tentativas erradas em sequência, o sistema faz você **esperar um pouco** antes de tentar de novo. Também é proposital.

### 2.3 Sair do sistema

Use o botão **Sair** quando terminar, principalmente em computador ou celular compartilhado. Por segurança, o acesso também **expira sozinho** depois de um tempo sem uso, e você precisará entrar de novo.

### 2.4 Trocar a sua senha

Em qualquer momento você pode trocar a senha informando a **senha atual**, a **nova senha** (duas vezes). Ao trocar, **todos os outros acessos abertos com a senha antiga são encerrados** (por exemplo, um celular em que você esqueceu a conta aberta). Troque a senha sempre que suspeitar que alguém a conhece.

### 2.5 Esqueci minha senha

1. Na tela de entrada, escolha **"Esqueci minha senha"** e informe o seu e-mail.
2. A resposta é sempre a mesma, exista ou não uma conta com esse e-mail: *"Se o e-mail estiver cadastrado, enviamos as instruções."*
3. Se existir uma conta ativa, você recebe um **link de uso único e de validade curta**. Abra-o e escolha uma nova senha (duas vezes).
4. Você recebe um **aviso por e-mail** de que a senha foi alterada. Se não foi você, avise o administrador imediatamente.

A recuperação só funciona para contas **já ativadas**.

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

### 3.3 Redefinir a senha de um usuário da família

Se alguém da sua família esqueceu a senha e não consegue recuperá-la, você pode **redefinir** a senha dessa pessoa, **inclusive de outro administrador de família**. Para a sua própria senha, use **"Esqueci minha senha"** (Seção 2.5). Você **não escolhe nem vê** a nova senha: o sistema envia à pessoa um novo link e um novo código, no mesmo formato da ativação (Seção 3.1), e ela escolhe a senha. A senha antiga deixa de valer imediatamente e os acessos abertos são encerrados.

### 3.4 Desativar um usuário

Desative a conta de quem deixou a família ou não deve mais ter acesso. A pessoa perde o acesso na hora, e os dados que registrou são mantidos.

### 3.5 O que você não pode fazer

- Ver ou escolher a senha de alguém.
- Alterar o e-mail de quem **já ativou** a conta.
- Cadastrar ou alterar administradores do sistema, o root, ou usuários de **outra** família.

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

Você pode redefinir a senha (Seção 3.3) e desativar (Seção 3.4) usuários de **qualquer** família. Pode também redefinir a senha de **outro administrador do sistema**, e ele a sua. Esse é um fluxo reservado a administradores do sistema (e ao root, Seção 5): administradores de família não o disparam para você. Para a sua própria senha, o caminho é **"Esqueci minha senha"** (Seção 2.5).

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

O comando pede o **nome de usuário**, o **e-mail** e a **senha** (digitada duas vezes, sem aparecer na tela). A senha precisa ter pelo menos 8 caracteres. Se já existir um root, o comando se recusa a criar outro.

### 5.3 Esqueci a senha do root

O root **não tem recuperação por e-mail**, de propósito: o e-mail do root é um alvo valioso para quem quiser tomar o sistema. A senha é redefinida **no servidor**, por quem tem acesso a ele:

```bash
uv run flask reset-root-password
```

Quem consegue executar o comando já tem acesso ao servidor e ao banco de dados, por isso esse é um canal confiável.

### 5.4 Cuidados

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
| Papéis (`Role`) e invariantes de `User` no domínio | **Implementado** |
| `CHECK` no banco para família/papel e nome obrigatório | **Implementado** |
| Unicidade global de `username` e `email` (sem diferenciar caixa) | **Implementado** |
| Hash de senha atrás de porta (`AbstractPasswordHasher`), com scrypt (Werkzeug) | **Implementado** |
| Política mínima de senha (8 caracteres) e confirmação em dois campos no serviço | **Implementado** (hoje no cadastro; será movido para a ativação, Seção 9) |
| Comando `flask create-root` | **Implementado** |
| CRUD de usuário (sem edição de senha, papel ou família) | **Implementado** (sem proteção de rotas) |
| `SECRET_KEY` obrigatória no startup | **Implementado** |
| Defesas de camada: escape de HTML, SQL parametrizado, escape de `LIKE`, DTOs restritos | **Implementado** |
| Cadastro sem senha, ativação por link e código | Planejado |
| Login, logout e sessão (Flask-Login) | Planejado |
| CSRF (Flask-WTF) e limite de tentativas (Flask-Limiter) | Planejado |
| Argon2id no lugar do scrypt | Planejado |
| Troca de senha, recuperação por e-mail, troca do próprio e-mail | Planejado |
| Desativação de usuário (`is_active`) | Planejado |
| `flask reset-root-password` | Planejado |
| Variáveis `APP_ENV` e `AUTH_ENABLED` e usuário de desenvolvimento | Planejado |
| Avisos por e-mail e registro de auditoria | Planejado |
| **Autorização** (papéis e escopo por família nas operações) | **Fora do escopo desta versão** (Seção 17) |

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

> **Cuidado em migrações no SQLite.** O `batch_alter_table` recria a tabela e **perde índices de expressão em silêncio** (o SQLAlchemy não os reflete). Toda migração que altere `users` deve derrubar e recriar esses índices, como faz a `4b7c1e9a2d55`, e deve ser testada em `upgrade`, `downgrade` e `upgrade`.

### 7.3 Mass assignment

`UpdateUserDTO` contém só `name`, `username` e `email`. Papel, família e senha **nunca** são alterados pelo CRUD de edição, e há teste garantindo que a rota ignora esses campos se vierem no POST.

### 7.4 Estados da conta (planejado)

Com o fluxo de ativação, o usuário passa a ter um ciclo de vida:

```
PENDENTE  --(ativação por link + código)-->  ATIVO  --(desativação)-->  DESATIVADO
                                               ^                              |
                                               +--------(reativação)---------+
```

- `PENDENTE`: criado sem senha; não autentica; e-mail ainda **não confiável**.
- `ATIVO`: tem senha; autentica; e-mail confiável (a ativação provou o controle da caixa).
- `DESATIVADO`: não autentica; sessões abertas caem na requisição seguinte; dados preservados.

Isso exige que `password_hash` deixe de ser obrigatório para o estado pendente (migração) e novos campos, como `activated_at` e `is_active`.

---

## 8. Senhas

### 8.1 Hash (implementado, com evolução planejada)

O hash fica atrás de `AbstractPasswordHasher` (`hash`, `verify`), implementada hoje por `WerkzeugPasswordHasher` (scrypt, aceito pelo OWASP). A recomendação atual do OWASP é **Argon2id**; a troca é planejada e se resume a **uma nova implementação da porta** (`argon2-cffi`), sem tocar no domínio nem nos serviços. Hashes antigos podem ser regravados no primeiro login, com `check_needs_rehash`.

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

## 9. Ativação de conta e redefinição por token e código (planejado)

Decisão de projeto: o administrador **nunca define nem conhece** a senha de outra pessoa. O usuário a escolhe pelo próprio e-mail, e a prova exige **dois canais independentes**.

### 9.1 Fluxo de ativação

1. O administrador cadastra o usuário (sem senha). O estado é `PENDENTE`.
2. O sistema gera:
   - um **token** de ativação, enviado por **e-mail** em um link;
   - um **código** de ativação, **mostrado uma única vez** ao administrador, que o repassa por **outro canal**.
3. O usuário abre o link, informa o **código** e define a senha (dois campos).
4. Com token **e** código válidos, o sistema grava o hash, passa o usuário a `ATIVO` e invalida o convite.

### 9.2 Requisitos do token e do código

| Item | Requisito |
|---|---|
| Geração | `secrets` (imprevisível). O código tem formato legível e curto o bastante para ser ditado |
| Armazenamento | **Só o hash** do código e do token, nunca o valor (Seção 9.4). O sistema "conhece" o código por poder compará-lo |
| Validade | Limitada; expira |
| Uso | **Único**; consumido na ativação |
| Tentativas | Contador de erros do código; bloqueio após o limite; recuperável apenas com novo convite |
| Reemissão | Reenviar gera **novo** token e **novo** código e invalida os anteriores |
| Comparação | Tempo constante |
| Registro | Nunca em log nem em URL de redirecionamento |

> A validade e o número máximo de tentativas do código ainda estão em aberto (Seção 18). Os convites ficam em uma **tabela** (Seção 9.4).

### 9.3 Redefinição de senha por administrador

Decidido: a redefinição usa o **mesmo mecanismo** da ativação (novo link e novo código), sem senha temporária definida pelo administrador. Efeito imediato: a senha anterior deixa de valer, as sessões abertas caem e o convite anterior, se houver, é revogado. Quem pode **disparar** o fluxo, conforme o papel do usuário-alvo:

| Alvo | Quem pode disparar |
|---|---|
| `FAMILY_USER` | `FAMILY_ADMIN` da **mesma família** ou qualquer `SYSTEM_ADMIN` |
| `FAMILY_ADMIN` | outro `FAMILY_ADMIN` da **mesma família** ou qualquer `SYSTEM_ADMIN` |
| `SYSTEM_ADMIN` | **somente** outro `SYSTEM_ADMIN` (e o `ROOT`, como rede de segurança: proposta em aberto, Seção 18) |
| `ROOT` | ninguém pela aplicação; usa `flask reset-root-password` |

Ninguém dispara o fluxo **para si mesmo**: para a própria senha existe a recuperação por e-mail (Seção 11.2). Cada disparo é registrado e avisa o usuário afetado por e-mail (Seção 15).

### 9.4 Tabela de convites (decidido)

Token e código vivem em uma **tabela**, não em tokens assinados sem estado. Com tabela é possível revogar na reemissão, contar tentativas erradas, garantir uso único de forma atômica e manter histórico; um token assinado sem estado só faria isso com artifícios.

Modelagem proposta (`user_invitations`; nome e colunas a confirmar na implementação):

| Coluna | Função |
|---|---|
| `id` | identificador |
| `user_id` | usuário-alvo (chave estrangeira, `ON DELETE CASCADE`) |
| `purpose` | `ACTIVATION` ou `PASSWORD_RESET` |
| `token_hash` | hash do token do link (SHA-256 basta: o token é aleatório e longo); índice único |
| `code_hash` | hash do código, com a porta de hash lento (o código é curto, então o hash rápido não protege) |
| `created_by_user_id`, `created_at` | quem emitiu e quando |
| `expires_at` | validade |
| `attempts` | tentativas erradas do código |
| `consumed_at`, `revoked_at` | uso único e revogação |

Regras:

- No máximo **um convite ativo por usuário**: índice único parcial sobre os convites não consumidos e não revogados. Emitir outro **revoga** o anterior.
- O consumo é **atômico**: uma única instrução condicional (`UPDATE ... WHERE consumed_at IS NULL AND revoked_at IS NULL AND expires_at > agora AND attempts < limite`) evita corrida entre duas requisições.
- O token chega na URL; localiza-se o convite pelo **hash** do token e o código é conferido em tempo constante.
- Excluir o usuário apaga seus convites. Convites vencidos podem ser removidos em rotina de limpeza.
- A migração segue o cuidado da Seção 7.2.

### 9.5 Observação sobre o estado atual

Hoje o cadastro ainda coleta uma **senha temporária** em dois campos (e `must_change_password` obriga a troca). Isso será **removido** do cadastro quando o fluxo acima for implementado. O botão de mostrar/ocultar senha (`password_toggle.js`) e a regra de confirmação migram para a página de definição de senha.

---

## 10. Autenticação e sessão (planejado)

### 10.1 Pilha

| Necessidade | Biblioteca |
|---|---|
| Sessão e proteção de rotas | **Flask-Login** (o `User` de domínio **não** herda de `UserMixin`; um adaptador na camada web faz a ponte) |
| CSRF | **Flask-WTF** (`CSRFProtect`) |
| Limite de tentativas | **Flask-Limiter** |
| Hash de senha | **argon2-cffi** (atrás da porta) |
| Tokens assinados | **itsdangerous** (já vem com o Flask) |

Nada de código de segurança criptográfico próprio.

### 10.2 Login

- Identificador: **nome de usuário ou e-mail** (ambos únicos, sem diferenciar caixa).
- Erro **genérico** sempre ("Usuário ou senha inválidos"), sem distinguir usuário inexistente, senha errada, conta pendente ou desativada.
- **Tempo de resposta equalizado**: quando o usuário não existe, calcula-se o hash de uma senha falsa para gastar o mesmo tempo.
- Limite de tentativas por IP e por conta, com atraso progressivo (nunca bloqueio permanente, que permitiria negar serviço a terceiros).
- Só autentica usuário `ATIVO`.
- Ao autenticar, a sessão é **recriada** (`session.clear()` antes de gravar o usuário) para evitar fixação de sessão.
- Parâmetro `next` do login **validado** (apenas caminhos relativos), para evitar redirecionamento aberto.
- Logout por **POST** (com CSRF).

### 10.3 Sessão

- Cookie de sessão **assinado** (não criptografado): não guardar dados sensíveis.
- Configuração: `HttpOnly`, `SameSite=Lax` e `Secure` em produção.
- O cookie guarda o **id do usuário mais uma impressão digital** derivada do hash da senha atual (HMAC com a `SECRET_KEY`). O usuário é **recarregado do banco a cada requisição**. Consequências: trocar a senha, desativar ou excluir o usuário derruba todas as sessões abertas, sem precisar de armazenamento de sessões.
- Duração e expiração por inatividade: em aberto (Seção 18).

### 10.4 CSRF

Todo POST exige token (`CSRFProtect`). Mutação de estado **nunca** ocorre em GET (convenção de rotas do projeto: `GET`+verbo para leitura, `POST`+verbo para mutação).

---

## 11. E-mail do usuário (planejado, com regras já decididas)

O e-mail é a **chave-mestra** da conta, porque a recuperação o usa como "senha de reserva". Por isso é tratado como dado sensível.

### 11.1 Regras

1. **Cadastro:** o e-mail é informado em **dois campos** com verificação de igualdade **no serviço**; **colar é permitido**; antes de salvar, uma **janela de confirmação** mostra o endereço.
2. **Normalização e validação:** biblioteca `email-validator` (não expressão regular própria); unicidade sem diferenciar caixa (já implementada). Decisão em aberto sobre caracteres Unicode parecidos (aceitar só ASCII ou confiar na normalização).
3. **Antes da ativação**, o administrador (inclusive de família) pode **corrigir** o e-mail; o convite é reenviado ao novo endereço.
4. **Depois da ativação**, só o **próprio usuário** altera o e-mail: senha atual, novo e-mail em dois campos, janela de confirmação; aviso ao endereço antigo; idealmente confirmação por link no endereço novo (depende de SMTP).
5. **Recuperação de senha por e-mail só para conta `ATIVA`:** um e-mail de conta pendente é só o que o administrador digitou e pode estar errado.
6. **`ROOT` fica fora da recuperação por e-mail** (usa o CLI) e nenhum administrador altera o e-mail do root.
7. Os tokens de recuperação e de troca de e-mail são **presos ao e-mail e à senha atuais** (impressão digital de ambos): mudar qualquer um invalida links antigos.

### 11.2 Recuperação de senha (planejada)

Token assinado (`URLSafeTimedSerializer`, `salt` próprio), validade curta, uso único por construção, resposta **sempre igual** ao pedir a recuperação (sem confirmar se o e-mail existe), limite por IP **e por endereço de destino** (contra *e-mail bombing*), aviso por e-mail após a troca, senha escolhida é definitiva.

---

## 12. Configuração de ambiente e proteção de rotas

### 12.1 Segredos e configuração (implementado)

- `SECRET_KEY` é **obrigatória**: `create_app` falha se não estiver definida. Trocá-la derruba as sessões e invalida tokens assinados.
- `.env` fica **fora do controle de versão**. Nunca registre valores de `.env` em log, issue ou commit.

### 12.2 `AUTH_ENABLED` (decidido, planejado)

Variável de ambiente, lida por `Config`, que define se a proteção das rotas está ativa ao subir o servidor.

- **Sempre deve ser informada.** Sem valor padrão: se ausente, a aplicação **recusa subir** (falha fechada). Só pode valer `false` quando `APP_ENV=development` (Seção 12.3).
- `true`: proteção ativa, funcionamento normal.
- `false`: apenas para **desenvolvimento**. Em vez de ficar sem identidade, a aplicação **autentica sozinha como um usuário configurado** (`DEV_AUTO_LOGIN_USERNAME`), por meio de um `request_loader` do Flask-Login. A autenticação por senha é dispensada, mas as demais camadas continuam funcionando com um ator real.
- **Não usar `LOGIN_DISABLED` do Flask-Login**: ele deixa `current_user` anônimo, e qualquer regra futura que dependa de papel ou família quebraria ou, pior, seria contornada.
- O desvio vive em **um único ponto** (a configuração do gerenciador de login), não em `if` espalhados pelas rotas.
- Com a proteção desligada: **aviso no log** na subida e **faixa visível em todas as telas**. Nunca pode ser desligada por URL, cabeçalho ou formulário.
- Escolher **qual** usuário é o de desenvolvimento permite testar a tela como administrador do sistema, administrador de família ou usuário de família.

### 12.3 `APP_ENV` e a trava de produção (decidido, planejado)

O `DEBUG` do Flask **não** define "produção". `FLASK_ENV` foi removido a partir do Flask 2.3 e o Flask não tem, por si, noção de ambiente de produção. `DEBUG` só liga o depurador interativo e o recarregador, e deve estar desligado em produção porque o depurador permite executar código. Por isso o ambiente é declarado por uma variável **explícita** do projeto, `APP_ENV`:

- Valores aceitos: `development` ou `production`. Qualquer outro valor, ou a ausência da variável, **impede a subida** (sem valor padrão, como `AUTH_ENABLED`).
- `production`: só sobe se `AUTH_ENABLED=true`, `DEBUG` estiver desligado, a `SECRET_KEY` for forte (comprimento mínimo a fixar na implementação) e `SESSION_COOKIE_SECURE` estiver ativo. Se qualquer condição falhar, a aplicação **não sobe** e informa qual.
- `development`: permite `AUTH_ENABLED=false` (Seção 12.2).
- `DEBUG` continua sendo uma configuração própria, e deixa de ser o critério para decidir se algo é permitido ou não.

A validação acontece **uma única vez**, na criação da aplicação (`create_app`), e as demais camadas apenas leem a configuração já validada.

> Nota sobre o código atual: `Config.DEBUG` usa `os.getenv("FLASK_DEBUG", "True")`, ou seja, o padrão é **ligado** quando a variável não existe. Esse padrão deve ser invertido (desligado) quando a autenticação entrar.

### 12.4 Testes

A proteção de rotas é testada **sempre com `AUTH_ENABLED=true`**, independentemente da configuração local do desenvolvedor.

---

## 13. Comandos de CLI

### 13.1 `flask create-root` (implementado)

- Opções interativas: nome de usuário, e-mail e senha (`hide_input`, com confirmação). Também aceita `--username`, `--email` e `--password`, mas o uso normal é o prompt (valores na linha de comando ficam no histórico do shell).
- Cria o usuário `ROOT`, sem nome e sem família, com `must_change_password=True`.
- Falha (sem traceback) se já existir um root, se username/e-mail já estiverem em uso ou se a senha for curta.
- Serviço: `UserService.create_root`. O root **não** é criável nem excluível pelo CRUD (`root_cannot_be_created`, `root_cannot_be_deleted`).

### 13.2 `flask reset-root-password` (planejado)

Redefine a senha do root. Mesma interação do `create-root`. É o **único** caminho de redefinição do root: o root está fora da recuperação por e-mail e fora do alcance dos demais administradores.

---

## 14. Defesas nas demais camadas (implementado)

| Ameaça | Defesa |
|---|---|
| XSS | Autoescape do Jinja; o realce de pesquisa escapa o texto antes de marcar (há testes de injeção de HTML) |
| Injeção de SQL | Somente consultas parametrizadas (SQLAlchemy); curingas de `LIKE` (`%`, `_`, `\`) do termo de pesquisa são tratados como texto |
| Mass assignment | DTOs com campos explícitos |
| Vazamento de dados | `UserResponseDTO` sem `password_hash`; a listagem nunca renderiza hash nem senha (há teste) |
| Segredo ausente | `SECRET_KEY` obrigatória no startup |
| Eco de senha | Em erro de formulário, a senha digitada **não volta** para a página |

Planejado: cabeçalhos de segurança (CSP, `X-Frame-Options` ou `frame-ancestors`, HSTS, `Referrer-Policy: no-referrer` nas páginas com token), por exemplo com Flask-Talisman.

---

## 15. Auditoria e avisos (planejado)

Registro **somente de inclusão** (append-only) de eventos de segurança, com data, ator, alvo, ação e IP, **sem segredos**:

- login com sucesso e falha, bloqueios por excesso de tentativas;
- ativação, troca e redefinição de senha (e quem redefiniu);
- criação, desativação, reativação e exclusão de usuário;
- alteração de e-mail.

Ações sensíveis feitas por administrador **avisam o usuário afetado por e-mail**.

---

## 16. Testes de segurança

**Existentes:** invariantes de papel e família (domínio e `CHECK`); nome obrigatório por papel; unicidade global sem diferenciar caixa; hash com sal; confirmação de senha no serviço; `create-root` (inclusive recusa de segundo root e entrada inválida); proteção contra atribuição em massa; ausência de hash e senha nas respostas; escape de HTML nas listagens.

**Obrigatórios ao implementar a autenticação:**

- toda rota é **protegida ou pública declarada**: um teste percorre `app.url_map` e falha ao encontrar uma rota nova sem proteção, sempre com `AUTH_ENABLED=true`;
- login: erro genérico, equalização de tempo, limite de tentativas, conta pendente e desativada não autenticam;
- sessão cai quando a senha muda ou a conta é desativada;
- ativação: token e código exigidos juntos, expiração, uso único, bloqueio por tentativas, reemissão invalida o anterior;
- tokens presos a e-mail e senha;
- CSRF rejeita POST sem token;
- recuperação responde igual exista ou não o e-mail.

---

## 17. Autorização: fora do escopo desta versão

A decisão de **quem pode fazer o quê** em cada operação (papéis, escopo por família, `Principal`, política, filtro de tenant nas consultas) **não está especificada nem implementada** nesta versão. As descrições de papéis na Parte I tratam apenas do ciclo de vida das contas (cadastrar, ativar, redefinir senha, desativar), que faz parte do fluxo de autenticação.

Quando a autorização for abordada, esta seção será substituída pela especificação, que parte de que **a Família é o tenant** e de que toda consulta de dados financeiros deve ser escopada por `family_id` vindo da sessão, nunca de formulário.

---

## 18. Decisões em aberto

| Tema | Situação |
|---|---|
| Provedor de e-mail (SMTP) | Em discussão. Em desenvolvimento, um envio que escreve no log pode bastar, atrás de uma porta `AbstractEmailSender` |
| Tempos de sessão | Recomendação apresentada: 30 minutos de inatividade e 8 horas de duração absoluta, sem "lembrar de mim"; aguarda decisão |
| Validade do convite e tentativas do código | Recomendação apresentada: 24 horas (12 horas é aceitável) e 5 tentativas; aguarda decisão |
| O `ROOT` pode disparar a redefinição de um `SYSTEM_ADMIN` | Proposta: sim, como rede de segurança se o único administrador do sistema perder o acesso; aguarda confirmação |
| Colar no segundo campo do e-mail na troca do **próprio** e-mail | Confirmado para o cadastro; a definir para a troca |
| Caracteres Unicode parecidos em e-mails | A definir |
| Confirmação final da pilha (Flask-Login, Flask-WTF, Flask-Limiter, Argon2id) | Proposta, aguarda confirmação |

---

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
