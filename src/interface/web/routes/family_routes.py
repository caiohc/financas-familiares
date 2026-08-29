from flask import Blueprint, request, redirect, current_app
from application.dtos.family_dtos import CreateFamilyDTO
from application.services.family_service import FamilyService

bp = Blueprint('family', __name__)

def get_family_service() -> FamilyService:
    """Resolve a dependência do Serviço de Família através da factory registrada no app."""
    return current_app.family_service_factory()

@bp.route('/new', methods=['POST'])
def create():
    name = request.form.get("name")
    
    dto = CreateFamilyDTO(name=name)
    service = get_family_service()
    service.create_family(dto)
    
    # PRG Pattern: Post -> Redirect -> Get
    return redirect('/families')

@bp.route('', methods=['GET'])
def list_families():
    service = get_family_service()
    families = service.list_families()
    
    # Temporário: Retornamos os nomes como puro texto separados por vírgula.
    # No futuro, renderizaremos um template HTML passando as famílias (Jinja2).
    names = [f.name for f in families]
    return ", ".join(names), 200
