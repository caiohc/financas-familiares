from flask import Blueprint, render_template, url_for, current_app
from application.services.dashboard_service import DashboardService

bp = Blueprint('dashboard', __name__)

def get_dashboard_service() -> DashboardService:
    """Resolve a dependência do Serviço de Dashboard através da factory registrada no app."""
    return current_app.dashboard_service_factory()

@bp.route('/', methods=['GET'])
def index():
    counts = get_dashboard_service().get_entity_counts()

    # Rótulo, quantidade e listagem de cada entidade, na ordem em que aparecem na barra lateral.
    entities = [
        ("Famílias", counts.families, url_for('family.list_families')),
        ("Centros de custo", counts.cost_centers, url_for('family_cost_center.list_cost_centers')),
        ("Membros", counts.members, url_for('member.list_members')),
        ("Categorias", counts.categories, url_for('category.list_categories')),
    ]
    return render_template('home.html', entities=entities)
