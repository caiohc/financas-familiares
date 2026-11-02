# Segurança, autenticação e autorização: tutorial didático

Material de estudo para a feature de autenticação do projeto. A ordem é cronológica: a mesma em que
uma pessoa, uma requisição e, depois, o código encontram cada problema. Cada capítulo explica o
conceito, mostra um exemplo no ecossistema Python e diz onde a peça entra no projeto.

> **Aviso.** Os trechos de código são didáticos e curtos. Servem para entender a ideia, não são o
> código final do projeto. Nomes de bibliotecas e opções devem ser conferidos na documentação da
> versão que for instalada.

## Sumário

0. Vocabulário
1. Modelo mental e modelo de ameaças
2. HTTP não tem memória: cookies e sessões
3. Senhas: como guardar e como exigir
4. O login, passo a passo
5. Ataques que usam o navegador da vítima
6. Fluxos de credencial e segurança da conta e do e-mail (temporária, troca, recuperação, troca de e-mail, administradores como ameaça)
7. Autorização: quem pode fazer o quê
8. Operação: segredos, HTTPS, registros e dependências
9. Mapa do projeto e ordem de implementação
10. Glossário e leituras

---

## 0. Vocabulário

| Termo | Pergunta que responde | Exemplo no projeto |
|---|---|---|
| **Identificação** | "Quem você diz ser?" | digitar o nome de usuário |
| **Autenticação** (AuthN) | "Você prova que é essa pessoa?" | conferir a senha |
| **Autorização** (AuthZ) | "O que essa pessoa pode fazer?" | só o administrador da família cadastra membros |
| **Auditoria** | "O que foi feito, por quem e quando?" | registro de logins e redefinições |
| **Sessão** | "Como o servidor lembra quem é você entre requisições?" | cookie assinado |
| **Tenant** | "Qual é a fronteira de isolamento dos dados?" | a Família |

Uma analogia: o crachá na portaria prova quem você é (autenticação); o que o crachá abre
(autorização) é outra decisão, e o livro de visitas é a auditoria. Confundir autenticação com
autorização é a origem de muitos incidentes: estar logado não significa poder acessar qualquer
coisa.

Os códigos HTTP refletem a diferença: **401** é "não sei quem você é"; **403** é "sei quem você é,
mas não pode". Em sistemas com vários tenants costuma-se responder **404** quando o recurso existe
mas pertence a outro tenant, para não revelar que ele existe.

---

## 1. Modelo mental e modelo de ameaças

### 1.1 Princípios que guiam todas as decisões

1. **Menor privilégio.** Cada papel recebe só o que precisa.
2. **Negar por padrão.** Uma rota nova nasce protegida; liberar é uma decisão explícita.
3. **Defesa em profundidade.** Nunca uma única barreira: decorador na rota, regra no serviço e
   filtro de tenant na consulta.
4. **Nunca confiar no cliente.** Campos escondidos, validação em JavaScript e o próprio `family_id`
   vindo do formulário podem ser alterados por quem usa o navegador.
5. **Não inventar criptografia.** Usar bibliotecas consolidadas e padrões publicados.
6. **Falhar fechado.** Na dúvida (erro, token inválido, papel desconhecido), negar.

### 1.2 Modelo de ameaças do projeto

Antes de escolher ferramentas, pergunte: *o que protegemos e de quem?*

- **Ativo:** dados financeiros de famílias.
- **Atacantes plausíveis:**
  - uma pessoa de **outra família** tentando ver dados alheios (quebra de isolamento do tenant);
  - um **usuário comum** tentando ações de administrador (escalada de privilégio);
  - um **atacante externo** adivinhando senhas, roubando sessão ou enganando o navegador de alguém
    logado;
  - um **administrador comprometido** (a conta de alguém com muito poder).
- **O que o OWASP diz:** a lista OWASP Top 10 coloca a *quebra de controle de acesso* (broken access
  control) no topo na edição de 2021, seguida de falhas criptográficas e falhas de identificação e
  autenticação. É exatamente o território deste tutorial.

---

## 2. HTTP não tem memória: cookies e sessões

### 2.1 O problema

Cada requisição HTTP chega ao servidor sem lembrar da anterior. Para saber "quem é você" a cada
clique, o servidor entrega ao navegador um **cookie** que ele devolverá em toda requisição.

### 2.2 Cookie assinado (o que o Flask faz)

A sessão do Flask é um cookie **assinado, não criptografado**: qualquer pessoa pode *ler* o
conteúdo, mas não consegue *alterá-lo* sem a chave secreta. A biblioteca por baixo é o
`itsdangerous`:

```python
from itsdangerous import URLSafeSerializer, BadSignature

serializer = URLSafeSerializer("uma-chave-secreta-longa", salt="demo")

cookie = serializer.dumps({"user_id": 42})
print(serializer.loads(cookie))          # {'user_id': 42}

adulterado = cookie[:-1] + ("A" if cookie[-1] != "A" else "B")
try:
    serializer.loads(adulterado)
except BadSignature:
    print("assinatura inválida: o cookie foi alterado")
```

Consequências práticas:

- Nunca guarde segredos nem dados sensíveis na sessão: o usuário (e qualquer um que veja o
  cookie) consegue ler.
- A chave (`SECRET_KEY`) é o que sustenta tudo. Vazou, qualquer um forja sessões.
- **Revogação é difícil** com cookie assinado puro: o servidor não tem uma lista de sessões para
  apagar. Veremos como resolver isso no capítulo 4.

