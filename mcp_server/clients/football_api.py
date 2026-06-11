"""Async client for API-Football v3."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://v3.football.api-sports.io"
WORLD_CUP_LEAGUE_ID = 1
WORLD_CUP_SEASON = 2026


class FootballAPIClient:
    """Async wrapper around API-Football v3 endpoints."""

    def __init__(self, api_key: str, base_url: str = BASE_URL):
        self.api_key = api_key
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"x-apisports-key": self.api_key},
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict:
        """Make a GET request and return the JSON response."""
        client = await self._get_client()
        response = await client.get(endpoint, params=params)

        # Log rate limit info
        remaining = response.headers.get("x-ratelimit-requests-remaining")
        if remaining:
            logger.info(f"API-Football rate limit remaining: {remaining}")

        response.raise_for_status()
        return response.json()

    async def get_fixtures(self, date: str) -> list[dict]:
        """Get fixtures for a specific date (YYYY-MM-DD format).

        Queries World Cup 2026 fixtures by default.
        """
        data = await self._request(
            "/fixtures",
            params={
                "date": date,
                "league": WORLD_CUP_LEAGUE_ID,
                "season": WORLD_CUP_SEASON,
            },
        )
        return data.get("response", [])

    async def get_standings(self, league: int = WORLD_CUP_LEAGUE_ID, season: int = WORLD_CUP_SEASON) -> list[dict]:
        """Get league standings."""
        data = await self._request(
            "/standings",
            params={"league": league, "season": season},
        )
        return data.get("response", [])

    async def get_team_stats(self, team_id: int, season: int = WORLD_CUP_SEASON, league: int = WORLD_CUP_LEAGUE_ID) -> dict:
        """Get team statistics for the season."""
        data = await self._request(
            "/teams/statistics",
            params={"team": team_id, "season": season, "league": league},
        )
        return data.get("response", {})

    async def get_player_stats(self, player_id: int, season: int = WORLD_CUP_SEASON) -> list[dict]:
        """Get player statistics for the season."""
        data = await self._request(
            "/players",
            params={"id": player_id, "season": season},
        )
        return data.get("response", [])
