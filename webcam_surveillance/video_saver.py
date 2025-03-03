import logging
from collections import deque
from functools import lru_cache
from datetime import datetime as dt
import zoneinfo

import cv2
import numpy as np

from webcam_surveillance import OUTPUT_DIR
from webcam_surveillance.enums import MotionDetected
from webcam_surveillance.notifier import NotifierInterface
from webcam_surveillance.webcam_properties import WebcamProperties

log = logging.getLogger(__name__)


class VideoSaver:
    FOURCC_OUTPUT_CODEC = "mp4v"  # fmp4 not supported (video only, no audio)
    FILE_EXTENSION = "mp4"  # .{FILE_EXTENSION} is appended to the file name
    MAX_VIDEO_DURATION = 10  # seconds
    PRE_MOVEMENT_DURATION = 1  # seconds -- the number of seconds to save in the video before the movement starts

    TIMEZONE = zoneinfo.ZoneInfo("Europe/Paris")

    def __init__(
            self,
            webcam_properties: WebcamProperties,
            notifier: NotifierInterface
    ) -> None:
        self.webcam_properties = webcam_properties
        self.notifier = notifier
        if not self.webcam_properties.ready():
            raise ValueError("Webcam properties not initialized properly")
        self.fourcc = cv2.VideoWriter_fourcc(*self.FOURCC_OUTPUT_CODEC)  # noqa: VideoWriter_fourcc does exists

        self.motion_in_buffer = False
        self.circular_buffer_size = int(self.MAX_VIDEO_DURATION * self.webcam_properties.fps)
        self.frames: deque[tuple[cv2.typing.MatLike, MotionDetected]] = deque(
            maxlen=self.circular_buffer_size
        )
        # Initialize the frames with black frames
        for _ in range(self.circular_buffer_size):
            self.frames.append(
                (
                    np.zeros((self.webcam_properties.height, self.webcam_properties.width, 3), dtype=np.uint8),
                    MotionDetected.NO_MOTION
                )
            )

    @lru_cache(maxsize=1)
    def _get_index_of_frame_for_first_motion(self) -> int:
        return self.circular_buffer_size - int(self.PRE_MOVEMENT_DURATION * self.webcam_properties.fps)

    def add_frame(self, frame: cv2.typing.MatLike, motion: MotionDetected) -> None:
        if self.motion_in_buffer:
            if self.frames[0][1] == MotionDetected.DETECTED_MOTION:
                log.info("Saving video clip")
                self._save_video_clip(list(f[0] for f in self.frames))
                log.info("Removing motion tag from the buffer, waiting for new motion")
                self.motion_in_buffer = False
        if not self.motion_in_buffer and motion == MotionDetected.DETECTED_MOTION:
            log.info("Motion detected, starting to save video clip")
            self.motion_in_buffer = True
            ff, _ = self.frames[self._get_index_of_frame_for_first_motion()]
            self.frames[self._get_index_of_frame_for_first_motion()] = (ff, MotionDetected.DETECTED_MOTION)
            log.debug("Patched frame at index %s", self._get_index_of_frame_for_first_motion())
        self.frames.append((frame, MotionDetected.NO_MOTION))

    def _save_video_clip(self, frames_to_save: list[np.ndarray]) -> None:
        """Save the video clip as a video file according to the video codec"""
        timestamp = dt.now(tz=self.TIMEZONE)
        file_path = OUTPUT_DIR / f"motion_{timestamp.isoformat()}.{self.FILE_EXTENSION}"
        out = cv2.VideoWriter(
            str(file_path),
            self.fourcc,
            self.webcam_properties.fps,
            (self.webcam_properties.width, self.webcam_properties.height))
        for frame in frames_to_save:
            out.write(frame)
        out.release()
        self.notifier.notify_video(
            subject=f"Motion detected in your house at {timestamp.date()}",
            message=f"Motion detected at {timestamp.strftime('%Hh%m:%S')}. More information on your server.",
            video_path=file_path
        )