import re
import uuid
from datetime import datetime
from decimal import Decimal
from html import unescape

import pytest

from application.dtos.family_dtos import FamilyResponseDTO
from application.dtos.identity_dtos import (
    CreateUserDTO,
    InvitationIssuedDTO,
    SessionUserDTO,
    UpdateUserDTO,
    UserResponseDTO,
)
from application.dtos.shared_dtos import DeletionPreviewDTO
from domain.identity.entities import AccountStatus, Role
from domain.identity.exceptions import (
    access_denied,
    cannot_act_on_self,
    root_cannot_be_deleted,
    user_has_dependencies,
    user_not_found,
    username_already_exists,
)
from domain.identity.invitations import InvitationPurpose
from domain.shared.exceptions import DomainValidationError, EntityNotFoundError
from fakes.pagination import page_of


def _family(name: str) -> FamilyResponseDTO:
    return FamilyResponseDTO(id=uuid.uuid4(), name=name, current_balance=Decimal("0.00"))


def _user(name="João da Silva", family_id=None, role=Role.FAMILY_USER, username="joao", email="joao@example.com",
          status=AccountStatus.ACTIVE, user_id=None):
    return UserResponseDTO(
        id=user_id or uuid.uuid4(), role=role, family_id=family_id, name=name, username=username, email=email,
        status=status, is_active=status is not AccountStatus.DEACTIVATED, is_pending=status is AccountStatus.PENDING,
    )


def _issued(user=None, purpose=InvitationPurpose.ACTIVATION, code="ABCD-EFGH", email_sent=True) -> InvitationIssuedDTO:
    return InvitationIssuedDTO(
        user=user or _user(status=AccountStatus.PENDING), purpose=purpose, code=code,
        expires_at=datetime(2026, 11, 9, 12, 0), email_sent=email_sent,
    )


def _login_as(auth_service, role, family_id=None):
    auth_service.find_session_user_by_username.return_value = SessionUserDTO(
        id=uuid.uuid4(), role=role, family_id=family_id, name="Quem Age", username="quem", email="quem@example.com",
        session_id="s",
    )


FORM = {
    "role": "FAMILY_USER", "name": "João", "username": "joao", "email": "joao@example.com",
    "email_confirmation": "joao@example.com",
}


# --- Listagem ---

def test_list_users_shows_name_username_email_role_family_and_status(client, user_service, family_service):
    family = _family("Família Silva")
    family_service.list_families.return_value = [family]
    user_service.list_users_page.return_value = page_of([
        _user("João da Silva", family.id, Role.FAMILY_ADMIN, "joao", "joao@example.com"),
        _user("Caio", None, Role.SYSTEM_ADMIN, "caio", "caio@example.com", status=AccountStatus.PENDING),
    ])

    response = client.get("/user/list")

    assert response.status_code == 200
    html = unescape(response.get_data(as_text=True))
    for text in ("João da Silva", "joao", "joao@example.com", "Administrador da família",
                 f"Família Silva · {str(family.id)[:8]}", "Caio", "caio@example.com", "Administrador do sistema",
                 "Ativo", "Pendente de ativação"):
        assert text in html


@pytest.mark.parametrize("status, label", [
    (AccountStatus.ACTIVE, "Ativo"), (AccountStatus.PENDING, "Pendente de ativação"),
    (AccountStatus.AWAITING_PASSWORD, "Aguardando nova senha"), (AccountStatus.DEACTIVATED, "Desativado"),
])
def test_list_shows_each_account_status(client, user_service, status, label):
    user_service.list_users_page.return_value = page_of([_user(status=status, family_id=uuid.uuid4())])

    assert label in client.get("/user/list").get_data(as_text=True)


def test_list_users_shows_a_dash_for_the_nameless_root(client, user_service):
    user_service.list_users_page.return_value = page_of([_user(None, None, Role.ROOT, "root", "root@example.com")])

    html = client.get("/user/list").get_data(as_text=True)

    assert "root@example.com" in html and "Root" in html
    assert "None" not in html


