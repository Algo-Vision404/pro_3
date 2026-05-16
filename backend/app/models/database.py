"""
SQLAlchemy ORM models + database engine setup.
Uses SQLite by default (DATABASE_URL env var overrides to PostgreSQL, etc.)
"""
import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Float, Integer, Boolean,
    DateTime, Text, JSON, ForeignKey, Enum as SAEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/nexus.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class TicketORM(Base):
    __tablename__ = "tickets"

    ticket_id   = Column(String, primary_key=True, index=True)
    user_id     = Column(String, nullable=False, index=True)
    subject     = Column(String, nullable=False)
    body        = Column(Text, nullable=False)
    source      = Column(String, nullable=False)
    status      = Column(String, default="new")
    priority    = Column(Integer, default=0)
    tags        = Column(JSON, default=[])
    timestamp   = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, nullable=True)
    resolution_time_ms = Column(Integer, nullable=True)

    # Relationships
    classification  = relationship("ClassificationORM", back_populates="ticket", uselist=False)
    response_draft  = relationship("ResponseDraftORM",  back_populates="ticket", uselist=False)
    escalation      = relationship("EscalationORM",     back_populates="ticket", uselist=False)
    feedback        = relationship("FeedbackORM",        back_populates="ticket", uselist=False)


class ClassificationORM(Base):
    __tablename__ = "classifications"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id       = Column(String, ForeignKey("tickets.ticket_id"), unique=True)
    intent          = Column(String)
    urgency_score   = Column(Float)
    sentiment       = Column(String)
    confidence      = Column(Float, default=0.8)
    keywords        = Column(JSON, default=[])
    sub_topics      = Column(JSON, default=[])

    ticket = relationship("TicketORM", back_populates="classification")


class ResponseDraftORM(Base):
    __tablename__ = "response_drafts"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id       = Column(String, ForeignKey("tickets.ticket_id"), unique=True)
    response_draft  = Column(Text)
    confidence_score = Column(Float)
    requires_human_review = Column(Boolean, default=False)
    tone            = Column(String, default="professional")
    estimated_resolution_time = Column(String, nullable=True)
    suggested_knowledge_articles = Column(JSON, default=[])

    ticket = relationship("TicketORM", back_populates="response_draft")


class EscalationORM(Base):
    __tablename__ = "escalations"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id       = Column(String, ForeignKey("tickets.ticket_id"), unique=True)
    issue_summary   = Column(Text)
    suggested_actions = Column(Text)
    context_bundle  = Column(JSON, default=[])
    escalation_reasons = Column(JSON, default=[])
    risk_level      = Column(String, default="medium")
    assigned_team   = Column(String, default="tier-2-support")

    ticket = relationship("TicketORM", back_populates="escalation")


class FeedbackORM(Base):
    __tablename__ = "feedback"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    feedback_id     = Column(String, unique=True)
    ticket_id       = Column(String, ForeignKey("tickets.ticket_id"), unique=True)
    human_edited_response = Column(Text, nullable=True)
    resolution_status = Column(String)
    feedback_notes  = Column(Text, nullable=True)
    rating          = Column(Integer, nullable=True)
    was_escalation_correct = Column(Boolean, nullable=True)
    submitted_at    = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("TicketORM", back_populates="feedback")


class KnowledgeArticleORM(Base):
    __tablename__ = "knowledge_articles"

    article_id  = Column(String, primary_key=True, index=True)
    title       = Column(String, nullable=False)
    content     = Column(Text, nullable=False)
    category    = Column(String, nullable=False)
    tags        = Column(JSON, default=[])
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, nullable=True)
    views       = Column(Integer, default=0)
    helpful_votes = Column(Integer, default=0)


# ---------------------------------------------------------------------------
# DB Utilities
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and ensure data directory exists."""
    os.makedirs("./data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
