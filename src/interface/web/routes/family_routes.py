from flask import Blueprint, request, redirect, render_template, url_for, current_app, flash
from application.dtos.family_dtos import CreateFamilyDTO
from application.services.family_service import FamilyService
from domain.family.exceptions import FamilyAlreadyExistsError

bp = Blueprint('family', __name__)

def get_family_service() -> FamilyService:
    """Resolve a dependência do Serviço de Família através da factory registrada no app."""
    return current_app.family_service_factory()

def _render_create_form(name: str = "", error: str | None = None, status: int = 200):
    context = {"name": name, "error": error, "form_action": url_for('family.create')}
    return render_template('family/form.html', **context), status

@bp.route('/new', methods=['GET'])
def new():
    return _render_create_form()

@bp.route('/create', methods=['POST'])
def create():
    name = request.form.get("name")

    dto = CreateFamilyDTO(name=name)
    service = get_family_service()
    try:
        service.create_family(dto)
    except FamilyAlreadyExistsError as error:
        return _render_create_form(name=name, error=str(error), status=409)

    flash(f'Família "{name}" criada com sucesso.', "success")

    # PRG Pattern: Post -> Redirect -> Get
    return redirect(url_for('family.list_families'))

@bp.route('/list', methods=['GET'])
def list_families():
    service = get_family_service()
    families = service.list_families()
    return render_template('family/index.html', families=families)
