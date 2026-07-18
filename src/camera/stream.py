import cv2
import threading
import time


class CameraStream:
    """Reads camera frames in a background thread to avoid blocking the main loop."""

    def __init__(self, index=0, use_dshow=True):
        backend = cv2.CAP_DSHOW if use_dshow else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(index, backend)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()
        print("Camera opened:", self.cap.isOpened())

    def _reader(self):
        while self.running:
            success, frame = self.cap.read()
            if success:
                with self.lock:
                    self.frame = frame
            else:
                time.sleep(0.1)

    def read(self):
        with self.lock:
            return self.frame is not None, (
                self.frame.copy() if self.frame is not None else None
            )

    def release(self):
        self.running = False
        self._thread.join()
        self.cap.release()