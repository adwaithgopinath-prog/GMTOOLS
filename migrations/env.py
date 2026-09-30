from logging.config import fileConfig
from alembic import context
from app import db  # Import your SQLAlchemy instance from app.py

# Alembic Config object
config = context.config

# Logging
fileConfig(config.config_file_name)

# Link Alembic to your models
target_metadata = db.metadata

def run_migrations_offline():
    url = db.engine.url.render_as_string(hide_password=False)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    with db.engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
