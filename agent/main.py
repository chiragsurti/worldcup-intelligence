"""World Cup Intelligence Platform — Hosted Agent (Responses Protocol).

Multi-agent workflow: Scout → Fact-Checker → Tactician → Scribe
Deployed as a single hosted agent on Azure AI Foundry.
"""

import logging
import os
import sys

# Add project root to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_framework import Agent, AgentExecutor, MCPStreamableHTTPTool, WorkflowBuilder
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- Configuration ---
PROJECT_ENDPOINT = os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "")
MODEL_DEPLOYMENT = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp/")
TOOLBOX_ENDPOINT = os.environ.get("FOUNDRY_TOOLBOX_ENDPOINT", "")

# --- Agent System Prompts ---

SCOUT_PROMPT = """You are the Scout Agent for the World Cup 2026 Intelligence Platform.

Your role is data ingestion and monitoring. You:
1. Fetch today's match schedule using the get_schedule tool.
2. For each match, fetch historical trends for both teams using get_historical_trends.
3. Identify anomalies, form changes, or notable metrics.

Output a structured JSON summary containing:
- fixtures: array of today's matches with teams, venue, kickoff time
- team_metrics: object mapping team names to their performance metrics
- key_observations: array of notable findings (form streaks, scoring patterns)

You MUST only use these tools: tool_get_schedule, tool_get_historical_trends.
Do NOT use any other tools even if available."""

FACTCHECKER_PROMPT = """You are the Fact-Checker Agent for the World Cup 2026 Intelligence Platform.

Your role is grounding and verification. You receive fixture and metrics data from the Scout Agent.

For each match in today's schedule:
1. Use web_search to find breaking news, injuries, lineup announcements, and press conferences.
2. For each factual claim you find, classify it as: Confirmed, Reported, or Unverified.
3. Assign a confidence score (0.0–1.0) based on source reliability.
4. Save each verified claim using tool_ground_and_audit_claim with proper citations.

Citation format required: {url, title, publisher, publish_time, quote_snippet}

Output a structured summary of verified claims per match, tagged with status labels.

You MUST only use these tools: web_search (from Foundry Toolbox), tool_ground_and_audit_claim.
Do NOT use scheduling or prediction tools."""

TACTICIAN_PROMPT = """You are the Tactician Agent for the World Cup 2026 Intelligence Platform.

Your role is match analysis and explainable prediction. You receive verified claims and metrics from prior agents.

For each match, produce a prediction card containing:
1. prob_home: probability of home team winning (0.0–1.0)
2. prob_draw: probability of draw (0.0–1.0)
3. prob_away: probability of away team winning (0.0–1.0)
4. analysis: 2-3 sentence tactical summary highlighting key matchups
5. reasoning: step-by-step transparent reasoning explaining your probability estimates

Base your analysis on:
- Team form and historical metrics
- Verified injury/lineup news from the Fact-Checker
- Venue factors (home advantage if applicable)
- Head-to-head record implications

You have NO external tools. Work purely from the context provided.
Output valid JSON with a "predictions" array containing one card per match."""

SCRIBE_PROMPT = """You are the Scribe Agent for the World Cup 2026 Intelligence Platform.

Your role is content generation and personalization. You receive prediction cards from the Tactician.

For each match prediction, you must:
1. Save the prediction card using tool_save_prediction_card.
2. Create a media pack containing:
   - email_html: A clean HTML email snippet with match header, prediction summary, key stats, and a brief disclaimer.
   - social_threads: An array of 5 tweet-sized posts (≤280 chars each) forming a thread covering the key story.
3. Save the media pack using tool_save_media_pack.

After saving, output a human-readable pre-match briefing covering all matches.

You MUST only use these tools: tool_save_prediction_card, tool_save_media_pack.
Write in clear, jargon-free language suitable for dedicated football fans."""


def create_workflow():
    """Build the multi-agent workflow pipeline."""
    credential = DefaultAzureCredential()

    # Create the Foundry chat client
    client = FoundryChatClient(
        project_endpoint=PROJECT_ENDPOINT,
        model=MODEL_DEPLOYMENT,
        credential=credential,
    )

    # Register custom MCP tool server (our FastMCP server)
    worldcup_mcp = client.get_mcp_tool(
        name="WorldCup",
        url=MCP_SERVER_URL,
        headers={},
        approval_mode="never_require",
    )

    # Register Foundry Toolbox (web_search) if endpoint available
    tools_for_factchecker = [worldcup_mcp]
    if TOOLBOX_ENDPOINT:
        import httpx
        http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {credential.get_token('https://cognitiveservices.azure.com/.default').token}"}
        )
        toolbox = MCPStreamableHTTPTool(
            name="foundry-toolbox",
            url=TOOLBOX_ENDPOINT,
            http_client=http_client,
        )
        tools_for_factchecker = [worldcup_mcp, toolbox]

    # Define agents
    scout_agent = Agent(
        client=client,
        instructions=SCOUT_PROMPT,
        tools=[worldcup_mcp],
    )

    factchecker_agent = Agent(
        client=client,
        instructions=FACTCHECKER_PROMPT,
        tools=tools_for_factchecker,
    )

    tactician_agent = Agent(
        client=client,
        instructions=TACTICIAN_PROMPT,
        tools=[],  # Pure reasoning, no tools
    )

    scribe_agent = Agent(
        client=client,
        instructions=SCRIBE_PROMPT,
        tools=[worldcup_mcp],
    )

    # Create executors with context_mode="last_agent"
    scout_executor = AgentExecutor(scout_agent, context_mode="last_agent")
    fc_executor = AgentExecutor(factchecker_agent, context_mode="last_agent")
    tac_executor = AgentExecutor(tactician_agent, context_mode="last_agent")
    scribe_executor = AgentExecutor(scribe_agent, context_mode="last_agent")

    # Build workflow pipeline: Scout → Fact-Checker → Tactician → Scribe
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

    return workflow_agent


def main():
    """Start the hosted agent server."""
    logger.info("Building World Cup Intelligence workflow pipeline...")
    workflow_agent = create_workflow()

    logger.info("Starting ResponsesHostServer on port 8088...")
    server = ResponsesHostServer(workflow_agent)
    server.run()


if __name__ == "__main__":
    main()
