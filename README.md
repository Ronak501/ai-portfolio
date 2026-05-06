# AI Portfolio Auto-Updater

This project auto-detects GitHub repository updates, analyzes repositories, generates AI summaries, ranks projects, stores them in Firestore, and serves them to a React portfolio UI.

## Architecture

GitHub Webhook -> FastAPI Backend -> Repo Analyzer + AI Engine -> Firestore -> React Frontend

## Folder Structure

- backend: FastAPI service with webhook, analyzer, scoring, and Firestore persistence
- frontend: React app that fetches and displays live project data

## Quick Start

### 1) Backend setup

1. Create Python virtual environment.
2. Install dependencies:

   pip install -r backend/requirements.txt

3. Copy env template and fill values:

   copy backend/.env.example backend/.env

4. Run backend:

   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

### 2) Frontend setup

1. Install dependencies:

   cd frontend
   npm install

2. Run frontend:

   npm run dev

The frontend uses Vite proxy to call backend API endpoints.

## GitHub Webhook Configuration

Set webhook URL to:

[http://your-server/webhook/github](http://your-server/webhook/github)

Enable push events. If you configure a secret in GitHub, set the same secret in backend env.

## Endpoints

- POST /webhook/github
- GET /api/projects
- POST /api/sync/{owner}/{repo}
- POST /api/sync/all/{owner}
- GET /health

## Notes

- Firestore requires valid GCP credentials. Set GOOGLE_APPLICATION_CREDENTIALS.
- If Firestore is not configured, project data automatically falls back to local JSON storage at backend/data/projects.json.
- If Gemini key is missing, backend falls back to a deterministic non-AI summary.
- Top projects count is controlled by PORTFOLIO_TOP_K (default 6).
- Full account scan can be triggered via /api/sync/all/{owner}.
- Set FULL_SYNC_ON_WEBHOOK=true to sync all owner repos after each webhook event.
