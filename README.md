# CodeStat Agent

A lightweight, webhook-based code statistics tool that automatically analyzes code line counts for Gitea, GitHub, and GitLab repositories using Docker.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Features

- **Multi-Platform Support**: Abstracted webhook layer compatible with Gitea, GitHub, and GitLab.
- **Dockerized Execution**: Each analysis task runs in an isolated, lightweight Docker container (`alpine-linux`, `git`, `cloc`).
- **Incremental Analysis**: Repositories are persisted on the host, enabling fast `git pull` for subsequent analyses instead of full clones.
- **Configurable**: Supports global and repository-specific `cloc` parameter configuration.
- **.gitignore Aware**: Automatically uses the repository's `.gitignore` file to exclude files from analysis.
- **Web Dashboard**: A simple web interface to view repositories, recent tasks, and manage running containers.
- **REST API**: Provides API endpoints for programmatic management and integration.

## 🏗️ Architecture

The system is composed of a central agent that listens for webhook events and a set of worker containers that perform the analysis.

1.  **Webhook Receiver**: A unified endpoint (`/webhook/{provider}`) receives push events.
2.  **Event Parser**: The payload is parsed into a standardized `PushEvent` model.
3.  **Task Scheduler**: If the push is to the main branch, a new statistics task is scheduled.
4.  **Container Manager**: A dedicated Docker container is created or reused for the specific repository.
5.  **Worker Container**: The container clones or pulls the repository, runs `cloc` with the specified configuration, and saves the JSON result.
6.  **Database**: Task status and results are stored in a local SQLite database.
7.  **Web UI**: The FastAPI backend serves a simple dashboard to monitor the system.

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/zihaoli-cn/codestat-agent.git
    cd codestat-agent
    ```

2.  **Build the worker container image:**

    This image contains `git` and `cloc` and is used to run the analysis.

    ```bash
    ./docker/build.sh
    ```

3.  **Run the application with Docker Compose:**

    This will start the main CodeStat Agent service.

    ```bash
    docker-compose up --build
    ```

4.  **Access the Dashboard:**

    Open your browser and navigate to `http://localhost:8000`.

## 🔧 Configuration

### 0. Environment Variables (Optional)

CodeStat Agent supports flexible configuration through environment variables or a `.env` file.

**Copy the example configuration:**

```bash
cp .env.example .env
```

**Edit `.env` to customize your settings:**

```bash
# Application
APP_NAME=CodeStat Agent
DEBUG=false

# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/codestat.db

# Storage
DATA_DIR=./data

# Task Scheduler
TASK_CHECK_INTERVAL=5
TASK_MAX_MEMORY=1000

# Container
WORKER_IMAGE=codestat-worker:latest
CONTAINER_MEMORY_LIMIT=512m
CONTAINER_CPU_QUOTA=50000

# Default CLOC Configuration
DEFAULT_CLOC_TIMEOUT=600
DEFAULT_CLOC_OUTPUT_FORMAT=json
DEFAULT_USE_GITIGNORE=true
```

All settings have sensible defaults and can be overridden via environment variables.

### 1. Add a Repository

Configuration is managed via the REST API. You can use `curl` to add and configure a repository.

```bash
curl -X POST http://localhost:8000/api/repositories/{repository_id} \
-H "Content-Type: application/json" \
-d 
    {
        "repository_name": "owner/repo-name",
        "repository_url": "https://gitea.com/owner/repo-name.git",
        "webhook_secret": "your-webhook-secret",
        "cloc_config": {
            "exclude_lang": ["Markdown", "YAML"],
            "use_gitignore": true
        }
    }
```

- `{repository_id}`: A unique identifier for your repository (e.g., `gitea_owner_repo-name`).

### 2. Configure Webhooks

In your Git provider (Gitea, GitHub, GitLab), go to your repository's settings and add a new webhook.

- **Payload URL**: `http://<your-server-ip>:8000/webhook/{provider}`
    - Use `gitea`, `github`, or `gitlab` for `{provider}`.
- **Content Type**: `application/json`
- **Secret**: Enter the same secret you used in the API configuration.
- **Events**: Trigger on `push` events.

### 3. CLOC Configuration

The `cloc_config` object in the repository configuration supports the following fields:

- `exclude_ext` (list[str]): File extensions to exclude.
- `exclude_lang` (list[str]): Languages to exclude.
- `include_ext` (list[str]): File extensions to include.
- `use_gitignore` (bool): Whether to use `.gitignore` for exclusions (default: `true`).
- `timeout` (int): Task timeout in seconds (default: `600`).

## 📦 API Endpoints

The application provides a REST API for management. See the code in `src/web/api.py` for details.

- `GET /api/repositories`: List all configured repositories.
- `POST /api/repositories/{id}`: Create or update a repository.
- `GET /api/tasks`: List recent analysis tasks.
- `GET /api/containers`: List all managed Docker containers.
- `POST /api/containers/{id}/stop`: Stop a running container.

## 🖼️ Web Interface

The web dashboard at `http://localhost:8000` provides a simple, real-time view of:

- **Repositories**: A list of all configured code repositories.
- **Tasks**: A log of recent analysis tasks with their status and results.
- **Containers**: A list of active and stopped worker containers, with an option to stop them.

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
