from flask import Blueprint, request, redirect, render_template, url_for, current_app, flash, abort
from application.dtos.financial_dtos import CreateCategoryDTO, UpdateCategoryDTO
from application.services.category_service import CategoryService
from domain.financial.entities import TransactionType
from domain.shared.exceptions import (
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)

bp = Blueprint('category', __name__)

# Tipos oferecidos na interface. TRANSFER_IN/OUT existem no domínio, mas não
# fazem sentido como categoria escolhida pelo usuário.
TYPE_LABELS = {TransactionType.EXPENSE: "Despesa", TransactionType.INCOME: "Receita"}

def get_category_service() -> CategoryService:
    """Resolve a dependência do Serviço de Categoria através da factory registrada no app."""
    return current_app.category_service_factory()

def _parse_type(raw: str | None) -> TransactionType | None:
    # O controlador só traduz o formulário; se o tipo for inválido, quem recusa é o domínio.
    try:
        return TransactionType(raw)
    except ValueError:
        return None

def _render_form(form_action, category=None, name: str = "", selected_type=None,
                 error: str | None = None, status: int = 200):
    context = {
        "form_action": form_action,
        "category": category,
        "name": name,
        "selected_type": selected_type or (category.type if category else None),
        "type_labels": TYPE_LABELS,
        "error": error,
    }
    return render_template('category/form.html', **context), status

def _error_status(error: Exception) -> int:
    # Atributo inválido é erro do pedido (400); duplicidade é conflito com o estado existente (409).
    return 400 if isinstance(error, DomainValidationError) else 409

@bp.route('/new', methods=['GET'])
def new():
    return _render_form(form_action=url_for('category.create'))

@bp.route('/create', methods=['POST'])
def create():
    name = request.form.get("name")
    type_ = _parse_type(request.form.get("type"))

    try:
        get_category_service().create_category(CreateCategoryDTO(name=name, type=type_))
    except (EntityAlreadyExistsError, DomainValidationError) as error:
        return _render_form(
            form_action=url_for('category.create'),
            name=name, selected_type=type_, error=str(error), status=_error_status(error),
        )

    flash(f'Categoria "{name}" criada com sucesso.', "success")

    return redirect(url_for('category.list_categories'))

@bp.route('/edit/<uuid:category_id>', methods=['GET'])
def edit(category_id):
    try:
        category = get_category_service().get_category(category_id)
    except EntityNotFoundError:
        abort(404)

    return _render_form(form_action=url_for('category.update', category_id=category_id), category=category)

@bp.route('/update/<uuid:category_id>', methods=['POST'])
def update(category_id):
    name = request.form.get("name")
    type_ = _parse_type(request.form.get("type"))

    try:
        get_category_service().update_category(category_id, UpdateCategoryDTO(name=name, type=type_))
    except (EntityAlreadyExistsError, DomainValidationError) as error:
        return _render_form(
            form_action=url_for('category.update', category_id=category_id),
            name=name, selected_type=type_, error=str(error), status=_error_status(error),
        )
    except EntityNotFoundError:
        abort(404)

    flash(f'Categoria "{name}" atualizada com sucesso.', "success")

    return redirect(url_for('category.list_categories'))

@bp.route('/confirm-delete/<uuid:category_id>', methods=['GET'])
def confirm_delete(category_id):
    try:
        preview = get_category_service().preview_category_deletion(category_id)
    except EntityNotFoundError:
        abort(404)

    return render_template(
        'confirm_delete.html',
        title="Excluir categoria",
        question="Tem certeza que deseja excluir esta categoria?",
        item_name=preview.name,
        blocked_reason=preview.blocked_reason,
        delete_action=url_for('category.delete', category_id=category_id),
        cancel_url=url_for('category.list_categories'),
    )

@bp.route('/delete/<uuid:category_id>', methods=['POST'])
def delete(category_id):
    try:
        get_category_service().delete_category(category_id)
    except EntityNotFoundError:
        abort(404)
    except EntityHasDependenciesError as error:
        flash(str(error), "error")
        return redirect(url_for('category.list_categories'))

    flash("Categoria excluída com sucesso.", "success")

    return redirect(url_for('category.list_categories'))

@bp.route('/list', methods=['GET'])
def list_categories():
    categories = get_category_service().list_categories()
    return render_template('category/index.html', categories=categories, type_labels=TYPE_LABELS)