### 2.3 Cookie assinado versus sessão no servidor

| | Cookie assinado | Sessão no servidor |
|---|---|---|
| Onde fica o estado | no navegador | no servidor (Redis, banco) |
| Revogar uma sessão | difícil | trivial (apagar a linha) |
| Escala | simples | exige armazenamento compartilhado |
| Quando usar | apps pequenas e médias | quando revogação imediata é requisito forte |

O desenho proposto para o projeto: cookie assinado contendo só o id do usuário e uma *impressão
digital* da senha, e o usuário é **recarregado do banco a cada requisição**. Assim, excluir ou
desativar um usuário e trocar a senha derrubam as sessões abertas sem precisar de armazenamento
extra (capítulo 4).

### 2.4 Atributos do cookie de sessão

```python
# configuração do Flask
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,    # JavaScript não lê o cookie (limita o estrago de um XSS)
    SESSION_COOKIE_SECURE=True,      # só trafega por HTTPS (em produção)
    SESSION_COOKIE_SAMESITE="Lax",   # não vai em requisições POST vindas de outros sites
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
```

- **HttpOnly:** o navegador esconde o cookie do JavaScript da página.
- **Secure:** o cookie só viaja por HTTPS.
- **SameSite:** restringe o envio do cookie em requisições originadas por outros sites; é a
  primeira linha de defesa contra CSRF (capítulo 5).

### 2.5 Fixação de sessão

Ataque: o invasor faz a vítima usar uma sessão que *ele* conhece e, depois do login, passa a
controlá-la. Defesa: **criar uma sessão nova no momento do login** (`session.clear()` antes de
gravar o usuário). O Flask-Login faz isso ao chamar `login_user`.

---

## 3. Senhas: como guardar e como exigir

### 3.1 Por que não guardar a senha como ela é

Se o banco vazar, quem o lê não pode ver senhas. Mas "criptografar" também não resolve (quem tem a
chave descriptografa tudo). A solução é guardar um **hash**: uma função de mão única.

### 3.2 Por que SHA-256 simples não basta

`SHA-256` é rápido, e rápido é ruim para senhas: um atacante com placa de vídeo testa bilhões de
palavras por segundo. Para senhas usam-se funções **deliberadamente lentas e que consomem
memória**, com **sal** (valor aleatório único por senha, que impede ataques com tabelas
pré-calculadas e faz duas senhas iguais terem hashes diferentes).

A recomendação atual do OWASP (Password Storage Cheat Sheet), em ordem de preferência:

1. **Argon2id** (mínimo de 19 MiB de memória, 2 iterações, paralelismo 1);
2. **scrypt**;
3. **bcrypt** (aceitável, com fator de custo 10 ou mais);
4. **PBKDF2** (se exigência de conformidade FIPS).

### 3.3 Exemplos

Argon2id com `argon2-cffi` (o hash resultante já embute algoritmo, parâmetros e sal):

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

hasher = PasswordHasher()          # Argon2id, com parâmetros padrão razoáveis

hash_gravado = hasher.hash("minha senha longa")
# '$argon2id$v=19$m=65536,t=3,p=4$...'  (isto é o que vai para o banco)

try:
    hasher.verify(hash_gravado, "minha senha longa")     # atenção: (hash, senha)
except VerifyMismatchError:
    print("senha incorreta")

# Parâmetros mudam com o tempo: se o hash antigo ficou fraco, regrave no próximo login.
if hasher.check_needs_rehash(hash_gravado):
    hash_gravado = hasher.hash("minha senha longa")
```

O que o projeto usa hoje (Werkzeug, scrypt), igualmente aceito pelo OWASP:

```python
from werkzeug.security import generate_password_hash, check_password_hash

h = generate_password_hash("minha senha longa")
check_password_hash(h, "minha senha longa")    # True
```

> No projeto, o hash fica atrás da porta `AbstractPasswordHasher`. Trocar de scrypt para Argon2id
> é criar outra implementação da porta; o domínio e os serviços não mudam.

### 3.4 Comparações e aleatoriedade seguras

- Para comparar segredos (tokens, assinaturas), use comparação em **tempo constante**, que não
  vaza informação pelo tempo de resposta:

```python
import hmac
hmac.compare_digest(token_recebido, token_esperado)
```

- Para gerar tokens e senhas, use o módulo **`secrets`**, nunca `random` (que é previsível):

```python
import secrets
secrets.token_urlsafe(32)      # token imprevisível, seguro para URL
secrets.token_hex(32)          # ótimo para gerar uma SECRET_KEY
```

### 3.5 Política de senha

As diretrizes do NIST (SP 800-63B) se afastaram das regras antigas:

- **Comprimento importa mais do que complexidade.** Mínimo de 8; aceitar senhas longas (64 ou
  mais) e frases com espaços.
- **Sem regras do tipo "uma maiúscula, um número, um símbolo".** Elas geram `Senha@123`.
- **Sem expiração periódica obrigatória.** Troque quando houver suspeita de comprometimento.
- **Bloquear senhas comuns ou vazadas** (lista local ou consulta ao serviço Have I Been Pwned por
  *k-anonymity*, que nunca envia a senha inteira).
- **Permitir colar** no campo: gerenciadores de senhas. (O botão de olho do projeto ajuda quem
  digita, e a confirmação em dois campos evita erro de digitação.)
- Medidores como o `zxcvbn` estimam a força real em vez de contar caracteres.

### 3.6 Senha temporária

Como o administrador define a senha inicial, ela é um segredo compartilhado por outro canal. Regras:

- é **temporária de verdade**: `must_change_password = True` obriga a troca no primeiro acesso;
- nunca é registrada em log, e-mail ou tela depois do cadastro;
- se for gerada pelo sistema, use `secrets`:

```python
import secrets
import string

