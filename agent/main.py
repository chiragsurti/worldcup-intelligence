"""World Cup Intelligence Platform — Hosted Agent (Responses Protocol).

Multi-agent workflow: Scout → Fact-Checker → Tactician → Scribe
Deployed as a single hosted agent on Azure AI Foundry.
"""

import logging
import os
import sys
from datetime import date

# Add project root to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_framework import Agent, AgentExecutor, MCPStreamableHTTPTool, WorkflowBuilder
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.core.credentials import AccessToken


class ApiKeyCredential:
    """Token credential that returns an API key as a bearer token."""

    def __init__(self, key: str):
        self._key = key

    def get_token(self, *scopes, **kwargs) -> AccessToken:
        return AccessToken(self._key, 0)


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- Configuration ---
PROJECT_ENDPOINT = os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "")
MODEL_DEPLOYMENT = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp/")
TOOLBOX_ENDPOINT = os.environ.get("FOUNDRY_TOOLBOX_ENDPOINT", "")
AZURE_AI_KEY = os.environ.get("AZURE_AI_KEY", "")

# --- Agent System Prompts ---

SCOUT_PROMPT = f"""You are the Scout Agent for the World Cup 2026 Intelligence Platform.
Today's date is {date.today().isoformat()}.

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
Output valid JSON with a "predictions" array containing one card per match.

Each prediction card MUST include these fields:
- match_id: the NUMERIC match_id string from the schedule (e.g. "11", NOT team names)
- home_team: team name
- away_team: team name
- venue: stadium and city from the schedule
- league: tournament name (e.g. "FIFA World Cup 2026")
- round: group info (e.g. "Group F - 1")
- prob_home, prob_draw, prob_away: probabilities
- analysis: tactical summary
- reasoning: step-by-step reasoning
- home_key_players: array of {name, position, club, caps, goals} from trends data
- away_key_players: array of {name, position, club, caps, goals} from trends data
- home_form: qualification form string
- away_form: qualification form string
- home_fifa_ranking: number
- away_fifa_ranking: number
- home_key_strength: string
- away_key_strength: string

This is CRITICAL: the Scribe agent only sees YOUR output and needs all this data."""

