"""
Web API routes.
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from ..webhook.models import GitProvider, PushEvent
from ..task.models import TaskStatus, ClocConfig
from ..storage.database import DatabaseManager


class RepositoryConfigRequest(BaseModel):
    """Request model for repository configuration."""
    repository_name: str
    repository_url: str
    cloc_config: Optional[ClocConfig] = None
    webhook_secret: Optional[str] = None


class RepositoryResponse(BaseModel):
    """Response model for repository."""
    repository_id: str
    repository_name: str
    repository_url: str
    cloc_config: Optional[dict] = None
    enabled: bool
    created_at: str
    
    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    """Response model for task."""
    task_id: str
    repository_id: str
    repository_name: str
    branch: str
    commit_sha: str
    status: str
    result: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class ContainerInfo(BaseModel):
    """Container information."""
    id: str
    name: str
    status: str
    image: str


def create_api_router(db: DatabaseManager, container_manager) -> APIRouter:
    """Create API router with dependencies."""
    
    router = APIRouter(prefix="/api")
    
    # Repository endpoints
    
    @router.get("/repositories", response_model=List[RepositoryResponse])
    async def list_repositories():
        """List all repositories."""
        repos = await db.list_repositories()
        return [
            RepositoryResponse(
                repository_id=r.repository_id,
                repository_name=r.repository_name,
                repository_url=r.repository_url,
                cloc_config=r.cloc_config,
                enabled=r.enabled,
                created_at=r.created_at.isoformat(),
            )
            for r in repos
        ]
    
    @router.get("/repositories/{repository_id}", response_model=RepositoryResponse)
    async def get_repository(repository_id: str):
        """Get repository by ID."""
        repo = await db.get_repository(repository_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        return RepositoryResponse(
            repository_id=repo.repository_id,
            repository_name=repo.repository_name,
            repository_url=repo.repository_url,
            cloc_config=repo.cloc_config,
            enabled=repo.enabled,
            created_at=repo.created_at.isoformat(),
        )
    
    @router.post("/repositories/{repository_id}", response_model=RepositoryResponse)
    async def create_or_update_repository(
        repository_id: str,
        config: RepositoryConfigRequest
    ):
        """Create or update repository configuration."""
        repo = await db.create_or_update_repository(
            repository_id=repository_id,
            repository_name=config.repository_name,
            repository_url=config.repository_url,
            cloc_config=config.cloc_config,
            webhook_secret=config.webhook_secret,
        )
        
        return RepositoryResponse(
            repository_id=repo.repository_id,
            repository_name=repo.repository_name,
            repository_url=repo.repository_url,
            cloc_config=repo.cloc_config,
            enabled=repo.enabled,
            created_at=repo.created_at.isoformat(),
        )
    
    @router.delete("/repositories/{repository_id}")
    async def delete_repository(repository_id: str):
        """Delete repository configuration."""
        success = await db.delete_repository(repository_id)
        if not success:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        return {"status": "deleted"}
    
    # Task endpoints
    
    @router.get("/tasks", response_model=List[TaskResponse])
    async def list_tasks(
        repository_id: Optional[str] = Query(None),
        status: Optional[TaskStatus] = Query(None),
        limit: int = Query(100, le=500)
    ):
        """List tasks with optional filters."""
        tasks = await db.list_tasks(
            repository_id=repository_id,
            status=status,
            limit=limit
        )
        
        return [
            TaskResponse(
                task_id=t.task_id,
                repository_id=t.repository_id,
                repository_name=t.repository_name,
                branch=t.branch,
                commit_sha=t.commit_sha,
                status=t.status,
                result=t.result,
                error_message=t.error_message,
                created_at=t.created_at.isoformat(),
                started_at=t.started_at.isoformat() if t.started_at else None,
                finished_at=t.finished_at.isoformat() if t.finished_at else None,
            )
            for t in tasks
        ]
    
    @router.get("/tasks/{task_id}", response_model=TaskResponse)
    async def get_task(task_id: str):
        """Get task by ID."""
        task = await db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskResponse(
            task_id=task.task_id,
            repository_id=task.repository_id,
            repository_name=task.repository_name,
            branch=task.branch,
            commit_sha=task.commit_sha,
            status=task.status,
            result=task.result,
            error_message=task.error_message,
            created_at=task.created_at.isoformat(),
            started_at=task.started_at.isoformat() if task.started_at else None,
            finished_at=task.finished_at.isoformat() if task.finished_at else None,
        )
    
    # Container endpoints
    
    @router.get("/containers", response_model=List[ContainerInfo])
    async def list_containers():
        """List all containers."""
        containers = container_manager.list_containers()
        return [
            ContainerInfo(
                id=c["id"],
                name=c["name"],
                status=c["status"],
                image=c["image"],
            )
            for c in containers
        ]
    
    @router.post("/containers/{repository_id}/stop")
    async def stop_container(repository_id: str):
        """Stop container for repository."""
        container_manager.stop_container(repository_id)
        return {"status": "stopped"}
    
    @router.delete("/containers/{repository_id}")
    async def remove_container(repository_id: str):
        """Remove container for repository."""
        container_manager.remove_container(repository_id, force=True)
        return {"status": "removed"}
    
    @router.post("/containers/cleanup")
    async def cleanup_containers():
        """Cleanup stopped containers."""
        container_manager.cleanup_stopped_containers()
        return {"status": "cleaned"}
    
    return router
