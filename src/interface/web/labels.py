from typing import NamedTuple, Optional

from markupsafe import Markup, escape

from domain.shared.text import fold_text


class FamilyLabel(NamedTuple):
    """Nome da família + 8 primeiros caracteres do UUID.

    O nome não é único (várias famílias podem se chamar "Silva"), então a UI
    acrescenta o sufixo para a pessoa distinguir uma da outra.
    """
    name: str
    short_id: str

    def __str__(self) -> str:
        return f"{self.name} \u00b7 {self.short_id}"


def family_label_parts(family) -> FamilyLabel:
    return FamilyLabel(family.name, str(family.id)[:8])


def family_label(family) -> str:
    return str(family_label_parts(family))


def highlight(text: Optional[str], term: Optional[str]) -> Markup:
    """Texto escapado com <mark> em cada trecho que casa com a pesquisa (sem caixa e sem acentos)."""
    text = "" if text is None else str(text)
    needle = fold_text(term)
    folded = fold_text(text)
    if not needle or len(folded) != len(text):
        return escape(text)

    parts, start = [], 0
    while (found := folded.find(needle, start)) >= 0:
        end = found + len(needle)
        parts.append(escape(text[start:found]))
        parts.append(Markup("<mark>") + escape(text[found:end]) + Markup("</mark>"))
        start = end
    parts.append(escape(text[start:]))
    return Markup("").join(parts)


def highlight_label(label: Optional[FamilyLabel], term: Optional[str]) -> Markup:
    """Realça só o nome da família; o sufixo do UUID nunca é marcado."""
    if label is None:
        return Markup("\u2014")
    return highlight(label.name, term) + escape(f" \u00b7 {label.short_id}")
