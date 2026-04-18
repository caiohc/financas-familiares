import uuid
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from application.dtos.family_dtos import CreateFamilyDTO

family_bp = Blueprint('family', __name__, url_prefix='/family')

@family_bp.route('/')
def index():
    service = current_app.config['FAMILY_SERVICE']
    families = service.list_families()
    return render_template('family/index.html', families=families)

@family_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            service = current_app.config['FAMILY_SERVICE']
            dto = CreateFamilyDTO(name=name)
            service.create_family(dto)
            return redirect(url_for('family.index'))
    return render_template('family/form.html', family=None)

@family_bp.route('/<uuid:family_id>/update', methods=['GET', 'POST'])
def update(family_id):
    service = current_app.config['FAMILY_SERVICE']
    
    try:
        family_obj = service.get_family(family_id)
    except ValueError:
        return redirect(url_for('family.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            service.update_family(family_id, name)
            return redirect(url_for('family.index'))
            
    return render_template('family/form.html', family=family_obj)
