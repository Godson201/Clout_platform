import logging
from dataclasses import dataclass

from app.services.email.base import EmailSender

logger = logging.getLogger("clout.email")


@dataclass
class SentEmail:
    to: str
    subject: str
    html_body: str
    text_body: str


# Dev/test-only in-memory outbox — never used when EMAIL_MODE=smtp. Lets tests
# assert an email was "sent" without a real mailbox or network call.
SENT_EMAILS: list[SentEmail] = []


class ConsoleEmailSender(EmailSender):
    async def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        SENT_EMAILS.append(SentEmail(to=to, subject=subject, html_body=html_body, text_body=text_body))
        logger.info("Email (mock, not sent) to %s — %s", to, subject)
