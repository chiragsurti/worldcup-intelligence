"""Integration tests for API-Football v3 client.

These tests make real HTTP calls to validate endpoint availability
and response schema conformance per the API-Football v3 documentation.

Run with:
    pytest tests/test_football_api_integration.py -v -s

Requires FOOTBALL_API_KEY environment variable to be set.
"""

import json
import os

import pytest
import pytest_asyncio

from mcp_server.clients.football_api import (
    FootballAPIClient,
    WORLD_CUP_LEAGUE_ID,
    WORLD_CUP_SEASON,
)

API_KEY = os.environ.get("FOOTBALL_API_KEY", "")

pytestmark = [
    pytest.mark.skipif(
        not API_KEY,
        reason="FOOTBALL_API_KEY environment variable not set",
    ),
    pytest.mark.asyncio,
]


def _print_section(title: str):
    """Print a visual separator for test output."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _print_json(label: str, data, max_items: int = 3):
    """Print JSON data with truncation for large lists."""
    if isinstance(data, list) and len(data) > max_items:
        print(f"\n  {label} ({len(data)} items, showing first {max_items}):")
        print(f"  {json.dumps(data[:max_items], indent=4, default=str)}")
    else:
        print(f"\n  {label}:")
        print(f"  {json.dumps(data, indent=4, default=str)}")


def _check_fields(data: dict, required_fields: list[str], context: str = "") -> list[str]:
    """Check for required fields and print status. Returns list of missing fields."""
    present = [f for f in required_fields if f in data]
    missing = [f for f in required_fields if f not in data]
    prefix = f"  [{context}] " if context else "  "
    print(f"{prefix}Present fields: {present}")
    if missing:
        print(f"{prefix}*** MISSING fields: {missing} ***")
    else:
        print(f"{prefix}All required fields present âœ“")
    return missing


@pytest_asyncio.fixture
async def client():
    """Create and teardown a real API client."""
    c = FootballAPIClient(api_key=API_KEY)
    yield c
    await c.close()


# ---------------------------------------------------------------------------
# /status â€” API health check (no quota cost)
# ---------------------------------------------------------------------------


async def test_api_status(client: FootballAPIClient):
    """Validate /status endpoint returns account info and quota details.

    Documented response fields:
    - account.firstname, account.lastname, account.email
    - subscription.plan, subscription.end
    - requests.current, requests.limit_day
    """
    _print_section("GET /status")
    data = await client._request("/status")

    print(f"  Response keys: {list(data.keys())}")
    assert "response" in data
    response = data["response"]
    _print_json("Full /status response", response)

    # Account info
    missing = _check_fields(response, ["account", "subscription", "requests"], "/status")
    assert not missing, f"Missing top-level fields: {missing}"

    missing = _check_fields(response["account"], ["firstname", "email"], "/status.account")
    assert not missing

    # Subscription
    missing = _check_fields(response["subscription"], ["plan", "end"], "/status.subscription")
    assert not missing

    # Requests quota
    missing = _check_fields(response["requests"], ["current", "limit_day"], "/status.requests")
    assert not missing
    print(f"  Quota: {response['requests']['current']}/{response['requests']['limit_day']} requests used today")


# ---------------------------------------------------------------------------
# /timezone â€” Timezones list
# ---------------------------------------------------------------------------


async def test_timezone_endpoint(client: FootballAPIClient):
    """Validate /timezone endpoint returns a list of timezone strings.

    Per docs: response is an array of timezone strings (e.g., "Europe/London").
    """
    _print_section("GET /timezone")
    data = await client._request("/timezone")

    assert "response" in data
    timezones = data["response"]
    print(f"  Total timezones returned: {len(timezones)}")
    _print_json("Sample timezones", timezones[:5])

    assert isinstance(timezones, list)
    assert len(timezones) > 0, "Expected at least one timezone"
    # Each entry should be a string like "Continent/City"
    non_strings = [tz for tz in timezones if not isinstance(tz, str)]
    if non_strings:
        print(f"  *** Non-string entries found: {non_strings[:5]} ***")
    assert all(isinstance(tz, str) for tz in timezones)
    assert any("/" in tz for tz in timezones)


# ---------------------------------------------------------------------------
# /countries â€” Available countries
# ---------------------------------------------------------------------------


async def test_countries_endpoint(client: FootballAPIClient):
    """Validate /countries endpoint returns country objects.

    Per docs each country object has: name, code, flag.
    """
    _print_section("GET /countries")
    data = await client._request("/countries")

    assert "response" in data
    countries = data["response"]
    print(f"  Total countries returned: {len(countries)}")
    assert isinstance(countries, list)
    assert len(countries) > 0, "Expected at least one country"

    _print_json("Sample countries", countries[:3])

    country = countries[0]
    missing = _check_fields(country, ["name", "code", "flag"], "/countries[0]")
    assert not missing, f"Missing fields in country object: {missing}"


# ---------------------------------------------------------------------------
# /leagues â€” Available leagues (validate World Cup league exists)
# ---------------------------------------------------------------------------


async def test_leagues_endpoint(client: FootballAPIClient):
    """Validate /leagues endpoint and confirm World Cup league is accessible.

    Per docs each league entry has: league (id, name, type, logo),
    country (name, code, flag), seasons[].
    """
    _print_section(f"GET /leagues?id={WORLD_CUP_LEAGUE_ID}")
    data = await client._request("/leagues", params={"id": WORLD_CUP_LEAGUE_ID})

    assert "response" in data
    leagues = data["response"]
    print(f"  Leagues returned: {len(leagues)}")
    assert isinstance(leagues, list)
    assert len(leagues) >= 1, f"Expected World Cup league (id={WORLD_CUP_LEAGUE_ID}) to exist"

    entry = leagues[0]
    print(f"  Entry keys: {list(entry.keys())}")

    # League object
    missing = _check_fields(entry, ["league", "country", "seasons"], "leagues[0]")
    assert not missing

    league_obj = entry["league"]
    _print_json("League object", league_obj)
    missing = _check_fields(league_obj, ["id", "name", "type", "logo"], "leagues[0].league")
    assert not missing
    assert entry["league"]["id"] == WORLD_CUP_LEAGUE_ID, (
        f"Expected league id={WORLD_CUP_LEAGUE_ID}, got {entry['league']['id']}"
    )

    # Country object
    country = entry["country"]
    _print_json("Country object", country)
    missing = _check_fields(country, ["name"], "leagues[0].country")
    assert not missing

    # Seasons array
    seasons = entry["seasons"]
    print(f"  Total seasons: {len(seasons)}")
    _print_json("Latest season", seasons[-1] if seasons else {})
    assert isinstance(seasons, list)
    assert len(seasons) > 0
    season = seasons[0]
    missing = _check_fields(season, ["year", "start", "end"], "leagues[0].seasons[0]")
    assert not missing


# ---------------------------------------------------------------------------
# /fixtures â€” Fixtures for World Cup
# ---------------------------------------------------------------------------


async def test_get_fixtures_response_schema(client: FootballAPIClient):
    """Validate /fixtures endpoint response schema.

    Per docs each fixture entry contains:
    - fixture (id, referee, timezone, date, timestamp, periods, venue, status)
    - league (id, name, country, logo, flag, season, round)
    - teams (home, away â€” each with id, name, logo, winner)
    - goals (home, away)
    - score (halftime, fulltime, extratime, penalty)
    """
    _print_section("GET /fixtures?date=2026-06-13")
    fixtures = await client.get_fixtures("2026-06-13")

    assert isinstance(fixtures, list)
    print(f"  Fixtures returned: {len(fixtures)}")

    if len(fixtures) == 0:
        print("  *** No fixtures found even with fallback â€” check data files ***")
        pytest.fail("No fixtures found for 2026-06-13 â€” neither API nor fallback returned data")

    source = "API" if fixtures[0].get("fixture", {}).get("timestamp") is not None else "FALLBACK"
    print(f"  Data source: {source}")

    fixture_entry = fixtures[0]
    print(f"  Entry top-level keys: {list(fixture_entry.keys())}")
    missing = _check_fields(fixture_entry, ["fixture", "league", "teams", "goals", "score"], "fixtures[0]")
    assert not missing

    # fixture object
    fx = fixture_entry["fixture"]
    _print_json("fixture object", fx)
    missing = _check_fields(fx, ["id", "date", "status"], "fixtures[0].fixture")
    assert not missing
    print(f"  Status keys: {list(fx['status'].keys())}")
    assert "short" in fx["status"] or "long" in fx["status"]

    # league object
    lg = fixture_entry["league"]
    _print_json("league object", lg)
    missing = _check_fields(lg, ["id", "name", "season", "round"], "fixtures[0].league")
    assert not missing

    # teams object
    teams = fixture_entry["teams"]
    _print_json("teams object", teams)
    missing = _check_fields(teams, ["home", "away"], "fixtures[0].teams")
    assert not missing
    missing = _check_fields(teams["home"], ["id", "name"], "fixtures[0].teams.home")
    assert not missing
    missing = _check_fields(teams["away"], ["id", "name"], "fixtures[0].teams.away")
    assert not missing
    print(f"  Match: {teams['home']['name']} vs {teams['away']['name']}")

    # goals object
    _print_json("goals object", fixture_entry["goals"])

    # score object
    _print_json("score object", fixture_entry["score"])


# ---------------------------------------------------------------------------
# /fixtures with a different date (tournament day 2)
# ---------------------------------------------------------------------------


async def test_get_fixtures_alternate_date(client: FootballAPIClient):
    """Validate /fixtures with date=2026-06-14 returns fixtures."""
    _print_section(f"GET /fixtures?date=2026-06-14&league={WORLD_CUP_LEAGUE_ID}&season={WORLD_CUP_SEASON}")
    fixtures = await client.get_fixtures("2026-06-14")

    assert isinstance(fixtures, list)
    print(f"  Fixtures returned: {len(fixtures)}")

    if len(fixtures) > 0:
        source = "API" if fixtures[0].get("fixture", {}).get("timestamp") is not None else "FALLBACK"
        print(f"  Data source: {source}")
        for i, fx in enumerate(fixtures):
            teams = fx.get("teams", {})
            home = teams.get("home", {}).get("name", "?")
            away = teams.get("away", {}).get("name", "?")
            date = fx.get("fixture", {}).get("date", "?")
            print(f"    [{i+1}] {home} vs {away} â€” {date}")
        assert "fixture" in fixtures[0]
        assert "teams" in fixtures[0]
    else:
        print("  *** No fixtures found for 2026-06-14 â€” check data files ***")


# ---------------------------------------------------------------------------
# /standings â€” League standings
# ---------------------------------------------------------------------------


async def test_get_standings_response_schema(client: FootballAPIClient):
    """Validate /standings endpoint response schema.

    Per docs: response[].league.standings[][] where each standing has:
    - rank, team (id, name, logo), points, goalsDiff, group, form, status
    - all/home/away (played, win, draw, lose, goals.for, goals.against)
    """
    _print_section(f"GET /standings?league={WORLD_CUP_LEAGUE_ID}&season={WORLD_CUP_SEASON}")
    standings = await client.get_standings()

    assert isinstance(standings, list)
    print(f"  Standings entries returned: {len(standings)}")

    if len(standings) == 0:
        print("  *** No standings data even with fallback â€” check data files ***")
        pytest.fail("No standings data â€” neither API nor fallback returned data")

    entry = standings[0]
    print(f"  Entry keys: {list(entry.keys())}")
    assert "league" in entry
    assert "standings" in entry["league"]

    standings_groups = entry["league"]["standings"]
    print(f"  Number of groups: {len(standings_groups)}")
    assert isinstance(standings_groups, list)
    assert len(standings_groups) > 0

    group = standings_groups[0]
    print(f"  Teams in first group: {len(group)}")
    assert isinstance(group, list)
    assert len(group) > 0

    team_standing = group[0]
    _print_json("First team standing", team_standing)
    missing = _check_fields(
        team_standing,
        ["rank", "team", "points", "goalsDiff", "all"],
        "standings.group[0]",
    )
    assert not missing

    missing = _check_fields(team_standing["team"], ["id", "name"], "standings.team")
    assert not missing

    all_stats = team_standing["all"]
    missing = _check_fields(all_stats, ["played", "win", "draw", "lose", "goals"], "standings.all")
    assert not missing
    print(f"  Team: {team_standing['team']['name']} | Rank: {team_standing['rank']} | Pts: {team_standing['points']}")


# ---------------------------------------------------------------------------
# /teams/statistics â€” Team statistics
# ---------------------------------------------------------------------------


async def test_get_team_stats_response_schema(client: FootballAPIClient):
    """Validate /teams/statistics endpoint response schema.

    Per docs: response contains:
    - league (id, name, country, logo, flag, season)
    - team (id, name, logo)
    - form, fixtures, goals, biggest, clean_sheet, failed_to_score,
      penalty, lineups, cards
    """
    _print_section("GET /teams/statistics?team=13 (United States)")
    # Team ID 13 = USA in our local data (has match data: 4-1 vs Paraguay)
    stats = await client.get_team_stats(team_id=13)

    if not stats:
        print("  *** No team stats returned (empty response) ***")
        pytest.skip("No team stats available yet for World Cup 2026")

    print(f"  Response keys: {list(stats.keys())}")
    expected_top = ["league", "team", "form", "fixtures", "goals", "clean_sheet", "penalty"]
    missing = _check_fields(stats, expected_top, "team_stats")
    assert not missing

    # League info
    _print_json("league", stats["league"])
    missing = _check_fields(stats["league"], ["id", "name", "season"], "team_stats.league")
    assert not missing

    # Team info
    _print_json("team", stats["team"])
    missing = _check_fields(stats["team"], ["id", "name"], "team_stats.team")
    assert not missing
    print(f"  Team: {stats['team']['name']} | Form: {stats.get('form', 'N/A')}")

    # Fixtures breakdown
    _print_json("fixtures", stats["fixtures"])
    missing = _check_fields(stats["fixtures"], ["played", "wins", "draws", "loses"], "team_stats.fixtures")
    assert not missing

    # Goals
    _print_json("goals", stats["goals"])
    missing = _check_fields(stats["goals"], ["for", "against"], "team_stats.goals")
    assert not missing


# ---------------------------------------------------------------------------
# /players â€” Player statistics
# ---------------------------------------------------------------------------


async def test_get_player_stats_response_schema(client: FootballAPIClient):
    """Validate /players endpoint response schema.

    Per docs each entry contains:
    - player (id, name, firstname, lastname, age, birth, nationality, height, weight, photo)
    - statistics[] (team, league, games, substitutes, shots, goals, passes,
      tackles, duels, dribbles, fouls, cards, penalty)
    """
    _print_section("GET /players?id=1 (First player in fallback data)")
    # Player ID 1 = first player in our local data (Guillermo Ochoa)
    players = await client.get_player_stats(player_id=1)

    assert isinstance(players, list)
    print(f"  Player entries returned: {len(players)}")

    if len(players) == 0:
        print("  *** No player stats available for this player/season ***")
        pytest.skip("No player stats available for player_id=1 in World Cup 2026 season")

    entry = players[0]
    print(f"  Entry keys: {list(entry.keys())}")
    missing = _check_fields(entry, ["player", "statistics"], "players[0]")
    assert not missing

    # Player object
    player = entry["player"]
    _print_json("player object", player)
    missing = _check_fields(
        player,
        ["id", "name", "firstname", "lastname", "nationality", "photo"],
        "players[0].player",
    )
    assert not missing
    print(f"  Player: {player['firstname']} {player['lastname']} ({player['nationality']})")

    # Statistics array
    stats_list = entry["statistics"]
    print(f"  Statistics entries: {len(stats_list)}")
    assert isinstance(stats_list, list)
    assert len(stats_list) > 0

    stat = stats_list[0]
    _print_json("First statistics entry", stat)
    missing = _check_fields(stat, ["team", "league", "games", "goals", "passes"], "players[0].statistics[0]")
    assert not missing
    missing = _check_fields(stat["team"], ["id", "name"], "players[0].statistics[0].team")
    assert not missing


# ---------------------------------------------------------------------------
# /teams â€” Team information lookup
# ---------------------------------------------------------------------------


async def test_teams_endpoint(client: FootballAPIClient):
    """Validate /teams endpoint response schema.

    Per docs: response[].team (id, name, code, country, founded, logo)
    and response[].venue (id, name, address, city, capacity, image).
    """
    _print_section("GET /teams?id=26 (Brazil)")
    data = await client._request("/teams", params={"id": 26})

    assert "response" in data
    teams = data["response"]
    print(f"  Teams returned: {len(teams)}")
    assert isinstance(teams, list)
    assert len(teams) >= 1

    entry = teams[0]
    print(f"  Entry keys: {list(entry.keys())}")
    missing = _check_fields(entry, ["team", "venue"], "teams[0]")
    assert not missing

    team = entry["team"]
    _print_json("team object", team)
    missing = _check_fields(team, ["id", "name", "country", "logo"], "teams[0].team")
    assert not missing
    print(f"  Team: {team['name']} ({team['country']})")

    venue = entry["venue"]
    _print_json("venue object", venue)
    missing = _check_fields(venue, ["id", "name", "city", "capacity"], "teams[0].venue")
    assert not missing
    print(f"  Venue: {venue['name']}, {venue['city']} (capacity: {venue['capacity']})")


# # ---------------------------------------------------------------------------
# # Response envelope validation (errors/paging)
# # ---------------------------------------------------------------------------


# async def test_response_envelope_structure(client: FootballAPIClient):
#     """Validate that API responses follow the documented envelope format.

