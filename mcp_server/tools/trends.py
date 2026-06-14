"""MCP Tool: get_historical_trends — fetch team/player rolling metrics."""

import csv
import json
import logging
import os
from pathlib import Path

from mcp_server.clients.fallback_data import get_fallback_team_players
from mcp_server.clients.football_api import FootballAPIClient

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _resolve_team_id(team_id: int | None, team_name: str | None) -> int | None:
    """Resolve a team_id from team_name if team_id is not provided."""
    if team_id and team_id > 0:
        return team_id
    if not team_name:
        return None

    teams_file = DATA_DIR / "worldcup2026.teams.csv"
    if not teams_file.exists():
        return None

    team_name_lower = team_name.lower().strip()
    with open(teams_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("name_en", "").lower() == team_name_lower:
                return int(row["id"])
    # Fuzzy match: check if team_name is contained in name
    with open(teams_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if team_name_lower in row.get("name_en", "").lower() or row.get("name_en", "").lower() in team_name_lower:
                return int(row["id"])
    return None


async def get_historical_trends(team_id: int = 0, team_name: str | None = None, player_id: int | None = None) -> str:
    """Fetch historical performance trends for a team and optionally a player.

    Args:
        team_id: Team ID (from schedule response or API-Football).
        team_name: Team name (alternative to team_id — will resolve automatically).
        player_id: Optional API-Football player ID for individual stats.

    Returns:
        JSON string with rolling performance metrics.
    """
    # Resolve team_id from team_name if needed
    resolved_id = _resolve_team_id(team_id, team_name)
    if not resolved_id:
        return json.dumps({"error": f"Could not resolve team: team_id={team_id}, team_name={team_name}"})
    team_id = resolved_id

    api_key = os.environ.get("FOOTBALL_API_KEY", "")
    result = {"team_id": team_id, "team_name": team_name, "player_id": player_id, "metrics": {}}

    if not api_key:
        # Return mock trend data for development
        result["metrics"] = _mock_team_metrics(team_id)
        if player_id:
            result["player_metrics"] = _mock_player_metrics(player_id)
        result["key_players"] = _get_key_players(team_id)
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
            # Include pre-tournament metadata from fallback
            if team_stats.get("qualification_form"):
                result["metrics"]["qualification_form"] = team_stats["qualification_form"]
            if team_stats.get("fifa_ranking"):
                result["metrics"]["fifa_ranking"] = team_stats["fifa_ranking"]
            if team_stats.get("world_cup_titles"):
                result["metrics"]["world_cup_titles"] = team_stats["world_cup_titles"]
            if team_stats.get("world_cup_finals"):
                result["metrics"]["world_cup_finals"] = team_stats["world_cup_finals"]
            if team_stats.get("key_strength"):
                result["metrics"]["key_strength"] = team_stats["key_strength"]

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

        # Always include key players from fallback data
        result["key_players"] = _get_key_players(team_id)

        await client.close()
    except Exception as e:
        logger.warning(f"API-Football trends call failed, using mock data: {e}")
        result["metrics"] = _mock_team_metrics(team_id)
        if player_id:
            result["player_metrics"] = _mock_player_metrics(player_id)
        result["key_players"] = _get_key_players(team_id)

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


def _get_key_players(team_id: int) -> list[dict]:
    """Get key players for a team from fallback data."""
    players = get_fallback_team_players(team_id)
    return [
        {
            "name": p["name"],
            "position": p.get("position", ""),
            "club": p.get("club", ""),
            "caps": p.get("caps", 0),
            "goals": p.get("goals", 0),
        }
        for p in players
    ]
