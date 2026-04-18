import uuid

from application.dtos.financial_dtos import (
    CreateBankAccountDTO,
    CreateCardInstanceDTO,
    CreateCreditCardDTO,
    CreateCreditCardBillDTO,
    CreateTransactionDTO
)
from domain.financial.entities import BankAccount, CardInstance, CreditCard, CreditCardBill, Transaction, TransactionType
from domain.financial.repositories import (
    BankAccountRepository,
    CreditCardRepository,
    MemberRepository,
    TransactionRepository,
    CreditCardBillRepository
)
import datetime

class FinancialService:
    """Orquestra as lógicas e travas na manipulação de contas bancárias e cartões."""

    def __init__(
        self,
        bank_account_repo: BankAccountRepository,
        credit_card_repo: CreditCardRepository,
        member_repo: MemberRepository,
        transaction_repo: TransactionRepository,
        credit_card_bill_repo: CreditCardBillRepository
    ):
        self._bank_account_repo = bank_account_repo
        self._credit_card_repo = credit_card_repo
        self._member_repo = member_repo
        self._transaction_repo = transaction_repo
        self._credit_card_bill_repo = credit_card_bill_repo

    def _ensure_member_exists(self, member_id: uuid.UUID):
        """Função privada injetada para reuso visual da checagem primária de titularidade."""
        member = self._member_repo.get_by_id(member_id)
        if not member:
            raise ValueError(f"Membro {member_id} não encontrado no sistema.")
        return member

    def create_bank_account(self, dto: CreateBankAccountDTO) -> BankAccount:
        member = self._ensure_member_exists(dto.holder_id)
        
        # Validar cruzado: O id de família preenchido bate com a família originária do Membro titular?
        if member.family_id != dto.family_id:
            raise ValueError("Incoerência sistêmica: O titular fornecido não pertence à família selecionada.")

        account = BankAccount(
            family_id=dto.family_id,
            holder_id=dto.holder_id,
            name=dto.name
        )
        self._bank_account_repo.save(account)
        return account

    def create_credit_card(self, dto: CreateCreditCardDTO) -> CreditCard:
        member = self._ensure_member_exists(dto.holder_id)
        
        if member.family_id != dto.family_id:
            raise ValueError("O responsável legal do cartão não pertence à família informada.")

        card = CreditCard(
            family_id=dto.family_id,
            holder_id=dto.holder_id,
            name=dto.name,
            limit=dto.limit,
            due_day=dto.due_day
        )
        self._credit_card_repo.save(card)
        return card

    def create_card_instance(self, dto: CreateCardInstanceDTO) -> CardInstance:
        # Novamente exigimos certeza de que quem portará o plástico está no ecossistema
        # E com a arquitetura limpa, buscamos ele pelo repositório alheio perfeitamente.
        self._ensure_member_exists(dto.holder_id)
        
        # No futuro, nós injetaríamos o `_credit_card_repo.get_by_id(...)`
        # para validar se o id do master_card (dto.credit_card_id) também é verdadeiro no banco.
        
        instance = CardInstance(
            credit_card_id=dto.credit_card_id,
            holder_id=dto.holder_id,
            nickname=dto.nickname
        )
        self._credit_card_repo.save_instance(instance)
        return instance

    def create_credit_card_bill(self, dto: CreateCreditCardBillDTO) -> CreditCardBill:
        bill = CreditCardBill(
            credit_card_id=dto.credit_card_id,
            reference_month=dto.reference_month,
            due_date=dto.due_date
        )
        self._credit_card_bill_repo.save(bill)
        return bill

    def register_transaction(self, dto: CreateTransactionDTO) -> list[Transaction]:
        transactions_created = []
        t_type = TransactionType.INCOME if dto.type_str == "INCOME" else TransactionType.EXPENSE
        
        if dto.credit_card_id and dto.credit_card_bill_id:
            # Recuperar Cartão raiz
            card = self._credit_card_repo.get_by_id(dto.credit_card_id)
            if not card:
                raise ValueError("Contrato principal de Cartão de Crédito não localizado.")
                
            # Recuperar Fatura Base onde a transação parcelada começou
            base_bill = self._credit_card_bill_repo.get_by_id(dto.credit_card_bill_id)
            if not base_bill:
                raise ValueError("Fatura-mãe (Competência base) não existente.")
                
            year, month = map(int, base_bill.reference_month.split("-"))
            installment_val = dto.amount / dto.installment_total
            
            for i in range(1, dto.installment_total + 1):
                mo_offset = i - 1
                calc_mo = month + mo_offset
                
                target_year = year + ((calc_mo - 1) // 12)
                target_month = ((calc_mo - 1) % 12) + 1
                
                ref_month_str = f"{target_year}-{target_month:02d}"
                
                # Busca fatura do futuro ou cria on-the-fly
                target_bill = self._credit_card_bill_repo.get_by_card_and_month(card.id, ref_month_str)
                if not target_bill:
                    target_bill = CreditCardBill(
                        credit_card_id=card.id,
                        reference_month=ref_month_str,
                        due_date=datetime.date(target_year, target_month, card.due_day)
                    )
                    self._credit_card_bill_repo.save(target_bill)
                    
                t = Transaction(
                    family_id=dto.family_id,
                    category_id=dto.category_id,
                    type=t_type,
                    date=dto.date,
                    amount=round(installment_val, 2),
                    description=f"{dto.description} ({i}/{dto.installment_total})" if dto.installment_total > 1 else dto.description,
                    credit_card_bill_id=target_bill.id,
                    card_instance_id=dto.card_instance_id,
                    installment_current=i,
                    installment_total=dto.installment_total
                )
                target_bill.process_transaction(t)
                
                self._credit_card_bill_repo.save(target_bill)
                self._transaction_repo.save(t)
                transactions_created.append(t)
        else:
            # Fluxo normal Dinheiro/Conta
            t = Transaction(
                family_id=dto.family_id,
                category_id=dto.category_id,
                type=t_type,
                date=dto.date,
                amount=dto.amount,
                description=dto.description,
                bank_account_id=dto.bank_account_id
            )
            self._transaction_repo.save(t)
            transactions_created.append(t)
            
        return transactions_created
