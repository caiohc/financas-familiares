import uuid
from html import unescape

from application.dtos.financial_dtos import CategoryResponseDTO, CreateCategoryDTO, UpdateCategoryDTO
from domain.financial.entities import TransactionType
from domain.financial.exceptions import category_already_exists, category_has_dependencies, category_not_found
from domain.shared.exceptions import DomainValidationError

EXPENSE = TransactionType.EXPENSE
INCOME = TransactionType.INCOME

def _category(name: str, type_: TransactionType = EXPENSE) -> CategoryResponseDTO:
    return CategoryResponseDTO(id=uuid.uuid4(), name=name, type=type_)

# --- Listagem ---

def test_list_categories_shows_names_and_type_labels(client, category_service):
    category_service.list_categories.return_value = [_category("Lazer", EXPENSE), _category("Salário", INCOME)]

    response = client.get("/category/list")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for text in ("Lazer", "Salário", "Despesa", "Receita"):
        assert text in html

def test_list_categories_rows_are_wired_to_edit_and_confirm_delete(client, category_service):
    category = _category("Lazer")
    category_service.list_categories.return_value = [category]

    html = client.get("/category/list").get_data(as_text=True)

    assert 'href="/category/new"' in html
    assert f'href="/category/edit/{category.id}"' in html
    assert f'href="/category/confirm-delete/{category.id}"' in html
    assert "confirm(" not in html

# --- Criação ---

def test_new_category_form_offers_income_and_expense_types(client, category_service):
    response = client.get("/category/new")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'action="/category/create"' in html
    assert 'value="EXPENSE"' in html
    assert 'value="INCOME"' in html
    category_service.create_category.assert_not_called()

