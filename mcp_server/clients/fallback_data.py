"""Fallback data provider using local CSV/JSON files.

When the API-Football v3 endpoints return empty results (e.g. season data
not yet available), this module provides equivalent data from the local
data/ directory as a fallback.
"""

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_csv(filename: str) -> list[dict[str, str]]:
    """Load a CSV file from the data directory."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        logger.warning(f"Fallback data file not found: {filepath}")
        return []
    with open(filepath, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_json(filename: str) -> Any:
    """Load a JSON file from the data directory."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        logger.warning(f"Fallback data file not found: {filepath}")
        return []
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def _get_teams_lookup() -> dict[int, dict]:
    """Build a team_id -> team_info lookup from teams CSV."""
    rows = _load_csv("worldcup2026.teams.csv")
    lookup = {}
    for row in rows:
        team_id = int(row["id"])
        lookup[team_id] = {
            "id": team_id,
            "name": row["name_en"],
            "code": row.get("fifa_code", ""),
            "country": row["name_en"],
            "logo": row.get("flag", ""),
            "flag": row.get("flag", ""),
            "group": row.get("groups", ""),
        }
    return lookup


def _get_stadia_lookup() -> dict[int, dict]:
    """Build a stadium_id -> venue_info lookup from stadia CSV."""
    rows = _load_csv("worldcup2026.stadia.csv")
    lookup = {}
    for row in rows:
        stadium_id = int(row["id"])
        lookup[stadium_id] = {
            "id": stadium_id,
            "name": row["name_en"],
            "city": row["city_en"],
            "country": row["country_en"],
            "capacity": int(row["capacity"]) if row.get("capacity") else None,
        }
    return lookup


def get_fallback_fixtures(date: str) -> list[dict]:
    """Get fixtures for a specific date from local CSV data.

    Args:
        date: Date string in YYYY-MM-DD format.

    Returns:
        List of fixture dicts matching API-Football v3 response schema.
    """
    games = _load_csv("worldcup2026.games.csv")
    teams = _get_teams_lookup()
    stadia = _get_stadia_lookup()

    # Convert date from YYYY-MM-DD to MM/DD/YYYY prefix for matching local_date
    # local_date format in CSV: "06/11/2026 13:00"
    parts = date.split("-")  # ["2026", "06", "11"]
    if len(parts) == 3:
        date_prefix = f"{parts[1]}/{parts[2]}/{parts[0]}"
    else:
        return []

    results = []
    for game in games:
        local_date = game.get("local_date", "")
        if not local_date.startswith(date_prefix):
            continue

        home_id = int(game["home_team_id"])
        away_id = int(game["away_team_id"])
        home_team = teams.get(home_id, {"id": home_id, "name": f"Team {home_id}", "logo": ""})
        away_team = teams.get(away_id, {"id": away_id, "name": f"Team {away_id}", "logo": ""})
        stadium_id = int(game["stadium_id"]) if game.get("stadium_id") else None
        venue = stadia.get(stadium_id, {}) if stadium_id else {}

        finished = game.get("finished", "FALSE").upper() == "TRUE"
        home_score = int(game["home_score"]) if game.get("home_score") and game["home_score"] != "null" else None
        away_score = int(game["away_score"]) if game.get("away_score") and game["away_score"] != "null" else None

        fixture_entry = {
            "fixture": {
                "id": int(game["id"]),
                "referee": None,
                "timezone": "UTC",
                "date": game.get("date", f"{date}T00:00:00+00:00"),
                "timestamp": None,
                "periods": {"first": None, "second": None},
                "venue": {
                    "id": venue.get("id"),
                    "name": venue.get("name", ""),
                    "city": venue.get("city", ""),
                },
                "status": {
                    "long": "Match Finished" if finished else "Not Started",
                    "short": "FT" if finished else "NS",
                    "elapsed": int(game["time_elapsed"]) if game.get("time_elapsed", "").isdigit() else None,
                },
            },
            "league": {
                "id": 1,
                "name": "World Cup",
                "country": "World",
                "logo": "https://media.api-sports.io/football/leagues/1.png",
                "flag": None,
                "season": 2026,
                "round": f"Group {game.get('group', '?')} - {game.get('matchday', '1')}",
            },
            "teams": {
                "home": {
                    "id": home_team["id"],
                    "name": home_team["name"],
                    "logo": home_team.get("logo", ""),
                    "winner": (home_score > away_score) if home_score is not None and away_score is not None else None,
                },
                "away": {
                    "id": away_team["id"],
                    "name": away_team["name"],
                    "logo": away_team.get("logo", ""),
                    "winner": (away_score > home_score) if home_score is not None and away_score is not None else None,
                },
            },
            "goals": {
                "home": home_score,
                "away": away_score,
            },
            "score": {
                "halftime": {"home": None, "away": None},
                "fulltime": {"home": home_score, "away": away_score},
                "extratime": {"home": None, "away": None},
                "penalty": {"home": None, "away": None},
            },
        }
        results.append(fixture_entry)

    logger.info(f"Fallback: returned {len(results)} fixtures for date {date}")
    return results


