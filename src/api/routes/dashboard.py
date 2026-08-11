from fastapi import APIRouter, Depends
from sqlalchemy import func
from src.storage.db import SessionLocal, Cliente
from src.api.routes.chat import get_current_user_context

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/kpis")
def get_dashboard_kpis(user: dict = Depends(get_current_user_context), db=Depends(get_db)):
    role = user.get("role")
    dept = user.get("departamento")
    
    # Base query for all KPIs
    base_query = db.query(Cliente)
    
    # Apply department filter if not admin
    if role != "admin" and dept:
        base_query = base_query.filter(Cliente.departamento == dept)
        
    # KPI 1: Total Clients
    total_clients = base_query.count()
    
    # KPI 2: Clients by Department
    clients_by_dept = []
    if role == "admin":
        dept_counts = db.query(
            Cliente.departamento, 
            func.count(Cliente.id).label('count')
        ).group_by(Cliente.departamento).all()
        clients_by_dept = [{"departamento": d or "Sem Departamento", "count": c} for d, c in dept_counts]
    else:
        clients_by_dept = [{"departamento": dept, "count": total_clients}]
        
    # KPI 3: Recent Clients (last 5)
    recent_clients_query = base_query.order_by(Cliente.data_cadastro.desc()).limit(5).all()
    recent_clients = [{
        "id": c.id,
        "razao_social": c.razao_social,
        "departamento": c.departamento,
        "data_cadastro": c.data_cadastro.isoformat() if c.data_cadastro else None
    } for c in recent_clients_query]
    
    return {
        "total_clients": total_clients,
        "clients_by_department": clients_by_dept,
        "recent_clients": recent_clients
    }
