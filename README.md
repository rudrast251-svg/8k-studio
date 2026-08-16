# 8K Studio

AI-powered photo & video enhancement platform. Upload media, describe what you want in
plain English ("make this video 8K, cinematic, brighter, and smoother"), and the platform
runs it through a real background processing pipeline — plus an AI-driven website editor
that lets an admin restyle the live homepage by typing commands.

Built with Django (chosen because this environment has Python/Django available to actually
install, migrate, and test — not Node.js).

## What's real vs. demo mode

- **Real GPU AI provider**: when `REPLICATE_API_TOKEN` is set, image jobs call a real
  Real-ESRGAN model and video jobs call a real video upscaling model on
  [Replicate](https://replicate.com), asynchronously, over HTTP (`studio/ai/replicate_client.py`).
- **Demo mode** (default, no keys required): when no token is configured, jobs are still
  processed for real — just locally, with Pillow/OpenCV — instead of pretending:
  - Images: genuine Lanczos upscaling, unsharp-mask sharpening, fastNlMeans denoising,
    brightness/color grading, and real GrabCut-based background removal
    (`studio/ai/image_pipeline.py`).
  - Video: genuine frame-by-frame OpenCV processing — resize upscaling, bilateral
    denoising, sharpening, color grading, optical-flow-based stabilization, and
    frame-blend motion smoothing — written out as real, browser-playable H.264 (see
    "OpenH264 codec" below). Video jobs cannot preserve original audio in demo mode (no
    bundled audio muxer); this is surfaced to the user, not silently dropped.
  - Every demo job also shows a "Provider: Demo (local processing)" badge and lists which
    requested operations (e.g. face restoration) require a connected AI provider.
- **Instruction parsing**: a deterministic keyword parser always runs
  (`studio/ai/instructions.py`, `siteeditor/ai.py`). If `ANTHROPIC_API_KEY` is set, Claude
  is used for more flexible natural-language understanding and merged with the keyword
  parse for robustness.
- **Payments**: plan upgrades run for real via Stripe Checkout if `STRIPE_SECRET_KEY` is
  set; otherwise upgrades run in a clearly-labeled demo mode that switches your plan and
  grants credits instantly without charging a card.
- **Storage**: local disk by default; set `AWS_STORAGE_BUCKET_NAME` (+ keys) to switch to
  S3-compatible object storage (works with AWS S3, Cloudflare R2, Backblaze B2, etc.).

## Architecture

- `accounts` — custom email-based User model with a credit balance and plan.
- `studio` — Asset & Job models, the AI processing pipelines, upload/dashboard/queue/library
  views, and the background worker (`manage.py process_jobs`).
- `billing` — Plan, CreditTransaction ledger, Stripe checkout / demo upgrade flow.
- `siteeditor` — the editable `SiteConfig` singleton that drives the public homepage
  (colors, headline, hero video/image, autoplay/mute, CTA), the AI command parser, and the
  staff-only live-preview editor at `/site-editor/`.
- `corepages` — the public marketing/landing page.

### Background jobs & the processing queue

Jobs move through `uploaded → processing → completed | failed`. There's no Redis/Celery
dependency: jobs are claimed from Postgres/SQLite with an atomic conditional `UPDATE`
(`studio/management/commands/process_jobs.py`), which is portable across both databases.
Run the worker as its own process:

```bash
python manage.py process_jobs --loop     # long-running worker (use in production)
python manage.py process_jobs --once     # drain the queue once, then exit (handy for testing)
```

On job completion (or failure, with an automatic credit refund) an in-app `Notification`
is created and the user sees it via the bell icon, which polls every 15s. The job detail
page polls its own status every 2.5s while processing so the before/after preview and
download button appear automatically.

### OpenH264 codec (Windows dev only)

`bin/openh264-2.5.0-win64.dll` is Cisco's redistributable OpenH264 codec, loaded at
startup (`studio/apps.py`) so OpenCV can write real H.264 `.mp4` output on Windows during
local development — this was verified to actually play in Chromium, not just open with
OpenCV. On Linux (most production hosts), install system `ffmpeg` for the same
capability; if no H.264 encoder is available at all, video jobs fail cleanly with a clear
error and an automatic credit refund rather than producing a broken file.

## Getting started

```bash
python -m venv venv
./venv/Scripts/activate        # or `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env           # defaults already work for local demo mode
python manage.py migrate
python manage.py seed_demo     # plans, default site config, generated demo sample media
python manage.py runserver
```

In a second terminal, run the worker so uploaded jobs actually get processed:

```bash
python manage.py process_jobs --loop
```

Visit `http://127.0.0.1:8000/`. Sign up for a free account (25 credits), or sign in as the
seeded admin if you set `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env` before running `seed_demo`.

## Enabling real AI processing

Add to `.env`:

```
REPLICATE_API_TOKEN=r8_your_token
ANTHROPIC_API_KEY=sk-ant-your-key   # optional, improves instruction parsing
STRIPE_SECRET_KEY=sk_...            # optional, enables real payments
```

Restart the app and worker. The demo-mode banner disappears and jobs are sent to
Replicate instead of processed locally.

## Admin

Django admin (`/admin/`) manages users, plans, credit transactions, jobs (with a "requeue
failed jobs" action), assets, notifications, and the site configuration — everything the
brief asks for in one place, backed by the same database as the app.

Made by Rudra Tiwari.
