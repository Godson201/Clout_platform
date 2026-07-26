from app.core.config import get_settings

settings = get_settings()

_WRAPPER = """
<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:480px;margin:auto;color:#1f2937">
  <p style="font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:#7c3aed;font-weight:600">{system_name}</p>
  <h2 style="margin:8px 0 16px">{heading}</h2>
  {body}
</div>
"""

_BUTTON = (
    '<p><a href="{link}" style="display:inline-block;padding:10px 22px;background:#7c3aed;'
    'color:#fff;border-radius:8px;text-decoration:none;font-weight:600">{label}</a></p>'
)


def verification_email(*, to_name: str, token: str) -> tuple[str, str, str]:
    link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}"
    hours = settings.EMAIL_VERIFICATION_EXPIRE_MINUTES // 60
    subject = f"Confirm your {settings.SMTP_FROM_NAME} account"

    body = (
        f"<p>Hi {to_name},</p>"
        f"<p>Thanks for signing up. Confirm your email address to finish setting up your account.</p>"
        f"{_BUTTON.format(link=link, label='Confirm email')}"
        f'<p style="color:#6b7280;font-size:13px">Or paste this link into your browser: {link}</p>'
        f'<p style="color:#6b7280;font-size:13px">This link expires in {hours} hours.</p>'
    )
    html = _WRAPPER.format(system_name=settings.SMTP_FROM_NAME, heading="Confirm your email", body=body)
    text = (
        f"Hi {to_name},\n\nThanks for signing up for {settings.SMTP_FROM_NAME}. "
        f"Confirm your email by visiting:\n{link}\n\nThis link expires in {hours} hours."
    )
    return subject, html, text


def password_reset_email(*, to_name: str, token: str) -> tuple[str, str, str]:
    link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={token}"
    minutes = settings.PASSWORD_RESET_EXPIRE_MINUTES
    subject = f"Reset your {settings.SMTP_FROM_NAME} password"

    body = (
        f"<p>Hi {to_name},</p>"
        f"<p>We received a request to reset your password.</p>"
        f"{_BUTTON.format(link=link, label='Reset password')}"
        f'<p style="color:#6b7280;font-size:13px">If you didn\'t request this, you can safely ignore this email — '
        f"your password won't change.</p>"
        f'<p style="color:#6b7280;font-size:13px">This link expires in {minutes} minutes.</p>'
    )
    html = _WRAPPER.format(system_name=settings.SMTP_FROM_NAME, heading="Reset your password", body=body)
    text = (
        f"Hi {to_name},\n\nWe received a request to reset your {settings.SMTP_FROM_NAME} password. Visit:\n{link}\n\n"
        f"If you didn't request this, ignore this email — your password won't change. "
        f"This link expires in {minutes} minutes."
    )
    return subject, html, text


def password_changed_email(*, to_name: str) -> tuple[str, str, str]:
    subject = f"Your {settings.SMTP_FROM_NAME} password was changed"
    body = (
        f"<p>Hi {to_name},</p>"
        f"<p>Your account password was just changed.</p>"
        f'<p style="color:#6b7280;font-size:13px">If this wasn\'t you, contact support immediately.</p>'
    )
    html = _WRAPPER.format(system_name=settings.SMTP_FROM_NAME, heading="Password changed", body=body)
    text = (
        f"Hi {to_name},\n\nYour {settings.SMTP_FROM_NAME} account password was just changed. "
        f"If this wasn't you, contact support immediately."
    )
    return subject, html, text
