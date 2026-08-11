import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from src.storage.db import SessionLocal, User
from src.utils.logger import logger

SECRET_KEY = "cadastrai-secret-super-safe"
ALGORITHM = "HS256"

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserInfo(BaseModel):
    id: int
    username: str
    role: str
    departamento: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    # Simple simulated auth: password is the same as username for demo
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        logger.warning("login_failed_user_not_found", username=req.username)
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    
    # Generate token
    access_token = create_access_token(
        data={"sub": user.username, "id": user.id, "role": user.role, "departamento": user.departamento}
    )
    logger.info("login_success", username=req.username, role=user.role, dept=user.departamento)
    return {"access_token": access_token}

@router.get("/me", response_model=UserInfo)
def get_me(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
        
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
        
    return UserInfo(
        id=user.id,
        username=user.username,
        role=user.role,
        departamento=user.departamento
    )
