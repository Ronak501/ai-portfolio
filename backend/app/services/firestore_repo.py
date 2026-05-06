from typing import Any
from pathlib import Path
import json

from google.cloud import firestore
from google.auth.exceptions import DefaultCredentialsError

from ..settings import settings

_LOCAL_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "projects.json"


def _ensure_local_db() -> None:
    _LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _LOCAL_DB_PATH.exists():
        _LOCAL_DB_PATH.write_text("[]", encoding="utf-8")


def _local_read_all() -> list[dict[str, Any]]:
    _ensure_local_db()
    raw = _LOCAL_DB_PATH.read_text(encoding="utf-8").strip() or "[]"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = []
    return data if isinstance(data, list) else []


def _local_write_all(items: list[dict[str, Any]]) -> None:
    _ensure_local_db()
    _LOCAL_DB_PATH.write_text(json.dumps(items, ensure_ascii=True, indent=2), encoding="utf-8")


def _local_upsert(project: dict[str, Any]) -> None:
    items = _local_read_all()
    repo_id = project.get("repo_id")
    replaced = False
    for idx, item in enumerate(items):
        if item.get("repo_id") == repo_id:
            items[idx] = {**item, **project}
            replaced = True
            break
    if not replaced:
        items.append(project)
    _local_write_all(items)


def _sorted_projects(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda x: (x.get("score", 0), x.get("updated_at", "")),
        reverse=True,
    )


def _get_client() -> firestore.Client:
    if settings.firebase_project_id:
        return firestore.Client(project=settings.firebase_project_id)
    return firestore.Client()


def _can_use_firestore() -> bool:
    backend = settings.storage_backend.lower().strip()
    if backend == "local":
        return False
    if backend == "firestore":
        return True
    # auto mode: best effort Firestore, fallback to local JSON.
    return True


def upsert_project(project: dict[str, Any]) -> None:
    if not _can_use_firestore():
        _local_upsert(project)
        return

    try:
        client = _get_client()
        doc_id = str(project["repo_id"])
        client.collection("projects").document(doc_id).set(project, merge=True)
    except (DefaultCredentialsError, Exception):
        _local_upsert(project)


def list_top_projects(limit: int = 6) -> list[dict[str, Any]]:
    if not _can_use_firestore():
        return _sorted_projects(_local_read_all())[:limit]

    try:
        client = _get_client()
        query = (
            client.collection("projects")
            .order_by("score", direction=firestore.Query.DESCENDING)
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        docs = query.stream()
        return [{**d.to_dict(), "id": d.id} for d in docs]
    except (DefaultCredentialsError, Exception):
        return _sorted_projects(_local_read_all())[:limit]


def trim_to_top_projects(limit: int = 6) -> int:
    if not _can_use_firestore():
        items = _sorted_projects(_local_read_all())
        removed = max(0, len(items) - limit)
        _local_write_all(items[:limit])
        return removed

    try:
        client = _get_client()
        docs = list(
            client.collection("projects")
            .order_by("score", direction=firestore.Query.DESCENDING)
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .stream()
        )

        removed = 0
        for doc in docs[limit:]:
            doc.reference.delete()
            removed += 1
        return removed
    except (DefaultCredentialsError, Exception):
        items = _sorted_projects(_local_read_all())
        removed = max(0, len(items) - limit)
        _local_write_all(items[:limit])
        return removed
