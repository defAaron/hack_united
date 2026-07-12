# ClipCoach — AI Post-Game Highlight Editor
### Product Requirements Document (PRD)
**Hackathon:** Hack United — Sport Track  
**Version:** 1.1 (As-built)  
**Last updated:** July 12, 2026

---

## 1. Overview

### 1.1 Problem Statement
Amateur teams, high school/college athletes, weekend leagues, and content creators record hours of raw game footage but rarely have the time, tools, or editing skill to turn it into shareable highlight reels. Professional teams have dedicated video staff; everyone else is stuck scrubbing through 90+ minutes of footage manually, or the footage never gets watched again.

### 1.2 Solution
**ClipCoach** is a web app that ingests raw game footage (any sport), automatically detects the most exciting/important moments using multimodal signal analysis (audio spikes + motion/visual peaks), and auto-generates a polished, music-synced highlight reel. Users can then tweak the timeline (keep/drop, reorder, nudge) and re-render without re-uploading.

### 1.3 Elevator Pitch
"Upload your game tape. Get a highlight reel back in minutes — no editor, no timeline, no skills needed."

### 1.4 Track & Theme Fit
- **Sport Track**: built for sports footage (soccer, basketball, football, etc.).
- Judging criteria fit:
  - **Creativity**: multimodal event detection (audio + video) for amateur sports.
  - **Technical Complexity**: audio signal processing, motion analysis, event fusion/ranking, automated ffmpeg composition.
  - **Practicality**: usable the day after a game with a simple upload → preview → download flow.

---

## 2. Goals & Non-Goals

### 2.1 Goals (Shipped)
1. Accept uploaded video (mp4/mov), max ~500MB.
2. Detect highlight moments via audio energy + visual motion.
3. Rank/select clips to hit a user-chosen reel length (30 / 60 / 90s).
4. Cut and stitch clips with ffmpeg (single-pass filter graph preferred).
5. Mix a chosen royalty-free soundtrack with original game audio (ducked).
6. Preview and download the rendered reel in-browser.
7. Timeline editor: keep/drop, reorder, ±2s nudge, re-render from existing source.
8. Simple web UI: upload → processing status → preview/edit → download.
9. Hosted deployment: Next.js on Vercel + FastAPI on Railway.

### 2.2 Stretch / Future
- Scoreboard OCR / jersey detection.
- Sport-specific presets and richer pre-generate sliders.
- “Why selected” explainability cards per clip.
- Social export presets (9:16 / 16:9).
- Persistent cloud storage / shareable links.

### 2.3 Non-Goals (Out of Scope)
- Live/real-time streaming ingestion.
- Mobile native app.
- Multi-user accounts / auth.
- Sport-specific rule engines.
- Broadcast-quality color grading.

---

## 3. Target Users & Use Cases

| User | Use Case |
|---|---|
| Amateur/rec league team manager | Shareable highlight reel for group chat / socials |
| High school/college athlete | Recruiting reel |
| Sports content creator | Faster highlight production |
| Parent filming kids' games | Fun recap for family |
| Hackathon judges | Live upload demo |

### 3.1 User Stories
- Upload a full match recording and get a highlight reel without scrubbing footage.
- Reel should feel produced (music + clean cuts).
- See processing progress so large uploads don’t feel frozen.
- Preview, lightly edit the timeline, and download the final video.

---

## 4. Product Requirements

### 4.1 Functional Requirements

**FR1 — Upload**
- Upload mp4/mov; client validates type/size.
- Choose soundtrack and target duration (30/60/90s).

**FR2 — Processing Pipeline**
- Extract audio; analyze energy/RMS over windows (librosa).
- Sample low-res frames via ffmpeg; compute frame-difference motion.
- Fuse audio + motion into an excitement curve; select spaced local maxima.
- Expand peaks into clip windows (pre/post roll); fill target duration.

**FR3 — Video Composition**
- Cut/concat selected segments with ffmpeg.
- Mix background music under original audio (ducking).
- Cap render height on hosted environments to avoid OOM.

**FR4 — Playback, Edit & Export**
- In-browser preview + download.
- Timeline editor → `POST /api/jobs/{id}/rerender` without re-upload/re-analysis.

**FR5 — Status/Feedback**
- Stages: queued → analyzing_audio → analyzing_motion → selecting_highlights → rendering → done/error.

### 4.2 Non-Functional Requirements
- **Performance**: ~10–20 min clip analyzed + rendered in minutes on demo hardware (downsampled motion analysis).
- **Reliability**: flat audio falls back toward motion-only scoring.
- **Usability**: no login; single-page flow.
- **Deployment**: Vercel frontend + Railway Docker backend with CORS + healthcheck.

---

## 5. System Architecture

