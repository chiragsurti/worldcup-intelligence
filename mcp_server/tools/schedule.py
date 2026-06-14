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
        "away_team": "South Africa",
        "venue": "Estadio Azteca, Mexico City",
        "league": "FIFA World Cup 2026",
        "group": "A",
        "status": "finished",
        "home_score": 2,
        "away_score": 0,
    },
    {
        "match_id": "wc2026-002",
        "match_date": "2026-06-11",
        "home_team": "South Korea",
        "away_team": "Czech Republic",
        "venue": "Estadio Akron, Zapopan",
        "league": "FIFA World Cup 2026",
        "group": "A",
        "status": "finished",
        "home_score": 2,
        "away_score": 1,
    },
    {
        "match_id": "wc2026-003",
        "match_date": "2026-06-12",
        "home_team": "Canada",
        "away_team": "Bosnia and Herzegovina",
        "venue": "BMO Field, Toronto",
        "league": "FIFA World Cup 2026",
        "group": "B",
        "status": "finished",
        "home_score": 1,
        "away_score": 1,
    },
    {
        "match_id": "wc2026-004",
        "match_date": "2026-06-12",
        "home_team": "United States",
        "away_team": "Paraguay",
        "venue": "SoFi Stadium, Inglewood",
        "league": "FIFA World Cup 2026",
        "group": "D",
        "status": "finished",
        "home_score": 4,
        "away_score": 1,
    },
    {
        "match_id": "wc2026-005",
        "match_date": "2026-06-13",
        "home_team": "Qatar",
        "away_team": "Switzerland",
        "venue": "Levi's Stadium, Santa Clara",
        "league": "FIFA World Cup 2026",
        "group": "B",
        "status": "finished",
        "home_score": 1,
        "away_score": 1,
    },
    {
        "match_id": "wc2026-006",
        "match_date": "2026-06-13",
        "home_team": "Brazil",
        "away_team": "Morocco",
        "venue": "MetLife Stadium, East Rutherford",
        "league": "FIFA World Cup 2026",
        "group": "C",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-006b",
        "match_date": "2026-06-13",
        "home_team": "Haiti",
        "away_team": "Scotland",
        "venue": "Gillette Stadium, Foxborough",
        "league": "FIFA World Cup 2026",
        "group": "C",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-006c",
        "match_date": "2026-06-13",
        "home_team": "Australia",
        "away_team": "Turkey",
        "venue": "BC Place, Vancouver",
        "league": "FIFA World Cup 2026",
        "group": "D",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-007",
        "match_date": "2026-06-14",
        "home_team": "Germany",
        "away_team": "Curaçao",
        "venue": "NRG Stadium, Houston",
        "league": "FIFA World Cup 2026",
        "group": "E",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-008",
        "match_date": "2026-06-14",
        "home_team": "Ivory Coast",
        "away_team": "Ecuador",
        "venue": "Lincoln Financial Field, Philadelphia",
        "league": "FIFA World Cup 2026",
        "group": "E",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-009",
        "match_date": "2026-06-14",
        "home_team": "Netherlands",
        "away_team": "Japan",
        "venue": "AT&T Stadium, Arlington",
        "league": "FIFA World Cup 2026",
        "group": "F",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-010",
        "match_date": "2026-06-14",
        "home_team": "Sweden",
        "away_team": "Tunisia",
        "venue": "Estadio BBVA, Guadalupe",
        "league": "FIFA World Cup 2026",
        "group": "F",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-011",
        "match_date": "2026-06-15",
        "home_team": "Belgium",
        "away_team": "Egypt",
        "venue": "Lumen Field, Seattle",
        "league": "FIFA World Cup 2026",
        "group": "G",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-012",
        "match_date": "2026-06-15",
        "home_team": "Iran",
        "away_team": "New Zealand",
        "venue": "SoFi Stadium, Inglewood",
        "league": "FIFA World Cup 2026",
        "group": "G",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-013",
        "match_date": "2026-06-15",
        "home_team": "Spain",
        "away_team": "Cape Verde",
        "venue": "Mercedes-Benz Stadium, Atlanta",
        "league": "FIFA World Cup 2026",
        "group": "H",
        "status": "scheduled",
    },
    {
        "match_id": "wc2026-014",
        "match_date": "2026-06-15",
        "home_team": "Saudi Arabia",
        "away_team": "Uruguay",
        "venue": "Hard Rock Stadium, Miami Gardens",
        "league": "FIFA World Cup 2026",
        "group": "H",
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
