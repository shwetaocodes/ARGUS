import smtplib
from email.mime.text import MIMEText
from app.core.config import settings

def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    """Returns True on success, False on failure — never raises, so a broken email
    config never breaks the underlying alert/digest logic that calls it."""
    if not settings.SMTP_HOST:
        print(f"[Email] SMTP not configured — skipping email to {to_email}: {subject}")
        return False
    try:
        msg = MIMEText(body)
        msg["Subject"] = f"[ARGUS] {subject}"
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[Email] Failed to send to {to_email}: {e}")
        return False