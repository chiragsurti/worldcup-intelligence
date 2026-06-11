"""MCP Tool: ground_and_audit_claim — validate and persist grounded claims."""

import json
import logging
from datetime import UTC, datetime

from shared.db.database import get_session
from shared.db.models import AuditClaim

logger = logging.getLogger(__name__)

VALID_STATUS_LABELS = {"Confirmed", "Reported", "Unverified"}
REQUIRED_CITATION_FIELDS = {"url", "title", "publisher", "publish_time", "quote_snippet"}


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
    # Validate status label
    if status_label not in VALID_STATUS_LABELS:
        return json.dumps({
            "error": f"Invalid status_label '{status_label}'. Must be one of: {VALID_STATUS_LABELS}"
        })

    # Validate confidence score
    if not (0.0 <= confidence_score <= 1.0):
        return json.dumps({
            "error": f"confidence_score must be between 0.0 and 1.0, got {confidence_score}"
        })

    # Validate citation schema
    validation_errors = []
    for i, citation in enumerate(citations):
        missing = REQUIRED_CITATION_FIELDS - set(citation.keys())
        if missing:
            validation_errors.append(f"Citation[{i}] missing fields: {missing}")

    if validation_errors:
        return json.dumps({"error": "Citation validation failed", "details": validation_errors})

    # Persist to database
    with get_session() as session:
        claim = AuditClaim(
            match_id=match_id,
            claim_text=claim_text,
            entity_mappings=json.dumps(entity_mappings),
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
