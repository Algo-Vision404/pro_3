# Nexus Support AI - Cognitive Operations Platform

A production-grade, autonomous AI Customer Support Operations Platform designed to supercharge Tier-1 support. Nexus autonomously ingests, classifies, and resolves tickets utilizing a high-performance RAG-based context retrieval engine, LLM-powered synthesis, and an immersive, state-of-the-art Cognitive Command Center.

## Project Overview

This system is built to handle customer support tickets with unparalleled efficiency and intelligence. It employs a Retrieval-Augmented Generation (RAG) architecture to produce accurate, contextually-aware resolutions. The agent operates in two core modalities:
- **Autonomous Mode**: Intelligently resolves tickets end-to-end when confidence scores exceed safety thresholds.
- **Assisted Mode**: Synthesizes a high-accuracy draft response, routing it to human operators for final approval in the Command Center.

The platform is fortified by a robust escalation engine for high-risk or ambiguous cases, alongside a continuous-learning feedback loop.

## Key Features

- **Automated Ingestion**: Ingest high-volume support streams from multifaceted sources (Email, API, Webhooks).
- **Cognitive Classification**: Intelligent, deep-learning based classification of intent, sentiment, and urgency scoring.
- **RAG Context Retrieval**: Rapid semantic search into institutional knowledge bases and historical resolutions via ChromaDB.
- **Draft Synthesis**: Highly accurate, context-aware draft generation using advanced OpenAI GPT pipelines.
- **Escalation Engine**: Autonomous flagging of complex, high-liability, or emotionally charged tickets.
- **Feedback Loop**: Continuous reinforcement learning driven by human operator edits and approvals.
- **Cognitive Command Center**: A premium, high-fidelity UI featuring glassmorphism, dynamic metrics, active system health monitoring, and fluid micro-animations.

## Architecture

### Backend Engine
- **Framework**: FastAPI (Python) - Async, high-throughput API routing.
- **Vector Storage**: ChromaDB for rapid RAG semantic retrieval.
- **LLM Layer**: OpenAI GPT models for NLP processing and synthesis.
- **Database**: SQLAlchemy for persistent transactional storage (In-memory used for demo environments).
- **Data Processing**: Pandas, NumPy for metric aggregation.

### Frontend Command Center
- **Structure**: Semantic HTML5 with dynamic injection.
- **Design System**: Premium "Deep Dark" aesthetic featuring advanced glassmorphism, dynamic gradients, glowing accents, and modern typography (Inter & Outfit).
- **Interaction Logic**: Vanilla JavaScript driving real-time metric polling, responsive modals, and dynamic data binding.

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js (or any static HTTP server for the frontend)
- OpenAI API Key

### Backend Initialization

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Provision and activate the virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install platform dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment parameters in `.env`:
   ```env
   OPENAI_API_KEY=your_api_key_here
   DATABASE_URL=sqlite:///./support_agent.db
   CHROMA_DB_PATH=./chroma_db
   ```

5. Ignite the backend server:
   ```bash
   python -m app.main
   ```
   The engine will initialize and bind to `http://localhost:8000`.

### Frontend Initialization

The Cognitive Command Center is a static web application, engineered for rapid deployment.

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Boot a local server:
   ```bash
   python -m http.server 8080
   ```
   Access the command center at `http://localhost:8080`.

## Directory Architecture

```text
nexus-support-ai/
├── backend/
│   ├── app/
│   │   ├── models/       # Pydantic schemas and SQLAlchemy models
│   │   ├── services/     # Core logic engines (RAG, Classification, Escalation)
│   │   └── main.py       # FastAPI router and entry point
│   ├── requirements.txt  # Core dependencies
│   └── .env              # Environment configurations
├── frontend/
│   ├── index.html        # Cognitive Command Center UI
│   ├── style.css         # Premium glassmorphic design system
│   └── script.js         # Reactive UI state and API integrations
└── demo.py               # Synthetic ticket pipeline simulator
```

## Platform Operations

1. Spin up the backend API engine.
2. Launch the frontend and open the Cognitive Command Center in a modern browser.
3. Utilize the **"Ingest Synthetic Ticket"** tool to simulate incoming support requests from various vectors.
4. Monitor the Real-time Queue as the AI autonomously processes, classifies, and synthesizes drafts.
5. Review, edit, and approve drafts inside the modal interface to close the feedback loop.
6. Observe system health and telemetry through the integrated AI Metrics dashboard.
