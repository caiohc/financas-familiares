import re
import uuid
from decimal import Decimal
from html import unescape

from application.dtos.family_dtos import FamilyResponseDTO
from application.dtos.identity_dtos import CreateUserDTO, UpdateUserDTO, UserResponseDTO
from application.dtos.shared_dtos import DeletionPreviewDTO
from domain.identity.entities import Role
from domain.identity.exceptions import (
    root_cannot_be_deleted,
    user_has_dependencies,
    user_not_found,
    username_already_exists,
)
from domain.shared.exceptions import DomainValidationError, EntityNotFoundError
from fakes.pagination import page_of


def _family(name: str) -> FamilyResponseDTO:
    return FamilyResponseDTO(id=uuid.uuid4(), name=name, current_balance=Decimal("0.00"))


def _user(name="João da Silva", family_id=None, role=Role.FAMILY_USER, username="joao", email="joao@example.com"):
    return UserResponseDTO(
        id=uuid.uuid4(), role=role, family_id=family_id, name=name, username=username, email=email,
        must_change_password=True,
    )


FORM = {"role": "FAMILY_USER", "name": "João", "username": "joao", "email": "joao@example.com",
        "temporary_password": "senha-temporaria", "temporary_password_confirmation": "senha-temporaria"}


# --- Listagem ---

def test_list_users_shows_name_username_email_role_and_family(client, user_service, family_service):
    family = _family("Família Silva")
    family_service.list_families.return_value = [family]
    user_service.list_users_page.return_value = page_of([
        _user("João da Silva", family.id, Role.FAMILY_ADMIN, "joao", "joao@example.com"),
        _user("Caio", None, Role.SYSTEM_ADMIN, "caio", "caio@example.com"),
    ])

    response = client.get("/user/list")

    assert response.status_code == 200
    html = unescape(response.get_data(as_text=True))
    for text in ("João da Silva", "joao", "joao@example.com", "Administrador da família",
                 f"Família Silva · {str(family.id)[:8]}", "Caio", "caio@example.com", "Administrador do sistema"):
        assert text in html


def test_list_users_shows_a_dash_for_the_nameless_root(client, user_service):
    user_service.list_users_page.return_value = page_of([_user(None, None, Role.ROOT, "root", "root@example.com")])

    html = client.get("/user/list").get_data(as_text=True)

    assert "root@example.com" in html
    assert "Root" in html
    assert "None" not in html


def test_list_users_has_sortable_name_username_and_email_headers_but_not_role_or_family(client, user_service):
    user_service.list_users_page.return_value = page_of([_user()])

    html = client.get("/user/list").get_data(as_text=True)

    headers = {re.sub(r"<[^>]+>", "", th).strip(): ("href" in th) for th in re.findall(r"<th[^>]*>.*?</th>", html, re.S)}
    assert headers["Nome"] and headers["Usuário"] and headers["E-mail"]
    assert not headers["Papel"] and not headers["Família"] and not headers["Ações"]


def test_list_users_highlights_the_search_in_name_username_and_email(client, user_service):
    user_service.list_users_page.return_value = page_of(
        [_user("Silvana", None, Role.SYSTEM_ADMIN, "silvana", "silvana@silva.com")], search="silv"
    )

    html = client.get("/user/list?q=silv").get_data(as_text=True)

    # nome "Silvana", usuário "silvana" e e-mail "silvana@silva.com" (dois trechos): quatro realces
    assert len(re.findall(r"<mark>silv</mark>", html, re.I)) == 4


def test_list_users_offers_create_button(client, user_service):
    user_service.list_users_page.return_value = page_of([])

    assert 'href="/user/new"' in client.get("/user/list").get_data(as_text=True)


def test_list_users_empty_state(client, user_service):
    user_service.list_users_page.return_value = page_of([])

    assert "Nenhum usuário cadastrado ainda." in client.get("/user/list").get_data(as_text=True)


def test_list_users_rows_are_wired_to_edit_and_delete(client, user_service):
    user = _user()
    user_service.list_users_page.return_value = page_of([user])

    html = client.get("/user/list").get_data(as_text=True)

    assert f'href="/user/edit/{user.id}"' in html
    assert f'href="/user/confirm-delete/{user.id}"' in html
    assert "confirm(" not in html


def test_list_users_never_renders_a_password_or_hash(client, user_service):
    user_service.list_users_page.return_value = page_of([_user()])

    html = client.get("/user/list").get_data(as_text=True).lower()

    assert "password" not in html and "hash" not in html


def test_sidebar_links_to_users(client, user_service):
    user_service.list_users_page.return_value = page_of([])

    html = client.get("/user/list").get_data(as_text=True)

    assert re.search(r'<a href="/user/list" class="active">', html)


# --- Criação ---

