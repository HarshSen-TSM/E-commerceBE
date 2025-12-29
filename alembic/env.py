from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --------------------------------------------------
# Alembic Config
# --------------------------------------------------
config = context.config

# Configure logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --------------------------------------------------
# IMPORT SQLALCHEMY BASE + MODELS
# --------------------------------------------------
from database import Base

# IMPORTANT: import all models so Alembic can detect tables
from models.payment_model import Payment
from models.order_model import Order
# Later you can add:
# from models.product_model import Product
# from models.cart_model import Cart
# from models.inventory_model import Inventory

# Set metadata for autogenerate support
target_metadata = Base.metadata


# --------------------------------------------------
# OFFLINE MIGRATIONS
# --------------------------------------------------
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    This configures the context with just a URL.
    """
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # REQUIRED FOR SQLITE
    )

    with context.begin_transaction():
        context.run_migrations()


# --------------------------------------------------
# ONLINE MIGRATIONS
# --------------------------------------------------
def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Creates an Engine and associates a connection.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # REQUIRED FOR SQLITE
        )

        with context.begin_transaction():
            context.run_migrations()


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
