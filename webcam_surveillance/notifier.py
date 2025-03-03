import abc
import logging
from pathlib import Path

from webcam_surveillance.configuration import EmailNotificationConfiguration
from webcam_surveillance.email_sender import EmailSender

log = logging.getLogger(__name__)

class NotifierInterface(abc.ABC):
    @abc.abstractmethod
    def notify_video(self, subject: str, message: str, video_path: Path) -> None:
        pass

class LogNotifier(NotifierInterface):
    def notify_video(self, subject: str, message: str, video_path: Path) -> None:
        log.info(f"Notification: subject='%s', message='%s', video=%s", subject, message, video_path)


class EmailNotifier(NotifierInterface):
    def __init__(self, config: EmailNotificationConfiguration) -> None:
        self.config = config

        self.enabled = self.config["enabled"]
        self.email_sender = EmailSender(self.config)

    def notify_video(self, subject: str, message: str, video_path: Path) -> None:
        log.info(f"Sending email to='%s' with subject='%s' and message='%s' for video=%s",
                 self.config["receiver_email"], subject, message, video_path)
        if not self.enabled:
            log.debug("Email notification disabled")
            return
        self.email_sender.send_email(
            receiver_email=self.config["receiver_email"],
            subject=subject,
            body=message,
            attachments=[video_path]
        )