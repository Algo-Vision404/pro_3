"""
Template-based response generation engine.
Produces context-aware, professional support drafts without any LLM dependency.
If OPENAI_API_KEY is present in the environment, real GPT synthesis is used instead.
"""
import os
import logging
from typing import List, Optional
from app.models.schema import (
    ResponseDraft, ClassificationResult, RetrievalResult, Intent, Sentiment
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Template library keyed by (intent, sentiment_tier)
# sentiment_tier: "urgent" | "frustrated" | "negative" | "neutral" | "positive"
# ---------------------------------------------------------------------------

_TEMPLATES = {
    Intent.BILLING: {
        "urgent": (
            "I completely understand the urgency here and I'm prioritising your case immediately.\n\n"
            "I've flagged your billing concern for our senior billing team to review within the next hour. "
            "To expedite the resolution, could you please confirm:\n"
            "- The transaction ID(s) visible in your bank statement or our billing portal\n"
            "- The approximate amount and date of the disputed charge\n\n"
            "I'll have a resolution update for you as soon as possible. "
            "You can also track this ticket's status in real time through your dashboard."
        ),
        "negative": (
            "Thank you for bringing this to our attention, and I sincerely apologise for the billing discrepancy.\n\n"
            "Our billing team will investigate the charge in question within 1 business day. "
            "To help us resolve this quickly, please provide the transaction reference from your invoice or bank statement.\n\n"
            "If a duplicate or erroneous charge is confirmed, a full refund will be processed within 5-7 business days. "
            "We appreciate your patience and will keep you updated throughout the process."
        ),
        "default": (
            "Thank you for contacting us about your billing inquiry.\n\n"
            "I've reviewed your account and our billing team is looking into this for you. "
            "You can view a complete breakdown of all charges in Settings > Billing > Transaction History.\n\n"
            "If you have any questions about specific charges, please reply with the transaction ID and we'll clarify immediately. "
            "We aim to resolve all billing inquiries within 24 hours."
        ),
    },
    Intent.REFUND_REQUEST: {
        "urgent": (
            "I understand you need this resolved urgently, and I'm escalating your refund request now.\n\n"
            "Our refund policy allows full refunds within 14 days of purchase. "
            "I'm initiating a review of your account immediately. "
            "If your request is within the eligible window, we will process the refund today.\n\n"
            "Please confirm your preferred refund method (original payment method or account credit). "
            "Refunds to bank cards typically appear within 5-7 business days."
        ),
        "default": (
            "Thank you for your refund request. I've logged it in our system and it's now under review.\n\n"
            "Per our refund policy, eligible refunds are processed within 5-7 business days to the original payment method. "
            "We'll send you a confirmation email once the refund has been initiated.\n\n"
            "If you'd prefer account credit, we can apply it immediately — just let us know your preference."
        ),
    },
    Intent.ACCOUNT_ACCESS: {
        "urgent": (
            "I understand being locked out of your account is critically disruptive — let's get you back in immediately.\n\n"
            "**Quickest resolution path:**\n"
            "1. Go to login page → click 'Forgot Password'\n"
            "2. Enter your registered email address\n"
            "3. Open the reset link (valid for 30 minutes)\n\n"
            "If the reset email doesn't arrive within 5 minutes, please check your spam folder. "
            "I've also triggered a manual verification on our end to unblock your account. "
            "You should regain access within the next 10 minutes."
        ),
        "default": (
            "Thank you for reaching out about your account access issue.\n\n"
            "Here are the fastest steps to regain access:\n"
            "1. Navigate to the login page and click 'Forgot Password'\n"
            "2. Enter your account email — a reset link will be sent within 5 minutes\n"
            "3. If using 2FA and you've lost access to your authenticator, use one of your backup codes\n\n"
            "If none of these steps work, please reply with your account email and user ID. "
            "Our security team can manually verify and restore your access."
        ),
    },
    Intent.TECHNICAL_SUPPORT: {
        "urgent": (
            "I'm on this immediately — a technical issue blocking your work is our highest priority.\n\n"
            "Our engineering team has been notified and is investigating. "
            "While they work on a fix, please try these steps:\n"
            "1. Clear your browser cache (Ctrl+Shift+Del) and reload\n"
            "2. Try an incognito window or a different browser\n"
            "3. Check our status page at status.nexus.ai for any known outages\n\n"
            "I'll send you an update within 30 minutes. Thank you for your patience."
        ),
        "default": (
            "Thank you for reporting this technical issue. I've logged it and assigned it to our technical team.\n\n"
            "To help us diagnose and resolve this faster, could you share:\n"
            "- Your browser and operating system version\n"
            "- Steps to reproduce the issue\n"
            "- Any error messages or screenshots\n\n"
            "In the meantime, you can check our system status at status.nexus.ai. "
            "We aim to respond to all technical issues within 4 hours."
        ),
    },
    Intent.BUG_REPORT: {
        "default": (
            "Thank you for taking the time to report this bug — this helps us improve the platform for everyone.\n\n"
            "I've filed a bug report in our engineering tracker. To help our team reproduce and fix this quickly, "
            "could you provide:\n"
            "- Exact steps to reproduce the issue\n"
            "- Expected vs. actual behaviour\n"
            "- Browser/OS version and any console error messages\n\n"
            "We prioritise bug fixes based on severity and impact. You'll receive an update once the fix is deployed."
        ),
    },
    Intent.FEATURE_REQUEST: {
        "default": (
            "Thank you for this feature suggestion — we love hearing ideas from our users!\n\n"
            "I've logged your request and shared it with our product team. "
            "You can also upvote this and see similar requests on our public roadmap at roadmap.nexus.ai.\n\n"
            "Features with the most votes are prioritised for upcoming sprints. "
            "We'll notify you by email if and when this feature is scheduled for development."
        ),
    },
    Intent.CANCELLATION: {
        "default": (
            "I'm sorry to hear you'd like to cancel. Before proceeding, I'd love to understand what's not working — "
            "there may be a solution that better fits your needs.\n\n"
            "If you do wish to proceed, you can cancel at any time in Settings > Subscription > Cancel Plan. "
            "Your access continues until the end of the current billing period, and your data is archived for 90 days.\n\n"
            "Is there anything I can help resolve that might change your mind? "
            "We value your feedback and want to make things right."
        ),
    },
    Intent.GENERAL_INQUIRY: {
        "default": (
            "Thank you for reaching out! I'm happy to help with your inquiry.\n\n"
            "{context_snippet}"
            "\n\nIs there anything more specific I can help you with? "
            "Our support team is available 24/7 and typically responds within 2 hours."
        ),
    },
    Intent.UNKNOWN: {
        "default": (
            "Thank you for contacting CogV8 Support.\n\n"
            "I've received your message and will make sure it gets to the right team. "
            "To ensure we can help you as quickly as possible, could you provide a bit more detail about your request?\n\n"
            "Our support team will follow up within 4 hours."
        ),
    },
}


def _get_sentiment_tier(sentiment: Sentiment) -> str:
    if sentiment in (Sentiment.URGENT,):
        return "urgent"
    if sentiment in (Sentiment.FRUSTRATED,):
        return "frustrated"
    if sentiment in (Sentiment.NEGATIVE,):
        return "negative"
    if sentiment in (Sentiment.POSITIVE,):
        return "positive"
    return "default"


def _build_context_snippet(retrieval: RetrievalResult) -> str:
    if not retrieval.context:
        return ""
    lines = []
    for i, (ctx, src) in enumerate(zip(retrieval.context[:2], retrieval.sources or [])):
        short = ctx[:300] + "..." if len(ctx) > 300 else ctx
        lines.append(f"**{src}**: {short}")
    return "\n\n".join(lines)


def _compute_confidence(
    classification: ClassificationResult,
    retrieval: RetrievalResult
) -> float:
    base = classification.confidence
    # Boost confidence if we retrieved relevant context
    if retrieval.similarity_scores:
        top_sim = retrieval.similarity_scores[0]
        base = base * 0.7 + top_sim * 0.3
    return round(min(max(base, 0.0), 1.0), 4)


def _estimate_resolution_time(intent: Intent, urgency: float) -> str:
    if urgency >= 0.85:
        return "< 1 hour (critical escalation)"
    if urgency >= 0.65:
        return "1-4 hours"
    times = {
        Intent.BILLING: "1 business day",
        Intent.REFUND_REQUEST: "5-7 business days",
        Intent.ACCOUNT_ACCESS: "< 2 hours",
        Intent.TECHNICAL_SUPPORT: "4 hours",
        Intent.BUG_REPORT: "1-3 business days",
        Intent.FEATURE_REQUEST: "Next sprint cycle",
        Intent.CANCELLATION: "Immediate",
        Intent.GENERAL_INQUIRY: "2 hours",
    }
    return times.get(intent, "4 hours")


class GenerationService:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    async def generate_response(
        self,
        ticket_body: str,
        classification: ClassificationResult,
        retrieval: RetrievalResult,
    ) -> ResponseDraft:
        if self.openai_api_key:
            try:
                return await self._generate_with_llm(ticket_body, classification, retrieval)
            except Exception as e:
                logger.warning(f"OpenAI call failed, falling back to template: {e}")

        return self._generate_from_template(classification, retrieval)

    def _generate_from_template(
        self,
        classification: ClassificationResult,
        retrieval: RetrievalResult,
    ) -> ResponseDraft:
        intent = classification.intent
        tier = _get_sentiment_tier(classification.sentiment)

        intent_templates = _TEMPLATES.get(intent, _TEMPLATES[Intent.UNKNOWN])
        response = (
            intent_templates.get(tier)
            or intent_templates.get("negative")
            or intent_templates.get("default")
            or _TEMPLATES[Intent.UNKNOWN]["default"]
        )

        # Inject context snippet for general inquiries
        ctx_snippet = _build_context_snippet(retrieval)
        response = response.replace("{context_snippet}", ctx_snippet or "I'll be happy to help you find the information you need.")

        confidence = _compute_confidence(classification, retrieval)
        requires_review = (
            confidence < 0.65
            or classification.urgency_score >= 0.85
            or classification.intent == Intent.ACCOUNT_ACCESS
        )

        return ResponseDraft(
            response_draft=response,
            confidence_score=confidence,
            requires_human_review=requires_review,
            tone="empathetic" if classification.sentiment in (Sentiment.URGENT, Sentiment.FRUSTRATED) else "professional",
            estimated_resolution_time=_estimate_resolution_time(intent, classification.urgency_score),
            suggested_knowledge_articles=list(retrieval.sources or [])[:3],
        )

    async def _generate_with_llm(
        self,
        ticket_body: str,
        classification: ClassificationResult,
        retrieval: RetrievalResult,
    ) -> ResponseDraft:
        """Real OpenAI call — only invoked when API key is available."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.openai_api_key)
        context_str = "\n---\n".join(retrieval.context[:3]) if retrieval.context else "No context available."

        system_prompt = (
            "You are an expert customer support agent for CogV8 AI. "
            "Your tone is professional, empathetic, and solution-oriented. "
            "Provide a complete, actionable response draft to the customer's ticket. "
            "Format clearly using markdown where helpful."
        )
        user_prompt = f"""
Ticket Body: {ticket_body}

Classification:
- Intent: {classification.intent.value}
- Urgency Score: {classification.urgency_score}
- Sentiment: {classification.sentiment.value}
- Keywords: {', '.join(classification.keywords or [])}

Relevant Knowledge Base Context:
{context_str}

Generate a response draft. Return ONLY the response text with no JSON wrapper.
"""
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=600,
            temperature=0.4,
        )
        draft_text = response.choices[0].message.content.strip()
        confidence = _compute_confidence(classification, retrieval)

        return ResponseDraft(
            response_draft=draft_text,
            confidence_score=confidence,
            requires_human_review=confidence < 0.7 or classification.urgency_score >= 0.85,
            tone="empathetic" if classification.sentiment in (Sentiment.URGENT, Sentiment.FRUSTRATED) else "professional",
            estimated_resolution_time=_estimate_resolution_time(classification.intent, classification.urgency_score),
            suggested_knowledge_articles=list(retrieval.sources or [])[:3],
        )


generation_service = GenerationService()
