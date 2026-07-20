import numpy as np
from insightface.app import FaceAnalysis

_face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
_face_app.prepare(ctx_id=0, det_size=(640, 640))


def extract_embedding(image: np.ndarray) -> np.ndarray:
    """
    Inse receives an image in BGR and returns
    the 512-dimensional facial embedding of the first face found.
    Raises a ValueError if no face is detected by insightface.
    """
    faces = _face_app.get(image)

    if not faces:
        raise ValueError("insightface could not extract a face embedding from this image.")

    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

    return face.embedding.astype(np.float32)