def test_list_users_has_sortable_name_username_and_email_headers_only(client, user_service):
    user_service.list_users_page.return_value = page_of([_user()])

    html = client.get("/user/list").get_data(as_text=True)

    headers = {re.sub(r"<[^>]+>", "", th).strip(): ("href" in th) for th in re.findall(r"<th[^>]*>.*?</th>", html, re.S)}
    assert headers["Nome"] and headers["Usuário"] and headers["E-mail"]
    assert not any(headers[h] for h in ("Papel", "Família", "Situação", "Ações"))


def test_list_users_highlights_the_search_in_name_username_and_email(client, user_service):
    user_service.list_users_page.return_value = page_of(
        [_user("Silvana", None, Role.SYSTEM_ADMIN, "silvana", "silvana@silva.com")], search="silv"
    )

    html = client.get("/user/list?q=silv").get_data(as_text=True)

    assert len(re.findall(r"<mark>silv</mark>", html, re.I)) == 4


def test_list_never_renders_a_password_hash_or_code(client, user_service):
    user_service.list_users_page.return_value = page_of([_user()])

    html = client.get("/user/list").get_data(as_text=True).lower()

    assert "password_hash" not in html and "argon2" not in html and "code" not in html.replace("barcode", "")


def test_list_passes_the_acting_principal_to_the_service(client, user_service, dev_user):
    user_service.list_users_page.return_value = page_of([])

    client.get("/user/list")

    assert user_service.list_users_page.call_args.kwargs["actor"] == dev_user.principal


def test_list_empty_state(client, user_service):
    user_service.list_users_page.return_value = page_of([])
    assert "Nenhum usuário cadastrado ainda." in client.get("/user/list").get_data(as_text=True)


def test_list_offers_create_button(client, user_service):
    user_service.list_users_page.return_value = page_of([])
    assert 'href="/user/new"' in client.get("/user/list").get_data(as_text=True)


def _row(html, username):
    """A linha da tabela do usuário (achada pelo nome de usuário: o root não tem ações, logo nem o id aparece)."""
    return re.search(rf'<tr>(?:(?!</tr>).)*<td>{username}</td>(?:(?!</tr>).)*</tr>', html, re.S).group(0)


def test_each_row_offers_only_the_actions_the_actor_may_perform(client, user_service, family_service):
    """O administrador do sistema edita/desativa/exclui usuários de família e redefine a senha de outro administrador."""
    family = _family("Silva")
    family_service.list_families.return_value = [family]
    active = _user("Ana", family.id)
    pending = _user("Pedro", family.id, username="pedro", email="p@example.com", status=AccountStatus.PENDING)
    deactivated = _user("Rui", family.id, username="rui", email="r@example.com", status=AccountStatus.DEACTIVATED)
    peer = _user("Par", None, Role.SYSTEM_ADMIN, "par", "par@example.com")
    root = _user(None, None, Role.ROOT, "root", "root@example.com")
    user_service.list_users_page.return_value = page_of([active, pending, deactivated, peer, root])

    html = client.get("/user/list").get_data(as_text=True)

    ana, ped, rui, par, rt = (_row(html, u.username) for u in (active, pending, deactivated, peer, root))
    assert "Desativar" in ana and "Editar" in ana and "Excluir" in ana
    assert "Reenviar convite" not in ana and "Redefinir senha" not in ana          # já ativou: redefine sozinho
    assert "Reenviar convite" in ped
    assert "Reativar" in rui and "Desativar" not in rui
    assert "Redefinir senha" in par and "Desativar" in par
    assert "Editar" not in rt and "Excluir" not in rt and "Desativar" not in rt and "Redefinir" not in rt


def test_family_admin_sees_actions_only_on_its_own_family(client, user_service, family_service, auth_service):
    family = _family("Silva")
    _login_as(auth_service, Role.FAMILY_ADMIN, family.id)
    family_service.list_families.return_value = [family]
    mine = _user("Ana", family.id)
    pending = _user("Pedro", family.id, username="pedro", email="p@example.com", status=AccountStatus.PENDING)
    user_service.list_users_page.return_value = page_of([mine, pending])

    html = client.get("/user/list").get_data(as_text=True)

    assert "Editar" in _row(html, mine.username) and "Reenviar convite" in _row(html, pending.username)


def test_the_actor_cannot_deactivate_or_delete_their_own_row(client, user_service, family_service, dev_user):
    me = _user("Eu", None, Role.SYSTEM_ADMIN, "eu", "eu@example.com", user_id=dev_user.id)
    user_service.list_users_page.return_value = page_of([me])

    row = _row(client.get("/user/list").get_data(as_text=True), me.username)

    assert "Editar" in row and "Desativar" not in row and "Excluir" not in row


