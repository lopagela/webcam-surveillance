import logging
from collections import deque
from functools import lru_cache
from datetime import datetime as dt
import zoneinfo
from threading import Thread
from typing import Iterable

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
        self.fourcc = cv2.VideoWriter.fourcc(*self.FOURCC_OUTPUT_CODEC)

        self.num_frames_buffer = int(self.PRE_MOVEMENT_DURATION * self.webcam_properties.fps)
        self.num_frames_to_save = int(self.MAX_VIDEO_DURATION * self.webcam_properties.fps)
        self.motion_in_buffer = False
        self.pre_frames_buffer: deque[cv2.typing.MatLike] = deque(
            maxlen=self.num_frames_buffer
        )
        self.frames_to_save: deque[cv2.typing.MatLike] = deque(
            maxlen=self.num_frames_to_save
        )

        self.thread_saver: Thread | None = None

    def __del__(self) -> None:
        if self.thread_saver is not None:
            self.thread_saver.join()

    def test_enough_memory(self) -> int:
        for _ in range(self.num_frames_buffer):
            self.pre_frames_buffer.append(
                (
                    np.zeros((self.webcam_properties.height, self.webcam_properties.width, 3), dtype=np.uint8),
                    MotionDetected.NO_MOTION
                )
            )
        for _ in range(self.num_frames_to_save):
            self.frames_to_save.append(
                (
                    np.zeros((self.webcam_properties.height, self.webcam_properties.width, 3), dtype=np.uint8),
                    MotionDetected.NO_MOTION
                )
            )
        total_size_bytes = sum(
            np.prod(frame[0].shape) * frame[0].itemsize
            for frame in self.pre_frames_buffer
        )
        total_size_bytes += sum(
            np.prod(frame[0].shape) * frame[0].itemsize
            for frame in self.frames_to_save
        )
        log.info(f"Total size of the frames buffer: {total_size_bytes / 1024 / 1024:.2f} MB (it does not include the libraries memory pressure)")
        self.pre_frames_buffer.clear()
        self.frames_to_save.clear()
        return total_size_bytes


    @lru_cache(maxsize=1)
    def _get_index_of_frame_for_first_motion(self) -> int:
        return self.num_frames_to_save - int(self.PRE_MOVEMENT_DURATION * self.webcam_properties.fps)

    def add_frame(self, frame: cv2.typing.MatLike, motion: MotionDetected) -> None:
        self.pre_frames_buffer.append(frame)
        if self.motion_in_buffer:
            if len(self.frames_to_save) == self.num_frames_to_save:
                # Reached the maximum duration of the video clip, so we save it
                log.info("Saving video clip")
                self._save_video_clip(list(self.frames_to_save))
                log.info("Removing motion tag from the buffer, waiting for new motion")
                self.motion_in_buffer = False
                self.frames_to_save.clear()
            else:
                # We are still in the motion detection phase, we keep adding frames to the buffer
                self.frames_to_save.append(frame)
        if not self.motion_in_buffer and motion == MotionDetected.DETECTED_MOTION:
            assert len(self.frames_to_save) == 0, "Frames should be empty when starting a new motion"
            log.info("Motion detected, starting to save video clip")
            self.motion_in_buffer = True
            self.frames_to_save.extend(self.pre_frames_buffer)
            # No need to add the current frame to the buffer, it is already in the pre_frames_buffer

    def _save_video_clip(self, frames_to_save: Iterable[cv2.typing.MatLike]) -> None:
        if self.thread_saver is not None:
            # Finish the previous video clip saving before starting a new one
            self.thread_saver.join()
        self.thread_saver = Thread(target=self._save_video_clip_wrapped, args=(frames_to_save,))
        self.thread_saver.start()

    def _save_video_clip_wrapped(self, frames_to_save: Iterable[cv2.typing.MatLike]) -> None:
        """Save the video clip as a video file according to the video codec"""
        timestamp = dt.now(tz=self.TIMEZONE)
        file_path = OUTPUT_DIR / f"motion_{timestamp.isoformat()}.{self.FILE_EXTENSION}"
        log.info(f"Saving video clip to {file_path=}")
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
