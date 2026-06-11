# World Cup 2026 AI Intelligence Platform

An AI-powered multi-agent platform delivering pre-match briefings, explainable prediction cards, audit-grounded fact checks, and media packs for the FIFA World Cup 2026.

## Architecture

A collaborative multi-agent pipeline — **Scout → Fact-Checker → Tactician → Scribe** — runs as a single Microsoft Foundry Hosted Agent using the Agent Framework `WorkflowBuilder` pattern, backed by a dedicated MCP tool server and a Streamlit analytics dashboard.

| Service | Port | Description |
|---------|------|-------------|
| **MCP Server** | 8000 | FastMCP tool server (schedule, trends, grounding, persistence) |
| **Agent** | 8088 | Hosted Agent — Responses Protocol multi-agent workflow |
| **Dashboard** | 8501 | Streamlit analytics UI (schedule, predictions, audit trail, media packs) |

### System Architecture

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
    ACA -.-> PG_SVC
    ACA -.-> AI
```

### End-to-End Flow

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

### Database Schema

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

### Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Multi-agent pattern | `WorkflowBuilder` in-process pipeline (single hosted container) | Simpler deployment; single container; no inter-service auth overhead |
| MCP tool server | Separate container (FastMCP, port 8000) | Preserves protocol boundary; independently testable |
| Web search grounding | Foundry Toolbox `web_search` via `MCPStreamableHTTPTool` | Platform-managed citations; no manual Bing resource |
| Agent context passing | `context_mode="last_agent"` | Prevents context bloat; each agent only sees prior output |
| Storage | PostgreSQL (Docker container locally, Azure Database for PostgreSQL on Azure) | ACID-compliant; concurrent access; no file-locking issues |
| Deployment | `azd up` (single command) | Auto-provisions ACR, Container Apps, Foundry Toolbox, App Insights |

### Azure Deployment Architecture

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

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- An [API-Football](https://www.api-football.com/) API key
- Azure AI Foundry project endpoint (for hosted agent & GPT-4o)

## Quick Start (Local)

1. **Clone the repository**

   ```bash
   git clone <repo-url>
   cd AIHackathon
   ```

2. **Set environment variables**

   ```bash
   cp .env.example .env
   # Edit .env and fill in:
   #   FOOTBALL_API_KEY=<your-api-football-key>
   #   FOUNDRY_PROJECT_ENDPOINT=<your-azure-ai-foundry-endpoint>
   #   AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
   #   FOUNDRY_TOOLBOX_ENDPOINT=<optional-toolbox-endpoint>
   ```

3. **Run with Docker Compose**

   ```bash
   docker-compose up --build
   ```

   This starts the PostgreSQL database, MCP server, agent, and dashboard containers.

4. **Access the dashboard**

   Open [http://localhost:8501](http://localhost:8501) in your browser.

5. **Invoke the agent**

   ```bash
   curl -X POST http://localhost:8088/responses \
     -H "Content-Type: application/json" \
     -d '{"input": "Analyze today'\''s World Cup matches"}'
   ```

## Deploy to Azure

```bash
azd up
```

This provisions Azure Container Apps, Azure Container Registry, Azure Database for PostgreSQL, and Application Insights via the `azure.yaml` configuration.

## Project Structure

```
├── agent/              # Hosted Agent (Responses Protocol, WorkflowBuilder)
├── mcp_server/         # FastMCP tool server
│   ├── tools/          # get_schedule, get_historical_trends, grounding, persistence
│   └── clients/        # API-Football v3 async client
├── dashboard/          # Streamlit 4-page analytics app
├── shared/             # Shared DB models, Jinja2 email templates
├── config/             # Settings (pydantic-settings)
├── data/               # Local data files
├── tests/              # Unit tests
├── azure.yaml          # Azure Developer CLI manifest
└── docker-compose.yml  # Local orchestration
```

## Agent Pipeline

| Stage | Agent | Role |
|-------|-------|------|
| 1 | **Scout** | Fetches fixtures & team metrics via MCP tools |
| 2 | **Fact-Checker** | Verifies claims using web search & grounding tools |
| 3 | **Tactician** | Pure LLM reasoning — generates predictions & analysis |
| 4 | **Scribe** | Produces media packs, email HTML, and social content |

## Running Tests

```bash
pip install -r mcp_server/requirements.txt
pip install pytest
pytest tests/
```

## License

See [LICENSE](LICENSE) for details.