_ALFABETO = string.ascii_letters + string.digits

def gerar_senha_temporaria(tamanho: int = 14) -> str:
    return "".join(secrets.choice(_ALFABETO) for _ in range(tamanho))
```

---

## 4. O login, passo a passo

### 4.1 O fluxo

1. A pessoa envia identificador (usuário **ou** e-mail) e senha.
2. O servidor busca o usuário, **confere a senha** e verifica se a conta está ativa.
3. Se tudo bate, **abre uma sessão nova**; se não, devolve um erro **genérico**.
4. Se `must_change_password` estiver ligado, a pessoa só alcança a tela de troca de senha.

### 4.2 Erros genéricos e enumeração de usuários

Se a tela diz "usuário inexistente" para um caso e "senha incorreta" para outro, o atacante
descobre quais usuários existem (*enumeração*). Sempre a mesma mensagem: **"Usuário ou senha
inválidos."** O mesmo vale para o tempo de resposta: se o servidor responde rápido quando o usuário
não existe (nenhum hash calculado) e devagar quando existe, o tempo denuncia. A defesa é calcular
um hash de mentira nos dois casos:

```python
class InvalidCredentials(Exception):
    pass


class AuthService:
    def __init__(self, uow, hasher):
        self.uow = uow
        self.hasher = hasher
        # Hash de uma senha qualquer, calculado uma vez: serve para gastar o mesmo tempo
        # quando o usuário não existe.
        self._dummy_hash = hasher.hash("senha-que-ninguem-usa")

    def authenticate(self, identifier: str, password: str):
        with self.uow:
            user = (self.uow.users.get_by_username(identifier)
                    or self.uow.users.get_by_email(identifier))
            stored = user.password_hash if user else self._dummy_hash
            password_ok = self.hasher.verify(password, stored)

            if not (user and password_ok and user.is_active):
                raise InvalidCredentials()          # mensagem única, sem detalhes
            return user
```

### 4.3 Força bruta: limite de tentativas

Mesmo com senhas bem guardadas, é preciso frear tentativas repetidas. Estratégias:

- **Limitar por IP e por conta** (ex.: 5 tentativas por minuto), com `Flask-Limiter`;
- **Atraso progressivo** (backoff) em vez de bloqueio definitivo: bloqueio permanente permite que um
  atacante *tranque* a conta de outra pessoa de propósito (negação de serviço);
- Registrar as falhas (capítulo 8) para notar padrões.

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(get_remote_address, app=app, default_limits=[])

@bp.route("/authenticate", methods=["POST"])
@limiter.limit("5 per minute")
def authenticate():
    ...
```

### 4.4 Flask-Login: a sessão sem reinventar

O Flask-Login cuida de guardar o id na sessão, recarregar o usuário a cada requisição e proteger
rotas. O `User` de domínio **não** herda de nada do Flask: um adaptador fino faz a ponte.

```python
import hashlib
import hmac

from flask import current_app
from flask_login import LoginManager, UserMixin

login_manager = LoginManager()
login_manager.login_view = "auth.login"        # para onde mandar quem não está logado


def fingerprint(password_hash: str) -> str:
    """Impressão digital da senha atual, assinada com a SECRET_KEY."""
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, password_hash.encode(), hashlib.sha256).hexdigest()[:16]


class SessionUser(UserMixin):
    """Adaptador entre o User de domínio e o Flask-Login."""

    def __init__(self, user):
        self.user = user

    @property
    def is_active(self) -> bool:                # o Flask-Login recusa quem estiver inativo
        return self.user.is_active

    def get_id(self) -> str:
        # O cookie guarda "id:impressão". Se a senha mudar, a impressão muda e TODAS as
        # sessões antigas deixam de valer, sem precisar de lista de sessões.
        return f"{self.user.id}:{fingerprint(self.user.password_hash)}"


@login_manager.user_loader
def load_user(session_id: str):
    user_id, _, fp = session_id.partition(":")
    user = carregar_usuario_do_banco(user_id)   # a cada requisição (revogação imediata)
    if user is None or not hmac.compare_digest(fp, fingerprint(user.password_hash)):
        return None
    return SessionUser(user)
```

No login e no logout:

```python
from flask_login import login_user, logout_user, login_required

@bp.post("/authenticate")
def authenticate():
    try:
        user = auth_service.authenticate(request.form["identifier"], request.form["password"])
    except InvalidCredentials:
        flash("Usuário ou senha inválidos.", "error")
        return render_template("auth/login.html"), 401
    login_user(SessionUser(user))               # abre uma sessão nova
    return redirect(url_for("dashboard.index"))

@bp.post("/logout")                              # POST: logout por link GET é falsificável
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
```

### 4.5 Cuidado: redirecionamento aberto

