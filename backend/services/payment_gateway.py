#!/usr/bin/env python3
"""
Dummy Payment Gateway Service for Ticket Auto-Processing System

This service simulates payment processing with configurable success/failure rates,
transaction logging, and retry mechanisms for development and testing purposes.
"""

import os
import sys
import json
import asyncio
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from enum import Enum
import boto3
from botocore.exceptions import ClientError

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    """Payment transaction status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment method types"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"


class PaymentTransaction(BaseModel):
    """Payment transaction model"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str = Field(..., description="Customer ID")
    upgrade_order_id: str = Field(..., description="Upgrade order ID")
    amount: Decimal = Field(..., description="Payment amount")
    currency: str = Field(default="USD", description="Currency code")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, description="Payment status")
    gateway_transaction_id: Optional[str] = Field(None, description="Gateway transaction ID")
    failure_reason: Optional[str] = Field(None, description="Failure reason if failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    class Config:
        json_encoders = {
            Decimal: float,
            datetime: lambda v: v.isoformat()
        }


class PaymentGatewayConfig(BaseModel):
    """Configuration for the Payment Gateway"""
    
    success_rate: float = Field(default=0.8, description="Success rate (0.0 to 1.0)")
    processing_delay_min: float = Field(default=1.0, description="Min processing delay in seconds")
    processing_delay_max: float = Field(default=5.0, description="Max processing delay in seconds")
    max_retry_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_base: float = Field(default=2.0, description="Base retry delay in seconds")
    enable_logging: bool = Field(default=True, description="Enable transaction logging")
    log_file: str = Field(default="payment_transactions.log", description="Log file path")


class PaymentGateway:
    """Dummy Payment Gateway with configurable behavior"""
    
    def __init__(self, config: PaymentGatewayConfig):
        self.config = config
        self.transactions: Dict[str, PaymentTransaction] = {}
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up transaction logging"""
        if self.config.enable_logging:
            import logging
            
            self.logger = logging.getLogger('PaymentGateway')
            self.logger.setLevel(logging.INFO)
            
            # Create file handler
            handler = logging.FileHandler(self.config.log_file)
            handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            
            # Add handler to logger
            if not self.logger.handlers:
                self.logger.addHandler(handler)
    
    async def process_payment(self, 
                            customer_id: str,
                            upgrade_order_id: str,
                            amount: Decimal,
                            payment_method: PaymentMethod,
                            currency: str = "USD") -> PaymentTransaction:
        """Process a payment transaction"""
        
        # Create transaction record
        transaction = PaymentTransaction(
            customer_id=customer_id,
            upgrade_order_id=upgrade_order_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method
        )
        
        # Store transaction
        self.transactions[transaction.id] = transaction
        
        # Log transaction start
        if self.config.enable_logging:
            self.logger.info(f"Payment processing started: {transaction.id} - ${float(amount):.2f}")
        
        try:
            # Update status to processing
            transaction.status = PaymentStatus.PROCESSING
            transaction.updated_at = datetime.now()
            
            # Simulate processing delay
            processing_delay = random.uniform(
                self.config.processing_delay_min,
                self.config.processing_delay_max
            )
            await asyncio.sleep(processing_delay)
            
            # Simulate payment processing with configurable success rate
            success = random.random() < self.config.success_rate
            
            if success:
                # Payment successful
                transaction.status = PaymentStatus.COMPLETED
                transaction.gateway_transaction_id = f"gw_{uuid.uuid4().hex[:12]}"
                transaction.completed_at = datetime.now()
                transaction.updated_at = datetime.now()
                
                if self.config.enable_logging:
                    self.logger.info(f"Payment completed: {transaction.id} - {transaction.gateway_transaction_id}")
            
            else:
                # Payment failed
                transaction.status = PaymentStatus.FAILED
                transaction.failure_reason = self._generate_failure_reason()
                transaction.updated_at = datetime.now()
                
                if self.config.enable_logging:
                    self.logger.warning(f"Payment failed: {transaction.id} - {transaction.failure_reason}")
            
            return transaction
            
        except Exception as e:
            # Handle processing errors
            transaction.status = PaymentStatus.FAILED
            transaction.failure_reason = f"Processing error: {str(e)}"
            transaction.updated_at = datetime.now()
            
            if self.config.enable_logging:
                self.logger.error(f"Payment processing error: {transaction.id} - {str(e)}")
            
            return transaction
    
    async def retry_payment(self, transaction_id: str) -> PaymentTransaction:
        """Retry a failed payment transaction"""
        
        if transaction_id not in self.transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        transaction = self.transactions[transaction_id]
        
        # Check if retry is allowed
        if transaction.retry_count >= self.config.max_retry_attempts:
            raise ValueError(f"Maximum retry attempts ({self.config.max_retry_attempts}) exceeded")
        
        if transaction.status not in [PaymentStatus.FAILED, PaymentStatus.PENDING]:
            raise ValueError(f"Cannot retry transaction with status: {transaction.status}")
        
        # Increment retry count
        transaction.retry_count += 1
        transaction.updated_at = datetime.now()
        
        # Calculate retry delay with exponential backoff
        retry_delay = self.config.retry_delay_base ** transaction.retry_count
        await asyncio.sleep(retry_delay)
        
        if self.config.enable_logging:
            self.logger.info(f"Retrying payment: {transaction_id} (attempt {transaction.retry_count})")
        
        # Process payment again
        return await self._retry_process_payment(transaction)
    
    async def _retry_process_payment(self, transaction: PaymentTransaction) -> PaymentTransaction:
        """Internal method to retry payment processing"""
        
        try:
            # Update status to processing
            transaction.status = PaymentStatus.PROCESSING
            transaction.updated_at = datetime.now()
            
            # Simulate processing delay
            processing_delay = random.uniform(
                self.config.processing_delay_min,
                self.config.processing_delay_max
            )
            await asyncio.sleep(processing_delay)
            
            # Slightly higher success rate for retries
            retry_success_rate = min(self.config.success_rate + 0.1, 1.0)
            success = random.random() < retry_success_rate
            
            if success:
                # Payment successful
                transaction.status = PaymentStatus.COMPLETED
                transaction.gateway_transaction_id = f"gw_{uuid.uuid4().hex[:12]}"
                transaction.completed_at = datetime.now()
                transaction.updated_at = datetime.now()
                transaction.failure_reason = None  # Clear previous failure reason
                
                if self.config.enable_logging:
                    self.logger.info(f"Payment retry successful: {transaction.id} - {transaction.gateway_transaction_id}")
            
            else:
                # Payment failed again
                transaction.status = PaymentStatus.FAILED
                transaction.failure_reason = self._generate_failure_reason()
                transaction.updated_at = datetime.now()
                
                if self.config.enable_logging:
                    self.logger.warning(f"Payment retry failed: {transaction.id} - {transaction.failure_reason}")
            
            return transaction
            
        except Exception as e:
            # Handle processing errors
            transaction.status = PaymentStatus.FAILED
            transaction.failure_reason = f"Retry processing error: {str(e)}"
            transaction.updated_at = datetime.now()
            
            if self.config.enable_logging:
                self.logger.error(f"Payment retry error: {transaction.id} - {str(e)}")
            
            return transaction
    
    def _generate_failure_reason(self) -> str:
        """Generate realistic failure reasons"""
        failure_reasons = [
            "Insufficient funds",
            "Card declined by issuer",
            "Invalid card number",
            "Card expired",
            "CVV verification failed",
            "Transaction limit exceeded",
            "Suspected fraud",
            "Network timeout",
            "Gateway temporarily unavailable",
            "Invalid merchant configuration"
        ]
        
        return random.choice(failure_reasons)
    
    async def get_transaction(self, transaction_id: str) -> Optional[PaymentTransaction]:
        """Get transaction by ID"""
        return self.transactions.get(transaction_id)
    
    async def get_transactions_by_customer(self, customer_id: str) -> List[PaymentTransaction]:
        """Get all transactions for a customer"""
        return [
            transaction for transaction in self.transactions.values()
            if transaction.customer_id == customer_id
        ]
    
    async def get_transactions_by_order(self, upgrade_order_id: str) -> List[PaymentTransaction]:
        """Get all transactions for an upgrade order"""
        return [
            transaction for transaction in self.transactions.values()
            if transaction.upgrade_order_id == upgrade_order_id
        ]
    
    async def cancel_payment(self, transaction_id: str) -> PaymentTransaction:
        """Cancel a pending payment transaction"""
        
        if transaction_id not in self.transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        transaction = self.transactions[transaction_id]
        
        if transaction.status not in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]:
            raise ValueError(f"Cannot cancel transaction with status: {transaction.status}")
        
        transaction.status = PaymentStatus.CANCELLED
        transaction.updated_at = datetime.now()
        
        if self.config.enable_logging:
            self.logger.info(f"Payment cancelled: {transaction_id}")
        
        return transaction
    
    async def refund_payment(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentTransaction:
        """Refund a completed payment transaction"""
        
        if transaction_id not in self.transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        transaction = self.transactions[transaction_id]
        
        if transaction.status != PaymentStatus.COMPLETED:
            raise ValueError(f"Cannot refund transaction with status: {transaction.status}")
        
        # For simplicity, we'll just update the status
        # In a real system, this would create a separate refund transaction
        transaction.status = PaymentStatus.REFUNDED
        transaction.updated_at = datetime.now()
        
        refund_amount = amount or transaction.amount
        
        if self.config.enable_logging:
            self.logger.info(f"Payment refunded: {transaction_id} - ${float(refund_amount):.2f}")
        
        return transaction
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get payment gateway statistics"""
        total_transactions = len(self.transactions)
        
        if total_transactions == 0:
            return {
                "total_transactions": 0,
                "success_rate": 0.0,
                "average_amount": 0.0,
                "status_breakdown": {}
            }
        
        completed_count = sum(1 for t in self.transactions.values() if t.status == PaymentStatus.COMPLETED)
        total_amount = sum(t.amount for t in self.transactions.values())
        
        status_breakdown = {}
        for status in PaymentStatus:
            count = sum(1 for t in self.transactions.values() if t.status == status)
            status_breakdown[status.value] = count
        
        return {
            "total_transactions": total_transactions,
            "success_rate": completed_count / total_transactions if total_transactions > 0 else 0.0,
            "average_amount": float(total_amount / total_transactions) if total_transactions > 0 else 0.0,
            "total_amount": float(total_amount),
            "status_breakdown": status_breakdown
        }


def load_config() -> PaymentGatewayConfig:
    """Load configuration from environment variables"""
    # Load from .env file if it exists
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    return PaymentGatewayConfig(
        success_rate=float(os.getenv('PAYMENT_SUCCESS_RATE', '0.8')),
        processing_delay_min=float(os.getenv('PAYMENT_DELAY_MIN', '1.0')),
        processing_delay_max=float(os.getenv('PAYMENT_DELAY_MAX', '5.0')),
        max_retry_attempts=int(os.getenv('PAYMENT_MAX_RETRIES', '3')),
        retry_delay_base=float(os.getenv('PAYMENT_RETRY_DELAY', '2.0')),
        enable_logging=os.getenv('PAYMENT_LOGGING', 'true').lower() == 'true',
        log_file=os.getenv('PAYMENT_LOG_FILE', 'payment_transactions.log')
    )


# Example usage and testing
async def main():
    """Example usage of the Payment Gateway"""
    print("🏦 Dummy Payment Gateway Test")
    print("=" * 40)
    
    # Load configuration
    config = load_config()
    gateway = PaymentGateway(config)
    
    print(f"✅ Payment Gateway initialized")
    print(f"   Success rate: {config.success_rate * 100:.1f}%")
    print(f"   Max retries: {config.max_retry_attempts}")
    
    # Test payment processing
    print(f"\n💳 Testing payment processing...")
    
    transaction = await gateway.process_payment(
        customer_id="test-customer-123",
        upgrade_order_id="test-order-456",
        amount=Decimal("75.00"),
        payment_method=PaymentMethod.CREDIT_CARD
    )
    
    print(f"   Transaction ID: {transaction.id}")
    print(f"   Status: {transaction.status}")
    print(f"   Amount: ${float(transaction.amount):.2f}")
    
    if transaction.status == PaymentStatus.FAILED:
        print(f"   Failure reason: {transaction.failure_reason}")
        
        # Test retry mechanism
        print(f"\n🔄 Testing retry mechanism...")
        retry_transaction = await gateway.retry_payment(transaction.id)
        print(f"   Retry status: {retry_transaction.status}")
        if retry_transaction.status == PaymentStatus.COMPLETED:
            print(f"   Gateway transaction ID: {retry_transaction.gateway_transaction_id}")
    
    # Show statistics
    stats = gateway.get_statistics()
    print(f"\n📊 Gateway Statistics:")
    print(f"   Total transactions: {stats['total_transactions']}")
    print(f"   Success rate: {stats['success_rate'] * 100:.1f}%")
    print(f"   Average amount: ${stats['average_amount']:.2f}")
    print(f"   Status breakdown: {stats['status_breakdown']}")


if __name__ == "__main__":
    asyncio.run(main())