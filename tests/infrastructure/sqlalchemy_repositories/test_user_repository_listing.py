"""Listagem (paginação, ordenação, pesquisa), exclusão e dependências do repositório de usuário."""
import uuid

import pytest
from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Session

from domain.identity.entities import Role, User
from infrastructure.database.models import Base, FamilyModel
from infrastructure.repositories.sqlalchemy.sqlalchemy_user_repository import SQLAlchemyUserRepository


@pytest.fixture
def repo(session: Session) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(session)


@pytest.fixture
def family_id(session: Session) -> uuid.UUID:
    model = FamilyModel(id=str(uuid.uuid4()), name="Silva")
    session.add(model)
    session.flush()
    return uuid.UUID(model.id)


def _save(repo, session, family_id, name, username, email, role=Role.FAMILY_USER) -> User:
    in_family = role not in (Role.ROOT, Role.SYSTEM_ADMIN)
    user = User(
        role=role, family_id=family_id if in_family else None, name=name, username=username, email=email,
        password_hash="hash",
    )
    repo.save(user)
    session.flush()
    return user


def _names(page):
    return [u.name for u in page.items]


def _seed_people(repo, session, family_id) -> None:
    # Cada campo produz uma ordem diferente: nome (ana, Bruno, Zélia), usuário (Bruno, Zélia, ana),
    # e-mail (Zélia, ana, Bruno).
    _save(repo, session, family_id, "Zélia", "bz.login", "a.contato@mail.com")
    _save(repo, session, family_id, "ana", "cz.apelido", "m.correio@mail.com")
    _save(repo, session, family_id, "Bruno", "az.nick", "z.mensagem@mail.com")


# --- Paginação ---

def test_list_page_slices_and_reports_the_total(repo, session, family_id):
    for n in range(1, 6):
        _save(repo, session, family_id, f"Pessoa {n}", f"pessoa{n}", f"p{n}@example.com")

    first = repo.list_page(page=1, page_size=2)
    last = repo.list_page(page=3, page_size=2)

    assert first.total == 5
    assert _names(first) == ["Pessoa 1", "Pessoa 2"]
    assert _names(last) == ["Pessoa 5"]


def test_list_page_beyond_the_last_page_is_empty_but_keeps_the_total(repo, session, family_id):
    _save(repo, session, family_id, "João", "joao", "joao@example.com")

    page = repo.list_page(page=4, page_size=10)

    assert page.items == []
    assert page.total == 1


def test_list_page_includes_users_of_every_level(repo, session, family_id):
    _save(repo, session, None, None, "root", "root@example.com", role=Role.ROOT)
    _save(repo, session, None, "Caio", "caio", "caio@example.com", role=Role.SYSTEM_ADMIN)
    _save(repo, session, family_id, "Ana", "ana", "ana@example.com", role=Role.FAMILY_ADMIN)

    page = repo.list_page(page=1, page_size=10)

    assert page.total == 3
    assert {u.role for u in page.items} == {Role.ROOT, Role.SYSTEM_ADMIN, Role.FAMILY_ADMIN}


# --- Ordenação ---

def test_list_page_defaults_to_name_ignoring_case(repo, session, family_id):
    _seed_people(repo, session, family_id)

    assert _names(repo.list_page(page=1, page_size=10)) == ["ana", "Bruno", "Zélia"]


@pytest.mark.parametrize("field, ascending", [
    ("name", ["ana", "Bruno", "Zélia"]),
    ("username", ["Bruno", "Zélia", "ana"]),
    ("email", ["Zélia", "ana", "Bruno"]),
])
def test_list_page_sorts_by_each_field_in_both_directions(repo, session, family_id, field, ascending):
    _seed_people(repo, session, family_id)

    up = repo.list_page(page=1, page_size=10, sort_by=field)
    down = repo.list_page(page=1, page_size=10, sort_by=field, descending=True)

    assert _names(up) == ascending
    assert _names(down) == ascending[::-1]


def test_list_page_sorting_ignores_case_in_username_and_email(repo, session, family_id):
    _save(repo, session, family_id, "Um", "Beta", "B@example.com")
    _save(repo, session, family_id, "Dois", "alfa", "a@example.com")

    assert _names(repo.list_page(page=1, page_size=10, sort_by="username")) == ["Dois", "Um"]
    assert _names(repo.list_page(page=1, page_size=10, sort_by="email")) == ["Dois", "Um"]


def test_list_page_ties_on_name_are_broken_by_username(repo, session, family_id):
    _save(repo, session, family_id, "Maria", "maria.z", "z@example.com")
    _save(repo, session, family_id, "Maria", "maria.a", "a@example.com")

    page = repo.list_page(page=1, page_size=10)

    assert [u.username for u in page.items] == ["maria.a", "maria.z"]


def test_list_page_puts_the_nameless_root_first_ascending_and_last_descending(repo, session, family_id):
    _seed_people(repo, session, family_id)
    _save(repo, session, None, None, "root", "root@example.com", role=Role.ROOT)

    assert _names(repo.list_page(page=1, page_size=10)) == [None, "ana", "Bruno", "Zélia"]
    assert _names(repo.list_page(page=1, page_size=10, descending=True)) == ["Zélia", "Bruno", "ana", None]


