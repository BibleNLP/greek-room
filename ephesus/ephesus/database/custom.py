"""
Custom extensions specific to the ORM
"""
# Core Python imports
import datetime

# 3rd party imports
from sqlalchemy.types import TypeDecorator

# From this project
from sqlalchemy import DateTime


class TZDateTime(TypeDecorator):
    """Timezone aware datetime type"""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not value.tzinfo:
                raise TypeError("tzinfo is required")
            value = value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value
