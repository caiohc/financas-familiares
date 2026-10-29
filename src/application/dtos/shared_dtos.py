from dataclasses import dataclass
from typing import Optional

@dataclass(kw_only=True)
class DeletionPreviewDTO:
    """
    O que a tela de confirmação precisa saber antes de oferecer a exclusão:
    o nome do registro e, se houver dependências, o motivo do bloqueio.
    """
    name: str
    blocked_reason: Optional[str] = None
