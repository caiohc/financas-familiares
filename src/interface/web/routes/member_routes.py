import uuid

from flask import Blueprint, request, redirect, render_template, url_for, current_app, flash, abort
from application.dtos.family_dtos import CreateMemberDTO, UpdateMemberDTO
from application.services.family_service import FamilyService
from application.services.member_service import MemberService
from domain.shared.exceptions import (
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)

bp = Blueprint('member', __name__)

def get_member_service() -> MemberService:
    """Resolve a dependência do Serviço de Membro através da factory registrada no app."""
    return current_app.member_service_factory()

def get_family_service() -> FamilyService:
    """Resolve a dependência do Serviço de Família através da factory registrada no app."""
    return current_app.family_service_factory()

def _render_form(form_action, member=None, family_id=None, name: str = "",
                 error: str | None = None, status: int = 200):
    # Sem login ainda, a família é escolhida no formulário (criação) ou exibida
    # só para leitura (edição): por isso o formulário sempre recebe as famílias.
    context = {
        "form_action": form_action,
        "member": member,
        "families": get_family_service().list_families(),
        "selected_family_id": family_id,
        "name": name,
        "error": error,
    }
    return render_template('member/form.html', **context), status

def _error_status(error: Exception) -> int:
    # Atributo inválido é erro do pedido (400); duplicidade é conflito com o estado existente (409).
    return 400 if isinstance(error, DomainValidationError) else 409

def _parse_family_id(raw: str | None) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except (TypeError, ValueError):
        abort(400)

@bp.route('/new', methods=['GET'])
def new():
    return _render_form(form_action=url_for('member.create'))

@bp.route('/create', methods=['POST'])
def create():
    family_id = _parse_family_id(request.form.get("family_id"))
    name = request.form.get("name")

    try:
        get_member_service().create_member(CreateMemberDTO(family_id=family_id, name=name))
    except (EntityAlreadyExistsError, DomainValidationError) as error:
        return _render_form(
            form_action=url_for('member.create'),
            family_id=family_id, name=name, error=str(error), status=_error_status(error),
        )

    flash(f'Membro "{name}" cadastrado com sucesso.', "success")

    return redirect(url_for('member.list_members'))

@bp.route('/edit/<uuid:member_id>', methods=['GET'])
def edit(member_id):
    try:
        member = get_member_service().get_member(member_id)
    except EntityNotFoundError:
        abort(404)

    return _render_form(form_action=url_for('member.update', member_id=member_id), member=member)

@bp.route('/update/<uuid:member_id>', methods=['POST'])
def update(member_id):
    name = request.form.get("name")

    service = get_member_service()
    try:
        service.update_member(member_id, UpdateMemberDTO(name=name))
    except (EntityAlreadyExistsError, DomainValidationError) as error:
        return _render_form(
            form_action=url_for('member.update', member_id=member_id),
            member=service.get_member(member_id),
            name=name, error=str(error), status=_error_status(error),
        )
    except EntityNotFoundError:
        abort(404)

    flash(f'Membro "{name}" atualizado com sucesso.', "success")

    return redirect(url_for('member.list_members'))

@bp.route('/confirm-delete/<uuid:member_id>', methods=['GET'])
def confirm_delete(member_id):
    try:
        preview = get_member_service().preview_member_deletion(member_id)
    except EntityNotFoundError:
        abort(404)

    return render_template(
        'confirm_delete.html',
        title="Excluir membro",
        question="Tem certeza que deseja excluir este membro?",
        item_name=preview.name,
        blocked_reason=preview.blocked_reason,
        delete_action=url_for('member.delete', member_id=member_id),
        cancel_url=url_for('member.list_members'),
    )

@bp.route('/delete/<uuid:member_id>', methods=['POST'])
def delete(member_id):
    try:
        get_member_service().delete_member(member_id)
    except EntityNotFoundError:
        abort(404)
    except EntityHasDependenciesError as error:
        flash(str(error), "error")
        return redirect(url_for('member.list_members'))

    flash("Membro excluído com sucesso.", "success")

    return redirect(url_for('member.list_members'))

@bp.route('/list', methods=['GET'])
def list_members():
    """
    Provisório: lista membros de todas as famílias, sem escopo.
    Existe só porque não há autenticação/sessão de usuário ainda para
    resolver "a família do usuário atual". Revisitar quando login existir.
    """
    members = get_member_service().list_all_members()
    families_by_id = {f.id: f.name for f in get_family_service().list_families()}
    members = sorted(members, key=lambda item: (families_by_id.get(item.family_id, "").lower(), item.name.lower()))
    return render_template('member/index.html', members=members, families_by_id=families_by_id)
