from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class TicketSource(str, Enum):
    EMAIL = "email"
    CSV = "csv"
    API = "api"
    WEBHOOK = "webhook"

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class Intent(str, Enum):
    TECHNICAL_SUPPORT = "technical_support"
    BILLING = "billing"
    ACCOUNT_ACCESS = "account_access"
    FEATURE_REQUEST = "feature_request"
    GENERAL_INQUIRY = "general_inquiry"
    UNKNOWN = "unknown"

class OperationalMode(str, Enum):
    DRAFT = "draft"
    ASSISTED = "assisted"
    AUTONOMOUS = "autonomous"

class TicketBase(BaseModel):
    user_id: str
    subject: str
    body: str
    source: TicketSource

class TicketCreate(TicketBase):
    pass

class Ticket(TicketBase):
    ticket_id: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

class ClassificationResult(BaseModel):
    intent: Intent
    urgency_score: float = Field(ge=0.0, le=1.0)
    sentiment: Sentiment

class RetrievalResult(BaseModel):
    context: List[str]
    metadata: List[Dict[str, Any]]

class ResponseDraft(BaseModel):
    response_draft: str
    confidence_score: float
    requires_human_review: bool

class EscalationSummary(BaseModel):
    issue_summary: str
    suggested_actions: str
    context_bundle: List[str]

class FeedbackCreate(BaseModel):
    ticket_id: str
    human_edited_response: Optional[str] = None
    resolution_status: str
    feedback_notes: Optional[str] = None
