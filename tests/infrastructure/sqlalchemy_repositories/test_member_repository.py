from sqlalchemy.orm import Session
from domain.family.entities import Family, Member
from infrastructure.repositories.sqlalchemy_repositories import SQLAlchemyMemberRepository, SQLAlchemyFamilyRepository

def test_member_repository_save_and_get(session: Session):
    family_repo = SQLAlchemyFamilyRepository(session)
    member_repo = SQLAlchemyMemberRepository(session)
    
    family = Family(name="Test Family for Member")
    family_repo.save(family)
    
    member = Member(family_id=family.id, name="John Doe")
    member_repo.save(member)
    session.flush()
    
    fetched = member_repo.get_by_id(member.id)
    
    assert fetched is not None
    assert fetched.id == member.id
    assert fetched.family_id == family.id
    assert fetched.name == "John Doe"

def test_member_repository_list_by_family(session: Session):
    family_repo = SQLAlchemyFamilyRepository(session)
    member_repo = SQLAlchemyMemberRepository(session)
    
    family = Family(name="Test Family for Members List")
    family_repo.save(family)
    
    members = []
    for i in range(3):
        member = Member(family_id=family.id, name=f"Member {i}")
        members.append(member)
        member_repo.save(member)
        
    session.flush()
    
    # Adicionando um membro de outra família para garantir o filtro
    other_family = Family(name="Other Family")
    family_repo.save(other_family)
    other_member = Member(family_id=other_family.id, name="Other Member")
    member_repo.save(other_member)
    session.flush()
    
    # Apenas os membros da família desejada devem ser retornados
    fetched_members = member_repo.list_by_family(family.id)
    assert len(fetched_members) == len(members)
    
    for member in members:
        fetched = next((m for m in fetched_members if m.id == member.id), None)
        assert fetched is not None
        assert fetched.name == member.name
