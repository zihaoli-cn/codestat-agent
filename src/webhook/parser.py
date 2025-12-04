"""
Webhook payload parsers for different Git providers.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import hmac
import hashlib

from .models import PushEvent, GitProvider


class WebhookParser(ABC):
    """Abstract base class for webhook parsers."""
    
    @abstractmethod
    def parse(self, payload: Dict[str, Any]) -> Optional[PushEvent]:
        """Parse webhook payload into unified PushEvent."""
        pass
    
    @abstractmethod
    def verify_signature(self, payload_body: bytes, signature: str, secret: str) -> bool:
        """Verify webhook signature."""
        pass


class GiteaWebhookParser(WebhookParser):
    """Parser for Gitea webhooks."""
    
    def parse(self, payload: Dict[str, Any]) -> Optional[PushEvent]:
        """Parse Gitea webhook payload."""
        try:
            # Check if this is a push event
            if not payload.get("ref", "").startswith("refs/heads/"):
                return None
            
            repository = payload.get("repository", {})
            branch = payload["ref"].replace("refs/heads/", "")
            commits = payload.get("commits", [])
            latest_commit = commits[-1] if commits else {}
            
            return PushEvent(
                provider=GitProvider.GITEA,
                repository_url=repository.get("clone_url", ""),
                repository_name=repository.get("full_name", ""),
                branch=branch,
                commit_sha=payload.get("after", ""),
                commit_message=latest_commit.get("message"),
                pusher=payload.get("pusher", {}).get("username"),
                timestamp=latest_commit.get("timestamp")
            )
        except (KeyError, IndexError) as e:
            return None
    
    def verify_signature(self, payload_body: bytes, signature: str, secret: str) -> bool:
        """Verify Gitea webhook signature."""
        if not secret or not signature:
            return True  # No verification if secret not configured
        
        expected_signature = hmac.new(
            secret.encode(),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)


class GitHubWebhookParser(WebhookParser):
    """Parser for GitHub webhooks."""
    
    def parse(self, payload: Dict[str, Any]) -> Optional[PushEvent]:
        """Parse GitHub webhook payload."""
        try:
            # Check if this is a push event
            if not payload.get("ref", "").startswith("refs/heads/"):
                return None
            
            repository = payload.get("repository", {})
            branch = payload["ref"].replace("refs/heads/", "")
            
            return PushEvent(
                provider=GitProvider.GITHUB,
                repository_url=repository.get("clone_url", ""),
                repository_name=repository.get("full_name", ""),
                branch=branch,
                commit_sha=payload.get("after", ""),
                commit_message=payload.get("head_commit", {}).get("message"),
                pusher=payload.get("pusher", {}).get("name"),
                timestamp=payload.get("head_commit", {}).get("timestamp")
            )
        except KeyError:
            return None
    
    def verify_signature(self, payload_body: bytes, signature: str, secret: str) -> bool:
        """Verify GitHub webhook signature (X-Hub-Signature-256)."""
        if not secret or not signature:
            return True
        
        expected_signature = "sha256=" + hmac.new(
            secret.encode(),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)


class GitLabWebhookParser(WebhookParser):
    """Parser for GitLab webhooks."""
    
    def parse(self, payload: Dict[str, Any]) -> Optional[PushEvent]:
        """Parse GitLab webhook payload."""
        try:
            # Check if this is a push event
            if not payload.get("ref", "").startswith("refs/heads/"):
                return None
            
            project = payload.get("project", {})
            branch = payload["ref"].replace("refs/heads/", "")
            commits = payload.get("commits", [])
            latest_commit = commits[-1] if commits else {}
            
            return PushEvent(
                provider=GitProvider.GITLAB,
                repository_url=project.get("git_http_url", ""),
                repository_name=project.get("path_with_namespace", ""),
                branch=branch,
                commit_sha=payload.get("after", ""),
                commit_message=latest_commit.get("message"),
                pusher=payload.get("user_name"),
                timestamp=latest_commit.get("timestamp")
            )
        except (KeyError, IndexError):
            return None
    
    def verify_signature(self, payload_body: bytes, signature: str, secret: str) -> bool:
        """Verify GitLab webhook signature (X-Gitlab-Token)."""
        if not secret or not signature:
            return True
        
        return hmac.compare_digest(signature, secret)


class WebhookParserFactory:
    """Factory for creating webhook parsers."""
    
    _parsers = {
        GitProvider.GITEA: GiteaWebhookParser,
        GitProvider.GITHUB: GitHubWebhookParser,
        GitProvider.GITLAB: GitLabWebhookParser,
    }
    
    @classmethod
    def create(cls, provider: GitProvider) -> WebhookParser:
        """Create parser for given provider."""
        parser_class = cls._parsers.get(provider)
        if not parser_class:
            raise ValueError(f"Unsupported provider: {provider}")
        return parser_class()
