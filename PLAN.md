# World Cup AI Intelligence Platform — Project Plan

> **Validated: 2026-06-10** — All SDK APIs, package names, and deployment patterns verified against primary sources (PyPI, GitHub raw samples, Microsoft Learn docs). No blockers identified.

## Executive Summary

An AI-powered World Cup 2026 Intelligence Platform delivering pre-match briefings, explainable prediction cards, audit-grounded fact checks, and media packs for hardcore fans and media creators. A collaborative multi-agent pipeline — Scout → Fact-Checker → Tactician → Scribe — runs as a single Microsoft Foundry Hosted Agent using the **Agent Framework** `WorkflowBuilder` pattern, backed by a dedicated MCP tool server and a Streamlit analytics dashboard.

---

## System Architecture

```mermaid
graph TB
    subgraph CONSUMER["Consumers"]
        UI["🖥️ Streamlit Dashboard\n(port 8501)"]
        EMAIL["📧 HTML Email Preview\n(Jinja2 rendered file)"]
        API_CLIENT["🔌 API Client\nazd ai agent invoke"]
    end

    subgraph HOSTED_AGENT["Azure AI Foundry — Hosted Agent (port 8088)"]
        direction TB
        RHS["ResponsesHostServer\n(Responses Protocol /responses)"]

        subgraph WORKFLOW["WorkflowBuilder Pipeline"]
            direction LR
            SCOUT["🏃 Scout Agent\nAgentExecutor\n─────────────\nMCP tools:\n• get_schedule\n• get_historical_trends"]
            FC["🔍 Fact-Checker Agent\nAgentExecutor\n─────────────\n• Toolbox web_search\n  (MCPStreamableHTTPTool)\n• MCP: ground_and_audit_claim"]
            TAC["📊 Tactician Agent\nAgentExecutor\n─────────────\n• Pure reasoning\n  (no external tools)"]
            SCR["✍️ Scribe Agent\nAgentExecutor\n─────────────\nMCP tools:\n• save_prediction_card\n• save_media_pack"]

            SCOUT -->|"fixtures + metrics JSON\ncontext_mode=last_agent"| FC
            FC -->|"verified claims +\ncitations bundle"| TAC
            TAC -->|"prediction card +\nprobabilities + reasoning"| SCR
        end

        RHS --> WORKFLOW
    end

    subgraph MCP_SERVER["MCP Tool Server (FastMCP, port 8000)"]
        direction TB
        MCP["FastMCP HTTP Server\n/mcp endpoint\n(stateless_http=True)"]

        subgraph TOOLS["Registered Tools"]
            T1["get_schedule(date)"]
            T2["get_historical_trends\n(team_id, player_id)"]
            T3["web_discovery_search(query)\n(fallback if Toolbox unavailable)"]
            T4["ground_and_audit_claim\n(claim, citations, status,\nconfidence, entity_mappings)"]
            T5["save_prediction_card\n(match_id, analysis,\nprobabilities, reasoning)"]
            T6["save_media_pack\n(match_id, email_html,\nsocial_threads)"]
            T7["get_prediction_cards(date)"]
        end

        MCP --> TOOLS
    end

    subgraph EXTERNAL["External Services"]
        FOOTBALL["⚽ API-Football v3\nv3.football.api-sports.io\nHeader: x-apisports-key"]
        TOOLBOX["🔍 Foundry Toolbox\n(web_search tool)\nManaged MCP endpoint\nReal-time web + citations"]
        AOI["🤖 Azure OpenAI\nGPT-4o deployment"]
    end

    subgraph STORAGE["Shared Storage"]
        DB[("PostgreSQL\nworldcup database\n────────────────\n📋 fixtures\n🔎 audit_claims\n🃏 prediction_cards\n📦 media_packs")]
    end

    subgraph INFRA["Azure Infrastructure (azd up)"]
        ACA["Azure Container Apps\n3 services, same environment"]
        ACR["Azure Container Registry\n(image build via ACR Tasks)"]
        PG_SVC["Azure Database for PostgreSQL\nFlexible Server"]
        AI["Application Insights\nOpenTelemetry tracing"]
    end

    SCOUT -->|"client.get_mcp_tool()\nHTTP MCP calls"| MCP_SERVER
    FC -->|"client.get_mcp_tool()\nHTTP MCP calls"| MCP_SERVER
    FC -->|"MCPStreamableHTTPTool\n(FOUNDRY_TOOLBOX_ENDPOINT)"| TOOLBOX
    SCR -->|"client.get_mcp_tool()\nHTTP MCP calls"| MCP_SERVER

    MCP_SERVER -->|"REST + x-apisports-key"| FOOTBALL
    MCP_SERVER -->|"SQLAlchemy ORM"| STORAGE

    WORKFLOW -->|"LLM calls via\nFoundryChatClient"| AOI

    UI -->|"SQLAlchemy read-only"| STORAGE
    EMAIL -->|"Jinja2 render\nfrom media_packs"| STORAGE

    API_CLIENT -->|"POST /responses"| HOSTED_AGENT

    HOSTED_AGENT -.->|"deployed as container"| ACA
    MCP_SERVER -.->|"deployed as container"| ACA
    UI -.->|"deployed as container"| ACA
    ACA -.-> ACR
    ACA -.-> AFS
    ACA -.-> AI
```

