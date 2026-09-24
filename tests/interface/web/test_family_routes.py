import uuid
from decimal import Decimal
from html import unescape

from application.dtos.family_dtos import CreateFamilyDTO, FamilyResponseDTO
from domain.family.exceptions import FamilyAlreadyExistsError

def _family_response(name: str) -> FamilyResponseDTO:
    return FamilyResponseDTO(id=uuid.uuid4(), name=name, current_balance=Decimal("0.00"))

def test_create_family_calls_service_and_redirects_to_list(client, family_service):
    response = client.post("/family/create", data={"name": "Família Souza"})

    # PRG: um POST bem-sucedido redireciona (302) para a listagem
    assert response.status_code == 302
    assert response.headers["Location"] == "/family/list"

    # O controlador deve traduzir o formulário em um DTO e delegar ao serviço
    family_service.create_family.assert_called_once_with(CreateFamilyDTO(name="Família Souza"))

def test_create_family_flashes_success_message_surviving_the_redirect(client, family_service):
    family_service.list_families.return_value = []

    # follow_redirects segue o 302 na mesma sessão de cookies, como um navegador faria
    response = client.post("/family/create", data={"name": "Família Souza"}, follow_redirects=True)

    assert response.status_code == 200
    assert 'Família "Família Souza" criada com sucesso.' in unescape(response.get_data(as_text=True))

def test_flash_message_does_not_survive_a_second_request(client, family_service):
    family_service.list_families.return_value = []

    client.post("/family/create", data={"name": "Família Souza"})
    first_list = client.get("/family/list").get_data(as_text=True)
    second_list = client.get("/family/list").get_data(as_text=True)

    assert "criada com sucesso" in first_list
    assert "criada com sucesso" not in second_list

def test_list_families_returns_names_from_service(client, family_service):
    family_service.list_families.return_value = [
        _family_response("Família Silva"),
        _family_response("Família Souza"),
    ]

    response = client.get("/family/list")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Família Silva" in html
    assert "Família Souza" in html
    family_service.list_families.assert_called_once_with()

def test_list_families_when_empty(client, family_service):
    family_service.list_families.return_value = []

    response = client.get("/family/list")

    assert response.status_code == 200
    assert "Nenhuma família" in response.get_data(as_text=True)

def test_list_families_action_buttons_are_placeholders(client, family_service):
    family_service.list_families.return_value = [_family_response("Família Silva")]

    html = client.get("/family/list").get_data(as_text=True)

    # update/delete ainda não têm rota: os botões existem, mas são inertes (disabled)
    assert 'href="/family/update' not in html
    assert 'action="/family/delete' not in html
    assert html.count("disabled") == 2

def test_new_family_form_is_presented(client, family_service):
    response = client.get("/family/new")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Integrar Nova Família" in html
    assert 'action="/family/create"' in html
    assert 'name="name"' in html
    family_service.create_family.assert_not_called()

def test_create_duplicate_family_re_presents_form_with_error(client, family_service):
    family_service.create_family.side_effect = FamilyAlreadyExistsError("Família Souza")

    response = client.post("/family/create", data={"name": "Família Souza"})

    # Não há redirect: o formulário é reapresentado com status de conflito
    assert response.status_code == 409
    assert "Location" not in response.headers

    html = response.get_data(as_text=True)
    assert 'action="/family/create"' in html
    assert 'value="Família Souza"' in html
    assert 'Já existe uma família com o nome "Família Souza".' in unescape(html)

    family_service.create_family.assert_called_once_with(CreateFamilyDTO(name="Família Souza"))
