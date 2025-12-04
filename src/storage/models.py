"""
Database models for persistent storage.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, JSON, Enum as SQLEnum, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ..task.models import TaskStatus


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Repository(Base):
    """Repository configuration."""
    
    __tablename__ = "repositories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    repository_name: Mapped[str] = mapped_column(String(255))
    repository_url: Mapped[str] = mapped_column(String(512))
    
    # CLOC configuration (stored as JSON)
    cloc_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Webhook configuration
    webhook_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Task(Base):
    """Code statistics task record."""
    
    __tablename__ = "tasks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    repository_id: Mapped[str] = mapped_column(String(255), index=True)
    repository_name: Mapped[str] = mapped_column(String(255))
    repository_url: Mapped[str] = mapped_column(String(512))
    
    branch: Mapped[str] = mapped_column(String(255))
    commit_sha: Mapped[str] = mapped_column(String(64))
    
    status: Mapped[str] = mapped_column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    container_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Result data (stored as JSON)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
