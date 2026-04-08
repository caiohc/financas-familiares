import pytest
import uuid

from application.dtos.family_dtos import CreateFamilyDTO, CreateMemberDTO
from application.services.family_service import FamilyService
from infrastructure.repositories.in_memory import FamilyMemoryRepository, MemberMemoryRepository


def test_family_service_crud_flux():
    """Garante a injeção do banco falso (Memory) nas regras orquestradas dos Casos de Uso."""
    db_families = FamilyMemoryRepository()
    db_members = MemberMemoryRepository()
    
    service = FamilyService(family_repo=db_families, member_repo=db_members)
    
    # Executamos o caso de uso simulando se fosse uma request da Interface Web/CLI
    f_dto = CreateFamilyDTO(name="Constante")
    new_family = service.create_family(f_dto)
    
    assert new_family.id is not None
    assert new_family.name == "Constante"
    
    # O Serviço testa a família e aloca no banco falso
    m_dto = CreateMemberDTO(family_id=new_family.id, name="Caio Constante")
    new_member = service.create_member(m_dto)
    
    # O Serviço lista buscando do banco falso
    members = service.list_members(new_family.id)
    assert len(members) == 1
    assert members[0].name == "Caio Constante"


def test_family_service_blocks_orphan_member():
    """Prova que a regra de Inversão de Controle valida entidades relacionadas usando os Repositórios de Interface."""
    service = FamilyService(
        family_repo=FamilyMemoryRepository(), 
        member_repo=MemberMemoryRepository()
    )

    invalid_dto = CreateMemberDTO(family_id=uuid.uuid4(), name="Hacker")
    
    with pytest.raises(ValueError, match="não está registrada no ecossistema"):
        service.create_member(invalid_dto)
