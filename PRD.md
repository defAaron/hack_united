# ClipCoach — AI Post-Game Highlight Editor
### Product Requirements Document (PRD)
**Hackathon:** Hack United — Sport Track
**Version:** 1.0 (Hackathon Scope)
**Last updated:** July 10, 2026

---

## 1. Overview

### 1.1 Problem Statement
Amateur teams, high school/college athletes, weekend leagues, and content creators record hours of raw game footage but rarely have the time, tools, or editing skill to turn it into shareable highlight reels. Professional teams have dedicated video staff; everyone else is stuck scrubbing through 90+ minutes of footage manually, or the footage never gets watched again.

### 1.2 Solution
**ClipCoach** is a web app that ingests raw game footage (any sport), automatically detects the most exciting/important moments using multimodal signal analysis (audio spikes, motion/visual peaks, and optional scoreboard/OCR cues), and auto-generates a polished, music-synced highlight reel — with zero manual editing required.

### 1.3 Elevator Pitch
"Upload your game tape. Get a highlight reel back in minutes — no editor, no timeline, no skills needed."

### 1.4 Track & Theme Fit
- **Sport Track**: directly built for sports footage (soccer, basketball, football, etc.), tying into the World Cup theme.
- Judging criteria fit:
  - **Creativity**: multimodal event detection (audio + video) applied to an underserved amateur-sports use case.
  - **Technical Complexity**: audio signal processing, motion analysis/CV, event fusion/ranking algorithm, automated video composition pipeline.
  - **Practicality**: solves a real, immediate pain point; usable by any team the day after a game.

---

## 2. Goals & Non-Goals

### 2.1 Goals (Hackathon MVP)
1. Accept an uploaded video file (mp4) of a game.
2. Automatically detect candidate "highlight" moments using audio energy spikes (crowd noise/celebration) and visual motion peaks.
3. Rank and select the top N moments to hit a target reel duration (e.g., 60–120 seconds).
4. Auto-cut and stitch selected clips with smooth transitions.
5. Auto-sync a background music track to the edit (beat-matched cuts if time allows).
6. Export a final rendered highlight video, playable/downloadable in-browser.
7. Provide a simple web UI: upload → processing status → preview → download.

### 2.2 Stretch Goals (if time permits)
- Scoreboard OCR to detect score-change events precisely (soccer goal, basketball score).
- Player jersey/number detection to auto-tag "who scored."
- User-adjustable "excitement threshold" slider to make reels longer/shorter.
- Auto-generated on-screen captions/graphics (e.g., "GOAL!", timestamp, score).
- Multi-camera angle support (pick best angle per moment).
- Shareable link + social export presets (9:16 for Reels/TikTok, 16:9 for YouTube).

### 2.3 Non-Goals (Explicitly Out of Scope for Hackathon)
- Live/real-time streaming ingestion (batch upload only).
- Mobile native app (web-responsive only).
- Multi-user accounts, auth, or persistent cloud storage beyond session.
- Support for every sport's nuanced rules (focus on generic "action peak" detection, not sport-specific rule engines).
- Professional broadcast-quality color grading/editing.

---

## 3. Target Users & Use Cases

| User | Use Case |
|---|---|
| Amateur/rec league team manager | Upload game footage, get shareable highlight reel for team group chat / socials |
| High school/college athlete | Build a highlight reel for recruiting purposes |
| Sports content creator | Speed up highlight production for a channel |
| Parent filming kids' games | Turn raw footage into a fun recap to share with family |
| Hackathon judges (demo) | Upload a sample clip live, see reel generated in real time |

### 3.1 User Stories
- As a team manager, I want to upload my full match recording and get a 90-second highlight reel without manually scrubbing through footage.
- As a user, I want the reel to feel "produced" — with music and smooth cuts — not just a raw montage.
- As a user, I want to see processing progress so I know the app isn't frozen on a large file.
- As a user, I want to preview and download the final video easily.

---

## 4. Product Requirements

### 4.1 Functional Requirements

