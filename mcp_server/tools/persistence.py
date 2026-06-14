"""MCP Tools: persistence — save/retrieve prediction cards and media packs."""

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from shared.db.database import get_session
from shared.db.models import MediaPack, PredictionCard

logger = logging.getLogger(__name__)

# Load email template
_template_dir = Path(__file__).resolve().parent.parent.parent / "shared" / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_template_dir)), autoescape=False)
_email_template = _jinja_env.get_template("email.html.j2")


def _analysis_to_html(text: str) -> str:
    """Convert the campaign brief plain text into structured HTML sections."""
    import html as _html
    import re

    lines = text.split("\n")
    result: list[str] = []
    # Emoji section headers pattern
    section_re = re.compile(r"^([\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u26A1\u2699\uFE0F]+)\s*(.+)$")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for section header (starts with emoji)
        m = section_re.match(stripped)
        if m and not stripped.startswith("•"):
            emoji, title = m.group(1), _html.escape(m.group(2))
            result.append(f'<div class="section-header">{emoji} {title}</div>')
        elif stripped.startswith("•"):
            # Bullet point
            content = _html.escape(stripped[1:].strip())
            # Bold text before colon
            if ":" in content:
                label, rest = content.split(":", 1)
                result.append(f'<div class="bullet"><strong>{label}:</strong>{rest}</div>')
            else:
                result.append(f'<div class="bullet">{content}</div>')
        elif stripped.startswith("⚠️"):
            result.append(f'<div class="disclaimer-inline">{_html.escape(stripped)}</div>')
        else:
            result.append(f"<p>{_html.escape(stripped)}</p>")

    return "\n".join(result)


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
    home_team: str,
    away_team: str,
    venue: str,
    match_date: str,
    prob_home: float,
    prob_draw: float,
    prob_away: float,
    analysis: str,
    social_threads: list[str],
) -> str:
    """Save a media pack (rendered email HTML + social threads) for a match.

    The email HTML is rendered from the platform's Jinja2 template using the
    structured match data provided.

    Args:
        match_id: The fixture match_id (numeric string).
        home_team: Home team name.
        away_team: Away team name.
        venue: Stadium and city.
        match_date: Date string (e.g. "2026-06-14").
        prob_home: Home win probability (0.0–1.0).
        prob_draw: Draw probability (0.0–1.0).
        prob_away: Away win probability (0.0–1.0).
        analysis: Tactical analysis text for the match.
        social_threads: Array of social media post strings.

    Returns:
        JSON string with the saved media pack ID.
    """
    # Render the email template
    analysis_html = _analysis_to_html(analysis)
    email_html = _email_template.render(
        match_date=match_date,
        matches=[
            {
                "home_team": home_team,
                "away_team": away_team,
                "venue": venue,
                "prediction": {
                    "prob_home": prob_home,
                    "prob_draw": prob_draw,
                    "prob_away": prob_away,
                    "analysis": analysis_html,
                },
            }
        ],
        citations=[],
    )

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
