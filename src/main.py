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
from .storage import DatabaseManager
from .web import create_api_router


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
    db = DatabaseManager()
    await db.init_db()
    print("Database initialized")
    
    # Initialize container manager
    container_manager = ContainerManager(data_dir="./data")
    print("Container manager initialized")
    
    # Initialize task scheduler
    default_config = ClocConfig(
        output_format="json",
        use_gitignore=True,
        timeout=600
    )
    scheduler = TaskScheduler(container_manager, default_config)
    await scheduler.start()
    print("Task scheduler started")
    
    # Load repository configurations from database
    repos = await db.list_repositories(enabled_only=True)
    for repo in repos:
        if repo.cloc_config:
            from .task.models import ClocConfig
            config = ClocConfig(**repo.cloc_config)
            scheduler.set_repository_config(repo.repository_id, config)
    print(f"Loaded {len(repos)} repository configurations")
    
    # Initialize webhook handler
    webhook_handler = WebhookHandler()
    
    # Register webhook callback
    async def on_push(event):
        """Handle push events."""
        print(f"Received push event: {event.repository_name} @ {event.commit_sha[:7]}")
        
        # Schedule task
        task = await scheduler.schedule_from_push_event(event)
        
        # Save to database
        await db.save_task(task)
        
        print(f"Task scheduled: {task.task_id}")
    
    webhook_handler.on_push_event(on_push)
    print("Webhook handler initialized")
    
    # Register API router
    api_router = create_api_router(db, container_manager, scheduler)
    app.include_router(api_router)
    print("API router registered")
    
    # Background task to sync task status to database
    async def sync_tasks():
        while True:
            try:
                for task in scheduler.tasks.values():
                    await db.save_task(task)
            except Exception as e:
                print(f"Error syncing tasks: {e}")
            
            await asyncio.sleep(10)
    
    sync_task = asyncio.create_task(sync_tasks())
    
    yield
    
    # Cleanup
    sync_task.cancel()
    await scheduler.stop()
    await db.close()
    print("Application shutdown")


# Create FastAPI app
app = FastAPI(
    title="CodeStat Agent",
    description="Webhook-based code statistics tool",
    version="1.0.0",
    lifespan=lifespan
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
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
