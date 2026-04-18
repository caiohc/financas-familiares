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
    CreditCardBillSQLiteRepository
)

from application.services.family_service import FamilyService
from application.services.financial_service import FinancialService

# 1. ESTADO GLOBAL DA APLICAÇÃO E CONFIGURAÇÃO DO BANCO
DATABASE_PATH = os.path.abspath('app.db')
check_and_create_tables(DATABASE_PATH)

db_family = FamilySQLiteRepository(DATABASE_PATH)
db_member = MemberSQLiteRepository(DATABASE_PATH)
db_bank_account = BankAccountSQLiteRepository(DATABASE_PATH)
db_credit_card = CreditCardSQLiteRepository(DATABASE_PATH)
db_transaction = TransactionSQLiteRepository(DATABASE_PATH)
db_credit_card_bill = CreditCardBillSQLiteRepository(DATABASE_PATH)

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

from interface.web.routes.family import family_bp
from interface.web.routes.member import member_bp

app.register_blueprint(family_bp)
app.register_blueprint(member_bp)

# --- ROTAS BASE DO SISTEMA ---
@app.route("/")
def home():
    try:
        families = db_family.list_all()
    except Exception:
        families = []
    
    return render_template("home.html", total_families=len(families))

if __name__ == "__main__":
    app.run(debug=True, port=8000)