**FR1 — Upload**
- User can upload a video file (mp4/mov), max size ~500MB for hackathon demo (or provide a preset sample video for judges).
- Client validates file type/size before upload.

**FR2 — Processing Pipeline**
- System extracts audio track and analyzes energy/amplitude over time to find spikes (cheering, whistle, impact sounds).
- System samples video frames and computes motion intensity (optical flow or frame-differencing) to find action bursts.
- System fuses audio + visual signals into a single "excitement score" timeline.
- System selects local maxima above a threshold as candidate highlight timestamps, with a minimum gap between selections to avoid duplicates/overlaps.
- System expands each selected timestamp into a clip window (e.g., 3s before, 4s after the peak) for context.
- System trims/merges clips to fit a target total duration (default 90s, configurable).

**FR3 — Video Composition**
- System cuts the selected clip segments from the source video.
- System applies simple transitions between clips (hard cut or short crossfade).
- System overlays a background music track (royalty-free, pre-selected or user-chosen from a small library) at appropriate volume, ducking under original clip audio.
- System renders a single output video file.

**FR4 — Playback & Export**
- User can preview the rendered highlight reel in-browser.
- User can download the final mp4.
- (Stretch) User can regenerate with different duration/threshold settings without re-uploading.

**FR5 — Status/Feedback**
- UI shows processing stages (Uploading → Analyzing Audio → Analyzing Motion → Selecting Highlights → Rendering → Done) with progress indication.

### 4.2 Non-Functional Requirements
- **Performance**: process a 10–20 minute clip in under ~2–3 minutes on demo hardware (use downsampled analysis resolution/frame rate to stay fast).
- **Reliability**: pipeline should gracefully handle videos with no clear audio spikes (fallback to motion-only scoring).
- **Usability**: no login required; single-page flow simple enough for a live judge demo.
- **Portability**: runs locally via Docker/simple setup for demo; not required to be cloud-deployed, but bonus if hosted.

---

## 5. System Architecture

### 5.1 High-Level Architecture
```
┌─────────────┐     upload      ┌──────────────────┐
│   Frontend  │ ───────────────▶ │   Backend API     │
│  (React/    │                  │  (FastAPI/Node)    │
│   Next.js)  │ ◀─── status/ ──  │                    │
└─────────────┘     result       └─────────┬──────────┘
                                            │
                          ┌─────────────────┼─────────────────┐
                          ▼                 ▼                 ▼
                 ┌────────────────┐ ┌───────────────┐ ┌───────────────┐
                 │ Audio Analysis │ │ Motion/Video  │ │ Event Fusion  │
                 │ (librosa/ffmpeg)│ │ Analysis (CV) │ │ & Ranking     │
                 └────────────────┘ └───────────────┘ └───────┬───────┘
                                                                ▼
                                                     ┌───────────────────┐
                                                     │ Video Composer     │
                                                     │ (moviepy/ffmpeg)    │
                                                     └─────────┬───────────┘
                                                                ▼
                                                     ┌───────────────────┐
                                                     │ Rendered Highlight │
                                                     │ Reel (mp4) → CDN/  │
                                                     │ local storage      │
                                                     └───────────────────┘
```

### 5.2 Processing Pipeline (Detail)

1. **Ingestion**
   - Save uploaded file to temp storage (local disk / S3 bucket).
   - Extract metadata (duration, fps, resolution) via `ffprobe`.

2. **Audio Analysis**
   - Extract audio track via `ffmpeg`.
   - Compute short-time energy / RMS amplitude over sliding windows (e.g., 0.5s windows) using `librosa`.
   - Normalize and smooth signal; detect peaks above a dynamic threshold (mean + k·stddev).
   - Output: list of `(timestamp, audio_excitement_score)`.

3. **Visual Motion Analysis**
   - Sample video frames at reduced rate (e.g., 5 fps) for speed.
   - Compute frame-to-frame motion magnitude via optical flow (OpenCV `calcOpticalFlowFarneback` or simpler frame differencing for speed).
   - Aggregate motion score per time window matching audio windows.
   - Output: list of `(timestamp, motion_excitement_score)`.

