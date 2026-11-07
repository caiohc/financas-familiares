import uuid

from flask import Blueprint, request, redirect, render_template, url_for, current_app, flash, abort
from flask_login import current_user

from application.dtos.identity_dtos import CreateUserDTO, UpdateUserDTO
from application.services.family_service import FamilyService
from application.services.user_service import UserService
from domain.identity import policy
from domain.identity.entities import Role
from domain.shared.exceptions import (
    AccessDeniedError,
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)

from interface.web.labels import family_label_parts

bp = Blueprint('user', __name__)


@bp.before_request
def require_user_manager():
    """A área de usuários é só de quem administra contas. Usuário de família comum recebe 403."""
    if not policy.can_manage_users(current_user.principal):
        abort(403)


def get_user_service() -> UserService:
    """Resolve a dependência do Serviço de Usuário através da factory registrada no app."""
    return current_app.user_service_factory()

def get_family_service() -> FamilyService:
    """Resolve a dependência do Serviço de Família através da factory registrada no app."""
    return current_app.family_service_factory()

def _actor():
    """Quem está agindo, vindo SEMPRE da sessão (nunca de campo de formulário)."""
    return current_user.principal

def _render_form(form_action, user=None, form: dict | None = None, error: str | None = None, status: int = 200):
    # O administrador do sistema escolhe a família; o da família só cadastra na própria. Papel e família
    # não mudam depois de criados. Senha não existe aqui: quem a define é o próprio usuário, pelo convite.
    actor = _actor()
    families = get_family_service().list_families()
    if actor.family_id is not None:
        families = [f for f in families if f.id == actor.family_id]
    values = {"role": "", "family_id": "", "name": "", "username": "", "email": "", "email_confirmation": ""}
    if user:
        values.update(name=user.name or "", username=user.username, email=user.email)
    elif actor.family_id is not None:
        values["family_id"] = str(actor.family_id)
    values.update({key: value for key, value in (form or {}).items() if value is not None})
    context = {
        "form_action": form_action,
        "user": user,
        "families": families,
        "roles": policy.creatable_roles(actor),
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
    return {key: request.form.get(key) for key in ("role", "family_id", "name", "username", "email", "email_confirmation")}

def _abilities(page_users) -> dict:
    """O que o ator pode fazer em cada linha da listagem (a regra é a mesma do serviço; aqui só decide o que mostrar)."""
    actor = _actor()
    result = {}
    for user in page_users:
        can_manage = policy.can_manage_user(actor, user)
        can_invite = (
            policy.can_issue_invitation(actor, user)
            and user.is_active
            and (user.is_pending or user.role is Role.SYSTEM_ADMIN)
        )
        result[user.id] = {
            "edit": can_manage,
            "invite": can_invite,
            "invite_label": "Reenviar convite" if user.is_pending else "Redefinir senha",
            "deactivate": can_manage and user.is_active and user.id != actor.user_id,
            "reactivate": can_manage and not user.is_active,
            "delete": can_manage and user.id != actor.user_id,
        }
    return result

@bp.route('/new', methods=['GET'])
def new():
    return _render_form(form_action=url_for('user.create'))

@bp.route('/create', methods=['POST'])
def create():
    form = _form_values()
    actor = _actor()
    family_id = _parse_uuid(form["family_id"])
    if family_id is None and actor.family_id is not None:
        family_id = actor.family_id
    dto = CreateUserDTO(
        role=_parse_role(form["role"]),
        family_id=family_id,
        name=form["name"],
        username=form["username"],
        email=form["email"],
        email_confirmation=form["email_confirmation"],
    )

    try:
        issued = get_user_service().create_user(actor, dto)
    except AccessDeniedError:
        abort(403)
    except (EntityAlreadyExistsError, DomainValidationError) as error:
        return _render_form(
            form_action=url_for('user.create'), form=form, error=str(error), status=_error_status(error),
        )
    except EntityNotFoundError as error:
        # A família escolhida deixou de existir: o pedido é inválido, não o recurso da URL.
        return _render_form(form_action=url_for('user.create'), form=form, error=str(error), status=400)

    # Não redireciona: o código de ativação aparece UMA vez, nesta resposta, e não fica guardado em lugar nenhum.
    return render_template('user/invitation_issued.html', issued=issued, reissued=False)

@bp.route('/edit/<uuid:user_id>', methods=['GET'])
def edit(user_id):
    service = get_user_service()
    try:
        user = service.get_user(_actor(), user_id)
    except EntityNotFoundError:
        abort(404)
    if not policy.can_manage_user(_actor(), user):
        abort(403)

    return _render_form(form_action=url_for('user.update', user_id=user_id), user=user)

@bp.route('/update/<uuid:user_id>', methods=['POST'])
def update(user_id):
    form = _form_values()

    service = get_user_service()
    try:
        service.update_user(
            _actor(), user_id, UpdateUserDTO(name=form["name"], username=form["username"], email=form["email"])
        )
    except AccessDeniedError:
        abort(403)
    except (EntityAlreadyExistsError, DomainValidationError) as error:
        try:
            user = service.get_user(_actor(), user_id)
        except EntityNotFoundError:
            abort(404)
        return _render_form(
            form_action=url_for('user.update', user_id=user_id),
            user=user, form=form, error=str(error), status=_error_status(error),
        )
    except EntityNotFoundError:
        abort(404)

    flash(f'Usuário "{(form["username"] or "").strip()}" atualizado com sucesso.', "success")

    return redirect(url_for('user.list_users'))

@bp.route('/confirm-delete/<uuid:user_id>', methods=['GET'])
def confirm_delete(user_id):
    try:
        preview = get_user_service().preview_user_deletion(_actor(), user_id)
    except AccessDeniedError:
        abort(403)
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
        get_user_service().delete_user(_actor(), user_id)
    except AccessDeniedError:
        abort(403)
    except EntityNotFoundError:
        abort(404)
    except (EntityHasDependenciesError, DomainValidationError) as error:
        flash(str(error), "error")
        return redirect(url_for('user.list_users'))

    flash("Usuário excluído com sucesso.", "success")

    return redirect(url_for('user.list_users'))

def _change_status(action, user_id, message: str):
    try:
        action(_actor(), user_id)
    except AccessDeniedError:
        abort(403)
    except EntityNotFoundError:
        abort(404)
    except DomainValidationError as error:
        flash(str(error), "error")
        return redirect(url_for('user.list_users'))

    flash(message, "success")
    return redirect(url_for('user.list_users'))

@bp.route('/deactivate/<uuid:user_id>', methods=['POST'])
def deactivate(user_id):
    return _change_status(get_user_service().deactivate_user, user_id, "Usuário desativado. O acesso foi encerrado.")

@bp.route('/reactivate/<uuid:user_id>', methods=['POST'])
def reactivate(user_id):
    return _change_status(get_user_service().reactivate_user, user_id, "Usuário reativado.")

@bp.route('/reissue-invitation/<uuid:user_id>', methods=['POST'])
def reissue_invitation(user_id):
    try:
        issued = get_user_service().issue_invitation(_actor(), user_id)
    except AccessDeniedError:
        abort(403)
    except EntityNotFoundError:
        abort(404)
    except DomainValidationError as error:
        flash(str(error), "error")
        return redirect(url_for('user.list_users'))

    return render_template('user/invitation_issued.html', issued=issued, reissued=True)

@bp.route('/list', methods=['GET'])
def list_users():
    """Administrador do sistema e root veem todos os usuários; o administrador da família, só os da sua família."""
    result = get_user_service().list_users_page(
        actor=_actor(),
        page=request.args.get('page', type=int),
        page_size=request.args.get('per_page', type=int),
        sort_by=request.args.get('sort'),
        sort_dir=request.args.get('dir'),
        search=request.args.get('q'),
    )
    families_by_id = {f.id: family_label_parts(f) for f in get_family_service().list_families()}
    return render_template(
        'user/index.html', users=result.items, pagination=result, families_by_id=families_by_id,
        abilities=_abilities(result.items),
    )
