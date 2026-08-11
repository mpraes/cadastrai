import os
import sqlite3
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def test_env_file_exists():
    assert os.path.exists(".env")

def test_llm_module_import():
    from src.models.llm import get_llm
    assert callable(get_llm)

def test_db_initialization():
    """Testa se o banco de dados SQLAlchemy e as tabelas são criados corretamente."""
    from src.storage.db import init_db, engine, User, Cliente, AuditLog, SessionLocal
    
    # Initialize the DB (will create tables in the configured engine, usually local sqlite cadastrai.db)
    init_db()
    
    # Verify tables exist using raw SQL or SQLAlchemy inspector
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    assert 'clientes' in tables
    assert 'users' in tables
    assert 'audit_logs' in tables
    
    # Verify seeded users
    db = SessionLocal()
    users = db.query(User).all()
    assert len(users) >= 2
    usernames = [u.username for u in users]
    assert "admin" in usernames
    assert "vendedor" in usernames
    db.close()

def test_graph_import():
    """Testa se o grafo compila sem erros."""
    from src.agent.graph import app
    assert app is not None

def test_logger_initialization():
    """Testa se o logger foi configurado sem erros estruturais."""
    from src.utils.logger import logger
    # logger should be a bound logger from structlog
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
