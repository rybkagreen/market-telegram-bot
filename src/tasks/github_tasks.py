"""
Celery tasks for GitHub integration.
Queue: background | Worker: worker_background
"""

import logging

from src.core.services.github_service import GitHubIssuePayload, GitHubPRPayload, GitHubService
from src.tasks.celery_app import celery_app, QUEUE_BACKGROUND

logger = logging.getLogger(__name__)


@celery_app.task(name="github:create_issue", queue=QUEUE_BACKGROUND, bind=True)
def create_github_issue(self, title: str, body: str, labels: list[str] | None = None) -> dict:
    """
    Async task to create GitHub issue.

    Args:
        title: Issue title
        body: Issue body/description
        labels: Optional list of labels

    Returns:
        Issue data dict
    """
    service = GitHubService()
    payload = GitHubIssuePayload(title=title, body=body, labels=labels)

    import asyncio
    result = asyncio.run(service.create_issue(payload))
    return result or {}


@celery_app.task(name="github:create_pr", queue=QUEUE_BACKGROUND, bind=True)
def create_github_pr(
    self, title: str, body: str, head: str, base: str = "main", draft: bool = False
) -> dict:
    """
    Async task to create GitHub pull request.

    Args:
        title: PR title
        body: PR body/description
        head: Head branch
        base: Base branch (default: main)
        draft: Whether PR is draft

    Returns:
        PR data dict
    """
    service = GitHubService()
    payload = GitHubPRPayload(title=title, body=body, head=head, base=base, draft=draft)

    import asyncio
    result = asyncio.run(service.create_pull_request(payload))
    return result or {}


@celery_app.task(name="github:add_comment", queue=QUEUE_BACKGROUND, bind=True)
def add_github_comment(self, issue_number: int, comment: str) -> dict:
    """
    Async task to add comment to GitHub issue.

    Args:
        issue_number: Issue number
        comment: Comment text

    Returns:
        Comment data dict
    """
    service = GitHubService()

    import asyncio
    result = asyncio.run(service.add_issue_comment(issue_number, comment))
    return result or {}


@celery_app.task(name="github:close_issue", queue=QUEUE_BACKGROUND, bind=True)
def close_github_issue(self, issue_number: int, comment: str | None = None) -> bool:
    """
    Async task to close GitHub issue.

    Args:
        issue_number: Issue number
        comment: Optional closing comment

    Returns:
        True if successful
    """
    service = GitHubService()

    import asyncio
    return asyncio.run(service.close_issue(issue_number, comment))
