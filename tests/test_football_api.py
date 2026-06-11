"""Tests for the Football API client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server.clients.football_api import FootballAPIClient


@pytest.fixture
def client():
    return FootballAPIClient(api_key="test-key")


@pytest.fixture
def mock_fixtures_response():
    return {
        "response": [
            {
                "fixture": {
                    "id": 12345,
                    "date": "2026-06-11T18:00:00+00:00",
                    "status": {"long": "Not Started"},
                },
                "teams": {
                    "home": {"id": 1, "name": "Mexico"},
                    "away": {"id": 2, "name": "Colombia"},
                },
                "venue": {"name": "Estadio Azteca", "city": "Mexico City"},
                "league": {"name": "FIFA World Cup 2026"},
            }
        ]
    }


def _make_mock_response(data: dict):
    """Create a mock httpx response with sync json() for patching at client level."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.headers = {"x-ratelimit-requests-remaining": "99"}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.mark.asyncio
async def test_get_fixtures(client, mock_fixtures_response):
    mock_resp = _make_mock_response(mock_fixtures_response)

    with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_fixtures_response):
        fixtures = await client.get_fixtures("2026-06-11")
        assert len(fixtures) == 1
        assert fixtures[0]["teams"]["home"]["name"] == "Mexico"

    await client.close()


@pytest.mark.asyncio
async def test_get_team_stats(client):
    mock_data = {
        "response": {
            "form": "WWDWL",
            "fixtures": {"played": {"total": 9}},
            "goals": {"for": {"total": 18}, "against": {"total": 8}},
        }
    }

    with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_data):
        stats = await client.get_team_stats(team_id=1)
        assert stats["form"] == "WWDWL"

    await client.close()