É comum guardar a página pedida (`?next=/member/list`) para voltar a ela após o login. Se o valor
não for validado, `?next=https://site-falso.com` transforma o login legítimo num redirecionamento
para um site malicioso:

```python
from urllib.parse import urlparse

def is_safe_redirect(target: str) -> bool:
    parsed = urlparse(target)
    return not parsed.netloc and not parsed.scheme and target.startswith("/")
```

---

## 5. Ataques que usam o navegador da vítima

### 5.1 CSRF (falsificação de requisição entre sites)

**O ataque.** Você está logado no sistema. Em outra aba, uma página maliciosa contém um formulário
que envia `POST /user/delete/<id>` ao nosso sistema. O navegador anexa o cookie da sua sessão
automaticamente e o servidor acredita que foi você.

**Defesas combinadas:**

1. `SameSite=Lax` no cookie (já descrito);
2. **Token anti-CSRF** em todo formulário que altera estado, validado no servidor:

```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)       # passa a exigir o token em todo POST/PUT/PATCH/DELETE
```

```html
<form method="POST" action="/user/create">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    ...
</form>
```

3. Nunca alterar estado em requisições GET (por isso o projeto usa POST para mutações).

> Hoje o projeto não tem nenhuma proteção CSRF. Sem login isso era inofensivo; com sessão, passa a
> ser obrigatório.

### 5.2 XSS (injeção de script)

**O ataque.** Um texto digitado por alguém (um nome de membro, por exemplo) contém
`<script>...</script>` e é exibido a outra pessoa, executando código no navegador dela, com acesso
à página (e a ações em nome dela).

**Defesas:**

- O Jinja2 já **escapa** variáveis (`{{ nome }}`) automaticamente; o risco está em desligar isso
  com `|safe` ou `Markup()` sobre dados do usuário. (O realce de pesquisa do projeto escapa o texto
  antes de marcar, e há testes de injeção para isso.)
- **Content Security Policy (CSP):** um cabeçalho que diz ao navegador de onde scripts podem vir.
  Mesmo com falha de escape, scripts inline injetados não executam.
- `HttpOnly` no cookie limita o dano.

### 5.3 Clickjacking e cabeçalhos de segurança

Uma página alheia pode embutir o seu sistema num `<iframe>` invisível e fazer a pessoa clicar em
botões sem saber. Defesa: cabeçalhos `X-Frame-Options: DENY` ou `Content-Security-Policy:
frame-ancestors 'none'`. A extensão **Flask-Talisman** define em um só lugar esses cabeçalhos, o
CSP e o HSTS:

```python
from flask_talisman import Talisman

Talisman(app, content_security_policy={"default-src": "'self'"}, force_https=True)
```

### 5.4 Injeção de SQL e atribuição em massa

- **SQL:** use sempre consultas parametrizadas (o SQLAlchemy faz isso). O perigo está em montar SQL
  com f-strings:

```python
# ERRADO: o valor vira parte do SQL
session.execute(text(f"SELECT * FROM users WHERE username = '{username}'"))

# CERTO: o valor viaja como parâmetro
session.execute(text("SELECT * FROM users WHERE username = :u"), {"u": username})
```

- **Atribuição em massa (mass assignment):** copiar todos os campos do formulário para a entidade
  permite que alguém envie `role=SYSTEM_ADMIN` num formulário que não deveria aceitá-lo. Por isso o
  `UpdateUserDTO` do projeto só tem `name`, `username` e `email`, e há teste garantindo que a rota
  ignora `role`, `family_id` e senha enviados na edição.

---

## 6. Fluxos de credencial e segurança da conta e do e-mail

### 6.1 Os seis casos do projeto e sua natureza

| Caso | Quem escolhe a senha | `must_change_password` depois |
|---|---|---|
| Cadastro por administrador | o administrador (temporária) | `True` |
| Redefinição por administrador | o administrador (temporária) | `True` |
| Troca autônoma | a própria pessoa | `False` |
| Recuperação por e-mail | a própria pessoa | `False` |

A regra por trás: **só a pessoa conhece a senha definitiva dela**. Quando outro a define, ela é
provisória.

### 6.2 Forçar a troca no primeiro acesso

Enquanto a senha for temporária, a pessoa só alcança a tela de troca, o logout e os arquivos
estáticos:

```python
from flask import redirect, request, url_for
from flask_login import current_user

ROTAS_LIBERADAS = {"auth.change_password", "auth.update_password", "auth.logout", "static"}

@app.before_request
def exigir_troca_de_senha():
    if (current_user.is_authenticated
            and current_user.user.must_change_password
            and request.endpoint not in ROTAS_LIBERADAS):
        return redirect(url_for("auth.change_password"))
```

### 6.3 Troca autônoma

A pessoa informa a **senha atual** (prova que é ela, não alguém usando um computador deixado
aberto), a nova senha e a confirmação. O serviço valida a política, grava o novo hash e chama
`User.change_password`, que zera `must_change_password`. Como a impressão digital da sessão
depende do hash, **todas as outras sessões caem** e a atual precisa ser renovada (`login_user` de
novo).

### 6.4 Recuperação de senha por e-mail

O desenho em que a recuperação não exige tabela nova: um **token assinado, com prazo, que se
invalida sozinho quando a senha muda**.

