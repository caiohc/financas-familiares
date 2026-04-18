import uuid
# imports natives
from application.dtos.family_dtos import CreateFamilyDTO, CreateMemberDTO
from domain.financial.entities import Family, Member
from domain.financial.repositories import FamilyRepository, MemberRepository

class FamilyService:
    """Orquestra o CRUD aglomerado das Entidades Raíz da Organização Financeira baseando-se em DTOs."""
    
    def __init__(
        self, 
        family_repo: FamilyRepository, 
        member_repo: MemberRepository
    ):
        # A clássica Injeção de Dependências
        self._family_repo = family_repo
        self._member_repo = member_repo

    def create_family(self, dto: CreateFamilyDTO) -> Family:
        # 1. Absorve os os atributos burros do DTO
        # 2. Converte na Entidade forte do domínio resolvendo as lógicas implícitas
        family = Family(name=dto.name)
        self._family_repo.save(family)
        return family

    def get_family(self, family_id: uuid.UUID) -> Family:
        family = self._family_repo.get_by_id(family_id)
        if not family:
            raise ValueError(f"Família {family_id} não está registrada no ecossistema.")
        return family

    def list_families(self) -> list[Family]:
        return self._family_repo.list_all()

    def update_family(self, family_id: uuid.UUID, new_name: str) -> Family:
        family = self.get_family(family_id)
        family.name = new_name
        self._family_repo.save(family)
        return family

    def create_member(self, dto: CreateMemberDTO) -> Member:
        # Validação: Garante que não teremos um membro perdido sem família
        self.get_family(dto.family_id)
            
        member = Member(family_id=dto.family_id, name=dto.name)
        self._member_repo.save(member)
        return member

    def list_members(self, family_id: uuid.UUID) -> list[Member]:
        self.get_family(family_id)  # Se ela não existir, interrompe o fluxo automaticamente.
        return self._member_repo.list_by_family(family_id)

    def get_member(self, member_id: uuid.UUID) -> Member:
        member = self._member_repo.get_by_id(member_id)
        if not member:
            raise ValueError(f"Membro {member_id} não encontrado.")
        return member

    def list_all_members(self) -> list[Member]:
        return self._member_repo.list_all()

    def update_member(self, member_id: uuid.UUID, new_name: str, new_family_id: uuid.UUID) -> Member:
        # Confere se os dois ecossistemas existem
        member = self.get_member(member_id)
        self.get_family(new_family_id)
        
        member.name = new_name
        member.family_id = new_family_id
        
        self._member_repo.save(member)
        return member