# --- Acesso à área de usuários ---

@pytest.mark.parametrize("path", ["/user/list", "/user/new", f"/user/edit/{uuid.uuid4()}",
                                  f"/user/confirm-delete/{uuid.uuid4()}"])
def test_a_family_user_cannot_open_any_user_page(client, auth_service, user_service, path):
    _login_as(auth_service, Role.FAMILY_USER, uuid.uuid4())

    assert client.get(path).status_code == 403
    user_service.list_users_page.assert_not_called()


@pytest.mark.parametrize("path", [
    "/user/create", f"/user/update/{uuid.uuid4()}", f"/user/delete/{uuid.uuid4()}",
    f"/user/deactivate/{uuid.uuid4()}", f"/user/reactivate/{uuid.uuid4()}", f"/user/reissue-invitation/{uuid.uuid4()}",
])
def test_a_family_user_cannot_post_to_any_user_endpoint(client, auth_service, user_service, path):
    _login_as(auth_service, Role.FAMILY_USER, uuid.uuid4())

    assert client.post(path, data=FORM).status_code == 403
    assert user_service.mock_calls == []


def test_the_sidebar_hides_the_users_menu_from_a_family_user(client, auth_service, dashboard_service):
    from application.dtos.dashboard_dtos import EntityCountsDTO
    dashboard_service.get_entity_counts.return_value = EntityCountsDTO(families=0, members=0, users=0, cost_centers=0, categories=0)
    _login_as(auth_service, Role.FAMILY_USER, uuid.uuid4())

    assert 'href="/user/list"' not in client.get("/").get_data(as_text=True).split('<main')[0]


def test_the_sidebar_shows_the_users_menu_to_administrators(client, dashboard_service):
    from application.dtos.dashboard_dtos import EntityCountsDTO
    dashboard_service.get_entity_counts.return_value = EntityCountsDTO(families=0, members=0, users=0, cost_centers=0, categories=0)

    assert 'href="/user/list"' in client.get("/").get_data(as_text=True)


# --- Formulário de cadastro: sem senha, e-mail em dois campos ---

def test_new_user_form_has_no_password_fields_and_two_email_fields(client, family_service):
    family_service.list_families.return_value = []

    html = client.get("/user/new").get_data(as_text=True)

    assert 'action="/user/create"' in html
    assert 'type="password"' not in html and "temporary_password" not in html and 'name="password' not in html
    assert re.search(r'<input[^>]*type="email"[^>]*name="email"', html)
    assert re.search(r'<input[^>]*type="email"[^>]*name="email_confirmation"', html)


def test_the_email_fields_allow_pasting(client, family_service):
    family_service.list_families.return_value = []

    html = client.get("/user/new").get_data(as_text=True)

    assert "onpaste" not in html.lower() and "paste" not in html.lower()


def test_new_user_form_declares_the_confirmation_dialog_and_loads_its_script(client, family_service):
    family_service.list_families.return_value = []

    html = client.get("/user/new").get_data(as_text=True)

    assert "data-email-confirm-form" in html
    assert '<dialog id="email-confirm-dialog"' in html
    assert 'id="email-confirm-address"' in html and "data-confirm" in html and "data-cancel" in html
    assert 'js/email_confirm.js' in html


def test_the_confirmation_script_is_served_and_never_styles_or_blocks_paste(client):
    response = client.get("/static/js/email_confirm.js")

    assert response.status_code == 200
    script = response.get_data(as_text=True)
    assert "showModal" in script and "requestSubmit" in script
    assert ".style" not in script and "paste" not in script.lower()


def test_new_user_form_for_a_system_admin_offers_every_creatable_role_but_root(client, family_service):
    family_a, family_b = _family("Família A"), _family("Família B")
    family_service.list_families.return_value = [family_a, family_b]

    html = client.get("/user/new").get_data(as_text=True)

    for role in ("SYSTEM_ADMIN", "FAMILY_ADMIN", "FAMILY_USER"):
        assert f'value="{role}"' in html
    assert 'value="ROOT"' not in html
    assert f'value="{family_a.id}"' in html and f'value="{family_b.id}"' in html


