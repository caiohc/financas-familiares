import sys
import os

# Bypass obrigatório: O instalador `uv` destrói a variável PYTHONPATH por segurança para manter 
# o isolamento virtual. Essa manobra injeta nosso Dominio na raiz permitindo o run direto.
#sys.path.append(os.path.abspath('src'))

from flask import Flask, render_template

from infrastructure.database.setup import check_and_create_tables
from infrastructure.repositories.sqlite_repository import (
    FamilySQLiteRepository, MemberSQLiteRepository,
    BankAccountSQLiteRepository, CreditCardSQLiteRepository, TransactionSQLiteRepository,
    CreditCardBillSQLiteRepository, CategorySQLiteRepository
)

from application.services.family_service import FamilyService
from application.services.financial_service import FinancialService
from application.services.category_service import CategoryService
from infrastructure.database.bootstrap import bootstrap_categories

# 1. ESTADO GLOBAL DA APLICAÇÃO E CONFIGURAÇÃO DO BANCO
DATABASE_PATH = os.path.abspath('app.db')
check_and_create_tables(DATABASE_PATH)

db_family = FamilySQLiteRepository(DATABASE_PATH)
db_member = MemberSQLiteRepository(DATABASE_PATH)
db_bank_account = BankAccountSQLiteRepository(DATABASE_PATH)
db_credit_card = CreditCardSQLiteRepository(DATABASE_PATH)
db_transaction = TransactionSQLiteRepository(DATABASE_PATH)
db_credit_card_bill = CreditCardBillSQLiteRepository(DATABASE_PATH)
db_category = CategorySQLiteRepository(DATABASE_PATH)

# 2. INSTANCIAÇÃO DOS SERVIÇOS (Casos de uso)
# Inversão de Controle acontecendo no topo e injetando as dependências reais
family_service = FamilyService(family_repo=db_family, member_repo=db_member)
financial_service = FinancialService(
    bank_account_repo=db_bank_account,
    credit_card_repo=db_credit_card,
    member_repo=db_member,
    transaction_repo=db_transaction,
    credit_card_bill_repo=db_credit_card_bill
)

app = Flask(__name__)
app.config['FAMILY_SERVICE'] = family_service
app.config['FINANCIAL_SERVICE'] = financial_service

category_service = CategoryService(category_repo=db_category)
app.config['CATEGORY_SERVICE'] = category_service

# Executa o Bootstrap de categorias usando base padrão
DEFAULT_CATEGORIES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'default_categories.json'))
bootstrap_categories(category_service, DEFAULT_CATEGORIES_PATH)

from interface.web.routes.family import family_bp
from interface.web.routes.member import member_bp
from interface.web.routes.category import category_bp
from interface.web.routes.bank_account import bank_account_bp
from interface.web.routes.credit_card import credit_card_bp

app.register_blueprint(family_bp)
app.register_blueprint(member_bp)
app.register_blueprint(category_bp)
app.register_blueprint(bank_account_bp)
app.register_blueprint(credit_card_bp)

# --- ROTAS BASE DO SISTEMA ---
@app.route("/")
def home():
    counts = {}
    try:
        counts['Famílias'] = len(db_family.list_all())
        counts['Membros das Famílias'] = len(db_member.list_all())
        counts['Categorias de Orçamento'] = len(db_category.list_all())
        counts['Contas Bancárias'] = len(db_bank_account.list_all())
        counts['Cartões de Crédito Principais'] = len(db_credit_card.list_all())
        counts['Cartões (Instâncias/Plásticos)'] = len(db_credit_card.list_all_instances())
    except Exception as e:
        print(f"Erro ao obter métricas: {e}")
        counts = {}
        
    return render_template("home.html", counts=counts)

if __name__ == "__main__":
    app.run(debug=True, port=8000)
