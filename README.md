# World Cup 2026 AI Intelligence Platform

An AI-powered multi-agent platform delivering pre-match briefings, explainable prediction cards, audit-grounded fact checks, and media packs for the FIFA World Cup 2026.

## Demo

![Highlight Demo](Demo/Highlight-Demo.gif)

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

### Azure AI Foundry — Agent & Toolbox Architecture

```mermaid
graph TB
    subgraph USER["Client"]
        CLIENT["🔌 API Client / Dashboard\nPOST /responses"]
    end

    subgraph FOUNDRY_PLATFORM["Azure AI Foundry Platform"]
        direction TB

        subgraph PROJECT["AI Foundry Project (ms-foundry-c)"]
            direction TB
            ENDPOINT["🌐 Project Endpoint\nhttps://ms-foundry-c.services.ai.azure.com\n/api/projects/proj-default"]

            subgraph HOSTED_SVC["Foundry Hosted Agent Service"]
                direction LR
                RESP["ResponsesHostServer\n(Responses Protocol)\nport 8088"]
                AGENT_FW["Agent Framework\nWorkflowBuilder\n─────────────\n4-agent pipeline:\nScout → Fact-Checker\n→ Tactician → Scribe"]
                RESP --> AGENT_FW
            end

            subgraph MODEL_DEPLOY["Model Deployments"]
                GPT["🤖 GPT-4.1\nDeployment: gpt-4.1-960518\nAzure OpenAI inference\nAPI Key auth"]
            end

            subgraph TOOLBOX_SVC["Foundry Toolbox Service"]
                direction TB
                TB_EP["📡 Toolbox MCP Endpoint\n/toolboxes/WebsearchToolbox/mcp\n?api-version=v1"]
                TB_TOOLS["Registered Tools:\n• web_search(query)\n• web_search(query, count)\n• web_search(query, freshness)"]
                TB_EP --> TB_TOOLS
            end
        end

        subgraph BING["Microsoft Bing Infrastructure"]
            BING_API["🔍 Bing Web Search API\n(Grounded Search)\n─────────────────\n• Real-time web results\n• Inline citations\n• Source URLs + snippets\n• Publisher metadata"]
        end
    end

    subgraph CUSTOM_MCP["Custom MCP Server (Container)"]
        MCP_SRV["FastMCP Server\nport 8000 /mcp\n─────────────\nTools:\n• get_schedule\n• get_historical_trends\n• ground_and_audit_claim\n• save_prediction_card\n• save_media_pack"]
    end

    CLIENT -->|"POST /responses\nBearer API Key"| RESP
    AGENT_FW -->|"FoundryChatClient\nchat completions\napi-key header"| GPT
    AGENT_FW -->|"MCPStreamableHTTPTool\nFOUNDRY_TOOLBOX_ENDPOINT\napi-key header"| TB_EP
    AGENT_FW -->|"MCPStreamableHTTPTool\nMCP_SERVER_URL\nHTTP POST"| MCP_SRV
    TB_TOOLS -->|"Platform-managed\nBing Grounding"| BING_API

    style FOUNDRY_PLATFORM fill:#e8f4fd,stroke:#0078d4
    style PROJECT fill:#f0f8ff,stroke:#0078d4
    style TOOLBOX_SVC fill:#fff3e0,stroke:#f57c00
    style BING fill:#e8f5e9,stroke:#388e3c
    style HOSTED_SVC fill:#ede7f6,stroke:#5e35b1
    style MODEL_DEPLOY fill:#fce4ec,stroke:#c62828
```

#### Toolbox Connection Flow

```mermaid
sequenceDiagram
    participant Agent as Fact-Checker Agent
    participant FW as Agent Framework
    participant TB as Foundry Toolbox<br/>(WebsearchToolbox)
    participant Bing as Bing Web Search API

    Note over Agent,Bing: FOUNDRY_TOOLBOX_ENDPOINT = .../toolboxes/WebsearchToolbox/mcp?api-version=v1

    Agent->>FW: "Search for Brazil injury news World Cup 2026"
    FW->>TB: POST /toolboxes/WebsearchToolbox/mcp<br/>Header: api-key: AZURE_AI_KEY<br/>Body: {"method":"tools/call","params":{"name":"web_search","arguments":{"query":"..."}}}
    TB->>Bing: Bing Grounding API call<br/>(platform-managed, no user Bing key needed)
    Bing-->>TB: Web results with citations,<br/>snippets, URLs, publish dates
    TB-->>FW: MCP tool response<br/>{"content":[{"type":"text","text":"...results with citations..."}]}
    FW-->>Agent: Grounded search results<br/>with inline source citations

    Note over Agent: Agent uses citations to<br/>call ground_and_audit_claim<br/>on custom MCP server
```

## Prerequisites

