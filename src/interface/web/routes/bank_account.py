import uuid
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from application.dtos.financial_dtos import CreateBankAccountDTO

bank_account_bp = Blueprint('bank_account', __name__, url_prefix='/bank_account')

@bank_account_bp.route('/')
def index():
    service = current_app.config['FINANCIAL_SERVICE']
    family_service = current_app.config['FAMILY_SERVICE']
    
    accounts = service.list_all_bank_accounts()
    
    # Dictionaries for display
    families_dict = {f.id: f.name for f in family_service.list_families()}
    members_dict = {m.id: m.name for m in family_service.list_all_members()}
    
    return render_template('bank_account/index.html', accounts=accounts, families=families_dict, members=members_dict)

@bank_account_bp.route('/create', methods=['GET', 'POST'])
def create():
    service = current_app.config['FINANCIAL_SERVICE']
    family_service = current_app.config['FAMILY_SERVICE']
    
    families_list = family_service.list_families()
    members_list = family_service.list_all_members()
    
    if request.method == 'POST':
        name = request.form.get('name')
        family_id_str = request.form.get('family_id')
        holder_id_str = request.form.get('holder_id')
        
        if name and family_id_str and holder_id_str:
            try:
                dto = CreateBankAccountDTO(
                    family_id=uuid.UUID(family_id_str), 
                    holder_id=uuid.UUID(holder_id_str), 
                    name=name
                )
                service.create_bank_account(dto)
                return redirect(url_for('bank_account.index'))
            except ValueError as e:
                return render_template('bank_account/form.html', account=None, families=families_list, members=members_list, error=str(e))
            
    return render_template('bank_account/form.html', account=None, families=families_list, members=members_list)

@bank_account_bp.route('/<uuid:account_id>/update', methods=['GET', 'POST'])
def update(account_id):
    service = current_app.config['FINANCIAL_SERVICE']
    family_service = current_app.config['FAMILY_SERVICE']
    
    families_list = family_service.list_families()
    members_list = family_service.list_all_members()
    
    try:
        account_obj = service.get_bank_account(account_id)
    except ValueError:
        return redirect(url_for('bank_account.index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        
        if name:
            try:
                service.update_bank_account(account_id, name)
                return redirect(url_for('bank_account.index'))
            except ValueError as e:
                return render_template('bank_account/form.html', account=account_obj, families=families_list, members=members_list, error=str(e))
            
    return render_template('bank_account/form.html', account=account_obj, families=families_list, members=members_list)
