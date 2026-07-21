from db.database import init_db, insert_person, insert_face, find_closest_match, log_access
from recognition.embedding import extract_embedding
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from typing import Optional

import numpy as np
import mediapipe as mp

import oracledb
import cv2
import os

load_dotenv()

def crop_with_margin(img, bbox, margin: float = 0.3):
    img_h, img_w = img.shape[:2]
    x, y, w, h = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height

    pad_w = int(w * margin)
    pad_h = int(h * margin)

    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(img_w, x + w + pad_w)
    y2 = min(img_h, y + h + pad_h)

    face_crop = img[y1:y2, x1:x2]
    _, buffer = cv2.imencode(".jpg", face_crop)
    return buffer.tobytes()

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
    photo_1: UploadFile = File(...),
    photo_2: Optional[UploadFile] = File(None),
    photo_3: Optional[UploadFile] = File(None),
):
    photos = [p for p in (photo_1, photo_2, photo_3) if p is not None]

    processed_faces = []

    for i, photo in enumerate(photos, start=1):
        image_bytes = await photo.read()
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail=f"Photo {i}: invalid file")

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
        )
        result = detector.detect(mp_image)

        if not result.detections:
            raise HTTPException(status_code=422, detail=f"Photo {i}: no face detected")

        if len(result.detections) > 1:
            raise HTTPException(status_code=422, detail=f"Photo {i}: more than one face detected")

        try:
            embedding = extract_embedding(image)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Photo {i}: {exc}")

        cropped_bytes = crop_with_margin(image, result.detections[0].bounding_box)
        processed_faces.append((embedding, cropped_bytes))

    try:
        person_id = insert_person(name, employee_id, access_level)
    except oracledb.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=f"employee_id '{employee_id}' is already registered.",
        )

    for embedding, cropped_bytes in processed_faces:
        insert_face(person_id, embedding, cropped_bytes)

    return {
        "id": person_id,
        "name": name,
        "employee_id": employee_id,
        "access_level": access_level,
        "photos_registered": len(processed_faces),
        "status": "enrolled",
    }

@app.post("/recognize")
async def recognize_person(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")

    try:
        embedding = extract_embedding(image)
    except ValueError:
        log_access(person_id=None, employee_id=None, recognized=False, access_granted=False, face_image_bytes=image_bytes)
        return {"match": False}

    person = find_closest_match(embedding)

    if person is None:
        log_access(person_id=None, employee_id=None, recognized=False, access_granted=False, face_image_bytes=image_bytes)
        return {"match": False}

    access_granted = person["access_level"] != "Visitor"

    log_access(
        person_id=person["id"],
        employee_id=person["employee_id"],
        recognized=True,
        access_granted=access_granted,
        face_image_bytes=image_bytes,
    )

    return {
        "match": True,
        "name": person["name"],
        "employee_id": person["employee_id"],
        "access_level": person["access_level"],
        "access_granted": access_granted,
    }