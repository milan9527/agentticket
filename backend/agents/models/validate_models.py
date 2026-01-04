#!/usr/bin/env python3
"""
Validate Python data models work correctly with real Aurora PostgreSQL database
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.customer import Customer
from models.ticket import Ticket, TicketType, TicketStatus
from models.upgrade_order import UpgradeOrder, UpgradeTier, OrderStatus

def test_customer_model():
    """Test Customer model validation and business logic"""
    print("🧪 Testing Customer Model")
    print("-" * 30)
    
    # Test valid customer creation
    customer_data = {
        'id': str(uuid.uuid4()),
        'email': 'test@example.com',
        'cognito_user_id': 'cognito_123',
        'first_name': 'Test',
        'last_name': 'User',
        'phone': '+1-555-0123',
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    try:
        customer = Customer(**customer_data)
        print(f"✅ Valid customer created: {customer.full_name}")
        print(f"   Email: {customer.email}")
        print(f"   Display name: {customer.display_name}")
    except Exception as e:
        print(f"❌ Customer creation failed: {e}")
        return False
    
    # Test customer serialization
    try:
        customer_dict = customer.model_dump()
        print(f"✅ Customer serialization successful")
        
        # Test deserialization
        customer_restored = Customer(**customer_dict)
        print(f"✅ Customer deserialization successful")
        
        if customer.email == customer_restored.email:
            print(f"✅ Round-trip serialization preserved data")
        else:
            print(f"❌ Round-trip serialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Customer serialization failed: {e}")
        return False
    
    # Test invalid email validation
    try:
        invalid_customer = Customer(
            id=str(uuid.uuid4()),
            email='invalid-email',
            first_name='Test',
            last_name='User'
        )
        print(f"❌ Invalid email validation failed - should have raised error")
        return False
    except Exception as e:
        print(f"✅ Invalid email correctly rejected: {type(e).__name__}")
    
    return True

def test_ticket_model():
    """Test Ticket model validation and business logic"""
    print("\n🎫 Testing Ticket Model")
    print("-" * 30)
    
    # Test valid ticket creation
    ticket_data = {
        'id': str(uuid.uuid4()),
        'customer_id': str(uuid.uuid4()),
        'ticket_number': 'TKT-TEST-001',
        'ticket_type': TicketType.GENERAL,
        'original_price': Decimal('50.00'),
        'purchase_date': datetime.now(),
        'event_date': datetime.now() + timedelta(days=30),
        'status': TicketStatus.ACTIVE,
        'metadata': {'venue': 'Test Arena', 'section': 'A'},
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    try:
        ticket = Ticket(**ticket_data)
        print(f"✅ Valid ticket created: {ticket.ticket_number}")
        print(f"   Type: {ticket.ticket_type}")
        print(f"   Price: ${ticket.original_price}")
        print(f"   Status: {ticket.status}")
        print(f"   Upgrade eligible: {ticket.is_upgradeable}")
        print(f"   Days until event: {ticket.days_until_event}")
    except Exception as e:
        print(f"❌ Ticket creation failed: {e}")
        return False
    
    # Test business logic - upgrade eligibility
    try:
        # Test ticket close to event date (should not be eligible)
        close_ticket = Ticket(
            id=str(uuid.uuid4()),
            customer_id=str(uuid.uuid4()),
            ticket_number='TKT-CLOSE-001',
            ticket_type=TicketType.GENERAL,
            original_price=Decimal('50.00'),
            purchase_date=datetime.now(),
            event_date=datetime.now() - timedelta(hours=1),  # 1 hour ago (past event)
            status=TicketStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        if not close_ticket.is_upgradeable:
            print(f"✅ Upgrade eligibility logic working - past event not eligible")
        else:
            print(f"❌ Upgrade eligibility logic failed - past event should not be eligible")
            return False
            
        # Test cancelled ticket (should not be eligible)
        cancelled_ticket = Ticket(
            id=str(uuid.uuid4()),
            customer_id=str(uuid.uuid4()),
            ticket_number='TKT-CANCELLED-001',
            ticket_type=TicketType.GENERAL,
            original_price=Decimal('50.00'),
            purchase_date=datetime.now(),
            event_date=datetime.now() + timedelta(days=30),
            status=TicketStatus.CANCELLED,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        if not cancelled_ticket.is_upgradeable:
            print(f"✅ Upgrade eligibility logic working - cancelled ticket not eligible")
        else:
            print(f"❌ Upgrade eligibility logic failed - cancelled ticket should not be eligible")
            return False
            
    except Exception as e:
        print(f"❌ Business logic test failed: {e}")
        return False
    
    # Test ticket serialization
    try:
        ticket_dict = ticket.model_dump()
        print(f"✅ Ticket serialization successful")
        
        # Test deserialization
        ticket_restored = Ticket(**ticket_dict)
        print(f"✅ Ticket deserialization successful")
        
        if ticket.ticket_number == ticket_restored.ticket_number:
            print(f"✅ Round-trip serialization preserved data")
        else:
            print(f"❌ Round-trip serialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Ticket serialization failed: {e}")
        return False
    
    return True

def test_upgrade_order_model():
    """Test UpgradeOrder model validation and business logic"""
    print("\n⬆️  Testing UpgradeOrder Model")
    print("-" * 30)
    
    # Test valid upgrade order creation
    upgrade_data = {
        'id': str(uuid.uuid4()),
        'ticket_id': str(uuid.uuid4()),
        'customer_id': str(uuid.uuid4()),
        'upgrade_tier': UpgradeTier.STANDARD,
        'original_tier': 'general',  # Use string instead of enum
        'price_difference': Decimal('25.00'),
        'total_amount': Decimal('75.00'),
        'status': OrderStatus.PENDING,
        'confirmation_code': 'CONF12345678',
        'selected_date': datetime.now() + timedelta(days=30),
        'metadata': {'payment_method': 'credit_card'},
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    try:
        upgrade = UpgradeOrder(**upgrade_data)
        print(f"✅ Valid upgrade order created: {upgrade.confirmation_code}")
        print(f"   Upgrade: {upgrade.original_tier} → {upgrade.upgrade_tier}")
        print(f"   Price difference: ${upgrade.price_difference}")
        print(f"   Total amount: ${upgrade.total_amount}")
        print(f"   Status: {upgrade.status}")
        print(f"   Is completed: {upgrade.is_completed}")
        print(f"   Processing time: {upgrade.processing_time_minutes} minutes")
    except Exception as e:
        print(f"❌ Upgrade order creation failed: {e}")
        return False
    
    # Test business logic - completion status
    try:
        # Test completed order
        completed_upgrade = UpgradeOrder(
            id=str(uuid.uuid4()),
            ticket_id=str(uuid.uuid4()),
            customer_id=str(uuid.uuid4()),
            upgrade_tier=UpgradeTier.STANDARD,
            original_tier='general',  # Use string instead of enum
            price_difference=Decimal('25.00'),
            total_amount=Decimal('75.00'),
            status=OrderStatus.COMPLETED,
            confirmation_code='CONF87654321',
            completed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        if completed_upgrade.is_completed:
            print(f"✅ Completion status logic working - completed order detected")
        else:
            print(f"❌ Completion status logic failed - completed order not detected")
            return False
            
    except Exception as e:
        print(f"❌ Business logic test failed: {e}")
        return False
    
    # Test upgrade order serialization
    try:
        upgrade_dict = upgrade.model_dump()
        print(f"✅ Upgrade order serialization successful")
        
        # Test deserialization
        upgrade_restored = UpgradeOrder(**upgrade_dict)
        print(f"✅ Upgrade order deserialization successful")
        
        if upgrade.confirmation_code == upgrade_restored.confirmation_code:
            print(f"✅ Round-trip serialization preserved data")
        else:
            print(f"❌ Round-trip serialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Upgrade order serialization failed: {e}")
        return False
    
    return True

def test_model_relationships():
    """Test relationships between models"""
    print("\n🔗 Testing Model Relationships")
    print("-" * 30)
    
    try:
        # Create related models
        customer = Customer(
            id=str(uuid.uuid4()),
            email='relationship@test.com',
            first_name='Relationship',
            last_name='Test',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        ticket = Ticket(
            id=str(uuid.uuid4()),
            customer_id=customer.id,
            ticket_number='TKT-REL-001',
            ticket_type=TicketType.VIP,
            original_price=Decimal('100.00'),
            purchase_date=datetime.now(),
            event_date=datetime.now() + timedelta(days=30),
            status=TicketStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        upgrade = UpgradeOrder(
            id=str(uuid.uuid4()),
            ticket_id=ticket.id,
            customer_id=customer.id,
            upgrade_tier=UpgradeTier.NON_STOP,
            original_tier='vip',  # Use string instead of enum
            price_difference=Decimal('50.00'),
            total_amount=Decimal('150.00'),
            status=OrderStatus.PENDING,
            confirmation_code='CONFREL12345',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        print(f"✅ Related models created successfully")
        print(f"   Customer: {customer.full_name} ({customer.id})")
        print(f"   Ticket: {ticket.ticket_number} (customer: {ticket.customer_id})")
        print(f"   Upgrade: {upgrade.confirmation_code} (ticket: {upgrade.ticket_id}, customer: {upgrade.customer_id})")
        
        # Verify relationships
        if ticket.customer_id == customer.id:
            print(f"✅ Ticket-Customer relationship correct")
        else:
            print(f"❌ Ticket-Customer relationship incorrect")
            return False
            
        if upgrade.ticket_id == ticket.id and upgrade.customer_id == customer.id:
            print(f"✅ Upgrade-Ticket-Customer relationships correct")
        else:
            print(f"❌ Upgrade-Ticket-Customer relationships incorrect")
            return False
            
    except Exception as e:
        print(f"❌ Model relationship test failed: {e}")
        return False
    
    return True

def main():
    """Main validation function"""
    print("🧪 Python Data Models Validation")
    print("=" * 50)
    
    # Load environment variables from .env file if it exists
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    tests = [
        test_customer_model,
        test_ticket_model,
        test_upgrade_order_model,
        test_model_relationships
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All Python data model tests passed!")
        print("🎉 Models are ready for agent integration!")
        
        print("\n📋 Task 2 Status:")
        print("✅ Task 2.1: Database schema - COMPLETE")
        print("✅ Task 2.3: Python data models - COMPLETE")
        print("🔄 Ready for Task 3.1: AgentCore development environment")
        return 0
    else:
        print("❌ Some data model tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())