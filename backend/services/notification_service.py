#!/usr/bin/env python3
"""
Email Notification Service for Ticket Auto-Processing System

This service handles email notifications for payment confirmations, upgrade confirmations,
error notifications, and other customer communications.
"""

import os
import sys
import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from enum import Enum
import boto3
from botocore.exceptions import ClientError

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pydantic import BaseModel, Field, EmailStr


class NotificationType(str, Enum):
    """Notification types"""
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    UPGRADE_CONFIRMATION = "upgrade_confirmation"
    UPGRADE_CANCELLED = "upgrade_cancelled"
    REFUND_PROCESSED = "refund_processed"
    SYSTEM_ERROR = "system_error"
    WELCOME = "welcome"
    REMINDER = "reminder"


class NotificationStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"
    DELIVERED = "delivered"


class EmailTemplate(BaseModel):
    """Email template model"""
    
    type: NotificationType
    subject: str
    html_body: str
    text_body: str
    variables: List[str] = Field(default_factory=list, description="Template variables")


class NotificationRecord(BaseModel):
    """Notification record model"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str = Field(..., description="Customer ID")
    email: EmailStr = Field(..., description="Recipient email")
    notification_type: NotificationType = Field(..., description="Notification type")
    subject: str = Field(..., description="Email subject")
    status: NotificationStatus = Field(default=NotificationStatus.PENDING)
    template_data: Dict[str, Any] = Field(default_factory=dict, description="Template variables")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")
    delivered_at: Optional[datetime] = Field(None, description="Delivered timestamp")
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NotificationServiceConfig(BaseModel):
    """Configuration for the Notification Service"""
    
    aws_region: str = Field(default="us-west-2", description="AWS region")
    from_email: str = Field(..., description="From email address")
    reply_to_email: Optional[str] = Field(None, description="Reply-to email address")
    enable_ses: bool = Field(default=False, description="Enable AWS SES for real emails")
    enable_logging: bool = Field(default=True, description="Enable notification logging")
    log_file: str = Field(default="notifications.log", description="Log file path")
    simulate_delivery: bool = Field(default=True, description="Simulate email delivery")
    delivery_delay_min: float = Field(default=0.5, description="Min delivery delay in seconds")
    delivery_delay_max: float = Field(default=2.0, description="Max delivery delay in seconds")


class NotificationService:
    """Email notification service with template system"""
    
    def __init__(self, config: NotificationServiceConfig):
        self.config = config
        self.notifications: Dict[str, NotificationRecord] = {}
        self.templates: Dict[NotificationType, EmailTemplate] = {}
        self._setup_logging()
        self._setup_templates()
        
        if config.enable_ses:
            self.ses_client = boto3.client('ses', region_name=config.aws_region)
    
    def _setup_logging(self):
        """Set up notification logging"""
        if self.config.enable_logging:
            import logging
            
            self.logger = logging.getLogger('NotificationService')
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
    
    def _setup_templates(self):
        """Set up email templates"""
        
        # Payment Success Template
        self.templates[NotificationType.PAYMENT_SUCCESS] = EmailTemplate(
            type=NotificationType.PAYMENT_SUCCESS,
            subject="Payment Confirmation - Ticket Upgrade Successful",
            html_body="""
            <html>
            <body>
                <h2>Payment Confirmation</h2>
                <p>Dear {customer_name},</p>
                <p>Your payment has been successfully processed for your ticket upgrade!</p>
                
                <h3>Payment Details:</h3>
                <ul>
                    <li><strong>Transaction ID:</strong> {transaction_id}</li>
                    <li><strong>Amount:</strong> ${amount}</li>
                    <li><strong>Payment Method:</strong> {payment_method}</li>
                    <li><strong>Date:</strong> {payment_date}</li>
                </ul>
                
                <h3>Upgrade Details:</h3>
                <ul>
                    <li><strong>Ticket Number:</strong> {ticket_number}</li>
                    <li><strong>Original Type:</strong> {original_type}</li>
                    <li><strong>Upgraded To:</strong> {upgrade_tier}</li>
                    <li><strong>Event Date:</strong> {event_date}</li>
                </ul>
                
                <p>Your upgraded ticket is now active and ready for the event!</p>
                <p>Thank you for choosing our service.</p>
                
                <p>Best regards,<br>The Ticket System Team</p>
            </body>
            </html>
            """,
            text_body="""
            Payment Confirmation
            
            Dear {customer_name},
            
            Your payment has been successfully processed for your ticket upgrade!
            
            Payment Details:
            - Transaction ID: {transaction_id}
            - Amount: ${amount}
            - Payment Method: {payment_method}
            - Date: {payment_date}
            
            Upgrade Details:
            - Ticket Number: {ticket_number}
            - Original Type: {original_type}
            - Upgraded To: {upgrade_tier}
            - Event Date: {event_date}
            
            Your upgraded ticket is now active and ready for the event!
            Thank you for choosing our service.
            
            Best regards,
            The Ticket System Team
            """,
            variables=["customer_name", "transaction_id", "amount", "payment_method", 
                      "payment_date", "ticket_number", "original_type", "upgrade_tier", "event_date"]
        )
        
        # Payment Failed Template
        self.templates[NotificationType.PAYMENT_FAILED] = EmailTemplate(
            type=NotificationType.PAYMENT_FAILED,
            subject="Payment Failed - Ticket Upgrade",
            html_body="""
            <html>
            <body>
                <h2>Payment Failed</h2>
                <p>Dear {customer_name},</p>
                <p>We were unable to process your payment for the ticket upgrade.</p>
                
                <h3>Payment Details:</h3>
                <ul>
                    <li><strong>Transaction ID:</strong> {transaction_id}</li>
                    <li><strong>Amount:</strong> ${amount}</li>
                    <li><strong>Payment Method:</strong> {payment_method}</li>
                    <li><strong>Failure Reason:</strong> {failure_reason}</li>
                </ul>
                
                <h3>Next Steps:</h3>
                <p>Please try again with a different payment method or contact your bank if the issue persists.</p>
                <p>You can retry your upgrade by visiting our website or contacting customer support.</p>
                
                <p>If you need assistance, please contact us at support@ticket-system.com</p>
                
                <p>Best regards,<br>The Ticket System Team</p>
            </body>
            </html>
            """,
            text_body="""
            Payment Failed
            
            Dear {customer_name},
            
            We were unable to process your payment for the ticket upgrade.
            
            Payment Details:
            - Transaction ID: {transaction_id}
            - Amount: ${amount}
            - Payment Method: {payment_method}
            - Failure Reason: {failure_reason}
            
            Next Steps:
            Please try again with a different payment method or contact your bank if the issue persists.
            You can retry your upgrade by visiting our website or contacting customer support.
            
            If you need assistance, please contact us at support@ticket-system.com
            
            Best regards,
            The Ticket System Team
            """,
            variables=["customer_name", "transaction_id", "amount", "payment_method", "failure_reason"]
        )
        
        # Upgrade Confirmation Template
        self.templates[NotificationType.UPGRADE_CONFIRMATION] = EmailTemplate(
            type=NotificationType.UPGRADE_CONFIRMATION,
            subject="Ticket Upgrade Confirmed",
            html_body="""
            <html>
            <body>
                <h2>Ticket Upgrade Confirmed</h2>
                <p>Dear {customer_name},</p>
                <p>Your ticket upgrade has been confirmed and is now active!</p>
                
                <h3>Upgrade Details:</h3>
                <ul>
                    <li><strong>Ticket Number:</strong> {ticket_number}</li>
                    <li><strong>Original Type:</strong> {original_type}</li>
                    <li><strong>Upgraded To:</strong> {upgrade_tier}</li>
                    <li><strong>Event Date:</strong> {event_date}</li>
                    <li><strong>Total Price:</strong> ${total_price}</li>
                </ul>
                
                <h3>What's Included:</h3>
                <ul>
                    {upgrade_features}
                </ul>
                
                <p>Please bring this confirmation and a valid ID to the event.</p>
                <p>We look forward to seeing you there!</p>
                
                <p>Best regards,<br>The Ticket System Team</p>
            </body>
            </html>
            """,
            text_body="""
            Ticket Upgrade Confirmed
            
            Dear {customer_name},
            
            Your ticket upgrade has been confirmed and is now active!
            
            Upgrade Details:
            - Ticket Number: {ticket_number}
            - Original Type: {original_type}
            - Upgraded To: {upgrade_tier}
            - Event Date: {event_date}
            - Total Price: ${total_price}
            
            What's Included:
            {upgrade_features}
            
            Please bring this confirmation and a valid ID to the event.
            We look forward to seeing you there!
            
            Best regards,
            The Ticket System Team
            """,
            variables=["customer_name", "ticket_number", "original_type", "upgrade_tier", 
                      "event_date", "total_price", "upgrade_features"]
        )
        
        # System Error Template
        self.templates[NotificationType.SYSTEM_ERROR] = EmailTemplate(
            type=NotificationType.SYSTEM_ERROR,
            subject="System Error - We're Looking Into It",
            html_body="""
            <html>
            <body>
                <h2>System Error Notification</h2>
                <p>Dear {customer_name},</p>
                <p>We encountered a technical issue while processing your request.</p>
                
                <h3>Error Details:</h3>
                <ul>
                    <li><strong>Error ID:</strong> {error_id}</li>
                    <li><strong>Time:</strong> {error_time}</li>
                    <li><strong>Operation:</strong> {operation}</li>
                </ul>
                
                <p>Our technical team has been notified and is working to resolve this issue.</p>
                <p>We will contact you once the issue is resolved.</p>
                
                <p>We apologize for any inconvenience caused.</p>
                
                <p>Best regards,<br>The Ticket System Team</p>
            </body>
            </html>
            """,
            text_body="""
            System Error Notification
            
            Dear {customer_name},
            
            We encountered a technical issue while processing your request.
            
            Error Details:
            - Error ID: {error_id}
            - Time: {error_time}
            - Operation: {operation}
            
            Our technical team has been notified and is working to resolve this issue.
            We will contact you once the issue is resolved.
            
            We apologize for any inconvenience caused.
            
            Best regards,
            The Ticket System Team
            """,
            variables=["customer_name", "error_id", "error_time", "operation"]
        )
    
    async def send_notification(self,
                              customer_id: str,
                              email: str,
                              notification_type: NotificationType,
                              template_data: Dict[str, Any]) -> NotificationRecord:
        """Send a notification email"""
        
        # Get template
        if notification_type not in self.templates:
            raise ValueError(f"Template not found for notification type: {notification_type}")
        
        template = self.templates[notification_type]
        
        # Create notification record
        notification = NotificationRecord(
            customer_id=customer_id,
            email=email,
            notification_type=notification_type,
            subject=self._render_template(template.subject, template_data),
            template_data=template_data
        )
        
        # Store notification
        self.notifications[notification.id] = notification
        
        # Log notification start
        if self.config.enable_logging:
            self.logger.info(f"Sending notification: {notification.id} - {notification_type} to {email}")
        
        try:
            # Render email content
            html_body = self._render_template(template.html_body, template_data)
            text_body = self._render_template(template.text_body, template_data)
            
            if self.config.enable_ses:
                # Send via AWS SES
                await self._send_via_ses(notification, html_body, text_body)
            else:
                # Simulate email sending
                await self._simulate_email_sending(notification)
            
            # Update notification status
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now()
            
            if self.config.enable_logging:
                self.logger.info(f"Notification sent: {notification.id}")
            
            # Simulate delivery confirmation
            if self.config.simulate_delivery:
                await self._simulate_delivery_confirmation(notification)
            
            return notification
            
        except Exception as e:
            # Handle sending errors
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            
            if self.config.enable_logging:
                self.logger.error(f"Notification failed: {notification.id} - {str(e)}")
            
            return notification
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Render template with data"""
        try:
            return template.format(**data)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")
    
    async def _send_via_ses(self, notification: NotificationRecord, html_body: str, text_body: str):
        """Send email via AWS SES"""
        
        destination = {
            'ToAddresses': [notification.email]
        }
        
        message = {
            'Subject': {
                'Data': notification.subject,
                'Charset': 'UTF-8'
            },
            'Body': {
                'Html': {
                    'Data': html_body,
                    'Charset': 'UTF-8'
                },
                'Text': {
                    'Data': text_body,
                    'Charset': 'UTF-8'
                }
            }
        }
        
        source = self.config.from_email
        
        # Send email
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.ses_client.send_email(
                Source=source,
                Destination=destination,
                Message=message
            )
        )
        
        # Store SES message ID
        notification.template_data['ses_message_id'] = response['MessageId']
    
    async def _simulate_email_sending(self, notification: NotificationRecord):
        """Simulate email sending with delay"""
        import random
        
        # Simulate sending delay
        delay = random.uniform(
            self.config.delivery_delay_min,
            self.config.delivery_delay_max
        )
        await asyncio.sleep(delay)
        
        # Simulate occasional failures (5% failure rate)
        if random.random() < 0.05:
            raise Exception("Simulated email sending failure")
    
    async def _simulate_delivery_confirmation(self, notification: NotificationRecord):
        """Simulate delivery confirmation"""
        import random
        
        # Simulate delivery delay
        delivery_delay = random.uniform(1.0, 5.0)
        await asyncio.sleep(delivery_delay)
        
        # Simulate delivery confirmation (95% success rate)
        if random.random() < 0.95:
            notification.status = NotificationStatus.DELIVERED
            notification.delivered_at = datetime.now()
            
            if self.config.enable_logging:
                self.logger.info(f"Notification delivered: {notification.id}")
        else:
            notification.status = NotificationStatus.BOUNCED
            notification.error_message = "Email bounced"
            
            if self.config.enable_logging:
                self.logger.warning(f"Notification bounced: {notification.id}")
    
    async def get_notification(self, notification_id: str) -> Optional[NotificationRecord]:
        """Get notification by ID"""
        return self.notifications.get(notification_id)
    
    async def get_notifications_by_customer(self, customer_id: str) -> List[NotificationRecord]:
        """Get all notifications for a customer"""
        return [
            notification for notification in self.notifications.values()
            if notification.customer_id == customer_id
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get notification service statistics"""
        total_notifications = len(self.notifications)
        
        if total_notifications == 0:
            return {
                "total_notifications": 0,
                "delivery_rate": 0.0,
                "status_breakdown": {},
                "type_breakdown": {}
            }
        
        delivered_count = sum(1 for n in self.notifications.values() if n.status == NotificationStatus.DELIVERED)
        
        status_breakdown = {}
        for status in NotificationStatus:
            count = sum(1 for n in self.notifications.values() if n.status == status)
            status_breakdown[status.value] = count
        
        type_breakdown = {}
        for notification_type in NotificationType:
            count = sum(1 for n in self.notifications.values() if n.notification_type == notification_type)
            type_breakdown[notification_type.value] = count
        
        return {
            "total_notifications": total_notifications,
            "delivery_rate": delivered_count / total_notifications if total_notifications > 0 else 0.0,
            "status_breakdown": status_breakdown,
            "type_breakdown": type_breakdown
        }


def load_config() -> NotificationServiceConfig:
    """Load configuration from environment variables"""
    # Load from .env file if it exists
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    return NotificationServiceConfig(
        aws_region=os.getenv('AWS_REGION', 'us-west-2'),
        from_email=os.getenv('EMAIL_FROM', 'noreply@ticket-system.com'),
        reply_to_email=os.getenv('EMAIL_REPLY_TO'),
        enable_ses=os.getenv('ENABLE_SES', 'false').lower() == 'true',
        enable_logging=os.getenv('NOTIFICATION_LOGGING', 'true').lower() == 'true',
        log_file=os.getenv('NOTIFICATION_LOG_FILE', 'notifications.log'),
        simulate_delivery=os.getenv('SIMULATE_DELIVERY', 'true').lower() == 'true',
        delivery_delay_min=float(os.getenv('NOTIFICATION_DELAY_MIN', '0.5')),
        delivery_delay_max=float(os.getenv('NOTIFICATION_DELAY_MAX', '2.0'))
    )


# Example usage and testing
async def main():
    """Example usage of the Notification Service"""
    print("📧 Email Notification Service Test")
    print("=" * 40)
    
    # Load configuration
    config = load_config()
    service = NotificationService(config)
    
    print(f"✅ Notification Service initialized")
    print(f"   From email: {config.from_email}")
    print(f"   SES enabled: {config.enable_ses}")
    print(f"   Simulate delivery: {config.simulate_delivery}")
    
    # Test payment success notification
    print(f"\n📧 Testing payment success notification...")
    
    template_data = {
        "customer_name": "John Doe",
        "transaction_id": "txn_123456789",
        "amount": "75.00",
        "payment_method": "Credit Card",
        "payment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ticket_number": "TKT-TEST-001",
        "original_type": "General Admission",
        "upgrade_tier": "Standard Upgrade",
        "event_date": "2026-02-15 19:00:00"
    }
    
    notification = await service.send_notification(
        customer_id="test-customer-123",
        email="john.doe@example.com",
        notification_type=NotificationType.PAYMENT_SUCCESS,
        template_data=template_data
    )
    
    print(f"   Notification ID: {notification.id}")
    print(f"   Status: {notification.status}")
    print(f"   Subject: {notification.subject}")
    
    # Test payment failed notification
    print(f"\n❌ Testing payment failed notification...")
    
    failed_template_data = {
        "customer_name": "Jane Smith",
        "transaction_id": "txn_987654321",
        "amount": "50.00",
        "payment_method": "Debit Card",
        "failure_reason": "Insufficient funds"
    }
    
    failed_notification = await service.send_notification(
        customer_id="test-customer-456",
        email="jane.smith@example.com",
        notification_type=NotificationType.PAYMENT_FAILED,
        template_data=failed_template_data
    )
    
    print(f"   Notification ID: {failed_notification.id}")
    print(f"   Status: {failed_notification.status}")
    print(f"   Subject: {failed_notification.subject}")
    
    # Wait for delivery simulation
    print(f"\n⏳ Waiting for delivery simulation...")
    await asyncio.sleep(6)
    
    # Show statistics
    stats = service.get_statistics()
    print(f"\n📊 Notification Statistics:")
    print(f"   Total notifications: {stats['total_notifications']}")
    print(f"   Delivery rate: {stats['delivery_rate'] * 100:.1f}%")
    print(f"   Status breakdown: {stats['status_breakdown']}")
    print(f"   Type breakdown: {stats['type_breakdown']}")


if __name__ == "__main__":
    asyncio.run(main())