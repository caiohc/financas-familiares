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
                "INSERT INTO bank_accounts (id, family_id, holder_id, name, balance, ignores_consolidated_balance) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET balance=excluded.balance",
                (str(account.id), str(account.family_id), str(account.holder_id), account.name, 
                 account.current_balance, int(account.ignores_consolidated_balance))
            )

    def get_by_id(self, account_id: uuid.UUID) -> Optional[BankAccount]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM bank_accounts WHERE id = ?", (str(account_id),)).fetchone()
            if row:
                b = BankAccount(
                    family_id=uuid.UUID(row['family_id']), 
                    holder_id=uuid.UUID(row['holder_id']), 
                    name=row['name'], 
                    current_balance=row['balance'], 
                    ignores_consolidated_balance=bool(row['ignores_consolidated_balance'])
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
                    name=row['name'], 
                    current_balance=row['balance'], 
                    ignores_consolidated_balance=bool(row['ignores_consolidated_balance'])
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
                    name=row['name'], 
                    current_balance=row['balance'], 
                    ignores_consolidated_balance=bool(row['ignores_consolidated_balance'])
                )
                b.id = uuid.UUID(row['id'])
                res.append(b)
            return res


class CreditCardSQLiteRepository(CreditCardRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, cc: CreditCard) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO credit_cards (id, family_id, holder_id, name, limit_amount, due_day) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET limit_amount=excluded.limit_amount, due_day=excluded.due_day",
                (str(cc.id), str(cc.family_id), str(cc.holder_id), cc.name, cc.limit, cc.due_day)
            )

    def save_instance(self, ci: CardInstance) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO card_instances (id, credit_card_id, holder_id, nickname) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET nickname=excluded.nickname",
                (str(ci.id), str(ci.credit_card_id), str(ci.holder_id), ci.nickname)
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
                    name=row['name'],
                    limit=row['limit_amount'],
                    due_day=row['due_day']
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
                    name=row['name'],
                    limit=row['limit_amount'],
                    due_day=row['due_day']
                )
                c.id = uuid.UUID(row['id'])
                res.append(c)
            return res

    def get_instance_by_id(self, instance_id: uuid.UUID) -> Optional[CardInstance]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM card_instances WHERE id = ?", (str(instance_id),)).fetchone()
            if row:
                c = CardInstance(
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
                    credit_card_id=uuid.UUID(row['credit_card_id']),
                    holder_id=uuid.UUID(row['holder_id']),
                    nickname=row['nickname']
                )
                c.id = uuid.UUID(row['id'])
                res.append(c)
            return res


class CreditCardBillSQLiteRepository(CreditCardBillRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, bill: CreditCardBill) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO credit_card_bills (id, credit_card_id, reference_month, due_date, total_amount) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET total_amount=excluded.total_amount",
                (str(bill.id), str(bill.credit_card_id), bill.reference_month, str(bill.due_date), bill.total_amount)
            )

    def get_by_id(self, bill_id: uuid.UUID) -> Optional[CreditCardBill]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM credit_card_bills WHERE id = ?", (str(bill_id),)).fetchone()
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
                    date, is_realized, bank_account_id, credit_card_id, card_instance_id, 
                    credit_card_bill_id, installment_current, installment_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET is_realized=excluded.is_realized''',
                (
                    str(t.id), str(t.family_id), str(t.category_id), t.type_str, t.amount, t.description,
                    str(t.date), 1 if t.is_realized else 0,
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
        realized = True if row['is_realized'] == 1 else False if row['is_realized'] == 0 else None
        
        t = Transaction(
            family_id=uuid.UUID(row['family_id']),
            category_id=uuid.UUID(row['category_id']),
            type_str=row['type_str'],
            date=datetime.date(year, month, day),
            amount=row['amount'],
            description=row['description'],
            is_realized=realized,
            bank_account_id=uuid.UUID(row['bank_account_id']) if row['bank_account_id'] else None,
            credit_card_id=uuid.UUID(row['credit_card_id']) if row['credit_card_id'] else None,
            card_instance_id=uuid.UUID(row['card_instance_id']) if row['card_instance_id'] else None,
            credit_card_bill_id=uuid.UUID(row['credit_card_bill_id']) if row['credit_card_bill_id'] else None,
            installment_current=row['installment_current'],
            installment_total=row['installment_total']
        )
        t.id = uuid.UUID(row['id'])
        return t