- Python 3.11+
- Docker/Podman with Compose support
- [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/) *(for Azure deployment only)*
- An [API-Football](https://www.api-football.com/) API key
- Azure AI Foundry project endpoint + API key (for hosted agent & GPT-4.1)

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
   #   AZURE_AI_KEY=<your-foundry-api-key>
   #   AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4.1-960518
   #   FOUNDRY_TOOLBOX_ENDPOINT=<optional-toolbox-endpoint>
   ```

3. **Run with Docker Compose or Podman**

   ```bash
   # Docker
   docker-compose up --build

   # Podman (drop-in replacement, no extra config needed)
   podman compose up --build
   ```

   This starts PostgreSQL, MCP server, agent, and dashboard containers.

   **Rebuild a single service after code changes:**

   ```bash
   # Rebuild and restart only the changed component (e.g. mcp-server)
   podman compose up --build mcp-server

   # Rebuild and restart the agent
   podman compose up --build agent

   # Rebuild and restart the dashboard
   podman compose up --build dashboard

   # Rebuild multiple changed services at once
   podman compose up --build mcp-server agent
   ```

   Add `-d` to run in detached mode (background):

   ```bash
   podman compose up --build -d mcp-server
   ```

4. **Access the dashboard**

   Open [http://localhost:8501](http://localhost:8501) in your browser.

5. **Invoke the agent**

   ```bash
   curl -X POST http://localhost:8088/responses \
     -H "Content-Type: application/json" \
     -d '{"input": "Analyze today'\''s World Cup matches"}'
   ```

   PowerShell:
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8088/responses" -Method POST `
     -ContentType "application/json" `
     -Body '{"input": "Analyze today''s World Cup matches"}'
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
| 4 | **Scribe** | Premium Sports Journalist — produces campaign-style briefings, media packs, email HTML, and social hype threads |

### Scribe Output Format

The Scribe agent outputs a structured **Campaign Brief** per match:

- 🔥 **Campaign Brief** — match header
- 📍 **Competition Information** — tournament, stage, venue & atmosphere
- 📋 **Grounded Team Facts** — verified facts from Scout/Fact-Checker
- ⚡ **Match Highlights & What's Exciting** — narrative and tactical intrigue
- ⭐ **Exciting Players to Watch** — stats-backed star player spotlights
- 🧠 **Match Strategies** — win conditions from Tactician analysis
- 🔮 **Data-Backed Prediction** — historical context, probabilities, final verdict
- ⚠️ **Disclaimer** — "Predictions based on current data; football remains unpredictable!"

Media packs include visually compelling HTML emails and a 5-post social hype thread (hook → stat → player → tactics → prediction).

## Running Tests

```bash
pip install -r mcp_server/requirements.txt
pip install pytest
pytest tests/
```

## Utility Scripts

### Data Cleanup

Remove persisted data from PostgreSQL:

```bash
# Delete all data for a specific date
python scripts/cleanup_date.py 2026-06-14

# Delete ALL data (fixtures, predictions, media packs, audit claims)
python scripts/cleanup_date.py --all
```

### Wikipedia Data Sync

```bash
python scripts/sync_wikipedia_data.py
```

## Data Sources & Wikipedia Sync

The platform uses a multi-layered data strategy to ensure reliable operation even before the World Cup 2026 officially starts:

### Primary: API-Football v3 (Free Tier)

Live match data is fetched from [API-Football v3](https://www.api-football.com/) (`v3.football.api-sports.io`) using the World Cup league ID (`1`) and season `2026`. The platform uses the **free tier** subscription, which has the following limitations:

- **100 requests/day** rate limit
- Limited historical data depth
- No real-time lineups or live match events
- Delayed data updates compared to paid tiers

Due to these constraints, the platform relies heavily on pre-ingested fallback data to ensure consistent, rich analysis regardless of API availability.

### Fallback: Pre-Ingested Data from Wikipedia & Other Sources

To compensate for free-tier API limitations, the platform includes comprehensive pre-seeded CSV/JSON files in the `data/` directory, ingested from Wikipedia's [2026 FIFA World Cup](https://en.wikipedia.org/wiki/2026_FIFA_World_Cup) article, related pages, and other publicly available sources:

| File | Source | Contents |
|------|--------|----------|
| `worldcup2026.teams.csv` | Wikipedia team lists | 48 qualified teams with FIFA codes, ISO2 country codes, group assignments, and flag image URLs from Wikimedia Commons |
| `worldcup2026.games.csv` | Wikipedia match schedule | Full group stage fixture list with match dates, team IDs, stadium IDs, and kickoff times |
| `worldcup2026.stadia.csv` | Wikipedia venue articles | 16 host stadiums with city, country, capacity, and region |
| `worldcup2026.groups.csv` | Wikipedia group draw | Group compositions (A–L) with team assignments |
| `worldcup2026.groups.json` | Wikipedia group draw | Same as above in JSON format for programmatic access |
| `worldcup2026.players.json` | Wikipedia squad lists | Player data (name, position, club) for each national team |
| `worldcup2026.team_stats.json` | Wikipedia + historical data | Pre-tournament team statistics and performance metrics |

### Fallback Resolution Logic

The `FootballAPIClient` in `mcp_server/clients/football_api.py` implements automatic fallback to handle free-tier limitations gracefully:

1. Query API-Football for the requested data
2. If the API returns empty results, HTTP 429 (rate limit exceeded), or the daily quota is exhausted, load equivalent data from the local CSV/JSON files via `mcp_server/clients/fallback_data.py`
3. If no local files exist, use hardcoded seed fixtures for key match dates

This ensures the agent pipeline always has rich, complete data to work with — regardless of API-Football free-tier availability, rate limits, or whether the tournament has officially started. The ingested Wikipedia and public-source data provides the same level of detail (teams, squads, venues, historical stats) that a paid API tier would offer.

## License

See [LICENSE](LICENSE) for details.
