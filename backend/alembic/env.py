
from logging.config import fileConfig

from alembic import context

# Import the existing database configuration
from app.core.database import Base, engine

# Import all SQLAlchemy models
# This ensures Alembic detects the User model
import app.models  # noqa: F401


# Alembic configuration
config = context.config

# Configure Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# SQLAlchemy metadata used for migration generation
target_metadata = Base.metadata


def run_migrations_offline():
    """
    Run migrations without connecting to PostgreSQL.
    """

    context.configure(
        url=engine.url.render_as_string(
            hide_password=False
        ),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    Run migrations using the PostgreSQL connection.
    """

    with engine.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# Select the appropriate migration mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
