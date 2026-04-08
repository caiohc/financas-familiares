"""
Subdomínio de Autenticação e Autorização (Identidade)
"""

import uuid
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class User:
    """Entidade de sistema voltada especificamente para Autenticação e Autorização."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    member_id: uuid.UUID  # Aponta para o Member no Domínio Financeiro (Relação N -> 1)
    email: str
    
    # Exemplo: atributos de segurança, hashes de senha e parâmetros de permissões
    # pertenceriam exclusivamente à lógica deste subdomínio.
