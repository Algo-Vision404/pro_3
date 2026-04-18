import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from app.models.schema import (
    Ticket, TicketCreate, TicketSource, 
    ClassificationResult, ResponseDraft, 
    EscalationSummary, FeedbackCreate,
    OperationalMode
)
from app.services.classification_service import get_classifier
from app.services.rag_service import rag_service
from app.services.generation_service import generation_service
from app.services.escalation_service import escalation_service

app = FastAPI(title="AI Support Ops Agent")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for demo (should be DB in production)
tickets_db = {}
metrics = {
    "total_processed": 0,
    "resolved_count": 0,
    "escalated_count": 0,
    "avg_confidence": 0.0
}

@app.post("/ingest_ticket", response_model=Ticket)
async def ingest_ticket(ticket_in: TicketCreate):
    ticket_id = str(uuid.uuid4())
    ticket = Ticket(
        ticket_id=ticket_id,
        timestamp=datetime.now(),
        **ticket_in.dict()
    )
    tickets_db[ticket_id] = {
        "ticket": ticket,
        "processed_data": None
    }
    return ticket

@app.post("/process_ticket/{ticket_id}")
async def process_ticket(
    ticket_id: str, 
    mode: OperationalMode = Query(OperationalMode.ASSISTED)
):
    if ticket_id not in tickets_db:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket_data = tickets_db[ticket_id]
    ticket = ticket_data["ticket"]
    
    # 1. Classify
    classifier = get_classifier()
    classification = await classifier.classify(ticket.body)
    
    # 2. Retrieve context
    retrieval = await rag_service.retrieve(ticket.body)
    
    # 3. Generate Draft
    draft = await generation_service.generate_response(ticket.body, classification, retrieval)
    
    # 4. Evaluate Escalation
    escalation = escalation_service.evaluate_escalation(ticket.body, classification, draft, retrieval)
    
    # Store processed data
    process_result = {
        "classification": classification,
        "retrieval": retrieval,
        "draft": draft,
        "escalation": escalation,
        "mode": mode,
        "status": "escalated" if escalation else "resolved" if mode == OperationalMode.AUTONOMOUS else "pending_review"
    }
    tickets_db[ticket_id]["processed_data"] = process_result
    
    # Update metrics
    metrics["total_processed"] += 1
    if escalation:
        metrics["escalated_count"] += 1
    elif mode == OperationalMode.AUTONOMOUS:
        metrics["resolved_count"] += 1
    
    return process_result

@app.get("/tickets")
async def list_tickets():
    return [
        {
            "ticket_id": tid,
            "subject": data["ticket"].subject,
            "status": data["processed_data"]["status"] if data["processed_data"] else "new",
            "urgency_score": data["processed_data"]["classification"].urgency_score if data["processed_data"] else 0
        }
        for tid, data in tickets_db.items()
    ]

@app.get("/ticket/{ticket_id}")
async def get_ticket(ticket_id: str):
    if ticket_id not in tickets_db:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return tickets_db[ticket_id]

@app.post("/feedback")
async def store_feedback(feedback: FeedbackCreate):
    if feedback.ticket_id not in tickets_db:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # In practice, this would update the knowledge base or fine-tune models
    tickets_db[feedback.ticket_id]["feedback"] = feedback
    return {"status": "success", "message": "Feedback recorded"}

@app.get("/metrics")
async def get_metrics():
    return metrics

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
