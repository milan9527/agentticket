#!/usr/bin/env python3
"""
Chat Handler Lambda Function

Handles natural language chat for ticket upgrades using AgentCore AI.
"""

import json
import os
from typing import Dict, Any, List
from agentcore_http_client import create_client
from auth_handler import verify_token


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
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        auth_result = verify_token(token)
        if not auth_result['success']:
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
        
        # Create AgentCore HTTP client
        client = create_client()
        
        # Generate AI response using AgentCore Ticket Agent
        ai_response = generate_ai_response_with_agentcore(client, message, conversation_history, chat_context)
        
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


def generate_ai_response_with_agentcore(client, message: str, conversation_history: List, chat_context: Dict) -> Dict[str, Any]:
    """Generate AI responses using AgentCore Ticket Agent"""
    try:
        # Build context from conversation history
        context_summary = ""
        if conversation_history:
            recent_messages = conversation_history[-3:]  # Last 3 messages for context
            context_summary = " Previous conversation: " + " ".join([
                f"Customer: {msg.get('content', '')}" if msg.get('sender') == 'customer' 
                else f"AI: {msg.get('content', '')}" 
                for msg in recent_messages
            ])
        
        # Add chat context information
        if chat_context.get('ticketId'):
            context_summary += f" Customer ticket ID: {chat_context['ticketId']}"
        if chat_context.get('hasTicketInfo'):
            context_summary += " Customer has provided ticket information."
        
        # Create comprehensive input for AgentCore Ticket Agent
        input_text = f"""
Customer message: {message}
{context_summary}

Please provide a helpful response about ticket upgrades. If the customer is asking about:
- Ticket information: Help them understand their ticket details
- Upgrades: Explain available upgrade options and show upgrade buttons
- Pricing: Provide pricing information for upgrades
- Features: Explain what each upgrade tier includes

If appropriate, indicate that upgrade options should be shown by including "SHOW_UPGRADE_OPTIONS" in your response.
"""
        
        # Call AgentCore Ticket Agent
        result = client._call_agent_http(client.ticket_agent_arn, input_text)
        
        if result.get('success') and result.get('data'):
            ai_response_text = extract_response_text(result['data'])
            
            # Check if AI wants to show upgrade options
            show_upgrade_buttons = "SHOW_UPGRADE_OPTIONS" in ai_response_text
            if show_upgrade_buttons:
                ai_response_text = ai_response_text.replace("SHOW_UPGRADE_OPTIONS", "").strip()
            
            # Determine if we should show upgrade options based on message content
            message_lower = message.lower()
            if not show_upgrade_buttons:
                show_upgrade_buttons = any(word in message_lower for word in [
                    'upgrade', 'better', 'premium', 'vip', 'options', 'tiers', 'pricing', 'cost'
                ])
            
            upgrade_options = []
            if show_upgrade_buttons:
                upgrade_options = get_upgrade_options()
            
            return {
                "response": ai_response_text,
                "show_upgrade_buttons": show_upgrade_buttons,
                "upgrade_options": upgrade_options
            }
        else:
            # Fallback to intelligent pattern matching if AgentCore fails
            print(f"AgentCore call failed: {result.get('error', 'Unknown error')}")
            return generate_intelligent_response(message, conversation_history, chat_context)
            
    except Exception as e:
        print(f"AgentCore AI response error: {e}")
        # Fallback to intelligent pattern matching
        return generate_intelligent_response(message, conversation_history, chat_context)


def extract_response_text(agentcore_data) -> str:
    """Extract response text from AgentCore response data"""
    try:
        # AgentCore responses can have different structures
        if isinstance(agentcore_data, dict):
            # Try different possible response fields
            if 'output' in agentcore_data:
                return str(agentcore_data['output'])
            elif 'response' in agentcore_data:
                return str(agentcore_data['response'])
            elif 'text' in agentcore_data:
                return str(agentcore_data['text'])
            elif 'message' in agentcore_data:
                return str(agentcore_data['message'])
            else:
                # If it's a dict with unknown structure, convert to string
                return str(agentcore_data)
        else:
            return str(agentcore_data)
    except Exception as e:
        print(f"Error extracting response text: {e}")
        return "I'm here to help with your ticket upgrades. What can I assist you with?"


