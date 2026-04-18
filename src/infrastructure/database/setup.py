import sqlite3
import os

def check_and_create_tables(db_path: str):
    """Gera a estrutura física do Banco de Dados no Disco na primeira inicialização."""
    
    # Certifica-se de que o diretório base exista
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Famílias e Membros
    cursor.execute('CREATE TABLE IF NOT EXISTS families (id TEXT PRIMARY KEY, name TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS members (id TEXT PRIMARY KEY, family_id TEXT, name TEXT)')
    
    # Categorias de Gastos (Caso passem a existir independentemente)
    cursor.execute('CREATE TABLE IF NOT EXISTS categories (id TEXT PRIMARY KEY, name TEXT)')
    
    # Financeiro Nativo
    cursor.execute('''CREATE TABLE IF NOT EXISTS bank_accounts (
        id TEXT PRIMARY KEY, family_id TEXT, holder_id TEXT, name TEXT, balance REAL, ignores_consolidated_balance INTEGER
    )''')
    
    # Cartões de Crédito (Master e Plástico) e Faturas
    cursor.execute('''CREATE TABLE IF NOT EXISTS credit_cards (
        id TEXT PRIMARY KEY, family_id TEXT, holder_id TEXT, name TEXT, limit_amount REAL, due_day INTEGER
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS card_instances (
        id TEXT PRIMARY KEY, credit_card_id TEXT, holder_id TEXT, nickname TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS credit_card_bills (
        id TEXT PRIMARY KEY, credit_card_id TEXT, reference_month TEXT, due_date TEXT, total_amount REAL
    )''')
    
    # Veia de Transações Gerais
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY, family_id TEXT, category_id TEXT, type_str TEXT, amount REAL, description TEXT, 
        date TEXT, is_realized INTEGER, bank_account_id TEXT, credit_card_id TEXT, card_instance_id TEXT, 
        credit_card_bill_id TEXT, installment_current INTEGER, installment_total INTEGER
    )''')
    
    conn.commit()
    conn.close()
