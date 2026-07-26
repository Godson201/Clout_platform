from functools import lru_cache

from app.core.config import get_settings
from app.services.email.base import EmailSender
from app.services.email.console import ConsoleEmailSender
from app.services.email.smtp import SMTPEmailSender

settings = get_settings()


@lru_cache
def get_email_sender() -> EmailSender:
    if settings.EMAIL_MODE == "smtp":
        return SMTPEmailSender(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            from_email=settings.SMTP_FROM_EMAIL,
            from_name=settings.SMTP_FROM_NAME,
        )
    return ConsoleEmailSender()


__all__ = ["EmailSender", "get_email_sender"]
