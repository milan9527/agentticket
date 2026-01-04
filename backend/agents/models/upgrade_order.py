"""
Upgrade Order data models for the Ticket Auto-Processing System
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID
import re
from pydantic import Field, field_validator
from .base import BaseModel, TimestampMixin, UUIDMixin


class UpgradeTier(str, Enum):
    """Available upgrade tiers"""
    STANDARD = "standard"
    NON_STOP = "non-stop"
    DOUBLE_FUN = "double-fun"


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class UpgradeOrderBase(BaseModel):
    """Base upgrade order model with common fields"""
    
    upgrade_tier: UpgradeTier = Field(
        ...,
        description="Target upgrade tier",
        examples=[UpgradeTier.STANDARD]
    )
    original_tier: str = Field(
        ...,
        max_length=50,
        description="Original ticket tier",
        examples=["general"]
    )
    price_difference: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Price difference for upgrade",
        examples=[25.00]
    )
    total_amount: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Total amount to be charged",
        examples=[75.00]
    )
    status: OrderStatus = Field(
        default=OrderStatus.PENDING,
        description="Current order status"
    )
    selected_date: Optional[datetime] = Field(
        None,
        description="Selected date for the upgraded experience"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional order metadata"
    )
    
    @field_validator('original_tier')
    @classmethod
    def validate_original_tier(cls, v: str) -> str:
        """Validate original tier format"""
        if not v or not v.strip():
            raise ValueError("Original tier cannot be empty")
        
        cleaned = v.strip().lower()
        
        # Valid tier names
        valid_tiers = ["general", "standard", "vip", "premium"]
        if cleaned not in valid_tiers:
            raise ValueError(f"Original tier must be one of: {', '.join(valid_tiers)}")
        
        return cleaned
    
    @field_validator('price_difference', 'total_amount')
    @classmethod
    def validate_amounts(cls, v: Decimal) -> Decimal:
        """Validate monetary amounts"""
        if v < 0:
            raise ValueError("Amount cannot be negative")
        
        if v > 10000:  # Reasonable upper limit
            raise ValueError("Amount cannot exceed $10,000")
        
        return v
    
    @field_validator('selected_date')
    @classmethod
    def validate_selected_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate selected date"""
        if v is None:
            return v
        
        # Ensure timezone awareness
        if v.tzinfo is None:
            v = v.replace(tzinfo=datetime.now().astimezone().tzinfo)
        
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


class UpgradeOrderCreate(UpgradeOrderBase):
    """Model for creating a new upgrade order"""
    
    ticket_id: UUID = Field(
        ...,
        description="ID of the ticket being upgraded"
    )
    customer_id: UUID = Field(
        ...,
        description="ID of the customer placing the order"
    )
    
    @field_validator('ticket_id', 'customer_id')
    @classmethod
    def validate_uuids(cls, v: UUID) -> UUID:
        """Validate UUID fields"""
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {v}")
        return v


