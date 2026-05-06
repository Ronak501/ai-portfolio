from typing import Any


def score_project(repo: dict[str, Any]) -> int:
    score = 0

    stars = repo.get("stargazers_count", 0)
    forks_count = repo.get("forks_count", 0)
    has_language = bool(repo.get("language"))
    has_description = bool(repo.get("description"))
    is_fork = bool(repo.get("fork"))
    has_readme = bool(repo.get("readme"))

    if stars > 5:
        score += 3
    if stars > 20:
        score += 2
    if forks_count > 2:
        score += 1
    if has_language:
        score += 2
    if has_description:
        score += 2
    if has_readme:
        score += 2
    if not is_fork:
        score += 3

    return score
