# migrate.py
import os
from alembic.config import Config
from alembic import command
from alembic import context


config = context.config

database_url = os.getenv('DATABASE_URL')
if database_url:
    config.set_main_option('sqlalchemy.url', database_url)

alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")