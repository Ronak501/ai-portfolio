import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    gemini_api_url: str = os.getenv("GEMINI_API_URL", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_webhook_secret: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    firebase_project_id: str = os.getenv("FIREBASE_PROJECT_ID", "")
    portfolio_top_k: int = int(os.getenv("PORTFOLIO_TOP_K", "6"))
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
    github_max_repos: int = int(os.getenv("GITHUB_MAX_REPOS", "30"))
    github_content_file_limit: int = int(os.getenv("GITHUB_CONTENT_FILE_LIMIT", "8"))
    github_content_max_chars: int = int(os.getenv("GITHUB_CONTENT_MAX_CHARS", "12000"))
    full_sync_on_webhook: bool = os.getenv("FULL_SYNC_ON_WEBHOOK", "false").lower() == "true"
    storage_backend: str = os.getenv("STORAGE_BACKEND", "auto")


settings = Settings()