---

## End-to-End Flow

```mermaid
sequenceDiagram
    actor User as 👤 User / Scheduler
    participant HA as Hosted Agent<br/>(ResponsesHostServer:8088)
    participant Scout as 🏃 Scout Agent
    participant MCP as FastMCP Server :8000
    participant FootballAPI as ⚽ API-Football v3
    participant FC as 🔍 Fact-Checker Agent
    participant Toolbox as 🔍 Foundry Toolbox<br/>(web_search)
    participant PG as 🗃️ PostgreSQL DB
    participant Tac as 📊 Tactician Agent
    participant Scribe as ✍️ Scribe Agent
    participant Dashboard as 🖥️ Streamlit :8501

    User->>HA: POST /responses<br/>"Analyze today's World Cup matches — 2026-06-10"

    rect rgb(230, 244, 255)
        Note over HA,Scout: Stage 1 — Scout Agent (data ingestion)
        HA->>Scout: Invoke with user prompt
        Scout->>MCP: get_schedule("2026-06-10")
        MCP->>FootballAPI: GET /fixtures?date=2026-06-10
        FootballAPI-->>MCP: fixtures JSON (teams, venue, kickoff)
        MCP->>PG: UPSERT fixtures
        MCP-->>Scout: fixtures list
        Scout->>MCP: get_historical_trends(team_id=X)
        MCP->>FootballAPI: GET /teams/statistics?team=X&season=2026
        FootballAPI-->>MCP: team stats JSON
        MCP-->>Scout: rolling metrics, form, rankings
        Scout-->>HA: Structured fixture + metrics context
    end

    rect rgb(230, 255, 230)
        Note over HA,FC: Stage 2 — Fact-Checker Agent (grounding & verification)
        HA->>FC: Invoke with Scout output (context_mode=last_agent)
        FC->>Toolbox: web_search("Brazil injury news World Cup June 2026")
        Toolbox-->>FC: grounded results + inline citations
        FC->>MCP: ground_and_audit_claim(<br/>  claim_text, citations[],<br/>  status="Confirmed", confidence=0.92,<br/>  entity_mappings={wikidata_id, api_id})
        MCP->>PG: INSERT audit_claims
        MCP-->>FC: audit record id
        FC-->>HA: Verified claims bundle<br/>(Confirmed/Reported/Unverified tags)
    end

    rect rgb(255, 248, 220)
        Note over HA,Tac: Stage 3 — Tactician Agent (analysis & forecasting)
        HA->>Tac: Invoke with FC verified output
        Note over Tac: Pure LLM reasoning — no tool calls<br/>Analyzes matchups, form, verified context<br/>Generates probability estimates
        Tac-->>HA: Prediction card JSON:<br/>• prob_home / prob_draw / prob_away<br/>• Key tactical matchups<br/>• Transparent reasoning chain
    end

    rect rgb(255, 235, 235)
        Note over HA,Scribe: Stage 4 — Scribe Agent (content generation)
        HA->>Scribe: Invoke with Tactician prediction card
        Scribe->>MCP: save_prediction_card(<br/>  match_id, probabilities, reasoning)
        MCP->>PG: INSERT prediction_cards
        Note over Scribe: Formats email-ready content<br/>Drafts 5-tweet social thread
        Scribe->>MCP: save_media_pack(<br/>  match_id, email_html, social_threads)
        MCP->>PG: INSERT media_packs
        MCP-->>Scribe: saved OK
        Scribe-->>HA: Final briefing (streamed to user)
    end

    HA-->>User: Streamed Responses protocol reply<br/>(pre-match briefing + prediction summary)

    Note over User,Dashboard: Dashboard reads persisted data at any time
    User->>Dashboard: Open browser → localhost:8501
    Dashboard->>PG: SELECT from fixtures, prediction_cards,<br/>audit_claims, media_packs WHERE date=today
    PG-->>Dashboard: All stored data
    Dashboard-->>User: 4-page interactive dashboard<br/>Schedule / Predictions / Audit Trail / Media Pack
```

