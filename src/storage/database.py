"""
Database manager for persistent storage.
"""
from typing import Optional, List
from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from .models import Base, Repository, Task
from ..task.models import StatTask, TaskStatus, ClocConfig


class DatabaseManager:
    """Manages database operations."""
    
    def __init__(self, database_url: str = "sqlite+aiosqlite:///./data/codestat.db"):
        """
        Initialize database manager.
        
        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init_db(self):
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self):
        """Close database connections."""
        await self.engine.dispose()
    
    # Repository operations
    
    async def get_repository(self, repository_id: str) -> Optional[Repository]:
        """Get repository by ID."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Repository).where(Repository.repository_id == repository_id)
            )
            return result.scalar_one_or_none()
    
    async def create_or_update_repository(
        self,
        repository_id: str,
        repository_name: str,
        repository_url: str,
        cloc_config: Optional[ClocConfig] = None,
        webhook_secret: Optional[str] = None,
    ) -> Repository:
        """Create or update repository configuration."""
        async with self.session_factory() as session:
            # Check if exists
            result = await session.execute(
                select(Repository).where(Repository.repository_id == repository_id)
            )
            repo = result.scalar_one_or_none()
            
            if repo:
                # Update existing
                repo.repository_name = repository_name
                repo.repository_url = repository_url
                if cloc_config:
                    repo.cloc_config = cloc_config.model_dump()
                if webhook_secret is not None:
                    repo.webhook_secret = webhook_secret
            else:
                # Create new
                repo = Repository(
                    repository_id=repository_id,
                    repository_name=repository_name,
                    repository_url=repository_url,
                    cloc_config=cloc_config.model_dump() if cloc_config else None,
                    webhook_secret=webhook_secret,
                )
                session.add(repo)
            
            await session.commit()
            await session.refresh(repo)
            return repo
    
    async def list_repositories(self, enabled_only: bool = False) -> List[Repository]:
        """List all repositories."""
        async with self.session_factory() as session:
            query = select(Repository)
            if enabled_only:
                query = query.where(Repository.enabled == True)
            
            result = await session.execute(query.order_by(Repository.created_at.desc()))
            return list(result.scalars().all())
    
    async def delete_repository(self, repository_id: str) -> bool:
        """Delete repository configuration."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Repository).where(Repository.repository_id == repository_id)
            )
            repo = result.scalar_one_or_none()
            
            if repo:
                await session.delete(repo)
                await session.commit()
                return True
            return False
    
    # Task operations
    
    async def save_task(self, task: StatTask) -> Task:
        """Save task to database."""
        async with self.session_factory() as session:
            # Check if exists
            result = await session.execute(
                select(Task).where(Task.task_id == task.task_id)
            )
            db_task = result.scalar_one_or_none()
            
            if db_task:
                # Update existing
                db_task.status = task.status.value
                db_task.container_id = task.container_id
                db_task.result = task.result
                db_task.error_message = task.error_message
                db_task.started_at = task.started_at
                db_task.finished_at = task.finished_at
            else:
                # Create new
                db_task = Task(
                    task_id=task.task_id,
                    repository_id=task.repository_id,
                    repository_name=task.repository_name,
                    repository_url=task.repository_url,
                    branch=task.branch,
                    commit_sha=task.commit_sha,
                    status=task.status.value,
                    container_id=task.container_id,
                    result=task.result,
                    error_message=task.error_message,
                    started_at=task.started_at,
                    finished_at=task.finished_at,
                )
                session.add(db_task)
            
            await session.commit()
            await session.refresh(db_task)
            return db_task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Task).where(Task.task_id == task_id)
            )
            return result.scalar_one_or_none()
    
    async def list_tasks(
        self,
        repository_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
    ) -> List[Task]:
        """List tasks with optional filters."""
        async with self.session_factory() as session:
            query = select(Task)
            
            if repository_id:
                query = query.where(Task.repository_id == repository_id)
            
            if status:
                query = query.where(Task.status == status.value)
            
            query = query.order_by(desc(Task.created_at)).limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_latest_task_for_repository(
        self, repository_id: str
    ) -> Optional[Task]:
        """Get latest task for repository."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Task)
                .where(Task.repository_id == repository_id)
                .order_by(desc(Task.created_at))
                .limit(1)
            )
            return result.scalar_one_or_none()