def test_new_user_form_offers_roles_families_and_a_password_field(client, family_service):
    family_a, family_b = _family("Família A"), _family("Família B")
    family_service.list_families.return_value = [family_a, family_b]

    response = client.get("/user/new")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'action="/user/create"' in html
    for role in ("SYSTEM_ADMIN", "FAMILY_ADMIN", "FAMILY_USER"):
        assert f'value="{role}"' in html
    assert 'value="ROOT"' not in html
    assert f'value="{family_a.id}"' in html and f'value="{family_b.id}"' in html
    assert re.search(r'<input[^>]*type="password"[^>]*name="temporary_password"', html)
    assert re.search(r'<input[^>]*type="password"[^>]*name="temporary_password_confirmation"', html)
    for field in ("name", "username", "email"):
        assert f'name="{field}"' in html


def test_new_user_form_is_not_a_place_to_prefill_a_password(client, family_service):
    family_service.list_families.return_value = []

    html = client.get("/user/new").get_data(as_text=True)

    assert not re.search(r'type="password"[^>]*value="[^"]+"', html)


def test_create_user_calls_service_and_redirects_to_list(client, user_service):
    family_id = uuid.uuid4()

    response = client.post("/user/create", data={**FORM, "family_id": str(family_id)})

    assert response.status_code == 302
    assert response.headers["Location"] == "/user/list"
    user_service.create_user.assert_called_once_with(CreateUserDTO(
        role=Role.FAMILY_USER, family_id=family_id, name="João", username="joao", email="joao@example.com",
        temporary_password="senha-temporaria", temporary_password_confirmation="senha-temporaria",
    ))


def test_create_system_admin_sends_no_family(client, user_service):
    client.post("/user/create", data={**FORM, "role": "SYSTEM_ADMIN", "family_id": ""})

    dto = user_service.create_user.call_args.args[0]
    assert (dto.role, dto.family_id) == (Role.SYSTEM_ADMIN, None)


def test_create_user_flashes_success_message(client, user_service):
    user_service.list_users_page.return_value = page_of([])

    response = client.post("/user/create", data={**FORM, "family_id": str(uuid.uuid4())}, follow_redirects=True)

    assert response.status_code == 200
    assert "cadastrado com sucesso" in unescape(response.get_data(as_text=True))


def test_create_duplicate_username_re_presents_form_keeping_values_but_not_the_password(
    client, user_service, family_service
):
    family = _family("Família A")
    family_service.list_families.return_value = [family]
    user_service.create_user.side_effect = username_already_exists("joao")

    response = client.post("/user/create", data={**FORM, "family_id": str(family.id)})

    assert response.status_code == 409
    assert "Location" not in response.headers
    html = unescape(response.get_data(as_text=True))
    assert 'Já existe um usuário com o nome de usuário "joao".' in html
    assert 'value="João"' in html and 'value="joao"' in html and 'value="joao@example.com"' in html
    assert f'value="{family.id}" selected' in html
    assert 'value="FAMILY_USER" selected' in html
    assert "senha-temporaria" not in html


def test_create_user_with_invalid_input_re_presents_form(client, user_service, family_service):
    family_service.list_families.return_value = []
    user_service.create_user.side_effect = DomainValidationError("name", "Nome é obrigatório.")

    response = client.post("/user/create", data={**FORM, "name": "   "})

    assert response.status_code == 400
    assert "Nome é obrigatório." in unescape(response.get_data(as_text=True))


def test_create_user_in_a_vanished_family_re_presents_form_with_400(client, user_service, family_service):
    family_service.list_families.return_value = []
    user_service.create_user.side_effect = EntityNotFoundError("Family", uuid.uuid4(), "Família não encontrada.")

    response = client.post("/user/create", data={**FORM, "family_id": str(uuid.uuid4())})

    assert response.status_code == 400
    assert "Família não encontrada." in response.get_data(as_text=True)


def test_create_user_without_role_leaves_the_decision_to_the_domain(client, user_service, family_service):
    family_service.list_families.return_value = []
    user_service.create_user.side_effect = DomainValidationError("role", "Papel do usuário é obrigatório.")
    data = {k: v for k, v in FORM.items() if k != "role"}

    response = client.post("/user/create", data=data)

    assert response.status_code == 400
    assert user_service.create_user.call_args.args[0].role is None
    assert "Papel do usuário é obrigatório." in unescape(response.get_data(as_text=True))


def test_create_user_with_mismatching_confirmation_re_presents_form_without_echoing_passwords(
    client, user_service, family_service
):
    family_service.list_families.return_value = []
    user_service.create_user.side_effect = DomainValidationError(
        "password_confirmation", "As senhas informadas não conferem."
    )

    response = client.post("/user/create", data={**FORM, "temporary_password_confirmation": "outra-senha-123"})

    assert response.status_code == 400
    html = unescape(response.get_data(as_text=True))
    assert "As senhas informadas não conferem." in html
    assert 'value="joao"' in html
    assert "senha-temporaria" not in html and "outra-senha-123" not in html
    assert user_service.create_user.call_args.args[0].temporary_password_confirmation == "outra-senha-123"


