import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from starlette.concurrency import run_in_threadpool

from app.services.email.base import EmailSender

logger = logging.getLogger("clout.email")


class SMTPEmailSender(EmailSender):
    def __init__(self, *, host: str, port: int, username: str | None, password: str | None, from_email: str | None, from_name: str):
        self.host = host
        self.port = port
        self.username = username
        # Providers (Gmail included) display app passwords with spaces for
        # readability; the actual credential has none. Stripping here means
        # .env can hold either form without breaking auth.
        self.password = password.replace(" ", "") if password else password
        self.from_email = from_email or username
        self.from_name = from_name

    def _send_sync(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to
        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL(self.host, self.port, timeout=15) as server:
            server.login(self.username, self.password)
            server.sendmail(self.from_email, [to], message.as_string())

    async def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        # run_in_threadpool matters here specifically because smtplib is blocking
        # I/O with no async variant in the standard library — without it, a slow
        # or unreachable SMTP server would stall this request's event loop (and
        # every other concurrent request) for the full connection timeout.
        await run_in_threadpool(self._send_sync, to=to, subject=subject, html_body=html_body, text_body=text_body)
