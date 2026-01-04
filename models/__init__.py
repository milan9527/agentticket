"""
Data Models for Ticket Auto-Processing System

This module contains Pydantic models for all business entities:
- Customer: User information and authentication data
- Ticket: Ticket information and metadata
- UpgradeOrder: Upgrade order processing and status
"""

from .customer import Customer, CustomerCreate, CustomerUpdate
from .ticket import Ticket, TicketCreate, TicketUpdate, TicketStatus, TicketType
from .upgrade_order import (
    UpgradeOrder, 
    UpgradeOrderCreate, 
    UpgradeOrderUpdate,
    UpgradeTier,
    OrderStatus
)
from .base import BaseModel, TimestampMixin

__all__ = [
    # Base models
    'BaseModel',
    'TimestampMixin',
    
    # Customer models
    'Customer',
    'CustomerCreate', 
    'CustomerUpdate',
    
    # Ticket models
    'Ticket',
    'TicketCreate',
    'TicketUpdate',
    'TicketStatus',
    'TicketType',
    
    # Upgrade order models
    'UpgradeOrder',
    'UpgradeOrderCreate',
    'UpgradeOrderUpdate',
    'UpgradeTier',
    'OrderStatus'
]