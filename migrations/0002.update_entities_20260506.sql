-- 0002.update_entities_20260506.sql
-- Reflete as mudanças nas entidades do domínio financeiro realizadas em 06/05/2026

-- 1. Atualizações em bank_accounts
ALTER TABLE bank_accounts RENAME COLUMN name TO nickname;

-- 2. Atualizações em credit_cards
ALTER TABLE credit_cards RENAME COLUMN name TO nickname;
ALTER TABLE credit_cards ADD COLUMN issuer TEXT DEFAULT '';
ALTER TABLE credit_cards ADD COLUMN tier TEXT DEFAULT '';

-- 3. Atualizações em credit_card_bills
ALTER TABLE credit_card_bills ADD COLUMN family_id TEXT;
ALTER TABLE credit_card_bills ADD COLUMN is_closed INTEGER DEFAULT 0;

-- 4. Atualizações em card_instances
ALTER TABLE card_instances ADD COLUMN family_id TEXT;
