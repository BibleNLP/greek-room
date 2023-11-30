"""
Schemas/types used across the app
"""
from datetime import datetime
from typing_extensions import TypedDict
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Json,
    PlainSerializer,
    TypeAdapter,
)

from ..constants import (
    StatusType,
    ProjectAccessType,
)

# Model for project details in listing
class ProjectListModel(BaseModel):
    """Model for storing project details"""

    model_config = ConfigDict(from_attributes=True)

    resource_id: str
    name: str
    lang_code: str
    create_datetime: datetime


# Model for ProjectAccess
class ProjectAccessModel(BaseModel):
    """Model for the DB ProjectAccess class"""

    model_config = ConfigDict(from_attributes=True)

    create_datetime: datetime
    update_datetime: datetime

    access_type: ProjectAccessType
    access_rights: list[str | None]


# Model for Project
class ProjectModel(ProjectListModel):
    """The model for the DB Project class"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tags: list[str] = None
    status: StatusType
    update_datetime: datetime


class ProjectWithAccessModel(TypedDict):
    Project: ProjectModel
    ProjectAccess: ProjectAccessModel
