-- 0001.initial_schema.sql
-- Esqueleto inicial do banco de dados

CREATE TABLE IF NOT EXISTS families (
    id TEXT PRIMARY KEY, 
    name TEXT
);

CREATE TABLE IF NOT EXISTS members (
    id TEXT PRIMARY KEY, 
    family_id TEXT, 
    name TEXT,
    FOREIGN KEY(family_id) REFERENCES families(id)
);

CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY, 
    name TEXT, 
    type_str TEXT
);

CREATE TABLE IF NOT EXISTS bank_accounts (
    id TEXT PRIMARY KEY, 
    family_id TEXT, 
    holder_id TEXT, 
    name TEXT, 
    bank TEXT DEFAULT '', 
    agency TEXT DEFAULT '', 
    account_number TEXT DEFAULT '', 
    balance REAL, 
    ignores_consolidated_balance INTEGER,
    FOREIGN KEY(family_id) REFERENCES families(id),
    FOREIGN KEY(holder_id) REFERENCES members(id)
);

CREATE TABLE IF NOT EXISTS credit_cards (
    id TEXT PRIMARY KEY, 
    family_id TEXT, 
    holder_id TEXT, 
    name TEXT, 
    brand TEXT DEFAULT 'Desconhecida', 
    limit_amount REAL, 
    due_day INTEGER, 
    bank_account_id TEXT,
    FOREIGN KEY(family_id) REFERENCES families(id),
    FOREIGN KEY(holder_id) REFERENCES members(id),
    FOREIGN KEY(bank_account_id) REFERENCES bank_accounts(id)
);

CREATE TABLE IF NOT EXISTS card_instances (
    id TEXT PRIMARY KEY, 
    credit_card_id TEXT, 
    holder_id TEXT, 
    nickname TEXT,
    FOREIGN KEY(credit_card_id) REFERENCES credit_cards(id),
    FOREIGN KEY(holder_id) REFERENCES members(id)
);

CREATE TABLE IF NOT EXISTS credit_card_bills (
    id TEXT PRIMARY KEY, 
    credit_card_id TEXT, 
    reference_month TEXT, 
    due_date TEXT, 
    total_amount REAL,
    FOREIGN KEY(credit_card_id) REFERENCES credit_cards(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY, 
    family_id TEXT, 
    category_id TEXT, 
    type_str TEXT, 
    amount REAL, 
    description TEXT, 
    date TEXT, 
    is_realized INTEGER, 
    bank_account_id TEXT, 
    credit_card_id TEXT, 
    card_instance_id TEXT, 
    credit_card_bill_id TEXT, 
    installment_current INTEGER, 
    installment_total INTEGER,
    FOREIGN KEY(family_id) REFERENCES families(id),
    FOREIGN KEY(category_id) REFERENCES categories(id),
    FOREIGN KEY(bank_account_id) REFERENCES bank_accounts(id),
    FOREIGN KEY(credit_card_id) REFERENCES credit_cards(id),
    FOREIGN KEY(card_instance_id) REFERENCES card_instances(id),
    FOREIGN KEY(credit_card_bill_id) REFERENCES credit_card_bills(id)
);
