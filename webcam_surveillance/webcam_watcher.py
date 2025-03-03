import logging

import cv2

from webcam_surveillance.enums import MotionDetected
from webcam_surveillance.notifier import NotifierInterface
from webcam_surveillance.video_saver import VideoSaver
from webcam_surveillance.webcam_properties import WebcamProperties

log = logging.getLogger(__name__)

class WebcamWatcher:
    START_RECORDING_DELAY = 2  # seconds -- the number of seconds to wait before starting to record the video
    def __init__(
            self,
            webcam_properties: WebcamProperties,
            notifier: NotifierInterface
    ) -> None:
        self.webcam_properties = webcam_properties
        self.notifier = notifier

        # Initialize the webcam capture
        self.cap = cv2.VideoCapture(self.webcam_properties.device_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.webcam_properties.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.webcam_properties.height)
        self.webcam_properties.initialize_fps_of_webcam(self.cap)

        self.video_saver = VideoSaver(
            webcam_properties=self.webcam_properties,
            notifier=self.notifier)

    def __del__(self):
        # Release the webcam and close all OpenCV windows
        self.cap.release()
        cv2.destroyAllWindows()

    def watch(self) -> None:
        # Read the first frames
        # NOTE: Doing it multiple times to get a more reliable first frame
        frame = None
        log.debug("Warm-up the webcam by reading the first frames, to get a more reliable first frame")
        for _ in range(5):
            ret, frame = self.cap.read()
            if not ret:
                log.error("Error reading webcam frame, exiting")
                raise Exception("Failed to capture image")

        log.info("First frames captured, starting the actual recording")
        # Convert the first frame to grayscale and blur it
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)



        # Main loop
        while True:
            motion_in_frame_detected = MotionDetected.NO_MOTION
            ret, frame = self.cap.read()
            if not ret:
                log.error("Could not read frame in main loop, exiting")
                break

            # Convert the current frame to grayscale and blur it
            gray_current = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_current = cv2.GaussianBlur(gray_current, (21, 21), 0)

            # Compute the absolute difference between the current frame and the first frame
            frame_delta = cv2.absdiff(gray, gray_current)
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

            # Dilate the thresholded image to fill in holes, then find contours on thresholded image
            thresh = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Loop over the contours
            for contour in contours:
                # If the contour is too small, ignore it
                if cv2.contourArea(contour) < 500.0:
                    continue
                log.info("Motion detected in current frame")
                motion_in_frame_detected = MotionDetected.DETECTED_MOTION

            self.video_saver.add_frame(frame, motion_in_frame_detected)

            # Update the first frame
            gray = gray_current

            # Display the frame
            cv2.imshow('Frame', frame)

            # Break the loop on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