def get_fallback_standings() -> list[dict]:
    """Get standings from local JSON/CSV data.

    Returns:
        List matching API-Football v3 /standings response schema.
    """
    groups_data = _load_json("worldcup2026.groups.json")
    teams = _get_teams_lookup()

    standings_groups = []
    for group in groups_data:
        group_name = group.get("name", "?")
        group_standings = []

        for idx, team_entry in enumerate(group.get("teams", []), start=1):
            team_id = int(team_entry["team_id"])
            team_info = teams.get(team_id, {"id": team_id, "name": f"Team {team_id}", "logo": ""})

            mp = int(team_entry.get("mp", 0))
            wins = int(team_entry.get("w", 0))
            draws = int(team_entry.get("d", 0))
            losses = int(team_entry.get("l", 0))
            gf = int(team_entry.get("gf", 0))
            ga = int(team_entry.get("ga", 0))
            gd = int(team_entry.get("gd", 0))
            pts = int(team_entry.get("pts", 0))

            group_standings.append({
                "rank": idx,
                "team": {
                    "id": team_info["id"],
                    "name": team_info["name"],
                    "logo": team_info.get("logo", ""),
                },
                "points": pts,
                "goalsDiff": gd,
                "group": f"Group {group_name}",
                "form": None,
                "status": "same",
                "description": None,
                "all": {
                    "played": mp,
                    "win": wins,
                    "draw": draws,
                    "lose": losses,
                    "goals": {"for": gf, "against": ga},
                },
                "home": {
                    "played": 0, "win": 0, "draw": 0, "lose": 0,
                    "goals": {"for": 0, "against": 0},
                },
                "away": {
                    "played": 0, "win": 0, "draw": 0, "lose": 0,
                    "goals": {"for": 0, "against": 0},
                },
            })

        # Sort by points desc, then goal difference desc
        group_standings.sort(key=lambda x: (-x["points"], -x["goalsDiff"]))
        for rank, entry in enumerate(group_standings, start=1):
            entry["rank"] = rank

        standings_groups.append(group_standings)

    if not standings_groups:
        return []

    return [{
        "league": {
            "id": 1,
            "name": "World Cup",
            "country": "World",
            "logo": "https://media.api-sports.io/football/leagues/1.png",
            "flag": None,
            "season": 2026,
            "standings": standings_groups,
        }
    }]


def get_fallback_team_info(team_id: int) -> list[dict]:
    """Get team info from local CSV data.

    Returns:
        List matching API-Football v3 /teams response schema.
    """
    teams = _get_teams_lookup()
    team = teams.get(team_id)
    if not team:
        return []

    return [{
        "team": {
            "id": team["id"],
            "name": team["name"],
            "code": team.get("code", ""),
            "country": team.get("country", ""),
            "founded": None,
            "national": True,
            "logo": team.get("logo", ""),
        },
        "venue": {
            "id": None,
            "name": None,
            "address": None,
            "city": None,
            "capacity": None,
            "surface": None,
            "image": None,
        },
    }]


def get_fallback_team_stats(team_id: int) -> dict:
    """Get team statistics from local JSON data.

    Args:
        team_id: Numeric team ID matching worldcup2026.teams.csv.

    Returns:
        Dict matching API-Football v3 /teams/statistics response schema.
    """
    team_stats_data = _load_json("worldcup2026.team_stats.json")
    teams = _get_teams_lookup()
    team_info = teams.get(team_id)

    if not team_info:
        return {}

    # Find stats for this team
    stats = None
    for entry in team_stats_data:
        if entry.get("team_id") == team_id:
            stats = entry
            break

    if not stats:
        # Team exists but has no match data yet — return zeroed stats
        stats = {
            "matches_played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
            "form": "",
        }

    mp = stats.get("matches_played", 0)
    wins = stats.get("wins", 0)
    draws = stats.get("draws", 0)
    losses = stats.get("losses", 0)
    gf = stats.get("goals_for", 0)
    ga = stats.get("goals_against", 0)
    form = stats.get("form", "") or stats.get("qualification_form", "")

    result = {
        "league": {
            "id": 1,
            "name": "World Cup",
            "country": "World",
            "logo": "https://media.api-sports.io/football/leagues/1.png",
            "flag": None,
            "season": 2026,
        },
        "team": {
            "id": team_info["id"],
            "name": team_info["name"],
            "logo": team_info.get("logo", ""),
        },
        "form": form,
        "fixtures": {
            "played": {"home": 0, "away": 0, "total": mp},
            "wins": {"home": 0, "away": 0, "total": wins},
            "draws": {"home": 0, "away": 0, "total": draws},
            "loses": {"home": 0, "away": 0, "total": losses},
        },
        "goals": {
            "for": {
                "total": {"home": 0, "away": 0, "total": gf},
                "average": {"home": "0.0", "away": "0.0", "total": f"{gf/mp:.1f}" if mp > 0 else "0.0"},
            },
            "against": {
                "total": {"home": 0, "away": 0, "total": ga},
                "average": {"home": "0.0", "away": "0.0", "total": f"{ga/mp:.1f}" if mp > 0 else "0.0"},
            },
        },
        "clean_sheet": {"home": 0, "away": 0, "total": 1 if ga == 0 and mp > 0 else 0},
        "penalty": {
            "scored": {"total": 0, "percentage": "0%"},
            "missed": {"total": 0, "percentage": "0%"},
            "total": 0,
        },
    }

    # Add pre-tournament metadata if available
    if stats.get("qualification_form"):
        result["qualification_form"] = stats["qualification_form"]
    if stats.get("fifa_ranking"):
        result["fifa_ranking"] = stats["fifa_ranking"]
    if stats.get("world_cup_titles"):
        result["world_cup_titles"] = stats["world_cup_titles"]
    if stats.get("world_cup_finals"):
        result["world_cup_finals"] = stats["world_cup_finals"]
    if stats.get("key_strength"):
        result["key_strength"] = stats["key_strength"]

    return result


