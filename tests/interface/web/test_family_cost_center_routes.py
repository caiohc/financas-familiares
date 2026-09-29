import uuid
from html import unescape

from application.dtos.family_dtos import CreateFamilyCostCenterDTO, UpdateFamilyCostCenterDTO

def test_create_family_cost_center_calls_service_and_redirects_to_list(client, family_cost_center_service):
    family_id = uuid.uuid4()

    response = client.post(
        f"/family/{family_id}/cost-center/create",
        data={"name": "Casa de Praia", "description": "Litoral"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == f"/family/{family_id}/cost-center/list"
    family_cost_center_service.create_family_cost_center.assert_called_once_with(
        CreateFamilyCostCenterDTO(family_id=family_id, name="Casa de Praia", description="Litoral")
    )

def test_create_family_cost_center_flashes_success_message(client, family_cost_center_service):
    family_id = uuid.uuid4()
    family_cost_center_service.list_family_cost_centers.return_value = []

    response = client.post(
        f"/family/{family_id}/cost-center/create",
        data={"name": "Casa de Praia"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "criado com sucesso" in unescape(response.get_data(as_text=True))

def test_create_duplicate_family_cost_center_re_presents_form_with_error(client, family_cost_center_service):
    from domain.family.exceptions import FamilyCostCenterAlreadyExistsError

    family_id = uuid.uuid4()
    family_cost_center_service.create_family_cost_center.side_effect = FamilyCostCenterAlreadyExistsError(
        family_id, "Casa de Praia"
    )

    response = client.post(f"/family/{family_id}/cost-center/create", data={"name": "Casa de Praia"})

    assert response.status_code == 409
    assert "Location" not in response.headers
    html = unescape(response.get_data(as_text=True))
    assert 'Já existe um centro de custo com o nome "Casa de Praia" nesta família.' in html

def test_new_family_cost_center_form_is_presented(client, family_cost_center_service):
    family_id = uuid.uuid4()

    response = client.get(f"/family/{family_id}/cost-center/new")

    assert response.status_code == 200
    family_cost_center_service.create_family_cost_center.assert_not_called()

def test_list_family_cost_centers(client, family_cost_center_service):
    from application.dtos.family_dtos import FamilyCostCenterResponseDTO

    family_id = uuid.uuid4()
    family_cost_center_service.list_family_cost_centers.return_value = [
        FamilyCostCenterResponseDTO(id=uuid.uuid4(), family_id=family_id, name="Casa de Praia", description=None),
        FamilyCostCenterResponseDTO(id=uuid.uuid4(), family_id=family_id, name="Filhos", description=None),
    ]

    response = client.get(f"/family/{family_id}/cost-center/list")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Casa de Praia" in html
    assert "Filhos" in html
    family_cost_center_service.list_family_cost_centers.assert_called_once_with(family_id)

def test_edit_family_cost_center_form_is_presented(client, family_cost_center_service):
    from application.dtos.family_dtos import FamilyCostCenterResponseDTO

    family_id = uuid.uuid4()
    cost_center_id = uuid.uuid4()
    family_cost_center_service.get_family_cost_center.return_value = FamilyCostCenterResponseDTO(
        id=cost_center_id, family_id=family_id, name="Casa de Praia", description=None
    )

    response = client.get(f"/family/{family_id}/cost-center/edit/{cost_center_id}")

    assert response.status_code == 200
    assert 'value="Casa de Praia"' in response.get_data(as_text=True)
    family_cost_center_service.get_family_cost_center.assert_called_once_with(cost_center_id)

def test_edit_nonexistent_family_cost_center_returns_404(client, family_cost_center_service):
    from domain.family.exceptions import FamilyCostCenterNotFoundError

    family_id = uuid.uuid4()
    cost_center_id = uuid.uuid4()
    family_cost_center_service.get_family_cost_center.side_effect = FamilyCostCenterNotFoundError(cost_center_id)

    response = client.get(f"/family/{family_id}/cost-center/edit/{cost_center_id}")

    assert response.status_code == 404

def test_update_family_cost_center_calls_service_and_redirects_to_list(client, family_cost_center_service):
    family_id = uuid.uuid4()
    cost_center_id = uuid.uuid4()

    response = client.post(
        f"/family/{family_id}/cost-center/update/{cost_center_id}",
        data={"name": "Nome Novo", "description": "Desc"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == f"/family/{family_id}/cost-center/list"
    family_cost_center_service.update_family_cost_center.assert_called_once_with(
        cost_center_id, UpdateFamilyCostCenterDTO(name="Nome Novo", description="Desc")
    )

def test_update_family_cost_center_flashes_success_message(client, family_cost_center_service):
    family_id = uuid.uuid4()
    cost_center_id = uuid.uuid4()
    family_cost_center_service.list_family_cost_centers.return_value = []

    response = client.post(
        f"/family/{family_id}/cost-center/update/{cost_center_id}",
        data={"name": "Nome Novo"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "atualizado com sucesso" in unescape(response.get_data(as_text=True))

def test_update_duplicate_family_cost_center_re_presents_form_with_error(client, family_cost_center_service):
    from domain.family.exceptions import FamilyCostCenterAlreadyExistsError

    family_id = uuid.uuid4()
    cost_center_id = uuid.uuid4()
    family_cost_center_service.update_family_cost_center.side_effect = FamilyCostCenterAlreadyExistsError(
        family_id, "Casa de Praia"
    )

    response = client.post(
        f"/family/{family_id}/cost-center/update/{cost_center_id}", data={"name": "Casa de Praia"}
    )

    assert response.status_code == 409
    assert "Location" not in response.headers

def test_update_nonexistent_family_cost_center_returns_404(client, family_cost_center_service):
    from domain.family.exceptions import FamilyCostCenterNotFoundError

    family_id = uuid.uuid4()
    cost_center_id = uuid.uuid4()
    family_cost_center_service.update_family_cost_center.side_effect = FamilyCostCenterNotFoundError(cost_center_id)

    response = client.post(
        f"/family/{family_id}/cost-center/update/{cost_center_id}", data={"name": "Nome Novo"}
    )

    assert response.status_code == 404

def test_delete_family_cost_center_calls_service_and_redirects_to_list(client, family_cost_center_service):
    family_id = uuid.uuid4()
    cost_center_id = uuid.uuid4()

    response = client.post(f"/family/{family_id}/cost-center/delete/{cost_center_id}")

    assert response.status_code == 302
    assert response.headers["Location"] == f"/family/{family_id}/cost-center/list"
    family_cost_center_service.delete_family_cost_center.assert_called_once_with(cost_center_id)

def test_delete_family_cost_center_flashes_success_message(client, family_cost_center_service):
    family_id = uuid.uuid4()
    cost_center_id = uuid.uuid4()
    family_cost_center_service.list_family_cost_centers.return_value = []

    response = client.post(
        f"/family/{family_id}/cost-center/delete/{cost_center_id}", follow_redirects=True
    )

    assert response.status_code == 200
    assert "excluído com sucesso" in unescape(response.get_data(as_text=True))

def test_delete_nonexistent_family_cost_center_returns_404(client, family_cost_center_service):
    from domain.family.exceptions import FamilyCostCenterNotFoundError

    family_id = uuid.uuid4()
    cost_center_id = uuid.uuid4()
    family_cost_center_service.delete_family_cost_center.side_effect = FamilyCostCenterNotFoundError(cost_center_id)

    response = client.post(f"/family/{family_id}/cost-center/delete/{cost_center_id}")

    assert response.status_code == 404
