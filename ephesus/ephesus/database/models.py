from sqlalchemy import String, Enum, JSON, ForeignKey
from sqlalchemy.orm import (
    mapped_column,
    Mapped,
    relationship,
)

import secrets
from datetime import datetime, timezone

from .setup import Base
from ..constants import (
    StatusType,
    ProjectAccessType,
)
from .custom import (
    TZDateTime,
)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    projects = relationship("ProjectAccess", back_populates="user")


class Project(Base):
    """Model to hold project specific information"""

    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Human-and-URL-friendly ID
    resource_id: Mapped[str] = mapped_column(
        String(50), default=secrets.token_urlsafe(6)
    )
    name: Mapped[str] = mapped_column(String(1000))
    lang_code: Mapped[str] = mapped_column(String(10))
    tags: Mapped[JSON] = mapped_column(JSON, default=[])
    status: Mapped[Enum] = mapped_column(
        Enum(StatusType), default=StatusType.ACTIVE.name
    )
    create_datetime: Mapped[TZDateTime] = mapped_column(
        TZDateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    update_datetime: Mapped[TZDateTime] = mapped_column(
        TZDateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    # Store arbitary project metadata
    project_metadata: Mapped[JSON] = mapped_column(JSON, default={})

    users = relationship("ProjectAccess", back_populates="project")


# Join table for NxN relationship between
# Users and Projects tables
class ProjectAccess(Base):
    """Model to connect Users with Projects based on permissions and store metadata"""

    __tablename__ = "project_access"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    project_id: Mapped[int] = mapped_column(ForeignKey(Project.id))

    create_datetime: Mapped[TZDateTime] = mapped_column(
        TZDateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    update_datetime: Mapped[TZDateTime] = mapped_column(
        TZDateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="projects")
    project = relationship("Project", back_populates="users")

    access_type: Mapped[Enum] = mapped_column(Enum(ProjectAccessType))

    access_rights: Mapped[JSON] = mapped_column(JSON, default=[])
