"""
Webhook event models and abstractions.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class GitProvider(str, Enum):
    """Supported Git providers."""
    GITEA = "gitea"
    GITHUB = "github"
    GITLAB = "gitlab"


class PushEvent(BaseModel):
    """Unified push event model across different Git providers."""
    
    provider: GitProvider = Field(..., description="Git provider type")
    repository_url: str = Field(..., description="Repository clone URL")
    repository_name: str = Field(..., description="Repository full name (owner/repo)")
    branch: str = Field(..., description="Branch name (without refs/heads/ prefix)")
    commit_sha: str = Field(..., description="Latest commit SHA")
    commit_message: Optional[str] = Field(None, description="Latest commit message")
    pusher: Optional[str] = Field(None, description="Username who pushed")
    timestamp: Optional[str] = Field(None, description="Push timestamp")
    
    @property
    def is_main_branch(self) -> bool:
        """Check if this is a push to main branch."""
        return self.branch in ("main", "master")
    
    @property
    def repository_id(self) -> str:
        """Generate unique repository identifier."""
        return self.repository_name.replace("/", "_").replace(".", "_")


class WebhookConfig(BaseModel):
    """Webhook configuration for a repository."""
    
    provider: GitProvider
    secret: Optional[str] = Field(None, description="Webhook secret for signature verification")
    enabled: bool = Field(True, description="Whether webhook is enabled")
