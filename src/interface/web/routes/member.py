import uuid
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from application.dtos.family_dtos import CreateMemberDTO

member_bp = Blueprint('member', __name__, url_prefix='/member')

@member_bp.route('/')
def index():
    service = current_app.config['FAMILY_SERVICE']
    members = service.list_all_members()
    # Cacheia dicionário resolvendo ids para exibição imediata do Nome da Família daquele integrante
    families_dict = {f.id: f.name for f in service.list_families()} 
    return render_template('member/index.html', members=members, families=families_dict)

@member_bp.route('/create', methods=['GET', 'POST'])
def create():
    service = current_app.config['FAMILY_SERVICE']
    families_list = service.list_families()
    
    if request.method == 'POST':
        name = request.form.get('name')
        family_id_str = request.form.get('family_id')
        
        if name and family_id_str:
            dto = CreateMemberDTO(family_id=uuid.UUID(family_id_str), name=name)
            service.create_member(dto)
            return redirect(url_for('member.index'))
            
    return render_template('member/form.html', member=None, families=families_list)

@member_bp.route('/<uuid:member_id>/update', methods=['GET', 'POST'])
def update(member_id):
    service = current_app.config['FAMILY_SERVICE']
    families_list = service.list_families()
    
    try:
        member_obj = service.get_member(member_id)
    except ValueError:
        return redirect(url_for('member.index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        family_id_str = request.form.get('family_id')
        
        if name and family_id_str:
            service.update_member(member_id, name, uuid.UUID(family_id_str))
            return redirect(url_for('member.index'))
            
    return render_template('member/form.html', member=member_obj, families=families_list)
