from datetime import datetime, timezone
from typing import Any

from .ai_engine import AIEngineError, generate_description
from .firestore_repo import trim_to_top_projects, upsert_project
from .github_client import get_repo_context, get_repo_details, list_owner_repos
from .ranking import score_project
from ..schemas import ProjectRecord
from ..settings import settings


def _normalize_repo(repo_data: dict[str, Any], context_text: str) -> dict[str, Any]:
    return {
        "repo_id": repo_data.get("id"),
        "owner": (repo_data.get("owner") or {}).get("login", ""),
        "name": repo_data.get("name", ""),
        "full_name": repo_data.get("full_name", ""),
        "html_url": repo_data.get("html_url", ""),
        "description": repo_data.get("description", ""),
        "language": repo_data.get("language", ""),
        "stargazers_count": repo_data.get("stargazers_count", 0),
        "forks_count": repo_data.get("forks_count", 0),
        "fork": repo_data.get("fork", False),
        "context": context_text,
    }


def _process_repo_data(owner: str, repo_data: dict[str, Any], trim_after: bool = True) -> dict[str, Any]:
    repo = repo_data.get("name", "")
    context_text = get_repo_context(owner, repo, repo_data)
    normalized = _normalize_repo(repo_data, context_text)

    try:
        ai_data = generate_description(repo_data, context_text)
    except AIEngineError:
        ai_data = {
            "short_description": repo_data.get("description") or "No description available.",
            "tech_stack": [repo_data.get("language")] if repo_data.get("language") else [],
            "category": "General",
        }

    merged = {
        **normalized,
        **ai_data,
    }
    score = score_project(merged)

    record = ProjectRecord(
        repo_id=repo_data.get("id"),
        owner=owner,
        name=repo,
        full_name=repo_data.get("full_name", f"{owner}/{repo}"),
        html_url=repo_data.get("html_url", ""),
        short_description=merged["short_description"],
        tech_stack=merged["tech_stack"],
        category=merged["category"],
        score=score,
        stars=repo_data.get("stargazers_count", 0),
        forks=repo_data.get("forks_count", 0),
        language=repo_data.get("language") or "",
        updated_at=datetime.now(timezone.utc).isoformat(),
    )

    upsert_project(record.model_dump())
    removed = trim_to_top_projects(limit=settings.portfolio_top_k) if trim_after else 0

    return {
        "repo": record.full_name,
        "score": score,
        "trimmed": removed,
    }


def process_repo(owner: str, repo: str) -> dict[str, Any]:
    repo_data = get_repo_details(owner, repo)
    return _process_repo_data(owner, repo_data, trim_after=True)


def process_owner_repos(owner: str) -> dict[str, Any]:
    repos = list_owner_repos(owner, max_repos=settings.github_max_repos)
    processed = 0
    skipped = 0
    failures: list[dict[str, str]] = []

    for repo_data in repos:
        if repo_data.get("archived"):
            skipped += 1
            continue

        repo_name = repo_data.get("name", "")
        try:
            _process_repo_data(owner, repo_data, trim_after=False)
            processed += 1
        except Exception as exc:
            failures.append({"repo": repo_name, "error": str(exc)})

    trim_to_top_projects(limit=settings.portfolio_top_k)
    return {
        "owner": owner,
        "processed": processed,
        "skipped": skipped,
        "failed": len(failures),
        "failures": failures[:10],
    }
