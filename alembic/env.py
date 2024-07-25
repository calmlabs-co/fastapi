from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
  fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# from backend.app.dependencies.database import Base
from sqlmodel import SQLModel
from alembic import context
from backend.app.models.message import Message
from backend.app.models.user import User
from backend.app.models.summary import Summary

from sqlmodel import create_engine

target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Define the include_name function to exclude specific tables
def include_name(name, type_, parent_names):
    # List of tables to exclude
    excluded_tables = ["slack_installations", "slack_oauth_states", "slack_bots"]
    # op.drop_index('slack_installations_idx', table_name='slack_installations')
    # op.drop_table('slack_installations')
    # op.drop_index('slack_bots_idx', table_name='slack_bots')
    # op.drop_table('slack_bots')
    # op.drop_table('slack_oauth_states')
    # or type_ == "index"
    if type_ == "table":
        # Return False if the table is in the excluded list
        if name in excluded_tables:
            return False
        # Check schema-qualified names as well
        if "schema_qualified_table_name" in parent_names:
            if parent_names["schema_qualified_table_name"] in excluded_tables:
                return False
        # Include all other tables
        return parent_names["schema_qualified_table_name"] in target_metadata.tables
    else:
        return True



def run_migrations_offline() -> None:
  """Run migrations in 'offline' mode.

  This configures the context with just a URL
  and not an Engine, though an Engine is acceptable
  here as well.  By skipping the Engine creation
  we don't even need a DBAPI to be available.

  Calls to context.execute() here emit the given string to the
  script output.

  """
  url = config.get_main_option("sqlalchemy.url")
  context.configure(
    url=url,
    target_metadata=target_metadata,
    literal_binds=True,
    dialect_opts={"paramstyle": "named"},
  )

  with context.begin_transaction():
    context.run_migrations()


def run_migrations_online() -> None:
  """Run migrations in 'online' mode.

  In this scenario we need to create an Engine
  and associate a connection with the context.

  """
  connectable = create_engine(os.getenv('DATABASE_URL'))

  with connectable.connect() as connection:
    context.configure(
      connection=connection, 
      target_metadata=target_metadata,
      include_name=include_name,
    )

    with context.begin_transaction():
      context.run_migrations()


if context.is_offline_mode():
  run_migrations_offline()
else:
  run_migrations_online()