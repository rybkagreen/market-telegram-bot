# GitHub Integration Setup — Discovery Report

**Date:** 2026-04-19  
**Status:** Complete

## Summary

Added GitHub integration infrastructure to enable async GitHub operations (issue creation, PR management, comments) via Celery background tasks.

## Files Modified

### Configuration
- **`.env`** — Added `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`
- **`src/config/settings.py`** — Added `github_token`, `github_repo_owner`, `github_repo_name` fields

### Services
- **`src/core/services/github_service.py`** — NEW
  - `GitHubService` class with async methods for API operations
  - `GitHubIssuePayload`, `GitHubPRPayload` dataclasses
  - Methods: `create_issue`, `create_pull_request`, `add_issue_comment`, `close_issue`, `get_issue`, `list_issues`
  - Lazy-loads `github.Github` client on first use (PyGithub dependency)

### Tasks
- **`src/tasks/github_tasks.py`** — NEW
  - Celery tasks for async GitHub operations: `github:create_issue`, `github:create_pr`, `github:add_comment`, `github:close_issue`
  - Tasks execute in `QUEUE_BACKGROUND`, processed by `worker_background`
  - Async wrappers around `GitHubService` methods using asyncio

### Celery Configuration
- **`src/tasks/celery_app.py`** — Modified
  - Added `src.tasks.github_tasks` to `include` list (line 51)
  - Added `"github:*"` → `QUEUE_BACKGROUND` routing (line 82)

## API/Contract Changes

### New Settings Fields
- `github_token: str | None` — GitHub personal access token (read from `GITHUB_TOKEN`)
- `github_repo_owner: str` — Repository owner/org (read from `GITHUB_REPO_OWNER`)
- `github_repo_name: str` — Repository name (read from `GITHUB_REPO_NAME`)

### New Celery Task Queue
- Prefix: `github:*`
- Queue: `background` (worker_background, concurrency 4)
- Time limit: 5 min soft, 10 min hard (inherited from celery_app defaults)

### New Service Public API
```python
# GitHubService methods (all async)
async def create_issue(payload: GitHubIssuePayload) -> Optional[dict]
async def create_pull_request(payload: GitHubPRPayload) -> Optional[dict]
async def add_issue_comment(issue_number: int, comment: str) -> Optional[dict]
async def close_issue(issue_number: int, comment: Optional[str] = None) -> bool
async def get_issue(issue_number: int) -> Optional[dict]
async def list_issues(state: str = "open", limit: int = 10) -> list[dict]
```

## Dependencies

- **PyGithub** — Required for GitHub API integration (not yet in `pyproject.toml`)
  - Install: `pip install PyGithub`
  - Lazy-loaded in `GitHubService._client` to avoid hard dependency

## Usage Examples

### From Python Service
```python
from src.core.services.github_service import GitHubService, GitHubIssuePayload

service = GitHubService()
result = await service.create_issue(
    GitHubIssuePayload(
        title="Bug: Something broken",
        body="Description...",
        labels=["bug", "urgent"]
    )
)
```

### From Celery Task
```python
from src.tasks.github_tasks import create_github_issue

# Async dispatch
create_github_issue.delay(
    title="Issue title",
    body="Issue body",
    labels=["bug"]
)
```

## Environment Configuration

Add to `.env`:
```
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REPO_OWNER=your-org-or-user
GITHUB_REPO_NAME=your-repo-name
```

**Note:** Token has limited expiration for security. After setup is verified, rotate the token in GitHub settings.

## Testing & Verification

1. **Settings load:** `from src.config.settings import settings; print(settings.github_token)`
2. **Service init:** `from src.core.services.github_service import GitHubService; s = GitHubService()`
3. **Task discovery:** `celery -A src.tasks.celery_app inspect active_queues | grep background`
4. **Manual test:** `create_github_issue.delay(title="Test", body="Test body")`

## Next Steps

1. **Add PyGithub to dependencies:** `poetry add PyGithub`
2. **Create integration tests** for GitHub service (mock PyGithub)
3. **Deploy & test** with real GitHub repo
4. **Rotate token** after deployment verification

## Notes

- All methods are async-safe; internal asyncio.run() wraps sync PyGithub calls
- Service returns `None` on errors, never raises (safe for task execution)
- Logging: all operations logged at `src.core.services.github_service` level
- Queue: `background` chosen to avoid blocking critical tasks
- Token expires per GitHub policy; plan for rotation strategy

---

🔍 Verified against: `HEAD` (before commit) | 📅 Updated: 2026-04-19T00:00:00Z
