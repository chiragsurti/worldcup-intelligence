# World Cup 2026 AI Intelligence Platform

An AI-powered multi-agent platform delivering pre-match briefings, explainable prediction cards, audit-grounded fact checks, and media packs for the FIFA World Cup 2026.

## Architecture

A collaborative multi-agent pipeline — **Scout → Fact-Checker → Tactician → Scribe** — runs as a single Microsoft Foundry Hosted Agent using the Agent Framework `WorkflowBuilder` pattern, backed by a dedicated MCP tool server and a Streamlit analytics dashboard.

| Service | Port | Description |
|---------|------|-------------|
| **MCP Server** | 8000 | FastMCP tool server (schedule, trends, grounding, persistence) |
| **Agent** | 8088 | Hosted Agent — Responses Protocol multi-agent workflow |
| **Dashboard** | 8501 | Streamlit analytics UI (schedule, predictions, audit trail, media packs) |

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

   This starts the MCP server, agent, and dashboard containers.

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

This provisions Azure Container Apps, Azure Container Registry, Azure Files (shared SQLite volume), and Application Insights via the `azure.yaml` configuration.

## Project Structure

```
├── agent/              # Hosted Agent (Responses Protocol, WorkflowBuilder)
├── mcp_server/         # FastMCP tool server
│   ├── tools/          # get_schedule, get_historical_trends, grounding, persistence
│   └── clients/        # API-Football v3 async client
├── dashboard/          # Streamlit 4-page analytics app
├── shared/             # Shared DB models, Jinja2 email templates
├── config/             # Settings (pydantic-settings)
├── data/               # SQLite database (local dev volume)
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
