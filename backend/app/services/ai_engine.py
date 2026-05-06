import json
from typing import Any

import requests

from ..settings import settings


class AIEngineError(RuntimeError):
    pass


def _fallback_summary(repo_data: dict[str, Any], context_text: str) -> dict[str, Any]:
    language = repo_data.get("language") or "Unknown"
    topics = repo_data.get("topics") or []
    category = "AI" if "ai" in [t.lower() for t in topics] else "Web" if language.lower() in {"javascript", "typescript"} else "App"

    short = repo_data.get("description") or "Repository with active development and documented functionality."

    tech_stack = [language] if language != "Unknown" else []
    lowered = context_text.lower()
    if "fastapi" in lowered:
        tech_stack.append("FastAPI")
    if "react" in lowered:
        tech_stack.append("React")

    deduped = []
    for t in tech_stack:
        if t not in deduped:
            deduped.append(t)

    return {
        "short_description": short[:220],
        "tech_stack": deduped,
        "category": category,
    }


def generate_description(repo_data: dict[str, Any], context_text: str) -> dict[str, Any]:
    if not settings.gemini_api_key:
        return _fallback_summary(repo_data, context_text)

    prompt = {
        "repo": {
            "name": repo_data.get("name"),
            "full_name": repo_data.get("full_name"),
            "description": repo_data.get("description"),
            "language": repo_data.get("language"),
            "topics": repo_data.get("topics", []),
            "stargazers_count": repo_data.get("stargazers_count", 0),
            "fork": repo_data.get("fork", False),
            "size": repo_data.get("size", 0),
        },
        "repository_context_excerpt": context_text[:9000],
        "task": {
            "output_format": "json",
            "keys": ["short_description", "tech_stack", "category"],
            "rules": [
                "short_description must be 1-2 concise lines",
                "tech_stack must be a JSON array of strings",
                "category must be one of AI, Web, App, Data, DevTool, General",
            ],
        },
    }

    instruction = (
        "You analyze repositories and return strict JSON only with keys: "
        "short_description, tech_stack, category. Do not return markdown."
    )

    if settings.gemini_api_url:
        url = settings.gemini_api_url
    else:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent"
        )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": instruction,
                    },
                    {
                        "text": json.dumps(prompt),
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    try:
        res = requests.post(
            url,
            params={"key": settings.gemini_api_key},
            json=payload,
            timeout=45,
        )
        res.raise_for_status()
        result = res.json()
    except Exception as exc:
        raise AIEngineError(f"Gemini request failed: {exc}") from exc

    raw = (
        (((result.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [{}])[0].get("text")
        or ""
    ).strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    if not raw:
        raise AIEngineError("Empty AI response")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIEngineError("Invalid AI JSON response") from exc

    short_description = str(parsed.get("short_description", "")).strip()
    if not short_description:
        short_description = repo_data.get("description") or "No description available."

    tech_stack = parsed.get("tech_stack") or []
    if not isinstance(tech_stack, list):
        tech_stack = []

    cleaned_stack = [str(item).strip() for item in tech_stack if str(item).strip()]

    category = str(parsed.get("category", "General")).strip() or "General"

    return {
        "short_description": short_description[:300],
        "tech_stack": cleaned_stack[:12],
        "category": category,
    }
