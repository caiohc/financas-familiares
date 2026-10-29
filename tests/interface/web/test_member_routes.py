import uuid
from decimal import Decimal
from html import unescape

from application.dtos.family_dtos import (
    CreateMemberDTO,
    FamilyResponseDTO,
    MemberResponseDTO,
    UpdateMemberDTO,
)
from domain.family.exceptions import member_already_exists, member_has_dependencies, member_not_found
from domain.shared.exceptions import DomainValidationError

def _family(name: str) -> FamilyResponseDTO:
    return FamilyResponseDTO(id=uuid.uuid4(), name=name, current_balance=Decimal("0.00"))

def _member(name: str, family_id) -> MemberResponseDTO:
    return MemberResponseDTO(id=uuid.uuid4(), family_id=family_id, name=name)

# --- Listagem ---

def test_list_members_shows_entries_across_families(client, member_service, family_service):
    family_a = _family("Família A")
    family_b = _family("Família B")
    family_service.list_families.return_value = [family_a, family_b]
    member_service.list_all_members.return_value = [_member("João", family_a.id), _member("Pedro", family_b.id)]

    response = client.get("/member/list")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for text in ("João", "Pedro", "Família A", "Família B"):
        assert text in html

def test_list_members_offers_create_button(client, member_service):
    member_service.list_all_members.return_value = []

    assert 'href="/member/new"' in client.get("/member/list").get_data(as_text=True)

def test_list_members_rows_are_wired_to_edit_and_delete(client, member_service, family_service):
    family = _family("Família A")
    member = _member("João", family.id)
    family_service.list_families.return_value = [family]
    member_service.list_all_members.return_value = [member]

    html = client.get("/member/list").get_data(as_text=True)

    assert f'href="/member/edit/{member.id}"' in html
    assert f'href="/member/confirm-delete/{member.id}"' in html
    assert "confirm(" not in html

# --- Criação ---

def test_new_member_form_offers_family_selector(client, member_service, family_service):
    family_a = _family("Família A")
    family_b = _family("Família B")
    family_service.list_families.return_value = [family_a, family_b]

    response = client.get("/member/new")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'action="/member/create"' in html
    assert 'name="family_id"' in html
    assert f'value="{family_a.id}"' in html
    assert f'value="{family_b.id}"' in html
    member_service.create_member.assert_not_called()

