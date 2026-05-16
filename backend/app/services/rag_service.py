"""
RAG Service — ChromaDB-backed retrieval with an embedded knowledge base.
Seeds the vector store on first startup with ~20 knowledge articles.
Falls back gracefully to empty context if ChromaDB is unavailable.
"""
import os
import uuid
import logging
from typing import List, Dict, Any
from datetime import datetime

from app.models.schema import RetrievalResult, KnowledgeArticle, KnowledgeArticleCreate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed knowledge base
# ---------------------------------------------------------------------------
_SEED_ARTICLES = [
    {
        "title": "How to Reset Your Password",
        "content": (
            "To reset your password, navigate to the login page and click 'Forgot Password'. "
            "Enter your registered email address. You will receive an email with a secure reset link "
            "within 5 minutes. Click the link, enter a new password, and confirm it. "
            "If you don't receive the email, check your spam folder or contact support."
        ),
        "category": "account_access",
        "tags": ["password", "reset", "login", "account"],
    },
    {
        "title": "Understanding Your Invoice",
        "content": (
            "Your invoice is generated on the first day of each billing cycle. "
            "It lists all charges for the current period including subscription fees, usage overages, and add-ons. "
            "You can download past invoices from Settings > Billing > Invoice History. "
            "If you see an unexpected charge, please contact our billing team within 30 days."
        ),
        "category": "billing",
        "tags": ["invoice", "billing", "charges", "statement"],
    },
    {
        "title": "Refund and Cancellation Policy",
        "content": (
            "We offer a full refund within 14 days of the initial purchase or subscription start date. "
            "After 14 days, refunds are prorated for annual plans and not available for monthly plans. "
            "To request a refund, contact support with your account email and order ID. "
            "Cancellations take effect at the end of the current billing period."
        ),
        "category": "billing",
        "tags": ["refund", "cancellation", "policy", "money back"],
    },
    {
        "title": "API Rate Limiting",
        "content": (
            "Our API enforces rate limits to ensure platform stability. "
            "Standard tier: 100 requests/minute. Professional tier: 1,000 requests/minute. "
            "Enterprise tier: unlimited with dedicated infrastructure. "
            "If you receive a 429 Too Many Requests error, implement exponential backoff. "
            "You can monitor your usage in the dashboard under Settings > API > Usage."
        ),
        "category": "technical_support",
        "tags": ["api", "rate limit", "429", "quota"],
    },
    {
        "title": "Two-Factor Authentication Setup",
        "content": (
            "Two-Factor Authentication (2FA) adds an extra security layer to your account. "
            "To enable: Go to Settings > Security > Two-Factor Authentication. "
            "Scan the QR code with an authenticator app (Google Authenticator or Authy recommended). "
            "Enter the 6-digit code to verify. Store your backup codes in a safe location. "
            "If you lose access to your authenticator, use a backup code or contact support."
        ),
        "category": "account_access",
        "tags": ["2fa", "security", "authenticator", "mfa"],
    },
    {
        "title": "Data Export Guide",
        "content": (
            "You can export your data at any time from Settings > Data & Privacy > Export Data. "
            "Available export formats: CSV, JSON, and XLSX. "
            "Large exports are processed asynchronously and emailed to you within 2 hours. "
            "Exports include: activity logs, transactions, user profiles, and custom configurations. "
            "Data is retained for 30 days after account cancellation."
        ),
        "category": "general_inquiry",
        "tags": ["export", "csv", "data", "download", "compliance"],
    },
    {
        "title": "Troubleshooting Login Issues",
        "content": (
            "If you cannot log in: 1) Clear browser cache and cookies. "
            "2) Try an incognito/private window. 3) Disable browser extensions. "
            "4) Ensure your email is verified — check for a verification email. "
            "5) Confirm Caps Lock is off. 6) Try resetting your password. "
            "7) If using SSO, contact your IT administrator. "
            "If issues persist after these steps, contact support with your browser version and error screenshot."
        ),
        "category": "account_access",
        "tags": ["login", "troubleshoot", "sso", "browser", "cache"],
    },
    {
        "title": "Subscription Plans Comparison",
        "content": (
            "Starter Plan: $9/month — Up to 5 users, 10GB storage, email support. "
            "Professional Plan: $29/month — Up to 25 users, 100GB storage, priority support, API access. "
            "Enterprise Plan: Custom pricing — Unlimited users, dedicated infrastructure, SLA, custom integrations. "
            "Annual billing saves 20% compared to monthly. "
            "You can upgrade or downgrade your plan at any time from Settings > Subscription."
        ),
        "category": "billing",
        "tags": ["pricing", "plans", "subscription", "upgrade"],
    },
    {
        "title": "Webhook Integration Guide",
        "content": (
            "Webhooks allow real-time event notifications to your endpoint. "
            "Configure webhooks under Settings > Integrations > Webhooks. "
            "Available events: ticket.created, ticket.resolved, user.signup, payment.failed. "
            "We sign all webhook payloads with HMAC-SHA256. Verify the X-Nexus-Signature header. "
            "Retry policy: up to 5 retries with exponential backoff on non-2xx responses."
        ),
        "category": "technical_support",
        "tags": ["webhook", "integration", "api", "events"],
    },
    {
        "title": "Double Charge Investigation Process",
        "content": (
            "If you believe you have been charged twice: "
            "1) Check your bank statement — some banks show pending and settled charges simultaneously. "
            "2) Log in and navigate to Settings > Billing > Transaction History. "
            "3) If two distinct charges exist, contact support immediately with the transaction IDs. "
            "We will investigate within 1 business day and process any valid refund within 5-7 business days. "
            "Include your account email and the last 4 digits of the card charged."
        ),
        "category": "billing",
        "tags": ["double charge", "duplicate payment", "refund", "billing error"],
    },
    {
        "title": "Account Cancellation Process",
        "content": (
            "To cancel your account: Go to Settings > Subscription > Cancel Subscription. "
            "Your data and access remain until the end of the current billing period. "
            "After cancellation, your data is archived for 90 days before permanent deletion. "
            "You can reactivate within 90 days without data loss. "
            "Note: Cancellation does not automatically trigger a refund unless within the 14-day window."
        ),
        "category": "cancellation",
        "tags": ["cancel", "cancellation", "close account", "subscription"],
    },
    {
        "title": "Feature Request Submission",
        "content": (
            "We value your feedback! To submit a feature request: "
            "1) Visit our public roadmap at roadmap.nexus.ai. "
            "2) Search for existing requests — upvote if found. "
            "3) Submit a new request with a clear title and use-case description. "
            "Our product team reviews all submissions monthly. "
            "High-upvote features are prioritized for the next release cycle."
        ),
        "category": "feature_request",
        "tags": ["feature", "request", "roadmap", "suggestion"],
    },
    {
        "title": "Storage and File Upload Limits",
        "content": (
            "Maximum file upload size: 25MB per file. "
            "Supported file types: PDF, DOCX, XLSX, CSV, PNG, JPG, ZIP. "
            "Total storage: depends on your plan (see Subscription Plans). "
            "Files are automatically compressed for efficient storage. "
            "Exceeding your storage limit will prevent new uploads until you upgrade or delete files."
        ),
        "category": "general_inquiry",
        "tags": ["storage", "upload", "file", "limit", "size"],
    },
    {
        "title": "Security Best Practices",
        "content": (
            "Protect your account: Use a strong, unique password (12+ characters, mixed case, numbers, symbols). "
            "Enable 2FA for all users. Review active sessions under Settings > Security > Active Sessions. "
            "Never share your API key — rotate it immediately if compromised. "
            "We will never ask for your password via email or phone. "
            "Suspicious activity? Contact security@nexus.ai immediately."
        ),
        "category": "technical_support",
        "tags": ["security", "password", "2fa", "best practices", "api key"],
    },
    {
        "title": "Integration with Third-Party Tools",
        "content": (
            "Nexus integrates with: Slack, Jira, Salesforce, HubSpot, Zapier, and more. "
            "Native integrations are available under Settings > Integrations. "
            "For custom integrations, use our REST API with OAuth2 authentication. "
            "Zapier allows no-code automation with 3,000+ apps. "
            "Contact enterprise@nexus.ai for bespoke integration support."
        ),
        "category": "technical_support",
        "tags": ["integration", "slack", "zapier", "api", "oauth"],
    },
]


