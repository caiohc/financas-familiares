from flask import Blueprint, request, redirect, render_template, url_for, current_app, flash, abort
from application.dtos.family_dtos import CreateFamilyDTO, UpdateFamilyDTO
from application.services.family_service import FamilyService
from domain.family.exceptions import (
    FamilyAlreadyExistsError,
    FamilyHasDependenciesError,
    FamilyNotFoundError,
)

bp = Blueprint('family', __name__)

def get_family_service() -> FamilyService:
    """Resolve a dependência do Serviço de Família através da factory registrada no app."""
    return current_app.family_service_factory()

def _render_form(form_action, family=None, name: str = "", error: str | None = None, status: int = 200):
    context = {"name": name, "error": error, "form_action": form_action, "family": family}
    return render_template('family/form.html', **context), status

@bp.route('/new', methods=['GET'])
def new():
    return _render_form(form_action=url_for('family.create'))

@bp.route('/create', methods=['POST'])
def create():
    name = request.form.get("name")

    dto = CreateFamilyDTO(name=name)
    service = get_family_service()
    try:
        service.create_family(dto)
    except FamilyAlreadyExistsError as error:
        return _render_form(form_action=url_for('family.create'), name=name, error=str(error), status=409)

    flash(f'Família "{name}" criada com sucesso.', "success")

    # PRG Pattern: Post -> Redirect -> Get
    return redirect(url_for('family.list_families'))

@bp.route('/edit/<uuid:family_id>', methods=['GET'])
def edit(family_id):
    service = get_family_service()
    try:
        family = service.get_family(family_id)
    except FamilyNotFoundError:
        abort(404)

    return _render_form(form_action=url_for('family.update', family_id=family_id), family=family)

@bp.route('/update/<uuid:family_id>', methods=['POST'])
def update(family_id):
    name = request.form.get("name")

    dto = UpdateFamilyDTO(name=name)
    service = get_family_service()
    try:
        service.update_family(family_id, dto)
    except FamilyAlreadyExistsError as error:
        return _render_form(
            form_action=url_for('family.update', family_id=family_id),
            name=name, error=str(error), status=409,
        )
    except FamilyNotFoundError:
        abort(404)

    flash(f'Família "{name}" atualizada com sucesso.', "success")

    return redirect(url_for('family.list_families'))

@bp.route('/delete/<uuid:family_id>', methods=['POST'])
def delete(family_id):
    service = get_family_service()
    try:
        service.delete_family(family_id)
    except FamilyNotFoundError:
        abort(404)
    except FamilyHasDependenciesError as error:
        flash(str(error), "error")
        return redirect(url_for('family.list_families'))

    flash("Família excluída com sucesso.", "success")

    return redirect(url_for('family.list_families'))

@bp.route('/list', methods=['GET'])
def list_families():
    service = get_family_service()
    families = service.list_families()
    return render_template('family/index.html', families=families)
