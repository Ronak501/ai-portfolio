from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, Field


class ProjectRecord(BaseModel):
    repo_id: int
    owner: str
    name: str
    full_name: str
    html_url: str
    short_description: str
    tech_stack: List[str] = Field(default_factory=list)
    category: str = "General"
    score: int
    stars: int = 0
    forks: int = 0
    language: str = ""
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
