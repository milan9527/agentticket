#!/usr/bin/env python3
"""
AgentCore-compatible Ticket Agent for Ticket Auto-Processing System

This agent is configured for deployment to AWS Bedrock AgentCore Runtime.
It handles ticket processing, upgrade workflows, and customer interactions using LLM reasoning.
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from uuid import UUID
import boto3
from botocore.exceptions import ClientError
import calendar

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.customer import Customer
from models.ticket import Ticket, TicketType, TicketStatus
from models.upgrade_order import UpgradeOrder, UpgradeTier, OrderStatus

# FastMCP imports for AgentCore
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


class TicketAgentConfig(BaseModel):
    """Configuration for the AgentCore Ticket Agent"""
    
    aws_region: str = Field(default="us-west-2", description="AWS region")
    bedrock_model_id: str = Field(..., description="Bedrock model ID for LLM reasoning")


class UpgradePricingEngine:
    """Handles upgrade pricing calculations and business logic"""
    
    # Upgrade tier pricing matrix
    UPGRADE_PRICING = {
        TicketType.GENERAL: {
            UpgradeTier.STANDARD: Decimal('25.00'),
            UpgradeTier.NON_STOP: Decimal('50.00'),
            UpgradeTier.DOUBLE_FUN: Decimal('75.00')
        },
        TicketType.STANDARD: {
            UpgradeTier.NON_STOP: Decimal('25.00'),
            UpgradeTier.DOUBLE_FUN: Decimal('50.00')
        },
        TicketType.VIP: {
            UpgradeTier.DOUBLE_FUN: Decimal('25.00')
        },
        TicketType.PREMIUM: {}  # Premium tickets cannot be upgraded
    }
    
    # Upgrade tier descriptions
    TIER_DESCRIPTIONS = {
        UpgradeTier.STANDARD: {
            "name": "Standard Upgrade",
            "description": "Enhanced experience with priority seating and complimentary refreshments",
            "features": ["Priority seating", "Complimentary drinks", "Fast-track entry"]
        },
        UpgradeTier.NON_STOP: {
            "name": "Non-Stop Experience",
            "description": "Premium experience with exclusive access and premium amenities",
            "features": ["VIP lounge access", "Premium seating", "Exclusive merchandise", "Meet & greet"]
        },
        UpgradeTier.DOUBLE_FUN: {
            "name": "Double Fun Package",
            "description": "Ultimate experience with all premium features and exclusive perks",
            "features": ["All Non-Stop features", "Backstage access", "Photo opportunities", "Premium gift package"]
        }
    }
    
    @classmethod
    def get_available_upgrades(cls, ticket_type: TicketType) -> List[Dict[str, Any]]:
        """Get available upgrade options for a ticket type"""
        available_upgrades = []
        
        if ticket_type in cls.UPGRADE_PRICING:
            for tier, price in cls.UPGRADE_PRICING[ticket_type].items():
                tier_info = cls.TIER_DESCRIPTIONS[tier].copy()
                tier_info['tier'] = tier
                tier_info['price'] = float(price)
                available_upgrades.append(tier_info)
        
        return available_upgrades
    
    @classmethod
    def calculate_upgrade_price(cls, ticket_type: TicketType, upgrade_tier: UpgradeTier) -> Optional[Decimal]:
        """Calculate upgrade price for a specific ticket type and tier"""
        if ticket_type in cls.UPGRADE_PRICING:
            return cls.UPGRADE_PRICING[ticket_type].get(upgrade_tier)
        return None


class UpgradeCalendarEngine:
    """Handles upgrade availability calendar and pricing display"""
    
    def __init__(self):
        self.base_pricing_multipliers = {
            'weekend': Decimal('1.2'),
            'peak': Decimal('1.5'),
            'off_peak': Decimal('0.9'),
            'standard': Decimal('1.0')
        }
    
    def get_pricing_for_date(self, target_date: date, ticket_type: TicketType, upgrade_tier: UpgradeTier) -> Dict[str, Any]:
        """Get specific pricing for a date and upgrade combination"""
        
        # Get base price
        base_price = UpgradePricingEngine.calculate_upgrade_price(ticket_type, upgrade_tier)
        if base_price is None:
            return {"error": "Upgrade not available for this ticket type"}
        
        # Apply calendar pricing
        pricing_category = self._get_pricing_category(target_date)
        multiplier = self.base_pricing_multipliers[pricing_category]
        calendar_price = base_price * multiplier
        
        # Check availability
        is_available = self._check_date_availability(target_date)
        
        return {
            "date": target_date.isoformat(),
            "ticket_type": ticket_type.value,
            "upgrade_tier": upgrade_tier.value,
            "is_available": is_available,
            "pricing": {
                "base_price": float(base_price),
                "calendar_price": float(calendar_price),
                "pricing_category": pricing_category,
                "multiplier": float(multiplier),
                "savings_vs_peak": float(calendar_price - (base_price * self.base_pricing_multipliers['peak']))
            },
            "tier_info": UpgradePricingEngine.TIER_DESCRIPTIONS[upgrade_tier]
        }
    
    def _get_pricing_category(self, target_date: date) -> str:
        """Determine pricing category for a given date"""
        
        # Weekend check (Friday, Saturday, Sunday)
        if target_date.weekday() >= 4:
            return 'weekend'
        
        # Peak season check (simulate holiday periods)
        month = target_date.month
        day = target_date.day
        
        # Holiday periods (simplified)
        peak_periods = [
            (12, 20, 12, 31),  # Christmas/New Year
            (7, 1, 7, 15),     # Summer peak
            (11, 20, 11, 30),  # Thanksgiving week
        ]
        
        for start_month, start_day, end_month, end_day in peak_periods:
            if (month == start_month and day >= start_day) or (month == end_month and day <= end_day):
                return 'peak'
        
        # Off-peak check (Tuesday, Wednesday in non-peak months)
        if target_date.weekday() in [1, 2] and month in [1, 2, 3, 9, 10]:
            return 'off_peak'
        
        return 'standard'
    
    def _check_date_availability(self, target_date: date) -> bool:
        """Check if upgrades are available on a specific date"""
        
        # No upgrades for past dates
        if target_date < date.today():
            return False
        
        # No upgrades within 24 hours
        if target_date <= date.today() + timedelta(days=1):
            return False
        
        # Simulate some blackout dates (e.g., maintenance days)
        if target_date.day == 15:
            return False
        
        return True


class LLMReasoningEngine:
    """Handles LLM reasoning for ticket processing and customer interactions"""
    
    def __init__(self, config: TicketAgentConfig):
        self.config = config
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=config.aws_region)
    
    async def reason_about_ticket_eligibility(self, ticket: Dict[str, Any], customer: Dict[str, Any]) -> str:
        """Use LLM to analyze ticket upgrade eligibility"""
        prompt = f"""
        Analyze ticket upgrade eligibility for the following scenario:
        
        Customer: {customer.get('first_name', '')} {customer.get('last_name', '')} ({customer.get('email', '')})
        Ticket: {ticket.get('ticket_number', '')} - {ticket.get('ticket_type', '')} 
        Original Price: ${ticket.get('original_price', 0)}
        Event Date: {ticket.get('event_date', '')}
        Status: {ticket.get('status', '')}
        Days Until Event: {ticket.get('days_until_event', 0)}
        
        Provide a detailed analysis of:
        1. Eligibility for upgrades
        2. Recommended upgrade tiers
        3. Any restrictions or considerations
        4. Customer communication suggestions
        """
        
        return await self._call_llm(prompt, {"operation": "ticket_eligibility", "ticket": ticket, "customer": customer})
    
    async def reason_about_upgrade_selection(self, ticket: Dict[str, Any], upgrade_options: List[Dict[str, Any]], customer_preferences: Dict[str, Any] = None) -> str:
        """Use LLM to provide upgrade recommendations"""
        prompt = f"""
        Help a customer choose the best upgrade option:
        
        Ticket Details:
        - Type: {ticket.get('ticket_type', '')}
        - Original Price: ${ticket.get('original_price', 0)}
        - Event Date: {ticket.get('event_date', '')}
        
        Available Upgrades:
        {json.dumps(upgrade_options, indent=2)}
        
        Customer Preferences: {json.dumps(customer_preferences or {}, indent=2)}
        
        Provide personalized recommendations including:
        1. Best value upgrade option
        2. Reasoning for each recommendation
        3. What the customer can expect from each tier
        4. Any special considerations
        """
        
        return await self._call_llm(prompt, {"operation": "upgrade_recommendation", "ticket": ticket, "options": upgrade_options})
    
    async def _call_llm(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Call Nova Pro model for reasoning"""
        try:
            system_prompt = """You are an expert ticket upgrade advisor with deep knowledge of event management, 
            customer service, and pricing strategies. You provide clear, actionable insights and recommendations 
            that help both customers and business operations."""
            
            full_prompt = f"{system_prompt}\n\nContext: {json.dumps(context) if context else 'None'}\n\nQuery: {prompt}"
            
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": full_prompt}]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 800,
                    "temperature": 0.3
                }
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.bedrock_runtime.invoke_model(
                    modelId=self.config.bedrock_model_id,
                    body=json.dumps(request_body)
                )
            )
            
            response_body = json.loads(response['body'].read())
            content_list = response_body.get('output', {}).get('message', {}).get('content', [])
            text_block = next((item for item in content_list if "text" in item), None)
            
            if text_block:
                return text_block.get('text', 'No response from LLM')
            else:
                return 'No response from LLM'
                
        except Exception as e:
            print(f"LLM reasoning error: {e}")
            return f"LLM reasoning failed: {str(e)}"


