import uuid
from fakes.pagination import page_of
from decimal import Decimal
from html import unescape

from application.dtos.family_dtos import (
    CreateFamilyCostCenterDTO,
    FamilyCostCenterResponseDTO,
    FamilyResponseDTO,
    UpdateFamilyCostCenterDTO,
)
from domain.family.exceptions import cost_center_already_exists, cost_center_not_found

def _family(name: str, family_id=None) -> FamilyResponseDTO:
    return FamilyResponseDTO(id=family_id or uuid.uuid4(), name=name, current_balance=Decimal("0.00"))

def _cost_center(name: str, family_id, cost_center_id=None) -> FamilyCostCenterResponseDTO:
    return FamilyCostCenterResponseDTO(
        id=cost_center_id or uuid.uuid4(), family_id=family_id, name=name, description=None
    )

# --- Listagem ---

def test_list_cost_centers_shows_entries_across_families(client, family_cost_center_service, family_service):
    family_a = _family("Família A")
    family_b = _family("Família B")
    family_service.list_families.return_value = [family_a, family_b]
    family_cost_center_service.list_all_family_cost_centers_page.return_value = page_of([
        _cost_center("Casa de Praia", family_a.id),
        _cost_center("Outro", family_b.id),
    ])

    response = client.get("/cost-center/list")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Casa de Praia" in html
    assert "Outro" in html
    assert "Família A" in html
    assert "Família B" in html

def test_list_cost_centers_offers_create_button(client, family_cost_center_service):
    family_cost_center_service.list_all_family_cost_centers_page.return_value = page_of([])

    html = client.get("/cost-center/list").get_data(as_text=True)

    assert 'href="/cost-center/new"' in html

def test_list_cost_centers_rows_are_wired_to_edit_and_delete(client, family_cost_center_service, family_service):
    family = _family("Família A")
    cost_center = _cost_center("Casa de Praia", family.id)
    family_service.list_families.return_value = [family]
    family_cost_center_service.list_all_family_cost_centers_page.return_value = page_of([cost_center])

    html = client.get("/cost-center/list").get_data(as_text=True)

    assert f'href="/cost-center/edit/{cost_center.id}"' in html
    assert f'href="/cost-center/confirm-delete/{cost_center.id}"' in html
    assert "confirm(" not in html

# --- Criação ---

def test_new_cost_center_form_offers_family_selector(client, family_cost_center_service, family_service):
    family_a = _family("Família A")
    family_b = _family("Família B")
    family_service.list_families.return_value = [family_a, family_b]

    response = client.get("/cost-center/new")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'action="/cost-center/create"' in html
    assert 'name="family_id"' in html
    assert f'value="{family_a.id}"' in html
    assert f'value="{family_b.id}"' in html
    family_cost_center_service.create_family_cost_center.assert_not_called()

