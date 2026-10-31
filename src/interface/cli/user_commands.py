import click
from flask import Flask, current_app

from application.dtos.identity_dtos import CreateRootDTO
from domain.shared.exceptions import DomainValidationError, EntityAlreadyExistsError


def register_user_commands(app: Flask) -> None:
    @app.cli.command("create-root")
    @click.option("--username", prompt="Nome de usuário", help="Nome de usuário do root.")
    @click.option("--email", prompt="E-mail", help="E-mail do root.")
    @click.option("--password", prompt="Senha temporária", hide_input=True, confirmation_prompt=True,
                  help="Senha temporária; será obrigatório trocá-la no primeiro acesso. "
                       "Prefira o prompt: valores passados na linha de comando ficam no histórico do shell.")
    def create_root(username: str, email: str, password: str) -> None:
        """Cria o usuário root (o inicial, sem nome de pessoa). Só funciona enquanto não houver um."""
        dto = CreateRootDTO(username=username, email=email, temporary_password=password)
        try:
            root = current_app.user_service_factory().create_root(dto)
        except (DomainValidationError, EntityAlreadyExistsError) as error:
            raise click.ClickException(str(error))

        click.echo(f"Usuário root \"{root.username}\" criado. A senha deverá ser trocada no primeiro acesso.")
