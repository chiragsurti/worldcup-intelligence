"""FastMCP server entry point for World Cup Intelligence Platform."""

import logging
import os
import sys

# Add project root to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from shared.db.database import init_db

from mcp_server.tools.grounding import ground_and_audit_claim
from mcp_server.tools.persistence import get_prediction_cards, save_media_pack, save_prediction_card
from mcp_server.tools.schedule import get_schedule
from mcp_server.tools.trends import get_historical_trends

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    "WorldCupIntelligence",
    stateless_http=True,
    json_response=True,
)


# --- Tool registrations ---


@mcp.tool()
async def tool_get_schedule(date: str) -> str:
    """Fetch World Cup fixtures for a given date and persist them.

    Args:
        date: Date in YYYY-MM-DD format (e.g., '2026-06-11').

    Returns:
        JSON array of fixture objects with match_id, teams, venue, status.
    """
    return await get_schedule(date)


@mcp.tool()
async def tool_get_historical_trends(team_id: int, player_id: int | None = None) -> str:
    """Get historical performance trends for a team and optionally a player.

    Args:
        team_id: API-Football team ID.
        player_id: Optional API-Football player ID.

    Returns:
        JSON with rolling metrics (form, goals, clean sheets, etc.).
    """
    return await get_historical_trends(team_id, player_id)


@mcp.tool()
async def tool_ground_and_audit_claim(
    claim_text: str,
    citations: list[dict],
    status_label: str,
    confidence_score: float,
    entity_mappings: dict,
    match_id: str = "unknown",
) -> str:
    """Validate and persist a grounded claim with citations to the audit trail.

    Args:
        claim_text: Normalized claim text.
        citations: Array of objects with url, title, publisher, publish_time, quote_snippet.
        status_label: One of 'Confirmed', 'Reported', or 'Unverified'.
        confidence_score: Confidence between 0.0 and 1.0.
        entity_mappings: Dict of entity ID mappings (e.g., wikidata → api_football).
        match_id: Related fixture match_id.

    Returns:
        JSON with saved record ID and status.
    """
    return await ground_and_audit_claim(
        claim_text=claim_text,
        citations=citations,
        status_label=status_label,
        confidence_score=confidence_score,
        entity_mappings=entity_mappings,
        match_id=match_id,
    )


@mcp.tool()
async def tool_save_prediction_card(
    match_id: str,
    prob_home: float,
    prob_draw: float,
    prob_away: float,
    analysis: str,
    reasoning: str,
) -> str:
    """Save a match prediction card with probabilities and reasoning.

    Args:
        match_id: Fixture match_id.
        prob_home: Home win probability (0.0–1.0).
        prob_draw: Draw probability (0.0–1.0).
        prob_away: Away win probability (0.0–1.0).
        analysis: Summary of tactical analysis.
        reasoning: Transparent reasoning chain explaining the prediction.

    Returns:
        JSON with saved prediction card ID.
    """
    return await save_prediction_card(
        match_id=match_id,
        prob_home=prob_home,
        prob_draw=prob_draw,
        prob_away=prob_away,
        analysis=analysis,
        reasoning=reasoning,
    )


@mcp.tool()
async def tool_save_media_pack(
    match_id: str,
    email_html: str,
    social_threads: list[str],
) -> str:
    """Save a media pack with email HTML and social media thread posts.

    Args:
        match_id: Fixture match_id.
        email_html: Full rendered HTML email content.
        social_threads: Array of social media post strings (e.g., 5-tweet thread).

    Returns:
        JSON with saved media pack ID.
    """
    return await save_media_pack(
        match_id=match_id,
        email_html=email_html,
        social_threads=social_threads,
    )


@mcp.tool()
async def tool_get_prediction_cards(date: str) -> str:
    """Retrieve all prediction cards for matches on a given date.

    Args:
        date: Date in YYYY-MM-DD format.

    Returns:
        JSON array of prediction card objects.
    """
    return await get_prediction_cards(date)


if __name__ == "__main__":
    # Initialize database tables
    init_db()
    logger.info("Database initialized. Starting MCP server on port 8000...")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
