import uuid
from decimal import Decimal
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
    cards_dict = {c.id: c.nickname for c in cards}
    accounts_dict = {a.id: a.nickname for a in service.list_all_bank_accounts()}
    
    return render_template('credit_card/index.html', cards=cards, instances=instances, families=families_dict, members=members_dict, cards_dict=cards_dict, accounts=accounts_dict)

@credit_card_bp.route('/create', methods=['GET', 'POST'])
def create():
    service = current_app.config['FINANCIAL_SERVICE']
    family_service = current_app.config['FAMILY_SERVICE']
    
    families_list = family_service.list_families()
    families_dict = {f.id: f.name for f in families_list}
    members_list = family_service.list_all_members()
    accounts_list = service.list_all_bank_accounts()
    
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        issuer = request.form.get('issuer')
        brand = request.form.get('brand')
        family_id_str = request.form.get('family_id')
        holder_id_str = request.form.get('holder_id')
        limit_str = request.form.get('limit')
        due_day_str = request.form.get('due_day')
        bank_account_id_str = request.form.get('bank_account_id')
        
        if brand and family_id_str and holder_id_str and limit_str and due_day_str:
            try:
                dto = CreateCreditCardDTO(
                    family_id=uuid.UUID(family_id_str), 
                    holder_id=uuid.UUID(holder_id_str), 
                    nickname=nickname if nickname else None,
                    issuer=issuer if issuer else None,
                    brand=brand,
                    limit=Decimal(limit_str),
                    due_day=int(due_day_str),
                    bank_account_id=uuid.UUID(bank_account_id_str) if bank_account_id_str else None
                )
                service.create_credit_card(dto)
                return redirect(url_for('credit_card.index'))
            except ValueError as e:
                return render_template('credit_card/form.html', card=None, families=families_list, families_dict=families_dict, members=members_list, accounts=accounts_list, error=str(e))
            
    return render_template('credit_card/form.html', card=None, families=families_list, families_dict=families_dict, members=members_list, accounts=accounts_list)

@credit_card_bp.route('/<uuid:card_id>/update', methods=['GET', 'POST'])
def update(card_id):
    service = current_app.config['FINANCIAL_SERVICE']
    family_service = current_app.config['FAMILY_SERVICE']
    
    families_list = family_service.list_families()
    families_dict = {f.id: f.name for f in families_list}
    members_list = family_service.list_all_members()
    accounts_list = service.list_all_bank_accounts()
    
    try:
        card_obj = service.get_credit_card(card_id)
    except ValueError:
        return redirect(url_for('credit_card.index'))
        
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        issuer = request.form.get('issuer')
        brand = request.form.get('brand')
        limit_str = request.form.get('limit')
        due_day_str = request.form.get('due_day')
        bank_account_id_str = request.form.get('bank_account_id')
        
        if brand and limit_str and due_day_str:
            try:
                # Se o campo não for enviado pelo form (por estar disabled), usamos o valor existente
                final_bank_account_id = uuid.UUID(bank_account_id_str) if bank_account_id_str else card_obj.bank_account_id
                
                service.update_credit_card(
                    card_id, 
                    nickname, 
                    issuer,
                    brand, 
                    Decimal(limit_str), 
                    int(due_day_str), 
                    final_bank_account_id
                )
                return redirect(url_for('credit_card.index'))
            except ValueError as e:
                return render_template('credit_card/form.html', card=card_obj, families=families_list, families_dict=families_dict, members=members_list, accounts=accounts_list, error=str(e))
            
    return render_template('credit_card/form.html', card=card_obj, families=families_list, families_dict=families_dict, members=members_list, accounts=accounts_list)

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
        
        if credit_card_id_str and holder_id_str:
            try:
                card_id = uuid.UUID(credit_card_id_str)
                card_obj = service.get_credit_card(card_id)
                
                dto = CreateCardInstanceDTO(
                    family_id=card_obj.family_id,
                    credit_card_id=card_id, 
                    holder_id=uuid.UUID(holder_id_str), 
                    nickname=nickname if nickname else None
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
        
        # O nickname agora é opcional, a lógica de fallback está no serviço
        try:
            service.update_card_instance(instance_id, nickname)
            return redirect(url_for('credit_card.index'))
        except ValueError as e:
            return render_template('credit_card/form_instance.html', instance=instance_obj, cards=cards_list, members=members_list, error=str(e))
            
    return render_template('credit_card/form_instance.html', instance=instance_obj, cards=cards_list, members=members_list)

@credit_card_bp.route('/<uuid:card_id>/delete', methods=['POST'])
def delete(card_id):
    service = current_app.config['FINANCIAL_SERVICE']
    
    try:
        service.delete_credit_card(card_id)
        return redirect(url_for('credit_card.index'))
    except ValueError as e:
        # Re-renderiza o index com a mensagem de erro
        cards = service.list_all_credit_cards()
        instances = service.list_all_card_instances()
        
        family_service = current_app.config['FAMILY_SERVICE']
        families_dict = {f.id: f.name for f in family_service.list_families()}
        members_dict = {m.id: m.name for m in family_service.list_all_members()}
        accounts_dict = {a.id: f"{a.bank} - {a.nickname}" for a in service.list_all_bank_accounts()}
        cards_dict = {c.id: c.nickname for c in cards}
        
        return render_template('credit_card/index.html', cards=cards, instances=instances, families=families_dict, members=members_dict, cards_dict=cards_dict, accounts=accounts_dict, error=str(e))

@credit_card_bp.route('/instance/<uuid:instance_id>/delete', methods=['POST'])
def delete_instance(instance_id):
    service = current_app.config['FINANCIAL_SERVICE']
    
    try:
        service.delete_card_instance(instance_id)
        return redirect(url_for('credit_card.index'))
    except ValueError as e:
        cards = service.list_all_credit_cards()
        instances = service.list_all_card_instances()
        
        family_service = current_app.config['FAMILY_SERVICE']
        families_dict = {f.id: f.name for f in family_service.list_families()}
        members_dict = {m.id: m.name for m in family_service.list_all_members()}
        accounts_dict = {a.id: f"{a.bank} - {a.nickname}" for a in service.list_all_bank_accounts()}
        cards_dict = {c.id: c.nickname for c in cards}
        
        return render_template('credit_card/index.html', cards=cards, instances=instances, families=families_dict, members=members_dict, cards_dict=cards_dict, accounts=accounts_dict, error=str(e))
