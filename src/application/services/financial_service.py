import uuid
from decimal import Decimal

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

        account = BankAccount.create(
            family_id=dto.family_id,
            holder_id=dto.holder_id,
            holder_name=member.name,
            bank=dto.bank,
            agency=dto.agency,
            account_number=dto.account_number,
            nickname=dto.nickname
        )
        self._bank_account_repo.save(account)
        return account

    def create_credit_card(self, dto: CreateCreditCardDTO) -> CreditCard:
        member = self._ensure_member_exists(dto.holder_id)
        
        if member.family_id != dto.family_id:
            raise ValueError("O responsável legal do cartão não pertence à família informada.")

        # 1.5. Domínio: Se informou conta bancária, ela deve pertencer à mesma família
        bank_account = None
        if dto.bank_account_id:
            bank_account = self._bank_account_repo.get_by_id(dto.bank_account_id)
            if not bank_account or bank_account.family_id != dto.family_id:
                raise ValueError("Incoerência sistêmica: A conta bancária de débito fornecida não pertence à família selecionada.")

        credit_card_nickname = dto.nickname
        credit_card_issuer = dto.issuer
        
        # Lógica do Emissor (issuer)
        if not credit_card_issuer or credit_card_issuer.strip() == "":
            if bank_account:
                credit_card_issuer = bank_account.bank
            else:
                raise ValueError("Emissor é obrigatório quando não há conta bancária vinculada.")
                
        # Lógica do Apelido (nickname)
        if not credit_card_nickname or credit_card_nickname.strip() == "":
            if bank_account:
                credit_card_nickname = f"{bank_account.nickname} - {dto.brand}"
            else:
                primeiro_nome = member.name.split()[0] if member.name else "Membro"
                credit_card_nickname = f"{credit_card_issuer} ({primeiro_nome}) - {dto.brand}"

        card = CreditCard(
            family_id=dto.family_id,
            holder_id=dto.holder_id,
            nickname=credit_card_nickname,
            issuer=credit_card_issuer,
            brand=dto.brand,
            tier="",
            limit=dto.limit,
            due_day=dto.due_day,
            bank_account_id=dto.bank_account_id
        )
        self._credit_card_repo.save(card)
        return card

    def create_card_instance(self, dto: CreateCardInstanceDTO) -> CardInstance:
        # Novamente exigimos certeza de que quem portará o plástico está no ecossistema
        member = self._ensure_member_exists(dto.holder_id)
        
        # Validar cruzado: O id de família preenchido bate com a família originária do Membro titular?
        if member.family_id != dto.family_id:
            raise ValueError("Incoerência sistêmica: O portador fornecido não pertence à família selecionada.")

        # Buscar o cartão mestre para herdar o apelido se necessário
        master_card = self.get_credit_card(dto.credit_card_id)
        if master_card.family_id != dto.family_id:
             raise ValueError("Incoerência sistêmica: O cartão principal selecionado não pertence à família selecionada.")

        nickname = dto.nickname
        if not nickname or nickname.strip() == "":
            primeiro_nome = member.name.split()[0] if member.name else "Membro"
            nickname = f"{master_card.nickname} ({primeiro_nome})"
        
        instance = CardInstance(
            family_id=dto.family_id,
            credit_card_id=dto.credit_card_id,
            holder_id=dto.holder_id,
            nickname=nickname
        )
        self._credit_card_repo.save_instance(instance)
        return instance

    def list_all_bank_accounts(self) -> list[BankAccount]:
        return self._bank_account_repo.list_all()

    def get_bank_account(self, account_id: uuid.UUID) -> BankAccount:
        account = self._bank_account_repo.get_by_id(account_id)
        if not account:
            raise ValueError(f"Conta Bancária {account_id} não encontrada.")
        return account

    def update_bank_account(self, account_id: uuid.UUID, nickname: str, bank: str, agency: str, account_number: str) -> BankAccount:
        account = self.get_bank_account(account_id)
        
        if not nickname or nickname.strip() == "":
            member = self._ensure_member_exists(account.holder_id)
            primeiro_nome = member.name.split()[0] if member.name else "Membro"
            banco_nome = bank if bank else "Banco"
            nickname = f"{banco_nome} ({primeiro_nome})"
            
        account.nickname = nickname
        account.bank = bank
        account.agency = agency
        account.account_number = account_number
        self._bank_account_repo.save(account)
        return account

    def delete_bank_account(self, account_id: uuid.UUID) -> None:
        account = self.get_bank_account(account_id)
        
        # Verificar vínculos com Cartões de Crédito (Débito automático)
        cards = self._credit_card_repo.list_all()
        for card in cards:
            if card.bank_account_id == account_id:
                raise ValueError(f"A conta está vinculada ao cartão de crédito '{card.nickname}' para débito automático. Desvincule-a primeiro.")
                
        # Verificar vínculos com Transações
        # Em produção idealmente teríamos uma query SQL para isso, mas como a regra arquitetural 
        # nos permite e o escopo é local, usamos list_all do repositório
        transactions = self._transaction_repo.list_by_account(account_id)
        if transactions:
            raise ValueError("A conta não pode ser excluída pois possui transações financeiras atreladas a ela.")
                
        self._bank_account_repo.delete(account_id)

    def list_all_credit_cards(self) -> list[CreditCard]:
        return self._credit_card_repo.list_all()

    def get_credit_card(self, card_id: uuid.UUID) -> CreditCard:
        card = self._credit_card_repo.get_by_id(card_id)
        if not card:
            raise ValueError(f"Cartão de Crédito {card_id} não encontrado.")
        return card

    def update_credit_card(self, card_id: uuid.UUID, nickname: str, issuer: str, brand: str, limit: Decimal, due_day: int, bank_account_id: uuid.UUID = None) -> CreditCard:
        card = self.get_credit_card(card_id)
        
        bank_account = None
        if bank_account_id:
            bank_account = self._bank_account_repo.get_by_id(bank_account_id)
            if not bank_account or bank_account.family_id != card.family_id:
                raise ValueError("Incoerência sistêmica: A conta bancária de débito fornecida não pertence à família selecionada.")

        # Lógica do Emissor (issuer)
        if not issuer or issuer.strip() == "":
            if bank_account:
                issuer = bank_account.bank
            else:
                raise ValueError("Emissor é obrigatório quando não há conta bancária vinculada.")
                
        card.issuer = issuer
        card.brand = brand
        card.limit = limit
        card.due_day = due_day
        card.bank_account_id = bank_account_id
        
        # Lógica do Apelido (nickname)
        if not nickname or nickname.strip() == "":
            if bank_account:
                card.nickname = f"{bank_account.nickname} - {brand}"
            else:
                member = self._ensure_member_exists(card.holder_id)
                primeiro_nome = member.name.split()[0] if member.name else "Membro"
                card.nickname = f"{issuer} ({primeiro_nome}) - {brand}"
        else:
            card.nickname = nickname

        self._credit_card_repo.save(card)
        return card

    def delete_credit_card(self, card_id: uuid.UUID) -> None:
        card = self.get_credit_card(card_id)
        instances = self._credit_card_repo.list_all_instances()
        for inst in instances:
            if inst.credit_card_id == card_id:
                raise ValueError("O cartão não pode ser excluído pois possui plásticos (adicionais) associados a ele. Exclua-os primeiro.")
        self._credit_card_repo.delete(card_id)

    def list_all_card_instances(self) -> list[CardInstance]:
        return self._credit_card_repo.list_all_instances()

    def get_card_instance(self, instance_id: uuid.UUID) -> CardInstance:
        instance = self._credit_card_repo.get_instance_by_id(instance_id)
        if not instance:
            raise ValueError(f"Plástico {instance_id} não encontrado.")
        return instance

    def update_card_instance(self, instance_id: uuid.UUID, nickname: str) -> CardInstance:
        instance = self.get_card_instance(instance_id)
        
        if not nickname or nickname.strip() == "":
            member = self._ensure_member_exists(instance.holder_id)
            master_card = self.get_credit_card(instance.credit_card_id)
            primeiro_nome = member.name.split()[0] if member.name else "Membro"
            nickname = f"{master_card.nickname} ({primeiro_nome})"

        instance.nickname = nickname
        self._credit_card_repo.save_instance(instance)
        return instance

    def delete_card_instance(self, instance_id: uuid.UUID) -> None:
        instance = self.get_card_instance(instance_id)
        transactions = self._transaction_repo.list_by_credit_card_instance(instance_id)
        if transactions:
            raise ValueError("O plástico não pode ser excluído pois possui transações financeiras atreladas a ele.")
        self._credit_card_repo.delete_instance(instance_id)

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
