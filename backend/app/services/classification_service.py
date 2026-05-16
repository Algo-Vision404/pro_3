"""
Rule-based + keyword-scoring classifier.
Works fully offline — no OpenAI key required.
Falls back to LLM synthesis if OPENAI_API_KEY is set.
"""
import re
from typing import Dict, List, Tuple
from app.models.schema import ClassificationResult, Intent, Sentiment


# ---------------------------------------------------------------------------
# Keyword taxonomy — (pattern, weight)
# ---------------------------------------------------------------------------
_INTENT_RULES: Dict[Intent, List[Tuple[str, float]]] = {
    Intent.BILLING: [
        (r"charg(e|ed|ing)", 1.0),
        (r"invoice", 1.0),
        (r"payment", 0.9),
        (r"refund", 0.8),
        (r"bill(ed|ing)?", 1.0),
        (r"credit card", 0.9),
        (r"subscription fee", 0.9),
        (r"double.?charg", 1.2),
        (r"overcharg", 1.2),
    ],
    Intent.REFUND_REQUEST: [
        (r"refund", 1.2),
        (r"money back", 1.2),
        (r"reimburse", 1.1),
        (r"return.*payment", 1.0),
        (r"get.*money", 0.8),
    ],
    Intent.ACCOUNT_ACCESS: [
        (r"(can'?t|cannot|unable to).{0,20}(log|sign|access)", 1.2),
        (r"password", 0.9),
        (r"login", 1.0),
        (r"lock(ed)?.*account", 1.1),
        (r"2fa|two.factor|authenticat", 0.9),
        (r"reset.*password", 1.0),
    ],
    Intent.TECHNICAL_SUPPORT: [
        (r"error|exception|crash|bug", 1.0),
        (r"not work(ing)?", 1.0),
        (r"broken", 0.9),
        (r"500|404|403", 0.8),
        (r"slow|timeout|latency", 0.7),
        (r"outage|down(time)?", 1.0),
        (r"install(ation)?", 0.7),
    ],
    Intent.BUG_REPORT: [
        (r"bug", 1.2),
        (r"glitch", 1.0),
        (r"unexpected.{0,15}behavior", 1.1),
        (r"reproduce|regression", 1.0),
        (r"steps to (reproduce|replicate)", 1.2),
    ],
    Intent.FEATURE_REQUEST: [
        (r"feature.{0,15}request", 1.2),
        (r"would (love|like|appreciate)", 0.9),
        (r"can you add", 1.0),
        (r"wish(list)?", 0.8),
        (r"suggestion|propose|idea", 0.8),
        (r"dark mode", 0.7),
    ],
    Intent.CANCELLATION: [
        (r"cancel(l?ation|ing|ed)?", 1.2),
        (r"unsubscribe", 1.0),
        (r"stop.*subscription", 1.0),
        (r"downgrade", 0.9),
        (r"close.*account", 1.0),
    ],
    Intent.GENERAL_INQUIRY: [
        (r"how (do|can|to)", 0.6),
        (r"what (is|are)", 0.5),
        (r"information|info", 0.5),
        (r"question|inquiry|enquiry", 0.7),
        (r"export.*data", 0.8),
        (r"download|csv", 0.7),
    ],
}

_SENTIMENT_RULES: Dict[Sentiment, List[Tuple[str, float]]] = {
    Sentiment.URGENT: [
        (r"urgent|asap|immediately|right now|now!|emergency", 1.5),
        (r"critical|crisis", 1.3),
        (r"presentation|meeting|deadline", 1.0),
        (r"!!!+|!!", 0.8),
    ],
    Sentiment.FRUSTRATED: [
        (r"frustrat(ed|ing)?", 1.2),
        (r"ridiculous|unacceptable|terrible|awful|horrible", 1.2),
        (r"wasted.*time|waste of time", 1.0),
        (r"worst|useless|broken", 1.0),
        (r"angry|angry|furious|upset", 1.1),
    ],
    Sentiment.NEGATIVE: [
        (r"not (working|happy|good|satisfied)", 1.0),
        (r"disappointed|unhappy|bad", 0.9),
        (r"problem|issue|trouble", 0.6),
        (r"fail(ed|ure)?|wrong", 0.8),
    ],
    Sentiment.POSITIVE: [
        (r"thank(s| you)|appreciate|great|awesome", 1.0),
        (r"love|excellent|perfect|fantastic", 1.2),
        (r"happy|pleased|satisfied", 1.0),
        (r"good job|well done", 1.0),
    ],
    Sentiment.NEUTRAL: [
        (r"how (do|can|to|does)", 0.5),
        (r"information|question|inquiry", 0.5),
    ],
}

