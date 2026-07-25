from app.services.comment_analysis.base import ClassificationResult, CommentClassifier
from app.services.comment_analysis.rule_based import RuleBasedClassifier

__all__ = ["ClassificationResult", "CommentClassifier", "get_classifier"]

_classifier = RuleBasedClassifier()


def get_classifier() -> CommentClassifier:
    """Single implementation today, but kept as a factory (matching
    get_payment_client/get_adapter elsewhere) so a real ML-based classifier can
    be swapped in later without touching any call site.
    """
    return _classifier
