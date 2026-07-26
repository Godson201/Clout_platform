from abc import ABC, abstractmethod


class EmailSender(ABC):
    """Every call site talks to this interface only — same abstraction-first
    pattern as PaymentClient/SocialPlatformAdapter, so swapping the mock for a
    real transactional-email provider later is a one-class change.
    """

    @abstractmethod
    async def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> None: ...
