"""
Convites de acesso: o único caminho pelo qual uma senha é definida por convite.

O administrador nunca define nem conhece a senha de outra pessoa. Ele emite um convite:
- ACTIVATION: ativação de uma conta nova. Link por e-mail + código por outro canal.
- ADMIN_RESET: redefinição da senha de um administrador do sistema, por outro administrador.
  Link por e-mail + código por outro canal.
- RECOVERY: recuperação autônoma ("Esqueci minha senha"). Só o link, de validade curta.

O token (no link) e o código nunca são guardados: só o hash de cada um.
"""
import hashlib
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from domain.identity.exceptions import invalid_invitation

# Sem 0/O e 1/I/L, que se confundem quando o código é ditado ou lido.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


class InvitationPurpose(Enum):
    ACTIVATION = "ACTIVATION"
    ADMIN_RESET = "ADMIN_RESET"
    RECOVERY = "RECOVERY"

    @property
    def requires_code(self) -> bool:
        return self is not InvitationPurpose.RECOVERY


def generate_token() -> str:
    """Token imprevisível (256 bits) para o link."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 basta: o token é aleatório e longo, então não há o que adivinhar com um hash lento."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(code: Optional[str]) -> str:
    """Tolera hífen, espaços e minúsculas ao digitar: 'abcd-efgh' vale 'ABCDEFGH'."""
    return re.sub(r"[^A-Za-z0-9]", "", code or "").upper()


def format_code(code: str) -> str:
    return f"{code[:CODE_LENGTH // 2]}-{code[CODE_LENGTH // 2:]}"


@dataclass(kw_only=True)
class Invitation:
    user_id: uuid.UUID
    purpose: InvitationPurpose
    token_hash: str
    code_hash: Optional[str]
    created_at: datetime
    expires_at: datetime
    id: Optional[uuid.UUID] = None
    created_by_user_id: Optional[uuid.UUID] = None
    attempts: int = 0
    consumed_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    def __post_init__(self):
        if self.id is None:
            self.id = uuid.uuid4()
        if self.purpose.requires_code and not self.code_hash:
            raise ValueError("Convite com código precisa do hash do código.")
        if not self.purpose.requires_code and self.code_hash:
            raise ValueError("Convite de recuperação não tem código.")

    @property
    def requires_code(self) -> bool:
        return self.purpose.requires_code

    def is_usable(self, now: datetime, max_attempts: int) -> bool:
        return (
            self.consumed_at is None
            and self.revoked_at is None
            and now < self.expires_at
            and self.attempts < max_attempts
        )

    def ensure_usable(self, now: datetime, max_attempts: int) -> None:
        if not self.is_usable(now, max_attempts):
            raise invalid_invitation()
