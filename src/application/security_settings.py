from dataclasses import dataclass, field
from datetime import timedelta


@dataclass(frozen=True)
class SecuritySettings:
    """Prazos e limites dos convites. Decididos: convite 24 h; recuperação 15 min; 5 tentativas do código."""
    invitation_ttl: timedelta = field(default_factory=lambda: timedelta(hours=24))
    recovery_ttl: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    max_code_attempts: int = 5
