from app.core.config import get_settings
from app.services.report_generation.anthropic_client import AnthropicNarrativeGenerator
from app.services.report_generation.base import NarrativeGenerator, ReportData
from app.services.report_generation.template import TemplateNarrativeGenerator

__all__ = ["NarrativeGenerator", "ReportData", "get_narrative_generator"]

_template_generator = TemplateNarrativeGenerator()
_anthropic_generator = AnthropicNarrativeGenerator()


def get_narrative_generator() -> NarrativeGenerator:
    settings = get_settings()
    if settings.REPORT_GENERATOR_MODE == "anthropic":
        return _anthropic_generator
    return _template_generator
