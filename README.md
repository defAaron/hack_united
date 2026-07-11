# ClipCoach

AI-powered post-game highlight editor. Upload raw game footage, get a music-synced highlight reel back automatically — no manual editing required.

See [`docs/PRD.md`](./docs/PRD.md) for the full product/technical spec.

## Repo Structure

```
hack_united/
├── backend/                 FastAPI service (analysis + rendering)
│   ├── app/                 API, pipeline services, models
│   ├── assets/music/        Royalty-free soundtrack library
│   ├── storage_data/        Per-job uploads + rendered reels (gitignored)
│   └── Dockerfile
├── frontend/                Next.js app (Vercel-ready)
├── docs/PRD.md              Product requirements
└── README.md
```

## Why this split?

The frontend is deployed on **Vercel** (Next.js is a first-class fit). The backend
runs the media pipeline (ffmpeg, librosa, OpenCV), which needs a persistent
process and system binaries — so it deploys separately (Railway/Fly/Render) and
the frontend talks to it via `NEXT_PUBLIC_API_URL`.

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
- `app/services/motion_analysis.py` — visual motion excitement curve
- `app/services/fusion.py` — combines both signals, selects highlight clips
- `app/services/composer.py` — cuts/concatenates clips and mixes background music
- `app/services/music_catalog.py` — soundtrack library (title → file)
- `app/services/pipeline.py` — orchestrates the above, updates job status
- `app/api/routes/jobs.py` — upload / status / result
- `app/api/routes/music.py` — list available soundtracks

## Frontend — Local Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points NEXT_PUBLIC_API_URL at localhost:8000
npm run dev
```

Open http://localhost:3000.

## Background Music

Tracks live in `backend/assets/music/`. The upload UI lets users pick a song by
title; the renderer mixes that track with the original game audio (original
ducked under music). To add a track: drop an mp3 into `assets/music/` and add
an entry in `app/services/music_catalog.py`.

## Deployment

- **Frontend**: connect the repo in Vercel with root directory `frontend`. Set
  `NEXT_PUBLIC_API_URL` to your hosted backend URL.
- **Backend**: deploy via `backend/Dockerfile` to Railway/Fly.io/Render.
  Set `CLIPCOACH_CORS_ORIGINS` to your Vercel domain.
