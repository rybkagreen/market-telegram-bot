"""
GitHub Integration Service.
Provides methods to interact with GitHub API using PyGithub.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from src.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class GitHubIssuePayload:
    """Payload for creating GitHub issue."""

    title: str
    body: str
    labels: Optional[list[str]] = None
    assignees: Optional[list[str]] = None


@dataclass
class GitHubPRPayload:
    """Payload for creating GitHub pull request."""

    title: str
    body: str
    head: str
    base: str = "main"
    draft: bool = False


class GitHubService:
    """
    GitHub Integration Service.

    Requires PyGithub library: pip install PyGithub
    Configured via: GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME
    """

    def __init__(self) -> None:
        """Initialize GitHub service with token from settings."""
        self.token = settings.github_token
        self.repo_owner = settings.github_repo_owner
        self.repo_name = settings.github_repo_name
        self._client = None

        if not self.token:
            logger.warning("GITHUB_TOKEN not configured")
        if not self.repo_owner or not self.repo_name:
            logger.warning("GITHUB_REPO_OWNER or GITHUB_REPO_NAME not configured")

    @property
    def client(self):
        """Lazy-load GitHub client."""
        if self._client is None and self.token:
            try:
                from github import Github
                self._client = Github(self.token)
            except ImportError:
                logger.error("PyGithub not installed: pip install PyGithub")
                raise
        return self._client

    @property
    def repo(self):
        """Get repository object."""
        if not self.client or not self.repo_owner or not self.repo_name:
            return None
        try:
            return self.client.get_user(self.repo_owner).get_repo(self.repo_name)
        except Exception as e:
            logger.error(f"Failed to get repo {self.repo_owner}/{self.repo_name}: {e}")
            return None

    async def create_issue(self, payload: GitHubIssuePayload) -> Optional[dict]:
        """
        Create GitHub issue.

        Args:
            payload: Issue payload with title, body, labels, assignees

        Returns:
            Issue data dict or None on error
        """
        if not self.repo:
            logger.error("Repository not configured")
            return None

        try:
            issue = self.repo.create_issue(
                title=payload.title,
                body=payload.body,
                labels=payload.labels or [],
                assignees=payload.assignees or [],
            )
            logger.info(f"Created issue #{issue.number}: {payload.title}")
            return {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "body": issue.body,
            }
        except Exception as e:
            logger.error(f"Failed to create issue: {e}")
            return None

    async def create_pull_request(self, payload: GitHubPRPayload) -> Optional[dict]:
        """
        Create GitHub pull request.

        Args:
            payload: PR payload with title, body, head, base branches

        Returns:
            PR data dict or None on error
        """
        if not self.repo:
            logger.error("Repository not configured")
            return None

        try:
            pr = self.repo.create_pull(
                title=payload.title,
                body=payload.body,
                head=payload.head,
                base=payload.base,
                draft=payload.draft,
            )
            logger.info(f"Created PR #{pr.number}: {payload.title}")
            return {
                "number": pr.number,
                "title": pr.title,
                "url": pr.html_url,
                "body": pr.body,
                "draft": pr.draft,
            }
        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            return None

    async def add_issue_comment(self, issue_number: int, comment: str) -> Optional[dict]:
        """
        Add comment to GitHub issue.

        Args:
            issue_number: Issue number
            comment: Comment text

        Returns:
            Comment data dict or None on error
        """
        if not self.repo:
            logger.error("Repository not configured")
            return None

        try:
            issue = self.repo.get_issue(issue_number)
            comment_obj = issue.create_comment(comment)
            logger.info(f"Added comment to issue #{issue_number}")
            return {
                "id": comment_obj.id,
                "body": comment_obj.body,
                "url": comment_obj.html_url,
            }
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            return None

    async def close_issue(self, issue_number: int, comment: Optional[str] = None) -> bool:
        """
        Close GitHub issue.

        Args:
            issue_number: Issue number
            comment: Optional closing comment

        Returns:
            True if successful
        """
        if not self.repo:
            logger.error("Repository not configured")
            return False

        try:
            issue = self.repo.get_issue(issue_number)
            if comment:
                issue.create_comment(comment)
            issue.edit(state="closed")
            logger.info(f"Closed issue #{issue_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to close issue: {e}")
            return False

    async def get_issue(self, issue_number: int) -> Optional[dict]:
        """
        Get GitHub issue details.

        Args:
            issue_number: Issue number

        Returns:
            Issue data dict or None on error
        """
        if not self.repo:
            logger.error("Repository not configured")
            return None

        try:
            issue = self.repo.get_issue(issue_number)
            return {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "url": issue.html_url,
                "labels": [label.name for label in issue.labels],
            }
        except Exception as e:
            logger.error(f"Failed to get issue: {e}")
            return None

    async def list_issues(self, state: str = "open", limit: int = 10) -> list[dict]:
        """
        List GitHub issues.

        Args:
            state: Issue state (open, closed, all)
            limit: Max issues to return

        Returns:
            List of issue dicts
        """
        if not self.repo:
            logger.error("Repository not configured")
            return []

        try:
            issues = self.repo.get_issues(state=state)
            result = []
            for i, issue in enumerate(issues):
                if i >= limit:
                    break
                result.append(
                    {
                        "number": issue.number,
                        "title": issue.title,
                        "state": issue.state,
                        "url": issue.html_url,
                    }
                )
            return result
        except Exception as e:
            logger.error(f"Failed to list issues: {e}")
            return []