class UpgradeOrderUpdate(BaseModel):
    """Model for updating upgrade order information"""
    
    status: Optional[OrderStatus] = Field(
        None,
        description="Updated order status"
    )
    payment_intent_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Payment processor intent ID"
    )
    confirmation_code: Optional[str] = Field(
        None,
        max_length=20,
        description="Order confirmation code"
    )
    selected_date: Optional[datetime] = Field(
        None,
        description="Updated selected date"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Updated metadata"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Completion timestamp"
    )
    
    @field_validator('payment_intent_id')
    @classmethod
    def validate_payment_intent_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate payment intent ID"""
        if v is None:
            return v
        
        cleaned = v.strip()
        if not cleaned:
            return None
        
        # Basic validation for payment intent ID format
        if not re.match(r'^[a-zA-Z0-9_\-]+$', cleaned):
            raise ValueError("Payment intent ID contains invalid characters")
        
        return cleaned
    
    @field_validator('confirmation_code')
    @classmethod
    def validate_confirmation_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate confirmation code"""
        if v is None:
            return v
        
        cleaned = v.strip().upper()
        if not cleaned:
            return None
        
        # Confirmation code should be alphanumeric
        if not re.match(r'^[A-Z0-9]+$', cleaned):
            raise ValueError("Confirmation code must be alphanumeric")
        
        if len(cleaned) < 4 or len(cleaned) > 20:
            raise ValueError("Confirmation code must be between 4 and 20 characters")
        
        return cleaned
    
    @field_validator('selected_date', 'completed_at')
    @classmethod
    def validate_dates(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate date fields"""
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


class UpgradeOrder(UpgradeOrderBase, UUIDMixin, TimestampMixin):
    """Complete upgrade order model with all fields"""
    
    ticket_id: UUID = Field(
        ...,
        description="ID of the ticket being upgraded"
    )
    customer_id: UUID = Field(
        ...,
        description="ID of the customer placing the order"
    )
    payment_intent_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Payment processor intent ID"
    )
    confirmation_code: Optional[str] = Field(
        None,
        max_length=20,
        description="Order confirmation code"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="When the order was completed"
    )
    
    @property
    def is_pending(self) -> bool:
        """Check if order is pending"""
        return self.status == OrderStatus.PENDING
    
    @property
    def is_completed(self) -> bool:
        """Check if order is completed"""
        return self.status == OrderStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if order failed"""
        return self.status == OrderStatus.FAILED
    
    @property
    def can_be_cancelled(self) -> bool:
        """Check if order can be cancelled"""
        return self.status in [OrderStatus.PENDING, OrderStatus.PROCESSING]
    
    @property
    def processing_time_minutes(self) -> Optional[int]:
        """Get processing time in minutes"""
        if not self.completed_at:
            return None
        
        delta = self.completed_at - self.created_at
        return int(delta.total_seconds() / 60)
    
    def get_upgrade_description(self) -> str:
        """Get human-readable upgrade description"""
        tier_descriptions = {
            UpgradeTier.STANDARD: "Standard Upgrade",
            UpgradeTier.NON_STOP: "Non-Stop Experience",
            UpgradeTier.DOUBLE_FUN: "Double Fun Package"
        }
        
        return tier_descriptions.get(self.upgrade_tier, self.upgrade_tier.value.title())
    
    def calculate_savings(self, original_price: Decimal) -> Decimal:
        """Calculate savings compared to buying new ticket"""
        # Assume new ticket would cost original_price + price_difference + 20%
        new_ticket_price = original_price + self.price_difference * Decimal('1.2')
        return new_ticket_price - self.total_amount
    
    def to_dict(self) -> dict:
        """Convert upgrade order to dictionary for serialization"""
        return {
            'id': str(self.id),
            'ticket_id': str(self.ticket_id),
            'customer_id': str(self.customer_id),
            'upgrade_tier': self.upgrade_tier.value,
            'original_tier': self.original_tier,
            'price_difference': float(self.price_difference),
            'total_amount': float(self.total_amount),
            'status': self.status.value,
            'payment_intent_id': self.payment_intent_id,
            'confirmation_code': self.confirmation_code,
            'selected_date': self.selected_date.isoformat() if self.selected_date else None,
            'metadata': self.metadata,
            'is_pending': self.is_pending,
            'is_completed': self.is_completed,
            'is_failed': self.is_failed,
            'can_be_cancelled': self.can_be_cancelled,
            'upgrade_description': self.get_upgrade_description(),
            'processing_time_minutes': self.processing_time_minutes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    class Config:
        """Pydantic configuration"""
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "ticket_id": "987fcdeb-51a2-43d1-9f12-345678901234",
                "customer_id": "456789ab-cdef-1234-5678-90abcdef1234",
                "upgrade_tier": "standard",
                "original_tier": "general",
                "price_difference": 25.00,
                "total_amount": 75.00,
                "status": "completed",
                "payment_intent_id": "pi_1234567890",
                "confirmation_code": "CONF12345",
                "selected_date": "2024-06-01T19:00:00Z",
                "metadata": {"special_requests": "aisle seat"},
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:30:00Z",
                "completed_at": "2024-01-01T12:30:00Z"
            }
        }