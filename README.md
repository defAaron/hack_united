# ClipCoach

AI-powered post-game highlight editor. Upload raw game footage, get a music-synced highlight reel back automatically — no manual editing required.

See [`PRD.md`](./PRD.md) for the full product/technical spec.

## Repo Structure

```
hack_united/
├── backend/     FastAPI service: upload, job pipeline (audio + motion analysis,
│                fusion/ranking, video composition), status/result API
├── frontend/    Next.js app (deployed to Vercel): upload UI, processing status,
│                result preview/download
└── PRD.md       Full product requirements document
```

## Why this split?

The frontend is deployed on **Vercel** (Next.js is a first-class fit). The backend
runs the actual media pipeline (ffmpeg, librosa, OpenCV, moviepy), which needs a
persistent process and system binaries — not a great fit for Vercel's serverless
Python functions — so it's deployed separately (Railway/Fly.io/Render all work
well) and the frontend talks to it via `NEXT_PUBLIC_API_URL`.

## Backend — Local Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# ffmpeg must be installed and on PATH
brew install ffmpeg   # macOS

cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Run tests:

```bash
pytest -q
```

Key modules:
- `app/services/audio_analysis.py` — audio excitement curve (librosa)
- `app/services/motion_analysis.py` — visual motion excitement curve (OpenCV)
- `app/services/fusion.py` — combines both signals, selects highlight clips
- `app/services/composer.py` — cuts/concatenates/renders the final reel (moviepy)
- `app/services/pipeline.py` — orchestrates the above, updates job status
- `app/api/routes/jobs.py` — `POST /api/upload`, `GET /api/status/{id}`, `GET /api/result/{id}`
- `app/core/config.py` — all pipeline tuning parameters (env-overridable)

## Frontend — Local Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points NEXT_PUBLIC_API_URL at localhost:8000
npm run dev
```

Open http://localhost:3000.

## Deployment

- **Frontend**: `vercel --prod` from `frontend/` (or connect the repo in the
  Vercel dashboard with root directory set to `frontend`). Set `NEXT_PUBLIC_API_URL`
  to your hosted backend URL in the Vercel project's environment variables.
- **Backend**: deploy via the included `backend/Dockerfile` to Railway/Fly.io/Render.
  Set `CLIPCOACH_CORS_ORIGINS` to your Vercel domain.

## Build Plan

See PRD section 8 for the full hour-by-hour hackathon build plan. Current status:
repo scaffolding + working end-to-end pipeline skeleton (upload → audio/motion
analysis → fusion/ranking → render → download) is complete and tested locally.
