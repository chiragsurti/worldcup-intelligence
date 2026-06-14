"""Async client for API-Football v3."""

import logging
from typing import Any

import httpx

from mcp_server.clients.fallback_data import (
    get_fallback_fixtures,
    get_fallback_player_stats,
    get_fallback_standings,
    get_fallback_team_info,
    get_fallback_team_stats,
)

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

        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded (429), using fallback data")
            return {"response": []}

        response.raise_for_status()
        return response.json()

    async def get_fixtures(self, date: str) -> list[dict]:
        """Get fixtures for a specific date (YYYY-MM-DD format).

        Queries World Cup 2026 fixtures by default.
        Falls back to local CSV data if API returns empty results.
        """
        data = await self._request(
            "/fixtures",
            params={
                "date": date,
                "league": WORLD_CUP_LEAGUE_ID,
                "season": WORLD_CUP_SEASON,
            },
        )
        results = data.get("response", [])
        if not results:
            logger.info(f"API returned empty fixtures for {date}, using fallback data")
            results = get_fallback_fixtures(date)
        return results

    async def get_standings(self, league: int = WORLD_CUP_LEAGUE_ID, season: int = WORLD_CUP_SEASON) -> list[dict]:
        """Get league standings.

        Falls back to local JSON data if API returns empty results.
        """
        data = await self._request(
            "/standings",
            params={"league": league, "season": season},
        )
        results = data.get("response", [])
        if not results and league == WORLD_CUP_LEAGUE_ID:
            logger.info("API returned empty standings, using fallback data")
            results = get_fallback_standings()
        return results

    async def get_team_stats(self, team_id: int, season: int = WORLD_CUP_SEASON, league: int = WORLD_CUP_LEAGUE_ID) -> dict:
        """Get team statistics for the season.

        Falls back to local JSON data if API returns empty results.
        """
        data = await self._request(
            "/teams/statistics",
            params={"team": team_id, "season": season, "league": league},
        )
        results = data.get("response", {})
        if not results and league == WORLD_CUP_LEAGUE_ID:
            logger.info(f"API returned empty team stats for team_id={team_id}, using fallback data")
            results = get_fallback_team_stats(team_id)
        return results

    async def get_team_info(self, team_id: int) -> list[dict]:
        """Get team information.

        Falls back to local CSV data if API returns empty results.
        """
        data = await self._request("/teams", params={"id": team_id})
        results = data.get("response", [])
        if not results:
            logger.info(f"API returned empty team info for id={team_id}, using fallback data")
            results = get_fallback_team_info(team_id)
        return results

    async def get_player_stats(self, player_id: int, season: int = WORLD_CUP_SEASON) -> list[dict]:
        """Get player statistics for the season.

        Falls back to local JSON data if API returns empty results.
        """
        data = await self._request(
            "/players",
            params={"id": player_id, "season": season},
        )
        results = data.get("response", [])
        if not results:
            logger.info(f"API returned empty player stats for player_id={player_id}, using fallback data")
            results = get_fallback_player_stats(player_id)
        return results
