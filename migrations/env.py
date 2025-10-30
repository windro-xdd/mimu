"""Alembic environment configuration."""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from backend.db import Base, DatabaseConfig, get_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


database_config = DatabaseConfig.from_env()
config.set_main_option("sqlalchemy.url", database_config.url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    connectable = get_engine(database_config, poolclass=pool.NullPool)
    render_as_batch = connectable.dialect.name == "sqlite"

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=render_as_batch,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


def run_migrations() -> None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()


run_migrations()
