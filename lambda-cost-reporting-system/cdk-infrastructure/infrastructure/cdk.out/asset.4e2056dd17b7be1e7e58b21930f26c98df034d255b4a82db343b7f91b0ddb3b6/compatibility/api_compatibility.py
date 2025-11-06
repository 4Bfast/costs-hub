"""
API Compatibility Layer

This module provides backward compatibility for existing API endpoints,
allowing existing clients to continue working while gradually migrating
to the new multi-cloud system.
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
import json
import boto3
from botocore.exceptions import ClientError

from ..models.multi_cloud_models import (
    UnifiedCostRecord, CloudProvider, ServiceCategory
)
from ..services.cost_history_service import CostHistoryService
from .feature_flags import FeatureFlagManager


logger = logging.getLogger(__name__)


class CompatibilityAPIHandler:
    """
    Handles backward compatibility for existing API endpoints.
    Translates between old and new data formats.
    """
    
    def __init__(
        self,
        cost_history_service: CostHistoryService,
        feature_flag_manager: FeatureFlagManager
    ):
        """
        Initialize the compatibility API handler.
        
        Args:
            cost_history_service: Service for accessing cost data
            feature_flag_manager: Manager for feature flags
        """
        self.cost_history_service = cost_history_service
        self.feature_flags = feature_flag_manager
        
        # Legacy API endpoint mappings
        self.legacy_endpoints = {
            '/api/v1/costs/daily': self._handle_daily_costs,
            '/api/v1/costs/by-service': self._handle_costs_by_service,
            '/api/v1/costs/summary': self._handle_cost_summary,
            '/api/v1/costs/trends': self._handle_cost_trends,
            '/api/v1/aws-accounts': self._handle_aws_accounts,
            '/api/v1/organizations': self._handle_organizations
        }
    
    async def handle_legacy_request(
        self,
        endpoint: str,
        method: str,
        params: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Handle a legacy API request and return compatible response.
        
        Args:
            endpoint: The API endpoint being called
            method: HTTP method (GET, POST, etc.)
            params: Request parameters
            headers: Request headers
            
        Returns:
            Response in legacy format
        """
        logger.info(f"Handling legacy request: {method} {endpoint}")
        
        # Extract client information from headers or params
        client_id = self._extract_client_id(headers, params)
        
        # Check if client should use new API
        if await self.feature_flags.should_use_new_api(client_id):
            return await self._redirect_to_new_api(endpoint, method, params, headers)
        
        # Handle legacy request
        if endpoint in self.legacy_endpoints:
            handler = self.legacy_endpoints[endpoint]
            return await handler(method, params, headers, client_id)
        else:
            return {
                'error': 'Endpoint not found',
                'message': f'Legacy endpoint {endpoint} is not supported',
                'status_code': 404
            }
    
    def _extract_client_id(self, headers: Dict[str, str], params: Dict[str, Any]) -> str:
        """Extract client ID from request headers or parameters."""
        # Try to get from authorization header (JWT token)
        auth_header = headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            # In a real implementation, you'd decode the JWT token
            # For now, we'll use a placeholder
            return 'legacy-client'
        
        # Try to get from parameters
        org_id = params.get('organization_id')
        if org_id:
            return f"org-{org_id}"
        
        return 'unknown-client'
    
    async def _redirect_to_new_api(
        self,
        endpoint: str,
        method: str,
        params: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Redirect request to new API and translate response."""
        # This would integrate with the new API system
        return {
            'message': 'Client has been migrated to new API',
            'new_endpoint': self._map_to_new_endpoint(endpoint),
            'migration_guide': 'https://docs.example.com/migration-guide',
            'status_code': 301
        }
    
    def _map_to_new_endpoint(self, legacy_endpoint: str) -> str:
        """Map legacy endpoint to new API endpoint."""
        mapping = {
            '/api/v1/costs/daily': '/api/v2/multi-cloud/costs/daily',
            '/api/v1/costs/by-service': '/api/v2/multi-cloud/costs/by-service',
            '/api/v1/costs/summary': '/api/v2/multi-cloud/costs/summary',
            '/api/v1/costs/trends': '/api/v2/multi-cloud/analytics/trends',
            '/api/v1/aws-accounts': '/api/v2/multi-cloud/accounts',
            '/api/v1/organizations': '/api/v2/clients'
        }
        return mapping.get(legacy_endpoint, '/api/v2/multi-cloud/')
    
    async def _handle_daily_costs(
        self,
        method: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        client_id: str
    ) -> Dict[str, Any]:
        """Handle legacy daily costs endpoint."""
        if method != 'GET':
            return {'error': 'Method not allowed', 'status_code': 405}
        
        try:
            # Extract parameters
            start_date = self._parse_date(params.get('start_date'))
            end_date = self._parse_date(params.get('end_date'))
            account_id = params.get('account_id')
            
            # Get data from new system
            cost_records = await self.cost_history_service.get_cost_data(
                client_id=client_id,
                provider=CloudProvider.AWS,
                start_date=start_date,
                end_date=end_date
            )
            
            # Transform to legacy format
            legacy_response = self._transform_to_legacy_daily_format(
                cost_records, account_id
            )
            
            return {
                'data': legacy_response,
                'status_code': 200,
                'metadata': {
                    'source': 'multi-cloud-system',
                    'compatibility_layer': True,
                    'migration_available': True
                }
            }
        
        except Exception as e:
            logger.error(f"Error handling daily costs: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': str(e),
                'status_code': 500
            }
    
    async def _handle_costs_by_service(
        self,
        method: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        client_id: str
    ) -> Dict[str, Any]:
        """Handle legacy costs by service endpoint."""
        if method != 'GET':
            return {'error': 'Method not allowed', 'status_code': 405}
        
        try:
            # Extract parameters
            start_date = self._parse_date(params.get('start_date'))
            end_date = self._parse_date(params.get('end_date'))
            
            # Get data from new system
            cost_records = await self.cost_history_service.get_cost_data(
                client_id=client_id,
                provider=CloudProvider.AWS,
                start_date=start_date,
                end_date=end_date
            )
            
            # Transform to legacy format
            legacy_response = self._transform_to_legacy_service_format(cost_records)
            
            return {
                'data': legacy_response,
                'status_code': 200,
                'metadata': {
                    'source': 'multi-cloud-system',
                    'compatibility_layer': True
                }
            }
        
        except Exception as e:
            logger.error(f"Error handling costs by service: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': str(e),
                'status_code': 500
            }
    
    async def _handle_cost_summary(
        self,
        method: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        client_id: str
    ) -> Dict[str, Any]:
        """Handle legacy cost summary endpoint."""
        if method != 'GET':
            return {'error': 'Method not allowed', 'status_code': 405}
        
        try:
            # Get current month data
            today = date.today()
            start_date = today.replace(day=1)
            end_date = today
            
            # Get data from new system
            cost_records = await self.cost_history_service.get_cost_data(
                client_id=client_id,
                provider=CloudProvider.AWS,
                start_date=start_date,
                end_date=end_date
            )
            
            # Transform to legacy summary format
            legacy_response = self._transform_to_legacy_summary_format(cost_records)
            
            return {
                'data': legacy_response,
                'status_code': 200,
                'metadata': {
                    'source': 'multi-cloud-system',
                    'compatibility_layer': True
                }
            }
        
        except Exception as e:
            logger.error(f"Error handling cost summary: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': str(e),
                'status_code': 500
            }
    
    async def _handle_cost_trends(
        self,
        method: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        client_id: str
    ) -> Dict[str, Any]:
        """Handle legacy cost trends endpoint."""
        if method != 'GET':
            return {'error': 'Method not allowed', 'status_code': 405}
        
        try:
            # Get last 30 days of data
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            # Get data from new system
            cost_records = await self.cost_history_service.get_cost_data(
                client_id=client_id,
                provider=CloudProvider.AWS,
                start_date=start_date,
                end_date=end_date
            )
            
            # Transform to legacy trends format
            legacy_response = self._transform_to_legacy_trends_format(cost_records)
            
            return {
                'data': legacy_response,
                'status_code': 200,
                'metadata': {
                    'source': 'multi-cloud-system',
                    'compatibility_layer': True,
                    'ai_insights_available': True
                }
            }
        
        except Exception as e:
            logger.error(f"Error handling cost trends: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': str(e),
                'status_code': 500
            }
    
    async def _handle_aws_accounts(
        self,
        method: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        client_id: str
    ) -> Dict[str, Any]:
        """Handle legacy AWS accounts endpoint."""
        try:
            if method == 'GET':
                # Get client configuration (this would come from a client config service)
                accounts = await self._get_client_aws_accounts(client_id)
                
                return {
                    'data': accounts,
                    'status_code': 200,
                    'metadata': {
                        'source': 'multi-cloud-system',
                        'compatibility_layer': True,
                        'multi_cloud_available': True
                    }
                }
            
            elif method == 'POST':
                # Handle account creation (would integrate with new onboarding)
                return {
                    'message': 'Account creation via legacy API is deprecated',
                    'new_endpoint': '/api/v2/multi-cloud/accounts',
                    'status_code': 301
                }
            
            else:
                return {'error': 'Method not allowed', 'status_code': 405}
        
        except Exception as e:
            logger.error(f"Error handling AWS accounts: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': str(e),
                'status_code': 500
            }
    
    async def _handle_organizations(
        self,
        method: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        client_id: str
    ) -> Dict[str, Any]:
        """Handle legacy organizations endpoint."""
        try:
            if method == 'GET':
                # Get client information
                client_info = await self._get_client_info(client_id)
                
                # Transform to legacy organization format
                legacy_org = {
                    'id': client_info.get('original_org_id', 1),
                    'org_name': client_info.get('organization_name', 'Unknown'),
                    'status': 'ACTIVE',
                    'created_at': client_info.get('created_at'),
                    'aws_accounts': client_info.get('aws_accounts', [])
                }
                
                return {
                    'data': legacy_org,
                    'status_code': 200,
                    'metadata': {
                        'source': 'multi-cloud-system',
                        'compatibility_layer': True
                    }
                }
            
            else:
                return {'error': 'Method not allowed', 'status_code': 405}
        
        except Exception as e:
            logger.error(f"Error handling organizations: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': str(e),
                'status_code': 500
            }
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S').date()
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
                return None
    
    def _transform_to_legacy_daily_format(
        self,
        cost_records: List[UnifiedCostRecord],
        account_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Transform unified cost records to legacy daily format."""
        legacy_data = []
        
        for record in cost_records:
            # Filter by account if specified
            if account_id:
                if account_id not in record.accounts:
                    continue
                account_cost = record.accounts[account_id].cost
            else:
                account_cost = record.total_cost
            
            legacy_record = {
                'usage_date': record.date,
                'total_cost': float(account_cost),
                'currency': record.currency.value,
                'services': []
            }
            
            # Add service breakdown
            for service_name, service in record.services.items():
                if account_id:
                    # Filter services for specific account
                    if account_id in record.accounts:
                        account_services = record.accounts[account_id].services
                        if service_name not in account_services:
                            continue
                        service_cost = account_services[service_name].cost
                    else:
                        continue
                else:
                    service_cost = service.cost
                
                legacy_service = {
                    'aws_service': service_name,
                    'service_category': service.unified_category.value,
                    'cost': float(service_cost),
                    'charge_category': service.provider_specific_data.get('charge_category', 'Usage')
                }
                legacy_record['services'].append(legacy_service)
            
            legacy_data.append(legacy_record)
        
        return legacy_data
    
    def _transform_to_legacy_service_format(
        self,
        cost_records: List[UnifiedCostRecord]
    ) -> List[Dict[str, Any]]:
        """Transform unified cost records to legacy service format."""
        service_totals = {}
        
        for record in cost_records:
            for service_name, service in record.services.items():
                if service_name not in service_totals:
                    service_totals[service_name] = {
                        'aws_service': service_name,
                        'service_category': service.unified_category.value,
                        'total_cost': 0.0,
                        'currency': service.currency.value
                    }
                
                service_totals[service_name]['total_cost'] += float(service.cost)
        
        # Sort by cost descending
        return sorted(
            service_totals.values(),
            key=lambda x: x['total_cost'],
            reverse=True
        )
    
    def _transform_to_legacy_summary_format(
        self,
        cost_records: List[UnifiedCostRecord]
    ) -> Dict[str, Any]:
        """Transform unified cost records to legacy summary format."""
        total_cost = sum(record.total_cost for record in cost_records)
        
        # Calculate service breakdown
        service_breakdown = {}
        for record in cost_records:
            for service_name, service in record.services.items():
                category = service.unified_category.value
                if category not in service_breakdown:
                    service_breakdown[category] = 0.0
                service_breakdown[category] += float(service.cost)
        
        # Calculate account breakdown
        account_breakdown = {}
        for record in cost_records:
            for account_id, account in record.accounts.items():
                if account_id not in account_breakdown:
                    account_breakdown[account_id] = {
                        'account_id': account_id,
                        'account_name': account.account_name,
                        'total_cost': 0.0
                    }
                account_breakdown[account_id]['total_cost'] += float(account.cost)
        
        return {
            'total_cost': float(total_cost),
            'currency': 'USD',
            'period': {
                'start_date': min(record.date for record in cost_records) if cost_records else None,
                'end_date': max(record.date for record in cost_records) if cost_records else None
            },
            'service_breakdown': service_breakdown,
            'account_breakdown': list(account_breakdown.values()),
            'record_count': len(cost_records)
        }
    
    def _transform_to_legacy_trends_format(
        self,
        cost_records: List[UnifiedCostRecord]
    ) -> Dict[str, Any]:
        """Transform unified cost records to legacy trends format."""
        # Group by date
        daily_costs = {}
        for record in cost_records:
            daily_costs[record.date] = float(record.total_cost)
        
        # Calculate simple trend
        dates = sorted(daily_costs.keys())
        costs = [daily_costs[date] for date in dates]
        
        if len(costs) >= 2:
            trend_direction = 'increasing' if costs[-1] > costs[0] else 'decreasing'
            trend_percentage = ((costs[-1] - costs[0]) / costs[0] * 100) if costs[0] > 0 else 0
        else:
            trend_direction = 'stable'
            trend_percentage = 0
        
        return {
            'daily_costs': [
                {'date': date, 'cost': daily_costs[date]}
                for date in dates
            ],
            'trend': {
                'direction': trend_direction,
                'percentage': trend_percentage
            },
            'statistics': {
                'average_daily_cost': sum(costs) / len(costs) if costs else 0,
                'max_daily_cost': max(costs) if costs else 0,
                'min_daily_cost': min(costs) if costs else 0,
                'total_cost': sum(costs)
            }
        }
    
    async def _get_client_aws_accounts(self, client_id: str) -> List[Dict[str, Any]]:
        """Get AWS accounts for a client (placeholder implementation)."""
        # This would integrate with the client configuration service
        return [
            {
                'id': 1,
                'account_name': 'Production Account',
                'payer_account_id': '123456789012',
                'status': 'ACTIVE',
                'is_connection_active': True
            }
        ]
    
    async def _get_client_info(self, client_id: str) -> Dict[str, Any]:
        """Get client information (placeholder implementation)."""
        # This would integrate with the client configuration service
        return {
            'client_id': client_id,
            'organization_name': 'Example Organization',
            'original_org_id': 1,
            'created_at': '2024-01-01T00:00:00Z',
            'aws_accounts': await self._get_client_aws_accounts(client_id)
        }