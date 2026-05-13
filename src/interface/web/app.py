import sys
import os

from flask import Flask, render_template

from infrastructure.database.setup import apply_migrations
from infrastructure.repositories.sqlite_repository import (
    FamilySQLiteRepository, MemberSQLiteRepository,
    BankAccountSQLiteRepository, CreditCardSQLiteRepository, TransactionSQLiteRepository,
    CreditCardBillSQLiteRepository, CategorySQLiteRepository
)

from application.services.family_service import FamilyService
from application.services.financial_service import FinancialService
from application.services.category_service import CategoryService
from infrastructure.database.bootstrap import bootstrap_categories
from config import DB_ABS_PATH, DEFAULT_CATEGORIES_ABS_PATH

# 1. ESTADO GLOBAL DA APLICAÇÃO E CONFIGURAÇÃO DO BANCO
DATABASE_PATH = str(DB_ABS_PATH)
apply_migrations(DATABASE_PATH)

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
category_service = CategoryService(category_repo=db_category)

app = Flask(__name__)
app.config['FAMILY_SERVICE'] = family_service
app.config['FINANCIAL_SERVICE'] = financial_service
app.config['CATEGORY_SERVICE'] = category_service

# Executa o Bootstrap de categorias usando base padrão
bootstrap_categories(category_service, str(DEFAULT_CATEGORIES_ABS_PATH))

from interface.web.routes.home import home_bp
from interface.web.routes.family import family_bp
from interface.web.routes.member import member_bp
from interface.web.routes.category import category_bp
from interface.web.routes.bank_account import bank_account_bp
from interface.web.routes.credit_card import credit_card_bp

app.register_blueprint(home_bp)
app.register_blueprint(family_bp)
app.register_blueprint(member_bp)
app.register_blueprint(category_bp)
app.register_blueprint(bank_account_bp)
app.register_blueprint(credit_card_bp)

if __name__ == "__main__":
    app.run(debug=True, port=8000)
