-- Depende de: 0002.update_entities_20260506.sql
-- Backfill the family_id column for existing card_instances that were migrated
UPDATE card_instances
SET family_id = (
    SELECT family_id 
    FROM credit_cards 
    WHERE credit_cards.id = card_instances.credit_card_id
)
WHERE family_id IS NULL;

-- Backfill the family_id column for existing credit_card_bills that were migrated
UPDATE credit_card_bills
SET family_id = (
    SELECT family_id 
    FROM credit_cards 
    WHERE credit_cards.id = credit_card_bills.credit_card_id
)
WHERE family_id IS NULL;