def test_list_page_sorted_still_reports_the_full_total(repo, session, family_id):
    _seed_people(repo, session, family_id)

    page = repo.list_page(page=2, page_size=2, sort_by="email")

    assert page.total == 3
    assert _names(page) == ["Bruno"]


@pytest.mark.parametrize("field", ["role", "family", "password_hash", "balance"])
def test_list_page_rejects_an_unknown_sort_field(repo, field):
    with pytest.raises(ValueError):
        repo.list_page(page=1, page_size=10, sort_by=field)


# --- Pesquisa ---

@pytest.mark.parametrize("term, expected", [
    ("zel", ["Zélia"]),
    ("APELIDO", ["ana"]),
    ("mensagem", ["Bruno"]),
    ("mail", ["ana", "Bruno", "Zélia"]),
    ("xyz", []),
])
def test_search_matches_name_username_or_email(repo, session, family_id, term, expected):
    _seed_people(repo, session, family_id)

    page = repo.list_page(page=1, page_size=10, search=term)

    assert _names(page) == expected
    assert page.total == len(expected)


def test_search_ignores_case_and_accents(repo, session, family_id):
    _save(repo, session, family_id, "José", "jose", "jose@example.com")
    _save(repo, session, family_id, "Bruno", "bruno", "bruno@example.com")

    assert _names(repo.list_page(page=1, page_size=10, search="JOSE")) == ["José"]
    assert _names(repo.list_page(page=1, page_size=10, search="josé")) == ["José"]


def test_search_does_not_match_the_nameless_root_by_name_but_finds_it_by_username(repo, session, family_id):
    _save(repo, session, None, None, "root", "root@example.com", role=Role.ROOT)
    _save(repo, session, family_id, "Ana", "ana", "ana@example.com")

    assert repo.list_page(page=1, page_size=10, search="root").total == 1
    assert repo.list_page(page=1, page_size=10, search="ana").total == 1


def test_search_does_not_duplicate_a_user_matching_in_several_fields(repo, session, family_id):
    _save(repo, session, family_id, "Silvia", "silvia", "silvia@example.com")

    page = repo.list_page(page=1, page_size=10, search="sil")

    assert page.total == 1
    assert len(page.items) == 1


@pytest.mark.parametrize("term", ["%", "_", "\\"])
def test_search_wildcards_are_literal(repo, session, family_id, term):
    _save(repo, session, family_id, "Ana", "ana", "ana@example.com")

    assert repo.list_page(page=1, page_size=10, search=term).total == 0


def test_search_finds_a_literal_underscore(repo, session, family_id):
    _save(repo, session, family_id, "Ana", "ana_souza", "ana@example.com")
    _save(repo, session, family_id, "Bia", "biasouza", "bia@example.com")

    assert _names(repo.list_page(page=1, page_size=10, search="a_s")) == ["Ana"]


def test_pagination_and_sorting_work_over_the_search_results(repo, session, family_id):
    for n in range(1, 6):
        _save(repo, session, family_id, f"Silva {n}", f"silva{n}", f"s{n}@example.com")
    for n in range(1, 11):
        _save(repo, session, family_id, f"Souza {n:02d}", f"souza{n:02d}", f"z{n:02d}@example.com")

    first = repo.list_page(page=1, page_size=2, search="silva")
    last = repo.list_page(page=3, page_size=2, sort_by="username", descending=True, search="silva")

    assert first.total == last.total == 5
    assert _names(first) == ["Silva 1", "Silva 2"]
    assert _names(last) == ["Silva 1"]


# --- Exclusão e dependências ---

def test_delete_removes_the_user(repo, session, family_id):
    user = _save(repo, session, family_id, "João", "joao", "joao@example.com")

    repo.delete(user.id)
    session.flush()

    assert repo.get_by_id(user.id) is None


def test_delete_nonexistent_user_is_a_noop(repo, session):
    repo.delete(uuid.uuid4())
    session.flush()


def test_user_without_dependents_has_no_dependencies(repo, session, family_id):
    user = _save(repo, session, family_id, "João", "joao", "joao@example.com")

    assert repo.has_dependencies(user.id) is False


def test_user_referenced_by_another_table_has_dependencies(repo, session, family_id):
    # Nenhuma entidade referencia usuário ainda (auditoria virá depois). A checagem é derivada das FKs
    # do modelo, então uma tabela futura passa a valer sozinha: simula-se uma com FK para users.
    audit = Table(
        "tmp_user_audit_trail", Base.metadata,
        Column("id", String(36), primary_key=True),
        Column("user_id", String(36), ForeignKey("users.id")),
    )
    user = _save(repo, session, family_id, "João", "joao", "joao@example.com")
    audit.create(session.connection())
    try:
        assert repo.has_dependencies(user.id) is False

        session.execute(audit.insert().values(id=str(uuid.uuid4()), user_id=str(user.id)))

        assert repo.has_dependencies(user.id) is True
    finally:
        audit.drop(session.connection())
        Base.metadata.remove(audit)
