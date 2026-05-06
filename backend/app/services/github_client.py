import base64
from typing import Any

import requests

from ..settings import settings

GITHUB_API = "https://api.github.com"
TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".css",
    ".html",
}


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def get_repo_details(owner: str, repo: str) -> dict[str, Any]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    res = requests.get(url, headers=_headers(), timeout=30)
    res.raise_for_status()
    return res.json()


def list_owner_repos(owner: str, max_repos: int | None = None) -> list[dict[str, Any]]:
    limit = max_repos or settings.github_max_repos
    page = 1
    repos: list[dict[str, Any]] = []

    while len(repos) < limit:
        url = f"{GITHUB_API}/users/{owner}/repos"
        params = {
            "per_page": min(100, limit),
            "page": page,
            "sort": "updated",
            "direction": "desc",
        }
        res = requests.get(url, headers=_headers(), params=params, timeout=30)
        res.raise_for_status()
        batch = res.json()
        if not batch:
            break

        repos.extend(batch)
        page += 1

    return repos[:limit]


def get_readme(owner: str, repo: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
    res = requests.get(url, headers=_headers(), timeout=30)

    if res.status_code == 404:
        return ""

    res.raise_for_status()
    data = res.json()

    content = data.get("content", "")
    encoding = data.get("encoding")
    if encoding == "base64" and content:
        try:
            return base64.b64decode(content).decode("utf-8", errors="ignore")
        except Exception:
            return ""

    return ""


def _is_candidate_text_file(path: str) -> bool:
    lowered = path.lower()
    if lowered.startswith(("node_modules/", "dist/", "build/", ".git/", ".next/", "venv/", ".venv/")):
        return False

    for ext in TEXT_EXTENSIONS:
        if lowered.endswith(ext):
            return True
    return False


def _get_repo_tree(owner: str, repo: str, default_branch: str) -> list[dict[str, Any]]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{default_branch}"
    res = requests.get(url, headers=_headers(), params={"recursive": "1"}, timeout=30)
    if res.status_code == 404:
        return []
    res.raise_for_status()
    data = res.json()
    return data.get("tree", [])


def _get_file_content(owner: str, repo: str, path: str, ref: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    res = requests.get(url, headers=_headers(), params={"ref": ref}, timeout=30)
    if res.status_code in {403, 404}:
        return ""
    res.raise_for_status()
    data = res.json()
    content = data.get("content", "")
    if data.get("encoding") != "base64" or not content:
        return ""
    try:
        return base64.b64decode(content).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def get_repo_context(owner: str, repo: str, repo_data: dict[str, Any]) -> str:
    readme = get_readme(owner, repo)
    branch = repo_data.get("default_branch") or "main"
    tree = _get_repo_tree(owner, repo, branch)

    files: list[str] = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        if not path or not _is_candidate_text_file(path):
            continue
        files.append(path)

    sampled_files = files[: settings.github_content_file_limit]
    chunks: list[str] = []

    if readme:
        chunks.append("README:\n" + readme[:4000])

    remaining = max(1000, settings.github_content_max_chars - sum(len(c) for c in chunks))
    for path in sampled_files:
        if remaining <= 0:
            break
        body = _get_file_content(owner, repo, path, branch)
        if not body:
            continue
        snippet = body[: min(1800, remaining)]
        chunks.append(f"FILE {path}:\n{snippet}")
        remaining -= len(snippet)

    return "\n\n".join(chunks)
