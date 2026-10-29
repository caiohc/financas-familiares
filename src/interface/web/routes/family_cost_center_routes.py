import uuid

from flask import Blueprint, request, redirect, render_template, url_for, current_app, flash, abort
from application.dtos.family_dtos import CreateFamilyCostCenterDTO, UpdateFamilyCostCenterDTO
from application.services.family_cost_center_service import FamilyCostCenterService
from application.services.family_service import FamilyService
from domain.shared.exceptions import (
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)

bp = Blueprint('family_cost_center', __name__)

def get_family_cost_center_service() -> FamilyCostCenterService:
    """Resolve a dependência do Serviço de Centro de Custo através da factory registrada no app."""
    return current_app.family_cost_center_service_factory()

def get_family_service() -> FamilyService:
    """Resolve a dependência do Serviço de Família através da factory registrada no app."""
    return current_app.family_service_factory()

def _render_form(form_action, cost_center=None, family_id=None, name: str = "", description: str = "",
                 error: str | None = None, status: int = 200):
    # Sem login ainda, a família é escolhida no formulário (criação) ou exibida
    # só para leitura (edição): por isso o formulário sempre recebe as famílias.
    context = {
        "form_action": form_action,
        "cost_center": cost_center,
        "families": get_family_service().list_families(),
        "selected_family_id": family_id,
        "name": name,
        "description": description,
        "error": error,
    }
    return render_template('family_cost_center/form.html', **context), status

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
    return _render_form(form_action=url_for('family_cost_center.create'))

@bp.route('/create', methods=['POST'])
def create():
    family_id = _parse_family_id(request.form.get("family_id"))
    name = request.form.get("name")
    description = request.form.get("description")

    dto = CreateFamilyCostCenterDTO(family_id=family_id, name=name, description=description)
    try:
        get_family_cost_center_service().create_family_cost_center(dto)
    except (EntityAlreadyExistsError, DomainValidationError) as error:
        return _render_form(
            form_action=url_for('family_cost_center.create'),
            family_id=family_id, name=name, description=description or "",
            error=str(error), status=_error_status(error),
        )

    flash(f'Centro de custo "{name}" criado com sucesso.', "success")

    return redirect(url_for('family_cost_center.list_cost_centers'))

@bp.route('/edit/<uuid:cost_center_id>', methods=['GET'])
def edit(cost_center_id):
    try:
        cost_center = get_family_cost_center_service().get_family_cost_center(cost_center_id)
    except EntityNotFoundError:
        abort(404)

    return _render_form(
        form_action=url_for('family_cost_center.update', cost_center_id=cost_center_id),
        cost_center=cost_center,
    )

@bp.route('/update/<uuid:cost_center_id>', methods=['POST'])
def update(cost_center_id):
    name = request.form.get("name")
    description = request.form.get("description")

    dto = UpdateFamilyCostCenterDTO(name=name, description=description)
    service = get_family_cost_center_service()
    try:
        service.update_family_cost_center(cost_center_id, dto)
    except (EntityAlreadyExistsError, DomainValidationError) as error:
        return _render_form(
            form_action=url_for('family_cost_center.update', cost_center_id=cost_center_id),
            cost_center=service.get_family_cost_center(cost_center_id),
            name=name, description=description or "",
            error=str(error), status=_error_status(error),
        )
    except EntityNotFoundError:
        abort(404)

    flash(f'Centro de custo "{name}" atualizado com sucesso.', "success")

    return redirect(url_for('family_cost_center.list_cost_centers'))

@bp.route('/confirm-delete/<uuid:cost_center_id>', methods=['GET'])
def confirm_delete(cost_center_id):
    try:
        preview = get_family_cost_center_service().preview_family_cost_center_deletion(cost_center_id)
    except EntityNotFoundError:
        abort(404)

    return render_template(
        'confirm_delete.html',
        title="Excluir centro de custo",
        question="Tem certeza que deseja excluir este centro de custo?",
        item_name=preview.name,
        blocked_reason=preview.blocked_reason,
        delete_action=url_for('family_cost_center.delete', cost_center_id=cost_center_id),
        cancel_url=url_for('family_cost_center.list_cost_centers'),
    )

@bp.route('/delete/<uuid:cost_center_id>', methods=['POST'])
def delete(cost_center_id):
    try:
        get_family_cost_center_service().delete_family_cost_center(cost_center_id)
    except EntityNotFoundError:
        abort(404)
    except EntityHasDependenciesError as error:
        flash(str(error), "error")
        return redirect(url_for('family_cost_center.list_cost_centers'))

    flash("Centro de custo excluído com sucesso.", "success")

    return redirect(url_for('family_cost_center.list_cost_centers'))

@bp.route('/list', methods=['GET'])
def list_cost_centers():
    """
    Provisório: lista centros de custo de todas as famílias, sem escopo.
    Existe só porque não há autenticação/sessão de usuário ainda para
    resolver "a família do usuário atual". Revisitar quando login existir.
    """
    cost_centers = get_family_cost_center_service().list_all_family_cost_centers()
    families_by_id = {f.id: f.name for f in get_family_service().list_families()}
    cost_centers = sorted(cost_centers, key=lambda item: (families_by_id.get(item.family_id, "").lower(), item.name.lower()))
    return render_template(
        'family_cost_center/index.html', cost_centers=cost_centers, families_by_id=families_by_id
    )
