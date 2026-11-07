"""
Comandos de CLI do usuário root: create-root, reset-root-password e change-root-email.

Rodam no servidor, por quem tem acesso a ele (é por isso que são o único caminho para mexer no root: nenhum
administrador age sobre o root pela aplicação, e o root não tem recuperação por e-mail).

As mensagens de erro saem em vermelho, sem traceback, e dizem o que fazer a seguir. Os valores que faltam são
perguntados; um valor inválido ou já em uso é explicado e perguntado de novo (se veio de uma opção, o comando
termina, porque repetir não adiantaria).
"""
from typing import Callable, Optional

import click
from flask import Flask, current_app

from application.dtos.identity_dtos import CreateRootDTO
from domain.shared.exceptions import DomainValidationError, EntityAlreadyExistsError, EntityNotFoundError

_PASSWORD_HELP = (
    "Senha digitada no terminal. Prefira o prompt: valores passados na linha de comando ficam no "
    "histórico do shell."
)

_HINTS = {
    "username": "Escolha outro nome de usuário para o root.",
    "email": (
        "O root não representa uma pessoa: use um e-mail só dele, diferente do e-mail das contas pessoais "
        "(cada e-mail só pode ser usado por uma conta)."
    ),
}


def _error(message: str, *hints: str) -> None:
    click.echo(click.style(f"✗ {message}", fg="red", bold=True), err=True)
    for hint in hints:
        click.echo(f"  {hint}", err=True)


def _fail(message: str, *hints: str) -> None:
    _error(message, *hints)
    raise click.exceptions.Exit(1)


def _ask(label: str, given: Optional[str], check: Callable[[str], str]) -> str:
    """Valor de uma opção ou, se não foi dada, perguntado até ser válido e estar livre."""
    value = given
    while True:
        if value is None:
            value = click.prompt(label).strip()
        try:
            return check(value)
        except (DomainValidationError, EntityAlreadyExistsError) as error:
            field = getattr(error, "field", "")
            _error(str(error), *([_HINTS[field]] if isinstance(error, EntityAlreadyExistsError) and field in _HINTS else []))
            if given is not None:
                raise click.exceptions.Exit(1)
            value = None


def register_user_commands(app: Flask) -> None:
    def users():
        return current_app.user_service_factory()

    @app.cli.command("create-root")
    @click.option("--username", default=None, help="Nome de usuário do root.")
    @click.option("--email", default=None, help="E-mail do root.")
    @click.option("--password", default=None, help=_PASSWORD_HELP)
    def create_root(username: Optional[str], email: Optional[str], password: Optional[str]) -> None:
        """Cria o usuário root (o inicial, sem nome de pessoa). Só pode existir um."""
        root = users().get_root()
        if root:
            _fail(
                "Já existe um usuário root. O sistema permite um único root, então um segundo não pode ser criado.",
                "Para trocar a senha dele:  flask reset-root-password",
                "Para trocar o e-mail dele: flask change-root-email",
            )

        username = _ask("Nome de usuário", username, users().check_root_username)
        email = _ask("E-mail", email, users().check_root_email)

        while True:
            typed = password if password is not None else click.prompt(
                "Senha", hide_input=True, confirmation_prompt=True,
            )
            # O prompt já confirmou a senha; o serviço confere de novo (a regra vale também fora da CLI).
            dto = CreateRootDTO(username=username, email=email, password=typed, password_confirmation=typed)
            try:
                created = users().create_root(dto)
                break
            except DomainValidationError as error:
                _error(str(error))
                if password is not None:
                    raise click.exceptions.Exit(1)
            except EntityAlreadyExistsError as error:
                _fail(str(error))        # alguém criou o root (ou usou o nome/e-mail) entre a pergunta e a gravação

        click.echo(click.style(f'✓ Usuário root "{created.username}" criado.', fg="green"))

    @app.cli.command("reset-root-password")
    @click.option("--password", default=None, help=_PASSWORD_HELP)
    def reset_root_password(password: Optional[str]) -> None:
        """Troca a senha do root. É o ÚNICO caminho: o root não tem recuperação por e-mail e nenhum
        administrador age sobre ele. Quem executa já tem acesso ao servidor."""
        if users().get_root() is None:
            _fail("Ainda não existe usuário root.", "Crie-o com:  flask create-root")

        while True:
            typed = password if password is not None else click.prompt(
                "Nova senha", hide_input=True, confirmation_prompt=True,
            )
            try:
                root = users().reset_root_password(typed, typed)
                break
            except DomainValidationError as error:
                _error(str(error))
                if password is not None:
                    raise click.exceptions.Exit(1)
            except EntityNotFoundError as error:
                _fail(str(error))

        click.echo(click.style(
            f'✓ Senha do root "{root.username}" redefinida. Os acessos abertos do root foram encerrados.', fg="green",
        ))

    @app.cli.command("change-root-email")
    @click.option("--email", default=None, help="Novo e-mail do root.")
    def change_root_email(email: Optional[str]) -> None:
        """Troca o e-mail do root. Pela aplicação ninguém altera o e-mail do root: só por este comando."""
        root = users().get_root()
        if root is None:
            _fail("Ainda não existe usuário root.", "Crie-o com:  flask create-root")

        click.echo(f'E-mail atual do root "{root.username}": {root.email}')

        def check(value: str) -> str:
            checked = users().check_root_email(value, ignore_user_id=root.id)
            if checked.casefold() == root.email.casefold():
                raise DomainValidationError("email", "O novo e-mail é igual ao atual.")
            return checked

        while True:
            new_email = _ask("Novo e-mail", email, check)
            confirmation = new_email if email is not None else click.prompt("Confirmar novo e-mail").strip()
            try:
                changed = users().change_root_email(new_email, confirmation)
                break
            except DomainValidationError as error:
                _error(str(error))
                if email is not None:
                    raise click.exceptions.Exit(1)
            except (EntityAlreadyExistsError, EntityNotFoundError) as error:
                _fail(str(error))

        click.echo(click.style(f'✓ E-mail do root "{changed.username}" alterado para {changed.email}.', fg="green"))
