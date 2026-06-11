"""MCP Tools: persistence — save/retrieve prediction cards and media packs."""

import json
import logging
from datetime import UTC, datetime

from shared.db.database import get_session
from shared.db.models import MediaPack, PredictionCard

logger = logging.getLogger(__name__)


async def save_prediction_card(
    match_id: str,
    prob_home: float,
    prob_draw: float,
    prob_away: float,
    analysis: str,
    reasoning: str,
) -> str:
    """Save a prediction card for a match.

    Args:
        match_id: The fixture match_id.
        prob_home: Win probability for home team (0.0–1.0).
        prob_draw: Draw probability (0.0–1.0).
        prob_away: Win probability for away team (0.0–1.0).
        analysis: Summary analysis text.
        reasoning: Transparent reasoning chain.

    Returns:
        JSON string with the saved prediction card ID.
    """
    with get_session() as session:
        card = PredictionCard(
            match_id=match_id,
            prob_home=prob_home,
            prob_draw=prob_draw,
            prob_away=prob_away,
            analysis=analysis,
            reasoning=reasoning,
            created_at=datetime.now(UTC),
        )
        session.add(card)
        session.flush()
        record_id = card.id

    logger.info(f"Prediction card saved: id={record_id}, match={match_id}")
    return json.dumps({"id": record_id, "status": "saved", "match_id": match_id})


async def save_media_pack(
    match_id: str,
    email_html: str,
    social_threads: list[str],
) -> str:
    """Save a media pack (email + social threads) for a match.

    Args:
        match_id: The fixture match_id.
        email_html: Rendered HTML email content.
        social_threads: Array of social media post strings.

    Returns:
        JSON string with the saved media pack ID.
    """
    with get_session() as session:
        pack = MediaPack(
            match_id=match_id,
            email_html=email_html,
            social_threads=json.dumps(social_threads),
            created_at=datetime.now(UTC),
        )
        session.add(pack)
        session.flush()
        record_id = pack.id

    logger.info(f"Media pack saved: id={record_id}, match={match_id}")
    return json.dumps({"id": record_id, "status": "saved", "match_id": match_id})


async def get_prediction_cards(date_str: str) -> str:
    """Retrieve all prediction cards for matches on a given date.

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        JSON string with array of prediction cards.
    """
    from shared.db.models import Fixture

    with get_session() as session:
        # Get match_ids for the date
        query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        fixtures = session.query(Fixture).filter(Fixture.match_date == query_date).all()
        match_ids = [f.match_id for f in fixtures]

        if not match_ids:
            return json.dumps([])

        cards = session.query(PredictionCard).filter(PredictionCard.match_id.in_(match_ids)).all()
        result = [card.to_dict() for card in cards]

    return json.dumps(result, indent=2)
