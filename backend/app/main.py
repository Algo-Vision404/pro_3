"""
CogV8 Support AI — FastAPI Application Entry Point
Full end-to-end backend with SQLite persistence, analytics, WebSocket live feed,
and knowledge base management.
"""
import uuid
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Body, Query, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.schema import (
    Ticket, TicketCreate, TicketListItem, TicketSource,
    ClassificationResult, ResponseDraft,
    EscalationSummary, FeedbackCreate, FeedbackRecord,
    OperationalMode, TicketStatus, ProcessResult,
    OperationalMetrics, AnalyticsDashboard, TimeSeriesPoint,
    HealthReport, ServiceStatus,
    KnowledgeArticle, KnowledgeArticleCreate,
)
from app.models.database import (
    TicketORM, ClassificationORM, ResponseDraftORM,
    EscalationORM, FeedbackORM, KnowledgeArticleORM,
    get_db, init_db,
)
from app.services.classification_service import get_classifier
from app.services.rag_service import rag_service
from app.services.generation_service import generation_service
from app.services.escalation_service import escalation_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------
APP_VERSION = "2.0.0"
APP_START_TIME = time.time()

app = FastAPI(
    title="CogV8 Support AI",
    description="Autonomous AI Customer Support Operations Platform",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection pool
active_connections: List[WebSocket] = []


@app.on_event("startup")
async def on_startup():
    init_db()
    logger.info(f"CogV8 Support AI v{APP_VERSION} started. DB initialised.")


# ---------------------------------------------------------------------------
# WebSocket Live Feed
# ---------------------------------------------------------------------------

@app.websocket("/ws/live-feed")
async def websocket_live_feed(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive ping
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def _broadcast(event: dict):
    for connection in list(active_connections):
        try:
            await connection.send_json(event)
        except Exception:
            active_connections.remove(connection)


# ---------------------------------------------------------------------------
# System Health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthReport, tags=["System"])
async def health_check():
    uptime = time.time() - APP_START_TIME
    services = []

    # Check ChromaDB
    t0 = time.time()
    try:
        count = rag_service.get_collection_count()
        services.append(ServiceStatus(
            name="ChromaDB Vector Store",
            status="online",
            latency_ms=round((time.time() - t0) * 1000, 2),
            details=f"{count} documents indexed",
        ))
    except Exception as e:
        services.append(ServiceStatus(name="ChromaDB Vector Store", status="offline", details=str(e)))

    # Check SQLite
    t0 = time.time()
    try:
        db = next(get_db())
        db.execute(TicketORM.__table__.select().limit(1))
        services.append(ServiceStatus(
            name="SQLite Persistence Layer",
            status="online",
            latency_ms=round((time.time() - t0) * 1000, 2),
            details="Read/write operational",
        ))
    except Exception as e:
        services.append(ServiceStatus(name="SQLite Persistence Layer", status="degraded", details=str(e)))

    # Classifier (always local)
    services.append(ServiceStatus(
        name="Classification Engine",
        status="online",
        latency_ms=0.1,
        details="Rule-based classifier active",
    ))

    # Generation engine
    import os
    has_llm = bool(os.getenv("OPENAI_API_KEY"))
    services.append(ServiceStatus(
        name="Generation Engine",
        status="online",
        latency_ms=None,
        details="GPT-4o-mini active" if has_llm else "Template engine active (no API key)",
    ))

    return HealthReport(
        status="healthy",
        version=APP_VERSION,
        uptime_seconds=round(uptime, 2),
        services=services,
        timestamp=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# Ticket Ingestion
# ---------------------------------------------------------------------------

@app.post("/ingest_ticket", response_model=Ticket, tags=["Tickets"])
async def ingest_ticket(ticket_in: TicketCreate, db: Session = Depends(get_db)):
    ticket_id = str(uuid.uuid4())
    now = datetime.utcnow()
    orm = TicketORM(
        ticket_id=ticket_id,
        user_id=ticket_in.user_id,
        subject=ticket_in.subject,
        body=ticket_in.body,
        source=ticket_in.source,
        status=TicketStatus.NEW,
        priority=ticket_in.priority or 0,
        tags=ticket_in.tags or [],
        timestamp=now,
    )
    db.add(orm)
    db.commit()
    db.refresh(orm)

    ticket = Ticket(
        ticket_id=ticket_id,
        user_id=ticket_in.user_id,
        subject=ticket_in.subject,
        body=ticket_in.body,
        source=ticket_in.source,
        timestamp=now,
        status=TicketStatus.NEW,
        priority=ticket_in.priority or 0,
        tags=ticket_in.tags or [],
    )

    await _broadcast({"event": "ticket_ingested", "ticket_id": ticket_id, "subject": ticket_in.subject})
    return ticket


@app.post("/bulk_ingest", tags=["Tickets"])
async def bulk_ingest(tickets: List[TicketCreate], db: Session = Depends(get_db)):
    """Ingest multiple tickets at once."""
    created_ids = []
    for ticket_in in tickets:
        ticket_id = str(uuid.uuid4())
        orm = TicketORM(
            ticket_id=ticket_id,
            user_id=ticket_in.user_id,
            subject=ticket_in.subject,
            body=ticket_in.body,
            source=ticket_in.source,
            status=TicketStatus.NEW,
            priority=ticket_in.priority or 0,
            tags=ticket_in.tags or [],
            timestamp=datetime.utcnow(),
        )
        db.add(orm)
        created_ids.append(ticket_id)
    db.commit()
    return {"created": len(created_ids), "ticket_ids": created_ids}


# ---------------------------------------------------------------------------
# AI Processing Pipeline
# ---------------------------------------------------------------------------

@app.post("/process_ticket/{ticket_id}", response_model=ProcessResult, tags=["AI Pipeline"])
async def process_ticket(
    ticket_id: str,
    mode: OperationalMode = Query(OperationalMode.ASSISTED),
    db: Session = Depends(get_db),
):
    orm = db.query(TicketORM).filter(TicketORM.ticket_id == ticket_id).first()
    if not orm:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Update status to processing
    orm.status = TicketStatus.PROCESSING
    db.commit()

    start_ms = time.time()

    # 1. Classify
    classifier = get_classifier()
    classification = await classifier.classify(orm.body, orm.subject)

    # 2. Retrieve context
    retrieval = await rag_service.retrieve(f"{orm.subject} {orm.body}")

    # 3. Generate draft
    draft = await generation_service.generate_response(orm.body, classification, retrieval)

    # 4. Evaluate escalation
    escalation = escalation_service.evaluate_escalation(orm.body, classification, draft, retrieval)

    # 5. Determine final status
    if escalation:
        final_status = TicketStatus.ESCALATED
    elif mode == OperationalMode.AUTONOMOUS and draft.confidence_score >= 0.75:
        final_status = TicketStatus.RESOLVED
    else:
        final_status = TicketStatus.PENDING_REVIEW

    processing_time_ms = int((time.time() - start_ms) * 1000)

    # Persist classification
    cls_orm = ClassificationORM(
        ticket_id=ticket_id,
        intent=classification.intent.value,
        urgency_score=classification.urgency_score,
        sentiment=classification.sentiment.value,
        confidence=classification.confidence,
        keywords=classification.keywords,
        sub_topics=classification.sub_topics,
    )
    db.merge(cls_orm)

    # Persist draft
    draft_orm = ResponseDraftORM(
        ticket_id=ticket_id,
        response_draft=draft.response_draft,
        confidence_score=draft.confidence_score,
        requires_human_review=draft.requires_human_review,
        tone=draft.tone,
        estimated_resolution_time=draft.estimated_resolution_time,
        suggested_knowledge_articles=draft.suggested_knowledge_articles,
    )
    db.merge(draft_orm)

    # Persist escalation
    if escalation:
        esc_orm = EscalationORM(
            ticket_id=ticket_id,
            issue_summary=escalation.issue_summary,
            suggested_actions=escalation.suggested_actions,
            context_bundle=escalation.context_bundle,
            escalation_reasons=[r.value for r in escalation.escalation_reasons],
            risk_level=escalation.risk_level,
            assigned_team=escalation.assigned_team,
        )
        db.merge(esc_orm)

    # Update ticket status
    orm.status = final_status
    orm.updated_at = datetime.utcnow()
    orm.resolution_time_ms = processing_time_ms
    db.commit()

    await _broadcast({
        "event": "ticket_processed",
        "ticket_id": ticket_id,
        "status": final_status,
        "intent": classification.intent.value,
        "urgency": classification.urgency_score,
    })

    return ProcessResult(
        ticket_id=ticket_id,
        classification=classification,
        retrieval=retrieval,
        draft=draft,
        escalation=escalation,
        status=final_status,
        mode=mode,
        processing_time_ms=processing_time_ms,
    )


# ---------------------------------------------------------------------------
# Ticket Queries
# ---------------------------------------------------------------------------

@app.get("/tickets", response_model=List[TicketListItem], tags=["Tickets"])
async def list_tickets(
    status: Optional[str] = None,
    intent: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(TicketORM)
    if status:
        q = q.filter(TicketORM.status == status)
    results = q.order_by(TicketORM.timestamp.desc()).limit(limit).all()
    output = []
    for t in results:
        cls = t.classification
        item = TicketListItem(
            ticket_id=t.ticket_id,
            subject=t.subject,
            status=t.status,
            urgency_score=cls.urgency_score if cls else 0.0,
            intent=cls.intent if cls else None,
            sentiment=cls.sentiment if cls else None,
            timestamp=t.timestamp,
        )
        if intent and item.intent != intent:
            continue
        output.append(item)
    return output


@app.get("/ticket/{ticket_id}", tags=["Tickets"])
async def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    orm = db.query(TicketORM).filter(TicketORM.ticket_id == ticket_id).first()
    if not orm:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket = Ticket(
        ticket_id=orm.ticket_id,
        user_id=orm.user_id,
        subject=orm.subject,
        body=orm.body,
        source=orm.source,
        timestamp=orm.timestamp,
        status=orm.status,
        priority=orm.priority,
        tags=orm.tags or [],
    )

    cls = orm.classification
    classification = None
    if cls:
        from app.models.schema import Intent, Sentiment
        classification = ClassificationResult(
            intent=cls.intent, urgency_score=cls.urgency_score,
            sentiment=cls.sentiment, confidence=cls.confidence,
            keywords=cls.keywords or [], sub_topics=cls.sub_topics or [],
        )

    draft = None
    if orm.response_draft:
        d = orm.response_draft
        draft = ResponseDraft(
            response_draft=d.response_draft, confidence_score=d.confidence_score,
            requires_human_review=d.requires_human_review, tone=d.tone,
            estimated_resolution_time=d.estimated_resolution_time,
            suggested_knowledge_articles=d.suggested_knowledge_articles or [],
        )

    escalation = None
    if orm.escalation:
        e = orm.escalation
        escalation = EscalationSummary(
            issue_summary=e.issue_summary, suggested_actions=e.suggested_actions,
            context_bundle=e.context_bundle or [], escalation_reasons=e.escalation_reasons or [],
            risk_level=e.risk_level, assigned_team=e.assigned_team,
        )

    return {
        "ticket": ticket,
        "processed_data": {
            "classification": classification,
            "draft": draft,
            "escalation": escalation,
            "status": orm.status,
        } if classification else None,
    }


@app.delete("/ticket/{ticket_id}", tags=["Tickets"])
async def delete_ticket(ticket_id: str, db: Session = Depends(get_db)):
    orm = db.query(TicketORM).filter(TicketORM.ticket_id == ticket_id).first()
    if not orm:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.delete(orm)
    db.commit()
    return {"status": "deleted", "ticket_id": ticket_id}


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

@app.post("/feedback", response_model=FeedbackRecord, tags=["Feedback"])
async def store_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    orm = db.query(TicketORM).filter(TicketORM.ticket_id == feedback.ticket_id).first()
    if not orm:
        raise HTTPException(status_code=404, detail="Ticket not found")

    feedback_id = str(uuid.uuid4())
    fb_orm = FeedbackORM(
        feedback_id=feedback_id,
        ticket_id=feedback.ticket_id,
        human_edited_response=feedback.human_edited_response,
        resolution_status=feedback.resolution_status,
        feedback_notes=feedback.feedback_notes,
        rating=feedback.rating,
        was_escalation_correct=feedback.was_escalation_correct,
        submitted_at=datetime.utcnow(),
    )
    db.merge(fb_orm)

    # Mark ticket resolved/closed
    if feedback.resolution_status in ("resolved", "closed"):
        orm.status = TicketStatus.CLOSED
        orm.updated_at = datetime.utcnow()
    db.commit()

    await _broadcast({"event": "ticket_resolved", "ticket_id": feedback.ticket_id})

    return FeedbackRecord(feedback_id=feedback_id, submitted_at=datetime.utcnow(), **feedback.dict())


# ---------------------------------------------------------------------------
# Analytics & Metrics
# ---------------------------------------------------------------------------

@app.get("/metrics", response_model=OperationalMetrics, tags=["Analytics"])
async def get_metrics(db: Session = Depends(get_db)):
    all_tickets = db.query(TicketORM).all()
    processed = [t for t in all_tickets if t.classification]
    escalated = [t for t in all_tickets if t.status == TicketStatus.ESCALATED]
    resolved  = [t for t in all_tickets if t.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)]
    pending   = [t for t in all_tickets if t.status == TicketStatus.PENDING_REVIEW]

    avg_conf = 0.0
    if processed:
        avg_conf = sum(t.classification.confidence for t in processed) / len(processed)

    avg_res_time = 0.0
    timed = [t for t in all_tickets if t.resolution_time_ms]
    if timed:
        avg_res_time = sum(t.resolution_time_ms for t in timed) / len(timed)

    total = len(all_tickets)
    now = datetime.utcnow()
    last_hour = [t for t in all_tickets if t.timestamp and (now - t.timestamp).total_seconds() < 3600]
    last_24h  = [t for t in all_tickets if t.timestamp and (now - t.timestamp).total_seconds() < 86400]

    # Distributions
    intent_dist: dict = {}
    sentiment_dist: dict = {}
    source_dist: dict = {}
    for t in processed:
        c = t.classification
        intent_dist[c.intent]   = intent_dist.get(c.intent, 0) + 1
        sentiment_dist[c.sentiment] = sentiment_dist.get(c.sentiment, 0) + 1
        source_dist[t.source] = source_dist.get(t.source, 0) + 1

    return OperationalMetrics(
        total_processed=total,
        resolved_count=len(resolved),
        escalated_count=len(escalated),
        pending_count=len(pending),
        avg_confidence=round(avg_conf, 4),
        avg_resolution_time_ms=round(avg_res_time, 2),
        auto_resolve_rate=round(len(resolved) / total, 4) if total else 0.0,
        escalation_rate=round(len(escalated) / total, 4) if total else 0.0,
        top_intents=intent_dist,
        sentiment_distribution=sentiment_dist,
        source_distribution=source_dist,
        tickets_last_hour=len(last_hour),
        tickets_last_24h=len(last_24h),
    )


@app.get("/analytics", response_model=AnalyticsDashboard, tags=["Analytics"])
async def get_analytics(db: Session = Depends(get_db)):
    metrics = await get_metrics(db)
    # Build time series for the last 24 hours (1h buckets)
    all_tickets = db.query(TicketORM).all()
    now = datetime.utcnow()
    confidence_trend, volume_trend = [], []
    for h in range(23, -1, -1):
        bucket_start = now - timedelta(hours=h + 1)
        bucket_end   = now - timedelta(hours=h)
        bucket = [
            t for t in all_tickets
            if t.timestamp and bucket_start <= t.timestamp < bucket_end
        ]
        ts = bucket_end.strftime("%H:%M")
        volume_trend.append(TimeSeriesPoint(timestamp=ts, value=len(bucket)))
        if bucket:
            conf = [t.classification.confidence for t in bucket if t.classification]
            avg = sum(conf) / len(conf) if conf else 0.0
        else:
            avg = 0.0
        confidence_trend.append(TimeSeriesPoint(timestamp=ts, value=round(avg, 4)))

    return AnalyticsDashboard(
        metrics=metrics,
        confidence_trend=confidence_trend,
        volume_trend=volume_trend,
    )


# ---------------------------------------------------------------------------
# Knowledge Base Management
# ---------------------------------------------------------------------------

@app.get("/knowledge-base", response_model=List[KnowledgeArticle], tags=["Knowledge Base"])
async def list_knowledge_articles(
    category: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(KnowledgeArticleORM)
    if category:
        q = q.filter(KnowledgeArticleORM.category == category)
    articles = q.limit(limit).all()
    return [
        KnowledgeArticle(
            article_id=a.article_id, title=a.title, content=a.content,
            category=a.category, tags=a.tags or [],
            created_at=a.created_at, updated_at=a.updated_at,
            views=a.views, helpful_votes=a.helpful_votes,
        )
        for a in articles
    ]


@app.post("/knowledge-base", response_model=KnowledgeArticle, tags=["Knowledge Base"])
async def create_knowledge_article(article: KnowledgeArticleCreate, db: Session = Depends(get_db)):
    article_id = str(uuid.uuid4())
    now = datetime.utcnow()
    orm = KnowledgeArticleORM(
        article_id=article_id,
        title=article.title,
        content=article.content,
        category=article.category,
        tags=article.tags,
        created_at=now,
    )
    db.add(orm)
    db.commit()

    # Also index in ChromaDB
    await rag_service.add_article(article, article_id)

    return KnowledgeArticle(
        article_id=article_id,
        title=article.title,
        content=article.content,
        category=article.category,
        tags=article.tags,
        created_at=now,
    )


@app.get("/knowledge-base/search", tags=["Knowledge Base"])
async def search_knowledge_base(q: str, limit: int = 5):
    """Semantic search over the knowledge base via ChromaDB."""
    retrieval = await rag_service.retrieve(q, k=limit)
    return {
        "query": q,
        "results": [
            {"content": c, "source": s, "similarity": sc}
            for c, s, sc in zip(
                retrieval.context,
                retrieval.sources or [],
                retrieval.similarity_scores or [],
            )
        ],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
