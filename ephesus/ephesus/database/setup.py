"""
Initial configuration and setup of the Database
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.event import listen as sqlalchemy_listen

from ..constants import EphesusEnvType
from ..config import get_ephesus_settings

# Get app settings
ephesus_settings = get_ephesus_settings()

## DB engine setup
engine = create_engine(
    ephesus_settings.sqlalchemy_database_uri, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

## Declarative base class
class Base(DeclarativeBase):
    pass
