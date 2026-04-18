import os
from typing import List
from app.models.schema import ResponseDraft, ClassificationResult, RetrievalResult
import openai
from dotenv import load_dotenv

load_dotenv()

class GenerationService:
    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")

    async def generate_response(
        self, 
        ticket_body: str, 
        classification: ClassificationResult, 
        retrieval: RetrievalResult
    ) -> ResponseDraft:
        
        context_str = "\n".join(retrieval.context)
        
        prompt = f"""
        You are a professional customer support agent. 
        Tone: Empathetic, Concise, Solution-oriented.
        
        Ticket: {ticket_body}
        
        Classification:
        Intent: {classification.intent}
        Urgency: {classification.urgency_score}
        Sentiment: {classification.sentiment}
        
        Knowledge Base Context:
        {context_str}
        
        Generate a response draft.
        Also provide a confidence score (0-1) and whether it requires human review.
        
        Output JSON:
        {{
            "response_draft": "text",
            "confidence_score": 0.0,
            "requires_human_review": boolean
        }}
        """

        # Mocking for now
        if not self.api_key:
            return ResponseDraft(
                response_draft="Thank you for reaching out. We've received your billing inquiry and a technician will look into it. (Mock Response)",
                confidence_score=0.85,
                requires_human_review=False
            )

        # Real OpenAI call would go here
        return ResponseDraft(
            response_draft="Real AI response would be here.",
            confidence_score=0.9,
            requires_human_review=False
        )

generation_service = GenerationService()
