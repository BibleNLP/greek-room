from typing import (
    List,
)
from functools import partial
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Enum,
    JSON,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import (
    mapped_column,
    Mapped,
    relationship,
)

from ..setup import Base
from ...constants import (
    StatusType,
    ProjectAccessType,
)
from ..custom import (
    TZDateTime,
)


class User(Base):
    """Model to hold user specific information"""
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    create_datetime: Mapped[TZDateTime] = mapped_column(
        TZDateTime(timezone=True), default=partial(datetime.now, tz=timezone.utc)
    )

    update_datetime: Mapped[TZDateTime] = mapped_column(
        TZDateTime(timezone=True),
        default=partial(datetime.now, tz=timezone.utc),
        onupdate=partial(datetime.now, tz=timezone.utc),
    )

    projects: Mapped[List["Project"]] = relationship(
        "ProjectAccess", back_populates="user"
    )


class Project(Base):
    """Model to hold project specific information"""

    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Human-and-URL-friendly ID
    resource_id: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(1000))
    lang_code: Mapped[str] = mapped_column(String(10))
    lang_name: Mapped[str] = mapped_column(String(100))

    tags: Mapped[JSON | None] = mapped_column(JSON, default=[])
    status: Mapped[Enum] = mapped_column(
        Enum(StatusType), default=StatusType.ACTIVE.name
    )
    create_datetime: Mapped[TZDateTime] = mapped_column(
        TZDateTime(timezone=True), default=partial(datetime.now, tz=timezone.utc)
    )

    update_datetime: Mapped[TZDateTime] = mapped_column(
        TZDateTime(timezone=True),
        default=partial(datetime.now, tz=timezone.utc),
        onupdate=partial(datetime.now, tz=timezone.utc),
    )

    # Store arbitrary project metadata
    project_metadata: Mapped[JSON] = mapped_column(JSON, default={})

    users: Mapped[List["User"]] = relationship(
        "ProjectAccess", back_populates="project"
    )

    # Self-referential key for handling things like references
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("project.id"))
    # Handle deletion manually (not via cascade) to avoid unintentional deletion
    children: Mapped[List["Project"]] = relationship()


# Join table for NxN relationship between
# Users and Projects tables
class ProjectAccess(Base):
    """Model to connect Users with Projects based on permissions and store metadata"""

    __tablename__ = "project_access"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    project_id: Mapped[int] = mapped_column(ForeignKey(Project.id))

    create_datetime: Mapped[TZDateTime] = mapped_column(
        TZDateTime(timezone=True), default=partial(datetime.now, tz=timezone.utc)
    )

    update_datetime: Mapped[TZDateTime] = mapped_column(
        TZDateTime(timezone=True),
        default=partial(datetime.now, tz=timezone.utc),
        onupdate=partial(datetime.now, tz=timezone.utc),
    )

    user: Mapped[List["User"]] = relationship("User", back_populates="projects")
    project: Mapped[List["Project"]] = relationship("Project", back_populates="users")

    access_type: Mapped[Enum | None] = mapped_column(Enum(ProjectAccessType))
    access_rights: Mapped[JSON | None] = mapped_column(JSON, default=[])
