#!/usr/bin/env python3
"""
Ticket Agent for Ticket Auto-Processing System

This agent handles ticket processing, upgrade workflows, and customer interactions using LLM reasoning.
It provides ticket validation, upgrade calculations, and customer guidance through fastMCP.
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

# FastMCP imports
from fastmcp import FastMCP
from pydantic import BaseModel, Field


class TicketAgentConfig(BaseModel):
    """Configuration for the Ticket Agent"""
    
    aws_region: str = Field(default="us-west-2", description="AWS region")
    bedrock_model_id: str = Field(..., description="Bedrock model ID for LLM reasoning")
    data_agent_url: str = Field(default="http://localhost:8001", description="Data Agent MCP server URL")


class UpgradeCalendarEngine:
    """Handles upgrade availability calendar and pricing display"""
    
    def __init__(self):
        self.base_pricing_multipliers = {
            # Weekend pricing (Friday-Sunday)
            'weekend': Decimal('1.2'),
            # Peak season (holidays, special events)
            'peak': Decimal('1.5'),
            # Off-peak (weekdays, low demand)
            'off_peak': Decimal('0.9'),
            # Standard (regular weekdays)
            'standard': Decimal('1.0')
        }
    
    def generate_availability_calendar(self, 
                                     start_date: date = None, 
                                     days_ahead: int = 90,
                                     ticket_type: TicketType = None) -> Dict[str, Any]:
        """Generate availability calendar with pricing for upgrade options"""
        
        if start_date is None:
            start_date = date.today()
        
        calendar_data = {
            "start_date": start_date.isoformat(),
            "end_date": (start_date + timedelta(days=days_ahead)).isoformat(),
            "days_ahead": days_ahead,
            "availability": [],
            "pricing_legend": {
                "standard": "Regular pricing",
                "weekend": "+20% weekend premium",
                "peak": "+50% peak season",
                "off_peak": "-10% off-peak discount"
            }
        }
        
        # Generate daily availability and pricing
        for day_offset in range(days_ahead):
            current_date = start_date + timedelta(days=day_offset)
            
            # Determine pricing category
            pricing_category = self._get_pricing_category(current_date)
            multiplier = self.base_pricing_multipliers[pricing_category]
            
            # Check availability (simulate based on date)
            is_available = self._check_date_availability(current_date)
            
            # Get upgrade options with calendar pricing
            upgrade_options = []
            if ticket_type and is_available:
                base_upgrades = UpgradePricingEngine.get_available_upgrades(ticket_type)
                
                for upgrade in base_upgrades:
                    calendar_price = Decimal(str(upgrade['price'])) * multiplier
                    upgrade_with_calendar_pricing = upgrade.copy()
                    upgrade_with_calendar_pricing.update({
                        'calendar_price': float(calendar_price),
                        'base_price': upgrade['price'],
                        'pricing_category': pricing_category,
                        'price_multiplier': float(multiplier),
                        'savings_vs_peak': float(calendar_price - (Decimal(str(upgrade['price'])) * self.base_pricing_multipliers['peak']))
                    })
                    upgrade_options.append(upgrade_with_calendar_pricing)
            
            day_data = {
                "date": current_date.isoformat(),
                "day_of_week": current_date.strftime("%A"),
                "is_available": is_available,
                "pricing_category": pricing_category,
                "price_multiplier": float(multiplier),
                "upgrade_options": upgrade_options,
                "availability_reason": self._get_availability_reason(current_date, is_available)
            }
            
            calendar_data["availability"].append(day_data)
        
        return calendar_data
    
    def get_pricing_for_date(self, 
                           target_date: date, 
                           ticket_type: TicketType, 
                           upgrade_tier: UpgradeTier) -> Dict[str, Any]:
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
    
    def get_best_pricing_dates(self, 
                             ticket_type: TicketType, 
                             upgrade_tier: UpgradeTier,
                             days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Find the best pricing dates for an upgrade within the next N days"""
        
        start_date = date.today()
        best_dates = []
        
        for day_offset in range(days_ahead):
            current_date = start_date + timedelta(days=day_offset)
            pricing_info = self.get_pricing_for_date(current_date, ticket_type, upgrade_tier)
            
            if pricing_info.get("is_available"):
                best_dates.append({
                    "date": current_date.isoformat(),
                    "day_of_week": current_date.strftime("%A"),
                    "price": pricing_info["pricing"]["calendar_price"],
                    "category": pricing_info["pricing"]["pricing_category"],
                    "savings": pricing_info["pricing"]["savings_vs_peak"]
                })
        
        # Sort by price (best deals first)
        best_dates.sort(key=lambda x: x["price"])
        
        return best_dates[:10]  # Return top 10 best deals
    
    def _get_pricing_category(self, target_date: date) -> str:
        """Determine pricing category for a given date"""
        
        # Weekend check (Friday, Saturday, Sunday)
        if target_date.weekday() >= 4:  # 4=Friday, 5=Saturday, 6=Sunday
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
        if target_date.weekday() in [1, 2] and month in [1, 2, 3, 9, 10]:  # Jan, Feb, Mar, Sep, Oct
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
        # For demo purposes, make every 15th of the month unavailable
        if target_date.day == 15:
            return False
        
        return True
    
    def _get_availability_reason(self, target_date: date, is_available: bool) -> str:
        """Get human-readable reason for availability status"""
        
        if not is_available:
            if target_date < date.today():
                return "Past date - upgrades not available"
            elif target_date <= date.today() + timedelta(days=1):
                return "Too close to event - upgrades require 48+ hours notice"
            elif target_date.day == 15:
                return "System maintenance day - upgrades unavailable"
            else:
                return "Upgrades not available for this date"
        
        return "Upgrades available"


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
    
    @classmethod
    def calculate_total_price(cls, original_price: Decimal, upgrade_price: Decimal) -> Decimal:
        """Calculate total price including upgrade"""
        return original_price + upgrade_price


