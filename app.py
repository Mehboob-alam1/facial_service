"""
Smart Campus — Face Recognition API (Railway)

POST /register-roster { "user_id": "<firebase_uid>", "image_base64": "..." }  # teacher/admin
POST /register-face   { "user_id": "<firebase_uid>", "image_base64": "..." }  # student (must match roster)
POST /verify-face     { "user_id": "<firebase_uid>", "image_base64": "..." }  # daily attendance
GET  /health

Flutter (Firebase Auth) sends the Firebase UID as user_id.
"""
import base64
import os
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATA_DIR = Path(os.environ.get("EMBEDDINGS_DIR", str(Path(__file__).resolve().parent / "data" / "embeddings")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

MATCH_THRESHOLD = float(os.environ.get("MATCH_THRESHOLD", "0.68"))

_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def _decode_to_gray(image_base64: str) -> np.ndarray:
    raw = base64.b64decode(image_base64)
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image data")
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _crop_face(gray: np.ndarray) -> np.ndarray:
    faces = _cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
    )
    if len(faces) == 0:
        raise ValueError("No face detected — look at the camera with good lighting")
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face = gray[y : y + h, x : x + w]
    face = cv2.resize(face, (200, 200))
    return cv2.equalizeHist(face)


def _safe_id(user_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(user_id))


def _user_path(user_id: str) -> Path:
    return DATA_DIR / f"{_safe_id(user_id)}.npy"


def _roster_path(user_id: str) -> Path:
    return DATA_DIR / f"{_safe_id(user_id)}_roster.npy"


def _similarity(a: np.ndarray, b: np.ndarray) -> float:
    aa = a.astype(np.float64).ravel()
    bb = b.astype(np.float64).ravel()
    if aa.std() < 1e-6 or bb.std() < 1e-6:
        return 0.0
    corr = float(np.corrcoef(aa, bb)[0, 1])
    if np.isnan(corr):
        return 0.0
    return corr


@app.get("/")
def root():
    return jsonify(
        {
            "service": "smartcampus-face-api",
            "ok": True,
            "endpoints": ["/health", "/register-roster", "/register-face", "/verify-face"],
        }
    )


@app.get("/health")
def health():
    return jsonify(
        {
            "ok": True,
            "engine": "opencv-haar-corr",
            "threshold": MATCH_THRESHOLD,
            "embeddings_dir": str(DATA_DIR),
        }
    )


@app.post("/register-roster")
def register_roster():
    try:
        body = request.get_json(force=True) or {}
        user_id = str(body.get("user_id") or "").strip()
        b64 = body.get("image_base64") or ""
        if not user_id or not b64:
            return jsonify({"error": "user_id and image_base64 required"}), 400
        face = _crop_face(_decode_to_gray(b64))
        np.save(str(_roster_path(user_id)), face.astype(np.uint8))
        enrolled = _user_path(user_id)
        if enrolled.exists():
            enrolled.unlink()
        return jsonify({"success": True, "message": "Roster photo saved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.post("/register-face")
def register_face():
    try:
        body = request.get_json(force=True) or {}
        user_id = str(body.get("user_id") or "").strip()
        b64 = body.get("image_base64") or ""
        if not user_id or not b64:
            return jsonify({"error": "user_id and image_base64 required"}), 400

        roster = _roster_path(user_id)
        if not roster.exists():
            return jsonify(
                {
                    "error": "No class photo on file. Ask your teacher/admin to upload your roster photo first.",
                    "matched": False,
                }
            ), 400

        face = _crop_face(_decode_to_gray(b64))
        stored = np.load(str(roster))
        score = _similarity(stored, face)
        if score < MATCH_THRESHOLD:
            return jsonify(
                {
                    "error": "Live face does not match your class photo. Try better lighting or contact admin.",
                    "matched": False,
                    "similarity": round(score, 4),
                    "threshold": MATCH_THRESHOLD,
                }
            ), 400

        np.save(str(_user_path(user_id)), face.astype(np.uint8))
        return jsonify(
            {
                "success": True,
                "matched": True,
                "message": "Face registered — matched class photo",
                "similarity": round(score, 4),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e), "matched": False}), 400


@app.post("/verify-face")
def verify_face():
    """Daily attendance: live selfie must match enrolled face and class (roster) photo."""
    try:
        body = request.get_json(force=True) or {}
        user_id = str(body.get("user_id") or "").strip()
        b64 = body.get("image_base64") or ""
        if not user_id or not b64:
            return jsonify({"error": "user_id and image_base64 required", "matched": False}), 400

        enrolled_path = _user_path(user_id)
        roster_path = _roster_path(user_id)
        if not enrolled_path.exists():
            return jsonify(
                {"error": "No registered face for this user — register face first", "matched": False}
            ), 400
        if not roster_path.exists():
            return jsonify(
                {
                    "error": "No class photo on file. Ask your teacher to upload your photo first.",
                    "matched": False,
                }
            ), 400

        face = _crop_face(_decode_to_gray(b64))
        enrolled = np.load(str(enrolled_path))
        roster = np.load(str(roster_path))
        score_enrolled = _similarity(enrolled, face)
        score_roster = _similarity(roster, face)

        # Must look like the enrolled selfie AND the teacher's class photo
        matched = score_enrolled >= MATCH_THRESHOLD and score_roster >= MATCH_THRESHOLD
        return jsonify(
            {
                "matched": bool(matched),
                "similarity": round(score_enrolled, 4),
                "similarity_roster": round(score_roster, 4),
                "threshold": MATCH_THRESHOLD,
                "error": None
                if matched
                else "Face not matched to your class photo / registered face",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e), "matched": False}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
