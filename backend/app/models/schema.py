from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TicketSource(str, Enum):
    EMAIL = "email"
    CSV = "csv"
    API = "api"
    WEBHOOK = "webhook"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"
    URGENT = "urgent"


class Intent(str, Enum):
    TECHNICAL_SUPPORT = "technical_support"
    BILLING = "billing"
    ACCOUNT_ACCESS = "account_access"
    FEATURE_REQUEST = "feature_request"
    GENERAL_INQUIRY = "general_inquiry"
    BUG_REPORT = "bug_report"
    REFUND_REQUEST = "refund_request"
    CANCELLATION = "cancellation"
    UNKNOWN = "unknown"


class OperationalMode(str, Enum):
    DRAFT = "draft"
    ASSISTED = "assisted"
    AUTONOMOUS = "autonomous"


class TicketStatus(str, Enum):
    NEW = "new"
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class EscalationReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    HIGH_URGENCY = "high_urgency"
    SENSITIVE_INTENT = "sensitive_intent"
    NEGATIVE_SENTIMENT = "negative_sentiment"
    HUMAN_FLAG = "human_flag"
    LEGAL_RISK = "legal_risk"


# ---------------------------------------------------------------------------
# Core Ticket Models
# ---------------------------------------------------------------------------

class TicketBase(BaseModel):
    user_id: str
    subject: str
    body: str
    source: TicketSource
    tags: Optional[List[str]] = []
    priority: Optional[int] = Field(default=0, ge=0, le=3, description="0=normal, 1=high, 2=critical, 3=emergency")


class TicketCreate(TicketBase):
    pass


class Ticket(TicketBase):
    ticket_id: str
    timestamp: datetime
    status: TicketStatus = TicketStatus.NEW
    updated_at: Optional[datetime] = None
    resolution_time_ms: Optional[int] = None

    class Config:
        from_attributes = True


class TicketListItem(BaseModel):
    ticket_id: str
    subject: str
    status: str
    urgency_score: float
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    timestamp: Optional[datetime] = None


# ---------------------------------------------------------------------------
# AI Pipeline Models
# ---------------------------------------------------------------------------

class ClassificationResult(BaseModel):
    intent: Intent
    urgency_score: float = Field(ge=0.0, le=1.0)
    sentiment: Sentiment
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    keywords: Optional[List[str]] = []
    sub_topics: Optional[List[str]] = []


class RetrievalResult(BaseModel):
    context: List[str]
    metadata: List[Dict[str, Any]]
    similarity_scores: Optional[List[float]] = []
    sources: Optional[List[str]] = []


class ResponseDraft(BaseModel):
    response_draft: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool
    tone: Optional[str] = "professional"
    estimated_resolution_time: Optional[str] = None
    suggested_knowledge_articles: Optional[List[str]] = []


class EscalationSummary(BaseModel):
    issue_summary: str
    suggested_actions: str
    context_bundle: List[str]
    escalation_reasons: List[EscalationReason] = []
    risk_level: str = "medium"
    assigned_team: Optional[str] = "tier-2-support"


class ProcessResult(BaseModel):
    ticket_id: str
    classification: ClassificationResult
    retrieval: RetrievalResult
    draft: ResponseDraft
    escalation: Optional[EscalationSummary]
    status: TicketStatus
    mode: OperationalMode
    processing_time_ms: Optional[int] = None


# ---------------------------------------------------------------------------
# Feedback & Learning
# ---------------------------------------------------------------------------

class FeedbackCreate(BaseModel):
    ticket_id: str
    human_edited_response: Optional[str] = None
    resolution_status: str
    feedback_notes: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="1-5 star rating")
    was_escalation_correct: Optional[bool] = None


class FeedbackRecord(FeedbackCreate):
    feedback_id: str
    submitted_at: datetime


# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------

class KnowledgeArticle(BaseModel):
    article_id: str
    title: str
    content: str
    category: str
    tags: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    views: int = 0
    helpful_votes: int = 0


class KnowledgeArticleCreate(BaseModel):
    title: str
    content: str
    category: str
    tags: List[str] = []


# ---------------------------------------------------------------------------
# Analytics & Metrics
# ---------------------------------------------------------------------------

class OperationalMetrics(BaseModel):
    total_processed: int
    resolved_count: int
    escalated_count: int
    pending_count: int
    avg_confidence: float
    avg_resolution_time_ms: float
    auto_resolve_rate: float
    escalation_rate: float
    top_intents: Dict[str, int]
    sentiment_distribution: Dict[str, int]
    source_distribution: Dict[str, int]
    tickets_last_hour: int
    tickets_last_24h: int


class TimeSeriesPoint(BaseModel):
    timestamp: str
    value: float


class AnalyticsDashboard(BaseModel):
    metrics: OperationalMetrics
    confidence_trend: List[TimeSeriesPoint]
    volume_trend: List[TimeSeriesPoint]


# ---------------------------------------------------------------------------
# System Health
# ---------------------------------------------------------------------------

class ServiceStatus(BaseModel):
    name: str
    status: str  # "online" | "degraded" | "offline"
    latency_ms: Optional[float] = None
    details: Optional[str] = None


class HealthReport(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    services: List[ServiceStatus]
    timestamp: datetime
