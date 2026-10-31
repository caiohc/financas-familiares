from domain.shared.text import fold_text

def test_fold_text_ignores_case_and_accents():
    assert fold_text("José ÁLVARO Çarneiro") == "jose alvaro carneiro"

def test_fold_text_keeps_the_length_of_each_character():
    # O realce do trecho encontrado depende de a posição no texto dobrado ser a do original
    original = "Conceição Ñandú"
    assert len(fold_text(original)) == len(original)

def test_fold_text_of_none_or_empty_is_empty():
    assert fold_text(None) == ""
    assert fold_text("") == ""