---

## Project Structure

```
c:\Repos\AIHackathon\
├── agent/                          # Hosted Agent service (Responses protocol)
│   ├── main.py                     # WorkflowBuilder: Scout→FC→Tactician→Scribe
│   ├── agent.yaml                  # Runtime config (model, protocol, env bindings)
│   ├── agent.manifest.yaml         # azd ai agent init manifest (resources, toolbox)
│   ├── Dockerfile
│   └── requirements.txt
│
├── mcp_server/                     # FastMCP tool server (separate container)
│   ├── server.py                   # FastMCP("WorldCupIntelligence") entry point
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── schedule.py             # get_schedule(date)
│   │   ├── trends.py              # get_historical_trends(team_id, player_id)
│   │   ├── grounding.py            # ground_and_audit_claim(...)
│   │   └── persistence.py          # save_prediction_card / save_media_pack / get_prediction_cards
│   ├── clients/
│   │   ├── __init__.py
│   │   └── football_api.py         # API-Football v3 async httpx client
│   ├── Dockerfile
│   └── requirements.txt
│
├── dashboard/                      # Streamlit analytics dashboard
│   ├── app.py                      # 4-page app: Schedule / Predictions / Audit / Media
│   ├── Dockerfile
│   └── requirements.txt
│
├── shared/
│   ├── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy ORM: fixtures, audit_claims, prediction_cards, media_packs
│   │   └── database.py             # Engine factory + session context manager
│   └── templates/
│       └── email.html.j2           # Jinja2 pre-match email template
│
├── config/
│   ├── __init__.py
│   └── settings.py                 # Pydantic BaseSettings (all env vars)
│
├── tests/
│   ├── test_football_api.py        # Mock httpx responses
│   ├── test_mcp_tools.py           # In-process FastMCP tool tests
│   └── test_workflow.py            # Stub agents, verify pipeline order
│
├── .env.example
├── azure.yaml                      # azd multi-service project file
├── docker-compose.yml              # Local dev (3 services + shared volume)
└── PLAN.md                         # This document
```

---

## Verified SDK API Patterns

### Imports (confirmed from sample source code)

```python
# agent/main.py
from agent_framework import Agent, AgentExecutor, WorkflowBuilder, MCPStreamableHTTPTool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
```

### FoundryChatClient + MCP Tool Registration (from sample 03-mcp)

```python
client = FoundryChatClient(
    project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
    credential=DefaultAzureCredential(),
)

# Register our custom MCP server as a tool source
worldcup_mcp = client.get_mcp_tool(
    name="WorldCup",
    url=os.environ["MCP_SERVER_URL"],  # http://mcp-server:8000/mcp/
    headers={},
    approval_mode="never_require",
)
```

