"""Cleanup script: Remove all PostgreSQL data for a specific date.

Usage:
    python scripts/cleanup_date.py 2026-06-14
    python scripts/cleanup_date.py --all
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db.database import get_session
from shared.db.models import AuditClaim, Fixture, MediaPack, PredictionCard


def cleanup_all():
    """Delete ALL predictions, media packs, audit claims, and fixtures."""
    with get_session() as session:
        claims_deleted = session.query(AuditClaim).delete()
        print(f"  Deleted {claims_deleted} audit claim(s)")

        predictions_deleted = session.query(PredictionCard).delete()
        print(f"  Deleted {predictions_deleted} prediction card(s)")

        media_deleted = session.query(MediaPack).delete()
        print(f"  Deleted {media_deleted} media pack(s)")

        fixtures_deleted = session.query(Fixture).delete()
        print(f"  Deleted {fixtures_deleted} fixture(s)")

        print("\nFull cleanup complete.")


def cleanup_date(date_str: str):
    """Delete all records associated with fixtures on the given date."""
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    with get_session() as session:
        # Find all match_ids for the target date
        fixtures = session.query(Fixture).filter(Fixture.match_date == target_date).all()
        match_ids = [f.match_id for f in fixtures]

        if not match_ids:
            print(f"No fixtures found for {date_str}. Nothing to delete.")
            return

        print(f"Found {len(match_ids)} fixture(s) for {date_str}: {match_ids}")

        # Delete related records
        claims_deleted = session.query(AuditClaim).filter(AuditClaim.match_id.in_(match_ids)).delete(synchronize_session="fetch")
        print(f"  Deleted {claims_deleted} audit claim(s)")

        predictions_deleted = session.query(PredictionCard).filter(PredictionCard.match_id.in_(match_ids)).delete(synchronize_session="fetch")
        print(f"  Deleted {predictions_deleted} prediction card(s)")

        media_deleted = session.query(MediaPack).filter(MediaPack.match_id.in_(match_ids)).delete(synchronize_session="fetch")
        print(f"  Deleted {media_deleted} media pack(s)")

        fixtures_deleted = session.query(Fixture).filter(Fixture.match_date == target_date).delete(synchronize_session="fetch")
        print(f"  Deleted {fixtures_deleted} fixture(s)")

        print(f"\nCleanup complete for {date_str}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/cleanup_date.py YYYY-MM-DD")
        print("       python scripts/cleanup_date.py --all")
        sys.exit(1)

    if sys.argv[1] == "--all":
        cleanup_all()
    else:
        cleanup_date(sys.argv[1])
