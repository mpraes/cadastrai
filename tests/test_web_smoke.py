from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pytest
import jwt
from datetime import datetime, timedelta

from src.api.main import app
from src.api.routes.auth import SECRET_KEY, ALGORITHM

client = TestClient(app)

def test_web_index_page():
    """Testa se a página inicial em HTML carrega corretamente (Smoke Test do Template)"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "CadastrAÍ" in response.text
    assert "id=\"login-modal\"" in response.text

def test_auth_login_endpoint():
    """Testa o fluxo de login simulado do smoke test"""
    # Requires DB seeded by init_db
    from src.storage.db import init_db
    init_db()
    
    payload = {"username": "admin", "password": "any"}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

def test_auth_me_endpoint():
    # Gerar um token fake válido para o teste
    token = jwt.encode(
        {"sub": "admin", "id": 1, "role": "admin", "departamento": "Todos", "exp": datetime.utcnow() + timedelta(hours=1)},
        SECRET_KEY, 
        algorithm=ALGORITHM
    )
    
    response = client.get(f"/api/auth/me?token={token}")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"

@patch("src.api.routes.chat.agent_app.ainvoke")
@pytest.mark.asyncio
async def test_api_chat_endpoint(mock_ainvoke):
    """Testa se o endpoint da API /api/chat passa o contexto de auth e recebe payload correto"""
    
    mock_ainvoke.return_value = {
        "response": "Por favor, revise os dados.",
        "route": "CADASTRO",
        "pending_confirmation": {"nome": "Teste"}
    }

    # Generate a dummy token to test the Depends(get_current_user_context)
    token = jwt.encode({"sub": "vendedor", "id": 2, "role": "user", "departamento": "Vendas"}, SECRET_KEY, algorithm=ALGORITHM)
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"message": "Cadastrar Teste"}
    
    response = client.post("/api/chat", json=payload, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Por favor, revise os dados."
    assert data["route"] == "CADASTRO"
    assert "nome" in data["pending_confirmation"]
    
    # Verifica se o agente foi invocado com o estado esperado incluindo contexto de usuário
    mock_ainvoke.assert_called_once()
    called_arg = mock_ainvoke.call_args[0][0]
    assert called_arg["input"] == "Cadastrar Teste"
    assert called_arg["user_context"]["username"] == "vendedor"

@patch("src.api.routes.chat.insert_cliente")
def test_api_confirm_registration(mock_insert_cliente):
    """Testa o endpoint de confirmação do human-in-the-loop"""
    mock_insert_cliente.return_value = 1
    
    token = jwt.encode({"sub": "admin", "id": 1, "role": "admin", "departamento": "Todos"}, SECRET_KEY, algorithm=ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "dados": {
            "razao_social": "Empresa Teste",
            "documento": "123",
            "departamento": "TI"
        }
    }
    
    response = client.post("/api/confirm_registration", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    mock_insert_cliente.assert_called_once_with(payload["dados"], departamento="TI")
