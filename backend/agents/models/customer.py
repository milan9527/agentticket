"""
Customer data models for the Ticket Auto-Processing System
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
import re
from pydantic import EmailStr, Field, field_validator
from .base import BaseModel, TimestampMixin, UUIDMixin


class CustomerBase(BaseModel):
    """Base customer model with common fields"""
    
    email: EmailStr = Field(
        ..., 
        description="Customer email address (unique)",
        examples=["john.doe@example.com"]
    )
    first_name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Customer first name",
        examples=["John"]
    )
    last_name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Customer last name", 
        examples=["Doe"]
    )
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="Customer phone number",
        examples=["+1-555-0101"]
    )
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name fields"""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        
        # Remove extra whitespace and title case
        cleaned = v.strip().title()
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-']+$", cleaned):
            raise ValueError("Name can only contain letters, spaces, hyphens, and apostrophes")
        
        return cleaned
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format"""
        if v is None:
            return v
        
        # Remove all non-digit characters except + and -
        cleaned = re.sub(r'[^\d\+\-\(\)\s]', '', v.strip())
        
        if not cleaned:
            return None
        
        # Basic phone number validation (international format)
        if not re.match(r'^[\+]?[\d\-\(\)\s]{10,20}$', cleaned):
            raise ValueError("Invalid phone number format")
        
        return cleaned


class CustomerCreate(CustomerBase):
    """Model for creating a new customer"""
    
    cognito_user_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Cognito user ID for authentication",
        examples=["us-west-2:12345678-1234-1234-1234-123456789012"]
    )
    
    @field_validator('cognito_user_id')
    @classmethod
    def validate_cognito_user_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate Cognito user ID format"""
        if v is None:
            return v
        
        # Basic Cognito user ID format validation
        if not re.match(r'^[a-zA-Z0-9\-:]+$', v):
            raise ValueError("Invalid Cognito user ID format")
        
        return v


class CustomerUpdate(BaseModel):
    """Model for updating customer information"""
    
    first_name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=100,
        description="Updated first name"
    )
    last_name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=100,
        description="Updated last name"
    )
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="Updated phone number"
    )
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate name fields for updates"""
        if v is None:
            return v
        
        if not v or not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        
        # Remove extra whitespace and title case
        cleaned = v.strip().title()
        
        # Check for valid characters
        if not re.match(r"^[a-zA-Z\s\-']+$", cleaned):
            raise ValueError("Name can only contain letters, spaces, hyphens, and apostrophes")
        
        return cleaned
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number for updates"""
        if v is None:
            return v
        
        # Remove all non-digit characters except + and -
        cleaned = re.sub(r'[^\d\+\-\(\)\s]', '', v.strip())
        
        if not cleaned:
            return None
        
        # Basic phone number validation
        if not re.match(r'^[\+]?[\d\-\(\)\s]{10,20}$', cleaned):
            raise ValueError("Invalid phone number format")
        
        return cleaned


class Customer(CustomerBase, UUIDMixin, TimestampMixin):
    """Complete customer model with all fields"""
    
    cognito_user_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Cognito user ID for authentication"
    )
    
    @property
    def full_name(self) -> str:
        """Get customer's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def display_name(self) -> str:
        """Get customer's display name for UI"""
        return self.full_name
    
    def to_dict(self) -> dict:
        """Convert customer to dictionary for serialization"""
        return {
            'id': str(self.id),
            'email': self.email,
            'cognito_user_id': self.cognito_user_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'phone': self.phone,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    class Config:
        """Pydantic configuration"""
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john.doe@example.com",
                "cognito_user_id": "us-west-2:12345678-1234-1234-1234-123456789012",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1-555-0101",
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z"
            }
        }