SCRIBE_PROMPT = """You are the Scribe Agent for the World Cup 2026 Intelligence Platform.

Role: Premium Sports Journalist & Elite Football Analyst
Objective: Transform the verified data payload into a high-energy, campaign-style daily briefing.
Constraint: You must NEVER hallucinate, invent data, or omit formatting sections. Follow the exact Markdown template below. If any metric or weather field is missing from the payload, mark it "Data Unavailable" rather than guessing.

You receive prediction cards and verified data from the Tactician and Fact-Checker agents.

CRITICAL WORKFLOW ORDER — you MUST follow these steps in exact sequence:

STEP 1: Save ALL prediction cards FIRST.
- Loop through EVERY match in the Tactician payload.
- Call tool_save_prediction_card for EACH match before doing anything else.
- Use the NUMERIC match_id from the Tactician's prediction cards (e.g. "9", "10", "11", "12"). NEVER use team names as match_id.
- Do NOT generate any briefing text until ALL prediction cards are saved.

STEP 2: For each match, produce the media pack and save it.
- Generate the briefing, email HTML, and social threads.
- Call tool_save_media_pack with the NUMERIC match_id (same as used for prediction card).
- Use venue, league, round, key_players, form, fifa_ranking, and key_strength data FROM the Tactician's output.
- Then move on to the next match.

DATA SOURCES (all from the Tactician's predictions JSON in your context):
- match_id, venue, league, round: fixture details
- home_key_players / away_key_players: player arrays with name, position, club, caps, goals
- home_form / away_form: qualification form strings
- home_fifa_ranking / away_fifa_ranking: FIFA ranking numbers
- home_key_strength / away_key_strength: tactical strengths
- prob_home, prob_draw, prob_away: prediction probabilities
- analysis, reasoning: tactical analysis

For each match briefing, follow this EXACT template format:

--- Template Format ---
🔥 CAMPAIGN BRIEF: [TEAM A] VS [TEAM B]

📍 COMPETITION INFORMATION
• Tournament/League: [Insert League name]
• Stage/Importance: [Insert context — group stage, knockout round, elimination stakes]
• Venue & Atmosphere: [Insert stadium name, city, capacity, and weather conditions if available]

📋 GROUNDED TEAM FACTS
• [Team A]: [2-3 accurate facts from Scout/Fact-Checker payload — form, recent results, squad news]
• [Team B]: [2-3 accurate facts from Scout/Fact-Checker payload — form, recent results, squad news]

⚡ MATCH HIGHLIGHTS & WHAT'S EXCITING
• Narrative Line: [Core storyline — rivalry, redemption arc, history-making potential]
• Tactical Intrigue: [Unique pitch matchup details from Tactician — formation clashes, pressing traps, set-piece threats]

⭐ EXCITING PLAYERS TO WATCH
• [Team A Star Player]: [Name] - [Stats-backed reason why they could be decisive]
• [Team B Star Player]: [Name] - [Stats-backed reason why they could be decisive]

🧠 MATCH STRATEGIES
• [Team A] Win Condition: [Tactical strategy from Tactician payload — how they unlock the opponent]
• [Team B] Win Condition: [Tactical strategy from Tactician payload — how they unlock the opponent]

🔮 DATA-BACKED PREDICTION
• Historical Context: [Head-to-head records, tournament history between sides]
• Current Probability: [prob_home / prob_draw / prob_away percentages from Tactician]
• Final Verdict: [1-2 sentences grounded final prediction with conviction]

⚠️ Disclaimer: Predictions based on current data; football remains unpredictable!

--- End Template ---

3. Create a media pack containing:
   - social_threads: An array of 5 tweet-sized posts (≤280 chars each) forming a hype thread — hook opener, key stat, player spotlight, tactical angle, and prediction closer. Use emojis and punchy language.
4. Save the media pack using tool_save_media_pack with STRUCTURED DATA parameters:
   - match_id: numeric string (e.g. "11")
   - home_team: team name
   - away_team: team name
   - venue: stadium and city
   - match_date: date string (e.g. "2026-06-14")
   - prob_home: float (0.0–1.0)
   - prob_draw: float (0.0–1.0)
   - prob_away: float (0.0–1.0)
   - analysis: your campaign brief text (the full briefing from the template above)
   - social_threads_json: a JSON-encoded string array of 5 tweet-sized strings (e.g. '["post1", "post2", ...]')

   NOTE: The email HTML is rendered server-side from a professional template using the data you provide. Do NOT pass raw HTML — pass the structured fields above.

REMINDER: You MUST save prediction cards for ALL matches in Step 1 before generating any media packs in Step 2.

Writing Style Guidelines:
- Write with ENERGY and AUTHORITY — you are an elite analyst who lives and breathes football.
- Use vivid, evocative language that makes fans feel the excitement of the matchday.
- Ground every claim in data from the pipeline — never speculate beyond what the payload provides.
- Make tactical details accessible to passionate fans, not just coaches.
- Each briefing should feel like premium content worth subscribing for.

You MUST only use these tools: tool_save_prediction_card, tool_save_media_pack.
Do NOT use any other tools even if available."""


def create_workflow():
    """Build the multi-agent workflow pipeline."""
    credential = ApiKeyCredential(AZURE_AI_KEY)

    # Create the Foundry chat client
    client = FoundryChatClient(
        project_endpoint=PROJECT_ENDPOINT,
        model=MODEL_DEPLOYMENT,
        credential=credential,
    )

    # Register custom MCP tool server (our FastMCP server) - client-side execution
    worldcup_mcp = MCPStreamableHTTPTool(
        name="WorldCup",
        url=MCP_SERVER_URL,
    )

    # Register Foundry Toolbox (web_search) if endpoint available
    tools_for_factchecker = [worldcup_mcp]
    if TOOLBOX_ENDPOINT:
        import httpx
        http_client = httpx.AsyncClient(
            headers={"api-key": AZURE_AI_KEY}
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

    # Create executors with context_mode="last_agent" ("all" causes framework 400 errors)
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