### 5.1 High-Level Architecture
```
┌─────────────┐     upload      ┌──────────────────┐
│   Frontend  │ ───────────────▶ │   Backend API     │
│  (Next.js)  │                  │  (FastAPI)        │
│             │ ◀─── status/ ──  │                    │
└─────────────┘     result       └─────────┬──────────┘
                                            │
                          ┌─────────────────┼─────────────────┐
                          ▼                 ▼                 ▼
                 ┌────────────────┐ ┌───────────────┐ ┌───────────────┐
                 │ Audio Analysis │ │ Motion        │ │ Event Fusion  │
                 │ (librosa)      │ │ (ffmpeg+numpy)│ │ & Ranking     │
                 └────────────────┘ └───────────────┘ └───────┬───────┘
                                                                ▼
                                                     ┌───────────────────┐
                                                     │ Video Composer     │
                                                     │ (ffmpeg)           │
                                                     └─────────┬───────────┘
                                                                ▼
                                                     ┌───────────────────┐
                                                     │ Highlight reel     │
                                                     │ (local storage)    │
                                                     └───────────────────┘
```

### 5.2 Processing Pipeline (Detail)

1. **Ingestion** — save upload; probe duration via ffprobe.
2. **Audio Analysis** — ffmpeg extract WAV → librosa RMS/energy → normalized excitement curve.
3. **Motion Analysis** — ffmpeg low-res grayscale pipe → frame differencing → normalized curve.
4. **Fusion & Ranking** — weighted sum; local maxima with min gap; greedy fill to target duration; chronological order.
5. **Composition** — single-pass ffmpeg filter graph (trim/scale/concat); music mix with ducking; height cap for hosted RAM.
6. **Delivery** — store under `storage_data/{job_id}/`; serve via `/media`.

### 5.3 Tech Stack (As-built)

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, ogl (Strands background) |
| Backend API | FastAPI + background threads for jobs |
| Audio | librosa + system ffmpeg |
| Motion | ffmpeg frame stream + numpy |
| Composition | system ffmpeg (no moviepy) |
| Storage | Local filesystem per job |
| Deploy | Vercel (frontend) + Railway Docker (backend) |

### 5.4 API Contract

```
POST /api/upload
  multipart: file, music_track_id?, target_duration_seconds? (30|60|90)
  → { job_id }

GET /api/status/{job_id}
  → { job_id, stage, progress, message?, error? }

GET /api/result/{job_id}
  → { job_id, video_url, duration_seconds, source_duration_seconds,
      clip_count, clips[], music_track_id?, music_track_title? }

POST /api/jobs/{job_id}/rerender
  JSON: { clips: HighlightClip[] }
  → { job_id }

GET /api/music
  → [{ id, title, preview_url }]

GET /health
  → { status: "ok" }
```

---

## 6. Highlight Detection Algorithm

### 6.1 Signal Model
Two parallel time-series (audio energy, visual motion) → fused excitement curve → peaks = highlight candidates.

### 6.2 Why Multimodal
- Audio catches crowd reactions; can false-positive on music/whistles.
- Motion catches action; can miss quiet celebrations.
- Fusion with tunable weights is more robust than either alone.

### 6.3 Tunable Parameters (env / settings)
- `analysis_window_seconds` (default 0.5)
- `min_gap_between_clips_seconds` (default 8)
- `clip_pre_roll_seconds` / `clip_post_roll_seconds` (default 4 / 4)
- `target_duration_seconds` (default 90; UI offers 30/60/90)
- `audio_weight` / `motion_weight` (default 0.6 / 0.4)
- `motion_sample_fps` (default 2)
- `max_render_height` (default 720; often 480 on Railway)

### 6.4 Fallback
If audio variance is too low, fusion shifts toward motion-only scoring.

---

## 7. UX / UI Flow

1. **Landing** — ClipCoach brand, tagline, upload CTA (Strands background).
2. **Upload** — file picker, reel length, soundtrack with preview.
3. **Processing** — stage labels + progress.
4. **Result** — video player, download, timeline editor, re-render.

### 7.1 Design Principles
- Zero-friction defaults; transparent progress; payoff moment on reveal.

---

## 8. Repo Layout

```
backend/app/services/   audio, motion, fusion, composer, pipeline, music, media_utils
backend/app/api/routes/ jobs, music
frontend/src/           app, components, lib
docs/PRD.md
```

See root `README.md` for setup and deployment.

---

## 9. Success Metrics (Demo-Day)

- End-to-end reel from raw upload within the demo window.
- Selected moments correspond to real exciting plays.
- Final reel feels intentionally edited (music + cuts).
- Clear articulation of multimodal fusion as the technical differentiator.

---

## 10. Pitch Narrative

- **Creativity**: fuses audio + visual motion into a unified excitement score.
- **Technical Complexity**: signal processing, ranking, and automated ffmpeg composition.
- **Practicality**: upload and go — clear path to a real product.
