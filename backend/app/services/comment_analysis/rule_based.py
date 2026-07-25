import re

from app.models.enums import CommentCategory, SentimentLabel
from app.services.comment_analysis.base import ClassificationResult

CLASSIFIER_VERSION = "rule-based-v1"

# Deliberately not scikit-learn/transformers: at this stage there's no labeled
# training data (no corpus of CLOUT comments with confirmed categories), and a
# fixed lexicon is auditable and instantly explainable to a brand asking "why
# was this flagged a complaint" — the same "explainable before ML" reasoning
# services/matching.py already applies to influencer scoring. The interface
# (CommentClassifier) is the seam for swapping in a real model later without
# touching call sites, same pattern as PaymentClient/SocialPlatformAdapter.

_SUGGESTION_PATTERNS = [
    r"\byou should\b",
    r"\bshould add\b",
    r"\bcould you\b",
    r"\bplease add\b",
    r"\bwould be great if\b",
    r"\bi wish\b",
    r"\bcan you add\b",
    r"\bwhat about\b",
]

_COMPLAINT_WORDS = {
    "scam",
    "refund",
    "terrible",
    "awful",
    "worst",
    "disappointed",
    "disappointing",
    "broken",
    "waste",
    "horrible",
    "fraud",
    "rip-off",
    "ripoff",
}

_POSITIVE_WORDS = {
    "love",
    "amazing",
    "best",
    "great",
    "excellent",
    "awesome",
    "recommend",
    "fantastic",
    "perfect",
    "good",
    "nice",
    "happy",
    "beautiful",
    "wonderful",
}

_NEGATIVE_WORDS = {
    "hate",
    "worst",
    "terrible",
    "awful",
    "bad",
    "disappointed",
    "disappointing",
    "scam",
    "broken",
    "waste",
    "horrible",
    "poor",
    "annoying",
}

_SENTIMENT_THRESHOLD = 0.2
_WORD_RE = re.compile(r"[a-zA-Z']+")


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def _sentiment(words: list[str]) -> tuple[SentimentLabel, float]:
    positive_hits = sum(1 for w in words if w in _POSITIVE_WORDS)
    negative_hits = sum(1 for w in words if w in _NEGATIVE_WORDS)
    total_signal = positive_hits + negative_hits

    if total_signal == 0:
        return SentimentLabel.NEUTRAL, 0.0

    score = max(-1.0, min(1.0, (positive_hits - negative_hits) / total_signal))
    if score > _SENTIMENT_THRESHOLD:
        return SentimentLabel.POSITIVE, score
    if score < -_SENTIMENT_THRESHOLD:
        return SentimentLabel.NEGATIVE, score
    return SentimentLabel.NEUTRAL, score


class RuleBasedClassifier:
    """v1 comment classifier: keyword/pattern heuristics for intent
    (question/suggestion/complaint), a lexicon for sentiment. Order matters —
    a question is classified as a question even if it also happens to contain
    a positive word ("is this the best price?"), since intent is the more
    actionable signal for a brand skimming comments.
    """

    def classify(self, text: str) -> ClassificationResult:
        words = _tokenize(text)
        sentiment_label, sentiment_score = _sentiment(words)

        if not words:
            return ClassificationResult(
                category=CommentCategory.OTHER,
                sentiment_label=SentimentLabel.NEUTRAL,
                sentiment_score=0.0,
                classifier_version=CLASSIFIER_VERSION,
            )

        lowered = text.lower()

        if "?" in text:
            category = CommentCategory.QUESTION
        elif any(w in _COMPLAINT_WORDS for w in words):
            category = CommentCategory.COMPLAINT
        elif any(re.search(pattern, lowered) for pattern in _SUGGESTION_PATTERNS):
            category = CommentCategory.SUGGESTION
        elif sentiment_label == SentimentLabel.POSITIVE:
            category = CommentCategory.POSITIVE
        elif sentiment_label == SentimentLabel.NEGATIVE:
            category = CommentCategory.NEGATIVE
        else:
            category = CommentCategory.NEUTRAL

        return ClassificationResult(
            category=category,
            sentiment_label=sentiment_label,
            sentiment_score=sentiment_score,
            classifier_version=CLASSIFIER_VERSION,
        )