class UpgradeSelectionProcessor:
    """Handles upgrade selection processing workflow"""
    
    def __init__(self, pricing_engine: UpgradePricingEngine, calendar_engine: UpgradeCalendarEngine):
        self.pricing_engine = pricing_engine
        self.calendar_engine = calendar_engine
    
    async def process_upgrade_selection(self, 
                                      selection_data: Dict[str, Any],
                                      customer_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process complete upgrade selection workflow"""
        
        try:
            # Extract selection details
            ticket_type = TicketType(selection_data.get('ticket_type', 'general'))
            upgrade_tier = UpgradeTier(selection_data.get('upgrade_tier', 'standard'))
            selected_date = date.fromisoformat(selection_data.get('selected_date', date.today().isoformat()))
            original_price = Decimal(str(selection_data.get('original_price', 50.0)))
            
            # Validate selection
            validation_result = await self._validate_selection(
                ticket_type, upgrade_tier, selected_date, customer_context
            )
            
            if not validation_result['is_valid']:
                return {
                    "success": False,
                    "error": "Selection validation failed",
                    "validation_errors": validation_result['errors'],
                    "suggested_alternatives": validation_result.get('alternatives', [])
                }
            
            # Calculate final pricing
            pricing_result = self.calendar_engine.get_pricing_for_date(
                selected_date, ticket_type, upgrade_tier
            )
            
            if 'error' in pricing_result:
                return {
                    "success": False,
                    "error": pricing_result['error']
                }
            
            # Calculate totals
            upgrade_price = Decimal(str(pricing_result['pricing']['calendar_price']))
            total_price = original_price + upgrade_price
            
            # Generate selection summary
            selection_summary = {
                "selection_id": f"SEL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "ticket_details": {
                    "type": ticket_type.value,
                    "original_price": float(original_price)
                },
                "upgrade_details": {
                    "tier": upgrade_tier.value,
                    "tier_name": self.pricing_engine.TIER_DESCRIPTIONS[upgrade_tier]['name'],
                    "features": self.pricing_engine.TIER_DESCRIPTIONS[upgrade_tier]['features'],
                    "selected_date": selected_date.isoformat(),
                    "day_of_week": selected_date.strftime("%A")
                },
                "pricing_breakdown": {
                    "original_ticket_price": float(original_price),
                    "base_upgrade_price": pricing_result['pricing']['base_price'],
                    "calendar_upgrade_price": pricing_result['pricing']['calendar_price'],
                    "pricing_category": pricing_result['pricing']['pricing_category'],
                    "total_price": float(total_price),
                    "savings_vs_peak": pricing_result['pricing']['savings_vs_peak']
                },
                "next_steps": [
                    "Review upgrade details",
                    "Proceed to payment",
                    "Receive confirmation email"
                ]
            }
            
            return {
                "success": True,
                "selection_summary": selection_summary,
                "validation_result": validation_result,
                "ready_for_payment": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Selection processing failed: {str(e)}"
            }
    
    async def _validate_selection(self, 
                                ticket_type: TicketType, 
                                upgrade_tier: UpgradeTier, 
                                selected_date: date,
                                customer_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate upgrade selection against business rules"""
        
        errors = []
        warnings = []
        alternatives = []
        
        # Check if upgrade tier is available for ticket type
        available_upgrades = self.pricing_engine.get_available_upgrades(ticket_type)
        available_tiers = [UpgradeTier(upgrade['tier']) for upgrade in available_upgrades]
        
        if upgrade_tier not in available_tiers:
            errors.append(f"Upgrade to {upgrade_tier.value} not available for {ticket_type.value} tickets")
            alternatives.extend([
                {"tier": tier.value, "name": self.pricing_engine.TIER_DESCRIPTIONS[tier]['name']}
                for tier in available_tiers
            ])
        
        # Check date availability
        if not self.calendar_engine._check_date_availability(selected_date):
            errors.append(f"Upgrades not available on {selected_date.isoformat()}")
            
            # Suggest alternative dates
            best_dates = self.calendar_engine.get_best_pricing_dates(ticket_type, upgrade_tier, 14)
            alternatives.extend([
                {"type": "date", "date": date_info["date"], "price": date_info["price"]}
                for date_info in best_dates[:3]
            ])
        
        # Check timing constraints
        days_until_event = (selected_date - date.today()).days
        if days_until_event < 2:
            errors.append("Upgrades require at least 48 hours notice")
        elif days_until_event < 7:
            warnings.append("Upgrade processing may be expedited due to proximity to event")
        
        # Customer-specific validations
        if customer_context:
            # Check if customer has pending upgrades
            if customer_context.get('has_pending_upgrades'):
                warnings.append("You have other pending upgrade requests")
            
            # Check customer tier eligibility
            customer_tier = customer_context.get('customer_tier', 'standard')
            if customer_tier == 'vip' and upgrade_tier == UpgradeTier.STANDARD:
                warnings.append("As a VIP customer, you may prefer our premium upgrade options")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "alternatives": alternatives
        }
    
    def get_upgrade_tier_comparison(self, ticket_type: TicketType, selected_date: date = None) -> Dict[str, Any]:
        """Generate comparison of all three upgrade tiers for a ticket type"""
        
        if selected_date is None:
            selected_date = date.today() + timedelta(days=7)  # Default to next week
        
        available_upgrades = self.pricing_engine.get_available_upgrades(ticket_type)
        
        comparison = {
            "ticket_type": ticket_type.value,
            "comparison_date": selected_date.isoformat(),
            "tiers": []
        }
        
        # Ensure we show all three tiers: Standard, Non-stop, Double Fun
        all_tiers = [UpgradeTier.STANDARD, UpgradeTier.NON_STOP, UpgradeTier.DOUBLE_FUN]
        
        for tier in all_tiers:
            tier_info = self.pricing_engine.TIER_DESCRIPTIONS[tier].copy()
            
            # Check if this tier is available for this ticket type
            is_available = any(upgrade['tier'] == tier for upgrade in available_upgrades)
            
            if is_available:
                pricing_info = self.calendar_engine.get_pricing_for_date(selected_date, ticket_type, tier)
                tier_info.update({
                    "tier": tier.value,
                    "available": True,
                    "pricing": pricing_info.get('pricing', {}),
                    "value_score": self._calculate_tier_value_score(tier, pricing_info.get('pricing', {}).get('calendar_price', 0))
                })
            else:
                tier_info.update({
                    "tier": tier.value,
                    "available": False,
                    "reason": f"Not available for {ticket_type.value} tickets",
                    "pricing": None
                })
            
            comparison["tiers"].append(tier_info)
        
        # Add recommendation
        available_tiers = [tier for tier in comparison["tiers"] if tier["available"]]
        if available_tiers:
            best_value = max(available_tiers, key=lambda x: x.get("value_score", 0))
            comparison["recommended_tier"] = best_value["tier"]
            comparison["recommendation_reason"] = f"Best value based on features and pricing"
        
        return comparison
    
    def _calculate_tier_value_score(self, tier: UpgradeTier, price: float) -> float:
        """Calculate value score for tier comparison"""
        feature_weights = {
            UpgradeTier.STANDARD: 3,
            UpgradeTier.NON_STOP: 5,
            UpgradeTier.DOUBLE_FUN: 8
        }
        
        if price <= 0:
            return 0
        
        weight = feature_weights.get(tier, 1)
        return round(weight / price * 100, 2)


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
    
    async def reason_about_customer_interaction(self, conversation_context: Dict[str, Any], customer_query: str) -> str:
        """Use LLM to handle customer interactions and queries"""
        prompt = f"""
        You are a helpful ticket upgrade assistant. A customer has asked: "{customer_query}"
        
        Context:
        {json.dumps(conversation_context, indent=2)}
        
        Provide a helpful, friendly response that:
        1. Addresses their specific question
        2. Provides relevant information about their tickets/upgrades
        3. Suggests next steps if appropriate
        4. Maintains a professional but warm tone
        """
        
        return await self._call_llm(prompt, {"operation": "customer_interaction", "query": customer_query, "context": conversation_context})
    
    async def reason_about_pricing_strategy(self, ticket: Dict[str, Any], market_conditions: Dict[str, Any] = None) -> str:
        """Use LLM to analyze pricing strategy and recommendations"""
        prompt = f"""
        Analyze pricing strategy for ticket upgrade:
        
        Ticket Information:
        {json.dumps(ticket, indent=2)}
        
        Market Conditions:
        {json.dumps(market_conditions or {}, indent=2)}
        
        Provide analysis on:
        1. Pricing competitiveness
        2. Value proposition for each upgrade tier
        3. Potential demand factors
        4. Revenue optimization suggestions
        """
        
        return await self._call_llm(prompt, {"operation": "pricing_strategy", "ticket": ticket, "market": market_conditions})
    
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


