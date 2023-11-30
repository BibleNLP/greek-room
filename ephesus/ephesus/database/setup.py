"""
Initial configuration and setup of the Database
"""
from functools import partial

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.event import listen as sqlalchemy_listen

from ..config import get_ephesus_settings

# Get app settings
ephesus_setting = get_ephesus_settings()

## DB engine setup
engine = create_engine(
    ephesus_setting.sqlalchemy_database_uri, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

## Declarative base class
class Base(DeclarativeBase):
    pass


## Setup seed data
# This is here to avoid circular imports
from .models.user_projects import (
    User,
    Project,
    ProjectAccess,
)
from .seed import seed_data

# This method receives a table, a connection
# and inserts data to that table.
def seed_table(target, connection, **kw):
    tablename = str(target)
    if tablename in seed_data and len(seed_data[tablename]) > 0:
        connection.execute(target.insert(), seed_data[tablename])


sqlalchemy_listen(User.__table__, "after_create", seed_table)
sqlalchemy_listen(Project.__table__, "after_create", seed_table)
sqlalchemy_listen(ProjectAccess.__table__, "after_create", seed_table)