def get_fallback_team_players(team_id: int) -> list[dict]:
    """Get key players for a team from local JSON data.

    Args:
        team_id: Numeric team ID matching worldcup2026.teams.csv.

    Returns:
        List of player dicts with name, position, caps, goals, club.
    """
    players_data = _load_json("worldcup2026.players.json")
    if not players_data:
        return []

    team_players = [p for p in players_data if p.get("team_id") == team_id]
    # Sort by goals desc, then caps desc to surface star players first
    team_players.sort(key=lambda p: (-p.get("goals", 0), -p.get("caps", 0)))
    return team_players


def get_fallback_player_stats(player_id: int) -> list[dict]:
    """Get player statistics from local JSON data.

    Args:
        player_id: Numeric player ID. Since Wikipedia data doesn't have
        API-Football IDs, we use a sequential ID based on the players list.

    Returns:
        List matching API-Football v3 /players response schema.
    """
    players_data = _load_json("worldcup2026.players.json")
    teams = _get_teams_lookup()

    if not players_data:
        return []

    # Find player by sequential ID (1-indexed)
    if player_id < 1 or player_id > len(players_data):
        return []

    player = players_data[player_id - 1]
    team_id = player.get("team_id")
    team_info = teams.get(team_id, {"id": team_id, "name": player.get("team", ""), "logo": ""})

    # Map position codes to full names
    position_map = {"GK": "Goalkeeper", "DF": "Defender", "MF": "Midfielder", "FW": "Attacker"}

    return [{
        "player": {
            "id": player_id,
            "name": player["name"],
            "firstname": player["name"].split()[0] if " " in player["name"] else player["name"],
            "lastname": " ".join(player["name"].split()[1:]) if " " in player["name"] else "",
            "age": player.get("age"),
            "birth": {"date": player.get("date_of_birth", ""), "place": None, "country": player.get("team", "")},
            "nationality": player.get("team", ""),
            "height": None,
            "weight": None,
            "injured": False,
            "photo": None,
        },
        "statistics": [{
            "team": {
                "id": team_info["id"],
                "name": team_info["name"],
                "logo": team_info.get("logo", ""),
            },
            "league": {
                "id": 1,
                "name": "World Cup",
                "country": "World",
                "logo": "https://media.api-sports.io/football/leagues/1.png",
                "flag": None,
                "season": 2026,
            },
            "games": {
                "appearences": player.get("caps", 0),
                "lineups": player.get("caps", 0),
                "minutes": None,
                "number": None,
                "position": position_map.get(player.get("position", ""), player.get("position", "")),
                "rating": None,
                "captain": False,
            },
            "substitutes": {"in": 0, "out": 0, "bench": 0},
            "shots": {"total": None, "on": None},
            "goals": {
                "total": player.get("goals", 0),
                "conceded": None,
                "assists": None,
                "saves": None,
            },
            "passes": {"total": None, "key": None, "accuracy": None},
            "tackles": {"total": None, "blocks": None, "interceptions": None},
            "duels": {"total": None, "won": None},
            "dribbles": {"attempts": None, "success": None, "past": None},
            "fouls": {"drawn": None, "committed": None},
            "cards": {"yellow": 0, "yellowred": 0, "red": 0},
            "penalty": {"won": None, "committed": None, "scored": 0, "missed": 0, "saved": None},
        }],
    }]
