import logging
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from webcam_surveillance.configuration import EmailNotificationConfiguration

log = logging.getLogger(__name__)

class EmailSender:
    def __init__(self, smtp_conf: EmailNotificationConfiguration) -> None:
        self.smtp_conf = smtp_conf

    def send_email(
            self,
            receiver_email: str,
            subject: str,
            body: str,
            attachments: list[Path] = None  # List of file paths to attach
    ) -> None:
        # Create the MIME message
        message = MIMEMultipart()
        message["From"] = self.smtp_conf["sender_email"]
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # Attach files if provided
        if attachments:
            for file_path in attachments:
                if file_path.is_file():
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(file_path.read_bytes())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={file_path.name}"
                    )
                    message.attach(part)
                else:
                    log.warning(f"Attachment not found: {file_path}")

        try:
            # Connect to the SMTP server
            # We are expecting to use SSL, so we use the SMTP_SSL class
            with smtplib.SMTP_SSL(self.smtp_conf["smtp_host"], port=self.smtp_conf["smtp_port"]) as server:
                # server.starttls()  # This is not needed when using SMTP_SSL
                server.login(self.smtp_conf["sender_email"], self.smtp_conf["sender_password"])  # Login to the email account
                server.sendmail(self.smtp_conf["sender_email"], receiver_email, message.as_string())  # Send the email
            log.info("Email sent successfully!")
        except Exception as e:
            log.exception(f"Failed to send email: {e}")