```python
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

serializer = URLSafeTimedSerializer(SECRET_KEY, salt="recuperacao-de-senha")


def gerar_token(user) -> str:
    return serializer.dumps({"uid": str(user.id), "fp": fingerprint(user.password_hash)})


def ler_token(token: str, carregar_usuario):
    try:
        dados = serializer.loads(token, max_age=30 * 60)      # válido por 30 minutos
    except (BadSignature, SignatureExpired):
        return None
    user = carregar_usuario(dados["uid"])
    # Se a senha já mudou desde que o link foi emitido, a impressão é outra: link morto.
    if user is None or not hmac.compare_digest(dados["fp"], fingerprint(user.password_hash)):
        return None
    return user
```

Regras de segurança do fluxo:

1. **Resposta sempre igual** ao pedir recuperação: "Se o e-mail estiver cadastrado, enviamos as
   instruções." Nunca confirmar se o e-mail existe.
2. **Limite de tentativas** por IP e por e-mail (Flask-Limiter).
3. **Prazo curto** (30 a 60 minutos) e **uso único** (o token morre quando a senha muda).
4. O link vai **só por HTTPS**. O token fica na URL, então não deve ser registrado em log nem
   enviado a terceiros via cabeçalho `Referer` (use `Referrer-Policy: no-referrer`).
5. Depois da troca, **avisar por e-mail** que a senha mudou (a vítima de um roubo percebe).
6. A senha escolhida na recuperação é definitiva (`must_change_password = False`).

### 6.5 Quando o e-mail é confiável

A recuperação envia um link para o e-mail cadastrado. Se alguém digitou o endereço errado, o link
chega a um desconhecido, que poderia **tomar uma conta que nunca foi usada**. Daí a regra:

- o e-mail só é considerado **confiável depois do primeiro acesso** (quem recebeu a senha
  temporária provou ser a pessoa certa ao entrar);
- antes do primeiro acesso, a recuperação por e-mail fica desligada; o administrador resolve com
  uma redefinição;
- depois do primeiro acesso, o e-mail **não pode mais ser editado por terceiros**: senão, quem
  altera o e-mail e pede a recuperação assume a conta.

### 6.6 Desativar em vez de excluir

Excluir apaga o histórico. **Desativar** (`is_active = False`) impede o login mantendo os dados. O
Flask-Login já entende a propriedade `is_active`: usuário inativo é recusado no login e as sessões
existentes caem na próxima requisição, porque o usuário é recarregado do banco.

### 6.7 A conta root

O usuário root é o único que não pode ser recuperado por e-mail (editar o e-mail do root seria
tomar o controle total). Para ele existe uma **saída por fora da aplicação**: um comando de CLI
executado por quem tem acesso ao servidor. Quem tem a máquina já tem o banco; por isso o canal é
confiável.

```bash
uv run flask reset-root-password
```

### 6.8 O e-mail é a chave-mestra da conta

Com a recuperação por e-mail, **quem controla o endereço controla a conta**: o e-mail passa a ser uma
"senha de reserva". Por isso tudo o que mexe com ele (cadastrar, corrigir, trocar, validar) é
tratado como ação sensível. Há dois lados:

- **Fora do nosso controle:** a caixa de entrada da pessoa pode ser invadida. O que podemos fazer é
  limitar o estrago (links curtos e de uso único, aviso por e-mail quando a senha muda e, no
  futuro, segundo fator).
- **Dentro do nosso controle:** quem pode alterar o endereço guardado no sistema, e em que
  condições. É onde estão as brechas que dependem do nosso desenho, inclusive as que partem de
  administradores.

### 6.9 Quadro de ameaças ligadas à conta e ao e-mail

| Ameaça | Quem a pratica | Como | Defesa |
|---|---|---|---|
| Tomada de conta pela recuperação | administrador (do sistema ou da família) | troca o e-mail do usuário e pede a recuperação | e-mail imutável por terceiros depois do primeiro acesso; recuperação só depois do primeiro acesso; auditoria |
| Personificação por redefinição | administrador | redefine a senha (temporária) e entra como o usuário | inevitável no desenho (o administrador define a senha), então: a troca obrigatória encerra o acesso dele no primeiro login real da pessoa; **aviso por e-mail** ao usuário; auditoria de quem redefiniu; matriz de quem pode redefinir quem |
| Link de recuperação para desconhecido | erro de digitação do administrador | e-mail errado no cadastro | recuperação desligada até o primeiro acesso |
| Tomada permanente a partir de sessão roubada | atacante externo | com o computador aberto ou o cookie roubado, troca o e-mail e recupera a senha | pedir a **senha atual** na troca, avisar o endereço antigo, confirmar o novo por link |
| Enumeração de contas pela troca de e-mail | qualquer usuário autenticado | tenta um e-mail e lê "já está em uso" | resposta neutra (ver 6.11) |
| Inundação de e-mails (*e-mail bombing*) | atacante externo | dispara pedidos de recuperação para o e-mail de uma vítima | limite por IP **e por endereço de destino**, intervalo mínimo entre envios, resposta idêntica |
| Contas duplicadas por variações do endereço | usuário ou administrador | `Ana@x.com` ≠ `ana@x.com`; caracteres Unicode parecidos | normalização e validação (ver 6.12) |
| Token antigo que continua válido | atacante com e-mail antigo vazado | usa um link emitido antes da troca | o token só vale para o e-mail atual (ver 6.10) |

### 6.10 Tokens presos ao e-mail e à senha