### Foundry Toolbox web_search (from sample 04-foundry-toolbox)

```python
# Toolbox web_search for Fact-Checker agent (managed Bing-equivalent)
toolbox = MCPStreamableHTTPTool(
    name="foundry-toolbox",
    url=os.environ["FOUNDRY_TOOLBOX_ENDPOINT"],
    http_client=http_client,  # httpx.AsyncClient with DefaultAzureCredential
)
```

### WorkflowBuilder Pipeline (from sample 05-workflows)

```python
scout_executor = AgentExecutor(scout_agent, context_mode="last_agent")
fc_executor = AgentExecutor(factchecker_agent, context_mode="last_agent")
tac_executor = AgentExecutor(tactician_agent, context_mode="last_agent")
scribe_executor = AgentExecutor(scribe_agent, context_mode="last_agent")

workflow_agent = (
    WorkflowBuilder(
        start_executor=scout_executor,
        output_executors=[scribe_executor],
    )
    .add_edge(scout_executor, fc_executor)
    .add_edge(fc_executor, tac_executor)
    .add_edge(tac_executor, scribe_executor)
    .build()
    .as_agent()
)

server = ResponsesHostServer(workflow_agent)
server.run()  # Starts on http://localhost:8088
```

---

## Database Schema

```mermaid
erDiagram
    fixtures {
        int      id          PK
        string   match_id    UK
        date     match_date
        string   home_team
        string   away_team
        string   venue
        string   league
        string   status
        json     raw_data
        datetime created_at
    }

    audit_claims {
        int      id               PK
        string   match_id         FK
        string   claim_text
        json     entity_mappings
        string   status_label
        float    confidence_score
        json     citations
        datetime created_at
    }

    prediction_cards {
        int      id          PK
        string   match_id    FK
        float    prob_home
        float    prob_draw
        float    prob_away
        text     analysis
        text     reasoning
        datetime created_at
    }

    media_packs {
        int      id              PK
        string   match_id        FK
        text     email_html
        json     social_threads
        datetime created_at
    }

    fixtures ||--o{ audit_claims     : "verified for"
    fixtures ||--o| prediction_cards : "predicted by"
    fixtures ||--o| media_packs      : "packed into"
```

---

## Implementation Phases

| Phase | Steps | Depends On | Parallelizable |
|---|---|---|---|
| **1. Foundation** | settings, DB models, football API client | — | All 3 steps in parallel |
| **2. MCP Server** | 4 tool modules + FastMCP server entry + Dockerfile | Phase 1 | Tool modules in parallel; server wiring last |
| **3. Hosted Agent** | 4 agent defs + WorkflowBuilder + agent.yaml + Dockerfile | Phase 2 | Sequential (pipeline order) |
| **4. Dashboard + Email** | Streamlit 4 pages + Jinja2 template + Dockerfile | Phase 1 | Fully parallel with Phase 3 |
| **5. Infrastructure** | docker-compose + azure.yaml + .env.example | All | — |

### Phase 1 — Foundation

- **`config/settings.py`** — Pydantic `BaseSettings` loading all secrets from env vars
- **`shared/db/models.py`** — SQLAlchemy ORM tables: `fixtures`, `audit_claims`, `prediction_cards`, `media_packs`
- **`shared/db/database.py`** — engine factory with `pool_pre_ping=True`, session context manager, `create_all()`
- **`mcp_server/clients/football_api.py`** — async `httpx` client; auth via `x-apisports-key` header; respects `x-ratelimit-requests-remaining`; methods: `get_fixtures`, `get_standings`, `get_player_stats`, `get_team_stats`

### Phase 2 — MCP Server