def test_create_user_without_confirmation_field_sends_none_to_the_service(client, user_service):
    data = {k: v for k, v in FORM.items() if k != "temporary_password_confirmation"}
    data["family_id"] = str(uuid.uuid4())

    client.post("/user/create", data=data)

    assert user_service.create_user.call_args.args[0].temporary_password_confirmation is None


def test_create_user_with_unknown_role_returns_400_without_calling_the_service(client, user_service):
    response = client.post("/user/create", data={**FORM, "role": "SUPERUSER"})

    assert response.status_code == 400
    user_service.create_user.assert_not_called()


def test_create_user_with_malformed_family_id_returns_400_without_calling_the_service(client, user_service):
    response = client.post("/user/create", data={**FORM, "family_id": "not-a-uuid"})

    assert response.status_code == 400
    user_service.create_user.assert_not_called()


# --- Edição ---

def test_edit_user_form_is_presented_with_role_and_family_read_only(client, user_service, family_service):
    family = _family("Família A")
    user = _user(family_id=family.id, role=Role.FAMILY_ADMIN)
    family_service.list_families.return_value = [family]
    user_service.get_user.return_value = user

    response = client.get(f"/user/edit/{user.id}")

    assert response.status_code == 200
    html = unescape(response.get_data(as_text=True))
    assert f'action="/user/update/{user.id}"' in html
    assert 'value="João da Silva"' in html and 'value="joao"' in html and 'value="joao@example.com"' in html
    assert "Administrador da família" in html and "Família A" in html
    assert 'name="role"' not in html and 'name="family_id"' not in html
    assert 'name="temporary_password"' not in html
    user_service.get_user.assert_called_once_with(user.id)


def test_edit_system_admin_shows_no_family(client, user_service, family_service):
    family_service.list_families.return_value = []
    user = _user(family_id=None, role=Role.SYSTEM_ADMIN)
    user_service.get_user.return_value = user

    html = unescape(client.get(f"/user/edit/{user.id}").get_data(as_text=True))

    assert "nível de sistema" in html


def test_edit_root_does_not_require_a_name(client, user_service, family_service):
    family_service.list_families.return_value = []
    root = _user(name=None, family_id=None, role=Role.ROOT, username="root", email="root@example.com")
    user_service.get_user.return_value = root

    html = client.get(f"/user/edit/{root.id}").get_data(as_text=True)

    name_input = re.search(r'<input[^>]*id="name"[^>]*>', html).group(0)
    assert "required" not in name_input
    assert 'value="None"' not in html


def test_edit_other_roles_require_a_name(client, user_service, family_service):
    family_service.list_families.return_value = []
    user = _user(family_id=None, role=Role.SYSTEM_ADMIN)
    user_service.get_user.return_value = user

    html = client.get(f"/user/edit/{user.id}").get_data(as_text=True)

    assert "required" in re.search(r'<input[^>]*id="name"[^>]*>', html).group(0)


def test_edit_nonexistent_user_returns_404(client, user_service):
    user_id = uuid.uuid4()
    user_service.get_user.side_effect = user_not_found(user_id)

    assert client.get(f"/user/edit/{user_id}").status_code == 404


# --- Atualização ---

