
"""
SQLAlchemy models for the NexaSense application.

Import models here so that Alembic can discover them
when generating database migrations.
"""

from app.models.user import User

__all__ = ["User"]
