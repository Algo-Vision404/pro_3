"""
Multi-rule escalation engine.
Evaluates risk across confidence, urgency, sentiment, intent, and legal signal rules.
"""
import re
from typing import Optional, List
from app.models.schema import (
    ClassificationResult, ResponseDraft, EscalationSummary,
    Intent, Sentiment, RetrievalResult, EscalationReason
)

# Legal/risk trigger phrases
_LEGAL_TRIGGERS = [
    r"lawyer|attorney|legal action",
    r"sue|lawsuit|court|litigation",
    r"bbb|better business bureau",
    r"fraud|scam",
    r"data breach|hacked|stolen.*data",
    r"media|press|news|twitter|social media",
    r"chargebac|dispute.*bank",
]


class EscalationService:
    def __init__(
        self,
        confidence_threshold: float = 0.60,
        urgency_threshold: float = 0.80,
    ):
        self.confidence_threshold = confidence_threshold
        self.urgency_threshold = urgency_threshold

    def _check_legal_risk(self, text: str) -> bool:
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in _LEGAL_TRIGGERS)

    def evaluate_escalation(
        self,
        ticket_body: str,
        classification: ClassificationResult,
        draft: ResponseDraft,
        retrieval: RetrievalResult,
    ) -> Optional[EscalationSummary]:
        reasons: List[EscalationReason] = []
        reason_texts: List[str] = []

        # Rule 1: Low AI confidence
        if draft.confidence_score < self.confidence_threshold:
            reasons.append(EscalationReason.LOW_CONFIDENCE)
            reason_texts.append(f"Low AI confidence ({draft.confidence_score:.0%})")

        # Rule 2: High urgency
        if classification.urgency_score > self.urgency_threshold:
            reasons.append(EscalationReason.HIGH_URGENCY)
            reason_texts.append(f"Critical urgency score ({classification.urgency_score:.0%})")

        # Rule 3: AI explicitly flagged it
        if draft.requires_human_review:
            reasons.append(EscalationReason.HUMAN_FLAG)
            reason_texts.append("Generation engine flagged for human review")

        # Rule 4: Sensitive intents requiring human verification
        sensitive_intents = {
            Intent.ACCOUNT_ACCESS: "Security-sensitive: account access",
            Intent.CANCELLATION: "Churn risk: cancellation intent detected",
            Intent.REFUND_REQUEST: "Financial: explicit refund request",
        }
        if classification.intent in sensitive_intents:
            reasons.append(EscalationReason.SENSITIVE_INTENT)
            reason_texts.append(sensitive_intents[classification.intent])

        # Rule 5: Very negative / frustrated sentiment
        if classification.sentiment in (Sentiment.FRUSTRATED, Sentiment.URGENT) and classification.urgency_score > 0.6:
            if EscalationReason.NEGATIVE_SENTIMENT not in reasons:
                reasons.append(EscalationReason.NEGATIVE_SENTIMENT)
                reason_texts.append(f"Extreme negative sentiment: {classification.sentiment.value}")

        # Rule 6: Legal risk signals
        if self._check_legal_risk(ticket_body):
            reasons.append(EscalationReason.LEGAL_RISK)
            reason_texts.append("Legal / PR risk keywords detected — immediate escalation required")

        if not reasons:
            return None

        # Determine risk level
        if EscalationReason.LEGAL_RISK in reasons or classification.urgency_score >= 0.9:
            risk_level = "critical"
            assigned_team = "legal-and-senior-support"
        elif len(reasons) >= 2 or classification.urgency_score >= 0.75:
            risk_level = "high"
            assigned_team = "tier-2-support"
        else:
            risk_level = "medium"
            assigned_team = "tier-2-support"

        # Suggested actions
        actions = []
        if EscalationReason.LEGAL_RISK in reasons:
            actions.append("Loop in legal counsel immediately.")
        if EscalationReason.ACCOUNT_ACCESS in [EscalationReason.SENSITIVE_INTENT]:
            actions.append("Verify user identity before any account actions.")
        if EscalationReason.HIGH_URGENCY in reasons:
            actions.append("Respond within 30 minutes.")
        if EscalationReason.NEGATIVE_SENTIMENT in reasons:
            actions.append("Use empathetic tone; offer a goodwill gesture if appropriate.")
        if not actions:
            actions.append("Review context and provide a tailored human response.")

        return EscalationSummary(
            issue_summary=f"Escalated — {'; '.join(reason_texts)}",
            suggested_actions=" | ".join(actions),
            context_bundle=retrieval.context[:3],
            escalation_reasons=reasons,
            risk_level=risk_level,
            assigned_team=assigned_team,
        )


escalation_service = EscalationService()
