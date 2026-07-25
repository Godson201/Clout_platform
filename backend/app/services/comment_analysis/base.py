from dataclasses import dataclass
from typing import Protocol

from app.models.enums import CommentCategory, SentimentLabel


@dataclass(frozen=True)
class ClassificationResult:
    category: CommentCategory
    sentiment_label: SentimentLabel
    sentiment_score: float  # -1.0 (very negative) to 1.0 (very positive)
    classifier_version: str


class CommentClassifier(Protocol):
    def classify(self, text: str) -> ClassificationResult: ...
