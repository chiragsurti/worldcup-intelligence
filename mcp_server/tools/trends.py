"""MCP Tool: get_historical_trends — fetch team/player rolling metrics."""

import json
import logging
import os

from mcp_server.clients.football_api import FootballAPIClient

logger = logging.getLogger(__name__)


async def get_historical_trends(team_id: int, player_id: int | None = None) -> str:
    """Fetch historical performance trends for a team and optionally a player.

    Args:
        team_id: API-Football team ID.
        player_id: Optional API-Football player ID for individual stats.

    Returns:
        JSON string with rolling performance metrics.
    """
    api_key = os.environ.get("FOOTBALL_API_KEY", "")
    result = {"team_id": team_id, "player_id": player_id, "metrics": {}}

    if not api_key:
        # Return mock trend data for development
        result["metrics"] = _mock_team_metrics(team_id)
        if player_id:
            result["player_metrics"] = _mock_player_metrics(player_id)
        return json.dumps(result, indent=2)

    try:
        client = FootballAPIClient(api_key=api_key)

        # Team stats
        team_stats = await client.get_team_stats(team_id=team_id)
        if team_stats:
            result["metrics"] = {
                "form": team_stats.get("form", ""),
                "fixtures_played": team_stats.get("fixtures", {}).get("played", {}),
                "goals_for": team_stats.get("goals", {}).get("for", {}),
                "goals_against": team_stats.get("goals", {}).get("against", {}),
                "clean_sheets": team_stats.get("clean_sheet", {}),
                "penalty_scoring_pct": team_stats.get("penalty", {}).get("scored", {}).get("percentage", "0%"),
            }

        # Player stats (if requested)
        if player_id:
            player_data = await client.get_player_stats(player_id=player_id)
            if player_data:
                player_info = player_data[0] if player_data else {}
                stats = player_info.get("statistics", [{}])[0] if player_info.get("statistics") else {}
                result["player_metrics"] = {
                    "name": player_info.get("player", {}).get("name", "Unknown"),
                    "goals": stats.get("goals", {}).get("total", 0),
                    "assists": stats.get("goals", {}).get("assists", 0),
                    "appearances": stats.get("games", {}).get("appearences", 0),
                    "rating": stats.get("games", {}).get("rating", "N/A"),
                    "minutes_played": stats.get("games", {}).get("minutes", 0),
                }

        await client.close()
    except Exception as e:
        logger.warning(f"API-Football trends call failed, using mock data: {e}")
        result["metrics"] = _mock_team_metrics(team_id)
        if player_id:
            result["player_metrics"] = _mock_player_metrics(player_id)

    return json.dumps(result, indent=2)


def _mock_team_metrics(team_id: int) -> dict:
    """Generate mock team metrics for development."""
    return {
        "form": "WWDWL",
        "fixtures_played": {"home": 5, "away": 4, "total": 9},
        "goals_for": {"home": 12, "away": 6, "total": 18},
        "goals_against": {"home": 3, "away": 5, "total": 8},
        "clean_sheets": {"home": 3, "away": 1, "total": 4},
        "penalty_scoring_pct": "80%",
        "note": "Mock data — API-Football key not configured or unavailable",
    }


def _mock_player_metrics(player_id: int) -> dict:
    """Generate mock player metrics for development."""
    return {
        "name": f"Player #{player_id}",
        "goals": 7,
        "assists": 4,
        "appearances": 9,
        "rating": "7.8",
        "minutes_played": 720,
        "note": "Mock data — API-Football key not configured or unavailable",
    }