def test_new_user_form_for_the_root_offers_only_system_admin(client, auth_service, family_service):
    _login_as(auth_service, Role.ROOT)
    family_service.list_families.return_value = []

    html = client.get("/user/new").get_data(as_text=True)

    assert 'value="SYSTEM_ADMIN"' in html
    assert 'value="FAMILY_ADMIN"' not in html and 'value="FAMILY_USER"' not in html


def test_new_user_form_for_a_family_admin_offers_only_its_own_family_and_family_roles(client, auth_service, family_service):
    mine, other = _family("Minha"), _family("Outra")
    _login_as(auth_service, Role.FAMILY_ADMIN, mine.id)
    family_service.list_families.return_value = [mine, other]

    html = client.get("/user/new").get_data(as_text=True)

    assert f'value="{mine.id}"' in html and f'value="{other.id}"' not in html
    assert 'value="SYSTEM_ADMIN"' not in html
    assert 'value="FAMILY_ADMIN"' in html and 'value="FAMILY_USER"' in html


# --- Criação ---

def test_create_user_calls_the_service_with_the_actor_and_shows_the_code_once(client, user_service, dev_user):
    family_id = uuid.uuid4()
    user_service.create_user.return_value = _issued(code="KXPE-BREF")

    response = client.post("/user/create", data={**FORM, "family_id": str(family_id)})

    assert response.status_code == 200
    user_service.create_user.assert_called_once_with(dev_user.principal, CreateUserDTO(
        role=Role.FAMILY_USER, family_id=family_id, name="João", username="joao", email="joao@example.com",
        email_confirmation="joao@example.com",
    ))
    html = response.get_data(as_text=True)
    assert "KXPE-BREF" in html and 'id="invitation-code"' in html
    assert "não será mostrado de novo" in unescape(html)


def test_the_code_page_is_not_cacheable_and_is_not_a_redirect(client, user_service):
    user_service.create_user.return_value = _issued()

    response = client.post("/user/create", data={**FORM, "family_id": str(uuid.uuid4())})

    assert response.status_code == 200 and "Location" not in response.headers
    assert response.headers["Cache-Control"] == "no-store"


def test_the_code_is_never_in_a_cookie_or_url(client, user_service):
    user_service.create_user.return_value = _issued(code="KXPE-BREF")

    response = client.post("/user/create", data={**FORM, "family_id": str(uuid.uuid4())})

    assert "KXPE" not in "".join(response.headers.getlist("Set-Cookie"))
    assert "KXPE" not in response.headers.get("Location", "")


def test_the_code_page_warns_when_the_email_could_not_be_sent(client, user_service):
    user_service.create_user.return_value = _issued(email_sent=False)

    html = unescape(client.post("/user/create", data={**FORM, "family_id": str(uuid.uuid4())}).get_data(as_text=True))

    assert "Não foi possível enviar o e-mail" in html and "Reenviar convite" in html


def test_the_code_page_confirms_the_destination_when_the_email_was_sent(client, user_service):
    user_service.create_user.return_value = _issued(user=_user(email="destino@example.com", status=AccountStatus.PENDING))

    html = client.post("/user/create", data={**FORM, "family_id": str(uuid.uuid4())}).get_data(as_text=True)

    assert "destino@example.com" in html and "foi enviado para" in unescape(html)


def test_create_system_admin_sends_no_family(client, user_service):
    user_service.create_user.return_value = _issued()

    client.post("/user/create", data={**FORM, "role": "SYSTEM_ADMIN", "family_id": ""})

    dto = user_service.create_user.call_args.args[1]
    assert (dto.role, dto.family_id) == (Role.SYSTEM_ADMIN, None)


def test_create_user_ignores_password_fields_sent_by_a_tamperer(client, user_service):
    user_service.create_user.return_value = _issued()

    client.post("/user/create", data={**FORM, "family_id": str(uuid.uuid4()), "password": "x", "temporary_password": "y"})

    dto = user_service.create_user.call_args.args[1]
    assert set(vars(dto)) == {"role", "family_id", "name", "username", "email", "email_confirmation"}


