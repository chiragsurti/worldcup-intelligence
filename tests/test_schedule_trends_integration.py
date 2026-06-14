"""Integration tests for 2026-06-14 match schedule and historical trends.

Validates that tool_get_schedule and tool_get_historical_trends return complete
data for all June 14 matches, specifically Netherlands vs Japan (match 11).
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db.database import init_db


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Create a temporary SQLite database for each test."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    import shared.db.database as db_mod
    db_mod._engine = None
    db_mod._SessionLocal = None

    init_db(db_url)
    yield db_url


# ─── tool_get_schedule tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_schedule_june14_returns_4_matches(setup_test_db, monkeypatch):
    """Schedule for 2026-06-14 should return exactly 4 fixtures."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.schedule import get_schedule

    result = await get_schedule("2026-06-14")
    fixtures = json.loads(result)

    assert len(fixtures) == 4, f"Expected 4 fixtures, got {len(fixtures)}"


@pytest.mark.asyncio
async def test_schedule_june14_netherlands_japan_fixture(setup_test_db, monkeypatch):
    """Netherlands vs Japan fixture has correct team IDs, venue, and league."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.schedule import get_schedule

    result = await get_schedule("2026-06-14")
    fixtures = json.loads(result)

    # Find Netherlands vs Japan
    ned_jpn = [f for f in fixtures if f["home_team"] == "Netherlands" and f["away_team"] == "Japan"]
    assert len(ned_jpn) == 1, f"Netherlands vs Japan not found. Fixtures: {[f['home_team'] + ' vs ' + f['away_team'] for f in fixtures]}"

    match = ned_jpn[0]
    assert match["home_team_id"] == 21, f"Expected home_team_id=21, got {match['home_team_id']}"
    assert match["away_team_id"] == 22, f"Expected away_team_id=22, got {match['away_team_id']}"
    assert match["venue"], "Venue should not be empty"
    assert match["league"], "League should not be empty"
    assert "World Cup" in match["league"], f"League should contain 'World Cup', got: {match['league']}"


@pytest.mark.asyncio
async def test_schedule_june14_all_fixtures_have_required_fields(setup_test_db, monkeypatch):
    """All fixtures must have match_id, teams, venue, league, and team IDs."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.schedule import get_schedule

    result = await get_schedule("2026-06-14")
    fixtures = json.loads(result)

    required_fields = ["match_id", "home_team", "away_team", "home_team_id", "away_team_id", "venue", "league"]

    for fix in fixtures:
        for field in required_fields:
            assert field in fix, f"Missing field '{field}' in fixture: {fix.get('home_team', '?')} vs {fix.get('away_team', '?')}"
            assert fix[field], f"Field '{field}' is empty in fixture: {fix['home_team']} vs {fix['away_team']}"


@pytest.mark.asyncio
async def test_schedule_june14_fixture_has_group_info(setup_test_db, monkeypatch):
    """Fixtures should have group/round info in raw_data."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.schedule import get_schedule

    result = await get_schedule("2026-06-14")
    fixtures = json.loads(result)

    ned_jpn = [f for f in fixtures if f["home_team"] == "Netherlands"][0]

    # Check raw_data has league round info
    raw = ned_jpn.get("raw_data", {})
    if isinstance(raw, str):
        raw = json.loads(raw)

    league_info = raw.get("league", {})
    assert league_info.get("round"), f"Missing round in raw_data.league: {league_info}"
    assert "Group F" in league_info["round"], f"Expected 'Group F' in round, got: {league_info['round']}"


# ─── tool_get_historical_trends tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_trends_netherlands_has_form_and_ranking(setup_test_db, monkeypatch):
    """Netherlands (team_id=21) should have qualification form and FIFA ranking."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.trends import get_historical_trends

    result = await get_historical_trends(team_id=21)
    data = json.loads(result)

    metrics = data.get("metrics", {})
    assert metrics.get("form"), f"Netherlands should have form data, got: {metrics}"
    assert len(metrics["form"]) >= 5, f"Form should be at least 5 chars, got: {metrics['form']}"
    assert metrics.get("fifa_ranking"), f"Netherlands should have FIFA ranking, got: {metrics}"
    assert metrics["fifa_ranking"] > 0, f"FIFA ranking should be > 0, got: {metrics['fifa_ranking']}"


@pytest.mark.asyncio
async def test_trends_japan_has_form_and_ranking(setup_test_db, monkeypatch):
    """Japan (team_id=22) should have qualification form and FIFA ranking."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.trends import get_historical_trends

    result = await get_historical_trends(team_id=22)
    data = json.loads(result)

    metrics = data.get("metrics", {})
    assert metrics.get("form"), f"Japan should have form data, got: {metrics}"
    assert metrics.get("fifa_ranking"), f"Japan should have FIFA ranking, got: {metrics}"
    assert metrics.get("key_strength"), f"Japan should have key_strength, got: {metrics}"


@pytest.mark.asyncio
async def test_trends_netherlands_has_key_players(setup_test_db, monkeypatch):
    """Netherlands (team_id=21) should return key players with goals/caps."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.trends import get_historical_trends

    result = await get_historical_trends(team_id=21)
    data = json.loads(result)

    key_players = data.get("key_players", [])
    assert len(key_players) >= 3, f"Netherlands should have >=3 key players, got {len(key_players)}"

    # Check star player data
    star = key_players[0]
    assert star.get("name"), "Star player should have a name"
    assert star.get("position"), "Star player should have a position"
    assert star.get("goals", 0) > 0 or star.get("caps", 0) > 0, (
        f"Star player should have goals or caps: {star}"
    )

    # Verify known players are present
    player_names = [p["name"] for p in key_players]
    assert any("Depay" in n or "Gakpo" in n or "van Dijk" in n for n in player_names), (
        f"Expected a known Netherlands player, got: {player_names}"
    )


