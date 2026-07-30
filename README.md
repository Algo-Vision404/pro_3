# CogV8 Support AI — Cognitive Operations Platform

> **Production-grade, autonomous AI Customer Support Operations Platform.** CogV8 replaces Tier-1 support with an end-to-end intelligent pipeline: ticket ingestion -> classification -> RAG retrieval -> response synthesis -> escalation routing — all exposed through a premium, real-time Cognitive Command Center.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [API Reference](#api-reference)
- [System Architecture](#system-architecture)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)

---

## Overview

CogV8 operates in two modes:
| Mode | Behaviour |
|------|-----------| 
| **Assisted** | Generates a draft response and routes to a human operator for review |
| **Autonomous** | Auto-resolves tickets where AI confidence >= 75%, no human needed |

A six-rule **Escalation Engine** catches edge-cases (legal risk, extreme urgency, low confidence) and routes them to the appropriate human team with a full risk assessment.

---

## Architecture

### End-to-End Data Flow

```mermaid
flowchart TD
    A["Ticket Source - Email / API / Webhook"] -->|POST /ingest_ticket| B(FastAPI Router)
    B --> DB[("SQLite DB - SQLAlchemy ORM")]
    B -->|POST /process_ticket| C{AI Pipeline}

    subgraph C [AI Processing Pipeline]
        direction TB
        C1["1. Classification Engine - Rule-based keyword scoring - Intent, Urgency, Sentiment"]
        C2["2. RAG Retrieval - ChromaDB vector store - Semantic similarity search"]
        C3["3. Generation Engine - Template synthesis or GPT-4o-mini"]
        C4["4. Escalation Engine - 6-rule risk evaluator - Legal, Urgency, Confidence"]
        C1 --> C2 --> C3 --> C4
    end

    C --> DB
    C -->|WebSocket broadcast| WS["Live Feed - ws://localhost:8000/ws/live-feed"]
    DB -->|GET /metrics| METRICS[Analytics Engine]
    DB -->|GET /analytics| METRICS
    WS --> UI["Cognitive Command Center - localhost:8080"]
    METRICS --> UI
```

### Service Architecture

```mermaid
graph LR
    subgraph Frontend ["Frontend - Port 8080"]
        F1[Ticket Queue]
        F2[Analytics Dashboard]
        F3[Knowledge Base Viewer]
        F4["Modal: Ticket Detail"]
    end

    subgraph Backend ["Backend - Port 8000"]
        B1[FastAPI Router]
        B2[Classification Service]
        B3[RAG Service]
        B4[Generation Service]
        B5[Escalation Service]
        B6[SQLite + SQLAlchemy]
        B7[ChromaDB Vector Store]
    end

    F1 & F2 & F3 & F4 <-->|REST + WebSocket| B1
    B1 --> B2 --> B3 --> B4 --> B5
    B1 <--> B6
    B3 <--> B7
```

### Classification Engine — Intent Scoring

```mermaid
flowchart LR
    IN[Ticket Text] --> KWS["Keyword Scorer - Regex pattern matching - per Intent taxonomy"]
    KWS --> URG["Urgency Booster - Critical phrase detection"]
    KWS --> SENT["Sentiment Classifier - 5-tier: positive/neutral/negative/frustrated/urgent"]
    KWS --> INTENT["Intent Resolver - 9 categories"]
    URG & SENT --> CONF[Confidence Score]
    INTENT & CONF & SENT --> OUT[ClassificationResult]
```

### Escalation Decision Tree

```mermaid
flowchart TD
    START[Ticket Processed] --> R1{"Confidence < 60%?"}
    R1 -- Yes --> ESC
    R1 -- No --> R2{"Urgency > 80%?"}
    R2 -- Yes --> ESC
    R2 -- No --> R3{"Sensitive Intent? Account / Refund / Cancel"}
    R3 -- Yes --> ESC
    R3 -- No --> R4{"Extreme Sentiment? Frustrated or Urgent"}
    R4 -- Yes --> R4B{"Urgency > 60%?"}
    R4B -- Yes --> ESC
    R4B -- No --> R5{"Legal Keywords? lawyer / sue / breach"}
    R5 -- Yes --> ESC_CRITICAL["ESCALATE - Critical - Risk Level: Legal"]
    R5 -- No --> RESOLVE["Auto-resolve or Pending Review"]
    ESC["ESCALATE - High/Medium - Assign to Tier-2"]
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Smart Classification** | 9-intent, 5-sentiment rule-based engine with urgency scoring — works offline, no API key needed |
| **RAG Knowledge Base** | ChromaDB vector store pre-seeded with 15 knowledge articles; supports semantic search and article management |
| **Template Generation** | Rich per-intent, per-sentiment response templates; optionally upgrades to GPT-4o-mini if `OPENAI_API_KEY` is set |
| **Escalation Engine** | Six-rule risk evaluator: low confidence, high urgency, sensitive intents, extreme sentiment, legal signals |
| **SQLite Persistence** | Full SQLAlchemy ORM — all tickets, classifications, drafts, escalations, and feedback are persisted |
| **WebSocket Live Feed** | Real-time ticket events broadcast via `ws://localhost:8000/ws/live-feed` |
| **Analytics API** | Time-series volume & confidence trends, intent/sentiment distributions, resolution rates |
| **Health Check** | `/health` endpoint reports service status and latency for all subsystems |
| **Knowledge Base API** | Full CRUD + semantic search (`/knowledge-base/search?q=...`) |
| **Bulk Ingest** | `POST /bulk_ingest` accepts arrays of tickets for high-throughput scenarios |
| **Ticket Delete** | `DELETE /ticket/{id}` for audit and compliance workflows |

---

## API Reference

### Tickets
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingest_ticket` | Ingest a single ticket |
| `POST` | `/bulk_ingest` | Ingest multiple tickets |
| `POST` | `/process_ticket/{id}?mode=assisted\|autonomous` | Run AI pipeline on a ticket |
| `GET` | `/tickets?status=&intent=&limit=` | List tickets with optional filters |
| `GET` | `/ticket/{id}` | Get full ticket with AI results |
| `DELETE` | `/ticket/{id}` | Delete a ticket |

### Feedback & Learning
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/feedback` | Submit human edit, rating, and resolution status |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/metrics` | Live operational metrics |
| `GET` | `/analytics` | Full dashboard with 24h time-series trends |

### Knowledge Base
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/knowledge-base?category=` | List knowledge articles |
| `POST` | `/knowledge-base` | Add article (indexed in ChromaDB automatically) |
| `GET` | `/knowledge-base/search?q=` | Semantic search |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System health report |
| `GET` | `/docs` | Swagger interactive API docs |
| `WS` | `/ws/live-feed` | WebSocket event stream |

---

## System Architecture

```mermaid
block-beta
    columns 3

    block:INGESTION["Ingestion Layer"]:1
        columns 1
        i1["Email Source"]
        i2["API / Webhook"]
        i3["Bulk CSV"]
    end

    space

    block:FRONTEND["Presentation Layer"]:1
        columns 1
        f1["Cognitive Command Center (localhost:8080)"]
        f2["Live Ticket Queue"]
        f3["Analytics Dashboard"]
        f4["Knowledge Base Viewer"]
        f5["Ticket Detail Modal"]
    end

    INGESTION -- "POST /ingest_ticket" --> API
    FRONTEND <-- "REST + WebSocket" --> API

    block:API["API Gateway - FastAPI - localhost:8000"]:3
        columns 3
        a1["Ticket Endpoints /ingest /tickets /ticket/{id}"]
        a2["Pipeline Endpoint /process_ticket/{id}"]
        a3["System Endpoints /health /metrics /analytics /docs"]
        a4["Feedback Endpoint /feedback"]
        a5["Knowledge Base /knowledge-base /search"]
        a6["WebSocket /ws/live-feed"]
    end

    API --> PIPELINE

    block:PIPELINE["AI Processing Pipeline"]:3
        columns 3
        p1["Classification Engine - Rule-based keyword scoring - 9 intents, 5 sentiments - Urgency boosting"]
        p2["RAG Retrieval - ChromaDB semantic search - 15 seeded KB articles - Cosine similarity scoring"]
        p3["Generation Engine - Template library per intent + sentiment - Optional GPT-4o-mini"]
        space
        p4["Escalation Engine - 6-rule risk evaluator - Legal, Urgency, Confidence, Sentiment, Intent"]
        space
    end

    PIPELINE --> STORAGE

    block:STORAGE["Persistence Layer"]:2
        columns 2
        s1["SQLite (SQLAlchemy ORM) - Tickets, Classifications - Drafts, Escalations - Feedback, KB Articles"]
        s2["ChromaDB Vector Store - HNSW Index - Cosine Similarity - Persistent or Ephemeral"]
    end
```

### Layer Responsibilities

| Layer | Technology | Responsibility |
|-------|-----------|----------------|
| **Ingestion** | FastAPI REST | Accept tickets from Email, API, Webhooks, CSV bulk upload |
| **API Gateway** | FastAPI + Uvicorn | Route all requests, manage WebSocket connections, serve OpenAPI docs |
| **Classification** | Rule-based NLP | Detect intent (9 categories), sentiment (5 tiers), and urgency score |
| **RAG Retrieval** | ChromaDB + HNSW | Semantic vector search over knowledge base to inject relevant context |
| **Generation** | Template Engine / GPT-4o-mini | Synthesise empathetic, actionable response drafts with confidence scoring |
| **Escalation** | Rule Engine | Evaluate 6 risk rules; route high-risk tickets to human teams |
| **Persistence** | SQLite + SQLAlchemy | Persist all entities with relational integrity and full query support |
| **Presentation** | HTML/CSS/JS | Premium glassmorphic command center with real-time WebSocket updates |

---

## Getting Started

### Prerequisites
- Python 3.9+
- No API keys required to run in offline mode

### Backend

```bash
cd backend

# Create virtualenv
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start server (auto-creates DB and seeds knowledge base on first run)
python -m app.main
```
> API available at `http://localhost:8000` — Swagger docs at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
python -m http.server 8080
```
> Dashboard at `http://localhost:8080`

---

## Configuration

Create a `.env` file inside `backend/`:

```env
# Optional — enables GPT-4o-mini for response generation
OPENAI_API_KEY=sk-...

# Optional — override database (default: SQLite)
DATABASE_URL=sqlite:///./data/cogv8.db
# DATABASE_URL=postgresql://user:password@localhost/cogv8
```

Without an `OPENAI_API_KEY`, the system runs **fully offline** using the built-in template engine and rule-based classifier.

---

## Usage Guide

1. **Start both servers** (backend on `:8000`, frontend on `:8080`)
2. **Open the Command Center** at `http://localhost:8080`
3. Click **"Ingest Synthetic Ticket"** — the AI pipeline runs in under 100ms
4. Watch the **Live Queue** update with intent, urgency, and status
5. Click any ticket to open the **Ticket Modal** — review the AI draft, edit it, then click **Approve & Resolve**
6. Visit `http://localhost:8000/docs` to explore all API endpoints interactively
7. Run the bulk demo script: `python demo.py` (requires the backend to be running)
 Fix the architecture and flowchart in this readme, I think the design didn’t appear