class TicketAgent:
    """Main Ticket Agent class with LLM reasoning and business logic"""
    
    def __init__(self, config: TicketAgentConfig):
        self.config = config
        self.llm = LLMReasoningEngine(config)
        self.pricing = UpgradePricingEngine()
        self.calendar = UpgradeCalendarEngine()
        self.selection_processor = UpgradeSelectionProcessor(self.pricing, self.calendar)
        self.app = FastMCP("TicketAgent")
        self._setup_tools()
    
    def _setup_tools(self):
        """Set up MCP tools for the Ticket Agent"""
        
        @self.app.tool()
        async def validate_ticket_eligibility(ticket_id: str, customer_id: str = None) -> Dict[str, Any]:
            """Validate if a ticket is eligible for upgrades with LLM analysis"""
            try:
                # This would normally call the Data Agent to get ticket and customer info
                # For now, we'll simulate the data structure
                
                # Simulate ticket data (in production, this would come from Data Agent)
                ticket_data = {
                    "id": ticket_id,
                    "ticket_number": f"TKT-{ticket_id[:8].upper()}",
                    "ticket_type": "general",
                    "original_price": 50.00,
                    "event_date": (datetime.now() + timedelta(days=30)).isoformat(),
                    "status": "active",
                    "days_until_event": 30,
                    "is_upgradeable": True
                }
                
                customer_data = {
                    "id": customer_id or "sample-customer-id",
                    "first_name": "Sample",
                    "last_name": "Customer",
                    "email": "sample@example.com"
                }
                
                # Check basic eligibility
                is_eligible = (
                    ticket_data["status"] == "active" and
                    ticket_data["days_until_event"] > 1 and
                    ticket_data["ticket_type"] in ["general", "standard", "vip"]
                )
                
                # Get available upgrades
                ticket_type = TicketType(ticket_data["ticket_type"])
                available_upgrades = self.pricing.get_available_upgrades(ticket_type)
                
                # Use LLM for detailed analysis
                llm_analysis = await self.llm.reason_about_ticket_eligibility(ticket_data, customer_data)
                
                return {
                    "success": True,
                    "eligible": is_eligible,
                    "ticket": ticket_data,
                    "customer": customer_data,
                    "available_upgrades": available_upgrades,
                    "eligibility_reasons": llm_analysis,
                    "restrictions": [] if is_eligible else ["Event too soon", "Invalid ticket status", "No upgrades available"]
                }
                
            except Exception as e:
                return {"error": str(e), "success": False}
        
        @self.app.tool()
        async def calculate_upgrade_pricing(ticket_type: str, upgrade_tier: str, original_price: float = None) -> Dict[str, Any]:
            """Calculate upgrade pricing with detailed breakdown"""
            try:
                ticket_type_enum = TicketType(ticket_type.lower())
                upgrade_tier_enum = UpgradeTier(upgrade_tier.lower().replace(' ', '-').replace('_', '-'))
                
                # Calculate upgrade price
                upgrade_price = self.pricing.calculate_upgrade_price(ticket_type_enum, upgrade_tier_enum)
                
                if upgrade_price is None:
                    return {
                        "error": f"Upgrade from {ticket_type} to {upgrade_tier} not available",
                        "success": False
                    }
                
                original_price_decimal = Decimal(str(original_price)) if original_price else Decimal('50.00')
                total_price = self.pricing.calculate_total_price(original_price_decimal, upgrade_price)
                
                # Get tier information
                tier_info = self.pricing.TIER_DESCRIPTIONS[upgrade_tier_enum]
                
                # Use LLM for pricing analysis
                pricing_context = {
                    "ticket_type": ticket_type,
                    "upgrade_tier": upgrade_tier,
                    "original_price": float(original_price_decimal),
                    "upgrade_price": float(upgrade_price),
                    "total_price": float(total_price)
                }
                
                llm_analysis = await self.llm.reason_about_pricing_strategy(pricing_context)
                
                return {
                    "success": True,
                    "pricing": {
                        "original_price": float(original_price_decimal),
                        "upgrade_price": float(upgrade_price),
                        "total_price": float(total_price),
                        "savings_vs_new_ticket": float(upgrade_price * Decimal('0.2'))  # Assume 20% savings
                    },
                    "upgrade_info": tier_info,
                    "pricing_analysis": llm_analysis
                }
                
            except ValueError as e:
                return {"error": f"Invalid ticket type or upgrade tier: {str(e)}", "success": False}
            except Exception as e:
                return {"error": str(e), "success": False}
        
        @self.app.tool()
        async def get_upgrade_recommendations(ticket_data: Dict[str, Any], customer_preferences: Dict[str, Any] = None) -> Dict[str, Any]:
            """Get personalized upgrade recommendations using LLM"""
            try:
                ticket_type = TicketType(ticket_data.get("ticket_type", "general"))
                available_upgrades = self.pricing.get_available_upgrades(ticket_type)
                
                if not available_upgrades:
                    return {
                        "success": True,
                        "recommendations": [],
                        "message": "No upgrades available for this ticket type"
                    }
                
                # Use LLM for personalized recommendations
                llm_recommendations = await self.llm.reason_about_upgrade_selection(
                    ticket_data, 
                    available_upgrades, 
                    customer_preferences or {}
                )
                
                # Add pricing information to each upgrade
                for upgrade in available_upgrades:
                    upgrade_tier = UpgradeTier(upgrade['tier'])
                    upgrade_price = self.pricing.calculate_upgrade_price(ticket_type, upgrade_tier)
                    original_price = Decimal(str(ticket_data.get('original_price', 50.0)))
                    
                    upgrade['pricing'] = {
                        'upgrade_price': float(upgrade_price),
                        'total_price': float(original_price + upgrade_price),
                        'value_score': self._calculate_value_score(upgrade_tier, upgrade_price)
                    }
                
                return {
                    "success": True,
                    "recommendations": available_upgrades,
                    "personalized_advice": llm_recommendations,
                    "best_value": self._find_best_value_upgrade(available_upgrades)
                }
                
            except Exception as e:
                return {"error": str(e), "success": False}
        
        @self.app.tool()
        async def process_customer_query(query: str, conversation_context: Dict[str, Any] = None) -> Dict[str, Any]:
            """Process customer queries and provide intelligent responses"""
            try:
                # Use LLM to understand and respond to customer query
                llm_response = await self.llm.reason_about_customer_interaction(
                    conversation_context or {}, 
                    query
                )
                
                # Analyze query intent
                query_lower = query.lower()
                intent = "general"
                
                if any(word in query_lower for word in ["upgrade", "better", "premium"]):
                    intent = "upgrade_inquiry"
                elif any(word in query_lower for word in ["price", "cost", "how much"]):
                    intent = "pricing_inquiry"
                elif any(word in query_lower for word in ["cancel", "refund", "change"]):
                    intent = "modification_request"
                elif any(word in query_lower for word in ["when", "time", "date"]):
                    intent = "scheduling_inquiry"
                
                return {
                    "success": True,
                    "response": llm_response,
                    "intent": intent,
                    "suggested_actions": self._get_suggested_actions(intent),
                    "requires_human_escalation": self._requires_escalation(query, intent)
                }
                
            except Exception as e:
                return {"error": str(e), "success": False}
        
        @self.app.tool()
        async def get_upgrade_calendar(ticket_type: str, days_ahead: int = 30) -> Dict[str, Any]:
            """Get availability calendar with pricing for upgrade options"""
            try:
                ticket_type_enum = TicketType(ticket_type.lower())
                
                calendar_data = self.calendar.generate_availability_calendar(
                    start_date=date.today(),
                    days_ahead=days_ahead,
                    ticket_type=ticket_type_enum
                )
                
                # Add LLM analysis of calendar data
                calendar_context = {
                    "ticket_type": ticket_type,
                    "calendar_data": calendar_data,
                    "days_ahead": days_ahead
                }
                
                llm_analysis = await self.llm.reason_about_customer_interaction(
                    calendar_context,
                    f"Analyze the upgrade calendar for {ticket_type} tickets and provide insights about pricing patterns and best dates"
                )
                
                return {
                    "success": True,
                    "calendar": calendar_data,
                    "insights": llm_analysis,
                    "best_deals": self.calendar.get_best_pricing_dates(ticket_type_enum, UpgradeTier.STANDARD, days_ahead)
                }
                
            except ValueError as e:
                return {"error": f"Invalid ticket type: {str(e)}", "success": False}
            except Exception as e:
                return {"error": str(e), "success": False}
        
        @self.app.tool()
        async def get_upgrade_tier_comparison(ticket_type: str, selected_date: str = None) -> Dict[str, Any]:
            """Get comparison of all three upgrade tiers (Standard, Non-stop, Double Fun)"""
            try:
                ticket_type_enum = TicketType(ticket_type.lower())
                
                if selected_date:
                    comparison_date = date.fromisoformat(selected_date)
                else:
                    comparison_date = date.today() + timedelta(days=7)
                
                comparison = self.selection_processor.get_upgrade_tier_comparison(
                    ticket_type_enum, comparison_date
                )
                
                # Add LLM recommendations
                comparison_context = {
                    "ticket_type": ticket_type,
                    "comparison": comparison,
                    "selected_date": comparison_date.isoformat()
                }
                
                llm_recommendations = await self.llm.reason_about_upgrade_selection(
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
        
        @self.app.tool()
        async def process_upgrade_selection(selection_data: Dict[str, Any], customer_context: Dict[str, Any] = None) -> Dict[str, Any]:
            """Process complete upgrade selection workflow"""
            try:
                # Validate required fields
                required_fields = ['ticket_type', 'upgrade_tier', 'selected_date', 'original_price']
                missing_fields = [field for field in required_fields if field not in selection_data]
                
                if missing_fields:
                    return {
                        "success": False,
                        "error": f"Missing required fields: {', '.join(missing_fields)}"
                    }
                
                # Process the selection
                result = await self.selection_processor.process_upgrade_selection(
                    selection_data, customer_context
                )
                
                if result["success"]:
                    # Add LLM confirmation message
                    selection_summary = result["selection_summary"]
                    
                    confirmation_context = {
                        "selection": selection_summary,
                        "customer": customer_context or {}
                    }
                    
                    llm_confirmation = await self.llm.reason_about_customer_interaction(
                        confirmation_context,
                        "Generate a friendly confirmation message for this upgrade selection, highlighting the key benefits and next steps"
                    )
                    
                    result["confirmation_message"] = llm_confirmation
                
                return result
                
            except Exception as e:
                return {"error": str(e), "success": False}
        
        @self.app.tool()
        async def get_pricing_for_date(ticket_type: str, upgrade_tier: str, target_date: str) -> Dict[str, Any]:
            """Get specific pricing for a date and upgrade combination"""
            try:
                ticket_type_enum = TicketType(ticket_type.lower())
                upgrade_tier_enum = UpgradeTier(upgrade_tier.lower().replace(' ', '-').replace('_', '-'))
                date_obj = date.fromisoformat(target_date)
                
                pricing_result = self.calendar.get_pricing_for_date(
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
                
                llm_analysis = await self.llm.reason_about_pricing_strategy(pricing_context)
                
                return {
                    "success": True,
                    "pricing": pricing_result,
                    "pricing_analysis": llm_analysis
                }
                
            except ValueError as e:
                return {"error": f"Invalid input: {str(e)}", "success": False}
            except Exception as e:
                return {"error": str(e), "success": False}
            """Validate upgrade constraints and business rules"""
            try:
                constraints = []
                warnings = []
                is_valid = True
                
                # Check time constraints
                event_date = datetime.fromisoformat(ticket_data.get('event_date', ''))
                days_until_event = (event_date - datetime.now()).days
                
                if days_until_event < 1:
                    constraints.append("Cannot upgrade tickets for past events")
                    is_valid = False
                elif days_until_event < 7:
                    warnings.append("Upgrade processing may be expedited due to proximity to event")
                
                # Check ticket status
                if ticket_data.get('status') != 'active':
                    constraints.append(f"Cannot upgrade {ticket_data.get('status')} tickets")
                    is_valid = False
                
                # Check upgrade tier validity
                ticket_type = TicketType(ticket_data.get('ticket_type', 'general'))
                upgrade_tier = UpgradeTier(upgrade_selection.get('tier', ''))
                
                if upgrade_tier not in self.pricing.UPGRADE_PRICING.get(ticket_type, {}):
                    constraints.append(f"Upgrade to {upgrade_tier.value} not available for {ticket_type.value} tickets")
                    is_valid = False
                
                # Use LLM for additional validation insights
                validation_context = {
                    "ticket": ticket_data,
                    "upgrade": upgrade_selection,
                    "constraints": constraints,
                    "warnings": warnings
                }
                
                llm_validation = await self.llm.reason_about_customer_interaction(
                    validation_context,
                    "Validate this upgrade request and provide any additional considerations"
                )
                
                return {
                    "success": True,
                    "valid": is_valid,
                    "constraints": constraints,
                    "warnings": warnings,
                    "validation_analysis": llm_validation,
                    "recommended_actions": self._get_validation_actions(is_valid, constraints)
                }
                
            except Exception as e:
                return {"error": str(e), "success": False}
    
    def _calculate_value_score(self, upgrade_tier: UpgradeTier, price: Decimal) -> float:
        """Calculate value score for upgrade tier"""
        # Simple value scoring based on features vs price
        feature_counts = {
            UpgradeTier.STANDARD: 3,
            UpgradeTier.NON_STOP: 4,
            UpgradeTier.DOUBLE_FUN: 6
        }
        
        features = feature_counts.get(upgrade_tier, 1)
        return round(features / float(price) * 10, 2)
    
    def _find_best_value_upgrade(self, upgrades: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the best value upgrade option"""
        if not upgrades:
            return None
        
        best_upgrade = max(upgrades, key=lambda x: x.get('pricing', {}).get('value_score', 0))
        return best_upgrade
    
    def _get_suggested_actions(self, intent: str) -> List[str]:
        """Get suggested actions based on query intent"""
        actions = {
            "upgrade_inquiry": ["Show available upgrades", "Calculate pricing", "Explain upgrade benefits"],
            "pricing_inquiry": ["Provide detailed pricing breakdown", "Show value comparison", "Explain payment options"],
            "modification_request": ["Check modification policies", "Calculate change fees", "Escalate to support"],
            "scheduling_inquiry": ["Show event details", "Provide timeline information", "Send calendar invite"],
            "general": ["Provide general assistance", "Show account overview", "Offer upgrade options"]
        }
        
        return actions.get(intent, ["Provide general assistance"])
    
    def _requires_escalation(self, query: str, intent: str) -> bool:
        """Determine if query requires human escalation"""
        escalation_keywords = ["complaint", "angry", "refund", "cancel", "manager", "supervisor", "legal"]
        return any(keyword in query.lower() for keyword in escalation_keywords) or intent == "modification_request"
    
    def _get_validation_actions(self, is_valid: bool, constraints: List[str]) -> List[str]:
        """Get recommended actions based on validation results"""
        if is_valid:
            return ["Proceed with upgrade", "Send confirmation", "Process payment"]
        else:
            actions = ["Inform customer of constraints"]
            if "past events" in str(constraints):
                actions.append("Suggest future events")
            if "status" in str(constraints):
                actions.append("Check ticket status resolution")
            return actions
    
    async def start_server(self, host: str = "localhost", port: int = 8002):
        """Start the FastMCP server"""
        print(f"🎫 Starting Ticket Agent MCP server on {host}:{port}")
        print("🎯 Available tools:")
        print("  - validate_ticket_eligibility: Check if ticket can be upgraded")
        print("  - calculate_upgrade_pricing: Calculate upgrade costs and breakdown")
        print("  - get_upgrade_recommendations: Get personalized upgrade suggestions")
        print("  - process_customer_query: Handle customer questions and requests")
        print("  - get_upgrade_calendar: Get availability calendar with pricing")
        print("  - get_upgrade_tier_comparison: Compare all three upgrade tiers")
        print("  - process_upgrade_selection: Process complete upgrade selection workflow")
        print("  - get_pricing_for_date: Get specific pricing for date and upgrade")
        print("  - validate_upgrade_constraints: Validate upgrade business rules")
        print("🎪 Upgrade Tiers: Standard, Non-stop, Double Fun")
        print("📅 Calendar: Dynamic pricing based on demand and seasonality")
        
        await self.app.run(host=host, port=port)


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
        bedrock_model_id=os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0'),
        data_agent_url=os.getenv('DATA_AGENT_URL', 'http://localhost:8001')
    )


async def main():
    """Main function to run the Ticket Agent"""
    try:
        config = load_config()
        
        agent = TicketAgent(config)
        await agent.start_server()
        
    except KeyboardInterrupt:
        print("\n👋 Ticket Agent shutting down...")
        return 0
    except Exception as e:
        print(f"❌ Error starting Ticket Agent: {e}")
        return 1


if __name__ == "__main__":
    asyncio.run(main())