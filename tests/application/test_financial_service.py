import pytest
import uuid

from application.dtos.financial_dtos import (
    CreateBankAccountDTO, CreateCreditCardDTO, CreateCardInstanceDTO
)
from application.services.financial_service import FinancialService
from domain.financial.entities import Member
from infrastructure.repositories.in_memory import (
    BankAccountMemoryRepository, CreditCardMemoryRepository, MemberMemoryRepository
)

def test_financial_service_crud_flux():
    """Valida a orquestração do Serviço em amarrar contas e cartões com persistência fake."""
    db_members = MemberMemoryRepository()
    db_accounts = BankAccountMemoryRepository()
    db_cards = CreditCardMemoryRepository()
    
    # 1. SETUP INICIAL: Pre-cadastra um membro base já existindo no banco.
    fake_family_id = uuid.uuid4()
    titular_valido = Member(family_id=fake_family_id, name="Titular Silva")
    db_members.save(titular_valido)
    
    service = FinancialService(
        bank_account_repo=db_accounts,
        credit_card_repo=db_cards,
        member_repo=db_members
    )
    
    # 2. ACT -> Criação da Conta Bancária
    ba_dto = CreateBankAccountDTO(
        family_id=titular_valido.family_id, 
        holder_id=titular_valido.id, 
        name="Conta Conjunta ITAU"
    )
    acc = service.create_bank_account(ba_dto)
    assert acc.id is not None
    assert acc.name == "Conta Conjunta ITAU"
    
    # 3. ACT -> Criação da Máster Conta do Cartão de Crédito
    cc_dto = CreateCreditCardDTO(
        family_id=titular_valido.family_id, 
        holder_id=titular_valido.id, 
        name="Infinite Black Família", 
        limit=25000.0,
        due_day=10
    )
    card_master = service.create_credit_card(cc_dto)
    assert card_master.limit == 25000.0
    
    # 4. ACT -> Plástico Impresso e Vinculado ao master
    inst_dto = CreateCardInstanceDTO(
        credit_card_id=card_master.id,
        holder_id=titular_valido.id,
        nickname="Físico Pai (Carteira)"
    )
    plastico = service.create_card_instance(inst_dto)
    assert plastico.credit_card_id == card_master.id
    
    # 5. ASSERT EXTREMO: Validamos que o "JOIN" do db na memória acha os plásticos pela familia mãe.
    lista_plasticos = db_cards.list_instances_by_family(fake_family_id)
    assert len(lista_plasticos) == 1
    assert lista_plasticos[0].nickname == "Físico Pai (Carteira)"


def test_financial_service_blocks_cross_family_intruders():
    """Garante a blindagem Multi-tenant: Se o membro X tentar criar conta atrelando a URL a familia Y."""
    db_members = MemberMemoryRepository()
    service = FinancialService(
        bank_account_repo=BankAccountMemoryRepository(),
        credit_card_repo=CreditCardMemoryRepository(),
        member_repo=db_members
    )
    
    # O Titular é nativo da Family "oficial"
    familia_oficial_id = uuid.uuid4()
    titular_oficial = Member(family_id=familia_oficial_id, name="João Official")
    db_members.save(titular_oficial)
    
    # Algum intruso tentou mandar ID de familia diferente do titular apontado
    familia_intrusa_id = uuid.uuid4()
    
    invasao_dto = CreateBankAccountDTO(
        family_id=familia_intrusa_id,
        holder_id=titular_oficial.id,
        name="Conta Laranja Invisível"
    )
    
    with pytest.raises(ValueError, match="não pertence à família selecionada"):
        service.create_bank_account(invasao_dto)
