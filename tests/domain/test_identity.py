import uuid
from domain.identity.entities import User

def test_user_creation():
    """Testa se a entidade User de identidade inicializa corretamente associada a um membro."""
    fake_member_id = uuid.uuid4()
    
    # Criamos um usuario apontando para um membro pre-existente
    user = User(
        member_id=fake_member_id,
        email="member@example.com"
    )
    
    assert user.id is not None
    assert user.member_id == fake_member_id
    assert user.email == "member@example.com"
