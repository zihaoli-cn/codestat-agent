"""
Docker container manager for code statistics tasks.
"""
import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
import docker
from docker.models.containers import Container
from docker.errors import DockerException, NotFound, APIError

from .models import StatTask, ClocConfig


class ContainerManager:
    """Manages Docker containers for code statistics execution."""
    
    WORKER_IMAGE = "codestat-worker:latest"
    NETWORK_NAME = "codestat-network"
    
    def __init__(self, data_dir: str = "./data"):
        """
        Initialize container manager.
        
        Args:
            data_dir: Directory for persistent data storage
        """
        try:
            self.client = docker.from_env()
        except DockerException as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")
        
        self.data_dir = Path(data_dir).resolve()
        self.repos_dir = self.data_dir / "repos"
        self.results_dir = self.data_dir / "results"
        
        # Ensure directories exist
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure network exists
        self._ensure_network()
    
    def _ensure_network(self):
        """Ensure Docker network exists."""
        try:
            self.client.networks.get(self.NETWORK_NAME)
        except NotFound:
            self.client.networks.create(self.NETWORK_NAME, driver="bridge")
    
    def _get_container_name(self, repository_id: str) -> str:
        """Generate container name for repository."""
        return f"codestat-{repository_id}"
    
    def _get_repo_path(self, repository_id: str) -> Path:
        """Get local path for repository storage."""
        return self.repos_dir / repository_id
    
    def _get_result_path(self, task_id: str) -> Path:
        """Get path for task result file."""
        return self.results_dir / f"{task_id}.json"
    
    def get_container(self, repository_id: str) -> Optional[Container]:
        """Get existing container for repository."""
        container_name = self._get_container_name(repository_id)
        try:
            return self.client.containers.get(container_name)
        except NotFound:
            return None
    
    def create_or_get_container(self, task: StatTask) -> Container:
        """
        Create new container or get existing one for repository.
        
        Args:
            task: Statistics task
            
        Returns:
            Docker container
        """
        container_name = self._get_container_name(task.repository_id)
        repo_path = self._get_repo_path(task.repository_id)
        result_path = self._get_result_path(task.task_id)
        
        # Check if container already exists
        existing = self.get_container(task.repository_id)
        if existing:
            return existing
        
        # Ensure repo directory exists
        repo_path.mkdir(parents=True, exist_ok=True)
        
        # Prepare environment variables
        env = {
            "REPO_URL": task.repository_url,
            "REPO_NAME": task.repository_name,
            "BRANCH": task.branch,
            "COMMIT_SHA": task.commit_sha,
            "TASK_ID": task.task_id,
            "CLOC_ARGS": " ".join(task.cloc_config.to_cloc_args()),
            "USE_GITIGNORE": "1" if task.cloc_config.use_gitignore else "0",
        }
        
        # Create container
        try:
            container = self.client.containers.create(
                image=self.WORKER_IMAGE,
                name=container_name,
                environment=env,
                volumes={
                    str(repo_path): {"bind": "/workspace/repo", "mode": "rw"},
                    str(result_path.parent): {"bind": "/workspace/results", "mode": "rw"},
                },
                network=self.NETWORK_NAME,
                detach=True,
                auto_remove=False,  # Keep container for inspection
                mem_limit="512m",  # Limit memory
                cpu_quota=50000,  # Limit CPU (50% of one core)
            )
            return container
        except APIError as e:
            raise RuntimeError(f"Failed to create container: {e}")
    
    def start_task(self, task: StatTask) -> str:
        """
        Start statistics task in container.
        
        Args:
            task: Statistics task
            
        Returns:
            Container ID
        """
        container = self.create_or_get_container(task)
        
        # Start container if not running
        if container.status != "running":
            try:
                container.start()
            except APIError as e:
                raise RuntimeError(f"Failed to start container: {e}")
        
        return container.id
    
    def get_task_status(self, container_id: str) -> str:
        """
        Get task status from container.
        
        Args:
            container_id: Container ID
            
        Returns:
            Status string (running, exited, etc.)
        """
        try:
            container = self.client.containers.get(container_id)
            return container.status
        except NotFound:
            return "not_found"
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task result from output file.
        
        Args:
            task_id: Task ID
            
        Returns:
            Result dict or None if not available
        """
        result_path = self._get_result_path(task_id)
        
        if not result_path.exists():
            return None
        
        try:
            with open(result_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def stop_container(self, repository_id: str, timeout: int = 10):
        """
        Stop container for repository.
        
        Args:
            repository_id: Repository identifier
            timeout: Timeout in seconds
        """
        container = self.get_container(repository_id)
        if container and container.status == "running":
            try:
                container.stop(timeout=timeout)
            except APIError:
                pass
    
    def remove_container(self, repository_id: str, force: bool = False):
        """
        Remove container for repository.
        
        Args:
            repository_id: Repository identifier
            force: Force removal even if running
        """
        container = self.get_container(repository_id)
        if container:
            try:
                container.remove(force=force)
            except APIError:
                pass
    
    def list_containers(self) -> list[Dict[str, Any]]:
        """
        List all codestat containers.
        
        Returns:
            List of container info dicts
        """
        containers = self.client.containers.list(
            all=True,
            filters={"name": "codestat-"}
        )
        
        return [
            {
                "id": c.id[:12],
                "name": c.name,
                "status": c.status,
                "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
            }
            for c in containers
        ]
    
    def cleanup_stopped_containers(self):
        """Remove all stopped containers."""
        containers = self.client.containers.list(
            all=True,
            filters={"name": "codestat-", "status": "exited"}
        )
        
        for container in containers:
            try:
                container.remove()
            except APIError:
                pass
