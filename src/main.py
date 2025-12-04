"""
CodeStat Agent - Main application entry point.
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .webhook import WebhookHandler, GitProvider
from .task import ContainerManager, TaskScheduler, ClocConfig
from .task.models import TaskStatus
from .storage import DatabaseManager
from .web import create_api_router
from .config import settings
from .logger import logger


# Global instances
db: DatabaseManager = None
container_manager: ContainerManager = None
scheduler: TaskScheduler = None
webhook_handler: WebhookHandler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global db, container_manager, scheduler, webhook_handler
    
    # Initialize database
    db = DatabaseManager(database_url=settings.database_url)
    await db.init_db()
    logger.info("Database initialized")
    
    # Initialize container manager
    container_manager = ContainerManager(data_dir=settings.data_dir)
    logger.info("Container manager initialized")
    
    # Initialize task scheduler
    default_config = ClocConfig(
        output_format=settings.default_cloc_output_format,
        use_gitignore=settings.default_use_gitignore,
        timeout=settings.default_cloc_timeout
    )
    scheduler = TaskScheduler(container_manager, default_config)
    await scheduler.start()
    logger.info("Task scheduler started")
    
    # Load repository configurations from database
    repos = await db.list_repositories(enabled_only=True)
    for repo in repos:
        if repo.cloc_config:
            from .task.models import ClocConfig
            config = ClocConfig(**repo.cloc_config)
            scheduler.set_repository_config(repo.repository_id, config)
    logger.info(f"Loaded {len(repos)} repository configurations")
    
    # Initialize webhook handler
    webhook_handler = WebhookHandler()
    
    # Register webhook callback
    async def on_push(event):
        """Handle push events."""
        logger.info(f"Received push event: {event.repository_name} @ {event.commit_sha[:7]}")
        
        # Schedule task
        task = await scheduler.schedule_from_push_event(event)
        
        # Save to database
        await db.save_task(task)
        
        logger.info(f"Task scheduled: {task.task_id}")
    
    webhook_handler.on_push_event(on_push)
    logger.info("Webhook handler initialized")
    
    # Register API router
    api_router = create_api_router(db, container_manager, scheduler)
    app.include_router(api_router)
    logger.info("API router registered")
    
    # Background task to sync task status to database
    async def sync_tasks():
        while True:
            try:
                for task in scheduler.tasks.values():
                    await db.save_task(task)
            except Exception as e:
                logger.error(f"Error syncing tasks: {e}", exc_info=True)
            
            await asyncio.sleep(10)
    
    sync_task = asyncio.create_task(sync_tasks())
    
    yield
    
    # Cleanup
    logger.info("Shutting down application...")
    
    # Cancel sync task
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    
    # Wait for running tasks to complete (with timeout)
    running_tasks = [
        task for task in scheduler.tasks.values()
        if task.status == TaskStatus.RUNNING
    ]
    
    if running_tasks:
        logger.info(f"Waiting for {len(running_tasks)} running tasks to complete...")
        
        # Wait up to 30 seconds for tasks to finish
        for i in range(30):
            running_tasks = [
                task for task in scheduler.tasks.values()
                if task.status == TaskStatus.RUNNING
            ]
            if not running_tasks:
                break
            await asyncio.sleep(1)
        
        if running_tasks:
            logger.warning(f"{len(running_tasks)} tasks still running, forcing shutdown")
    
    # Stop scheduler
    await scheduler.stop()
    
    # Save final state to database
    for task in scheduler.tasks.values():
        await db.save_task(task)
    
    await db.close()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Webhook-based code statistics tool",
    version=settings.app_version,
    lifespan=lifespan,
    debug=settings.debug
)


# Webhook endpoints
@app.post("/webhook/gitea")
async def gitea_webhook(request: Request):
    """Gitea webhook endpoint."""
    return await webhook_handler.handle_webhook(request, GitProvider.GITEA)


@app.post("/webhook/github")
async def github_webhook(request: Request):
    """GitHub webhook endpoint."""
    return await webhook_handler.handle_webhook(request, GitProvider.GITHUB)


@app.post("/webhook/gitlab")
async def gitlab_webhook(request: Request):
    """GitLab webhook endpoint."""
    return await webhook_handler.handle_webhook(request, GitProvider.GITLAB)


# Web interface
templates = Jinja2Templates(directory=str(Path(__file__).parent / "web" / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "scheduler": "running" if scheduler and scheduler._running else "stopped",
        "database": "connected" if db else "disconnected",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
