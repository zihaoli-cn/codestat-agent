"""
Task models for code statistics jobs.
"""
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ClocConfig(BaseModel):
    """Configuration for CLOC execution."""
    
    exclude_ext: list[str] = Field(default_factory=list, description="File extensions to exclude")
    exclude_lang: list[str] = Field(default_factory=list, description="Languages to exclude")
    include_ext: list[str] = Field(default_factory=list, description="File extensions to include")
    output_format: str = Field("json", description="Output format (json, csv, yaml)")
    use_gitignore: bool = Field(True, description="Use .gitignore for exclusions")
    timeout: int = Field(600, description="Task timeout in seconds")
    
    def to_cloc_args(self) -> list[str]:
        """Convert config to CLOC command line arguments."""
        args = []
        
        if self.exclude_ext:
            args.extend(["--exclude-ext", ",".join(self.exclude_ext)])
        
        if self.exclude_lang:
            args.extend(["--exclude-lang", ",".join(self.exclude_lang)])
        
        if self.include_ext:
            args.extend(["--include-ext", ",".join(self.include_ext)])
        
        # Output format
        if self.output_format == "json":
            args.append("--json")
        elif self.output_format == "csv":
            args.append("--csv")
        elif self.output_format == "yaml":
            args.append("--yaml")
        
        return args


class StatTask(BaseModel):
    """Code statistics task."""
    
    task_id: str = Field(..., description="Unique task identifier")
    repository_id: str = Field(..., description="Repository identifier")
    repository_name: str = Field(..., description="Repository full name")
    repository_url: str = Field(..., description="Repository clone URL")
    branch: str = Field(..., description="Branch name")
    commit_sha: str = Field(..., description="Commit SHA")
    
    status: TaskStatus = Field(TaskStatus.PENDING, description="Task status")
    container_id: Optional[str] = Field(None, description="Docker container ID")
    
    cloc_config: ClocConfig = Field(default_factory=ClocConfig, description="CLOC configuration")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