- **`mcp_server/tools/schedule.py`** — `get_schedule(date: str)`: calls football API → upserts `fixtures` table → returns fixture list JSON
- **`mcp_server/tools/trends.py`** — `get_historical_trends(team_id, player_id)`: fetches team + player stats → returns rolling metrics dict
- **`mcp_server/tools/grounding.py`** — `ground_and_audit_claim(claim_text, citations, status_label, confidence_score, entity_mappings)`: validates citation schema (url, title, publisher, publish_time, quote_snippet) → persists `audit_claims` → returns record id
- **`mcp_server/tools/persistence.py`** — `save_prediction_card`, `save_media_pack`, `get_prediction_cards(date)`: CRUD for `prediction_cards` and `media_packs`
- **`mcp_server/server.py`** — `FastMCP("WorldCupIntelligence", stateless_http=True)`, all tools registered, DB + football client lifespan context, port `8000`, path `/mcp`

### Phase 3 — Hosted Agent

Reference: [05-workflows](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/agent-framework/responses/05-workflows) + [03-mcp](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/agent-framework/responses/03-mcp) + [04-foundry-toolbox](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/agent-framework/responses/04-foundry-toolbox)

- **`agent/main.py`**:
  1. Create `FoundryChatClient` with `project_endpoint`, `model`, `credential=DefaultAzureCredential()`
  2. Register custom MCP server via `client.get_mcp_tool(name="WorldCup", url=MCP_SERVER_URL, ...)`
  3. Register Foundry Toolbox via `MCPStreamableHTTPTool(name="foundry-toolbox", url=FOUNDRY_TOOLBOX_ENDPOINT, ...)`
  4. Define 4 `Agent` instances with tailored system prompts and tool subsets:
     - **Scout**: tools=`[worldcup_mcp]` — system prompt restricts to `get_schedule`, `get_historical_trends`
     - **Fact-Checker**: tools=`[worldcup_mcp, toolbox]` — system prompt restricts to `ground_and_audit_claim` + `web_search`
     - **Tactician**: tools=`[]` — pure LLM reasoning from context
     - **Scribe**: tools=`[worldcup_mcp]` — system prompt restricts to `save_prediction_card`, `save_media_pack`
  5. Wrap each in `AgentExecutor(context_mode="last_agent")`
  6. `WorkflowBuilder` chains them with `add_edge()`, `output_executors=[scribe_executor]`
  7. `.build().as_agent()` → `ResponsesHostServer(workflow_agent).run()`
- **`agent/agent.yaml`** — agent name, model deployment, protocol `responses`, env var bindings
- **`agent/agent.manifest.yaml`** — `azd ai agent init -m` compatible manifest including:
  ```yaml
  resources:
    - kind: toolbox
      name: worldcup-tools
      tools:
        - type: web_search
  ```

### Phase 4 — Dashboard + Email

- **`dashboard/app.py`** — Streamlit 4-page app reading PostgreSQL directly (read-only):
  - **Schedule**: today's fixtures from `fixtures` table
  - **Predictions**: expandable cards (probabilities, reasoning) from `prediction_cards`
  - **Audit Trail**: `audit_claims` table with Confirmed/Reported/Unverified badges, confidence score, citation expander
  - **Media Pack**: rendered email HTML preview + copy-to-clipboard social threads from `media_packs`
- **`shared/templates/email.html.j2`** — Jinja2 template: match header, prediction summary, key stats, disclaimer, citation footer

### Phase 5 — Infrastructure

- **`docker-compose.yml`** — 4 services: `postgres` (5432), `mcp-server` (8000), `agent` (8088), `dashboard` (8501)
- **`azure.yaml`** — `azd` project file declaring all 3 services as Azure Container Apps in same environment
- **`.env.example`** — all required env vars documented with descriptions

---

## Environment Variables

