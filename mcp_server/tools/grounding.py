"""MCP Tool: ground_and_audit_claim — validate and persist grounded claims."""

import json
import logging
from datetime import UTC, datetime

from shared.db.database import get_session
from shared.db.models import AuditClaim

logger = logging.getLogger(__name__)

VALID_STATUS_LABELS = {"Confirmed", "Reported", "Unverified"}


async def ground_and_audit_claim(
    claim_text: str,
    citations: list[dict],
    status_label: str,
    confidence_score: float,
    entity_mappings: dict,
    match_id: str = "unknown",
) -> str:
    """Validate a grounded claim and persist it to the audit trail.

    Args:
        claim_text: Normalized representation of the claim.
        citations: Array of citation objects with url, title, publisher, publish_time, quote_snippet.
        status_label: One of Confirmed, Reported, or Unverified.
        confidence_score: Float between 0.0 and 1.0.
        entity_mappings: Dict mapping entity identifiers (e.g., wikidata_id → api_football_id).
        match_id: The fixture match_id this claim relates to.

    Returns:
        JSON string with the saved audit record ID and status.
    """
    # Validate status label — default to Unverified if invalid
    if status_label not in VALID_STATUS_LABELS:
        logger.warning(f"Invalid status_label '{status_label}', defaulting to 'Unverified'")
        status_label = "Unverified"

    # Validate confidence score — clamp to valid range
    if not isinstance(confidence_score, (int, float)):
        confidence_score = 0.5
    confidence_score = max(0.0, min(1.0, confidence_score))

    # Ensure citations is a list
    if not isinstance(citations, list):
        citations = [] if citations is None else [citations]

    # Normalize citations — fill missing fields with defaults instead of rejecting
    normalized_citations = []
    for citation in citations:
        if not isinstance(citation, dict):
            citation = {"url": str(citation)}
        normalized = {
            "url": citation.get("url", ""),
            "title": citation.get("title", ""),
            "publisher": citation.get("publisher", "unknown"),
            "publish_time": citation.get("publish_time", ""),
            "quote_snippet": citation.get("quote_snippet", ""),
        }
        normalized_citations.append(normalized)
    citations = normalized_citations

    # Persist to database
    with get_session() as session:
        claim = AuditClaim(
            match_id=match_id or "unknown",
            claim_text=claim_text,
            entity_mappings=json.dumps(entity_mappings if isinstance(entity_mappings, dict) else {}),
            status_label=status_label,
            confidence_score=confidence_score,
            citations=json.dumps(citations),
            created_at=datetime.now(UTC),
        )
        session.add(claim)
        session.flush()
        record_id = claim.id

    logger.info(f"Audit claim saved: id={record_id}, status={status_label}, confidence={confidence_score}")

    return json.dumps({
        "id": record_id,
        "status": "saved",
        "match_id": match_id,
        "status_label": status_label,
        "confidence_score": confidence_score,
        "citation_count": len(citations),
    })
