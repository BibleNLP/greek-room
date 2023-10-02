from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.event import listen as sqlalchemy_listen

from functools import partial

EPHESUS_DATABASE_URL = "sqlite:///./ephesus.db"
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

engine = create_engine(EPHESUS_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def load_sqlite_extension(db_conn, unused, ext_path=""):
    db_conn.enable_load_extension(True)
    db_conn.load_extension(ext_path)
    db_conn.enable_load_extension(False)


load_sqlite_json1_extension = partial(
    load_sqlite_extension,
    ext_path="/Users/fox/dev/workspace/bt/greek-room/instance/sqlite_ext/json1.dylib",
)

sqlalchemy_listen(engine, "connect", load_sqlite_json1_extension)

# declarative base class
class Base(DeclarativeBase):
    pass