| Variable | Used By | Description |
|---|---|---|
| `FOUNDRY_PROJECT_ENDPOINT` | agent | Azure AI Foundry project endpoint URL |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | agent | GPT-4o model deployment name |
| `FOUNDRY_TOOLBOX_ENDPOINT` | agent | Foundry Toolbox MCP endpoint (provisioned by `azd provision`) |
| `MCP_SERVER_URL` | agent | Custom MCP server (`http://mcp-server:8000/mcp/` in Compose) |
| `FOOTBALL_API_KEY` | mcp_server | API-Football v3 key (`x-apisports-key` header) |
| `DATABASE_URL` | mcp_server, dashboard | PostgreSQL connection string (`postgresql://postgres:postgres@postgres:5432/worldcup`) |

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Multi-agent pattern | `WorkflowBuilder` in-process pipeline (single hosted container) | Simpler deployment; single container; no inter-service auth overhead; matches sample 05 |
| MCP tool server | Separate container (FastMCP, port 8000) | Preserves protocol boundary; independently testable; matches sample 03 pattern |
| Web search grounding | Foundry Toolbox `web_search` via `MCPStreamableHTTPTool` | Platform-managed citations; no manual Bing resource; declared in manifest |
| Tool scoping per agent | System prompt enforcement | `client.get_mcp_tool()` gives access to all MCP server tools; restrict via instruction ("only use X, Y tools") |
| Agent context passing | `context_mode="last_agent"` | Prevents context bloat; each agent only sees prior output; keeps token usage low |
| Storage | PostgreSQL (Docker container locally, Azure Database for PostgreSQL Flexible Server on Azure) | ACID-compliant; concurrent access; no file-locking issues; production-grade |
| Email delivery | Jinja2 HTML render → `media_packs.email_html` field | No SMTP infrastructure required; preview in Streamlit |
| Deployment | `azd up` (single command) | Auto-provisions ACR, Container Apps, Foundry Toolbox, App Insights |

---

## Azure Deployment Architecture

```mermaid
graph LR
    subgraph ACA_ENV["Azure Container Apps Environment"]
        A1["agent\n(1 replica max)\nport 8088\nIngress: external"]
        A2["mcp-server\n(1 replica max)\nport 8000\nIngress: internal"]
        A3["dashboard\n(1 replica max)\nport 8501\nIngress: external"]
    end

    subgraph STORAGE["Shared Storage"]
        PG_AZ["Azure Database for PostgreSQL\nFlexible Server\n'worldcup' database"]
    end

    subgraph MANAGED["Azure Managed Services"]
        FOUNDRY["AI Foundry Project\n+ GPT-4o deployment"]
        TOOLBOX["Foundry Toolbox\n(web_search)"]
        ACR2["Azure Container Registry"]
        APPI["Application Insights"]
    end

    A1 -->|"internal URL"| A2
    A3 -->|"reads from PostgreSQL"| PG_AZ
    A2 -->|"writes to PostgreSQL"| PG_AZ
    A1 --> FOUNDRY
    A1 --> TOOLBOX
    ACA_ENV --> ACR2
    ACA_ENV --> APPI
```

**Key constraints for Azure deployment:**
- MCP server ingress: **internal only** (not exposed to internet)
- Agent + Dashboard ingress: **external** (public-facing)
- PostgreSQL Flexible Server accessible from Container Apps via private networking
- Agent container accesses data only through MCP tools

---

## Data Source Strategy

| Source | Primary Use | Fallback if Unavailable |
|---|---|---|
| API-Football v3 (`league_id=1, season=2026`) | Fixtures, standings, player/team stats | Pre-seeded JSON fixtures file in `mcp_server/data/fixtures_seed.json` |
| Foundry Toolbox `web_search` | Breaking news, injuries, press conferences | `web_discovery_search` tool in our MCP server using `httpx` + Bing Web Search API directly |
| Azure OpenAI GPT-4o | All LLM reasoning across 4 agents | Azure OpenAI GPT-4o-mini (lower cost, acceptable for hackathon) |

**API-Football World Cup 2026 note:** The tournament runs June 11 – July 19, 2026. Fixture data should be available on API-Football by tournament start. If not available during development, use `mcp_server/data/fixtures_seed.json` with manually curated group stage fixtures for testing.

---

## Verification Checklist