def test_family_admin_creating_without_a_family_gets_its_own_family(client, auth_service, user_service):
    family_id = uuid.uuid4()
    _login_as(auth_service, Role.FAMILY_ADMIN, family_id)
    user_service.create_user.return_value = _issued()

    client.post("/user/create", data={**FORM, "family_id": ""})

    assert user_service.create_user.call_args.args[1].family_id == family_id


def test_forged_family_by_a_family_admin_is_forwarded_so_the_service_can_refuse(client, auth_service, user_service):
    _login_as(auth_service, Role.FAMILY_ADMIN, uuid.uuid4())
    other = uuid.uuid4()
    user_service.create_user.side_effect = access_denied("create_user")

    response = client.post("/user/create", data={**FORM, "family_id": str(other)})

    assert response.status_code == 403
    assert user_service.create_user.call_args.args[1].family_id == other


def test_create_duplicate_username_re_presents_form_keeping_values(client, user_service, family_service):
    family = _family("Família A")
    family_service.list_families.return_value = [family]
    user_service.create_user.side_effect = username_already_exists("joao")

    response = client.post("/user/create", data={**FORM, "family_id": str(family.id)})

    assert response.status_code == 409 and "Location" not in response.headers
    html = unescape(response.get_data(as_text=True))
    assert 'Já existe um usuário com o nome de usuário "joao".' in html
    assert 'value="João"' in html and 'value="joao"' in html and html.count('value="joao@example.com"') == 2
    assert f'value="{family.id}" selected' in html and 'value="FAMILY_USER" selected' in html


def test_create_user_with_mismatching_emails_re_presents_the_form(client, user_service, family_service):
    family_service.list_families.return_value = []
    user_service.create_user.side_effect = DomainValidationError("email_confirmation", "Os e-mails informados não conferem.")

    response = client.post("/user/create", data={**FORM, "email_confirmation": "outro@example.com"})

    assert response.status_code == 400
    assert "Os e-mails informados não conferem." in unescape(response.get_data(as_text=True))


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

    assert response.status_code == 400 and "Família não encontrada." in response.get_data(as_text=True)


def test_create_user_without_role_leaves_the_decision_to_the_domain(client, user_service, family_service):
    family_service.list_families.return_value = []
    user_service.create_user.side_effect = DomainValidationError("role", "Papel do usuário é obrigatório.")

    response = client.post("/user/create", data={k: v for k, v in FORM.items() if k != "role"})

    assert response.status_code == 400
    assert user_service.create_user.call_args.args[1].role is None


@pytest.mark.parametrize("role", ["SUPERUSER", "root", "ROOT ", "'; DROP TABLE users;--", "0"])
def test_create_user_with_unknown_role_returns_400_without_calling_the_service(client, user_service, role):
    assert client.post("/user/create", data={**FORM, "role": role}).status_code == 400
    user_service.create_user.assert_not_called()


@pytest.mark.parametrize("family_id", ["not-a-uuid", "1", "00000000-0000-0000-0000-00000000000g", "<script>"])
def test_create_user_with_malformed_family_id_returns_400_without_calling_the_service(client, user_service, family_id):
    assert client.post("/user/create", data={**FORM, "family_id": family_id}).status_code == 400
    user_service.create_user.assert_not_called()


def test_the_form_never_echoes_back_a_password(client, user_service, family_service):
    family_service.list_families.return_value = []
    user_service.create_user.side_effect = DomainValidationError("email", "Informe um e-mail válido.")

    html = client.post("/user/create", data={**FORM, "password": "segredo-123"}).get_data(as_text=True)

    assert "segredo-123" not in html


# --- Edição ---

def test_edit_form_of_a_pending_user_lets_the_administrator_correct_the_email(client, user_service, family_service):
    family = _family("Família A")
    user = _user(family_id=family.id, status=AccountStatus.PENDING)
    family_service.list_families.return_value = [family]
    user_service.get_user.return_value = user

    html = unescape(client.get(f"/user/edit/{user.id}").get_data(as_text=True))

    assert f'action="/user/update/{user.id}"' in html
    assert re.search(r'<input[^>]*type="email"[^>]*name="email"', html)
    assert 'name="email_confirmation"' not in html
    assert "Família A" in html and 'name="role"' not in html and 'name="family_id"' not in html


