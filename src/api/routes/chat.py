from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, field_validator
import jwt
from typing import Optional, Any
import re

from src.agent.graph import app as agent_app
from src.api.routes.auth import SECRET_KEY, ALGORITHM
from src.storage.db import insert_cliente
from src.utils.logger import logger

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    route: str | None = None
    structured_results: list[dict] | None = None
    pending_confirmation: dict | None = None

class ClienteDados(BaseModel):
    razao_social: str
    documento: str
    email: str
    telefone: str
    endereco: str
    departamento: str | None = None

    @field_validator('documento')
    @classmethod
    def validar_documento(cls, v: str):
        v_limpo = re.sub(r'[^0-9]', '', v)
        if len(v_limpo) not in (11, 14):
            raise ValueError("O documento deve ter 11 (CPF) ou 14 (CNPJ) dígitos.")
        return v
    
    @field_validator('email')
    @classmethod
    def validar_email(cls, v: str):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError("O formato do e-mail é inválido.")
        return v

    @field_validator('endereco')
    @classmethod
    def validar_endereco(cls, v: str):
        # Corrige erros comuns de digitação como os dois hifens do CEP que você comentou
        return re.sub(r'([^\w\s])\1+', r'\1', v)

class ConfirmRequest(BaseModel):
    dados: ClienteDados

def get_current_user_context(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        # Fallback to a default context if no token (for testing without auth)
        return {"id": None, "username": "guest", "role": "admin", "departamento": "Todos"}
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "id": payload.get("id"),
            "username": payload.get("sub"),
            "role": payload.get("role"),
            "departamento": payload.get("departamento")
        }
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, user: dict = Depends(get_current_user_context)):
    logger.info("chat_request_received", user_id=user.get("id"), username=user.get("username"), input_length=len(request.message))
    
    # Adicionar o contexto do usuário ao estado do LangGraph
    state = {
        "input": request.message,
        "user_context": user
    }
    
    # Define o thread_id com base no username para o MemorySaver do LangGraph
    thread_id = user.get("username") or "default_thread"
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        result = await agent_app.ainvoke(state, config)
        
        logger.info("chat_request_success", route=result.get("route"))
        
        # Extrair campos estruturados do estado resultante
        return ChatResponse(
            response=result.get("response", "Desculpe, ocorreu um erro."),
            route=result.get("route"),
            structured_results=result.get("sql_results"),
            pending_confirmation=result.get("pending_confirmation")
        )
    except Exception as e:
        logger.error("chat_request_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno do agente")

@router.post("/confirm_registration")
def confirm_registration(request: ConfirmRequest, user: dict = Depends(get_current_user_context)):
    """ Endpoint para confirmar o cadastro após validação do humano. """
    logger.info("confirm_registration_received", user_id=user.get("id"), username=user.get("username"))
    try:
        # Usa o departamento do payload ou do usuário se necessário.
        # Aqui, vamos forçar o departamento do usuário, a menos que ele seja Admin
        dept = user["departamento"] if user["role"] != "admin" else request.dados.departamento or "Geral"
        
        insert_cliente(request.dados.model_dump(), departamento=dept)
        logger.info("confirm_registration_success", dept=dept)
        return {"status": "success", "message": "Cliente cadastrado com sucesso!"}
    except Exception as e:
        logger.error("confirm_registration_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