O token de recuperação da seção 6.4 já morre quando a senha muda. Para que também morra quando o
**e-mail** muda, entra o e-mail na impressão digital:

```python
def impressao_da_credencial(user) -> str:
    # muda se a senha OU o e-mail mudarem: links emitidos antes deixam de valer
    return fingerprint(f"{user.password_hash}|{user.email}")

def gerar_token_recuperacao(user) -> str:
    return serializer.dumps({"uid": str(user.id), "fp": impressao_da_credencial(user)})
```

### 6.11 Troca do próprio e-mail: fluxo recomendado

Depois do primeiro acesso, só o próprio usuário altera o e-mail. O fluxo, do mais simples ao mais
completo:

**Etapa 1 (sem envio de e-mail):**

1. Usuário autenticado abre a tela de troca de e-mail.
2. Informa a **senha atual** (a sessão sozinha não basta: sessão roubada não deve render a conta),
   o **novo e-mail** e a **confirmação do e-mail** (campo em que colar é bloqueado, para o erro de
   digitação não ser copiado junto).
3. O sistema valida o formato (6.12), grava a troca e registra a ação na auditoria.

**Etapa 2 (com SMTP):**

1. Passos 1 e 2 iguais, mas o novo endereço fica em um campo **pendente** (`pending_email`); o e-mail
   ativo continua o antigo.
2. Um link, **enviado ao endereço novo**, confirma que a pessoa realmente controla a caixa. Só quando
   ele é aberto (com o usuário logado) a troca é efetivada:

```python
troca_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="troca-de-email")

def gerar_token_troca(user, novo_email: str) -> str:
    return troca_serializer.dumps({
        "uid": str(user.id),
        "novo": novo_email,
        "fp": impressao_da_credencial(user),
    })

def confirmar_troca(token: str, usuario_logado):
    try:
        dados = troca_serializer.loads(token, max_age=24 * 3600)      # 24 horas
    except (BadSignature, SignatureExpired):
        return None
    if dados["uid"] != str(usuario_logado.id):                         # só o dono confirma
        return None
    if not hmac.compare_digest(dados["fp"], impressao_da_credencial(usuario_logado)):
        return None                                                    # senha ou e-mail mudaram
    return dados["novo"]
```

