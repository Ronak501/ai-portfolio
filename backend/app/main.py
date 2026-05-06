import json
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .settings import settings
from .services.processor import process_owner_repos, process_repo
from .services.firestore_repo import list_top_projects
from .services.webhook_security import verify_github_signature

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Portfolio Auto-Updater", version="1.0.0")

origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/webhook/github")
async def github_webhook(request: Request):
    body = await request.body()

    if settings.github_webhook_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not verify_github_signature(body, signature, settings.github_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    event = request.headers.get("X-GitHub-Event", "")
    if event not in {"push", "repository"}:
        return JSONResponse({"status": "ignored", "reason": f"unsupported event {event}"})

    repo_info = data.get("repository") or {}
    owner_obj = repo_info.get("owner") or {}
    repo = repo_info.get("name")
    owner = owner_obj.get("login")

    if not owner or not repo:
        raise HTTPException(status_code=400, detail="Missing repository owner/name")

    logger.info("Received webhook for %s/%s", owner, repo)

    if settings.full_sync_on_webhook:
        result = process_owner_repos(owner)
    else:
        result = process_repo(owner, repo)
    return {"status": "processed", "result": result}


@app.post("/api/sync/{owner}/{repo}")
def sync_repo(owner: str, repo: str):
    result = process_repo(owner, repo)
    return {"status": "processed", "result": result}


@app.post("/api/sync/all/{owner}")
def sync_all_repos(owner: str):
    result = process_owner_repos(owner)
    return {"status": "processed", "result": result}


@app.get("/api/projects")
def get_projects(limit: int | None = None):
    top_k = limit or settings.portfolio_top_k
    projects = list_top_projects(limit=top_k)
    return {"projects": projects, "count": len(projects)}
