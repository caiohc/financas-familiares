import unicodedata
from typing import Optional


def fold_text(text: Optional[str]) -> str:
    """
    Texto sem diferença de caixa e de acentos, usado na pesquisa ("Álvaro" casa com "alvaro").
    Cada caractere vira exatamente um caractere, para que a posição de um trecho no texto
    dobrado seja a mesma no original (o realce do resultado depende disso).
    """
    if not text:
        return ""
    folded = []
    for char in unicodedata.normalize("NFC", text):
        base = "".join(c for c in unicodedata.normalize("NFD", char) if not unicodedata.combining(c)).lower()
        folded.append(base if len(base) == 1 else char)
    return "".join(folded)