3. Um aviso vai ao **endereço antigo** ("seu e-mail foi alterado para ...; se não foi você,
   contate o administrador").

**Resposta neutra.** Se o novo endereço já pertence a outra conta, dizer "já está em uso" confirma
que a conta existe. O desenho mais seguro responde sempre "enviamos um link de confirmação a esse
endereço" e, se o e-mail já estiver em uso, o único efeito é uma mensagem ao dono real avisando da
tentativa. Na etapa 1, sem envio de e-mail, esse vazamento mínimo é um compromisso consciente
(a pessoa está autenticada, e o sistema é de cadastro fechado), a ser decidido.

### 6.12 Normalizar e validar o e-mail

Duas contas com o "mesmo" e-mail escrito de formas diferentes quebram a unicidade e abrem brechas.

- **Validar o formato** com uma biblioteca (`email-validator`) em vez de expressão regular própria:

```python
from email_validator import validate_email, EmailNotValidError

def normalizar_email(texto: str) -> str:
    try:
        return validate_email(texto, check_deliverability=False).normalized
    except EmailNotValidError as erro:
        raise ValueError(str(erro))
```

- **Caixa e espaços:** o projeto já compara sem diferenciar maiúsculas de minúsculas e apara espaços
  (índice único sobre `lower(email)`).
- **Caracteres parecidos (homógrafos):** `аna@x.com` com um "а" cirílico *parece* `ana@x.com` e é
  outro endereço. Em um cadastro fechado o risco é baixo; ainda assim, decida se aceita só
  caracteres ASCII ou se confia na normalização Unicode da biblioteca.
- **`+etiquetas` (`ana+loja@x.com`):** costumam cair na mesma caixa de `ana@x.com`. Não é ameaça de
  segurança (a pessoa pode ter dois e-mails de verdade), então a recomendação é **não** tentar
  adivinhar equivalências entre provedores.
- **Um e-mail por conta** é regra de negócio do projeto. Consequência: duas pessoas que usam a mesma
  caixa (um casal com e-mail compartilhado, por exemplo) não podem ter contas separadas.

### 6.13 Administradores também são parte do modelo de ameaças

Um sistema que confia cegamente nos administradores tem como ponto fraco justamente quem tem mais
poder. Princípios:

1. **Nenhuma ação sensível é silenciosa.** Redefinir senha, desativar conta e alterar dados de
   identificação geram **aviso por e-mail** ao usuário afetado.
2. **Auditoria que o administrador não altera.** Registro apenas de inclusão (*append-only*): quem
   (ator), o quê (ação), sobre quem (alvo), quando e de onde (IP). Nem o administrador apaga linhas.
3. **Poder mínimo e com escopo.** O administrador da família só age sobre a própria família; o
   administrador do sistema não alcança o root; o root só administra administradores do sistema.
4. **Nada de ver senha nem "entrar como" o usuário.** Se um dia a personificação for necessária
   (suporte), ela exige registro, aviso e limite de tempo.
5. **Quem redefine não conhece a senha final.** A senha temporária só vale até a primeira troca,
   feita pela própria pessoa. A partir daí o administrador deixa de acessar a conta, mas o aviso e
   a auditoria continuam registrando que ele chegou a redefini-la.
6. **Separação de papéis.** Quem cadastra não é, por definição, quem audita; para ações de maior
   risco, considerar a aprovação de um segundo administrador (controle duplo), se um dia o risco
   justificar.

---

## 7. Autorização: quem pode fazer o quê

### 7.1 Modelos

- **ACL:** lista de quem pode o quê em cada objeto (ex.: permissões de arquivo).
- **RBAC** (por papéis): o poder vem do papel (`SYSTEM_ADMIN`, `FAMILY_ADMIN`, `FAMILY_USER`).
- **ABAC** (por atributos): a decisão olha atributos do ator, do objeto e do contexto (ex.: "mesma
  família").
- **ReBAC** (por relacionamento): "pode ver porque é membro da família do dono".

O projeto usa **RBAC com escopo de tenant**: o papel diz *o que* (cadastrar usuário), e a família
diz *onde* (só na própria).

### 7.2 A falha mais comum: BOLA / IDOR

*Broken Object Level Authorization* (ou IDOR): a rota confere que a pessoa está logada, mas não que
o **objeto** é dela. Basta trocar o id na URL.

```python
# ERRADO: qualquer usuário logado lê o membro de qualquer família
@bp.get("/member/edit/<uuid:member_id>")
@login_required
def edit(member_id):
    return render(member_service.get_member(member_id))

# CERTO: o serviço recebe QUEM está pedindo e confere o tenant
@bp.get("/member/edit/<uuid:member_id>")
@login_required
def edit(member_id):
    return render(member_service.get_member(actor=current_actor(), member_id=member_id))
```

Para quem está de fora, "recurso de outra família" e "recurso inexistente" devem ser
indistinguíveis (404).

### 7.3 Política como funções puras

As regras de quem pode o quê ficam em **funções puras do domínio**, sem Flask e sem banco, o que
as torna fáceis de ler e de testar:

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import uuid


class Role(Enum):
    ROOT = "ROOT"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    FAMILY_ADMIN = "FAMILY_ADMIN"
    FAMILY_USER = "FAMILY_USER"


@dataclass(frozen=True)
class Principal:
    """Quem está agindo: extraído da sessão, nunca do formulário."""
    user_id: uuid.UUID
    role: Role
    family_id: Optional[uuid.UUID]


def can_create_user(actor: Principal, new_role: Role, family_id: Optional[uuid.UUID]) -> bool:
    if actor.role is Role.ROOT:
        return new_role is Role.SYSTEM_ADMIN
    if actor.role is Role.SYSTEM_ADMIN:
        return new_role is not Role.ROOT
    if actor.role is Role.FAMILY_ADMIN:
        return new_role in (Role.FAMILY_ADMIN, Role.FAMILY_USER) and family_id == actor.family_id
    return False                                   # FAMILY_USER, e qualquer coisa inesperada: nega
```

### 7.4 Aplicar em três camadas (defesa em profundidade)

| Camada | O que faz | Por quê |
|---|---|---|
| **Rota** (`@roles_required`) | recusa cedo quem claramente não deveria entrar | resposta rápida, mas não é a única barreira |
| **Serviço** (chama a política) | decide com o objeto real em mãos | é aqui que mora a regra |
| **Repositório** (filtro por `family_id`) | a consulta nunca devolve linhas de outro tenant | mesmo um bug no serviço não vaza dados |

Decorador da camada de rota:

```python
from functools import wraps
from flask import abort, current_app
from flask_login import current_user


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()      # 401 / redireciona ao login
            if current_user.user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapper
    return decorator
```

### 7.5 Teste que impede esquecimento

O erro mais perigoso é uma rota nova nascer sem proteção. Um teste percorre **todas** as rotas
registradas e exige que cada uma seja pública (declarada explicitamente) ou redirecione quem não
está logado:

```python
PUBLICAS = {"auth.login", "auth.authenticate", "auth.recover", "static"}

def test_toda_rota_e_protegida_ou_explicitamente_publica(app):
    client = app.test_client()
    for rule in app.url_map.iter_rules():
        if rule.endpoint in PUBLICAS:
            continue
        url = montar_url_de_exemplo(rule)             # preenche <uuid:...> com um uuid qualquer
        for method in rule.methods & {"GET", "POST"}:
            resposta = client.open(url, method=method)
            assert resposta.status_code in (302, 401), f"{rule.endpoint} {method} está aberta"
```

E a matriz de papéis testada de forma tabular:

```python
@pytest.mark.parametrize("ator, novo_papel, mesma_familia, esperado", [
    (Role.ROOT,         Role.SYSTEM_ADMIN, None,  True),
    (Role.ROOT,         Role.FAMILY_USER,  True,  False),
    (Role.SYSTEM_ADMIN, Role.FAMILY_ADMIN, True,  True),
    (Role.SYSTEM_ADMIN, Role.ROOT,         None,  False),
    (Role.FAMILY_ADMIN, Role.FAMILY_USER,  True,  True),
    (Role.FAMILY_ADMIN, Role.FAMILY_USER,  False, False),   # outra família
    (Role.FAMILY_USER,  Role.FAMILY_USER,  True,  False),
])
def test_can_create_user(ator, novo_papel, mesma_familia, esperado): ...
```

### 7.6 Autorização e tenant no projeto

Como a Família é o tenant, **toda consulta de dados financeiros é escopada por `family_id`**, e esse
valor vem do `Principal` (sessão), nunca de campo de formulário. Administradores do sistema são os
únicos fora dessa regra, e mesmo eles agem sobre famílias de forma explícita.

---

## 8. Operação: segredos, HTTPS, registros e dependências

### 8.1 Segredos

- `SECRET_KEY` longa e aleatória: `python -c "import secrets; print(secrets.token_hex(32))"`.
- Guardada no `.env` fora do controle de versão (confira o `.gitignore`); em produção, num
  cofre de segredos.
- Trocar a chave **derruba todas as sessões** (e invalida os tokens de recuperação).
- Jamais registrar senhas, tokens ou o corpo de requisições de login em log.

### 8.2 HTTPS

Sem HTTPS, senha e cookie viajam legíveis pela rede. Em produção: certificado válido,
redirecionamento de HTTP para HTTPS, `SESSION_COOKIE_SECURE=True` e **HSTS** (o navegador passa a
recusar HTTP naquele domínio).

### 8.3 Registro de eventos de segurança (auditoria)

Registre, com data, usuário e IP, **sem segredos**:

- login com sucesso e falho (e bloqueios por excesso de tentativas);
- troca e redefinição de senha, e quem a fez;
- criação, desativação e exclusão de usuário;
- mudança de papel ou de e-mail.

Isso responde "o que aconteceu?" depois de um incidente e alimenta alertas ("50 falhas de login em
um minuto").

### 8.4 Dependências

- Fixe versões (`uv.lock`) e verifique vulnerabilidades conhecidas: `pip-audit` (ou o recurso de
  alertas do GitHub).
- Atualize bibliotecas de segurança com frequência: são as que mais recebem correções.

### 8.5 Evoluções futuras

- **Segundo fator (2FA) por TOTP** (aplicativo autenticador), com `pyotp`:

```python
import pyotp

segredo = pyotp.random_base32()                       # guardado (cifrado) por usuário
totp = pyotp.TOTP(segredo)
uri = totp.provisioning_uri(name="ana@example.com", issuer_name="Finanças")   # vira QR code
totp.verify("123456", valid_window=1)                 # True/False
```

- **Passkeys (WebAuthn):** autenticação sem senha, com a biblioteca `webauthn` (py_webauthn).
- **Provedor de identidade externo** (Keycloak e similares), quando o volume ou a conformidade
  exigirem.

---

## 9. Mapa do projeto e ordem de implementação

### 9.1 Onde cada peça fica (Arquitetura em camadas)

| Peça | Camada | Observação |
|---|---|---|
| `Role`, `User`, invariantes, política de senha, `Principal`, funções `can_*` | domínio | puro, sem Flask nem banco |
| `AuthService`, `UserService` (com ator), portas `AbstractPasswordHasher` e `AbstractEmailSender` | aplicação | sem Flask, testado com fakes |
| Hasher (Argon2id), repositórios, envio de e-mail | infraestrutura | detalhes substituíveis |
| Flask-Login, CSRF, Limiter, rotas `/auth`, decoradores, `before_request` | interface web | acoplamento com Flask permitido aqui |
| Comandos `create-root` e `reset-root-password` | interface (CLI) | canal confiável fora da web |

### 9.2 Ordem cronológica sugerida

1. **Base:** Argon2id atrás da porta, login e logout, sessão com impressão digital, CSRF, troca
   obrigatória e troca autônoma, `Principal` com a política de autorização, desativação de usuário
   e teste de "toda rota protegida".
2. **Cadastro e redefinição com ator:** casos de administrador do sistema, administrador de
   família e redefinição temporária; trava do e-mail após o primeiro acesso.
3. **Recuperação por e-mail:** porta de e-mail, token assinado, limite de tentativas e aviso de
   troca; comando `reset-root-password`.
4. **Endurecimento:** cabeçalhos de segurança (Talisman), limite de tentativas de login,
   registro de auditoria.

---

## 10. Glossário e leituras

**Glossário rápido:** *hash* (resumo de mão única), *sal* (aleatório por senha), *pimenta*
(segredo global opcional além do sal), *token* (valor secreto de uso restrito), *TTL* (prazo de
validade), *enumeração* (descobrir quais contas existem), *IDOR/BOLA* (acessar objeto alheio
trocando um id), *CSRF* (forçar ação em nome da vítima), *XSS* (executar script na página da
vítima), *HSTS* (obrigar HTTPS), *RBAC/ABAC* (controle por papel/atributo).

**Leituras recomendadas** (todas gratuitas):

- OWASP Cheat Sheet Series: *Authentication*, *Password Storage*, *Session Management*, *Cross-Site
  Request Forgery Prevention*, *Authorization* e *Forgot Password*:
  <https://cheatsheetseries.owasp.org/>
- OWASP Top 10: <https://owasp.org/www-project-top-ten/>
- NIST SP 800-63B (diretrizes de autenticação e senhas).
- RFC 6265 (cookies): <https://www.rfc-editor.org/rfc/rfc6265>
- RFC 9106 (Argon2): <https://www.rfc-editor.org/rfc/rfc9106>
- Documentação do Flask sobre segurança e das bibliotecas citadas: Flask-Login, Flask-WTF,
  Flask-Limiter, Flask-Talisman, `argon2-cffi`, `itsdangerous`, `pyotp`.
