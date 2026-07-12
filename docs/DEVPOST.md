# ClipCoach — Devpost Writeup

## Inspiration

Anyone who has played on a rec league team, coached a youth squad, or filmed a friend's weekend soccer match knows the ritual: you record 90 minutes of footage, promise yourself you'll "cut together the good parts later," and then… never do. Professional and college teams have video staff to build recruiting reels and hype clips. Everyone else just has a giant unwatched file sitting in their camera roll.

I wanted to build something that gave that same "produced" feeling — smooth cuts, music-synced highlights — to anyone, for any sport, with zero editing skill required. The core idea: a highlight moment isn't defined by any single signal. A goal is loud (crowd noise) *and* fast (players sprinting, camera whipping around). So instead of building "yet another audio-spike detector," I set out to fuse multiple signals into one excitement curve, the same way a human editor intuitively reacts to both what they hear and what they see.

## What it does

ClipCoach turns a raw, unedited game recording into a polished, music-synced highlight reel automatically:

1. **Upload** any game footage (mp4/mov) through the web app, pick a target reel length (30 / 60 / 90s) and a soundtrack.
2. **Analyze** the video along two independent tracks — audio energy and visual motion.
3. **Fuse** those two signals into a single excitement curve over time,

   $$
   e(t) = w_a \, a(t) + w_m \, m(t),
   $$

   and pick the peaks.
4. **Compose** the top peaks into clips, trim them to a target duration budget, and stitch them together with background music mixed under the original game audio.
5. **Deliver** a finished mp4 the user can preview in-browser, download, or fine-tune with a built-in timeline editor (keep / drop / reorder / nudge clips) and re-render instantly — without re-uploading or re-analyzing.

## How I built it

The backend is a FastAPI service that models the whole job as an async pipeline with explicit stages:

`queued` → `analyzing_audio` → `analyzing_motion` → `selecting_highlights` → `rendering` → `done`

so the frontend can show real progress instead of a spinner of faith.

- **Audio excitement** (`audio_analysis.py`) — extract the audio track via `ffmpeg`, compute short-time RMS energy with `librosa` over sliding windows, and normalize to $[0, 1]$.
- **Motion excitement** (`motion_analysis.py`) — decode a tiny grayscale proxy stream ($320 \times 180$, at most $5$ fps) straight from `ffmpeg` and compute simple frame-difference motion magnitude:

  $$
  m(t) = \frac{1}{N} \sum_{i=1}^{N} \bigl| F_t[i] - F_{t-1}[i] \bigr|
  $$

  I deliberately avoided walking full-resolution frames in Python (OpenCV optical flow on every decoded frame was far too slow for a live demo).
- **Fusion & ranking** (`fusion.py`) — resample both signals onto a shared time grid, blend them with tunable weights $w_a = 0.6$ and $w_m = 0.4$ by default, then run greedy peak selection with a minimum spacing $\Delta t_{\min} = 8\text{ s}$ so five near-duplicate samples from the same goal celebration don't all make the cut. Expand each peak $t_i$ into a clip window

  $$
  \bigl[t_i - t_{\mathrm{pre}},\; t_i + t_{\mathrm{post}}\bigr]
  $$

  (defaults $t_{\mathrm{pre}} = t_{\mathrm{post}} = 4\text{ s}$), greedily fill a target-duration budget $T$ subject to

  $$
  \sum_i \bigl(\mathrm{end}_i - \mathrm{start}_i\bigr) \le T,
  $$

  and finally re-sort chronologically for a natural narrative arc.
- **Composition** (`composer.py`) — cut and concatenate the selected segments and mix in a chosen royalty-free soundtrack, ducking the original crowd/game audio under the music.
- **Job orchestration** (`job_manager.py`, `pipeline.py`) — runs as a background task per job, tracks stage / progress / errors, and supports a lightweight `run_rerender` path that skips analysis entirely when the user just wants to re-cut the same source with an edited clip list.