# Initialize FastMCP for AgentCore with stateless HTTP
mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# Global configuration and engines
config = None
llm = None
pricing = None
calendar_engine = None


async def call_data_agent_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Call Data Agent tool via MCP protocol"""
    try:
        # In a real AgentCore environment, this would use the MCP protocol to call the Data Agent
        # For local testing, we'll simulate the call by directly invoking the Data Agent functions
        
        print(f"🔧 Calling Data Agent tool: {tool_name} with params: {parameters}")
        
        if tool_name == "get_customer":
            customer_id = parameters.get("customer_id")
            if not customer_id:
                return {"error": "Missing customer_id parameter", "success": False}
            
            # Simulate Data Agent response for testing - provide realistic customer data
            return {
                "success": True,
                "customer": {
                    "id": customer_id,
                    "email": "test.customer@example.com",
                    "first_name": "Test",
                    "last_name": "Customer",
                    "phone": "+1-555-0123",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "reasoning": "Test customer data provided for validation"
            }
            
        elif tool_name == "get_tickets_for_customer":
            customer_id = parameters.get("customer_id")
            if not customer_id:
                return {"error": "Missing customer_id parameter", "success": False}
            
            # Simulate Data Agent response with realistic ticket data
            from datetime import datetime, timedelta
            event_date = (datetime.now() + timedelta(days=30)).isoformat()
            
            return {
                "success": True,
                "data": {
                    "tickets": [
                        {
                            "id": "test-ticket-789",
                            "customer_id": customer_id,
                            "ticket_number": "TKT-TEST789",
                            "ticket_type": "general",
                            "original_price": 50.00,
                            "purchase_date": "2024-01-01T00:00:00Z",
                            "event_date": event_date,
                            "status": "active",
                            "metadata": {},
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": "2024-01-01T00:00:00Z"
                        }
                    ]
                },
                "tickets": [
                    {
                        "id": "test-ticket-789",
                        "customer_id": customer_id,
                        "ticket_number": "TKT-TEST789",
                        "ticket_type": "general",
                        "original_price": 50.00,
                        "purchase_date": "2024-01-01T00:00:00Z",
                        "event_date": event_date,
                        "status": "active",
                        "metadata": {},
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z"
                    }
                ],
                "count": 1,
                "reasoning": "Test ticket data provided for validation"
            }
            
        elif tool_name == "create_upgrade_order":
            # Simulate successful order creation
            return {
                "success": True,
                "upgrade_order": {
                    "id": "test-order-123",
                    "status": "pending",
                    "total_amount": parameters.get("total_amount", 0),
                    "confirmation_code": "CONF12345678"
                },
                "reasoning": "Test upgrade order created successfully"
            }
            
        elif tool_name == "validate_data_integrity":
            # Simulate integrity check with realistic data
            return {
                "success": True,
                "integrity_results": {
                    "total_customers": 1,
                    "total_tickets": 1,
                    "total_upgrades": 0,
                    "orphaned_tickets": 0,
                    "orphaned_upgrades": 0
                },
                "reasoning": "Database integrity check completed - test data validated"
            }
        else:
            return {"error": f"Unknown Data Agent tool: {tool_name}", "success": False}
            
    except Exception as e:
        print(f"❌ Error calling Data Agent tool {tool_name}: {e}")
        return {"error": f"Failed to call Data Agent tool {tool_name}: {str(e)}", "success": False}


def load_config() -> TicketAgentConfig:
    """Load configuration from environment variables"""
    # Load from .env file if it exists
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    return TicketAgentConfig(
        aws_region=os.getenv('AWS_REGION', 'us-west-2'),
        bedrock_model_id=os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
    )


def initialize_agent():
    """Initialize the agent configuration and engines"""
    global config, llm, pricing, calendar_engine
    config = load_config()
    llm = LLMReasoningEngine(config)
    pricing = UpgradePricingEngine()
    calendar_engine = UpgradeCalendarEngine()


# MCP Tools for AgentCore
@mcp.tool()
async def validate_ticket_eligibility(ticket_id: str, customer_id: str = None) -> Dict[str, Any]:
    """Validate if a ticket is eligible for upgrades with LLM analysis - calls Data Agent for ticket data"""
    try:
        # Call Data Agent to get actual ticket data
        data_agent_result = await call_data_agent_tool("get_tickets_for_customer", {"customer_id": customer_id or "sample-customer-id"})
        
        if not data_agent_result.get("success"):
            return {
                "error": "Failed to retrieve ticket data from Data Agent", 
                "success": False,
                "data_source": "Data Agent (Error)"
            }
        
        # Find the specific ticket - check both data.tickets and tickets arrays
        tickets = data_agent_result.get("data", {}).get("tickets", [])
        if not tickets:
            tickets = data_agent_result.get("tickets", [])
        
        ticket_data = None
        for ticket in tickets:
            if ticket["id"] == ticket_id:
                ticket_data = ticket
                break
        
        if not ticket_data:
            # Ticket not found - this should be an error, not a fallback
            return {
                "success": False,
                "eligible": False,
                "error": f"Ticket {ticket_id} not found in our system",
                "ticket": None,
                "restrictions": ["Ticket ID not found", "Please verify your ticket number"],
                "data_source": "Data Agent (Ticket Not Found)"
            }
        
        # Get customer data
        customer_result = await call_data_agent_tool("get_customer", {"customer_id": customer_id or "sample-customer-id"})
        customer_data = customer_result.get("customer", {
            "id": customer_id or "sample-customer-id",
            "first_name": "Sample",
            "last_name": "Customer",
            "email": "sample@example.com"
        })
        
        # Calculate days until event
        try:
            event_date = datetime.fromisoformat(ticket_data["event_date"].replace('Z', '+00:00'))
            days_until_event = (event_date - datetime.now()).days
            ticket_data["days_until_event"] = days_until_event
        except:
            ticket_data["days_until_event"] = 30  # Default fallback
        
        # Check basic eligibility
        is_eligible = (
            ticket_data["status"] == "active" and
            ticket_data.get("days_until_event", 30) > 1 and
            ticket_data.get("ticket_type", "general") in ["general", "standard", "vip"]
        )
        
        # Get available upgrades
        ticket_type = TicketType(ticket_data.get("ticket_type", "general"))
        available_upgrades = pricing.get_available_upgrades(ticket_type)
        
        # Use LLM for detailed analysis
        llm_analysis = await llm.reason_about_ticket_eligibility(ticket_data, customer_data)
        
        return {
            "success": True,
            "eligible": is_eligible,
            "ticket": ticket_data,
            "customer": customer_data,
            "available_upgrades": available_upgrades,
            "eligibility_reasons": llm_analysis,
            "restrictions": [] if is_eligible else ["Event too soon", "Invalid ticket status", "No upgrades available"],
            "data_source": "Data Agent"
        }
        
    except Exception as e:
        return {"error": str(e), "success": False, "data_source": "Error"}


@mcp.tool()
async def calculate_upgrade_pricing(ticket_type: str, upgrade_tier: str, original_price: float = None) -> Dict[str, Any]:
    """Calculate upgrade pricing with detailed breakdown"""
    try:
        ticket_type_enum = TicketType(ticket_type.lower())
        upgrade_tier_enum = UpgradeTier(upgrade_tier.lower().replace(' ', '-').replace('_', '-'))
        
        # Calculate upgrade price
        upgrade_price = pricing.calculate_upgrade_price(ticket_type_enum, upgrade_tier_enum)
        
        if upgrade_price is None:
            return {
                "error": f"Upgrade from {ticket_type} to {upgrade_tier} not available",
                "success": False
            }
        
        original_price_decimal = Decimal(str(original_price)) if original_price else Decimal('50.00')
        total_price = original_price_decimal + upgrade_price
        
        # Get tier information
        tier_info = pricing.TIER_DESCRIPTIONS[upgrade_tier_enum]
        
        # Use LLM for pricing analysis
        pricing_context = {
            "ticket_type": ticket_type,
            "upgrade_tier": upgrade_tier,
            "original_price": float(original_price_decimal),
            "upgrade_price": float(upgrade_price),
            "total_price": float(total_price)
        }
        
        llm_analysis = await llm.reason_about_upgrade_selection(pricing_context, [tier_info])
        
        return {
            "success": True,
            "pricing": {
                "original_price": float(original_price_decimal),
                "upgrade_price": float(upgrade_price),
                "total_price": float(total_price),
                "savings_vs_new_ticket": float(upgrade_price * Decimal('0.2'))
            },
            "upgrade_info": tier_info,
            "pricing_analysis": llm_analysis
        }
        
    except ValueError as e:
        return {"error": f"Invalid ticket type or upgrade tier: {str(e)}", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool()
async def get_upgrade_recommendations(ticket_data: Dict[str, Any], customer_preferences: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get personalized upgrade recommendations using LLM"""
    try:
        ticket_type = TicketType(ticket_data.get("ticket_type", "general"))
        available_upgrades = pricing.get_available_upgrades(ticket_type)
        
        if not available_upgrades:
            return {
                "success": True,
                "recommendations": [],
                "message": "No upgrades available for this ticket type"
            }
        
        # Use LLM for personalized recommendations
        llm_recommendations = await llm.reason_about_upgrade_selection(
            ticket_data, 
            available_upgrades, 
            customer_preferences or {}
        )
        
        # Add pricing information to each upgrade
        for upgrade in available_upgrades:
            upgrade_tier = UpgradeTier(upgrade['tier'])
            upgrade_price = pricing.calculate_upgrade_price(ticket_type, upgrade_tier)
            original_price = Decimal(str(ticket_data.get('original_price', 50.0)))
            
            upgrade['pricing'] = {
                'upgrade_price': float(upgrade_price),
                'total_price': float(original_price + upgrade_price),
                'value_score': round(len(upgrade['features']) / float(upgrade_price) * 10, 2)
            }
        
        return {
            "success": True,
            "recommendations": available_upgrades,
            "personalized_advice": llm_recommendations,
            "best_value": max(available_upgrades, key=lambda x: x['pricing']['value_score'])
        }
        
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool()
async def get_upgrade_tier_comparison(ticket_type: str, selected_date: str = None) -> Dict[str, Any]:
    """Get comparison of all three upgrade tiers (Standard, Non-stop, Double Fun)"""
    try:
        ticket_type_enum = TicketType(ticket_type.lower())
        
        if selected_date:
            comparison_date = date.fromisoformat(selected_date)
        else:
            comparison_date = date.today() + timedelta(days=7)
        
        available_upgrades = pricing.get_available_upgrades(ticket_type_enum)
        
        comparison = {
            "ticket_type": ticket_type,
            "comparison_date": comparison_date.isoformat(),
            "tiers": []
        }
        
        # Show all three tiers: Standard, Non-stop, Double Fun
        all_tiers = [UpgradeTier.STANDARD, UpgradeTier.NON_STOP, UpgradeTier.DOUBLE_FUN]
        
        for tier in all_tiers:
            tier_info = pricing.TIER_DESCRIPTIONS[tier].copy()
            
            # Check if this tier is available for this ticket type
            is_available = any(upgrade['tier'] == tier for upgrade in available_upgrades)
            
            if is_available:
                pricing_info = calendar_engine.get_pricing_for_date(comparison_date, ticket_type_enum, tier)
                tier_info.update({
                    "tier": tier.value,
                    "available": True,
                    "pricing": pricing_info.get('pricing', {}),
                    "value_score": round(len(tier_info['features']) / pricing_info.get('pricing', {}).get('calendar_price', 1) * 10, 2)
                })
            else:
                tier_info.update({
                    "tier": tier.value,
                    "available": False,
                    "reason": f"Not available for {ticket_type} tickets",
                    "pricing": None
                })
            
            comparison["tiers"].append(tier_info)
        
        # Add recommendation
        available_tiers = [tier for tier in comparison["tiers"] if tier["available"]]
        if available_tiers:
            best_value = max(available_tiers, key=lambda x: x.get("value_score", 0))
            comparison["recommended_tier"] = best_value["tier"]
            comparison["recommendation_reason"] = "Best value based on features and pricing"
        
        # Use LLM for recommendations
        llm_recommendations = await llm.reason_about_upgrade_selection(
            {"ticket_type": ticket_type, "event_date": comparison_date.isoformat()},
            comparison["tiers"],
            {"budget": "moderate"}
        )
        
        return {
            "success": True,
            "comparison": comparison,
            "llm_recommendations": llm_recommendations,
            "tier_count": len(comparison["tiers"]),
            "available_tiers": [tier["tier"] for tier in comparison["tiers"] if tier["available"]]
        }
        
    except ValueError as e:
        return {"error": f"Invalid input: {str(e)}", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool()
async def get_pricing_for_date(ticket_type: str, upgrade_tier: str, target_date: str) -> Dict[str, Any]:
    """Get specific pricing for a date and upgrade combination"""
    try:
        ticket_type_enum = TicketType(ticket_type.lower())
        upgrade_tier_enum = UpgradeTier(upgrade_tier.lower().replace(' ', '-').replace('_', '-'))
        date_obj = date.fromisoformat(target_date)
        
        pricing_result = calendar_engine.get_pricing_for_date(
            date_obj, ticket_type_enum, upgrade_tier_enum
        )
        
        if 'error' in pricing_result:
            return {"success": False, "error": pricing_result['error']}
        
        # Add LLM pricing analysis
        pricing_context = {
            "pricing": pricing_result,
            "date": target_date,
            "ticket_type": ticket_type,
            "upgrade_tier": upgrade_tier
        }
        
        llm_analysis = await llm.reason_about_upgrade_selection(pricing_context, [pricing_result])
        
        return {
            "success": True,
            "pricing": pricing_result,
            "pricing_analysis": llm_analysis
        }
        
    except ValueError as e:
        return {"error": f"Invalid input: {str(e)}", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


# Initialize the agent when the module is loaded
try:
    initialize_agent()
    print("✅ AgentCore Ticket Agent initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize AgentCore Ticket Agent: {e}")


if __name__ == "__main__":
    # Run the MCP server for AgentCore
    print("🎫 Starting AgentCore Ticket Agent MCP server on 0.0.0.0:8000")
    print("🎯 Available tools:")
    print("  - validate_ticket_eligibility: Check if ticket can be upgraded")
    print("  - calculate_upgrade_pricing: Calculate upgrade costs and breakdown")
    print("  - get_upgrade_recommendations: Get personalized upgrade suggestions")
    print("  - get_upgrade_tier_comparison: Compare all three upgrade tiers")
    print("  - get_pricing_for_date: Get specific pricing for date and upgrade")
    print("🎪 Upgrade Tiers: Standard, Non-stop, Double Fun")
    print("📅 Calendar: Dynamic pricing based on demand and seasonality")
    
    # For AgentCore, use streamable-http transport as required by AWS
    mcp.run(transport="streamable-http")