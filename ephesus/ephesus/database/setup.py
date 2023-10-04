"""
Initial configuration and setup of the Database
"""
from functools import partial

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.event import listen as sqlalchemy_listen


EPHESUS_DATABASE_URL = "sqlite:///./ephesus.db"
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

## DB engine setup
engine = create_engine(EPHESUS_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

## Load Sqlite extensions
def load_sqlite_extension(db_conn, unused, ext_path=""):
    db_conn.enable_load_extension(True)
    db_conn.load_extension(ext_path)
    db_conn.enable_load_extension(False)


load_sqlite_json1_extension = partial(
    load_sqlite_extension,
    ext_path="/Users/fox/dev/workspace/bt/greek-room/instance/sqlite_ext/json1.dylib",
)
sqlalchemy_listen(engine, "connect", load_sqlite_json1_extension)

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
