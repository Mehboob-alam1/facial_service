# Smart Campus Face API (Railway)

Standalone **Python Flask** service for face registration & verification.  
Use this with your **Flutter + Firebase** app (Firebase Auth UID = `user_id`).

This folder is meant to be its **own GitHub repo** and deployed on **Railway**.

## Architecture

```
Flutter app  →  Firebase Auth + Firestore  (users, complaints, attendance)
             →  this API on Railway      (register-face / verify-face only)
```

## API

| Method | Path | Body |
|--------|------|------|
| GET | `/health` | — |
| POST | `/register-face` | `{ "user_id": "<firebase_uid>", "image_base64": "..." }` |
| POST | `/verify-face` | `{ "user_id": "<firebase_uid>", "image_base64": "..." }` → `{ "matched": true/false }` |

## 1) Create a new GitHub repo

From this folder:

```bash
cd smartcampus-face-api
git init
git add .
git commit -m "Initial Smart Campus face API for Railway"
# Create empty repo on GitHub, then:
git branch -M main
git remote add origin https://github.com/YOUR_USER/smartcampus-face-api.git
git push -u origin main
```

## 2) Deploy on Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Select **`smartcampus-face-api`**
3. Railway will build with the **Dockerfile**
4. Open **Settings → Networking → Generate Domain** (public HTTPS URL)
5. Optional variables:

| Variable | Default | Meaning |
|----------|---------|---------|
| `MATCH_THRESHOLD` | `0.68` | Higher = stricter face match |
| `EMBEDDINGS_DIR` | `/data/embeddings` | Where face templates are stored |

6. (Recommended) Add a **Volume** mounted at `/data` so faces survive redeploys.

Copy your public URL, e.g.:

`https://smartcampus-face-api-production.up.railway.app`

(no trailing slash)

## 3) Point the Flutter app at Railway

In the **smartcampus** Flutter project:

```bash
flutter run --dart-define=PYTHON_FACE_URL=https://YOUR-RAILWAY-URL.up.railway.app
```

Or set the default in `lib/config/app_config.dart`:

```dart
defaultValue: 'https://YOUR-RAILWAY-URL.up.railway.app',
```

## 4) Local test (optional)

```bash
cd smartcampus-face-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5001/health
```

## Notes

- Embeddings are stored on disk. Without a Railway volume, **redeploy may wipe registered faces** (students must register again).
- This uses OpenCV (lightweight, fits Railway). The heavier DeepFace version lives in `../face_service/app.py` if you upgrade later.
- Firebase is **not** hosted here — only face ML. Auth & database stay on Firebase.
