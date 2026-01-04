#!/usr/bin/env python3
"""
Direct Agent Client for Lambda

This client implements the agent functionality directly without requiring AgentCore agents.
It provides the same interface as the AgentCore HTTP client but implements the business logic locally.
"""

import json
import boto3
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid


class DirectAgentClient:
    """Direct implementation of agent functionality"""
    
    def __init__(self):
        # Initialize AWS clients
        self.rds_client = boto3.client('rds-data', region_name='us-west-2')
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-west-2')
        
        # Database configuration
        self.db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
        self.db_secret_arn = os.getenv('DB_SECRET_ARN')
        self.database_name = os.getenv('DATABASE_NAME', 'ticket_system')
        
        # Bedrock configuration
        self.model_id = os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
    
    def _execute_sql(self, sql: str, parameters: list = None) -> Dict[str, Any]:
        """Execute SQL query using RDS Data API"""
        try:
            params = {
                'resourceArn': self.db_cluster_arn,
                'secretArn': self.db_secret_arn,
                'database': self.database_name,
                'sql': sql
            }
            
            if parameters:
                params['parameters'] = parameters
            
            response = self.rds_client.execute_statement(**params)
            return {'success': True, 'data': response}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _call_llm(self, prompt: str) -> str:
        """Call Nova Pro LLM for reasoning"""
        try:
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 1000,
                    "temperature": 0.7
                }
            }
            
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=request_body["messages"],
                inferenceConfig=request_body["inferenceConfig"]
            )
            
            return response['output']['message']['content'][0]['text']
            
        except Exception as e:
            return f"LLM Error: {str(e)}"
    
    # Data Agent methods
    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer by ID"""
        try:
            sql = "SELECT * FROM customers WHERE customer_id = :customer_id"
            parameters = [{'name': 'customer_id', 'value': {'stringValue': customer_id}}]
            
            result = self._execute_sql(sql, parameters)
            
            if result['success'] and result['data'].get('records'):
                record = result['data']['records'][0]
                customer_data = {
                    'customer_id': record[0]['stringValue'],
                    'name': record[1]['stringValue'],
                    'email': record[2]['stringValue'],
                    'phone': record[3]['stringValue'],
                    'tier': record[4]['stringValue'],
                    'created_at': record[5]['stringValue']
                }
                
                return {
                    'success': True,
                    'data': {
                        'customer': customer_data,
                        'message': f"Found customer: {customer_data['name']}"
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f'Customer {customer_id} not found'
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_tickets_for_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get tickets for customer"""
        try:
            sql = """
            SELECT t.*, c.name as customer_name 
            FROM tickets t 
            JOIN customers c ON t.customer_id = c.customer_id 
            WHERE t.customer_id = :customer_id
            """
            parameters = [{'name': 'customer_id', 'value': {'stringValue': customer_id}}]
            
            result = self._execute_sql(sql, parameters)
            
            if result['success']:
                tickets = []
                for record in result['data'].get('records', []):
                    ticket_data = {
                        'ticket_id': record[0]['stringValue'],
                        'customer_id': record[1]['stringValue'],
                        'event_name': record[2]['stringValue'],
                        'event_date': record[3]['stringValue'],
                        'venue': record[4]['stringValue'],
                        'seat_section': record[5]['stringValue'],
                        'seat_number': record[6]['stringValue'],
                        'original_price': float(record[7]['doubleValue']),
                        'current_tier': record[8]['stringValue'],
                        'status': record[9]['stringValue'],
                        'created_at': record[10]['stringValue'],
                        'customer_name': record[11]['stringValue']
                    }
                    tickets.append(ticket_data)
                
                return {
                    'success': True,
                    'data': {
                        'tickets': tickets,
                        'count': len(tickets),
                        'message': f"Found {len(tickets)} tickets for customer"
                    }
                }
            else:
                return result
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_upgrade_order(self, customer_id: str, ticket_id: str, upgrade_tier: str, 
                           travel_date: str, total_amount: float) -> Dict[str, Any]:
        """Create upgrade order"""
        try:
            order_id = str(uuid.uuid4())
            
            sql = """
            INSERT INTO upgrade_orders (order_id, customer_id, ticket_id, upgrade_tier, 
                                      travel_date, total_amount, status, created_at)
            VALUES (:order_id, :customer_id, :ticket_id, :upgrade_tier, 
                    :travel_date, :total_amount, 'pending', NOW())
            """
            
            parameters = [
                {'name': 'order_id', 'value': {'stringValue': order_id}},
                {'name': 'customer_id', 'value': {'stringValue': customer_id}},
                {'name': 'ticket_id', 'value': {'stringValue': ticket_id}},
                {'name': 'upgrade_tier', 'value': {'stringValue': upgrade_tier}},
                {'name': 'travel_date', 'value': {'stringValue': travel_date}},
                {'name': 'total_amount', 'value': {'doubleValue': total_amount}}
            ]
            
            result = self._execute_sql(sql, parameters)
            
            if result['success']:
                return {
                    'success': True,
                    'data': {
                        'order_id': order_id,
                        'status': 'pending',
                        'message': f"Created upgrade order {order_id} for ${total_amount}"
                    }
                }
            else:
                return result
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # Ticket Agent methods
    def validate_ticket_eligibility(self, ticket_id: str, upgrade_tier: str) -> Dict[str, Any]:
        """Validate ticket eligibility for upgrade"""
        try:
            # Get ticket details
            sql = "SELECT * FROM tickets WHERE ticket_id = :ticket_id"
            parameters = [{'name': 'ticket_id', 'value': {'stringValue': ticket_id}}]
            
            result = self._execute_sql(sql, parameters)
            
            if not result['success'] or not result['data'].get('records'):
                return {'success': False, 'error': f'Ticket {ticket_id} not found'}
            
            record = result['data']['records'][0]
            current_tier = record[8]['stringValue']  # current_tier column
            status = record[9]['stringValue']  # status column
            
            # Business logic for eligibility
            tier_hierarchy = ['Standard', 'Non-stop', 'Double Fun']
            
            if status != 'active':
                return {
                    'success': True,
                    'data': {
                        'eligible': False,
                        'reason': f'Ticket status is {status}, must be active for upgrades',
                        'current_tier': current_tier
                    }
                }
            
            if upgrade_tier not in tier_hierarchy:
                return {
                    'success': True,
                    'data': {
                        'eligible': False,
                        'reason': f'Invalid upgrade tier: {upgrade_tier}',
                        'current_tier': current_tier
                    }
                }
            
            current_index = tier_hierarchy.index(current_tier) if current_tier in tier_hierarchy else -1
            upgrade_index = tier_hierarchy.index(upgrade_tier)
            
            if upgrade_index <= current_index:
                return {
                    'success': True,
                    'data': {
                        'eligible': False,
                        'reason': f'Cannot downgrade from {current_tier} to {upgrade_tier}',
                        'current_tier': current_tier
                    }
                }
            
            return {
                'success': True,
                'data': {
                    'eligible': True,
                    'reason': f'Ticket eligible for upgrade from {current_tier} to {upgrade_tier}',
                    'current_tier': current_tier,
                    'upgrade_tier': upgrade_tier
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def calculate_upgrade_pricing(self, ticket_id: str, upgrade_tier: str, travel_date: str) -> Dict[str, Any]:
        """Calculate upgrade pricing"""
        try:
            # Get ticket details
            sql = "SELECT * FROM tickets WHERE ticket_id = :ticket_id"
            parameters = [{'name': 'ticket_id', 'value': {'stringValue': ticket_id}}]
            
            result = self._execute_sql(sql, parameters)
            
            if not result['success'] or not result['data'].get('records'):
                return {'success': False, 'error': f'Ticket {ticket_id} not found'}
            
            record = result['data']['records'][0]
            original_price = float(record[7]['doubleValue'])  # original_price column
            current_tier = record[8]['stringValue']  # current_tier column
            
            # Pricing logic
            base_prices = {
                'Standard': 50.0,
                'Non-stop': 150.0,
                'Double Fun': 300.0
            }
            
            # Seasonal multipliers
            event_date = datetime.strptime(travel_date, '%Y-%m-%d')
            is_weekend = event_date.weekday() >= 5
            is_holiday_season = event_date.month in [11, 12, 1]  # Nov, Dec, Jan
            
            multiplier = 1.0
            if is_weekend:
                multiplier += 0.2
            if is_holiday_season:
                multiplier += 0.3
            
            base_upgrade_price = base_prices.get(upgrade_tier, 100.0)
            final_price = base_upgrade_price * multiplier
            
            # LLM reasoning for pricing explanation
            llm_prompt = f"""
            Explain the pricing for upgrading a ticket from {current_tier} to {upgrade_tier} 
            on {travel_date}. The base price is ${base_upgrade_price:.2f} and the final price 
            is ${final_price:.2f} with multiplier {multiplier:.2f}.
            Weekend: {is_weekend}, Holiday season: {is_holiday_season}.
            Provide a brief, customer-friendly explanation.
            """
            
            explanation = self._call_llm(llm_prompt)
            
            return {
                'success': True,
                'data': {
                    'ticket_id': ticket_id,
                    'current_tier': current_tier,
                    'upgrade_tier': upgrade_tier,
                    'base_price': base_upgrade_price,
                    'multiplier': multiplier,
                    'final_price': round(final_price, 2),
                    'travel_date': travel_date,
                    'explanation': explanation,
                    'pricing_factors': {
                        'weekend_premium': is_weekend,
                        'holiday_premium': is_holiday_season
                    }
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_upgrade_recommendations(self, customer_id: str, ticket_id: str) -> Dict[str, Any]:
        """Get upgrade recommendations"""
        try:
            # Get customer and ticket details
            customer_result = self.get_customer(customer_id)
            if not customer_result['success']:
                return customer_result
            
            sql = "SELECT * FROM tickets WHERE ticket_id = :ticket_id"
            parameters = [{'name': 'ticket_id', 'value': {'stringValue': ticket_id}}]
            
            ticket_result = self._execute_sql(sql, parameters)
            
            if not ticket_result['success'] or not ticket_result['data'].get('records'):
                return {'success': False, 'error': f'Ticket {ticket_id} not found'}
            
            record = ticket_result['data']['records'][0]
            current_tier = record[8]['stringValue']
            event_name = record[2]['stringValue']
            event_date = record[3]['stringValue']
            
            customer_data = customer_result['data']['customer']
            customer_tier = customer_data['tier']
            
            # LLM-powered recommendations
            llm_prompt = f"""
            Provide upgrade recommendations for a {customer_tier} tier customer named {customer_data['name']} 
            who has a {current_tier} ticket for {event_name} on {event_date}.
            
            Available upgrade tiers: Standard, Non-stop, Double Fun
            Current tier: {current_tier}
            
            Consider the customer's tier status and provide personalized recommendations with reasons.
            Format as a JSON-like structure with recommendations.
            """
            
            recommendations_text = self._call_llm(llm_prompt)
            
            # Generate structured recommendations
            available_tiers = []
            tier_hierarchy = ['Standard', 'Non-stop', 'Double Fun']
            current_index = tier_hierarchy.index(current_tier) if current_tier in tier_hierarchy else -1
            
            for i, tier in enumerate(tier_hierarchy):
                if i > current_index:
                    available_tiers.append({
                        'tier': tier,
                        'recommended': i == current_index + 1,  # Recommend next tier up
                        'description': f'Upgrade to {tier} tier'
                    })
            
            return {
                'success': True,
                'data': {
                    'customer_id': customer_id,
                    'ticket_id': ticket_id,
                    'current_tier': current_tier,
                    'customer_tier': customer_tier,
                    'available_upgrades': available_tiers,
                    'ai_recommendations': recommendations_text,
                    'event_info': {
                        'name': event_name,
                        'date': event_date
                    }
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_available_upgrade_tiers(self, ticket_id: str) -> Dict[str, Any]:
        """Get available upgrade tiers"""
        try:
            # Get ticket details
            sql = "SELECT current_tier, status FROM tickets WHERE ticket_id = :ticket_id"
            parameters = [{'name': 'ticket_id', 'value': {'stringValue': ticket_id}}]
            
            result = self._execute_sql(sql, parameters)
            
            if not result['success'] or not result['data'].get('records'):
                return {'success': False, 'error': f'Ticket {ticket_id} not found'}
            
            record = result['data']['records'][0]
            current_tier = record[0]['stringValue']
            status = record[1]['stringValue']
            
            if status != 'active':
                return {
                    'success': True,
                    'data': {
                        'available_tiers': [],
                        'message': f'No upgrades available - ticket status is {status}'
                    }
                }
            
            # Define tier hierarchy and pricing
            tier_info = {
                'Standard': {'price_range': '$50-70', 'features': ['Priority boarding', 'Extra legroom']},
                'Non-stop': {'price_range': '$150-200', 'features': ['Premium seating', 'Complimentary drinks', 'Fast track entry']},
                'Double Fun': {'price_range': '$300-400', 'features': ['VIP experience', 'Meet & greet', 'Exclusive merchandise']}
            }
            
            tier_hierarchy = ['Standard', 'Non-stop', 'Double Fun']
            current_index = tier_hierarchy.index(current_tier) if current_tier in tier_hierarchy else -1
            
            available_tiers = []
            for i, tier in enumerate(tier_hierarchy):
                if i > current_index:
                    tier_data = tier_info[tier].copy()
                    tier_data['tier'] = tier
                    tier_data['available'] = True
                    available_tiers.append(tier_data)
            
            return {
                'success': True,
                'data': {
                    'ticket_id': ticket_id,
                    'current_tier': current_tier,
                    'available_tiers': available_tiers,
                    'total_available': len(available_tiers)
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


def create_client():
    """Create and return a DirectAgentClient instance"""
    return DirectAgentClient()