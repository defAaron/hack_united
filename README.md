# ClipCoach

AI-powered post-game highlight editor. Upload raw game footage, get a music-synced highlight reel back automatically — with optional timeline tweaks.

See [`docs/PRD.md`](./docs/PRD.md) for the full product/technical spec, and [`docs/DEVPOST.md`](./docs/DEVPOST.md) for the Devpost writeup.

## Features

- Multimodal highlight detection (audio energy + visual motion)
- Target reel length: 30 / 60 / 90 seconds
- Soundtrack picker with original-audio + music mix
- Timeline editor: keep/drop clips, reorder, ±2s nudge, re-render
- Hosted demo: frontend on Vercel, API on Railway

## Repo Structure

```
hack_united/
├── backend/                 FastAPI service (analysis + rendering)
│   ├── app/
│   │   ├── api/routes/      upload, status, result, rerender, music
│   │   ├── core/            config, job manager, pipeline options
│   │   ├── models/          Pydantic schemas
│   │   ├── services/        audio, motion, fusion, composer, pipeline
│   │   └── storage/         local per-job filesystem storage
│   ├── assets/music/        Royalty-free soundtrack library
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                Next.js (App Router) + Tailwind
│   └── src/
│       ├── app/             pages + global styles
│       ├── components/      upload, processing, result, timeline, strands
│       └── lib/             API client, types, job hook
├── docs/PRD.md
└── README.md
```

## Why this split?

The frontend deploys on **Vercel** (Next.js is a first-class fit). The backend runs the media pipeline (ffmpeg, librosa), which needs a persistent process and system binaries — so it deploys separately (Railway) and the frontend talks to it via `NEXT_PUBLIC_API_URL`.

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
- `app/services/motion_analysis.py` — visual motion via ffmpeg frame stream
- `app/services/fusion.py` — combines signals, selects highlight clips
- `app/services/composer.py` — ffmpeg cut/concat + music mix
- `app/services/media_utils.py` — shared ffprobe helpers
- `app/services/music_catalog.py` — soundtrack library (title → file)
- `app/services/pipeline.py` — orchestrates stages + timeline re-render
- `app/api/routes/jobs.py` — upload / status / result / rerender
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

Tracks live in `backend/assets/music/`. The upload UI lets users pick a song by title; the renderer mixes that track with the original game audio (original ducked under music). To add a track: drop an mp3 into `assets/music/` and add an entry in `app/services/music_catalog.py`.

## API (summary)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/upload` | Upload video (+ optional `music_track_id`, `target_duration_seconds`) |
| `GET` | `/api/status/{job_id}` | Poll pipeline stage / progress |
| `GET` | `/api/result/{job_id}` | Preview URL + clip list |
| `POST` | `/api/jobs/{job_id}/rerender` | Re-render from edited clips |
| `GET` | `/api/music` | Soundtrack catalog |
| `GET` | `/health` | Health check |

## Deployment

- **Frontend (Vercel)**: set root directory to `frontend`. Set `NEXT_PUBLIC_API_URL` to the Railway API URL.
- **Backend (Railway)**: deploy from `backend/` using the Dockerfile. Set:
  - `CLIPCOACH_CORS_ORIGINS` to your Vercel domain(s)
  - optionally `CLIPCOACH_MAX_RENDER_HEIGHT=480` on low-RAM plans