| # | Test | Command | Pass Criteria |
|---|---|---|---|
| 1 | MCP server starts | `cd mcp_server && python server.py` | Listening on `http://localhost:8000/mcp` |
| 2 | MCP tools respond | `curl -X POST http://localhost:8000/mcp -d '{"method":"tools/list"}'` | Returns 7 tool definitions |
| 3 | Football API integration | `pytest tests/test_football_api.py` | Mock responses parsed correctly |
| 4 | Agent starts locally | `cd agent && azd ai agent run` | Host on `http://localhost:8088` |
| 5 | Agent invocation | `azd ai agent invoke --local "Analyze World Cup matches for 2026-06-11"` | Streamed response with prediction card |
| 6 | PostgreSQL populated | `psql -h localhost -U postgres -d worldcup -c "SELECT count(*) FROM prediction_cards"` | ≥ 1 row after agent run |
| 7 | Dashboard renders | `cd dashboard && streamlit run app.py` | All 4 pages load at `localhost:8501` |
| 8 | Docker Compose E2E | `docker compose up` | All 4 services healthy; dashboard shows data |
| 9 | Azure deploy | `azd up` | 3 Container Apps running; `azd ai agent invoke` returns response |
| 10 | Agent Inspector | VS Code → Foundry Toolkit → Open Agent Inspector | Multi-turn conversation works |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| API-Football lacks WC2026 data before tournament starts | No live fixture data | Pre-seeded JSON fallback (`fixtures_seed.json`); switch to live API on June 11 |
| `agent-framework-foundry-hosting` is alpha (1.0.0a) | Breaking API changes possible | Pin exact version in `requirements.txt`; keep implementation close to official samples |
| PostgreSQL connection failure | Services can't start | Docker healthcheck with `pg_isready`; `depends_on` condition ensures DB is ready before app services start |
| Foundry Toolbox `web_search` not provisioned | Fact-Checker can't ground claims | Declare in `agent.manifest.yaml`; auto-provisioned by `azd provision`; manual fallback in Foundry portal |
| MCP tool scoping not enforced at SDK level | Agent calls wrong tools | Strong system prompts with explicit "ONLY use these tools" instructions; won't cause failures, just suboptimal routing |
| GPT-4o struggles with `context_mode="last_agent"` chaining | Agents lose context from earlier stages | Test with GPT-4o first; fall back to `context_mode="all"` if needed (higher token cost); sample README recommends advanced model |

---

## Requirements (Exact Package Versions)

### `agent/requirements.txt`
```
agent-framework>=1.2.2
agent-framework-foundry-hosting
azure-identity
httpx
pydantic-settings
```

### `mcp_server/requirements.txt`
```
mcp[server]
httpx
sqlalchemy
psycopg2-binary
pydantic-settings
```

### `dashboard/requirements.txt`
```
streamlit
sqlalchemy
psycopg2-binary
pandas
```

---

## Resolved Decisions (previously "Open Questions")

| Previous Question | Resolution |
|---|---|
| MCP tool scoping per agent | `client.get_mcp_tool()` gives access to ALL tools on the server. **Resolution:** Use system prompt enforcement per agent (e.g., "You MUST only use: get_schedule, get_historical_trends"). This is standard practice in the sample repos. |
| BingGroundingTool availability | `BingGroundingTool` does NOT exist in Agent Framework. **Resolution:** Use Foundry Toolbox `web_search` via `MCPStreamableHTTPTool` (sample 04 pattern). Declared in `agent.manifest.yaml` and auto-provisioned by `azd provision`. |
| PostgreSQL on Azure Container Apps | Container Apps are stateless. **Resolution:** Use Azure Database for PostgreSQL Flexible Server; connect from Container Apps via connection string in env var. No file mounts needed. |
| World Cup 2026 data availability | Tournament starts June 11, 2026. **Resolution:** Pre-seed `fixtures_seed.json` with known group stage matches for development. Switch to live API-Football on tournament day 1. |

---

*Reference samples: [05-workflows](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/agent-framework/responses/05-workflows) · [03-mcp](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/agent-framework/responses/03-mcp) · [04-foundry-toolbox](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/agent-framework/responses/04-foundry-toolbox)*
