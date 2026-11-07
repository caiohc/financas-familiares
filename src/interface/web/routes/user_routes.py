import uuid

from flask import Blueprint, request, redirect, render_template, url_for, current_app, flash, abort
from application.dtos.identity_dtos import CreateUserDTO, UpdateUserDTO
from application.services.family_service import FamilyService
from application.services.user_service import UserService
from domain.identity.entities import Role
from domain.shared.exceptions import (
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)

from interface.web.labels import family_label_parts

bp = Blueprint('user', __name__)

# O root nasce pelo comando create-root; por aqui só se cadastram os demais papéis.
CREATABLE_ROLES = (Role.SYSTEM_ADMIN, Role.FAMILY_ADMIN, Role.FAMILY_USER)

def get_user_service() -> UserService:
    """Resolve a dependência do Serviço de Usuário através da factory registrada no app."""
    return current_app.user_service_factory()

def get_family_service() -> FamilyService:
    """Resolve a dependência do Serviço de Família através da factory registrada no app."""
    return current_app.family_service_factory()

def _render_form(form_action, user=None, form: dict | None = None, error: str | None = None, status: int = 200):
    # Sem login ainda, a família é escolhida no formulário (criação) ou exibida
    # só para leitura (edição). Papel e família não mudam depois de criados.
    # A senha digitada nunca volta para o formulário.
    # Valores dos campos: o que a pessoa digitou (se houve envio) ou o que o usuário já tem.
    values = {"role": "", "family_id": "", "name": "", "username": "", "email": ""}
    if user:
        values.update(name=user.name or "", username=user.username, email=user.email)
    values.update({key: value for key, value in (form or {}).items() if value is not None})
    context = {
        "form_action": form_action,
        "user": user,
        "families": get_family_service().list_families(),
        "roles": CREATABLE_ROLES,
        "values": values,
        "error": error,
    }
    return render_template('user/form.html', **context), status

def _error_status(error: Exception) -> int:
    # Atributo inválido é erro do pedido (400); duplicidade é conflito com o estado existente (409).
    return 400 if isinstance(error, DomainValidationError) else 409

def _parse_uuid(raw: str | None) -> uuid.UUID | None:
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        abort(400)

def _parse_role(raw: str | None) -> Role | None:
    # Papel ausente é erro de validação do domínio; papel inexistente é pedido malformado.
    if not raw:
        return None
    try:
        return Role(raw)
    except ValueError:
        abort(400)

def _form_values() -> dict:
    return {key: request.form.get(key) for key in ("role", "family_id", "name", "username", "email")}

@bp.route('/new', methods=['GET'])
def new():
    return _render_form(form_action=url_for('user.create'))

@bp.route('/create', methods=['POST'])
def create():
    form = _form_values()
    dto = CreateUserDTO(
        role=_parse_role(form["role"]),
        family_id=_parse_uuid(form["family_id"]),
        name=form["name"],
        username=form["username"],
        email=form["email"],
        temporary_password=request.form.get("temporary_password"),
        temporary_password_confirmation=request.form.get("temporary_password_confirmation"),
    )

    try:
        get_user_service().create_user(dto)
    except (EntityAlreadyExistsError, DomainValidationError) as error:
        return _render_form(
            form_action=url_for('user.create'), form=form, error=str(error), status=_error_status(error),
        )
    except EntityNotFoundError as error:
        # A família escolhida deixou de existir: o pedido é inválido, não o recurso da URL.
        return _render_form(form_action=url_for('user.create'), form=form, error=str(error), status=400)

    flash(f'Usuário "{(dto.username or "").strip()}" cadastrado com sucesso.', "success")

    return redirect(url_for('user.list_users'))

@bp.route('/edit/<uuid:user_id>', methods=['GET'])
def edit(user_id):
    try:
        user = get_user_service().get_user(user_id)
    except EntityNotFoundError:
        abort(404)

    return _render_form(form_action=url_for('user.update', user_id=user_id), user=user)

@bp.route('/update/<uuid:user_id>', methods=['POST'])
def update(user_id):
    form = _form_values()

    service = get_user_service()
    try:
        service.update_user(
            user_id, UpdateUserDTO(name=form["name"], username=form["username"], email=form["email"])
        )
    except (EntityAlreadyExistsError, DomainValidationError) as error:
        return _render_form(
            form_action=url_for('user.update', user_id=user_id),
            user=service.get_user(user_id), form=form, error=str(error), status=_error_status(error),
        )
    except EntityNotFoundError:
        abort(404)

    flash(f'Usuário "{(form["username"] or "").strip()}" atualizado com sucesso.', "success")

    return redirect(url_for('user.list_users'))

@bp.route('/confirm-delete/<uuid:user_id>', methods=['GET'])
def confirm_delete(user_id):
    try:
        preview = get_user_service().preview_user_deletion(user_id)
    except EntityNotFoundError:
        abort(404)

    return render_template(
        'confirm_delete.html',
        title="Excluir usuário",
        question="Tem certeza que deseja excluir este usuário?",
        item_name=preview.name,
        blocked_reason=preview.blocked_reason,
        delete_action=url_for('user.delete', user_id=user_id),
        cancel_url=url_for('user.list_users'),
    )

@bp.route('/delete/<uuid:user_id>', methods=['POST'])
def delete(user_id):
    try:
        get_user_service().delete_user(user_id)
    except EntityNotFoundError:
        abort(404)
    except EntityHasDependenciesError as error:
        flash(str(error), "error")
        return redirect(url_for('user.list_users'))

    flash("Usuário excluído com sucesso.", "success")

    return redirect(url_for('user.list_users'))

@bp.route('/list', methods=['GET'])
def list_users():
    """
    Provisório: sem autenticação, lista os usuários de todas as famílias.
    Quando houver login, o administrador de família verá só os da sua família.
    """
    result = get_user_service().list_users_page(
        page=request.args.get('page', type=int),
        page_size=request.args.get('per_page', type=int),
        sort_by=request.args.get('sort'),
        sort_dir=request.args.get('dir'),
        search=request.args.get('q'),
    )
    families_by_id = {f.id: family_label_parts(f) for f in get_family_service().list_families()}
    return render_template(
        'user/index.html', users=result.items, pagination=result, families_by_id=families_by_id
    )