def test_create_cost_center_calls_service_and_redirects_to_list(client, family_cost_center_service):
    family_id = uuid.uuid4()

    response = client.post(
        "/cost-center/create",
        data={"family_id": str(family_id), "name": "Casa de Praia", "description": "Litoral"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/cost-center/list"
    family_cost_center_service.create_family_cost_center.assert_called_once_with(
        CreateFamilyCostCenterDTO(family_id=family_id, name="Casa de Praia", description="Litoral")
    )

def test_create_cost_center_flashes_success_message(client, family_cost_center_service):
    family_cost_center_service.list_all_family_cost_centers_page.return_value = page_of([])

    response = client.post(
        "/cost-center/create",
        data={"family_id": str(uuid.uuid4()), "name": "Casa de Praia"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "criado com sucesso" in unescape(response.get_data(as_text=True))

def test_create_duplicate_cost_center_re_presents_form_keeping_selected_family(
    client, family_cost_center_service, family_service
):
    family = _family("Família A")
    family_service.list_families.return_value = [family]
    family_cost_center_service.create_family_cost_center.side_effect = cost_center_already_exists("Casa de Praia")

    response = client.post(
        "/cost-center/create", data={"family_id": str(family.id), "name": "Casa de Praia"}
    )

    assert response.status_code == 409
    assert "Location" not in response.headers
    html = unescape(response.get_data(as_text=True))
    assert 'Já existe um centro de custo com o nome "Casa de Praia" nesta família.' in html
    assert 'value="Casa de Praia"' in html
    assert f'value="{family.id}" selected' in html

def test_create_cost_center_without_family_returns_400(client, family_cost_center_service):
    response = client.post("/cost-center/create", data={"name": "Casa de Praia"})

    assert response.status_code == 400
    family_cost_center_service.create_family_cost_center.assert_not_called()

# --- Edição ---

def test_edit_cost_center_form_is_presented_with_family_read_only(
    client, family_cost_center_service, family_service
):
    family = _family("Família A")
    cost_center = _cost_center("Casa de Praia", family.id)
    family_service.list_families.return_value = [family]
    family_cost_center_service.get_family_cost_center.return_value = cost_center

    response = client.get(f"/cost-center/edit/{cost_center.id}")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert f'action="/cost-center/update/{cost_center.id}"' in html
    assert 'value="Casa de Praia"' in html
    assert "Família A" in html
    # A família de um centro de custo existente não muda: sem seletor na edição.
    assert 'name="family_id"' not in html
    family_cost_center_service.get_family_cost_center.assert_called_once_with(cost_center.id)

def test_edit_nonexistent_cost_center_returns_404(client, family_cost_center_service):
    cost_center_id = uuid.uuid4()
    family_cost_center_service.get_family_cost_center.side_effect = cost_center_not_found(cost_center_id)

    response = client.get(f"/cost-center/edit/{cost_center_id}")

    assert response.status_code == 404

# --- Atualização ---

def test_update_cost_center_calls_service_and_redirects_to_list(client, family_cost_center_service):
    cost_center_id = uuid.uuid4()

    response = client.post(
        f"/cost-center/update/{cost_center_id}", data={"name": "Nome Novo", "description": "Desc"}
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/cost-center/list"
    family_cost_center_service.update_family_cost_center.assert_called_once_with(
        cost_center_id, UpdateFamilyCostCenterDTO(name="Nome Novo", description="Desc")
    )

def test_update_cost_center_flashes_success_message(client, family_cost_center_service):
    family_cost_center_service.list_all_family_cost_centers_page.return_value = page_of([])

    response = client.post(
        f"/cost-center/update/{uuid.uuid4()}", data={"name": "Nome Novo"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert "atualizado com sucesso" in unescape(response.get_data(as_text=True))

def test_update_duplicate_cost_center_re_presents_form_with_error(
    client, family_cost_center_service, family_service
):
    family = _family("Família A")
    cost_center = _cost_center("Filhos", family.id)
    family_service.list_families.return_value = [family]
    family_cost_center_service.get_family_cost_center.return_value = cost_center
    family_cost_center_service.update_family_cost_center.side_effect = cost_center_already_exists("Casa de Praia")

    response = client.post(f"/cost-center/update/{cost_center.id}", data={"name": "Casa de Praia"})

    assert response.status_code == 409
    assert "Location" not in response.headers
    html = unescape(response.get_data(as_text=True))
    assert f'action="/cost-center/update/{cost_center.id}"' in html
    assert 'value="Casa de Praia"' in html
    assert 'Já existe um centro de custo com o nome "Casa de Praia" nesta família.' in html

def test_update_nonexistent_cost_center_returns_404(client, family_cost_center_service):
    cost_center_id = uuid.uuid4()
    family_cost_center_service.update_family_cost_center.side_effect = cost_center_not_found(cost_center_id)

    response = client.post(f"/cost-center/update/{cost_center_id}", data={"name": "Nome Novo"})

    assert response.status_code == 404

# --- Exclusão ---

def test_delete_cost_center_calls_service_and_redirects_to_list(client, family_cost_center_service):
    cost_center_id = uuid.uuid4()

    response = client.post(f"/cost-center/delete/{cost_center_id}")

    assert response.status_code == 302
    assert response.headers["Location"] == "/cost-center/list"
    family_cost_center_service.delete_family_cost_center.assert_called_once_with(cost_center_id)

def test_delete_cost_center_flashes_success_message(client, family_cost_center_service):
    family_cost_center_service.list_all_family_cost_centers_page.return_value = page_of([])

    response = client.post(f"/cost-center/delete/{uuid.uuid4()}", follow_redirects=True)

    assert response.status_code == 200
    assert "excluído com sucesso" in unescape(response.get_data(as_text=True))

def test_delete_nonexistent_cost_center_returns_404(client, family_cost_center_service):
    cost_center_id = uuid.uuid4()
    family_cost_center_service.delete_family_cost_center.side_effect = cost_center_not_found(cost_center_id)

    response = client.post(f"/cost-center/delete/{cost_center_id}")

    assert response.status_code == 404

def test_create_cost_center_with_invalid_name_re_presents_form_keeping_selected_family(
    client, family_cost_center_service, family_service
):
    from domain.shared.exceptions import DomainValidationError

    family = _family("Família A")
    family_service.list_families.return_value = [family]
    family_cost_center_service.create_family_cost_center.side_effect = DomainValidationError(
        "name", "Nome do centro de custo é obrigatório."
    )

    response = client.post("/cost-center/create", data={"family_id": str(family.id), "name": "   "})

    assert response.status_code == 400
    assert "Location" not in response.headers
    html = unescape(response.get_data(as_text=True))
    assert "Nome do centro de custo é obrigatório." in html
    assert f'value="{family.id}" selected' in html

def test_update_cost_center_with_invalid_name_re_presents_form_with_error(
    client, family_cost_center_service, family_service
):
    from domain.shared.exceptions import DomainValidationError

    family = _family("Família A")
    cost_center = _cost_center("Filhos", family.id)
    family_service.list_families.return_value = [family]
    family_cost_center_service.get_family_cost_center.return_value = cost_center
    family_cost_center_service.update_family_cost_center.side_effect = DomainValidationError(
        "name", "Nome do centro de custo é obrigatório."
    )

    response = client.post(f"/cost-center/update/{cost_center.id}", data={"name": "   "})

    assert response.status_code == 400
    assert "Location" not in response.headers
    html = unescape(response.get_data(as_text=True))
    assert f'action="/cost-center/update/{cost_center.id}"' in html
    assert "Nome do centro de custo é obrigatório." in html

def test_delete_cost_center_with_dependencies_flashes_error_and_redirects(client, family_cost_center_service):
    from domain.family.exceptions import cost_center_has_dependencies

    cost_center_id = uuid.uuid4()
    family_cost_center_service.delete_family_cost_center.side_effect = cost_center_has_dependencies(cost_center_id)
    family_cost_center_service.list_all_family_cost_centers_page.return_value = page_of([])

    response = client.post(f"/cost-center/delete/{cost_center_id}", follow_redirects=True)

    assert response.status_code == 200
    assert "Não é possível excluir o centro de custo" in unescape(response.get_data(as_text=True))

def test_confirm_delete_cost_center_page_is_presented(client, family_cost_center_service):
    from application.dtos.shared_dtos import DeletionPreviewDTO

    cost_center_id = uuid.uuid4()
    family_cost_center_service.preview_family_cost_center_deletion.return_value = DeletionPreviewDTO(name="Casa de Praia")

    response = client.get(f"/cost-center/confirm-delete/{cost_center_id}")

    assert response.status_code == 200
    html = unescape(response.get_data(as_text=True))
    assert "Casa de Praia" in html
    assert f'action="/cost-center/delete/{cost_center_id}"' in html
    assert 'href="/cost-center/list"' in html
    family_cost_center_service.preview_family_cost_center_deletion.assert_called_once_with(cost_center_id)
    family_cost_center_service.delete_family_cost_center.assert_not_called()

def test_confirm_delete_cost_center_with_dependencies_explains_and_offers_no_delete(client, family_cost_center_service):
    from application.dtos.shared_dtos import DeletionPreviewDTO
    from domain.family.exceptions import cost_center_has_dependencies

    cost_center_id = uuid.uuid4()
    reason = str(cost_center_has_dependencies(cost_center_id))
    family_cost_center_service.preview_family_cost_center_deletion.return_value = DeletionPreviewDTO(name="Casa de Praia", blocked_reason=reason)

    html = unescape(client.get(f"/cost-center/confirm-delete/{cost_center_id}").get_data(as_text=True))

    assert reason in html
    assert f'action="/cost-center/delete/{cost_center_id}"' not in html
    assert 'href="/cost-center/list"' in html

def test_confirm_delete_nonexistent_cost_center_returns_404(client, family_cost_center_service):
    cost_center_id = uuid.uuid4()
    family_cost_center_service.preview_family_cost_center_deletion.side_effect = cost_center_not_found(cost_center_id)

    assert client.get(f"/cost-center/confirm-delete/{cost_center_id}").status_code == 404