4. **Event Fusion & Ranking**
   - Normalize both signal arrays to 0–1 scale.
   - Combine: `excitement(t) = w_audio * audio(t) + w_motion * motion(t)` (default weights ~0.6 audio / 0.4 motion, tunable).
   - Find local maxima with minimum spacing (e.g., 8s apart) to avoid near-duplicate clips.
   - Sort candidates by score descending; greedily select top candidates until target reel duration is filled (respecting per-clip length ~5–8s).
   - Re-sort selected clips by original chronological order for natural narrative flow.

5. **Video Composition**
   - Use `moviepy` (or direct `ffmpeg` filter graph for performance) to:
     - Cut each selected segment from the source video.
     - Concatenate segments with short crossfade transitions.
     - Overlay chosen background music track, looped/trimmed to reel length, mixed under original audio (ducking original audio to ~40% volume, music to ~70%).
   - Render final mp4 (H.264, 1080p or downscaled for speed).

6. **Delivery**
   - Store rendered file; return signed URL / local path to frontend.
   - Frontend displays video player + download button.

### 5.3 Tech Stack (Proposed)

| Layer | Technology |
|---|---|
| Frontend | React + Vite (or Next.js), Tailwind CSS |
| Backend API | FastAPI (Python) — best ecosystem fit for audio/video ML libs |
| Audio processing | `librosa`, `ffmpeg` |
| Video/motion processing | OpenCV, `ffmpeg` |
| Video composition/render | `moviepy` (wraps ffmpeg) or raw `ffmpeg` filter graphs for speed |
| Task orchestration | Simple async background task (FastAPI `BackgroundTasks` or Celery+Redis if time allows) |
| Storage | Local filesystem for hackathon demo; S3-compatible bucket if deployed |
| Deployment (optional) | Docker Compose; Render/Railway/Fly.io for live demo |

### 5.4 Data Flow / API Contract (Sketch)

```
POST /api/upload
  → multipart/form-data { file }
  ← { job_id }

GET /api/status/{job_id}
  ← { status: "analyzing_audio" | "analyzing_motion" | "selecting" | "rendering" | "done" | "error",
      progress: 0-100 }

GET /api/result/{job_id}
  ← { video_url, duration, clip_count, thumbnail_url }
```

---

## 6. Highlight Detection Algorithm — Design Notes

### 6.1 Signal Model
Treat the game footage as two parallel time-series signals (audio energy, visual motion), each producing an "excitement curve" over time. Peaks in the fused curve correspond to likely highlight moments (goals, big plays, celebrations, collisions).

### 6.2 Why Multimodal Fusion (Creativity/Complexity Angle)
- Audio-only detection catches crowd reactions but can false-positive on music/whistles/commentary.
- Motion-only detection catches fast action (sprints, collisions) but misses celebration moments where motion is actually a crowd stand-up rather than on-field.
- Fusing both, with tunable weighting, produces a more robust "excitement score" than either alone — a genuinely non-trivial signal processing problem, which strengthens the technical complexity narrative for judges.

### 6.3 Tunable Parameters
- `window_size` (analysis granularity, default 0.5s)
- `min_gap_between_clips` (default 8s)
- `clip_pre_roll` / `clip_post_roll` (default 3s / 4s)
- `target_duration` (default 90s)
- `audio_weight` / `motion_weight` (default 0.6 / 0.4)

### 6.4 Fallback Behavior
If audio signal is too flat (e.g., no crowd, silent gym footage), auto-shift weighting toward motion-only scoring. Detect this by checking variance of the normalized audio signal against a minimum threshold.

---

## 7. UX / UI Flow

1. **Landing Page** — Product name, tagline, "Upload Your Game Footage" CTA. Optional "Try a Sample Clip" button for judges/demo speed.
2. **Upload Screen** — Drag-and-drop or file picker; shows file name/size/duration once selected; "Generate Highlights" button.
3. **Processing Screen** — Progress bar with stage labels ("Analyzing crowd reactions...", "Detecting big plays...", "Editing your reel..."); estimated time remaining.
4. **Result Screen** — Embedded video player with the rendered highlight reel; Download button; (stretch) "Regenerate with different settings" controls (duration slider, music picker).
5. **(Stretch) Share Screen** — Copyable link, social-format export buttons (9:16 / 16:9).

