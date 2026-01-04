#!/usr/bin/env python3
"""
Working Chat Handler Lambda Function

Handles natural language chat for ticket upgrades with authentication and fallback responses.
Uses existing AgentCore ticket handler Lambda for validation and operations.
"""

import json
import os
import boto3
from typing import Dict, Any, List

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for AI chat
    """
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    try:
        # Handle preflight OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Verify authentication
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Missing or invalid authorization header'})
            }
        
        # For now, accept any Bearer token (we can add proper verification later)
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        if not token:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid token'})
            }
        
        # Parse request body
        if 'body' not in event or not event['body']:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing request body'})
            }
        
        body = json.loads(event['body'])
        message = body.get('message', '')
        conversation_history = body.get('conversationHistory', [])
        chat_context = body.get('context', {})
        
        if not message:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Message is required'})
            }
        
        # Generate AI response using intelligent pattern matching
        ai_response = generate_intelligent_response(message, conversation_history, chat_context, auth_header)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'response': ai_response['response'],
                'showUpgradeButtons': ai_response.get('show_upgrade_buttons', False),
                'upgradeOptions': ai_response.get('upgrade_options', [])
            })
        }
        
    except Exception as e:
        print(f"Chat error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'error': 'Internal server error'
            })
        }


def generate_intelligent_response(message: str, conversation_history: List, chat_context: Dict, auth_header: str) -> Dict[str, Any]:
    """Generate responses by delegating ALL processing to ticket handler Lambda - no AI chat responses"""
    message_lower = message.lower()
    
    # Check if user has selected an upgrade (from context) - PRIORITY CHECK
    if chat_context.get('selectedUpgrade'):
        selected = chat_context['selectedUpgrade']
        ticket_id = extract_ticket_id_from_context(chat_context, message)
        
        if ticket_id:
            # Delegate upgrade processing to ticket handler Lambda
            upgrade_result = process_upgrade_with_ticket_handler(ticket_id, selected, auth_header)
            return format_upgrade_response(selected, upgrade_result)
        else:
            return {
                "response": f"I'd love to help you with the {selected['name']} upgrade, but I need your ticket ID first. Please provide your ticket number so I can process the upgrade.",
                "show_upgrade_buttons": False,
                "upgrade_options": []
            }
    
    # Check if user is selecting an upgrade by typing upgrade names
    # Look for ticket ID from conversation history or context
    ticket_id = extract_ticket_id_from_context(chat_context, message)
    if not ticket_id:
        # Check conversation history for previously mentioned ticket ID
        for msg in conversation_history[-10:]:  # Check last 10 messages
            if msg.get('role') == 'user':
                potential_ticket = extract_ticket_id_from_context({}, msg.get('content', ''))
                if potential_ticket:
                    ticket_id = potential_ticket
                    break
    
    # Detect upgrade selection from message text
    selected_upgrade = detect_upgrade_selection_from_message(message)
    if selected_upgrade and ticket_id:
        print(f"Chat handler detected upgrade selection: '{selected_upgrade['name']}' for ticket: '{ticket_id}'")
        # Delegate upgrade processing to ticket handler Lambda
        upgrade_result = process_upgrade_with_ticket_handler(ticket_id, selected_upgrade, auth_header)
        return format_upgrade_response(selected_upgrade, upgrade_result)
    elif selected_upgrade and not ticket_id:
        return {
            "response": f"I'd love to help you with the {selected_upgrade['name']} upgrade! However, I need your ticket ID first to process this upgrade. Could you please provide your ticket number?",
            "show_upgrade_buttons": False,
            "upgrade_options": []
        }
    
    # Check if message contains a ticket ID (for initial ticket recognition)
    if ticket_id and not any(word in message_lower for word in ['no', 'not interested', 'maybe later', 'not now']):
        # Delegate ticket validation to ticket handler Lambda
        validation_result = validate_ticket_with_ticket_handler(ticket_id, auth_header)
        return format_ticket_validation_response(ticket_id, validation_result)
    
    # For messages WITHOUT ticket ID - guide user to provide ticket ID for proper delegation
    print(f"Chat handler: No ticket ID found, guiding user to provide ticket ID for delegation")
    
    # Check if user is asking about upgrades but hasn't provided ticket ID
    asking_about_upgrades = any(word in message_lower for word in [
        'upgrade', 'options', 'available', 'seat', 'class', 'premium', 'vip'
    ])
    
    if asking_about_upgrades:
        return {
            "response": "I can help you with ticket upgrades! To get started and process your request through our system, please provide your ticket ID. Once I have your ticket ID, I'll validate it through our AgentCore system and show you the available upgrade options.",
            "show_upgrade_buttons": False,
            "upgrade_options": []
        }
    
    # For general greetings or inquiries - guide to provide ticket ID
    if any(word in message_lower for word in ['hello', 'hi', 'hey', 'help']):
        return {
            "response": "Hello! I'm your ticket assistant. I can help you with ticket upgrades and services. To get started, please provide your ticket ID so I can process your request through our AgentCore system.",
            "show_upgrade_buttons": False,
            "upgrade_options": []
        }
    
    # Default - always guide to provide ticket ID for proper delegation
    return {
        "response": "I'm here to help with your ticket needs. Please provide your ticket ID so I can process your request through our AgentCore system and give you the most accurate information.",
        "show_upgrade_buttons": False,
        "upgrade_options": []
    }


def validate_ticket_with_ticket_handler(ticket_id: str, auth_header: str) -> Dict[str, Any]:
    """Delegate ticket validation to ticket handler Lambda - pass raw ticket ID"""
    try:
        import urllib3
        import json as json_lib
        
        api_base_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
        
        print(f"Chat handler delegating ticket validation for raw ID: '{ticket_id}' to ticket handler Lambda")
        
        # Create HTTP pool manager with SSL verification disabled for Lambda environment
        http = urllib3.PoolManager(
            cert_reqs='CERT_NONE',
            assert_hostname=False
        )
        
        # Disable SSL warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Prepare request data for ticket handler - pass raw ticket ID
        payload = {
            'upgrade_tier': 'Standard Upgrade'  # Use standard tier for validation
        }
        
        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        
        print(f"Making request to: {api_base_url}/tickets/{ticket_id}/validate")
        print(f"Auth header: {auth_header[:50]}...{auth_header[-20:]}")
        
        # Call ticket handler Lambda for validation - pass raw ticket ID in URL
        response = http.request(
            'POST',
            f'{api_base_url}/tickets/{ticket_id}/validate',
            body=json_lib.dumps(payload),
            headers=headers,
            timeout=10.0
        )
        
        print(f"Ticket handler response status: {response.status}")
        
        if response.status == 200:
            result = json_lib.loads(response.data.decode('utf-8'))
            print(f"Ticket handler validation result: {result}")
            return result
        else:
            error_data = response.data.decode('utf-8') if response.data else 'No response data'
            print(f"Ticket handler validation failed: {response.status} - {error_data}")
            return {
                'success': False,
                'error': f'Ticket validation failed with status {response.status}',
                'details': error_data
            }
            
    except Exception as e:
        print(f"Ticket validation delegation error: {e}")
        return {
            'success': False,
            'error': f'Unable to validate ticket: {str(e)}'
        }


def process_upgrade_with_ticket_handler(ticket_id: str, selected_upgrade: Dict, auth_header: str) -> Dict[str, Any]:
    """Delegate upgrade processing to ticket handler Lambda"""
    try:
        import urllib3
        import json as json_lib
        
        api_base_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
        
        print(f"Chat handler delegating upgrade processing for ticket: '{ticket_id}', upgrade: '{selected_upgrade['name']}'")
        
        # Create HTTP pool manager with SSL verification disabled for Lambda environment
        http = urllib3.PoolManager(
            cert_reqs='CERT_NONE',
            assert_hostname=False
        )
        
        # Disable SSL warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Prepare request data for ticket handler
        payload = {
            'upgrade_tier': selected_upgrade.get('name', 'Standard Upgrade')
        }
        
        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        
        print(f"Making upgrade request to: {api_base_url}/tickets/{ticket_id}/validate")
        print(f"Auth header: {auth_header[:50]}...{auth_header[-20:]}")
        
        # Call ticket handler Lambda for upgrade processing
        response = http.request(
            'POST',
            f'{api_base_url}/tickets/{ticket_id}/validate',
            body=json_lib.dumps(payload),
            headers=headers,
            timeout=10.0
        )
        
        print(f"Ticket handler upgrade response status: {response.status}")
        
        if response.status == 200:
            result = json_lib.loads(response.data.decode('utf-8'))
            print(f"Ticket handler upgrade result: {result}")
            return result
        else:
            error_data = response.data.decode('utf-8') if response.data else 'No response data'
            print(f"Ticket handler upgrade failed: {response.status} - {error_data}")
            return {
                'success': False,
                'error': f'Upgrade processing failed with status {response.status}',
                'details': error_data
            }
            
    except Exception as e:
        print(f"Upgrade processing delegation error: {e}")
        return {
            'success': False,
            'error': f'Unable to process upgrade: {str(e)}'
        }


def format_ticket_validation_response(ticket_id: str, validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """Format response based on ticket validation result from ticket handler"""
    if validation_result.get('success') and validation_result.get('data'):
        ticket_info = validation_result['data']
        
        if ticket_info.get('eligible'):
            current_tier = ticket_info.get('current_tier', 'your current')
            return {
                "response": f"Perfect! I can see your ticket ({ticket_id}). You currently have a {current_tier} ticket and it's verified and eligible for upgrades! There are several upgrade options available that could enhance your experience significantly. Would you like to see what upgrades are available?",
                "show_upgrade_buttons": True,
                "upgrade_options": get_upgrade_options()
            }
        else:
            reason = ticket_info.get('reason', 'Ticket validation failed')
            return {
                "response": f"I checked your ticket ID '{ticket_id}' with our system, but there's an issue: {reason}. Please double-check your ticket number or contact support for assistance.",
                "show_upgrade_buttons": False,
                "upgrade_options": []
            }
    else:
        error_msg = validation_result.get('error', 'Unable to validate ticket')
        # Handle specific case where ticket is not found
        if 'not found' in error_msg.lower() or 'invalid' in error_msg.lower():
            return {
                "response": f"I checked your ticket ID '{ticket_id}' with our system, but it doesn't appear to be valid or found in our database. Please double-check your ticket number - it might be a different format or you may need to contact support for assistance.",
                "show_upgrade_buttons": False,
                "upgrade_options": []
            }
        else:
            return {
                "response": f"I tried to validate your ticket ID '{ticket_id}', but encountered an issue: {error_msg}. Please try again or contact support for assistance.",
                "show_upgrade_buttons": False,
                "upgrade_options": []
            }


def format_upgrade_response(selected_upgrade: Dict, upgrade_result: Dict[str, Any]) -> Dict[str, Any]:
    """Format response based on upgrade processing result from ticket handler"""
    if upgrade_result.get('success') and upgrade_result.get('data'):
        ticket_info = upgrade_result['data']
        
        if ticket_info.get('eligible'):
            current_tier = ticket_info.get('current_tier', 'your current')
            return {
                "response": f"Perfect! You've selected the {selected_upgrade['name']} for ${selected_upgrade['price']}. This includes: {', '.join(selected_upgrade['features'])}. Your {current_tier} ticket has been validated and is eligible for this upgrade. To complete your upgrade, I'll process the payment and update your ticket. Your upgrade will be confirmed within 24 hours and you'll receive an email confirmation. Thank you for choosing to enhance your experience!",
                "show_upgrade_buttons": False,
                "upgrade_options": []
            }
        else:
            reason = ticket_info.get('reason', 'Upgrade validation failed')
            return {
                "response": f"I'd love to help you with the {selected_upgrade['name']} upgrade, but there's an issue: {reason} Please contact support for assistance.",
                "show_upgrade_buttons": False,
                "upgrade_options": []
            }
    else:
        error_msg = upgrade_result.get('error', 'Unable to process upgrade')
        return {
            "response": f"I'd love to help you with the {selected_upgrade['name']} upgrade, but there's an issue: {error_msg} Please contact support for assistance.",
            "show_upgrade_buttons": False,
            "upgrade_options": []
        }


def get_upgrade_options() -> List[Dict[str, Any]]:
    """Get the standard upgrade options"""
    return [
        {
            "id": "standard",
            "name": "Standard Upgrade",
            "price": 50,
            "features": ["Priority boarding", "Extra legroom", "Complimentary drink"],
            "description": "Enhanced comfort with priority perks"
        },
        {
            "id": "premium",
            "name": "Premium Experience", 
            "price": 150,
            "features": ["Premium seating", "Gourmet meal", "Fast track entry", "Lounge access"],
            "description": "Premium experience with exclusive amenities"
        },
        {
            "id": "vip",
            "name": "VIP Package",
            "price": 300,
            "features": ["VIP seating", "Meet & greet", "Exclusive merchandise", "Photo opportunities", "Backstage tour"],
            "description": "Ultimate VIP experience with exclusive access"
        }
    ]


def detect_upgrade_selection_from_message(message: str) -> Dict[str, Any]:
    """Detect if user is selecting an upgrade from their message text"""
    message_lower = message.lower().strip()
    
    # Get available upgrade options
    upgrade_options = get_upgrade_options()
    
    # Direct name matches
    for upgrade in upgrade_options:
        upgrade_name_lower = upgrade['name'].lower()
        if upgrade_name_lower in message_lower or message_lower in upgrade_name_lower:
            print(f"Direct upgrade match found: '{upgrade['name']}' from message: '{message}'")
            return upgrade
    
    # Keyword-based matching for common upgrade terms
    upgrade_keywords = {
        'standard': ['standard', 'basic', 'regular', 'normal'],
        'premium': ['premium', 'experience', 'better', 'enhanced'],
        'vip': ['vip', 'package', 'ultimate', 'exclusive', 'best']
    }
    
    # Map common user terms to our upgrade options
    user_term_mapping = {
        'seat upgrade': 'standard',  # Map "seat upgrade" to Standard Upgrade
        'seat': 'standard',
        'class upgrade': 'premium',
        'class': 'premium',
        'first class': 'vip',
        'business class': 'premium'
    }
    
    # Check user term mapping first
    for user_term, upgrade_id in user_term_mapping.items():
        if user_term in message_lower:
            for upgrade in upgrade_options:
                if upgrade['id'] == upgrade_id:
                    print(f"Mapped upgrade match: '{user_term}' -> '{upgrade['name']}' from message: '{message}'")
                    return upgrade
    
    # Check keyword matching
    for upgrade in upgrade_options:
        upgrade_id = upgrade['id']
        if upgrade_id in upgrade_keywords:
            keywords = upgrade_keywords[upgrade_id]
            if any(keyword in message_lower for keyword in keywords):
                print(f"Keyword upgrade match: '{upgrade['name']}' from message: '{message}'")
                return upgrade
    
    return None


def extract_ticket_id_from_context(chat_context: Dict, message: str) -> str:
    """Extract ticket ID from context or message - pass RAW values to ticket handler for validation"""
    # Check context first - handle multiple possible keys
    if chat_context.get('ticketId'):
        return chat_context['ticketId']
    
    # Check if there's a selectedUpgrade with ticket context
    if chat_context.get('selectedUpgrade') and chat_context.get('hasTicketInfo'):
        # Look for ticket ID in the conversation context
        if chat_context.get('ticketId'):
            return chat_context['ticketId']
    
    # Check for hasTicketInfo flag and try to find stored ticket ID
    if chat_context.get('hasTicketInfo') and chat_context.get('ticketId'):
        return chat_context['ticketId']
    
    # Look for ticket ID patterns in message - pass RAW values to ticket handler
    import re
    
    # UUID pattern (full UUIDs)
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    uuid_match = re.search(uuid_pattern, message.lower())
    if uuid_match:
        return uuid_match.group()
    
    # Ticket number pattern (TKT-XXXX format)
    ticket_pattern = r'TKT-\d{6}'
    ticket_match = re.search(ticket_pattern, message.upper())
    if ticket_match:
        return ticket_match.group()
    
    # Look for simple ticket patterns like "ticket 333", "ticket ID 123", etc.
    # CRITICAL: Pass RAW values (like "333") directly to ticket handler for validation
    # Do NOT do any mapping or validation here - let AgentCore handle it
    simple_ticket_patterns = [
        r'ticket\s+(\w+)',
        r'ticket\s+id\s+(\w+)', 
        r'ticket\s+number\s+(\w+)',
        r'my\s+ticket\s+is\s+(\w+)',
        r'ticket:\s*(\w+)',
        r'id\s+(\w+)',
        r'#(\w+)'
    ]
    
    for pattern in simple_ticket_patterns:
        match = re.search(pattern, message.lower())
        if match:
            # Return the RAW ticket ID exactly as user provided (e.g., "333")
            # Let ticket handler → AgentCore → Data Agent → Database validate it
            raw_ticket_id = match.group(1)
            print(f"Chat handler extracted raw ticket ID: '{raw_ticket_id}' - delegating to ticket handler for validation")
            return raw_ticket_id
    
    return None


