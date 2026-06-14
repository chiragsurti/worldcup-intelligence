"""SQLAlchemy ORM models for the World Cup Intelligence Platform."""

import json
from datetime import UTC, date, datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Fixture(Base):
    __tablename__ = "fixtures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String, unique=True, nullable=False, index=True)
    match_date = Column(Date, nullable=False, index=True)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    home_team_id = Column(Integer, nullable=True)
    away_team_id = Column(Integer, nullable=True)
    venue = Column(String, nullable=True)
    league = Column(String, default="FIFA World Cup 2026")
    status = Column(String, default="scheduled")
    raw_data = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "match_date": str(self.match_date),
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "venue": self.venue,
            "league": self.league,
            "status": self.status,
            "raw_data": json.loads(self.raw_data) if self.raw_data else None,
        }


class AuditClaim(Base):
    __tablename__ = "audit_claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String, nullable=False, index=True)
    claim_text = Column(Text, nullable=False)
    entity_mappings = Column(Text, nullable=True)  # JSON string
    status_label = Column(String, nullable=False)  # Confirmed / Reported / Unverified
    confidence_score = Column(Float, nullable=False)
    citations = Column(Text, nullable=True)  # JSON array string
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "match_id": self.match_id,
            "claim_text": self.claim_text,
            "entity_mappings": json.loads(self.entity_mappings) if self.entity_mappings else None,
            "status_label": self.status_label,
            "confidence_score": self.confidence_score,
            "citations": json.loads(self.citations) if self.citations else [],
            "created_at": str(self.created_at),
        }


class PredictionCard(Base):
    __tablename__ = "prediction_cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String, nullable=False, index=True)
    prob_home = Column(Float, nullable=False)
    prob_draw = Column(Float, nullable=False)
    prob_away = Column(Float, nullable=False)
    analysis = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "match_id": self.match_id,
            "prob_home": self.prob_home,
            "prob_draw": self.prob_draw,
            "prob_away": self.prob_away,
            "analysis": self.analysis,
            "reasoning": self.reasoning,
            "created_at": str(self.created_at),
        }


class MediaPack(Base):
    __tablename__ = "media_packs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String, nullable=False, index=True)
    email_html = Column(Text, nullable=True)
    social_threads = Column(Text, nullable=True)  # JSON array string
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "match_id": self.match_id,
            "email_html": self.email_html,
            "social_threads": json.loads(self.social_threads) if self.social_threads else [],
            "created_at": str(self.created_at),
        }
