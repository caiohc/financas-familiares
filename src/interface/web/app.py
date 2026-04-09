import sys
import os

# Bypass obrigatório: O instalador `uv` destrói a variável PYTHONPATH por segurança para manter 
# o isolamento virtual. Essa manobra injeta nosso Dominio na raiz permitindo o run direto.
sys.path.append(os.path.abspath('src'))

from flask import Flask, render_template

# A importação limpa respeitando as barreiras da nossa Clean Architecture
from infrastructure.repositories.in_memory import (
    FamilyMemoryRepository, MemberMemoryRepository,
    BankAccountMemoryRepository, CreditCardMemoryRepository, TransactionMemoryRepository
)

from application.services.family_service import FamilyService
from application.services.financial_service import FinancialService

# 1. ESTADO GLOBAL DA APLICAÇÃO (Singletons)
# Simulando o comportamento de um Banco de Dados durante a vida ativa do servidor
db_family = FamilyMemoryRepository()
db_member = MemberMemoryRepository()
db_bank_account = BankAccountMemoryRepository()
db_credit_card = CreditCardMemoryRepository()
db_transaction = TransactionMemoryRepository()

# 2. INSTANCIAÇÃO DOS SERVIÇOS (Casos de uso)
# Inversão de Controle acontecendo no topo e injetando as dependências reais
family_service = FamilyService(family_repo=db_family, member_repo=db_member)
financial_service = FinancialService(
    bank_account_repo=db_bank_account,
    credit_card_repo=db_credit_card,
    member_repo=db_member
)

app = Flask(__name__)

# --- ROTAS BASE DO SISTEMA ---
@app.route("/")
def home():
    # Passamos os contadores e dados abertos para o dashboard principal exibir
    familias = list(db_family._data.values())
    return render_template("home.html", total_families=len(familias))

if __name__ == "__main__":
    app.run(debug=True, port=8000)
