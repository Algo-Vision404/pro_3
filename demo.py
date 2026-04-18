import asyncio
import httpx
import json
import time

BASE_URL = "http://localhost:8000"

async def run_demo():
    print("Starting AI Support Operations Agent Demo...")
    
    async with httpx.AsyncClient() as client:
        # 1. Ingest Ticket
        print("\nPhase 1: Ingesting a complex ticket...")
        ticket_payload = {
            "user_id": "cust_99",
            "subject": "CRITICAL: Cannot access my business account",
            "body": "I have a big presentation in 10 minutes and your login system is throwing 500 errors. My user ID is cust_99. FIX THIS NOW!!!",
            "source": "api"
        }
        
        response = await client.post(f"{BASE_URL}/ingest_ticket", json=ticket_payload)
        ticket = response.json()
        ticket_id = ticket["ticket_id"]
        print(f"Ticket Ingested. ID: {ticket_id}")

        # 2. Process Ticket
        print("\nPhase 2: Processing ticket through AI pipeline...")
        print("   (Classification -> RAG -> Generation -> Escalation)")
        
        process_response = await client.post(f"{BASE_URL}/process_ticket/{ticket_id}?mode=assisted")
        result = process_response.json()
        
        print(f"   - Intent Detected: {result['classification']['intent']}")
        print(f"   - Urgency Score: {result['classification']['urgency_score']}")
        print(f"   - Sentiment: {result['classification']['sentiment']}")
        
        # 3. Decision
        print("\n Phase 3: Autonomous Decision")
        if result['escalation']:
            print(f"    ACTION: ESCALATED")
            print(f"   Reason: {result['escalation']['issue_summary']}")
        else:
            print(f"    ACTION: AUTO-RESOLVED (DRAFT CREATED)")
            print(f"   AI Confidence: {result['draft']['confidence_score']}")

        # 4. View Draft
        print("\n AI Draft Response:")
        print(f"---")
        print(result['draft']['response_draft'])
        print(f"---")

        # 5. Metrics
        metrics_res = await client.get(f"{BASE_URL}/metrics")
        print(f"\n System Metrics: {json.dumps(metrics_res.json(), indent=2)}")

if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except Exception as e:
        print(f" Error: {e}")
        print(" Tip: Make sure the FastAPI server is running first (uvicorn main:app --reload)")
