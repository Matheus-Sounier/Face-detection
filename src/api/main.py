from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from contextlib import asynccontextmanager
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from dotenv import load_dotenv

import numpy as np
import mediapipe as mp

import cv2
import os

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Facial Access Control API", lifespan=lifespan)

base_options = mp_python.BaseOptions(model_asset_path=os.getenv("MODEL_PATH"))
detector_options = vision.FaceDetectorOptions(base_options=base_options)
detector = vision.FaceDetector.create_from_options(detector_options)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/enroll")
async def enroll_person(
    name: str = Form(...),
    employee_id: str = Form(...),
    access_level: str = Form(...),
    photo: UploadFile = File(...),
):
    image_bytes = await photo.read()
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
    )
    result = detector.detect(mp_image)

    if not result.detections:
        raise HTTPException(status_code=422, detail="No face detected in the uploaded image.")

    if len(result.detections) > 1:
        raise HTTPException(
            status_code=422,
            detail="Multiple faces detected. Upload an image with a single face.",
        )

    return {
        "name": name,
        "employee_id": employee_id,
        "access_level": access_level,
        "status": "face_detected_pending_embedding",
    }