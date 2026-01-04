"""
Base models and mixins for the Ticket Auto-Processing System
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import pydantic
from pydantic import BaseModel as PydanticBaseModel, ConfigDict, field_validator


class BaseModel(PydanticBaseModel):
    """Base model with common configuration"""
    
    model_config = ConfigDict(
        # Enable validation on assignment
        validate_assignment=True,
        # Use enum values instead of names
        use_enum_values=True,
        # Allow population by field name or alias
        populate_by_name=True,
        # Validate default values
        validate_default=True,
        # Extra fields are forbidden
        extra='forbid'
    )


class TimestampMixin(BaseModel):
    """Mixin for models with timestamp fields"""
    
    created_at: datetime
    updated_at: datetime
    
    @field_validator('created_at', 'updated_at')
    @classmethod
    def validate_timestamps(cls, v: datetime) -> datetime:
        """Ensure timestamps are timezone-aware"""
        if v.tzinfo is None:
            # Assume UTC if no timezone info
            v = v.replace(tzinfo=timezone.utc)
        return v


class UUIDMixin(BaseModel):
    """Mixin for models with UUID primary keys"""
    
    id: UUID
    
    @field_validator('id')
    @classmethod
    def validate_uuid(cls, v: UUID) -> UUID:
        """Ensure UUID is valid"""
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {v}")
        return v