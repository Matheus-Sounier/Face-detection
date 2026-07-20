import time
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from config import MODEL_PATH

base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)

detector_options = vision.FaceDetectorOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
)

detector = vision.FaceDetector.create_from_options(
    detector_options
)

def detect_faces(img):
    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
    )
    timestamp_ms = int(time.perf_counter() * 1000)  
    return detector.detect(mp_image)