def test_create_member_calls_service_and_redirects_to_list(client, member_service):
    family_id = uuid.uuid4()

    response = client.post("/member/create", data={"family_id": str(family_id), "name": "João"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/member/list"
    member_service.create_member.assert_called_once_with(CreateMemberDTO(family_id=family_id, name="João"))

def test_create_member_flashes_success_message(client, member_service):
    member_service.list_all_members.return_value = []

    response = client.post(
        "/member/create", data={"family_id": str(uuid.uuid4()), "name": "João"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert "cadastrado com sucesso" in unescape(response.get_data(as_text=True))

def test_create_duplicate_member_re_presents_form_keeping_selected_family(client, member_service, family_service):
    family = _family("Família A")
    family_service.list_families.return_value = [family]
    member_service.create_member.side_effect = member_already_exists("João")

    response = client.post("/member/create", data={"family_id": str(family.id), "name": "João"})

    assert response.status_code == 409
    assert "Location" not in response.headers
    html = unescape(response.get_data(as_text=True))
    assert 'Já existe um membro com o nome "João" nesta família.' in html
    assert 'value="João"' in html
    assert f'value="{family.id}" selected' in html

def test_create_member_with_invalid_name_re_presents_form(client, member_service, family_service):
    family = _family("Família A")
    family_service.list_families.return_value = [family]
    member_service.create_member.side_effect = DomainValidationError("name", "Nome do membro é obrigatório.")

    response = client.post("/member/create", data={"family_id": str(family.id), "name": "   "})

    assert response.status_code == 400
    html = unescape(response.get_data(as_text=True))
    assert "Nome do membro é obrigatório." in html
    assert f'value="{family.id}" selected' in html

def test_create_member_without_family_returns_400(client, member_service):
    response = client.post("/member/create", data={"name": "João"})

    assert response.status_code == 400
    member_service.create_member.assert_not_called()

# --- Edição ---

def test_edit_member_form_is_presented_with_family_read_only(client, member_service, family_service):
    family = _family("Família A")
    member = _member("João", family.id)
    family_service.list_families.return_value = [family]
    member_service.get_member.return_value = member

    response = client.get(f"/member/edit/{member.id}")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert f'action="/member/update/{member.id}"' in html
    assert 'value="João"' in html
    assert "Família A" in html
    assert 'name="family_id"' not in html
    member_service.get_member.assert_called_once_with(member.id)

def test_edit_nonexistent_member_returns_404(client, member_service):
    member_id = uuid.uuid4()
    member_service.get_member.side_effect = member_not_found(member_id)

    assert client.get(f"/member/edit/{member_id}").status_code == 404

# --- Atualização ---

def test_update_member_calls_service_and_redirects_to_list(client, member_service):
    member_id = uuid.uuid4()

    response = client.post(f"/member/update/{member_id}", data={"name": "Maria"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/member/list"
    member_service.update_member.assert_called_once_with(member_id, UpdateMemberDTO(name="Maria"))

def test_update_member_flashes_success_message(client, member_service):
    member_service.list_all_members.return_value = []

    response = client.post(f"/member/update/{uuid.uuid4()}", data={"name": "Maria"}, follow_redirects=True)

    assert response.status_code == 200
    assert "atualizado com sucesso" in unescape(response.get_data(as_text=True))

def test_update_duplicate_member_re_presents_form_with_error(client, member_service, family_service):
    family = _family("Família A")
    member = _member("Maria", family.id)
    family_service.list_families.return_value = [family]
    member_service.get_member.return_value = member
    member_service.update_member.side_effect = member_already_exists("João")

    response = client.post(f"/member/update/{member.id}", data={"name": "João"})

    assert response.status_code == 409
    html = unescape(response.get_data(as_text=True))
    assert f'action="/member/update/{member.id}"' in html
    assert 'value="João"' in html
    assert 'Já existe um membro com o nome "João" nesta família.' in html

def test_update_member_with_invalid_name_re_presents_form(client, member_service, family_service):
    family = _family("Família A")
    member = _member("Maria", family.id)
    family_service.list_families.return_value = [family]
    member_service.get_member.return_value = member
    member_service.update_member.side_effect = DomainValidationError("name", "Nome do membro é obrigatório.")

    response = client.post(f"/member/update/{member.id}", data={"name": "   "})

    assert response.status_code == 400
    assert "Nome do membro é obrigatório." in unescape(response.get_data(as_text=True))

def test_update_nonexistent_member_returns_404(client, member_service):
    member_id = uuid.uuid4()
    member_service.update_member.side_effect = member_not_found(member_id)

    assert client.post(f"/member/update/{member_id}", data={"name": "Maria"}).status_code == 404

# --- Exclusão ---

def test_delete_member_calls_service_and_redirects_to_list(client, member_service):
    member_id = uuid.uuid4()

    response = client.post(f"/member/delete/{member_id}")

    assert response.status_code == 302
    assert response.headers["Location"] == "/member/list"
    member_service.delete_member.assert_called_once_with(member_id)

def test_delete_member_flashes_success_message(client, member_service):
    member_service.list_all_members.return_value = []

    response = client.post(f"/member/delete/{uuid.uuid4()}", follow_redirects=True)

    assert response.status_code == 200
    assert "excluído com sucesso" in unescape(response.get_data(as_text=True))

def test_delete_member_with_dependencies_flashes_error_and_redirects(client, member_service):
    member_id = uuid.uuid4()
    member_service.delete_member.side_effect = member_has_dependencies(member_id)
    member_service.list_all_members.return_value = []

    response = client.post(f"/member/delete/{member_id}", follow_redirects=True)

    assert response.status_code == 200
    assert "Não é possível excluir o membro" in unescape(response.get_data(as_text=True))

def test_delete_nonexistent_member_returns_404(client, member_service):
    member_id = uuid.uuid4()
    member_service.delete_member.side_effect = member_not_found(member_id)

    assert client.post(f"/member/delete/{member_id}").status_code == 404

def test_confirm_delete_member_page_is_presented(client, member_service):
    from application.dtos.shared_dtos import DeletionPreviewDTO

    member_id = uuid.uuid4()
    member_service.preview_member_deletion.return_value = DeletionPreviewDTO(name="João")

    response = client.get(f"/member/confirm-delete/{member_id}")

    assert response.status_code == 200
    html = unescape(response.get_data(as_text=True))
    assert "João" in html
    assert f'action="/member/delete/{member_id}"' in html
    assert 'href="/member/list"' in html
    member_service.preview_member_deletion.assert_called_once_with(member_id)
    member_service.delete_member.assert_not_called()

def test_confirm_delete_member_with_dependencies_explains_and_offers_no_delete(client, member_service):
    from application.dtos.shared_dtos import DeletionPreviewDTO
    from domain.family.exceptions import member_has_dependencies

    member_id = uuid.uuid4()
    reason = str(member_has_dependencies(member_id))
    member_service.preview_member_deletion.return_value = DeletionPreviewDTO(name="João", blocked_reason=reason)

    html = unescape(client.get(f"/member/confirm-delete/{member_id}").get_data(as_text=True))

    assert reason in html
    assert f'action="/member/delete/{member_id}"' not in html
    assert 'href="/member/list"' in html

def test_confirm_delete_nonexistent_member_returns_404(client, member_service):
    member_id = uuid.uuid4()
    member_service.preview_member_deletion.side_effect = member_not_found(member_id)

    assert client.get(f"/member/confirm-delete/{member_id}").status_code == 404
