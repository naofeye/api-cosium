import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("email_sender")


class EmailSender:
    def __init__(self) -> None:
        self.host = settings.mailhog_smtp_host
        self.port = settings.mailhog_smtp_port
        self.from_email = "noreply@optiflow.local"

    def send_email(self, to: str, subject: str, body_html: str) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to
            msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP(self.host, self.port) as server:
                server.sendmail(self.from_email, to, msg.as_string())

            logger.info("email_sent", to=to, subject=subject)
            return True
        except Exception as e:
            logger.error("email_send_failed", to=to, error=str(e))
            return False


email_sender = EmailSender()
