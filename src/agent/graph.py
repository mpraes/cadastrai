import json
import re
from typing import TypedDict, Literal, Annotated
import operator
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from src.models.llm import get_llm
from src.prompts.cadastrai_prompts import ROUTER_PROMPT, CADASTRO_PROMPT, TEXT_TO_SQL_PROMPT
from src.storage.db import insert_cliente, execute_read_only_query, log_audit
from src.utils.logger import logger

class AgentState(TypedDict):
    input: str
    chat_history: Annotated[list, operator.add]
    route: str
    response: str
    sql_query: str
    sql_results: list
    cliente_data: dict
    user_context: dict
    pending_confirmation: dict
    
llm = get_llm()

# --- NÓS DO GRAFO ---

def router_node(state: AgentState) -> AgentState:
    history = state.get("chat_history", [])
    # format history for the prompt if needed, or just include it
    messages = [("system", ROUTER_PROMPT)] + history + [("user", state["input"])]
    res = llm.invoke(messages)
    route = res.content.strip().upper()
    logger.info("router_decision", input=state["input"], route=route)
    return {"route": route, "chat_history": [("user", state["input"])]}

def cadastro_node(state: AgentState) -> AgentState:
    history = state.get("chat_history", [])[:-1] # exclude the current input we just added in router
    messages = [("system", CADASTRO_PROMPT)] + history + [("user", state["input"])]
    res = llm.invoke(messages)
    return {"response": res.content}

def execute_db_insert_node(state: AgentState) -> AgentState:
    response = state.get("response", "")
    json_match = re.search(r'```json(.*?)```', response, re.DOTALL)
    if json_match:
        try:
            dados = json.loads(json_match.group(1).strip())
            logger.info("cadastro_json_extracted", dados=dados)
            msg = "Por favor, revise e confirme os dados no formulário abaixo."
            return {
                "response": msg,
                "pending_confirmation": dados,
                "chat_history": [("assistant", msg)]
            }
        except Exception as e:
            logger.error("cadastro_json_error", error=str(e), json_string=json_match.group(1))
            msg = f"❌ Erro ao processar dados: {str(e)}"
            return {"response": msg, "chat_history": [("assistant", msg)]}
    
    return {"response": response, "chat_history": [("assistant", response)]}

def text_to_sql_node(state: AgentState) -> AgentState:
    user = state.get("user_context", {})
    role = user.get("role", "user")
    dept = user.get("departamento", "")
    
    system_prompt = TEXT_TO_SQL_PROMPT
    if role != "admin" and dept:
        system_prompt += f"\n\nATENÇÃO: O usuário tem acesso restrito. VOCÊ DEVE ADICIONAR a cláusula `WHERE departamento = '{dept}'` na query."
        
    history = state.get("chat_history", [])[:-1]
    messages = [("system", system_prompt)] + history + [("user", state["input"])]
    res = llm.invoke(messages)
    
    query = res.content.strip()
    if query.startswith("```sql"):
        query = query[6:]
    if query.startswith("```"):
        query = query[3:]
    if query.endswith("```"):
        query = query[:-3]
    
    clean_query = query.strip()
    logger.info("sql_generated", query=clean_query, dept=dept, role=role)
    return {"sql_query": clean_query}

def execute_sql_node(state: AgentState) -> AgentState:
    query = state.get("sql_query", "")
    try:
        results = execute_read_only_query(query)
        logger.info("sql_executed_success", result_count=len(results))
        return {"sql_results": results}
    except Exception as e:
        logger.error("sql_execution_error", error=str(e), query=query)
        msg = f"❌ Erro ao executar a consulta: {str(e)}"
        return {"response": msg, "chat_history": [("assistant", msg)]}

def format_response_node(state: AgentState) -> AgentState:
    if state.get("response") and state["response"].startswith("❌"):
        return state
    
    results = state.get("sql_results", [])
    
    if not results:
        msg = "Nenhum resultado encontrado."
        return {"response": msg, "chat_history": [("assistant", msg)]}
    
    prompt = f"O usuário perguntou: '{state['input']}'. Os dados encontrados no banco são:\n{json.dumps(results, indent=2, ensure_ascii=False)}\nResponda ao usuário de forma amigável e concisa com um pequeno resumo. O frontend exibirá os detalhes em uma tabela."
    res = llm.invoke([("user", prompt)])
    
    return {"response": res.content, "chat_history": [("assistant", res.content)]}

def blocked_node(state: AgentState) -> AgentState:
    route = state.get("route", "FORA_ESCOPO")
    user = state.get("user_context", {})
    user_id = user.get("id")
    
    log_audit(
        user_id=user_id,
        action=route,
        details=f"Input: {state.get('input')}"
    )
    
    logger.warning("request_blocked", user_id=user_id, route=route, input=state.get('input'))
    
    msg = "⚠️ Operação negada por razões de segurança ou fora do escopo do Cadastrai."
    return {"response": msg, "chat_history": [("assistant", msg)]}

# --- ROTEAMENTO CONDICIONAL ---

def route_decision(state: AgentState) -> Literal["cadastro", "sql", "blocked"]:
    route = state.get("route")
    if route == "CADASTRO":
        return "cadastro"
    elif route == "CONSULTA":
        return "sql"
    else:
        return "blocked"

# --- MONTAGEM DO GRAFO ---

workflow = StateGraph(AgentState)

workflow.add_node("router", router_node)
workflow.add_node("cadastro", cadastro_node)
workflow.add_node("execute_db_insert", execute_db_insert_node)
workflow.add_node("sql", text_to_sql_node)
workflow.add_node("execute_sql", execute_sql_node)
workflow.add_node("format_response", format_response_node)
workflow.add_node("blocked", blocked_node)

workflow.add_edge(START, "router")

workflow.add_conditional_edges(
    "router",
    route_decision,
    {
        "cadastro": "cadastro",
        "sql": "sql",
        "blocked": "blocked"
    }
)

workflow.add_edge("cadastro", "execute_db_insert")
workflow.add_edge("execute_db_insert", END)

workflow.add_edge("sql", "execute_sql")
workflow.add_edge("execute_sql", "format_response")
workflow.add_edge("format_response", END)

workflow.add_edge("blocked", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)