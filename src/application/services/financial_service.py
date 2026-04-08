import uuid

from application.dtos.financial_dtos import (
    CreateBankAccountDTO,
    CreateCardInstanceDTO,
    CreateCreditCardDTO,
)
from domain.financial.entities import BankAccount, CardInstance, CreditCard
from domain.financial.repositories import (
    BankAccountRepository,
    CreditCardRepository,
    MemberRepository,
)

class FinancialService:
    """Orquestra as lógicas e travas na manipulação de contas bancárias e cartões."""

    def __init__(
        self,
        bank_account_repo: BankAccountRepository,
        credit_card_repo: CreditCardRepository,
        member_repo: MemberRepository,
    ):
        self._bank_account_repo = bank_account_repo
        self._credit_card_repo = credit_card_repo
        self._member_repo = member_repo

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
