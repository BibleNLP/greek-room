"""
Schemas/types used across the app
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

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


# Model for Project
class ProjectModel(ProjectListModel):
    """The model for the DB Project model"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tags: list[str] = None
    status: StatusType
    update_datetime: datetime
