import uuid
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from application.dtos.financial_dtos import CreateCreditCardDTO, CreateCardInstanceDTO

credit_card_bp = Blueprint('credit_card', __name__, url_prefix='/credit_card')

@credit_card_bp.route('/')
def index():
    service = current_app.config['FINANCIAL_SERVICE']
    family_service = current_app.config['FAMILY_SERVICE']
    
    cards = service.list_all_credit_cards()
    instances = service.list_all_card_instances()
    
    families_dict = {f.id: f.name for f in family_service.list_families()}
    members_dict = {m.id: m.name for m in family_service.list_all_members()}
    cards_dict = {c.id: c.name for c in cards}
    
    return render_template('credit_card/index.html', cards=cards, instances=instances, families=families_dict, members=members_dict, cards_dict=cards_dict)

@credit_card_bp.route('/create', methods=['GET', 'POST'])
def create():
    service = current_app.config['FINANCIAL_SERVICE']
    family_service = current_app.config['FAMILY_SERVICE']
    
    families_list = family_service.list_families()
    members_list = family_service.list_all_members()
    
    if request.method == 'POST':
        name = request.form.get('name')
        family_id_str = request.form.get('family_id')
        holder_id_str = request.form.get('holder_id')
        limit_str = request.form.get('limit')
        due_day_str = request.form.get('due_day')
        
        if name and family_id_str and holder_id_str and limit_str and due_day_str:
            try:
                dto = CreateCreditCardDTO(
                    family_id=uuid.UUID(family_id_str), 
                    holder_id=uuid.UUID(holder_id_str), 
                    name=name,
                    limit=float(limit_str),
                    due_day=int(due_day_str)
                )
                service.create_credit_card(dto)
                return redirect(url_for('credit_card.index'))
            except ValueError as e:
                return render_template('credit_card/form.html', card=None, families=families_list, members=members_list, error=str(e))
            
    return render_template('credit_card/form.html', card=None, families=families_list, members=members_list)

@credit_card_bp.route('/<uuid:card_id>/update', methods=['GET', 'POST'])
def update(card_id):
    service = current_app.config['FINANCIAL_SERVICE']
    family_service = current_app.config['FAMILY_SERVICE']
    
    families_list = family_service.list_families()
    members_list = family_service.list_all_members()
    
    try:
        card_obj = service.get_credit_card(card_id)
    except ValueError:
        return redirect(url_for('credit_card.index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        limit_str = request.form.get('limit')
        due_day_str = request.form.get('due_day')
        
        if name and limit_str and due_day_str:
            try:
                service.update_credit_card(card_id, name, float(limit_str), int(due_day_str))
                return redirect(url_for('credit_card.index'))
            except ValueError as e:
                return render_template('credit_card/form.html', card=card_obj, families=families_list, members=members_list, error=str(e))
            
    return render_template('credit_card/form.html', card=card_obj, families=families_list, members=members_list)

@credit_card_bp.route('/instance/create', methods=['GET', 'POST'])
def create_instance():
    service = current_app.config['FINANCIAL_SERVICE']
    family_service = current_app.config['FAMILY_SERVICE']
    
    cards_list = service.list_all_credit_cards()
    members_list = family_service.list_all_members()
    
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        credit_card_id_str = request.form.get('credit_card_id')
        holder_id_str = request.form.get('holder_id')
        
        if nickname and credit_card_id_str and holder_id_str:
            try:
                dto = CreateCardInstanceDTO(
                    credit_card_id=uuid.UUID(credit_card_id_str), 
                    holder_id=uuid.UUID(holder_id_str), 
                    nickname=nickname
                )
                service.create_card_instance(dto)
                return redirect(url_for('credit_card.index'))
            except ValueError as e:
                return render_template('credit_card/form_instance.html', instance=None, cards=cards_list, members=members_list, error=str(e))
            
    return render_template('credit_card/form_instance.html', instance=None, cards=cards_list, members=members_list)

@credit_card_bp.route('/instance/<uuid:instance_id>/update', methods=['GET', 'POST'])
def update_instance(instance_id):
    service = current_app.config['FINANCIAL_SERVICE']
    family_service = current_app.config['FAMILY_SERVICE']
    
    cards_list = service.list_all_credit_cards()
    members_list = family_service.list_all_members()
    
    try:
        instance_obj = service.get_card_instance(instance_id)
    except ValueError:
        return redirect(url_for('credit_card.index'))
        
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        
        if nickname:
            try:
                service.update_card_instance(instance_id, nickname)
                return redirect(url_for('credit_card.index'))
            except ValueError as e:
                return render_template('credit_card/form_instance.html', instance=instance_obj, cards=cards_list, members=members_list, error=str(e))
            
    return render_template('credit_card/form_instance.html', instance=instance_obj, cards=cards_list, members=members_list)
