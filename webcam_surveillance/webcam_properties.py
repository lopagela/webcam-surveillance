import logging

import cv2

log = logging.getLogger(__name__)

class WebcamProperties:
    def __init__(
            self,
            width: int = 1280,
            height: int = 720,
            device_index: int = 0,
            default_fps: int = 10
    ) -> None:
        self.width = width
        self.height = height
        self.device_index = device_index
        self._default_fps = default_fps

        self.fps: int = -1  # default value, invalid

    def ready(self) -> bool:
        return self.fps > 0

    def initialize_fps_of_webcam(self, video_capture: cv2.VideoCapture) -> float:
        try:
            self.fps = video_capture.get(cv2.CAP_PROP_FPS)
        except Exception:
            self.fps = self._default_fps
            log.warning("Unable to get FPS, defaulting to 10")
        log.info("Frames per second using video.get(cv2.CAP_PROP_FPS) : %s", self.fps)
        return self.fps