### 7.1 Design Principles
- Zero-friction: no sign-up, no complex settings by default (smart defaults do the work).
- Transparent progress: users should never wonder if it's frozen — always show current pipeline stage.
- Delight: the reveal of the finished highlight reel should feel like a payoff moment (e.g., subtle animation/confetti on completion).

---

## 8. Milestones / Hackathon Build Plan

Given a typical ~24–36 hour hackathon window:

| Phase | Time | Tasks |
|---|---|---|
| **Hour 0–2** | Setup | Repo scaffolding, FastAPI + React boilerplate, sample footage sourcing (grab a few free stock sports clips/World Cup highlights for testing) |
| **Hour 2–8** | Core pipeline v1 | Audio energy extraction + peak detection working end-to-end on a sample video; CLI script proving the algorithm before wiring UI |
| **Hour 8–14** | Motion analysis + fusion | Add optical flow/motion scoring; combine into fused excitement curve; tune thresholds against sample footage |
| **Hour 14–20** | Video composition | Auto-cut + concatenate clips, add music overlay, render final mp4; wire up backend job status API |
| **Hour 20–28** | Frontend integration | Build upload → progress → result UI; connect to backend; end-to-end test with real uploads |
| **Hour 28–32** | Polish | Transitions/crossfades, UI polish, error handling, prepare 2–3 great demo clips |
| **Hour 32–36** | Demo prep | Record backup demo video (in case live processing fails), rehearse pitch, prepare slides tying back to judging criteria |

### 8.1 Risk Mitigation
- **Risk**: live processing too slow/flaky during judging → **Mitigation**: pre-process 1–2 impressive sample videos ahead of time as a guaranteed fallback demo, while still showing live upload capability.
- **Risk**: ffmpeg/moviepy rendering performance issues → **Mitigation**: downscale resolution/frame sampling rate aggressively for analysis; only use full resolution for final render.
- **Risk**: poor highlight selection on unfamiliar footage → **Mitigation**: test early against 3–4 varied sample clips (soccer, basketball) and tune thresholds/weights before demo day.

---

## 9. Success Metrics (Demo-Day Framing)

Since this is a hackathon (not production), success = judge-perceived value:
- Reel is generated end-to-end from raw upload within the live demo time window.
- Selected highlight moments visibly correspond to real exciting moments (goals, big plays) — judges should immediately recognize the selections as "correct."
- Final reel feels intentionally edited (music sync, transitions), not just a random montage.
- Clear articulation during pitch of the multimodal signal-fusion technical approach (this is the technical complexity differentiator vs. a naive "just cut every N seconds" approach).

---

## 10. Pitch Narrative (Tie-back to Judging Criteria)

- **Creativity**: Most highlight tools either require manual tagging or rely on a single signal (e.g., just audio). ClipCoach fuses audio + visual motion signals into a unified excitement score — a novel, from-scratch approach to automatic sports editing.
- **Technical Complexity**: Real signal processing (audio energy analysis, optical flow motion detection), a custom event-fusion/ranking algorithm, and an automated video composition pipeline (cutting, transitions, audio mixing, rendering) — multiple non-trivial systems working together.
- **Practicality**: Every rec league, high school team, and content creator has this exact problem today. No specialized hardware, no manual editing skill required — just upload and go. Clear path to a real product (subscription/team-plan model, integration with team management apps).

---

## 11. Open Questions / Decisions Needed
- Confirm target sports for demo footage (soccer + basketball recommended for visual/audio variety).
- Decide: pre-baked music library (2–3 tracks) vs. user upload — recommend pre-baked for hackathon simplicity.
- Decide: local Docker demo vs. hosted deployment — recommend local-first with hosted as stretch if time allows.
- Decide on fallback/backup demo video strategy (recommended: yes, always have one).
