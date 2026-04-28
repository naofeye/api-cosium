import smtplib
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("email_sender")


@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    mime_type: str = "application/pdf"


class EmailSender:
    def __init__(self) -> None:
        self.host = settings.mailhog_smtp_host
        self.port = settings.mailhog_smtp_port
        self.from_email = "noreply@optiflow.com"

    def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> bool:
        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to

            body_part = MIMEMultipart("alternative")
            body_part.attach(MIMEText(body_html, "html"))
            msg.attach(body_part)

            for att in attachments or []:
                main_type, _, sub_type = att.mime_type.partition("/")
                part = MIMEApplication(att.content, _subtype=sub_type or "octet-stream")
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=att.filename,
                )
                msg.attach(part)

            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                server.sendmail(self.from_email, to, msg.as_string())

            logger.info(
                "email_sent",
                to=to,
                subject=subject,
                attachments=len(attachments or []),
            )
            return True
        except Exception as e:
            logger.error("email_send_failed", to=to, error=str(e))
            return False


email_sender = EmailSender()
