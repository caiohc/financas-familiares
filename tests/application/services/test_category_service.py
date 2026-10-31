import uuid

import pytest

from application.dtos.financial_dtos import CreateCategoryDTO, UpdateCategoryDTO
from application.services.category_service import CategoryService
from domain.financial.entities import Category, TransactionType
from domain.shared.exceptions import (
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityHasDependenciesError,
    EntityNotFoundError,
)
from fakes.family_fakes import FakeUnitOfWork

EXPENSE = TransactionType.EXPENSE
INCOME = TransactionType.INCOME

@pytest.fixture
def uow():
    return FakeUnitOfWork()

@pytest.fixture
def service(uow):
    return CategoryService(uow)

def test_create_category(service: CategoryService, uow: FakeUnitOfWork):
    response = service.create_category(CreateCategoryDTO(name="Lazer", type=EXPENSE))

    assert (response.name, response.type) == ("Lazer", EXPENSE)
    assert uow.categories.get_by_id(response.id) is not None
    assert uow.committed is True

def test_create_category_with_duplicate_name_ignoring_case_and_spaces_raises(
    service: CategoryService, uow: FakeUnitOfWork
):
    uow.categories.save(Category(name="Lazer", type=EXPENSE))

    with pytest.raises(EntityAlreadyExistsError):
        service.create_category(CreateCategoryDTO(name="  lazer ", type=EXPENSE))

def test_create_category_with_same_name_but_other_type_also_raises(service: CategoryService, uow: FakeUnitOfWork):
    uow.categories.save(Category(name="Outros", type=EXPENSE))

    with pytest.raises(EntityAlreadyExistsError):
        service.create_category(CreateCategoryDTO(name="Outros", type=INCOME))

def test_create_category_without_type_raises_validation_error(service: CategoryService):
    with pytest.raises(DomainValidationError):
        service.create_category(CreateCategoryDTO(name="Lazer", type=None))

def test_get_category(service: CategoryService, uow: FakeUnitOfWork):
    category = Category(name="Saúde", type=EXPENSE)
    uow.categories.save(category)

    assert service.get_category(category.id).name == "Saúde"

def test_get_category_not_found(service: CategoryService):
    with pytest.raises(EntityNotFoundError):
        service.get_category(uuid.uuid4())

def test_list_categories_is_ordered_by_type_then_name(service: CategoryService, uow: FakeUnitOfWork):
    uow.categories.save(Category(name="Vendas", type=INCOME))
    uow.categories.save(Category(name="lazer", type=EXPENSE))
    uow.categories.save(Category(name="Alimentação", type=EXPENSE))
    uow.categories.save(Category(name="Salário", type=INCOME))

    names = [c.name for c in service.list_categories()]

    assert names == ["Alimentação", "lazer", "Salário", "Vendas"]

def test_update_category(service: CategoryService, uow: FakeUnitOfWork):
    category = Category(name="Vendas", type=EXPENSE)
    uow.categories.save(category)

    response = service.update_category(category.id, UpdateCategoryDTO(name="Vendas Online", type=INCOME))

    assert (response.name, response.type) == ("Vendas Online", INCOME)
    assert uow.committed is True

def test_update_category_to_own_current_name_is_allowed(service: CategoryService, uow: FakeUnitOfWork):
    category = Category(name="Lazer", type=EXPENSE)
    uow.categories.save(category)

    assert service.update_category(category.id, UpdateCategoryDTO(name="Lazer", type=EXPENSE)).name == "Lazer"

def test_update_category_to_duplicate_name_raises(service: CategoryService, uow: FakeUnitOfWork):
    uow.categories.save(Category(name="Lazer", type=EXPENSE))
    other = Category(name="Saúde", type=EXPENSE)
    uow.categories.save(other)

    with pytest.raises(EntityAlreadyExistsError):
        service.update_category(other.id, UpdateCategoryDTO(name="LAZER", type=EXPENSE))

def test_update_category_with_invalid_data_keeps_category_intact(service: CategoryService, uow: FakeUnitOfWork):
    category = Category(name="Lazer", type=EXPENSE)
    uow.categories.save(category)

    with pytest.raises(DomainValidationError):
        service.update_category(category.id, UpdateCategoryDTO(name="Diversão", type=None))

    stored = uow.categories.get_by_id(category.id)
    assert (stored.name, stored.type) == ("Lazer", EXPENSE)

def test_update_category_not_found(service: CategoryService):
    with pytest.raises(EntityNotFoundError):
        service.update_category(uuid.uuid4(), UpdateCategoryDTO(name="Qualquer", type=EXPENSE))

def test_delete_category_success(service: CategoryService, uow: FakeUnitOfWork):
    category = Category(name="A excluir", type=EXPENSE)
    uow.categories.save(category)

    service.delete_category(category.id)

    assert uow.categories.get_by_id(category.id) is None
    assert uow.committed is True

