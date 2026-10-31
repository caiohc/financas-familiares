from application.dtos.shared_dtos import DEFAULT_PAGE_SIZE, PageDTO


def page_of(
    items,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    total: int | None = None,
    sort_by: str = "name",
    sort_dir: str = "asc",
    search: str = "",
) -> PageDTO:
    """Monta a página que o serviço devolveria ao controlador (para os doubles dos testes de rota)."""
    items = list(items)
    return PageDTO(
        items=items, page=page, page_size=page_size,
        total=len(items) if total is None else total,
        sort_by=sort_by, sort_dir=sort_dir, search=search,
    )
