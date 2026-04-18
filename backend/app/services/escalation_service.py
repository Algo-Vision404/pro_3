from app.models.schema import (
    ClassificationResult, 
    ResponseDraft, 
    EscalationSummary, 
    Intent, 
    RetrievalResult
)
from typing import Optional

class EscalationService:
    def __init__(self, confidence_threshold: float = 0.7, urgency_threshold: float = 0.9):
        self.confidence_threshold = confidence_threshold
        self.urgency_threshold = urgency_threshold

    def evaluate_escalation(
        self, 
        ticket_body: str,
        classification: ClassificationResult, 
        draft: ResponseDraft,
        retrieval: RetrievalResult
    ) -> Optional[EscalationSummary]:
        
        reasons = []
        
        # Rule 1: Low Confidence
        if draft.confidence_score < self.confidence_threshold:
            reasons.append(f"Low AI confidence ({draft.confidence_score})")
            
        # Rule 2: High Urgency
        if classification.urgency_score > self.urgency_threshold:
            reasons.append(f"High urgency detected ({classification.urgency_score})")
            
        # Rule 3: Manual flag from generation
        if draft.requires_human_review:
            reasons.append("AI flagged for human review")
            
        # Rule 4: Critical Intent
        if classification.intent == Intent.ACCOUNT_ACCESS:
             # Account access issues often need human security verification
             reasons.append("Sensitive intent: Account Access")

        if not reasons:
            return None

        return EscalationSummary(
            issue_summary=f"Escalated due to: {', '.join(reasons)}",
            suggested_actions="Human verified response required. Verify user identity.",
            context_bundle=retrieval.context
        )

escalation_service = EscalationService()
