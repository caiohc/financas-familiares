import json
from pathlib import Path

import click
from flask import Flask, current_app

from application.dtos.financial_dtos import CreateCategoryDTO
from domain.financial.entities import TransactionType
from domain.shared.exceptions import DomainValidationError


def register_category_commands(app: Flask) -> None:
    @app.cli.command("seed-categories")
    @click.option("--file", "file_path", default=None,
                  help="JSON com as categorias padrão. Padrão: CATEGORIES_PATH da configuração.")
    def seed_categories(file_path: str | None) -> None:
        """Carrega as categorias padrão no banco. Idempotente: as que já existem são ignoradas."""
        path = Path(file_path or current_app.config["CATEGORIES_PATH"])
        if not path.is_file():
            raise click.ClickException(f"Arquivo de categorias não encontrado: {path}")

        try:
            items = json.loads(path.read_text(encoding="utf-8"))
            defaults = [CreateCategoryDTO(name=item["name"], type=TransactionType(item["type"])) for item in items]
            result = current_app.category_service_factory().seed_default_categories(defaults)
        except (json.JSONDecodeError, KeyError, ValueError) as error:
            # DomainValidationError também é ValueError; nada é gravado nesses casos.
            detail = str(error) if isinstance(error, DomainValidationError) else repr(error)
            raise click.ClickException(f"Arquivo de categorias inválido ({path}): {detail}")

        click.echo(f"Categorias padrão: {result.created} criada(s), {result.skipped} já existia(m).")
