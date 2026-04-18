# Autonomous Support Operations Agent

A production-grade, autonomous AI Customer Support Operations Agent designed to replace Tier-1 support by autonomously ingesting, classifying, and resolving tickets using RAG-based context retrieval and LLM-powered response generation.

## Project Overview

This system is built to handle customer support tickets with high efficiency. It uses a Retrieval-Augmented Generation (RAG) architecture to provide accurate, context-aware responses. The agent can operate in two modes:
- **Autonomous**: Automatically resolves tickets if confidence is high.
- **Assisted**: Prepares a draft response for a human agent to review.

The system includes a robust escalation engine for high-risk or ambiguous cases and a feedback loop for continuous improvement.

## Features

- **Automated Ingestion**: Seamlessly ingest tickets from various sources.
- **AI Classification**: Intelligent classification of tickets based on intent and urgency.
- **RAG-based Retrieval**: Deep search into documentation and past tickets using ChromaDB.
- **Smart Response Generation**: Context-aware draft generation using OpenAI GPT models.
- **Escalation Engine**: Automatically flags complex or high-risk tickets for human intervention.
- **Feedback Loop**: Enables continuous learning based on human corrections and feedback.
- **Metrics Dashboard**: Comprehensive observability with real-time tracking of resolution rates and confidence scores.

## Architecture

### Backend
- **Framework**: FastAPI (Python)
- **Vector Database**: ChromaDB for RAG retrieval
- **LLM**: OpenAI GPT models
- **Database**: SQLAlchemy for persistent storage (In-memory used for demo)
- **Data Processing**: Pandas, NumPy

### Frontend
- **Structure**: Semantic HTML5
- **Styling**: Vanilla CSS with a modern, high-fidelity dark mode aesthetic
- **Logic**: Vanilla JavaScript for real-time interaction with the API

## Getting Started

### Prerequisites
- Python 3.9 or higher
- Node.js (for serving frontend, or use any static server)
- OpenAI API Key

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables in a `.env` file:
   ```env
   OPENAI_API_KEY=your_api_key_here
   DATABASE_URL=sqlite:///./support_agent.db
   CHROMA_DB_PATH=./chroma_db
   ```

5. Run the server:
   ```bash
   python -m app.main
   ```
   The backend will be available at `http://localhost:8000`.

### Frontend Setup

The frontend is a static web application. You can serve it using any HTTP server. For example:

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Run a simple local server:
   ```bash
   python -m http.server 8080
   ```
   The application will be accessible at `http://localhost:8080`.

## Project Structure

```text
support-ops-agent/
├── backend/
│   ├── app/
│   │   ├── models/       # Data models and schemas
│   │   ├── services/     # Core logic (RAG, Classification, Escalation)
│   │   └── main.py       # FastAPI routes and server entry point
│   ├── requirements.txt  # Python dependencies
│   └── .env              # Environment configuration
├── frontend/
│   ├── index.html        # Main dashboard interface
│   ├── style.css         # Custom premium styling
│   └── script.js         # Frontend logic and API integration
└── demo.py               # Script to simulate ticket flow
```

## Usage

1. Start the backend server.
2. Open the frontend dashboard in your browser.
3. Use the "Ingest Ticket" feature to add new support requests.
4. Monitor the "Live Feed" as the AI processes, classifies, and drafts responses.
5. Review escalated tickets in the "Escalation Buffer".
6. View system performance in the "Operations Overview" metrics section.
