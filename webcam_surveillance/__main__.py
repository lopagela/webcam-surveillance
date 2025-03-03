import logging
import time

from webcam_surveillance.configuration import get_configuration
from webcam_surveillance.video_saver import VideoSaver
from webcam_surveillance.webcam_properties import WebcamProperties
from webcam_surveillance.webcam_watcher import WebcamWatcher
from webcam_surveillance.notifier import LogNotifier, EmailNotifier

# Format more compact:
COMPACT_LOG_FORMAT = '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s'
logging.basicConfig(level="DEBUG", format=COMPACT_LOG_FORMAT, datefmt="%H:%M:%S")
logging.captureWarnings(True)
log = logging.getLogger(__name__)

log.debug("Logging configured")

import cv2

def main_cli():
    configuration = get_configuration()

    log.info("OpenCV version: %s", cv2.__version__)
    webcam = WebcamProperties(
        width=configuration["webcam"]["width"],
        height=configuration["webcam"]["height"],
        device_index=configuration["webcam"]["device_index"],
        default_fps=configuration["webcam"]["default_fps"]
    )

    if configuration["email_notification"]["enabled"]:
        log.info("Email notification is enabled")
        notifier = EmailNotifier(configuration["email_notification"])
    else:
        log.info("Email notification is disabled")
        notifier = LogNotifier()

    watcher = WebcamWatcher(
        webcam_properties=webcam,
        notifier=notifier
    )
    # log.info("Testing if enough memory is available")
    # watcher.video_saver.test_enough_memory()
    watcher.watch()  # Main loop
    del watcher  # Release the webcam and close all OpenCV windows
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main_cli()