def test_create_category_calls_service_and_redirects_to_list(client, category_service):
    response = client.post("/category/create", data={"name": "Lazer", "type": "EXPENSE"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/category/list"
    category_service.create_category.assert_called_once_with(CreateCategoryDTO(name="Lazer", type=EXPENSE))

def test_create_category_with_unknown_type_passes_none_to_the_domain(client, category_service):
    # O controlador não decide se o tipo é válido: só traduz o formulário. Quem valida é o domínio.
    client.post("/category/create", data={"name": "Lazer", "type": "XYZ"})

    category_service.create_category.assert_called_once_with(CreateCategoryDTO(name="Lazer", type=None))

def test_create_category_flashes_success_message(client, category_service):
    category_service.list_categories.return_value = []

    response = client.post("/category/create", data={"name": "Lazer", "type": "EXPENSE"}, follow_redirects=True)

    assert response.status_code == 200
    assert "criada com sucesso" in unescape(response.get_data(as_text=True))

def test_create_duplicate_category_re_presents_form_keeping_values(client, category_service):
    category_service.create_category.side_effect = category_already_exists("Lazer")

    response = client.post("/category/create", data={"name": "Lazer", "type": "INCOME"})

    assert response.status_code == 409
    assert "Location" not in response.headers
    html = unescape(response.get_data(as_text=True))
    assert 'Já existe uma categoria com o nome "Lazer".' in html
    assert 'value="Lazer"' in html
    assert 'value="INCOME" selected' in html

def test_create_category_with_invalid_data_re_presents_form(client, category_service):
    category_service.create_category.side_effect = DomainValidationError("type", "Tipo da categoria é obrigatório.")

    response = client.post("/category/create", data={"name": "Lazer"})

    assert response.status_code == 400
    assert "Tipo da categoria é obrigatório." in unescape(response.get_data(as_text=True))

# --- Edição ---

def test_edit_category_form_is_presented(client, category_service):
    category = _category("Salário", INCOME)
    category_service.get_category.return_value = category

    response = client.get(f"/category/edit/{category.id}")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert f'action="/category/update/{category.id}"' in html
    assert 'value="Salário"' in html
    assert 'value="INCOME" selected' in html

def test_edit_nonexistent_category_returns_404(client, category_service):
    category_id = uuid.uuid4()
    category_service.get_category.side_effect = category_not_found(category_id)

    assert client.get(f"/category/edit/{category_id}").status_code == 404

# --- Atualização ---

def test_update_category_calls_service_and_redirects_to_list(client, category_service):
    category_id = uuid.uuid4()

    response = client.post(f"/category/update/{category_id}", data={"name": "Vendas", "type": "INCOME"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/category/list"
    category_service.update_category.assert_called_once_with(category_id, UpdateCategoryDTO(name="Vendas", type=INCOME))

def test_update_category_flashes_success_message(client, category_service):
    category_service.list_categories.return_value = []

    response = client.post(
        f"/category/update/{uuid.uuid4()}", data={"name": "Vendas", "type": "INCOME"}, follow_redirects=True
    )

    assert "atualizada com sucesso" in unescape(response.get_data(as_text=True))

def test_update_duplicate_category_re_presents_form_with_error(client, category_service):
    category_id = uuid.uuid4()
    category_service.update_category.side_effect = category_already_exists("Lazer")

    response = client.post(f"/category/update/{category_id}", data={"name": "Lazer", "type": "EXPENSE"})

    assert response.status_code == 409
    html = unescape(response.get_data(as_text=True))
    assert f'action="/category/update/{category_id}"' in html
    assert 'Já existe uma categoria com o nome "Lazer".' in html

def test_update_nonexistent_category_returns_404(client, category_service):
    category_id = uuid.uuid4()
    category_service.update_category.side_effect = category_not_found(category_id)

    assert client.post(f"/category/update/{category_id}", data={"name": "X", "type": "EXPENSE"}).status_code == 404

# --- Exclusão ---

def test_confirm_delete_category_page_is_presented(client, category_service):
    from application.dtos.shared_dtos import DeletionPreviewDTO

    category_id = uuid.uuid4()
    category_service.preview_category_deletion.return_value = DeletionPreviewDTO(name="Lazer")

    response = client.get(f"/category/confirm-delete/{category_id}")

    assert response.status_code == 200
    html = unescape(response.get_data(as_text=True))
    assert "Lazer" in html
    assert f'action="/category/delete/{category_id}"' in html
    assert 'href="/category/list"' in html
    category_service.preview_category_deletion.assert_called_once_with(category_id)
    category_service.delete_category.assert_not_called()

def test_confirm_delete_category_with_dependencies_explains_and_offers_no_delete(client, category_service):
    from application.dtos.shared_dtos import DeletionPreviewDTO
    from domain.financial.exceptions import category_has_dependencies

    category_id = uuid.uuid4()
    reason = str(category_has_dependencies(category_id))
    category_service.preview_category_deletion.return_value = DeletionPreviewDTO(name="Lazer", blocked_reason=reason)

    html = unescape(client.get(f"/category/confirm-delete/{category_id}").get_data(as_text=True))

    assert reason in html
    assert f'action="/category/delete/{category_id}"' not in html
    assert 'href="/category/list"' in html

def test_confirm_delete_nonexistent_category_returns_404(client, category_service):
    category_id = uuid.uuid4()
    category_service.preview_category_deletion.side_effect = category_not_found(category_id)

    assert client.get(f"/category/confirm-delete/{category_id}").status_code == 404

def test_delete_category_calls_service_and_redirects_to_list(client, category_service):
    category_id = uuid.uuid4()

    response = client.post(f"/category/delete/{category_id}")

    assert response.status_code == 302
    assert response.headers["Location"] == "/category/list"
    category_service.delete_category.assert_called_once_with(category_id)

def test_delete_category_flashes_success_message(client, category_service):
    category_service.list_categories.return_value = []

    response = client.post(f"/category/delete/{uuid.uuid4()}", follow_redirects=True)

    assert "excluída com sucesso" in unescape(response.get_data(as_text=True))

def test_delete_category_with_dependencies_flashes_error_and_redirects(client, category_service):
    category_id = uuid.uuid4()
    category_service.delete_category.side_effect = category_has_dependencies(category_id)
    category_service.list_categories.return_value = []

    response = client.post(f"/category/delete/{category_id}", follow_redirects=True)

    assert "Não é possível excluir a categoria" in unescape(response.get_data(as_text=True))

def test_delete_nonexistent_category_returns_404(client, category_service):
    category_id = uuid.uuid4()
    category_service.delete_category.side_effect = category_not_found(category_id)

    assert client.post(f"/category/delete/{category_id}").status_code == 404