@pytest.mark.asyncio
async def test_trends_japan_has_key_players(setup_test_db, monkeypatch):
    """Japan (team_id=22) should return key players with goals/caps."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.trends import get_historical_trends

    result = await get_historical_trends(team_id=22)
    data = json.loads(result)

    key_players = data.get("key_players", [])
    assert len(key_players) >= 3, f"Japan should have >=3 key players, got {len(key_players)}"

    # Verify known players
    player_names = [p["name"] for p in key_players]
    assert any("Kubo" in n or "Mitoma" in n or "Kamada" in n for n in player_names), (
        f"Expected a known Japan player, got: {player_names}"
    )


@pytest.mark.asyncio
async def test_trends_resolves_team_by_name(setup_test_db, monkeypatch):
    """get_historical_trends should resolve team_id from team_name."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.trends import get_historical_trends

    result = await get_historical_trends(team_name="Netherlands")
    data = json.loads(result)

    assert "error" not in data, f"Should resolve 'Netherlands', got error: {data}"
    assert data.get("team_id") == 21, f"Should resolve to team_id=21, got: {data.get('team_id')}"
    assert data.get("key_players"), "Should have key_players after name resolution"


@pytest.mark.asyncio
async def test_trends_netherlands_world_cup_finals(setup_test_db, monkeypatch):
    """Netherlands should have world_cup_finals = 3."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.trends import get_historical_trends

    result = await get_historical_trends(team_id=21)
    data = json.loads(result)

    metrics = data.get("metrics", {})
    assert metrics.get("world_cup_finals") == 3, (
        f"Netherlands should have 3 World Cup finals, got: {metrics.get('world_cup_finals')}"
    )


@pytest.mark.asyncio
async def test_trends_all_june14_teams_have_data(setup_test_db, monkeypatch):
    """All teams playing on June 14 should have non-empty trend data."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.trends import get_historical_trends

    # June 14 teams: Ivory Coast(19), Ecuador(20), Germany(17), Curaçao(18),
    # Netherlands(21), Japan(22), UEFA Path B(23), Tunisia(24)
    teams = {
        17: "Germany",
        18: "Curaçao",
        19: "Ivory Coast",
        20: "Ecuador",
        21: "Netherlands",
        22: "Japan",
        24: "Tunisia",
    }

    for team_id, team_name in teams.items():
        result = await get_historical_trends(team_id=team_id)
        data = json.loads(result)

        assert "error" not in data, f"{team_name} (id={team_id}) returned error: {data}"
        metrics = data.get("metrics", {})
        assert metrics.get("form"), f"{team_name} missing form data"
        assert metrics.get("fifa_ranking"), f"{team_name} missing FIFA ranking"
        assert metrics.get("key_strength"), f"{team_name} missing key_strength"

        key_players = data.get("key_players", [])
        assert len(key_players) >= 1, f"{team_name} has no key players"


# ─── End-to-end: schedule + trends combined ─────────────────────────────────


@pytest.mark.asyncio
async def test_e2e_schedule_then_trends_for_netherlands_japan(setup_test_db, monkeypatch):
    """End-to-end: fetch schedule, then get trends for Netherlands vs Japan teams."""
    monkeypatch.setenv("FOOTBALL_API_KEY", os.environ.get("FOOTBALL_API_KEY", "test"))

    from mcp_server.tools.schedule import get_schedule
    from mcp_server.tools.trends import get_historical_trends

    # Step 1: Get schedule
    schedule_result = await get_schedule("2026-06-14")
    fixtures = json.loads(schedule_result)
    ned_jpn = [f for f in fixtures if f["home_team"] == "Netherlands"][0]

    # Step 2: Get trends using team_ids from schedule
    home_id = ned_jpn["home_team_id"]
    away_id = ned_jpn["away_team_id"]

    home_trends = json.loads(await get_historical_trends(team_id=home_id))
    away_trends = json.loads(await get_historical_trends(team_id=away_id))

    # Verify complete data for Scribe agent
    assert home_trends["key_players"], "Netherlands key_players empty"
    assert away_trends["key_players"], "Japan key_players empty"
    assert home_trends["metrics"]["form"], "Netherlands form empty"
    assert away_trends["metrics"]["form"], "Japan form empty"
    assert home_trends["metrics"]["key_strength"], "Netherlands key_strength empty"
    assert away_trends["metrics"]["key_strength"], "Japan key_strength empty"

    # Verify the schedule has venue/league for Scribe
    assert ned_jpn["venue"], "Venue empty for Netherlands vs Japan"
    assert "World Cup" in ned_jpn["league"], f"League should be World Cup, got: {ned_jpn['league']}"
