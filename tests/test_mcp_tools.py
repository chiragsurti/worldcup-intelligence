"""Tests for MCP server tools — in-process tests without network."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db.database import get_engine, init_db


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Create a temporary SQLite database for each test."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    # Reset the singleton engine
    import shared.db.database as db_mod
    db_mod._engine = None
    db_mod._SessionLocal = None

    init_db(db_url)
    yield db_url


@pytest.mark.asyncio
async def test_get_schedule_seed_data(setup_test_db, monkeypatch):
    """Test schedule tool returns seed data when no API key."""
    monkeypatch.delenv("FOOTBALL_API_KEY", raising=False)

    from mcp_server.tools.schedule import get_schedule

    result = await get_schedule("2026-06-11")
    fixtures = json.loads(result)

    assert len(fixtures) >= 1
    assert fixtures[0]["home_team"] in ("Mexico", "USA")


@pytest.mark.asyncio
async def test_ground_and_audit_claim(setup_test_db):
    """Test grounding tool validates and persists claims."""
    from mcp_server.tools.grounding import ground_and_audit_claim

    result = await ground_and_audit_claim(
        claim_text="Neymar ruled out with knee injury",
        citations=[{
            "url": "https://example.com/article",
            "title": "Neymar Injury Update",
            "publisher": "ESPN",
            "publish_time": "2026-06-10T14:00:00Z",
            "quote_snippet": "Neymar has been ruled out of the opening match.",
        }],
        status_label="Confirmed",
        confidence_score=0.95,
        entity_mappings={"wikidata": "Q134567", "api_football": "276"},
        match_id="wc2026-003",
    )

    data = json.loads(result)
    assert data["status"] == "saved"
    assert data["match_id"] == "wc2026-003"


@pytest.mark.asyncio
async def test_ground_and_audit_claim_invalid_status(setup_test_db):
    """Test grounding tool rejects invalid status labels."""
    from mcp_server.tools.grounding import ground_and_audit_claim

    result = await ground_and_audit_claim(
        claim_text="Test claim",
        citations=[],
        status_label="InvalidStatus",
        confidence_score=0.5,
        entity_mappings={},
    )

    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_save_and_get_prediction_card(setup_test_db):
    """Test saving and retrieving prediction cards."""
    from mcp_server.tools.persistence import get_prediction_cards, save_prediction_card
    from mcp_server.tools.schedule import get_schedule

    # First create a fixture
    await get_schedule("2026-06-11")

    # Save a prediction card
    result = await save_prediction_card(
        match_id="wc2026-001",
        prob_home=0.45,
        prob_draw=0.25,
        prob_away=0.30,
        analysis="Mexico favored at home with strong form.",
        reasoning="Mexico's home record is 5W-0L. Colombia inconsistent away.",
    )

    data = json.loads(result)
    assert data["status"] == "saved"

    # Retrieve cards
    cards_result = await get_prediction_cards("2026-06-11")
    cards = json.loads(cards_result)
    assert len(cards) >= 1
    assert cards[0]["prob_home"] == 0.45


@pytest.mark.asyncio
async def test_save_media_pack(setup_test_db):
    """Test saving media packs."""
    from mcp_server.tools.persistence import save_media_pack

    result = await save_media_pack(
        match_id="wc2026-001",
        email_html="<h1>Mexico vs Colombia</h1><p>Preview...</p>",
        social_threads=[
            "🇲🇽🇨🇴 MATCH DAY! Mexico vs Colombia kicks off WC2026!",
            "Key stat: Mexico unbeaten at Azteca in 12 World Cup matches.",
            "Watch for: James Rodriguez's creativity vs Mexico's defensive block.",
            "Prediction: Mexico 2-1 Colombia. Home advantage decisive.",
            "Follow our thread for live updates! ⚽🏆 #WorldCup2026",
        ],
    )

    data = json.loads(result)
    assert data["status"] == "saved"
