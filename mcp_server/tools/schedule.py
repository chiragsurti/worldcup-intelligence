"""MCP Tool: get_schedule — fetch and persist daily fixtures."""

import json
import logging
import os
from datetime import date, datetime

from shared.db.database import get_session
from shared.db.models import Fixture

from mcp_server.clients.football_api import FootballAPIClient

logger = logging.getLogger(__name__)

# Seed data fallback for development / when API-Football has no WC2026 data yet
SEED_FIXTURES = [
    {
        "match_id": "wc2026-001",
        "match_date": "2026-06-11",
        "home_team": "Mexico",
        "away_team": "Colombia",
        "venue": "Estadio Azteca, Mexico City",
        "league": "FIFA World Cup 2026",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-002",
        "match_date": "2026-06-11",
        "home_team": "USA",
        "away_team": "Morocco",
        "venue": "SoFi Stadium, Los Angeles",
        "league": "FIFA World Cup 2026",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-003",
        "match_date": "2026-06-12",
        "home_team": "Brazil",
        "away_team": "Serbia",
        "venue": "MetLife Stadium, New York",
        "league": "FIFA World Cup 2026",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-004",
        "match_date": "2026-06-12",
        "home_team": "England",
        "away_team": "Japan",
        "venue": "AT&T Stadium, Dallas",
        "league": "FIFA World Cup 2026",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-005",
        "match_date": "2026-06-13",
        "home_team": "Argentina",
        "away_team": "Nigeria",
        "venue": "Hard Rock Stadium, Miami",
        "league": "FIFA World Cup 2026",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-006",
        "match_date": "2026-06-13",
        "home_team": "France",
        "away_team": "Australia",
        "venue": "BMO Stadium, Toronto",
        "league": "FIFA World Cup 2026",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-007",
        "match_date": "2026-06-14",
        "home_team": "Germany",
        "away_team": "Curaçao",
        "venue": "Lincoln Financial Field, Philadelphia",
        "league": "FIFA World Cup 2026",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-008",
        "match_date": "2026-06-14",
        "home_team": "Ivory Coast",
        "away_team": "Ecuador",
        "venue": "Gillette Stadium, Boston",
        "league": "FIFA World Cup 2026",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-009",
        "match_date": "2026-06-14",
        "home_team": "Netherlands",
        "away_team": "Japan",
        "venue": "MetLife Stadium, New York/New Jersey",
        "league": "FIFA World Cup 2026",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-010",
        "match_date": "2026-06-14",
        "home_team": "UEFA Path B Winner",
        "away_team": "Tunisia",
        "venue": "BMO Field, Toronto",
        "league": "FIFA World Cup 2026",
        "status": "scheduled",
    },
]


def _parse_api_fixture(fixture_data: dict) -> dict:
    """Parse API-Football fixture response into our schema."""
    fix = fixture_data.get("fixture", {})
    teams = fixture_data.get("teams", {})
    venue = fixture_data.get("venue", {})
    league = fixture_data.get("league", {})

    return {
        "match_id": str(fix.get("id", "")),
        "match_date": fix.get("date", "")[:10],  # YYYY-MM-DD
        "home_team": teams.get("home", {}).get("name", "Unknown"),
        "away_team": teams.get("away", {}).get("name", "Unknown"),
        "venue": f"{venue.get('name', '')}, {venue.get('city', '')}".strip(", "),
        "league": league.get("name", "FIFA World Cup 2026"),
        "status": fix.get("status", {}).get("long", "scheduled"),
        "raw_data": json.dumps(fixture_data),
    }


async def get_schedule(date_str: str) -> str:
    """Fetch fixtures for a given date and persist them to the database.

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        JSON string of fixtures for the requested date.
    """
    api_key = os.environ.get("FOOTBALL_API_KEY", "")
    fixtures_data = []

    # Try live API first
    if api_key:
        try:
            client = FootballAPIClient(api_key=api_key)
            raw_fixtures = await client.get_fixtures(date_str)
            await client.close()

            if raw_fixtures:
                fixtures_data = [_parse_api_fixture(f) for f in raw_fixtures]
                logger.info(f"Fetched {len(fixtures_data)} fixtures from API-Football for {date_str}")
        except Exception as e:
            logger.warning(f"API-Football call failed, falling back to seed data: {e}")

    # Fallback to seed data
    if not fixtures_data:
        fixtures_data = [f for f in SEED_FIXTURES if f["match_date"] == date_str]
        logger.info(f"Using {len(fixtures_data)} seed fixtures for {date_str}")

    # Persist to database
    with get_session() as session:
        for fix_data in fixtures_data:
            # Convert date string to Python date object for SQLAlchemy Date column
            fix_to_save = dict(fix_data)
            if isinstance(fix_to_save.get("match_date"), str):
                fix_to_save["match_date"] = datetime.strptime(fix_to_save["match_date"], "%Y-%m-%d").date()

            existing = session.query(Fixture).filter_by(match_id=fix_to_save["match_id"]).first()
            if existing:
                for key, value in fix_to_save.items():
                    if key != "match_id":
                        setattr(existing, key, value)
            else:
                session.add(Fixture(**fix_to_save))

    # Return the fixtures as JSON
    result = []
    with get_session() as session:
        query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        fixtures = session.query(Fixture).filter(Fixture.match_date == query_date).all()
        result = [f.to_dict() for f in fixtures]

    return json.dumps(result, indent=2)