def test_edit_form_of_an_activated_user_shows_the_email_as_read_only(client, user_service, family_service):
    user = _user(family_id=uuid.uuid4(), status=AccountStatus.ACTIVE, email="travado@example.com")
    family_service.list_families.return_value = []
    user_service.get_user.return_value = user

    html = unescape(client.get(f"/user/edit/{user.id}").get_data(as_text=True))

    assert "travado@example.com" in html
    assert not re.search(r'<input[^>]*type="email"', html)
    assert "só pode ser alterado pelo próprio usuário" in html


def test_edit_form_has_no_password_or_invitation_fields(client, user_service, family_service):
    user = _user(family_id=uuid.uuid4())
    family_service.list_families.return_value = []
    user_service.get_user.return_value = user

    html = client.get(f"/user/edit/{user.id}").get_data(as_text=True)

    assert 'type="password"' not in html and "temporary" not in html and "dialog" not in html


def test_edit_root_does_not_require_a_name(client, user_service, family_service, auth_service):
    root = _user(name=None, role=Role.ROOT, username="root", email="root@example.com")
    family_service.list_families.return_value = []
    user_service.get_user.return_value = root
    _login_as(auth_service, Role.ROOT)

    response = client.get(f"/user/edit/{root.id}")

    # o root não é gerenciável por ninguém: a tela de edição é negada
    assert response.status_code == 403


def test_edit_form_of_a_user_the_actor_cannot_manage_is_forbidden(client, user_service, family_service):
    family_service.list_families.return_value = []
    root = _user(name=None, role=Role.ROOT, username="root", email="root@example.com")
    user_service.get_user.return_value = root

    assert client.get(f"/user/edit/{root.id}").status_code == 403


def test_edit_nonexistent_user_returns_404(client, user_service):
    user_id = uuid.uuid4()
    user_service.get_user.side_effect = user_not_found(user_id)

    assert client.get(f"/user/edit/{user_id}").status_code == 404


# --- Atualização ---

def test_update_user_calls_service_with_the_actor_and_redirects(client, user_service, dev_user):
    user_id = uuid.uuid4()

    response = client.post(f"/user/update/{user_id}", data={"name": "Maria", "username": "maria", "email": "maria@example.com"})

    assert response.status_code == 302 and response.headers["Location"] == "/user/list"
    user_service.update_user.assert_called_once_with(
        dev_user.principal, user_id, UpdateUserDTO(name="Maria", username="maria", email="maria@example.com")
    )


def test_update_ignores_role_family_password_and_status_sent_by_a_tamperer(client, user_service):
    client.post(f"/user/update/{uuid.uuid4()}", data={
        "name": "Maria", "username": "maria", "email": "maria@example.com",
        "role": "SYSTEM_ADMIN", "family_id": str(uuid.uuid4()), "password": "x", "is_active": "false",
    })

    dto = user_service.update_user.call_args.args[2]
    assert set(vars(dto)) == {"name", "username", "email"}


def test_update_flashes_success_message(client, user_service):
    user_service.list_users_page.return_value = page_of([])

    response = client.post(
        f"/user/update/{uuid.uuid4()}", data={"name": "Maria", "username": "maria", "email": "maria@example.com"},
        follow_redirects=True,
    )

    assert "atualizado com sucesso" in unescape(response.get_data(as_text=True))


def test_update_duplicate_username_re_presents_form_with_error(client, user_service, family_service):
    user = _user(family_id=uuid.uuid4())
    family_service.list_families.return_value = []
    user_service.get_user.return_value = user
    user_service.update_user.side_effect = username_already_exists("maria")

    response = client.post(f"/user/update/{user.id}", data={"name": "Maria", "username": "maria", "email": "maria@example.com"})

    assert response.status_code == 409
    html = unescape(response.get_data(as_text=True))
    assert f'action="/user/update/{user.id}"' in html and 'value="maria"' in html
    assert 'Já existe um usuário com o nome de usuário "maria".' in html


def test_update_to_a_locked_email_is_refused_with_a_clear_message(client, user_service, family_service):
    user = _user(family_id=uuid.uuid4())
    family_service.list_families.return_value = []
    user_service.get_user.return_value = user
    user_service.update_user.side_effect = DomainValidationError("email", "O e-mail não pode ser alterado depois que a conta foi ativada.")

    response = client.post(f"/user/update/{user.id}", data={"name": "X", "username": "x", "email": "invasor@example.com"})

    assert response.status_code == 400
    assert "depois que a conta foi ativada" in unescape(response.get_data(as_text=True))