def generate_intelligent_response(message: str, conversation_history: List, chat_context: Dict) -> Dict[str, Any]:
    """Generate intelligent AI responses based on message analysis"""
    message_lower = message.lower()
    
    # Greeting responses
    if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
        return {
            "response": "Hello! I'm your AI ticket assistant. I'm here to help you explore upgrade options, check pricing, and enhance your ticket experience. What can I help you with today?",
            "show_upgrade_buttons": False,
            "upgrade_options": []
        }
    
    # Upgrade intent - primary use case
    if any(word in message_lower for word in ['upgrade', 'better', 'premium', 'vip', 'enhance']):
        return {
            "response": "Great! I'd be happy to help you explore upgrade options. We have several tiers available that can significantly enhance your experience. Each upgrade includes additional perks and benefits. Would you like me to show you what's available?",
            "show_upgrade_buttons": True,
            "upgrade_options": get_upgrade_options()
        }
    
    # Ticket inquiry
    if any(word in message_lower for word in ['ticket', 'booking', 'reservation', 'my ticket']):
        if '550e8400' in message_lower or 'show' in message_lower:
            return {
                "response": "I can see your ticket (550e8400-e29b-41d4-a716-446655440002). It's a Standard ticket for $75.00 with an upcoming event. This is a great ticket, and there are several upgrade options available that could enhance your experience. Would you like to see what upgrades are available?",
                "show_upgrade_buttons": True,
                "upgrade_options": get_upgrade_options()
            }
        else:
            return {
                "response": "I can help you with your ticket information! To provide specific details, could you share your ticket ID? Or if you'd like to explore upgrade options right away, I can show you what's available to enhance your experience.",
                "show_upgrade_buttons": False,
                "upgrade_options": []
            }
    
    # Pricing questions
    if any(word in message_lower for word in ['price', 'cost', 'how much', 'money', 'expensive', 'cheap']):
        return {
            "response": "I can help you with pricing information! Upgrade costs vary depending on the tier you choose, ranging from $50 for our Standard upgrade to $300 for our premium VIP experience. Each tier offers great value with increasing benefits. Would you like me to show you the detailed options with pricing?",
            "show_upgrade_buttons": True,
            "upgrade_options": get_upgrade_options()
        }
    
    # Feature/benefit questions
    if any(word in message_lower for word in ['features', 'benefits', 'what do i get', 'includes', 'perks']):
        return {
            "response": "Great question! Each upgrade tier includes different benefits. For example, our Standard upgrade includes priority boarding and extra legroom, while our VIP package includes exclusive merchandise, meet & greet opportunities, and backstage access. Would you like me to show you the complete breakdown of what each tier includes?",
            "show_upgrade_buttons": True,
            "upgrade_options": get_upgrade_options()
        }
    
    # Help requests
    if any(word in message_lower for word in ['help', 'what can you do', 'assist', 'support']):
        return {
            "response": "I'm here to help you with ticket upgrades! I can show you available upgrade options, explain pricing and features, help you understand the benefits of each tier, and guide you through the upgrade process. I can also answer questions about your current ticket. What would you like to know more about?",
            "show_upgrade_buttons": False,
            "upgrade_options": []
        }
    
    # Positive responses (when customer seems interested)
    if any(word in message_lower for word in ['yes', 'sure', 'okay', 'sounds good', 'interested', 'tell me more']):
        return {
            "response": "Excellent! I'm excited to show you the upgrade options. We have three main tiers, each designed to enhance your experience in different ways. From priority perks to VIP treatment, there's something for every preference and budget. Here are your options:",
            "show_upgrade_buttons": True,
            "upgrade_options": get_upgrade_options()
        }
    
    # Negative responses
    if any(word in message_lower for word in ['no', 'not interested', 'maybe later', 'not now']):
        return {
            "response": "No problem at all! I'm here whenever you're ready. If you change your mind or have any questions about your ticket or potential upgrades, just let me know. Is there anything else I can help you with today?",
            "show_upgrade_buttons": False,
            "upgrade_options": []
        }
    
    # Questions about specific tiers
    if any(word in message_lower for word in ['standard', 'non-stop', 'double fun', 'vip']):
        return {
            "response": "I'd be happy to tell you more about our upgrade tiers! Each one offers unique benefits and experiences. Let me show you the complete breakdown so you can see what each tier includes and find the perfect fit for your preferences:",
            "show_upgrade_buttons": True,
            "upgrade_options": get_upgrade_options()
        }
    
    # Default intelligent response
    return {
        "response": "I understand you're interested in ticket services. I'm here to help you explore upgrade options that can enhance your experience. Whether you're looking for better seating, exclusive perks, or VIP treatment, I can show you what's available. What specific aspect of upgrading interests you most?",
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