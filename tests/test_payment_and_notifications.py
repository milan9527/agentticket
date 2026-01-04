#!/usr/bin/env python3
"""
Test script for Payment Gateway and Notification Service integration
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.payment_gateway import PaymentGateway, PaymentMethod, PaymentStatus, load_config as load_payment_config
from backend.services.notification_service import NotificationService, NotificationType, load_config as load_notification_config


class PaymentNotificationIntegration:
    """Integration between Payment Gateway and Notification Service"""
    
    def __init__(self):
        self.payment_gateway = None
        self.notification_service = None
    
    async def setup_services(self):
        """Set up both services"""
        print("🔧 Setting up Payment Gateway and Notification Service")
        
        # Load configurations
        payment_config = load_payment_config()
        notification_config = load_notification_config()
        
        print(f"✅ Payment Gateway config: Success rate {payment_config.success_rate * 100:.1f}%")
        print(f"✅ Notification Service config: From {notification_config.from_email}")
        
        # Create service instances
        self.payment_gateway = PaymentGateway(payment_config)
        self.notification_service = NotificationService(notification_config)
        
        return True
    
    async def process_payment_with_notifications(self,
                                               customer_id: str,
                                               customer_name: str,
                                               customer_email: str,
                                               upgrade_order_id: str,
                                               amount: Decimal,
                                               payment_method: PaymentMethod,
                                               ticket_data: dict) -> dict:
        """Process payment and send appropriate notifications"""
        
        print(f"\n💳 Processing payment for {customer_name} (${float(amount):.2f})")
        
        # Process payment
        transaction = await self.payment_gateway.process_payment(
            customer_id=customer_id,
            upgrade_order_id=upgrade_order_id,
            amount=amount,
            payment_method=payment_method
        )
        
        print(f"   Transaction ID: {transaction.id}")
        print(f"   Status: {transaction.status}")
        
        # Send notification based on payment result
        if transaction.status == PaymentStatus.COMPLETED:
            # Payment successful - send success notification
            template_data = {
                "customer_name": customer_name,
                "transaction_id": transaction.gateway_transaction_id,
                "amount": str(float(amount)),
                "payment_method": payment_method.value.replace('_', ' ').title(),
                "payment_date": transaction.completed_at.strftime("%Y-%m-%d %H:%M:%S"),
                "ticket_number": ticket_data.get("ticket_number", "N/A"),
                "original_type": ticket_data.get("original_type", "N/A"),
                "upgrade_tier": ticket_data.get("upgrade_tier", "N/A"),
                "event_date": ticket_data.get("event_date", "N/A")
            }
            
            notification = await self.notification_service.send_notification(
                customer_id=customer_id,
                email=customer_email,
                notification_type=NotificationType.PAYMENT_SUCCESS,
                template_data=template_data
            )
            
            print(f"   ✅ Success notification sent: {notification.id}")
            
        elif transaction.status == PaymentStatus.FAILED:
            # Payment failed - send failure notification
            template_data = {
                "customer_name": customer_name,
                "transaction_id": transaction.id,
                "amount": str(float(amount)),
                "payment_method": payment_method.value.replace('_', ' ').title(),
                "failure_reason": transaction.failure_reason or "Unknown error"
            }
            
            notification = await self.notification_service.send_notification(
                customer_id=customer_id,
                email=customer_email,
                notification_type=NotificationType.PAYMENT_FAILED,
                template_data=template_data
            )
            
            print(f"   ❌ Failure notification sent: {notification.id}")
            
            # Try to retry payment
            if transaction.retry_count < self.payment_gateway.config.max_retry_attempts:
                print(f"   🔄 Attempting payment retry...")
                
                retry_transaction = await self.payment_gateway.retry_payment(transaction.id)
                
                if retry_transaction.status == PaymentStatus.COMPLETED:
                    # Retry successful - send success notification
                    template_data = {
                        "customer_name": customer_name,
                        "transaction_id": retry_transaction.gateway_transaction_id,
                        "amount": str(float(amount)),
                        "payment_method": payment_method.value.replace('_', ' ').title(),
                        "payment_date": retry_transaction.completed_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "ticket_number": ticket_data.get("ticket_number", "N/A"),
                        "original_type": ticket_data.get("original_type", "N/A"),
                        "upgrade_tier": ticket_data.get("upgrade_tier", "N/A"),
                        "event_date": ticket_data.get("event_date", "N/A")
                    }
                    
                    success_notification = await self.notification_service.send_notification(
                        customer_id=customer_id,
                        email=customer_email,
                        notification_type=NotificationType.PAYMENT_SUCCESS,
                        template_data=template_data
                    )
                    
                    print(f"   ✅ Retry success notification sent: {success_notification.id}")
                    transaction = retry_transaction
                else:
                    print(f"   ❌ Payment retry also failed: {retry_transaction.failure_reason}")
        
        return {
            "transaction": transaction,
            "payment_successful": transaction.status == PaymentStatus.COMPLETED
        }
    
    async def send_upgrade_confirmation(self,
                                      customer_id: str,
                                      customer_name: str,
                                      customer_email: str,
                                      ticket_data: dict) -> dict:
        """Send upgrade confirmation notification"""
        
        print(f"\n🎫 Sending upgrade confirmation to {customer_name}")
        
        # Format upgrade features
        features = ticket_data.get("upgrade_features", [])
        if isinstance(features, list):
            upgrade_features = "\n".join([f"- {feature}" for feature in features])
        else:
            upgrade_features = str(features)
        
        template_data = {
            "customer_name": customer_name,
            "ticket_number": ticket_data.get("ticket_number", "N/A"),
            "original_type": ticket_data.get("original_type", "N/A"),
            "upgrade_tier": ticket_data.get("upgrade_tier", "N/A"),
            "event_date": ticket_data.get("event_date", "N/A"),
            "total_price": str(ticket_data.get("total_price", "0.00")),
            "upgrade_features": upgrade_features
        }
        
        notification = await self.notification_service.send_notification(
            customer_id=customer_id,
            email=customer_email,
            notification_type=NotificationType.UPGRADE_CONFIRMATION,
            template_data=template_data
        )
        
        print(f"   ✅ Upgrade confirmation sent: {notification.id}")
        
        return {"notification": notification}
    
    async def handle_system_error(self,
                                customer_id: str,
                                customer_name: str,
                                customer_email: str,
                                error_details: dict) -> dict:
        """Handle system errors with notifications"""
        
        print(f"\n⚠️ Handling system error for {customer_name}")
        
        template_data = {
            "customer_name": customer_name,
            "error_id": error_details.get("error_id", "ERR-" + str(datetime.now().timestamp())),
            "error_time": error_details.get("error_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "operation": error_details.get("operation", "Unknown operation")
        }
        
        notification = await self.notification_service.send_notification(
            customer_id=customer_id,
            email=customer_email,
            notification_type=NotificationType.SYSTEM_ERROR,
            template_data=template_data
        )
        
        print(f"   ✅ Error notification sent: {notification.id}")
        
        return {"notification": notification}


async def test_payment_notification_integration():
    """Test the complete payment and notification workflow"""
    print("🚀 Payment Gateway & Notification Service Integration Test")
    print("=" * 60)
    
    integration = PaymentNotificationIntegration()
    
    try:
        # Setup services
        if not await integration.setup_services():
            print("❌ Service setup failed")
            return False
        
        # Test data
        test_customers = [
            {
                "customer_id": "cust-001",
                "customer_name": "Alice Johnson",
                "customer_email": "alice.johnson@example.com",
                "upgrade_order_id": "order-001",
                "amount": Decimal("75.00"),
                "payment_method": PaymentMethod.CREDIT_CARD,
                "ticket_data": {
                    "ticket_number": "TKT-ALICE-001",
                    "original_type": "General Admission",
                    "upgrade_tier": "Standard Upgrade",
                    "event_date": "2026-03-15 19:00:00",
                    "total_price": "75.00",
                    "upgrade_features": [
                        "Priority seating",
                        "Complimentary drinks",
                        "Fast-track entry"
                    ]
                }
            },
            {
                "customer_id": "cust-002",
                "customer_name": "Bob Smith",
                "customer_email": "bob.smith@example.com",
                "upgrade_order_id": "order-002",
                "amount": Decimal("100.00"),
                "payment_method": PaymentMethod.DEBIT_CARD,
                "ticket_data": {
                    "ticket_number": "TKT-BOB-002",
                    "original_type": "General Admission",
                    "upgrade_tier": "Non-Stop Experience",
                    "event_date": "2026-03-15 19:00:00",
                    "total_price": "100.00",
                    "upgrade_features": [
                        "VIP lounge access",
                        "Premium seating",
                        "Exclusive merchandise",
                        "Meet & greet"
                    ]
                }
            },
            {
                "customer_id": "cust-003",
                "customer_name": "Carol Davis",
                "customer_email": "carol.davis@example.com",
                "upgrade_order_id": "order-003",
                "amount": Decimal("125.00"),
                "payment_method": PaymentMethod.PAYPAL,
                "ticket_data": {
                    "ticket_number": "TKT-CAROL-003",
                    "original_type": "Standard",
                    "upgrade_tier": "Double Fun Package",
                    "event_date": "2026-03-15 19:00:00",
                    "total_price": "125.00",
                    "upgrade_features": [
                        "All Non-Stop features",
                        "Backstage access",
                        "Photo opportunities",
                        "Premium gift package"
                    ]
                }
            }
        ]
        
        successful_payments = 0
        failed_payments = 0
        
        # Process payments for all test customers
        for customer in test_customers:
            result = await integration.process_payment_with_notifications(
                customer_id=customer["customer_id"],
                customer_name=customer["customer_name"],
                customer_email=customer["customer_email"],
                upgrade_order_id=customer["upgrade_order_id"],
                amount=customer["amount"],
                payment_method=customer["payment_method"],
                ticket_data=customer["ticket_data"]
            )
            
            if result["payment_successful"]:
                successful_payments += 1
                
                # Send upgrade confirmation for successful payments
                await integration.send_upgrade_confirmation(
                    customer_id=customer["customer_id"],
                    customer_name=customer["customer_name"],
                    customer_email=customer["customer_email"],
                    ticket_data=customer["ticket_data"]
                )
            else:
                failed_payments += 1
        
        # Test system error notification
        await integration.handle_system_error(
            customer_id="cust-error",
            customer_name="Error Test User",
            customer_email="error@example.com",
            error_details={
                "error_id": "ERR-TEST-001",
                "error_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "operation": "ticket_upgrade_processing"
            }
        )
        
        # Wait for all notifications to be processed
        print(f"\n⏳ Waiting for notification delivery simulation...")
        await asyncio.sleep(8)
        
        # Show statistics
        print(f"\n📊 Integration Test Results:")
        print(f"   Successful payments: {successful_payments}")
        print(f"   Failed payments: {failed_payments}")
        print(f"   Total customers processed: {len(test_customers)}")
        
        # Payment gateway statistics
        payment_stats = integration.payment_gateway.get_statistics()
        print(f"\n💳 Payment Gateway Statistics:")
        print(f"   Total transactions: {payment_stats['total_transactions']}")
        print(f"   Success rate: {payment_stats['success_rate'] * 100:.1f}%")
        print(f"   Average amount: ${payment_stats['average_amount']:.2f}")
        print(f"   Status breakdown: {payment_stats['status_breakdown']}")
        
        # Notification service statistics
        notification_stats = integration.notification_service.get_statistics()
        print(f"\n📧 Notification Service Statistics:")
        print(f"   Total notifications: {notification_stats['total_notifications']}")
        print(f"   Delivery rate: {notification_stats['delivery_rate'] * 100:.1f}%")
        print(f"   Status breakdown: {notification_stats['status_breakdown']}")
        print(f"   Type breakdown: {notification_stats['type_breakdown']}")
        
        print(f"\n" + "=" * 60)
        print(f"✅ Payment and Notification Integration Test Completed!")
        print(f"🎉 Services are working together seamlessly!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_payment_notification_integration()
    return 0 if success else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))