def test_update_user_calls_service_and_redirects_to_list(client, user_service):
    user_id = uuid.uuid4()

    response = client.post(
        f"/user/update/{user_id}", data={"name": "Maria", "username": "maria", "email": "maria@example.com"}
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/user/list"
    user_service.update_user.assert_called_once_with(
        user_id, UpdateUserDTO(name="Maria", username="maria", email="maria@example.com")
    )


def test_update_user_ignores_role_family_and_password_in_the_form(client, user_service):
    user_id = uuid.uuid4()

    client.post(f"/user/update/{user_id}", data={
        "name": "Maria", "username": "maria", "email": "maria@example.com",
        "role": "SYSTEM_ADMIN", "family_id": str(uuid.uuid4()), "temporary_password": "outra-senha",
    })

    dto = user_service.update_user.call_args.args[1]
    assert set(vars(dto)) == {"name", "username", "email"}


def test_update_user_flashes_success_message(client, user_service):
    user_service.list_users_page.return_value = page_of([])

    response = client.post(
        f"/user/update/{uuid.uuid4()}",
        data={"name": "Maria", "username": "maria", "email": "maria@example.com"}, follow_redirects=True,
    )

    assert response.status_code == 200
    assert "atualizado com sucesso" in unescape(response.get_data(as_text=True))


def test_update_duplicate_username_re_presents_form_with_error(client, user_service, family_service):
    family = _family("Família A")
    user = _user(family_id=family.id)
    family_service.list_families.return_value = [family]
    user_service.get_user.return_value = user
    user_service.update_user.side_effect = username_already_exists("maria")

    response = client.post(
        f"/user/update/{user.id}", data={"name": "Maria", "username": "maria", "email": "maria@example.com"}
    )

    assert response.status_code == 409
    html = unescape(response.get_data(as_text=True))
    assert f'action="/user/update/{user.id}"' in html
    assert 'value="maria"' in html and 'value="Maria"' in html
    assert 'Já existe um usuário com o nome de usuário "maria".' in html


def test_update_user_with_invalid_input_re_presents_form(client, user_service, family_service):
    user = _user(family_id=uuid.uuid4())
    family_service.list_families.return_value = []
    user_service.get_user.return_value = user
    user_service.update_user.side_effect = DomainValidationError("name", "Nome é obrigatório.")

    response = client.post(
        f"/user/update/{user.id}", data={"name": "   ", "username": "joao", "email": "joao@example.com"}
    )

    assert response.status_code == 400
    assert "Nome é obrigatório." in unescape(response.get_data(as_text=True))


def test_update_nonexistent_user_returns_404(client, user_service):
    user_id = uuid.uuid4()
    user_service.update_user.side_effect = user_not_found(user_id)

    response = client.post(
        f"/user/update/{user_id}", data={"name": "Maria", "username": "maria", "email": "maria@example.com"}
    )

    assert response.status_code == 404


# --- Exclusão ---

def test_delete_user_calls_service_and_redirects_to_list(client, user_service):
    user_id = uuid.uuid4()

    response = client.post(f"/user/delete/{user_id}")

    assert response.status_code == 302
    assert response.headers["Location"] == "/user/list"
    user_service.delete_user.assert_called_once_with(user_id)


def test_delete_user_flashes_success_message(client, user_service):
    user_service.list_users_page.return_value = page_of([])

    response = client.post(f"/user/delete/{uuid.uuid4()}", follow_redirects=True)

    assert response.status_code == 200
    assert "excluído com sucesso" in unescape(response.get_data(as_text=True))


def test_delete_user_with_dependencies_flashes_error_and_redirects(client, user_service):
    user_id = uuid.uuid4()
    user_service.delete_user.side_effect = user_has_dependencies(user_id)
    user_service.list_users_page.return_value = page_of([])

    response = client.post(f"/user/delete/{user_id}", follow_redirects=True)

    assert response.status_code == 200
    assert "Não é possível excluir o usuário" in unescape(response.get_data(as_text=True))


def test_delete_root_flashes_error_and_redirects(client, user_service):
    user_id = uuid.uuid4()
    user_service.delete_user.side_effect = root_cannot_be_deleted(user_id)
    user_service.list_users_page.return_value = page_of([])

    response = client.post(f"/user/delete/{user_id}", follow_redirects=True)

    assert "usuário root" in unescape(response.get_data(as_text=True))


def test_delete_nonexistent_user_returns_404(client, user_service):
    user_id = uuid.uuid4()
    user_service.delete_user.side_effect = user_not_found(user_id)

    assert client.post(f"/user/delete/{user_id}").status_code == 404


def test_confirm_delete_user_page_is_presented(client, user_service):
    user_id = uuid.uuid4()
    user_service.preview_user_deletion.return_value = DeletionPreviewDTO(name="João da Silva")

    response = client.get(f"/user/confirm-delete/{user_id}")

    assert response.status_code == 200
    html = unescape(response.get_data(as_text=True))
    assert "João da Silva" in html
    assert f'action="/user/delete/{user_id}"' in html
    assert 'href="/user/list"' in html
    user_service.preview_user_deletion.assert_called_once_with(user_id)
    user_service.delete_user.assert_not_called()


def test_confirm_delete_user_with_dependencies_explains_and_offers_no_delete(client, user_service):
    user_id = uuid.uuid4()
    reason = str(user_has_dependencies(user_id))
    user_service.preview_user_deletion.return_value = DeletionPreviewDTO(name="João", blocked_reason=reason)

    html = unescape(client.get(f"/user/confirm-delete/{user_id}").get_data(as_text=True))

    assert reason in html
    assert f'action="/user/delete/{user_id}"' not in html
    assert 'href="/user/list"' in html


def test_confirm_delete_nonexistent_user_returns_404(client, user_service):
    user_id = uuid.uuid4()
    user_service.preview_user_deletion.side_effect = user_not_found(user_id)

    assert client.get(f"/user/confirm-delete/{user_id}").status_code == 404