def test_update_with_invalid_input_re_presents_form(client, user_service, family_service):
    user = _user(family_id=uuid.uuid4())
    family_service.list_families.return_value = []
    user_service.get_user.return_value = user
    user_service.update_user.side_effect = DomainValidationError("name", "Nome é obrigatório.")

    response = client.post(f"/user/update/{user.id}", data={"name": "   ", "username": "joao", "email": "joao@example.com"})

    assert response.status_code == 400
    assert "Nome é obrigatório." in unescape(response.get_data(as_text=True))


def test_update_nonexistent_user_returns_404(client, user_service):
    user_service.update_user.side_effect = user_not_found(uuid.uuid4())
    assert client.post(f"/user/update/{uuid.uuid4()}", data={"name": "M", "username": "m", "email": "m@example.com"}).status_code == 404


def test_update_denied_by_the_service_returns_403(client, user_service):
    user_service.update_user.side_effect = access_denied("update_user")
    assert client.post(f"/user/update/{uuid.uuid4()}", data={"name": "M", "username": "m", "email": "m@example.com"}).status_code == 403


# --- Desativar, reativar e convite ---

@pytest.mark.parametrize("path, method_name, message", [
    ("deactivate", "deactivate_user", "desativado"),
    ("reactivate", "reactivate_user", "reativado"),
])
def test_deactivate_and_reactivate_call_the_service_and_redirect(client, user_service, dev_user, path, method_name, message):
    user_id = uuid.uuid4()
    user_service.list_users_page.return_value = page_of([])

    response = client.post(f"/user/{path}/{user_id}", follow_redirects=True)

    getattr(user_service, method_name).assert_called_once_with(dev_user.principal, user_id)
    assert message in unescape(response.get_data(as_text=True)).lower()


@pytest.mark.parametrize("path, method_name", [("deactivate", "deactivate_user"), ("reactivate", "reactivate_user")])
def test_status_changes_by_get_are_not_allowed(client, user_service, path, method_name):
    assert client.get(f"/user/{path}/{uuid.uuid4()}").status_code == 405
    getattr(user_service, method_name).assert_not_called()


@pytest.mark.parametrize("path, method_name", [("deactivate", "deactivate_user"), ("reactivate", "reactivate_user")])
def test_status_changes_map_service_errors(client, user_service, path, method_name):
    service_method = getattr(user_service, method_name)

    service_method.side_effect = user_not_found(uuid.uuid4())
    assert client.post(f"/user/{path}/{uuid.uuid4()}").status_code == 404
    service_method.side_effect = access_denied(method_name)
    assert client.post(f"/user/{path}/{uuid.uuid4()}").status_code == 403


def test_deactivating_yourself_flashes_the_domain_error(client, user_service):
    user_service.deactivate_user.side_effect = cannot_act_on_self("desativar")
    user_service.list_users_page.return_value = page_of([])

    response = client.post(f"/user/deactivate/{uuid.uuid4()}", follow_redirects=True)

    assert "não pode desativar a sua própria conta" in unescape(response.get_data(as_text=True))


def test_reissue_invitation_shows_the_new_code_once(client, user_service, dev_user):
    user_id = uuid.uuid4()
    user_service.issue_invitation.return_value = _issued(code="NOVO-CODE", purpose=InvitationPurpose.ADMIN_RESET)

    response = client.post(f"/user/reissue-invitation/{user_id}")

    user_service.issue_invitation.assert_called_once_with(dev_user.principal, user_id)
    html = unescape(response.get_data(as_text=True))
    assert response.status_code == 200 and "NOVO-CODE" in html and "Convite reenviado" in html
    assert response.headers["Cache-Control"] == "no-store"


def test_reissue_invitation_by_get_is_not_allowed(client, user_service):
    assert client.get(f"/user/reissue-invitation/{uuid.uuid4()}").status_code == 405
    user_service.issue_invitation.assert_not_called()


def test_reissue_invitation_flashes_domain_errors(client, user_service):
    user_service.issue_invitation.side_effect = DomainValidationError("user", "Esta pessoa já definiu a própria senha.")
    user_service.list_users_page.return_value = page_of([])

    response = client.post(f"/user/reissue-invitation/{uuid.uuid4()}", follow_redirects=True)

    assert "já definiu a própria senha" in unescape(response.get_data(as_text=True))


