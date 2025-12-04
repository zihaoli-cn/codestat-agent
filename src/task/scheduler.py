"""
Task scheduler for managing code statistics jobs.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from ..webhook.models import PushEvent
from .models import StatTask, TaskStatus, ClocConfig
from .container import ContainerManager


class TaskScheduler:
    """Schedules and manages code statistics tasks."""
    
    def __init__(
        self,
        container_manager: ContainerManager,
        default_cloc_config: Optional[ClocConfig] = None
    ):
        """
        Initialize task scheduler.
        
        Args:
            container_manager: Container manager instance
            default_cloc_config: Default CLOC configuration
        """
        self.container_manager = container_manager
        self.default_cloc_config = default_cloc_config or ClocConfig()
        
        # In-memory task tracking
        self.tasks: Dict[str, StatTask] = {}
        self.repository_configs: Dict[str, ClocConfig] = {}
        
        # Background monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
    
    def set_repository_config(self, repository_id: str, config: ClocConfig):
        """Set CLOC configuration for specific repository."""
        self.repository_configs[repository_id] = config
    
    def get_repository_config(self, repository_id: str) -> ClocConfig:
        """Get CLOC configuration for repository."""
        return self.repository_configs.get(repository_id, self.default_cloc_config)
    
    async def schedule_from_push_event(self, event: PushEvent) -> StatTask:
        """
        Schedule task from push event.
        
        Args:
            event: Push event
            
        Returns:
            Created task
        """
        # Generate task ID
        task_id = f"{event.repository_id}_{event.commit_sha[:7]}_{uuid.uuid4().hex[:8]}"
        
        # Get repository-specific config
        cloc_config = self.get_repository_config(event.repository_id)
        
        # Create task
        task = StatTask(
            task_id=task_id,
            repository_id=event.repository_id,
            repository_name=event.repository_name,
            repository_url=event.repository_url,
            branch=event.branch,
            commit_sha=event.commit_sha,
            cloc_config=cloc_config,
            status=TaskStatus.PENDING,
        )
        
        # Store task
        self.tasks[task_id] = task
        
        # Start task execution
        await self._execute_task(task)
        
        return task
    
    async def _execute_task(self, task: StatTask):
        """Execute task in container."""
        try:
            # Update status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            
            # Start container
            container_id = self.container_manager.start_task(task)
            task.container_id = container_id
            
            print(f"Task {task.task_id} started in container {container_id[:12]}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.finished_at = datetime.utcnow()
            task.error_message = str(e)
            print(f"Task {task.task_id} failed to start: {e}")
    
    async def _monitor_tasks(self):
        """Background task to monitor running tasks."""
        while self._running:
            try:
                await self._check_running_tasks()
            except Exception as e:
                print(f"Error in task monitor: {e}")
            
            await asyncio.sleep(5)  # Check every 5 seconds
    
    async def _check_running_tasks(self):
        """Check status of running tasks."""
        for task in list(self.tasks.values()):
            if task.status != TaskStatus.RUNNING or not task.container_id:
                continue
            
            # Check container status
            status = self.container_manager.get_task_status(task.container_id)
            
            if status == "exited":
                # Task finished, get result
                result = self.container_manager.get_task_result(task.task_id)
                
                if result:
                    task.status = TaskStatus.SUCCESS
                    task.result = result
                else:
                    task.status = TaskStatus.FAILED
                    task.error_message = "No result file generated"
                
                task.finished_at = datetime.utcnow()
                print(f"Task {task.task_id} finished with status {task.status}")
            
            elif status == "not_found":
                task.status = TaskStatus.FAILED
                task.error_message = "Container not found"
                task.finished_at = datetime.utcnow()
            
            # Check timeout
            if task.started_at:
                elapsed = (datetime.utcnow() - task.started_at).total_seconds()
                if elapsed > task.cloc_config.timeout:
                    # Timeout, stop container
                    self.container_manager.stop_container(task.repository_id)
                    task.status = TaskStatus.TIMEOUT
                    task.finished_at = datetime.utcnow()
                    task.error_message = f"Task timeout after {elapsed:.0f}s"
                    print(f"Task {task.task_id} timed out")
    
    def get_task(self, task_id: str) -> Optional[StatTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(
        self,
        repository_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> list[StatTask]:
        """
        List tasks with optional filters.
        
        Args:
            repository_id: Filter by repository
            status: Filter by status
            limit: Maximum number of tasks to return
            
        Returns:
            List of tasks
        """
        tasks = list(self.tasks.values())
        
        # Apply filters
        if repository_id:
            tasks = [t for t in tasks if t.repository_id == repository_id]
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks[:limit]
    
    async def start(self):
        """Start background monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_tasks())
        print("Task scheduler started")
    
    async def stop(self):
        """Stop background monitoring."""
        if not self._running:
            return
        
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        print("Task scheduler stopped")