On the frontend (Next.js), I built an upload flow with drag-and-drop, a duration/music picker, a progress screen that mirrors the backend's stage machine, a result screen with an embedded player, and a `TimelineEditor` component that lets users visually keep / drop / reorder / nudge clips on a scrubber before triggering a fast re-render — turning a "black box AI edit" into something a user can actually collaborate with.

## Challenges I ran into

- **Naive full-resolution motion analysis was a non-starter.** Our first pass used OpenCV optical flow on every decoded frame — on an 11-minute 1080p clip this took minutes, which would have killed a live demo. I rebuilt motion analysis around a single `ffmpeg` decode pass at a tiny fixed resolution and capped sample rate, trading a bit of precision for a massive speedup.
- **Audio-only detection false-positives** on commentary, whistles, and music, while motion-only detection missed celebration moments where the excitement is in the crowd, not on the field. Neither signal alone was reliable — I needed genuine fusion, with fallback logic: if the audio track's standard deviation is too flat ($\sigma_{\mathrm{audio}} < \sigma_{\min}$, with $\sigma_{\min} = 0.05$), or missing entirely, fusion auto-shifts weight fully onto motion ($w_a \to 0$, $w_m \to 1$).
- **Avoiding duplicate / overlapping highlights.** A single big play can spike the excitement curve across many adjacent samples. Enforcing $\Delta t_{\min}$ between accepted peaks keeps the reel from repeating the same moment three times in a row.
- **Turning "trust the AI" into "collaborate with the AI."** An automatically generated reel is only useful if users can correct it when the algorithm picks a boring clip or misses a good one — so I added a re-render path that reuses the original uploaded source and skips the expensive audio/motion analysis stages entirely, making edits feel instant rather than another multi-minute wait.
- **Split-repo deployment.** The frontend needed to live on Vercel while the media pipeline (`ffmpeg`, `librosa`) needs a persistent process with system binaries, which Vercel serverless functions can't provide — so I split into two deployable services connected by `NEXT_PUBLIC_API_URL`.

## Accomplishments that I'm proud of

- A genuinely non-trivial, from-scratch multimodal signal-fusion pipeline — not just "cut every $N$ seconds" or a single audio threshold — that produces highlight selections a human would recognize as "correct."
- Getting end-to-end processing (upload → analyzed → rendered) fast enough to demo live, after starting from a version that was too slow to trust on stage.
- A graceful fallback path: the pipeline never crashes on silent or audio-poor footage; it just quietly reweights toward motion.
- Shipping a real human-in-the-loop editing experience (the timeline editor + fast re-render) instead of stopping at "here's your one AI-generated video, take it or leave it."

## What I learned

- **Robust automatic editing needs redundant signals.** No single feature (loudness, motion, etc.) is trustworthy enough on its own across varied, messy real-world footage — combining weak, cheap signals with sensible fallbacks beats chasing one perfect signal.
- **Perceived performance matters as much as raw performance.** Explicit pipeline stages with human-readable progress messages ("Detecting big plays…") made a multi-minute wait feel transparent and trustworthy instead of broken.
- **Cheap proxies win under time pressure.** Downsampling resolution and frame rate before doing "real" analysis — rather than reaching for the most accurate CV technique first — was the difference between a pipeline that worked in a hackathon demo and one that didn't.
- **Let users repair AI mistakes cheaply.** Decoupling expensive analysis from cheap re-composition meant a user-editable timeline was almost free to add once the pipeline was already staged that way.

## What's next for ClipCoach

- **Scoreboard / OCR event detection** to pinpoint exact goal / score-change moments rather than inferring them purely from audio/motion peaks.
- **Player / jersey detection** to auto-tag who scored and build player-specific highlight reels (great for recruiting tapes).
- **User-adjustable excitement threshold** so the same footage can produce a tighter 30-second cut or a longer 3-minute recap on demand.
- **Auto-generated captions / graphics** (e.g. "GOAL!", live score, timestamp overlays) to make reels feel even more broadcast-quality.
- **Multi-camera angle support** — pick the best angle per moment when multiple recordings of the same game are available.
- **Social export presets** (9:16 for Reels / TikTok, 16:9 for YouTube) and one-tap shareable links, so a finished reel goes straight from "rendered" to "posted."