# ---------------------------------------------------------------------------
# RAG Service
# ---------------------------------------------------------------------------

class RAGService:
    def __init__(self, collection_name: str = "nexus_knowledge_base"):
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._init_client()

    def _init_client(self):
        import chromadb
        # Try persistent storage first, fall back to in-memory on any error
        try:
            os.makedirs("./data/chroma_db", exist_ok=True)
            self.client = chromadb.PersistentClient(path="./data/chroma_db")
            logger.info("ChromaDB: using persistent storage.")
        except Exception as e:
            logger.warning(f"ChromaDB persistent init failed ({e}), switching to in-memory.")
            try:
                self.client = chromadb.EphemeralClient()
                logger.info("ChromaDB: using in-memory (ephemeral) client.")
            except Exception as e2:
                logger.error(f"ChromaDB unavailable entirely: {e2}")
                self.client = None
                self.collection = None
                return

        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            if self.collection.count() == 0:
                self._seed_knowledge_base()
            logger.info(f"ChromaDB ready. {self.collection.count()} documents indexed.")
        except Exception as e:
            logger.error(f"ChromaDB collection error: {e}")
            self.client = None
            self.collection = None

    def _seed_knowledge_base(self):
        """Seed the vector store with default knowledge articles."""
        documents, metadatas, ids = [], [], []
        for i, article in enumerate(_SEED_ARTICLES):
            article_id = f"seed-{i:03d}"
            documents.append(f"{article['title']}. {article['content']}")
            metadatas.append({
                "title": article["title"],
                "category": article["category"],
                "tags": ", ".join(article["tags"]),
                "article_id": article_id,
            })
            ids.append(article_id)
        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        logger.info(f"Seeded {len(documents)} knowledge articles.")

    async def retrieve(self, query: str, k: int = 3) -> RetrievalResult:
        if self.collection is None:
            return RetrievalResult(context=[], metadata=[], similarity_scores=[], sources=[])

        try:
            results = self.collection.query(query_texts=[query], n_results=min(k, self.collection.count() or k))
            docs      = results.get("documents", [[]])[0]
            metas     = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            # ChromaDB returns cosine distance (lower=better). Convert to similarity.
            similarities = [round(1.0 - d, 4) for d in distances]
            sources = [m.get("title", "Unknown") for m in metas]

            return RetrievalResult(
                context=docs,
                metadata=metas,
                similarity_scores=similarities,
                sources=sources,
            )
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return RetrievalResult(context=[], metadata=[], similarity_scores=[], sources=[])

    async def add_article(self, article: KnowledgeArticleCreate, article_id: str):
        if self.collection is None:
            return
        try:
            document = f"{article.title}. {article.content}"
            self.collection.add(
                documents=[document],
                metadatas=[{
                    "title": article.title,
                    "category": article.category,
                    "tags": ", ".join(article.tags),
                    "article_id": article_id,
                }],
                ids=[article_id],
            )
        except Exception as e:
            logger.error(f"Failed to add article to ChromaDB: {e}")

    def get_collection_count(self) -> int:
        if self.collection is None:
            return 0
        try:
            return self.collection.count()
        except Exception:
            return 0


rag_service = RAGService()
