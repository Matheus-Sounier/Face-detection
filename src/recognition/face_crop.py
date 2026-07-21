import cv2

def crop_face(img, x, y, w, h, margin=0.4):
    img_h, img_w = img.shape[:2]

    pad_w = int(w * margin)
    pad_h = int(h * margin)

    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(img_w, x + w + pad_w)
    y2 = min(img_h, y + h + pad_h)

    face_crop = img[y1:y2, x1:x2]

    _, buffer = cv2.imencode(".jpg", face_crop)
    return buffer.tobytes()