# Urgency keywords that directly bump the urgency score
_URGENCY_BOOSTERS = [
    (r"critical|emergency|urgent|asap", 0.4),
    (r"immediately|right now|NOW", 0.35),
    (r"can'?t (work|function|access|log)", 0.25),
    (r"presentation|deadline|meeting", 0.2),
    (r"hacked|breach|security", 0.45),
    (r"legal|lawyer|sue|lawsuit", 0.5),
    (r"!!!+", 0.15),
    (r"business (down|impact|critical)", 0.35),
]

_KEYWORDS_OF_INTEREST = [
    "billing", "refund", "account", "password", "login", "error", "bug",
    "crash", "timeout", "invoice", "subscription", "cancel", "payment",
    "access", "feature", "export", "integration", "api", "security",
]


def _score_text(text: str, rules: Dict) -> Dict:
    """Return a dict of {label: score} for each label in the rules dict."""
    text_lower = text.lower()
    scores = {label: 0.0 for label in rules}
    for label, patterns in rules.items():
        for pattern, weight in patterns:
            matches = re.findall(pattern, text_lower)
            scores[label] += len(matches) * weight
    return scores


def _extract_keywords(text: str) -> List[str]:
    text_lower = text.lower()
    return [kw for kw in _KEYWORDS_OF_INTEREST if kw in text_lower]


def _compute_urgency(text: str, base: float = 0.3) -> float:
    text_lower = text.lower()
    score = base
    for pattern, boost in _URGENCY_BOOSTERS:
        if re.search(pattern, text_lower):
            score += boost
    return round(min(score, 1.0), 3)


class RuleBasedClassifier:
    """
    Fully offline, deterministic classifier using keyword scoring.
    Intent and sentiment are chosen by highest-scoring category.
    """

    async def classify(self, ticket_body: str, subject: str = "") -> ClassificationResult:
        full_text = f"{subject} {ticket_body}"

        # --- Intent ---
        intent_scores = _score_text(full_text, _INTENT_RULES)
        best_intent = max(intent_scores, key=intent_scores.get)
        best_intent_score = intent_scores[best_intent]
        if best_intent_score < 0.3:
            best_intent = Intent.GENERAL_INQUIRY

        # Confidence = normalised score (0.5 - 1.0 range)
        total = sum(v for v in intent_scores.values() if v > 0) or 1
        confidence = round(0.5 + min(best_intent_score / total, 0.5), 3)

        # --- Sentiment ---
        sentiment_scores = _score_text(full_text, _SENTIMENT_RULES)
        best_sentiment = max(sentiment_scores, key=sentiment_scores.get)
        if sentiment_scores[best_sentiment] < 0.3:
            best_sentiment = Sentiment.NEUTRAL

        # --- Urgency ---
        urgency = _compute_urgency(full_text)

        # Bump urgency for certain intents
        if best_intent in (Intent.ACCOUNT_ACCESS, Intent.BUG_REPORT):
            urgency = min(urgency + 0.15, 1.0)
        if best_sentiment in (Sentiment.URGENT, Sentiment.FRUSTRATED):
            urgency = min(urgency + 0.2, 1.0)

        # Sub-topics
        sub_topics = []
        for intent, score in sorted(intent_scores.items(), key=lambda x: -x[1]):
            if score > 0.3 and intent != best_intent:
                sub_topics.append(intent.value)
            if len(sub_topics) >= 2:
                break

        return ClassificationResult(
            intent=best_intent,
            urgency_score=round(urgency, 3),
            sentiment=best_sentiment,
            confidence=confidence,
            keywords=_extract_keywords(full_text),
            sub_topics=sub_topics,
        )


# Singleton
_classifier = RuleBasedClassifier()


def get_classifier() -> RuleBasedClassifier:
    return _classifier