def test_delete_category_with_dependencies_raises_and_keeps_it(service: CategoryService, uow: FakeUnitOfWork):
    category = Category(name="Usada", type=EXPENSE)
    uow.categories.save(category)
    uow.categories.set_has_dependencies(True)

    with pytest.raises(EntityHasDependenciesError):
        service.delete_category(category.id)

    assert uow.categories.get_by_id(category.id) is not None

def test_delete_category_not_found(service: CategoryService):
    with pytest.raises(EntityNotFoundError):
        service.delete_category(uuid.uuid4())

# --- Carga das categorias padrão ---

def test_seed_default_categories_creates_all(service: CategoryService, uow: FakeUnitOfWork):
    defaults = [CreateCategoryDTO(name="Alimentação", type=EXPENSE), CreateCategoryDTO(name="Salário", type=INCOME)]

    result = service.seed_default_categories(defaults)

    assert (result.created, result.skipped) == (2, 0)
    assert {c.name for c in uow.categories.list_all()} == {"Alimentação", "Salário"}
    assert uow.committed is True

def test_seed_default_categories_is_idempotent(service: CategoryService, uow: FakeUnitOfWork):
    uow.categories.save(Category(name="alimentação", type=EXPENSE))
    defaults = [CreateCategoryDTO(name="Alimentação", type=EXPENSE), CreateCategoryDTO(name="Salário", type=INCOME)]

    result = service.seed_default_categories(defaults)

    assert (result.created, result.skipped) == (1, 1)
    assert len(uow.categories.list_all()) == 2

def test_seed_default_categories_with_an_invalid_item_creates_nothing(service: CategoryService, uow: FakeUnitOfWork):
    defaults = [CreateCategoryDTO(name="Alimentação", type=EXPENSE), CreateCategoryDTO(name="   ", type=INCOME)]

    with pytest.raises(DomainValidationError):
        service.seed_default_categories(defaults)

    assert uow.categories.list_all() == []
    assert uow.committed is False


def test_preview_category_deletion_without_dependencies(service, uow):
    category = Category(name="Lazer", type=EXPENSE)
    uow.categories.save(category)

    preview = service.preview_category_deletion(category.id)

    assert (preview.name, preview.blocked_reason) == ("Lazer", None)

def test_preview_category_deletion_with_dependencies_gives_the_reason(service, uow):
    from domain.financial.exceptions import category_has_dependencies

    category = Category(name="Lazer", type=EXPENSE)
    uow.categories.save(category)
    uow.categories.set_has_dependencies(True)

    preview = service.preview_category_deletion(category.id)

    assert preview.name == "Lazer"
    assert preview.blocked_reason == str(category_has_dependencies(category.id))

def test_preview_category_deletion_not_found(service):
    from domain.shared.exceptions import EntityNotFoundError

    with pytest.raises(EntityNotFoundError):
        service.preview_category_deletion(uuid.uuid4())


# --- Paginação, ordenação e pesquisa ---

def _seed(uow: FakeUnitOfWork):
    for name, type_ in (("Lazer", EXPENSE), ("Salário", INCOME), ("Alimentação", EXPENSE)):
        uow.categories.save(Category(name=name, type=type_))

def test_list_categories_page_defaults_to_name_ascending(service: CategoryService, uow: FakeUnitOfWork):
    _seed(uow)

    page = service.list_categories_page()

    assert [c.name for c in page.items] == ["Alimentação", "Lazer", "Salário"]
    assert (page.page, page.total, page.sort_by, page.sort_dir) == (1, 3, "name", "asc")

def test_list_categories_page_sorts_by_type_descending(service: CategoryService, uow: FakeUnitOfWork):
    _seed(uow)

    page = service.list_categories_page(sort_by="type", sort_dir="desc")

    assert [c.name for c in page.items] == ["Salário", "Alimentação", "Lazer"]
    assert (page.sort_by, page.sort_dir) == ("type", "desc")

def test_list_categories_page_falls_back_to_name_for_an_unsortable_field(service: CategoryService, uow: FakeUnitOfWork):
    _seed(uow)

    assert service.list_categories_page(sort_by="id").sort_by == "name"

def test_list_categories_page_searches_by_name_or_type_label(service: CategoryService, uow: FakeUnitOfWork):
    _seed(uow)

    by_name = service.list_categories_page(search="  aliment ")
    by_type = service.list_categories_page(search="receita")

    assert [c.name for c in by_name.items] == ["Alimentação"]
    assert by_name.search == "aliment"
    assert [c.name for c in by_type.items] == ["Salário"]
    assert by_type.total == 1

def test_list_categories_page_beyond_the_last_page_returns_the_last(service: CategoryService, uow: FakeUnitOfWork):
    _seed(uow)

    page = service.list_categories_page(page=9, page_size=10)

    assert page.page == 1
    assert len(page.items) == 3
