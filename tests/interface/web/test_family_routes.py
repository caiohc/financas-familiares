def test_create_family_form(client):
    # Envio tradicional de formulário HTML (application/x-www-form-urlencoded)
    response = client.post("/families/new", data={
        "name": "Família Souza"
    })
    
    # Em aplicações Web tradicionais, um POST bem sucedido gera um Redirect (302)
    # para evitar o reenvio duplo do formulário (Post/Redirect/Get pattern)
    assert response.status_code == 302
    assert response.headers["Location"] == "/families"

def test_list_families_page(client, family_service):
    # Populamos o banco diretamente pelo serviço (isolamento de teste), 
    # sem depender da rota de POST funcionar.
    from application.dtos.family_dtos import CreateFamilyDTO
    family_service.create_family(CreateFamilyDTO(name="Família Silva"))
    
    # Um GET clássico que, no futuro, renderizará um template HTML
    response = client.get("/families")
    
    assert response.status_code == 200
    # Verificamos se o nome da família aparece no corpo da resposta
    html_content = response.get_data(as_text=True)
    assert "Família Silva" in html_content