#     Per docs every response has: get, parameters, errors, results, paging, response.
#     """
#     _print_section("Response Envelope Validation (/timezone)")
#     data = await client._request("/timezone")

#     expected_envelope = ["get", "parameters", "errors", "results", "paging", "response"]
#     print(f"  Actual response keys: {list(data.keys())}")
#     missing = _check_fields(data, expected_envelope, "envelope")
#     assert not missing

#     # Paging structure
#     paging = data["paging"]
#     _print_json("paging", paging)
#     missing = _check_fields(paging, ["current", "total"], "envelope.paging")
#     assert not missing

#     print(f"  get: {data['get']}")
#     print(f"  results: {data['results']}")
#     print(f"  errors: {data['errors']}")
#     print(f"  paging: current={paging['current']}, total={paging['total']}")


# ---------------------------------------------------------------------------
# Error handling â€” invalid parameters
# ---------------------------------------------------------------------------


async def test_invalid_league_returns_empty(client: FootballAPIClient):
    """Validate that querying a non-existent league returns empty results, not an error."""
    _print_section("GET /standings?league=99999 (invalid)")
    data = await client._request("/standings", params={"league": 99999, "season": 2026})

    assert "response" in data
    print(f"  response: {data['response']}")
    print(f"  results: {data.get('results')}")
    print(f"  errors: {data.get('errors')}")
    assert data["response"] == [] or data["results"] == 0
    print("  Confirmed: invalid league returns empty results âœ“")


# # ---------------------------------------------------------------------------
# # Rate-limit headers are present
# # ---------------------------------------------------------------------------


# async def test_rate_limit_headers_present(client: FootballAPIClient):
#     """Validate that API responses include rate-limit headers.

#     Per docs: x-ratelimit-requests-limit, x-ratelimit-requests-remaining.
#     """
#     _print_section("Rate-Limit Headers Check")
#     http_client = await client._get_client()
#     response = await http_client.get("/timezone")
#     response.raise_for_status()

#     print(f"  Response status: {response.status_code}")
#     rate_headers = {k: v for k, v in response.headers.items() if "ratelimit" in k.lower()}
#     print(f"  Rate-limit headers found: {rate_headers}")

#     if not rate_headers:
#         print("  *** WARNING: No rate-limit headers found in response ***")
#         print(f"  All headers: {dict(response.headers)}")

#     assert "x-ratelimit-requests-limit" in response.headers or "x-ratelimit-remaining" in response.headers
#     print("  Rate-limit headers present âœ“")
