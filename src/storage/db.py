import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cadastrai.db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    razao_social = Column(String, index=True)
    documento = Column(String, index=True)
    email = Column(String)
    telefone = Column(String)
    endereco = Column(Text)
    departamento = Column(String) # Novo campo
    data_cadastro = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String) # 'admin' or 'user'
    departamento = Column(String)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, nullable=True)
    action = Column(String) # 'TENTATIVA_INJECAO', 'FORA_ESCOPO', etc
    details = Column(Text)

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Seed users if none exist
    if db.query(User).count() == 0:
        admin = User(username="admin", password="admin", role="admin", departamento="Todos")
        vendedor = User(username="vendedor", password="vendedor", role="user", departamento="Vendas")
        renan = User(username="renan_moraes", password="Rmoraes4!", role="admin", departamento="Todos")
        db.add_all([admin, vendedor, renan])
        db.commit()
    
    db.close()

def insert_cliente(dados: dict, departamento: str = "Vendas") -> int:
    """
    Insere um cliente usando SQLAlchemy.
    """
    db = SessionLocal()
    try:
        cliente = Cliente(
            razao_social=dados.get("razao_social", ""),
            documento=dados.get("documento", ""),
            email=dados.get("email", ""),
            telefone=dados.get("telefone", ""),
            endereco=dados.get("endereco", ""),
            departamento=dados.get("departamento", departamento)
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        return cliente.id
    finally:
        db.close()

def log_audit(user_id: int | None, action: str, details: str):
    db = SessionLocal()
    try:
        log = AuditLog(user_id=user_id, action=action, details=details)
        db.add(log)
        db.commit()
    finally:
        db.close()

def execute_read_only_query(query: str) -> list[dict]:
    """
    Executa uma query no banco. Aplica verificações básicas de segurança.
    """
    query_upper = query.upper().strip()
    if any(forbidden in query_upper for forbidden in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"]):
        raise ValueError("Tentativa de injeção ou comando não-SELECT bloqueada pela camada de dados.")
    
    db = SessionLocal()
    try:
        result = db.execute(text(query))
        rows = result.fetchall()
        keys = result.keys()
        
        return [dict(zip(keys, row)) for row in rows]
    except Exception as e:
        raise ValueError(f"Erro na execução da query: {str(e)}")
    finally:
        db.close()
