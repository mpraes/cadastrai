# CadastrAÍ - SAP Fiori Style Agent 🤖

O **CadastrAÍ** é um agente inteligente focado na gestão de dados cadastrais corporativos. Ele utiliza **LangGraph** para criar um fluxo de trabalho estruturado e seguro, garantindo que as intenções do usuário sejam roteadas corretamente entre **Cadastro** e **Consulta**, impedindo ataques de injeção ou solicitações fora de escopo (Guardião CadastrAÍ).

A interface e a organização da API seguem padrões inspirados no SAP Fiori (estilo SAP Joule), focando em simplicidade, segurança e robustez para ambientes corporativos.

---

## ✨ Funcionalidades

- 🛡️ **Guardião de Segurança**: Rotemaneto inteligente e bloqueio automático de injeções (`DROP`, `DELETE`) e solicitações fora de escopo.
- 🔐 **Autenticação e Permissões (JWT)**: Login integrado simulando isolamento de departamentos (ex: Administrador vs Vendedor). As consultas SQL são automaticamente filtradas com base no perfil do usuário logado.
- 📊 **Smart Tables (Fiori UI)**: Em vez de texto cru, o chat renderiza tabelas dinâmicas HTML para as consultas de banco de dados.
- 🧑‍💻 **Human-in-the-loop (Cadastro)**: A inserção não ocorre de forma automatizada pelo LLM. O agente extrai os dados e os exibe em um Card de Confirmação na interface para que o usuário revise e confirme antes da gravação (evitando alucinações).
- 🗄️ **Conector Multi-Banco (SQLAlchemy)**: Preparado para usar SQLite (desenvolvimento) ou bancos robustos como Postgres/SQLServer apenas alterando a variável `DATABASE_URL`.
- 📝 **Logs Estruturados e Auditoria**: Utiliza `structlog` para saídas JSON estruturadas no `stderr`. Tentativas de injeção são gravadas automaticamente em uma tabela `AuditLog` no banco.

---

## 🏗️ Estrutura Atual do Projeto

O projeto está modularizado para separar responsabilidades de roteamento (LLM), API, e persistência de dados.

```
cadastrai/
├── src/
│   ├── agent/               # Lógica do LangGraph (fluxo de decisão e execução)
│   │   └── graph.py         # Grafo principal com os nós (router, cadastro, sql, execute_db, blocked)
│   ├── api/                 # Rotas da API REST (FastAPI)
│   │   ├── routes/          # Endpoints separados (chat.py, auth.py)
│   │   └── main.py          # Ponto de entrada do backend Web
│   ├── models/              # Definições de modelos e LLMs
│   │   └── llm.py           # Configuração do modelo fundacional (ex: Gemini)
│   ├── prompts/             # Engenharia de Prompts (Segurança e Instruções)
│   │   └── cadastrai_prompts.py # Prompts do Guardião, Cadastro e Text-to-SQL
│   ├── storage/             # Camada de Banco de Dados (SQLAlchemy)
│   │   └── db.py            # Definição dos Models (User, Cliente, AuditLog) e funções utilitárias
│   ├── utils/               # Utilitários e helpers auxiliares
│   │   └── logger.py        # Configuração do structlog (JSON logging)
│   └── web/                 # Camada de interface web / frontend estático
│       ├── static/          # CSS Fiori (style.css), JS App (app.js)
│       └── templates/       # HTML (index.html)
├── tests/                   # Suíte de Testes (Pytest)
│   ├── test_smoke.py        # Testes de modelos, banco, logger e grafo
│   └── test_web_smoke.py    # Testes da API (Endpoints de Auth, Chat e Frontend)
├── pyproject.toml           # Configurações do ambiente e dependências (uv)
└── .env                     # Variáveis de ambiente (ex: chaves de API)
```

---

## 🚀 Como Rodar e Usar

Este projeto utiliza o gerenciador de pacotes **`uv`** por sua extrema velocidade.

### 1. Preparando o Ambiente

Instale as dependências usando o `uv`:

```bash
# Sincroniza e instala todas as dependências declaradas no pyproject.toml / uv.lock
uv sync
```

Configure suas variáveis de ambiente:

```bash
# Crie o arquivo .env e adicione suas chaves do LLM e Banco (Opcional)
touch .env
# Adicione: GEMINI_API_KEY="sua_chave_aqui"
# Adicione: DATABASE_URL="sqlite:///cadastrai.db" (Opcional, já é o default)
```

### 2. Rodando a Aplicação (Web/API)

A aplicação pode ser servida via **FastAPI** + **Uvicorn**:

```bash
# Inicie o servidor em modo de desenvolvimento
uv run uvicorn src.api.main:app --reload --port 8000
```

- Acesse a interface web no navegador: `http://localhost:8000/`
  - Na tela inicial, escolha entre *Admin* ou *Vendedor* para testar a aplicação simulando o contexto de departamentos (RLS implícito).
- Acesse a documentação Swagger da API: `http://localhost:8000/docs`

### 3. Rodando Testes Automáticos

A suíte de testes cobre a integridade do banco de dados (SQLAlchemy), compilação do LangGraph e integridade da API FastAPI (Endpoints, Auth, e Mock do LangGraph):

```bash
uv run pytest tests/
```
