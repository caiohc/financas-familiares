from flask import Blueprint, render_template, request, redirect, url_for, current_app

home_bp = Blueprint('home', __name__, url_prefix='/')

@home_bp.route('/')
def index():
    counts = {}
    family_service = current_app.config['FAMILY_SERVICE']
    financial_service = current_app.config['FINANCIAL_SERVICE']
    category_service = current_app.config['CATEGORY_SERVICE']
    try:
        counts['Famílias'] = len(family_service.list_families())
        counts['Membros das Famílias'] = len(family_service.list_all_members())
        counts['Categorias de Orçamento'] = len(category_service.list_all())
        counts['Contas Bancárias'] = len(financial_service.list_all_bank_accounts())
        counts['Cartões de Crédito Principais'] = len(financial_service.list_all_credit_cards())
        counts['Cartões (Instâncias/Plásticos)'] = len(financial_service.list_all_card_instances())
    except Exception as e:
        print(f"Erro ao obter métricas: {e}")
        counts = {}
        
    return render_template("home.html", counts=counts)