def test_reissue_invitation_maps_not_found_and_denied(client, user_service):
    user_service.issue_invitation.side_effect = user_not_found(uuid.uuid4())
    assert client.post(f"/user/reissue-invitation/{uuid.uuid4()}").status_code == 404
    user_service.issue_invitation.side_effect = access_denied("issue_invitation")
    assert client.post(f"/user/reissue-invitation/{uuid.uuid4()}").status_code == 403


# --- Exclusão ---

def test_delete_user_calls_service_with_the_actor_and_redirects(client, user_service, dev_user):
    user_id = uuid.uuid4()

    response = client.post(f"/user/delete/{user_id}")

    assert response.status_code == 302 and response.headers["Location"] == "/user/list"
    user_service.delete_user.assert_called_once_with(dev_user.principal, user_id)


def test_delete_user_flashes_success_message(client, user_service):
    user_service.list_users_page.return_value = page_of([])
    response = client.post(f"/user/delete/{uuid.uuid4()}", follow_redirects=True)
    assert "excluído com sucesso" in unescape(response.get_data(as_text=True))


def test_delete_user_with_dependencies_flashes_error_and_redirects(client, user_service):
    user_id = uuid.uuid4()
    user_service.delete_user.side_effect = user_has_dependencies(user_id)
    user_service.list_users_page.return_value = page_of([])

    response = client.post(f"/user/delete/{user_id}", follow_redirects=True)

    assert "Não é possível excluir o usuário" in unescape(response.get_data(as_text=True))


def test_delete_root_flashes_error_and_redirects(client, user_service):
    user_id = uuid.uuid4()
    user_service.delete_user.side_effect = root_cannot_be_deleted(user_id)
    user_service.list_users_page.return_value = page_of([])

    response = client.post(f"/user/delete/{user_id}", follow_redirects=True)

    assert "usuário root" in unescape(response.get_data(as_text=True))


def test_deleting_yourself_flashes_the_domain_error(client, user_service):
    user_service.delete_user.side_effect = cannot_act_on_self("excluir")
    user_service.list_users_page.return_value = page_of([])

    response = client.post(f"/user/delete/{uuid.uuid4()}", follow_redirects=True)

    assert "não pode excluir a sua própria conta" in unescape(response.get_data(as_text=True))


def test_delete_maps_not_found_and_denied(client, user_service):
    user_service.delete_user.side_effect = user_not_found(uuid.uuid4())
    assert client.post(f"/user/delete/{uuid.uuid4()}").status_code == 404
    user_service.delete_user.side_effect = access_denied("delete_user")
    assert client.post(f"/user/delete/{uuid.uuid4()}").status_code == 403


def test_confirm_delete_page_is_presented(client, user_service, dev_user):
    user_id = uuid.uuid4()
    user_service.preview_user_deletion.return_value = DeletionPreviewDTO(name="João da Silva")

    response = client.get(f"/user/confirm-delete/{user_id}")

    assert response.status_code == 200
    html = unescape(response.get_data(as_text=True))
    assert "João da Silva" in html and f'action="/user/delete/{user_id}"' in html and 'href="/user/list"' in html
    user_service.preview_user_deletion.assert_called_once_with(dev_user.principal, user_id)
    user_service.delete_user.assert_not_called()


def test_confirm_delete_with_a_reason_offers_no_delete(client, user_service):
    user_id = uuid.uuid4()
    reason = str(user_has_dependencies(user_id))
    user_service.preview_user_deletion.return_value = DeletionPreviewDTO(name="João", blocked_reason=reason)

    html = unescape(client.get(f"/user/confirm-delete/{user_id}").get_data(as_text=True))

    assert reason in html and f'action="/user/delete/{user_id}"' not in html


def test_confirm_delete_maps_not_found_and_denied(client, user_service):
    user_service.preview_user_deletion.side_effect = user_not_found(uuid.uuid4())
    assert client.get(f"/user/confirm-delete/{uuid.uuid4()}").status_code == 404
    user_service.preview_user_deletion.side_effect = access_denied("delete_user")
    assert client.get(f"/user/confirm-delete/{uuid.uuid4()}").status_code == 403
