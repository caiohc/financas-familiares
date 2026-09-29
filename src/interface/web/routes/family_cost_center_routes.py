from flask import Blueprint, request, redirect, render_template, url_for, current_app, flash, abort
from application.dtos.family_dtos import CreateFamilyCostCenterDTO, UpdateFamilyCostCenterDTO
from application.services.family_cost_center_service import FamilyCostCenterService
from domain.family.exceptions import (
    FamilyCostCenterAlreadyExistsError,
    FamilyCostCenterNotFoundError,
)

bp = Blueprint('family_cost_center', __name__)

def get_family_cost_center_service() -> FamilyCostCenterService:
    """Resolve a dependência do Serviço de Centro de Custo através da factory registrada no app."""
    return current_app.family_cost_center_service_factory()

def _render_form(family_id, form_action, cost_center=None, name: str = "", description: str = "",
                  error: str | None = None, status: int = 200):
    context = {
        "family_id": family_id,
        "name": name,
        "description": description,
        "error": error,
        "form_action": form_action,
        "cost_center": cost_center,
    }
    return render_template('family_cost_center/form.html', **context), status

@bp.route('/family/<uuid:family_id>/cost-center/new', methods=['GET'])
def new(family_id):
    return _render_form(family_id, form_action=url_for('family_cost_center.create', family_id=family_id))

@bp.route('/family/<uuid:family_id>/cost-center/create', methods=['POST'])
def create(family_id):
    name = request.form.get("name")
    description = request.form.get("description")

    dto = CreateFamilyCostCenterDTO(family_id=family_id, name=name, description=description)
    service = get_family_cost_center_service()
    try:
        service.create_family_cost_center(dto)
    except FamilyCostCenterAlreadyExistsError as error:
        return _render_form(
            family_id,
            form_action=url_for('family_cost_center.create', family_id=family_id),
            name=name, description=description or "", error=str(error), status=409,
        )

    flash(f'Centro de custo "{name}" criado com sucesso.', "success")

    return redirect(url_for('family_cost_center.list_family_cost_centers', family_id=family_id))

@bp.route('/family/<uuid:family_id>/cost-center/edit/<uuid:cost_center_id>', methods=['GET'])
def edit(family_id, cost_center_id):
    service = get_family_cost_center_service()
    try:
        cost_center = service.get_family_cost_center(cost_center_id)
    except FamilyCostCenterNotFoundError:
        abort(404)

    return _render_form(
        family_id,
        form_action=url_for('family_cost_center.update', family_id=family_id, cost_center_id=cost_center_id),
        cost_center=cost_center,
    )

@bp.route('/family/<uuid:family_id>/cost-center/update/<uuid:cost_center_id>', methods=['POST'])
def update(family_id, cost_center_id):
    name = request.form.get("name")
    description = request.form.get("description")

    dto = UpdateFamilyCostCenterDTO(name=name, description=description)
    service = get_family_cost_center_service()
    try:
        service.update_family_cost_center(cost_center_id, dto)
    except FamilyCostCenterAlreadyExistsError as error:
        return _render_form(
            family_id,
            form_action=url_for('family_cost_center.update', family_id=family_id, cost_center_id=cost_center_id),
            name=name, description=description or "", error=str(error), status=409,
        )
    except FamilyCostCenterNotFoundError:
        abort(404)

    flash(f'Centro de custo "{name}" atualizado com sucesso.', "success")

    return redirect(url_for('family_cost_center.list_family_cost_centers', family_id=family_id))

@bp.route('/family/<uuid:family_id>/cost-center/delete/<uuid:cost_center_id>', methods=['POST'])
def delete(family_id, cost_center_id):
    service = get_family_cost_center_service()
    try:
        service.delete_family_cost_center(cost_center_id)
    except FamilyCostCenterNotFoundError:
        abort(404)

    flash("Centro de custo excluído com sucesso.", "success")

    return redirect(url_for('family_cost_center.list_family_cost_centers', family_id=family_id))

@bp.route('/family/<uuid:family_id>/cost-center/list', methods=['GET'])
def list_family_cost_centers(family_id):
    service = get_family_cost_center_service()
    cost_centers = service.list_family_cost_centers(family_id)
    return render_template('family_cost_center/index.html', family_id=family_id, cost_centers=cost_centers)
