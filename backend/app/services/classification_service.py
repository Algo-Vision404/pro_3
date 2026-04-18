import os
from typing import Dict, Any
from app.models.schema import ClassificationResult, Intent, Sentiment
import openai
from dotenv import load_dotenv

load_dotenv()

class BaseClassifier:
    async def classify(self, ticket_body: str) -> ClassificationResult:
        raise NotImplementedError

class LLMClassifier(BaseClassifier):
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        if self.api_key:
            openai.api_key = self.api_key

    async def classify(self, ticket_body: str) -> ClassificationResult:
        # If no API key, return a mock classification for development
        if not self.api_key:
            return ClassificationResult(
                intent=Intent.GENERAL_INQUIRY,
                urgency_score=0.5,
                sentiment=Sentiment.NEUTRAL
            )

        prompt = f"""
        Analyze the following customer support ticket and classify it.
        Provide the output in strict JSON format.
        
        Ticket Body: {ticket_body}
        
        Required JSON fields:
        - intent: One of [technical_support, billing, account_access, feature_request, general_inquiry]
        - urgency_score: A float between 0.0 and 1.0
        - sentiment: One of [negative, neutral, positive]
        """
        
        # Real LLM call would happen here
        # For now, let's keep it robust with a try-except and mock fallback
        try:
            # response = await openai.ChatCompletion.acreate(...)
            # mock parsing
            return ClassificationResult(
                intent=Intent.TECHNICAL_SUPPORT,
                urgency_score=0.8,
                sentiment=Sentiment.NEGATIVE
            )
        except Exception:
            return ClassificationResult(
                intent=Intent.UNKNOWN,
                urgency_score=0.5,
                sentiment=Sentiment.NEUTRAL
            )

# Factory for pluggable classifiers
def get_classifier(classifier_type: str = "llm") -> BaseClassifier:
    if classifier_type == "llm":
        return LLMClassifier()
    return LLMClassifier() # Default
