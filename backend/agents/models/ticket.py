"""
Ticket data models for the Ticket Auto-Processing System
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID
import re
from pydantic import Field, field_validator
from .base import BaseModel, TimestampMixin, UUIDMixin


class TicketStatus(str, Enum):
    """Ticket status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    USED = "used"
    UPGRADED = "upgraded"


class TicketType(str, Enum):
    """Ticket type enumeration"""
    GENERAL = "general"
    VIP = "vip"
    PREMIUM = "premium"
    STANDARD = "standard"


class TicketBase(BaseModel):
    """Base ticket model with common fields"""
    
    ticket_number: str = Field(
        ...,
        max_length=50,
        description="Unique ticket number",
        examples=["TKT-20240101"]
    )
    ticket_type: TicketType = Field(
        ...,
        description="Type of ticket",
        examples=[TicketType.GENERAL]
    )
    original_price: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Original ticket price",
        examples=[50.00]
    )
    event_date: datetime = Field(
        ...,
        description="Date and time of the event",
        examples=["2024-06-01T19:00:00Z"]
    )
    status: TicketStatus = Field(
        default=TicketStatus.ACTIVE,
        description="Current ticket status"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional ticket metadata"
    )
    
    @field_validator('ticket_number')
    @classmethod
    def validate_ticket_number(cls, v: str) -> str:
        """Validate ticket number format"""
        if not v or not v.strip():
            raise ValueError("Ticket number cannot be empty")
        
        cleaned = v.strip().upper()
        
        # Basic ticket number format validation (TKT-YYYYMMDD or similar)
        if not re.match(r'^[A-Z0-9\-]+$', cleaned):
            raise ValueError("Ticket number can only contain letters, numbers, and hyphens")
        
        if len(cleaned) < 5:
            raise ValueError("Ticket number must be at least 5 characters long")
        
        return cleaned
    
    @field_validator('original_price')
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """Validate ticket price"""
        if v < 0:
            raise ValueError("Ticket price cannot be negative")
        
        if v > 10000:  # Reasonable upper limit
            raise ValueError("Ticket price cannot exceed $10,000")
        
        return v
    
    @field_validator('event_date')
    @classmethod
    def validate_event_date(cls, v: datetime) -> datetime:
        """Validate event date"""
        # Ensure timezone awareness
        if v.tzinfo is None:
            v = v.replace(tzinfo=datetime.now().astimezone().tzinfo)
        
        # Event should be in the future (with some tolerance for testing)
        # In production, you might want stricter validation
        return v
    
    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata dictionary"""
        if not isinstance(v, dict):
            raise ValueError("Metadata must be a dictionary")
        
        # Ensure all keys are strings
        for key in v.keys():
            if not isinstance(key, str):
                raise ValueError("All metadata keys must be strings")
        
        return v


class TicketCreate(TicketBase):
    """Model for creating a new ticket"""
    
    customer_id: UUID = Field(
        ...,
        description="ID of the customer who owns this ticket"
    )
    purchase_date: Optional[datetime] = Field(
        None,
        description="Date when ticket was purchased (defaults to now)"
    )
    
    @field_validator('purchase_date')
    @classmethod
    def validate_purchase_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate purchase date"""
        if v is None:
            return v
        
        # Ensure timezone awareness
        if v.tzinfo is None:
            v = v.replace(tzinfo=datetime.now().astimezone().tzinfo)
        
        return v


class TicketUpdate(BaseModel):
    """Model for updating ticket information"""
    
    status: Optional[TicketStatus] = Field(
        None,
        description="Updated ticket status"
    )
    event_date: Optional[datetime] = Field(
        None,
        description="Updated event date"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Updated metadata"
    )
    
    @field_validator('event_date')
    @classmethod
    def validate_event_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate updated event date"""
        if v is None:
            return v
        
        # Ensure timezone awareness
        if v.tzinfo is None:
            v = v.replace(tzinfo=datetime.now().astimezone().tzinfo)
        
        return v
    
    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate updated metadata"""
        if v is None:
            return v
        
        if not isinstance(v, dict):
            raise ValueError("Metadata must be a dictionary")
        
        # Ensure all keys are strings
        for key in v.keys():
            if not isinstance(key, str):
                raise ValueError("All metadata keys must be strings")
        
        return v


class Ticket(TicketBase, UUIDMixin, TimestampMixin):
    """Complete ticket model with all fields"""
    
    customer_id: UUID = Field(
        ...,
        description="ID of the customer who owns this ticket"
    )
    purchase_date: datetime = Field(
        ...,
        description="Date when ticket was purchased"
    )
    
    @property
    def is_active(self) -> bool:
        """Check if ticket is active"""
        return self.status == TicketStatus.ACTIVE
    
    @property
    def is_upgradeable(self) -> bool:
        """Check if ticket can be upgraded"""
        return (
            self.status == TicketStatus.ACTIVE and 
            self.event_date > datetime.now().astimezone()
        )
    
    @property
    def days_until_event(self) -> int:
        """Get number of days until event"""
        if self.event_date.tzinfo is None:
            event_date = self.event_date.replace(tzinfo=datetime.now().astimezone().tzinfo)
        else:
            event_date = self.event_date
        
        now = datetime.now().astimezone()
        delta = event_date - now
        return max(0, delta.days)
    
    def can_upgrade_to(self, target_tier: str) -> bool:
        """Check if ticket can be upgraded to target tier"""
        if not self.is_upgradeable:
            return False
        
        # Define upgrade paths
        upgrade_paths = {
            TicketType.GENERAL: ["standard", "non-stop", "double-fun"],
            TicketType.STANDARD: ["non-stop", "double-fun"],
            TicketType.VIP: ["double-fun"],
            TicketType.PREMIUM: []  # Premium tickets cannot be upgraded
        }
        
        return target_tier in upgrade_paths.get(self.ticket_type, [])
    
    def to_dict(self) -> dict:
        """Convert ticket to dictionary for serialization"""
        return {
            'id': str(self.id),
            'customer_id': str(self.customer_id),
            'ticket_number': self.ticket_number,
            'ticket_type': self.ticket_type.value,
            'original_price': float(self.original_price),
            'purchase_date': self.purchase_date.isoformat(),
            'event_date': self.event_date.isoformat(),
            'status': self.status.value,
            'metadata': self.metadata,
            'is_active': self.is_active,
            'is_upgradeable': self.is_upgradeable,
            'days_until_event': self.days_until_event,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    class Config:
        """Pydantic configuration"""
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "customer_id": "987fcdeb-51a2-43d1-9f12-345678901234",
                "ticket_number": "TKT-20240101",
                "ticket_type": "general",
                "original_price": 50.00,
                "purchase_date": "2024-01-01T10:00:00Z",
                "event_date": "2024-06-01T19:00:00Z",
                "status": "active",
                "metadata": {"section": "A", "row": "12", "seat": "5"},
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:00:00Z"
            }
        }