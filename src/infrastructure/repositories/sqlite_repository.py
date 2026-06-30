import sqlite3
import uuid
import datetime
from typing import Optional, List

from domain.financial.entities import (
    BankAccount, CardInstance, CreditCard, Family, Member, Transaction, CreditCardBill,
    Category, TransactionType
)
from domain.financial.repositories import (
    BankAccountRepository, CreditCardRepository, FamilyRepository, 
    MemberRepository, TransactionRepository, CreditCardBillRepository,
    CategoryRepository
)

def get_connection(db_path: str):
    """Fábrica de portas lógicas para o Disco. Garante tradução amigável pra dictonary."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

class FamilySQLiteRepository(FamilyRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, family: Family) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO families (id, name) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name",
                (str(family.id), family.name)
            )

    def get_by_id(self, family_id: uuid.UUID) -> Optional[Family]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM families WHERE id = ?", (str(family_id),)).fetchone()
            if row:
                f = Family(name=row['name'])
                f.id = uuid.UUID(row['id'])
                return f
        return None

    def list_all(self) -> list[Family]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM families").fetchall()
            result = []
            for r in rows:
                f = Family(name=r['name'])
                f.id = uuid.UUID(r['id'])
                result.append(f)
            return result

    def delete(self, family_id: uuid.UUID) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM families WHERE id = ?", (str(family_id),))

    def has_dependencies(self, family_id: uuid.UUID) -> bool:
        with get_connection(self.db_path) as conn:
            id_str = str(family_id)
            if conn.execute("SELECT 1 FROM members WHERE family_id = ? LIMIT 1", (id_str,)).fetchone(): return True
            if conn.execute("SELECT 1 FROM bank_accounts WHERE family_id = ? LIMIT 1", (id_str,)).fetchone(): return True
            if conn.execute("SELECT 1 FROM credit_cards WHERE family_id = ? LIMIT 1", (id_str,)).fetchone(): return True
            if conn.execute("SELECT 1 FROM transactions WHERE family_id = ? LIMIT 1", (id_str,)).fetchone(): return True
            if conn.execute("SELECT 1 FROM credit_card_bills WHERE family_id = ? LIMIT 1", (id_str,)).fetchone(): return True
            # card_instances possui family_id desde a migração 0002
            if conn.execute("SELECT 1 FROM card_instances WHERE family_id = ? LIMIT 1", (id_str,)).fetchone(): return True
            return False


class MemberSQLiteRepository(MemberRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, member: Member) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO members (id, family_id, name) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, family_id=excluded.family_id",
                (str(member.id), str(member.family_id), member.name)
            )

    def get_by_id(self, member_id: uuid.UUID) -> Optional[Member]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM members WHERE id = ?", (str(member_id),)).fetchone()
            if row:
                m = Member(family_id=uuid.UUID(row['family_id']), name=row['name'])
                m.id = uuid.UUID(row['id'])
                return m
        return None

    def list_by_family(self, family_id: uuid.UUID) -> list[Member]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM members WHERE family_id = ?", (str(family_id),)).fetchall()
            return self._map(rows)

    def list_all(self) -> list[Member]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM members").fetchall()
            return self._map(rows)

    def _map(self, rows) -> list[Member]:
        res = []
        for r in rows:
            m = Member(family_id=uuid.UUID(r['family_id']), name=r['name'])
            m.id = uuid.UUID(r['id'])
            res.append(m)
        return res

    def delete(self, member_id: uuid.UUID) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM members WHERE id = ?", (str(member_id),))

    def has_dependencies(self, member_id: uuid.UUID) -> bool:
        with get_connection(self.db_path) as conn:
            id_str = str(member_id)
            if conn.execute("SELECT 1 FROM bank_accounts WHERE holder_id = ? LIMIT 1", (id_str,)).fetchone(): return True
            if conn.execute("SELECT 1 FROM credit_cards WHERE holder_id = ? LIMIT 1", (id_str,)).fetchone(): return True
            if conn.execute("SELECT 1 FROM card_instances WHERE holder_id = ? LIMIT 1", (id_str,)).fetchone(): return True
            return False


class CategorySQLiteRepository(CategoryRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, category: Category) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO categories (id, name, type_str) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, type_str=excluded.type_str",
                (str(category.id), category.name, category.type.value)
            )

    def get_by_id(self, category_id: uuid.UUID) -> Optional[Category]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM categories WHERE id = ?", (str(category_id),)).fetchone()
            if row:
                c = Category(name=row['name'], type=TransactionType(row['type_str']))
                c.id = uuid.UUID(row['id'])
                return c
        return None

    def list_all(self) -> list[Category]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM categories").fetchall()
            result = []
            for r in rows:
                c = Category(name=r['name'], type=TransactionType(r['type_str']))
                c.id = uuid.UUID(r['id'])
                result.append(c)
            return result

    def list_by_type(self, type_str: str) -> list[Category]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM categories WHERE type_str = ?", (type_str,)).fetchall()
            result = []
            for r in rows:
                c = Category(name=r['name'], type=TransactionType(r['type_str']))
                c.id = uuid.UUID(r['id'])
                result.append(c)
            return result

    def delete(self, category_id: uuid.UUID) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM categories WHERE id = ?", (str(category_id),))



class BankAccountSQLiteRepository(BankAccountRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, account: BankAccount) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO bank_accounts (id, family_id, holder_id, nickname, bank, agency, account_number, balance, ignores_consolidated_balance) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET nickname=excluded.nickname, bank=excluded.bank, agency=excluded.agency, account_number=excluded.account_number, balance=excluded.balance",
                (str(account.id), str(account.family_id), str(account.holder_id), account.nickname, account.bank, account.agency, account.account_number, 
                 account.current_balance, 0) # ignores_consolidated_balance removido da entidade mas mantido no banco por segurança ou v0
            )

    def get_by_id(self, account_id: uuid.UUID) -> Optional[BankAccount]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM bank_accounts WHERE id = ?", (str(account_id),)).fetchone()
            if row:
                b = BankAccount(
                    family_id=uuid.UUID(row['family_id']), 
                    holder_id=uuid.UUID(row['holder_id']), 
                    nickname=row['nickname'], 
                    bank=row['bank'] if 'bank' in row.keys() else "",
                    agency=row['agency'] if 'agency' in row.keys() else "",
                    account_number=row['account_number'] if 'account_number' in row.keys() else "",
                    current_balance=row['balance']
                )
                b.id = uuid.UUID(row['id'])
                return b
        return None

    def list_by_family(self, family_id: uuid.UUID) -> list[BankAccount]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM bank_accounts WHERE family_id = ?", (str(family_id),)).fetchall()
            res = []
            for row in rows:
                b = BankAccount(
                    family_id=uuid.UUID(row['family_id']), 
                    holder_id=uuid.UUID(row['holder_id']), 
                    nickname=row['nickname'], 
                    bank=row['bank'] if 'bank' in row.keys() else None,
                    agency=row['agency'] if 'agency' in row.keys() else None,
                    account_number=row['account_number'] if 'account_number' in row.keys() else None,
                    current_balance=row['balance']
                )
                b.id = uuid.UUID(row['id'])
                res.append(b)
            return res

    def list_all(self) -> list[BankAccount]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM bank_accounts").fetchall()
            res = []
            for row in rows:
                b = BankAccount(
                    family_id=uuid.UUID(row['family_id']), 
                    holder_id=uuid.UUID(row['holder_id']), 
                    nickname=row['nickname'], 
                    bank=row['bank'] if 'bank' in row.keys() else None,
                    agency=row['agency'] if 'agency' in row.keys() else None,
                    account_number=row['account_number'] if 'account_number' in row.keys() else None,
                    current_balance=row['balance']
                )
                b.id = uuid.UUID(row['id'])
                res.append(b)
            return res

    def delete(self, account_id: uuid.UUID) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM bank_accounts WHERE id = ?", (str(account_id),))


class CreditCardSQLiteRepository(CreditCardRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, cc: CreditCard) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO credit_cards (id, family_id, holder_id, nickname, issuer, brand, tier, limit_amount, due_day, bank_account_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET nickname=excluded.nickname, issuer=excluded.issuer, brand=excluded.brand, tier=excluded.tier, limit_amount=excluded.limit_amount, due_day=excluded.due_day, bank_account_id=excluded.bank_account_id",
                (str(cc.id), str(cc.family_id), str(cc.holder_id), cc.nickname, cc.issuer, cc.brand, cc.tier, cc.limit, cc.due_day, str(cc.bank_account_id) if cc.bank_account_id else None)
            )

    def save_instance(self, ci: CardInstance) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO card_instances (id, family_id, credit_card_id, holder_id, nickname) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET nickname=excluded.nickname",
                (str(ci.id), str(ci.family_id), str(ci.credit_card_id), str(ci.holder_id), ci.nickname)
            )

    def list_instances_by_family(self, family_id: uuid.UUID) -> list[CardInstance]:
        with get_connection(self.db_path) as conn:
            # Join equivalente para pesquisar pelos Master Cards da Família
            query = """
            SELECT ci.* FROM card_instances ci
            INNER JOIN credit_cards cc ON cc.id = ci.credit_card_id
            WHERE cc.family_id = ?
            """
            rows = conn.execute(query, (str(family_id),)).fetchall()
            res = []
            for r in rows:
                c = CardInstance(
                    family_id=uuid.UUID(r['family_id']) if r['family_id'] else uuid.UUID(int=0),
                    credit_card_id=uuid.UUID(r['credit_card_id']),
                    holder_id=uuid.UUID(r['holder_id']),
                    nickname=r['nickname']
                )
                c.id = uuid.UUID(r['id'])
                res.append(c)
            return res

    def get_by_id(self, credit_card_id: uuid.UUID) -> Optional[CreditCard]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM credit_cards WHERE id = ?", (str(credit_card_id),)).fetchone()
            if row:
                c = CreditCard(
                    family_id=uuid.UUID(row['family_id']),
                    holder_id=uuid.UUID(row['holder_id']),
                    nickname=row['nickname'],
                    issuer=row['issuer'] if 'issuer' in row.keys() else '',
                    brand=row['brand'] if 'brand' in row.keys() and row['brand'] else 'Desconhecida',
                    tier=row['tier'] if 'tier' in row.keys() else '',
                    limit=row['limit_amount'],
                    due_day=row['due_day'],
                    bank_account_id=uuid.UUID(row['bank_account_id']) if 'bank_account_id' in row.keys() and row['bank_account_id'] else None
                )
                c.id = uuid.UUID(row['id'])
                return c
        return None

    def list_all(self) -> list[CreditCard]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM credit_cards").fetchall()
            res = []
            for row in rows:
                c = CreditCard(
                    family_id=uuid.UUID(row['family_id']),
                    holder_id=uuid.UUID(row['holder_id']),
                    nickname=row['nickname'],
                    issuer=row['issuer'] if 'issuer' in row.keys() else '',
                    brand=row['brand'] if 'brand' in row.keys() and row['brand'] else 'Desconhecida',
                    tier=row['tier'] if 'tier' in row.keys() else '',
                    limit=row['limit_amount'],
                    due_day=row['due_day'],
                    bank_account_id=uuid.UUID(row['bank_account_id']) if 'bank_account_id' in row.keys() and row['bank_account_id'] else None
                )
                c.id = uuid.UUID(row['id'])
                res.append(c)
            return res

    def get_instance_by_id(self, instance_id: uuid.UUID) -> Optional[CardInstance]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM card_instances WHERE id = ?", (str(instance_id),)).fetchone()
            if row:
                c = CardInstance(
                    family_id=uuid.UUID(row['family_id']) if row['family_id'] else uuid.UUID(int=0),
                    credit_card_id=uuid.UUID(row['credit_card_id']),
                    holder_id=uuid.UUID(row['holder_id']),
                    nickname=row['nickname']
                )
                c.id = uuid.UUID(row['id'])
                return c
        return None

    def list_all_instances(self) -> list[CardInstance]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM card_instances").fetchall()
            res = []
            for row in rows:
                c = CardInstance(
                    family_id=uuid.UUID(row['family_id']) if row['family_id'] else uuid.UUID(int=0),
                    credit_card_id=uuid.UUID(row['credit_card_id']),
                    holder_id=uuid.UUID(row['holder_id']),
                    nickname=row['nickname']
                )
                c.id = uuid.UUID(row['id'])
                res.append(c)
            return res

    def delete(self, credit_card_id: uuid.UUID) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM credit_cards WHERE id = ?", (str(credit_card_id),))

    def delete_instance(self, instance_id: uuid.UUID) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM card_instances WHERE id = ?", (str(instance_id),))


class CreditCardBillSQLiteRepository(CreditCardBillRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, bill: CreditCardBill) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO credit_card_bills (id, family_id, credit_card_id, reference_month, due_date, is_closed, total_amount) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET total_amount=excluded.total_amount, is_closed=excluded.is_closed",
                (str(bill.id), str(bill.family_id), str(bill.credit_card_id), bill.reference_month, str(bill.due_date), 1 if bill.is_closed else 0, bill.total_amount)
            )

    def get_by_id(self, bill_id: uuid.UUID) -> Optional[CreditCardBill]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM credit_card_bills WHERE id = ?", (str(bill_id),)).fetchone()
            if row:
                year, month, day = map(int, row['due_date'].split('-'))
                dt = datetime.date(year, month, day)
                b = CreditCardBill(
                    family_id=uuid.UUID(row['family_id']) if row['family_id'] else uuid.UUID(int=0),
                    credit_card_id=uuid.UUID(row['credit_card_id']),
                    reference_month=row['reference_month'],
                    due_date=dt,
                    is_closed=bool(row['is_closed']) if 'is_closed' in row.keys() else False
                )
                b.id = uuid.UUID(row['id'])
                b.total_amount = row['total_amount']
                return b
        return None

    def get_by_card_and_month(self, card_id: uuid.UUID, reference_month: str) -> Optional[CreditCardBill]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM credit_card_bills WHERE credit_card_id = ? AND reference_month = ?", 
                (str(card_id), reference_month)
            ).fetchone()
            if row:
                year, month, day = map(int, row['due_date'].split('-'))
                dt = datetime.date(year, month, day)
                b = CreditCardBill(
                    credit_card_id=uuid.UUID(row['credit_card_id']),
                    reference_month=row['reference_month'],
                    due_date=dt
                )
                b.id = uuid.UUID(row['id'])
                b.total_amount = row['total_amount']
                return b
        return None


class TransactionSQLiteRepository(TransactionRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, t: Transaction) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                '''INSERT INTO transactions (
                    id, family_id, category_id, type_str, amount, description, 
                    date, is_forecast, bank_account_id, credit_card_id, card_instance_id, 
                    credit_card_bill_id, installment_current, installment_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET is_forecast=excluded.is_forecast''',
                (
                    str(t.id), str(t.family_id), str(t.category_id), t.type.value, t.amount, t.description,
                    str(t.date), 1 if t.is_forecast else 0,
                    str(t.bank_account_id) if t.bank_account_id else None,
                    str(t.credit_card_id) if t.credit_card_id else None,
                    str(t.card_instance_id) if t.card_instance_id else None,
                    str(t.credit_card_bill_id) if t.credit_card_bill_id else None,
                    t.installment_current, t.installment_total
                )
            )

    def get_by_id(self, transaction_id: uuid.UUID) -> Optional[Transaction]:
        return self._fetch_one("SELECT * FROM transactions WHERE id = ?", (str(transaction_id),))

    def list_by_family(self, family_id: uuid.UUID) -> list[Transaction]:
        return self._fetch_all("SELECT * FROM transactions WHERE family_id = ?", (str(family_id),))

    def list_by_account(self, account_id: uuid.UUID) -> list[Transaction]:
        return self._fetch_all("SELECT * FROM transactions WHERE bank_account_id = ?", (str(account_id),))

    def list_by_credit_card_instance(self, card_instance_id: uuid.UUID) -> list[Transaction]:
        return self._fetch_all("SELECT * FROM transactions WHERE card_instance_id = ?", (str(card_instance_id),))

    def _fetch_one(self, query: str, args: tuple) -> Optional[Transaction]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(query, args).fetchone()
            if row: return self._map_row(row)
        return None

    def _fetch_all(self, query: str, args: tuple) -> list[Transaction]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, args).fetchall()
            return [self._map_row(r) for r in rows]

    def _map_row(self, row) -> Transaction:
        year, month, day = map(int, row['date'].split('-'))
        forecast = True if row['is_forecast'] == 1 else False if row['is_forecast'] == 0 else False
        
        t = Transaction(
            family_id=uuid.UUID(row['family_id']),
            category_id=uuid.UUID(row['category_id']),
            type=TransactionType(row['type_str']),
            date=datetime.date(year, month, day),
            amount=row['amount'],
            description=row['description'],
            is_forecast=forecast,
            bank_account_id=uuid.UUID(row['bank_account_id']) if row['bank_account_id'] else None,
            credit_card_id=uuid.UUID(row['credit_card_id']) if row['credit_card_id'] else None,
            card_instance_id=uuid.UUID(row['card_instance_id']) if row['card_instance_id'] else None,
            credit_card_bill_id=uuid.UUID(row['credit_card_bill_id']) if row['credit_card_bill_id'] else None,
            installment_current=row['installment_current'],
            installment_total=row['installment_total']
        )
        t.id = uuid.UUID(row['id'])
        return t
