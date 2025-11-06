"""
REST API Handler for Multi-Cloud Cost Analytics

This module provides REST API endpoints for the multi-cloud cost analytics platform,
including cost data retrieval, AI insights, client management, and webhook support.
"""

import json
import logging
import os
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
import asyncio
import boto3
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit

from ..models.multi_cloud_models import CloudProvider, UnifiedCostRecord
from ..models.multi_tenant_models import MultiCloudClient, ClientRole
from ..services.api_access_control import APIAccessControl, AuthenticationError, AuthorizationError
from ..services.rbac_service import RBACService, Permission, ResourceType
from ..services.multi_tenant_client_manager import MultiTenantClientManager
from ..services.cost_history_storage_service import CostHistoryStorageService
from ..services.ai_insights_service_enhanced import AIInsightsService
from ..services.notification_service import NotificationService
from ..services.rate_limiting_service import RateLimitingService
from ..utils.api_response import APIResponse, APIError
from ..utils.validation import validate_request_data, ValidationError


# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Environment variables
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'multi-cloud-cost-analytics')
JWT_SECRET = os.environ.get('JWT_SECRET')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
RATE_LIMIT_TABLE = os.environ.get('RATE_LIMIT_TABLE', 'api-rate-limits')


class MultiCloudAPIHandler:
    """
    REST API handler for multi-cloud cost analytics platform.
    
    Provides endpoints for cost data, AI insights, client management,
    and webhook notifications with comprehensive authentication and authorization.
    """
    
    def __init__(self):
        """Initialize the API handler with required services."""
        # Initialize core services
        self.rbac_service = RBACService(
            table_name=DYNAMODB_TABLE_NAME,
            region=AWS_REGION
        )
        
        self.api_access_control = APIAccessControl(
            rbac_service=self.rbac_service,
            jwt_secret=JWT_SECRET
        )
        
        self.client_manager = MultiTenantClientManager(
            table_name=DYNAMODB_TABLE_NAME,
            region=AWS_REGION
        )
        
        self.cost_storage = CostHistoryStorageService(
            table_name=DYNAMODB_TABLE_NAME,
            region=AWS_REGION
        )
        
        self.ai_insights = AIInsightsService()
        
        self.notification_service = NotificationService(
            region=AWS_REGION
        )
        
        self.rate_limiter = RateLimitingService(
            table_name=RATE_LIMIT_TABLE,
            region=AWS_REGION
        )
        
        # API response helper
        self.response = APIResponse()
    
    @tracer.capture_lambda_handler
    @logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY)
    def lambda_handler(self, event: Dict[str, Any], context) -> Dict[str, Any]:
        """
        Main Lambda handler entry point for API Gateway requests.
        
        Args:
            event: API Gateway event data
            context: Lambda context object
            
        Returns:
            API Gateway response
        """
        try:
            # Extract request information
            http_method = event.get('httpMethod', 'GET')
            path = event.get('path', '')
            headers = event.get('headers', {})
            query_params = event.get('queryStringParameters') or {}
            body = event.get('body', '')
            
            # Parse JSON body if present
            request_data = {}
            if body:
                try:
                    request_data = json.loads(body)
                except json.JSONDecodeError:
                    return self.response.error(
                        message="Invalid JSON in request body",
                        status_code=400
                    )
            
            # Log request
            logger.info("API request received", extra={
                "method": http_method,
                "path": path,
                "query_params": query_params,
                "user_agent": headers.get('User-Agent', 'Unknown')
            })
            
            # Add metrics
            metrics.add_metric(name="APIRequest", unit=MetricUnit.Count, value=1)
            metrics.add_metadata(key="method", value=http_method)
            metrics.add_metadata(key="path", value=path)
            
            # Route request to appropriate handler
            response = asyncio.run(self._route_request(
                http_method, path, headers, query_params, request_data, context
            ))
            
            # Add success metrics
            metrics.add_metric(name="APIRequestSuccess", unit=MetricUnit.Count, value=1)
            
            return response
            
        except Exception as e:
            # Log error
            logger.error("API request failed", extra={
                "error": str(e),
                "traceback": traceback.format_exc(),
                "method": event.get('httpMethod'),
                "path": event.get('path')
            })
            
            # Add failure metrics
            metrics.add_metric(name="APIRequestFailure", unit=MetricUnit.Count, value=1)
            
            return self.response.error(
                message="Internal server error",
                status_code=500,
                details={"error_id": context.aws_request_id if context else None}
            )
    
    async def _route_request(self, method: str, path: str, headers: Dict[str, str],
                           query_params: Dict[str, str], request_data: Dict[str, Any],
                           context) -> Dict[str, Any]:
        """
        Route API request to appropriate handler method.
        
        Args:
            method: HTTP method
            path: Request path
            headers: Request headers
            query_params: Query parameters
            request_data: Request body data
            context: Lambda context
            
        Returns:
            API response
        """
        try:
            # Authenticate request (except for health check)
            user_context = None
            if not path.endswith('/health'):
                try:
                    user_context = self.api_access_control.authenticate_request(headers)
                    
                    # Check rate limits
                    await self._check_rate_limits(user_context, method, path)
                    
                except (AuthenticationError, AuthorizationError) as e:
                    return self.response.error(
                        message=str(e),
                        status_code=401 if isinstance(e, AuthenticationError) else 403
                    )
            
            # Route based on path and method
            if path == '/health':
                return await self._handle_health_check()
            
            elif path.startswith('/api/v1/cost-data'):
                return await self._handle_cost_data_endpoints(
                    method, path, user_context, query_params, request_data
                )
            
            elif path.startswith('/api/v1/insights'):
                return await self._handle_insights_endpoints(
                    method, path, user_context, query_params, request_data
                )
            
            elif path.startswith('/api/v1/clients'):
                return await self._handle_client_endpoints(
                    method, path, user_context, query_params, request_data
                )
            
            elif path.startswith('/api/v1/webhooks'):
                return await self._handle_webhook_endpoints(
                    method, path, user_context, query_params, request_data
                )
            
            elif path.startswith('/api/v1/notifications'):
                return await self._handle_notification_endpoints(
                    method, path, user_context, query_params, request_data
                )
            
            else:
                return self.response.error(
                    message="Endpoint not found",
                    status_code=404
                )
                
        except Exception as e:
            logger.error(f"Request routing failed: {e}")
            return self.response.error(
                message="Request processing failed",
                status_code=500
            )
    
    async def _check_rate_limits(self, user_context: Dict[str, Any], method: str, path: str):
        """Check rate limits for the user."""
        user_id = user_context['user_id']
        tenant_id = user_context['tenant_id']
        
        # Check user-level rate limit
        user_limit_key = f"user:{user_id}"
        if not await self.rate_limiter.check_rate_limit(user_limit_key, limit=1000, window=3600):
            raise AuthorizationError("User rate limit exceeded")
        
        # Check tenant-level rate limit
        tenant_limit_key = f"tenant:{tenant_id}"
        if not await self.rate_limiter.check_rate_limit(tenant_limit_key, limit=5000, window=3600):
            raise AuthorizationError("Tenant rate limit exceeded")
        
        # Check endpoint-specific rate limits
        endpoint_key = f"endpoint:{user_id}:{path}"
        endpoint_limits = {
            '/api/v1/cost-data': (100, 3600),  # 100 requests per hour
            '/api/v1/insights': (50, 3600),    # 50 requests per hour
            '/api/v1/clients': (200, 3600),    # 200 requests per hour
        }
        
        for endpoint_pattern, (limit, window) in endpoint_limits.items():
            if path.startswith(endpoint_pattern):
                if not await self.rate_limiter.check_rate_limit(endpoint_key, limit, window):
                    raise AuthorizationError(f"Endpoint rate limit exceeded for {endpoint_pattern}")
                break
    
    async def _handle_health_check(self) -> Dict[str, Any]:
        """Handle health check endpoint."""
        return self.response.success(
            data={
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "services": {
                    "cost_storage": "healthy",
                    "ai_insights": "healthy",
                    "notifications": "healthy"
                }
            }
        )
    
    async def _handle_cost_data_endpoints(self, method: str, path: str, user_context: Dict[str, Any],
                                        query_params: Dict[str, str], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cost data related endpoints."""
        try:
            # Check permission
            self.api_access_control.authorize_request(
                user_context, Permission.COST_DATA_READ
            )
            
            if method == 'GET' and path == '/api/v1/cost-data':
                return await self._get_cost_data(user_context, query_params)
            
            elif method == 'GET' and path.startswith('/api/v1/cost-data/summary'):
                return await self._get_cost_summary(user_context, query_params)
            
            elif method == 'GET' and path.startswith('/api/v1/cost-data/trends'):
                return await self._get_cost_trends(user_context, query_params)
            
            elif method == 'GET' and path.startswith('/api/v1/cost-data/providers'):
                return await self._get_provider_breakdown(user_context, query_params)
            
            else:
                return self.response.error(
                    message="Cost data endpoint not found",
                    status_code=404
                )
                
        except AuthorizationError as e:
            return self.response.error(message=str(e), status_code=403)
        except Exception as e:
            logger.error(f"Cost data endpoint error: {e}")
            return self.response.error(
                message="Failed to process cost data request",
                status_code=500
            )
    
    async def _get_cost_data(self, user_context: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get cost data for the user's tenant."""
        try:
            tenant_id = user_context['tenant_id']
            
            # Parse query parameters
            start_date = query_params.get('start_date')
            end_date = query_params.get('end_date')
            provider = query_params.get('provider')
            granularity = query_params.get('granularity', 'daily')
            
            # Validate date parameters
            if start_date:
                start_date = datetime.fromisoformat(start_date)
            else:
                start_date = datetime.utcnow() - timedelta(days=30)
            
            if end_date:
                end_date = datetime.fromisoformat(end_date)
            else:
                end_date = datetime.utcnow()
            
            # Get client configuration
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Get cost data
            cost_records = await self.cost_storage.get_cost_data_range(
                client_id=client.client_id,
                start_date=start_date,
                end_date=end_date,
                provider=CloudProvider(provider) if provider else None
            )
            
            # Format response
            formatted_data = []
            for record in cost_records:
                formatted_data.append({
                    'date': record.date,
                    'provider': record.provider.value,
                    'total_cost': float(record.total_cost),
                    'currency': record.currency.value,
                    'services': {
                        name: {
                            'cost': float(service.cost),
                            'category': service.unified_category.value
                        }
                        for name, service in record.services.items()
                    },
                    'data_quality': record.data_quality.to_dict() if record.data_quality else None
                })
            
            return self.response.success(
                data={
                    'cost_data': formatted_data,
                    'summary': {
                        'total_records': len(formatted_data),
                        'date_range': {
                            'start': start_date.isoformat(),
                            'end': end_date.isoformat()
                        },
                        'providers': list(set(record['provider'] for record in formatted_data))
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get cost data: {e}")
            return self.response.error(
                message="Failed to retrieve cost data",
                status_code=500
            )
    
    async def _get_cost_summary(self, user_context: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get cost summary for the user's tenant."""
        try:
            tenant_id = user_context['tenant_id']
            
            # Get client configuration
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Get current month cost data
            now = datetime.utcnow()
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            current_month_data = await self.cost_storage.get_cost_data_range(
                client_id=client.client_id,
                start_date=start_of_month,
                end_date=now
            )
            
            # Calculate summary metrics
            total_cost = sum(record.total_cost for record in current_month_data)
            
            # Group by provider
            provider_costs = {}
            for record in current_month_data:
                provider = record.provider.value
                if provider not in provider_costs:
                    provider_costs[provider] = Decimal('0')
                provider_costs[provider] += record.total_cost
            
            # Group by service category
            category_costs = {}
            for record in current_month_data:
                for service in record.services.values():
                    category = service.unified_category.value
                    if category not in category_costs:
                        category_costs[category] = Decimal('0')
                    category_costs[category] += service.cost
            
            return self.response.success(
                data={
                    'current_month': {
                        'total_cost': float(total_cost),
                        'currency': 'USD',
                        'period': {
                            'start': start_of_month.isoformat(),
                            'end': now.isoformat()
                        }
                    },
                    'breakdown': {
                        'by_provider': {
                            provider: float(cost) 
                            for provider, cost in provider_costs.items()
                        },
                        'by_category': {
                            category: float(cost) 
                            for category, cost in category_costs.items()
                        }
                    },
                    'metadata': {
                        'data_points': len(current_month_data),
                        'providers_count': len(provider_costs),
                        'categories_count': len(category_costs)
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get cost summary: {e}")
            return self.response.error(
                message="Failed to retrieve cost summary",
                status_code=500
            )    as
ync def _get_cost_trends(self, user_context: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get cost trends analysis for the user's tenant."""
        try:
            tenant_id = user_context['tenant_id']
            
            # Get client configuration
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Parse parameters
            days = int(query_params.get('days', '90'))
            provider = query_params.get('provider')
            
            # Get historical data
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            cost_records = await self.cost_storage.get_cost_data_range(
                client_id=client.client_id,
                start_date=start_date,
                end_date=end_date,
                provider=CloudProvider(provider) if provider else None
            )
            
            # Generate AI insights for trends
            insights = await self.ai_insights.generate_insights(
                client_id=client.client_id,
                cost_data=cost_records
            )
            
            return self.response.success(
                data={
                    'trends': insights.trends.to_dict() if insights.trends else {},
                    'forecasts': [forecast.to_dict() for forecast in insights.forecasts],
                    'period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat(),
                        'days': days
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get cost trends: {e}")
            return self.response.error(
                message="Failed to retrieve cost trends",
                status_code=500
            )
    
    async def _get_provider_breakdown(self, user_context: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get cost breakdown by cloud provider."""
        try:
            tenant_id = user_context['tenant_id']
            
            # Get client configuration
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Parse parameters
            days = int(query_params.get('days', '30'))
            
            # Get recent data
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            cost_records = await self.cost_storage.get_cost_data_range(
                client_id=client.client_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Group by provider
            provider_breakdown = {}
            for record in cost_records:
                provider = record.provider.value
                if provider not in provider_breakdown:
                    provider_breakdown[provider] = {
                        'total_cost': Decimal('0'),
                        'services': {},
                        'accounts': {},
                        'data_points': 0
                    }
                
                breakdown = provider_breakdown[provider]
                breakdown['total_cost'] += record.total_cost
                breakdown['data_points'] += 1
                
                # Aggregate services
                for service_name, service in record.services.items():
                    if service_name not in breakdown['services']:
                        breakdown['services'][service_name] = {
                            'cost': Decimal('0'),
                            'category': service.unified_category.value
                        }
                    breakdown['services'][service_name]['cost'] += service.cost
                
                # Aggregate accounts
                for account_id, account in record.accounts.items():
                    if account_id not in breakdown['accounts']:
                        breakdown['accounts'][account_id] = {
                            'cost': Decimal('0'),
                            'name': account.account_name
                        }
                    breakdown['accounts'][account_id]['cost'] += account.cost
            
            # Format response
            formatted_breakdown = {}
            for provider, data in provider_breakdown.items():
                formatted_breakdown[provider] = {
                    'total_cost': float(data['total_cost']),
                    'data_points': data['data_points'],
                    'services': {
                        name: {
                            'cost': float(service['cost']),
                            'category': service['category']
                        }
                        for name, service in data['services'].items()
                    },
                    'accounts': {
                        account_id: {
                            'cost': float(account['cost']),
                            'name': account['name']
                        }
                        for account_id, account in data['accounts'].items()
                    }
                }
            
            return self.response.success(
                data={
                    'provider_breakdown': formatted_breakdown,
                    'period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat(),
                        'days': days
                    },
                    'summary': {
                        'total_providers': len(formatted_breakdown),
                        'total_cost': float(sum(data['total_cost'] for data in provider_breakdown.values()))
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get provider breakdown: {e}")
            return self.response.error(
                message="Failed to retrieve provider breakdown",
                status_code=500
            )
    
    async def _handle_insights_endpoints(self, method: str, path: str, user_context: Dict[str, Any],
                                       query_params: Dict[str, str], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle AI insights related endpoints."""
        try:
            # Check permission
            self.api_access_control.authorize_request(
                user_context, Permission.AI_INSIGHTS_READ
            )
            
            if method == 'GET' and path == '/api/v1/insights':
                return await self._get_ai_insights(user_context, query_params)
            
            elif method == 'GET' and path.startswith('/api/v1/insights/anomalies'):
                return await self._get_anomalies(user_context, query_params)
            
            elif method == 'GET' and path.startswith('/api/v1/insights/recommendations'):
                return await self._get_recommendations(user_context, query_params)
            
            elif method == 'GET' and path.startswith('/api/v1/insights/forecasts'):
                return await self._get_forecasts(user_context, query_params)
            
            else:
                return self.response.error(
                    message="Insights endpoint not found",
                    status_code=404
                )
                
        except AuthorizationError as e:
            return self.response.error(message=str(e), status_code=403)
        except Exception as e:
            logger.error(f"Insights endpoint error: {e}")
            return self.response.error(
                message="Failed to process insights request",
                status_code=500
            )
    
    async def _get_ai_insights(self, user_context: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get comprehensive AI insights for the user's tenant."""
        try:
            tenant_id = user_context['tenant_id']
            
            # Get client configuration
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Parse parameters
            days = int(query_params.get('days', '30'))
            provider = query_params.get('provider')
            
            # Get cost data
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            cost_records = await self.cost_storage.get_cost_data_range(
                client_id=client.client_id,
                start_date=start_date,
                end_date=end_date,
                provider=CloudProvider(provider) if provider else None
            )
            
            # Generate AI insights
            insights = await self.ai_insights.generate_insights(
                client_id=client.client_id,
                cost_data=cost_records
            )
            
            return self.response.success(
                data={
                    'insights': {
                        'anomalies': [anomaly.to_dict() for anomaly in insights.anomalies],
                        'trends': insights.trends.to_dict() if insights.trends else {},
                        'forecasts': [forecast.to_dict() for forecast in insights.forecasts],
                        'recommendations': [rec.to_dict() for rec in insights.recommendations],
                        'narrative': insights.narrative
                    },
                    'metadata': {
                        'analysis_period': {
                            'start': start_date.isoformat(),
                            'end': end_date.isoformat(),
                            'days': days
                        },
                        'data_points': len(cost_records),
                        'provider_filter': provider,
                        'generated_at': datetime.utcnow().isoformat()
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get AI insights: {e}")
            return self.response.error(
                message="Failed to retrieve AI insights",
                status_code=500
            )
    
    async def _get_anomalies(self, user_context: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get cost anomalies for the user's tenant."""
        try:
            tenant_id = user_context['tenant_id']
            
            # Get client configuration
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Parse parameters
            days = int(query_params.get('days', '7'))
            severity = query_params.get('severity')  # low, medium, high, critical
            
            # Get recent cost data
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            cost_records = await self.cost_storage.get_cost_data_range(
                client_id=client.client_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Generate insights to get anomalies
            insights = await self.ai_insights.generate_insights(
                client_id=client.client_id,
                cost_data=cost_records
            )
            
            # Filter anomalies by severity if specified
            anomalies = insights.anomalies
            if severity:
                anomalies = [
                    anomaly for anomaly in anomalies 
                    if anomaly.severity.value.lower() == severity.lower()
                ]
            
            return self.response.success(
                data={
                    'anomalies': [anomaly.to_dict() for anomaly in anomalies],
                    'summary': {
                        'total_anomalies': len(anomalies),
                        'severity_breakdown': {
                            'critical': len([a for a in insights.anomalies if a.severity.value == 'CRITICAL']),
                            'high': len([a for a in insights.anomalies if a.severity.value == 'HIGH']),
                            'medium': len([a for a in insights.anomalies if a.severity.value == 'MEDIUM']),
                            'low': len([a for a in insights.anomalies if a.severity.value == 'LOW'])
                        },
                        'period': {
                            'start': start_date.isoformat(),
                            'end': end_date.isoformat(),
                            'days': days
                        }
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get anomalies: {e}")
            return self.response.error(
                message="Failed to retrieve anomalies",
                status_code=500
            )
    
    async def _get_recommendations(self, user_context: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get cost optimization recommendations for the user's tenant."""
        try:
            tenant_id = user_context['tenant_id']
            
            # Get client configuration
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Parse parameters
            category = query_params.get('category')  # compute, storage, database, etc.
            min_savings = float(query_params.get('min_savings', '0'))
            
            # Get recent cost data for analysis
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            
            cost_records = await self.cost_storage.get_cost_data_range(
                client_id=client.client_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Generate insights to get recommendations
            insights = await self.ai_insights.generate_insights(
                client_id=client.client_id,
                cost_data=cost_records
            )
            
            # Filter recommendations
            recommendations = insights.recommendations
            if category:
                recommendations = [
                    rec for rec in recommendations 
                    if category.lower() in rec.category.lower()
                ]
            
            if min_savings > 0:
                recommendations = [
                    rec for rec in recommendations 
                    if rec.estimated_savings >= min_savings
                ]
            
            # Sort by estimated savings
            recommendations.sort(key=lambda x: x.estimated_savings, reverse=True)
            
            return self.response.success(
                data={
                    'recommendations': [rec.to_dict() for rec in recommendations],
                    'summary': {
                        'total_recommendations': len(recommendations),
                        'total_potential_savings': sum(rec.estimated_savings for rec in recommendations),
                        'categories': list(set(rec.category for rec in recommendations)),
                        'filters_applied': {
                            'category': category,
                            'min_savings': min_savings
                        }
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return self.response.error(
                message="Failed to retrieve recommendations",
                status_code=500
            )
    
    async def _get_forecasts(self, user_context: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get cost forecasts for the user's tenant."""
        try:
            tenant_id = user_context['tenant_id']
            
            # Get client configuration
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Parse parameters
            horizon_days = int(query_params.get('horizon_days', '90'))
            provider = query_params.get('provider')
            
            # Get historical data for forecasting
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=180)  # 6 months of history
            
            cost_records = await self.cost_storage.get_cost_data_range(
                client_id=client.client_id,
                start_date=start_date,
                end_date=end_date,
                provider=CloudProvider(provider) if provider else None
            )
            
            # Generate insights to get forecasts
            insights = await self.ai_insights.generate_insights(
                client_id=client.client_id,
                cost_data=cost_records
            )
            
            return self.response.success(
                data={
                    'forecasts': [forecast.to_dict() for forecast in insights.forecasts],
                    'metadata': {
                        'horizon_days': horizon_days,
                        'historical_period': {
                            'start': start_date.isoformat(),
                            'end': end_date.isoformat()
                        },
                        'provider_filter': provider,
                        'data_points_used': len(cost_records)
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get forecasts: {e}")
            return self.response.error(
                message="Failed to retrieve forecasts",
                status_code=500
            )
    
    async def _handle_client_endpoints(self, method: str, path: str, user_context: Dict[str, Any],
                                     query_params: Dict[str, str], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle client management related endpoints."""
        try:
            if method == 'GET' and path == '/api/v1/clients/me':
                return await self._get_current_client(user_context)
            
            elif method == 'PUT' and path == '/api/v1/clients/me':
                return await self._update_current_client(user_context, request_data)
            
            elif method == 'GET' and path.startswith('/api/v1/clients/me/accounts'):
                return await self._get_client_accounts(user_context, query_params)
            
            elif method == 'POST' and path.startswith('/api/v1/clients/me/accounts'):
                return await self._add_client_account(user_context, request_data)
            
            elif method == 'DELETE' and path.startswith('/api/v1/clients/me/accounts/'):
                account_id = path.split('/')[-1]
                return await self._remove_client_account(user_context, account_id)
            
            else:
                return self.response.error(
                    message="Client endpoint not found",
                    status_code=404
                )
                
        except AuthorizationError as e:
            return self.response.error(message=str(e), status_code=403)
        except Exception as e:
            logger.error(f"Client endpoint error: {e}")
            return self.response.error(
                message="Failed to process client request",
                status_code=500
            )
    
    async def _get_current_client(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get current client information."""
        try:
            tenant_id = user_context['tenant_id']
            
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            return self.response.success(
                data={
                    'client': {
                        'client_id': client.client_id,
                        'organization_name': client.organization_name,
                        'subscription_tier': client.subscription_tier.value,
                        'status': client.status.value,
                        'onboarding_status': client.onboarding_status.value,
                        'cloud_providers': [provider.value for provider in client.get_providers()],
                        'total_accounts': len(client.get_all_accounts()),
                        'active_accounts': len(client.get_active_accounts()),
                        'billing_preferences': client.billing_preferences.to_dict(),
                        'ai_preferences': client.ai_preferences.to_dict(),
                        'resource_limits': client.resource_limits.to_dict(),
                        'created_at': client.created_at.isoformat(),
                        'last_activity': client.last_activity.isoformat() if client.last_activity else None
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get current client: {e}")
            return self.response.error(
                message="Failed to retrieve client information",
                status_code=500
            )
    
    async def _update_current_client(self, user_context: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update current client configuration."""
        try:
            # Check permission
            self.api_access_control.authorize_request(
                user_context, Permission.CLIENT_CONFIG_WRITE
            )
            
            tenant_id = user_context['tenant_id']
            
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Validate request data
            allowed_updates = [
                'organization_name', 'billing_preferences', 
                'ai_preferences', 'notification_preferences'
            ]
            
            updates = {k: v for k, v in request_data.items() if k in allowed_updates}
            
            if not updates:
                return self.response.error(
                    message="No valid updates provided",
                    status_code=400
                )
            
            # Apply updates
            if 'organization_name' in updates:
                client.organization_name = updates['organization_name']
            
            if 'billing_preferences' in updates:
                from ..models.multi_tenant_models import BillingPreferences
                client.billing_preferences = BillingPreferences.from_dict(updates['billing_preferences'])
            
            if 'ai_preferences' in updates:
                from ..models.multi_tenant_models import AIPreferences
                client.ai_preferences = AIPreferences.from_dict(updates['ai_preferences'])
            
            if 'notification_preferences' in updates:
                from ..models.multi_tenant_models import NotificationPreferences
                client.notification_preferences = NotificationPreferences.from_dict(updates['notification_preferences'])
            
            # Save updates
            await self.client_manager.update_client(client)
            
            return self.response.success(
                data={
                    'message': 'Client updated successfully',
                    'updated_fields': list(updates.keys())
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to update client: {e}")
            return self.response.error(
                message="Failed to update client",
                status_code=500
            )


# Global handler instance
api_handler = MultiCloudAPIHandler()


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda entry point for API Gateway requests.
    
    Args:
        event: API Gateway event data
        context: Lambda context object
        
    Returns:
        API Gateway response
    """
    return api_handler.lambda_handler(event, context)    async d
ef _get_client_accounts(self, user_context: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get client cloud accounts."""
        try:
            tenant_id = user_context['tenant_id']
            
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Get all accounts
            all_accounts = client.get_all_accounts()
            
            # Format response
            accounts_data = []
            for account in all_accounts:
                accounts_data.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'provider': account.provider.value,
                    'regions': account.regions,
                    'is_active': account.is_active,
                    'monthly_budget': float(account.monthly_budget) if account.monthly_budget else None,
                    'currency': account.currency.value,
                    'created_at': account.created_at.isoformat(),
                    'updated_at': account.updated_at.isoformat()
                })
            
            return self.response.success(
                data={
                    'accounts': accounts_data,
                    'summary': {
                        'total_accounts': len(accounts_data),
                        'active_accounts': len([a for a in accounts_data if a['is_active']]),
                        'providers': list(set(a['provider'] for a in accounts_data))
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get client accounts: {e}")
            return self.response.error(
                message="Failed to retrieve client accounts",
                status_code=500
            )
    
    async def _add_client_account(self, user_context: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new cloud account to the client."""
        try:
            # Check permission
            self.api_access_control.authorize_request(
                user_context, Permission.CLIENT_CONFIG_WRITE
            )
            
            tenant_id = user_context['tenant_id']
            
            # Validate request data
            from ..utils.validation import validate_request_data, CLOUD_ACCOUNT_SCHEMA
            validated_data = validate_request_data(request_data, CLOUD_ACCOUNT_SCHEMA)
            
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Create cloud account
            from ..models.multi_tenant_models import CloudAccount, AWSCredentials, GCPCredentials, AzureCredentials
            
            provider = validated_data['provider']
            credentials_data = validated_data.get('credentials', {})
            
            # Create appropriate credentials based on provider
            if provider == CloudProvider.AWS:
                credentials = AWSCredentials(
                    access_key_id=credentials_data.get('access_key_id', ''),
                    secret_access_key=credentials_data.get('secret_access_key', ''),
                    role_arn=credentials_data.get('role_arn'),
                    external_id=credentials_data.get('external_id'),
                    region=credentials_data.get('region', 'us-east-1')
                )
            elif provider == CloudProvider.GCP:
                credentials = GCPCredentials(
                    service_account_key=credentials_data.get('service_account_key', {}),
                    project_id=credentials_data.get('project_id', '')
                )
            elif provider == CloudProvider.AZURE:
                credentials = AzureCredentials(
                    client_id=credentials_data.get('client_id', ''),
                    client_secret=credentials_data.get('client_secret', ''),
                    tenant_id=credentials_data.get('tenant_id', ''),
                    subscription_id=credentials_data.get('subscription_id', '')
                )
            else:
                return self.response.error(
                    message="Unsupported cloud provider",
                    status_code=400
                )
            
            cloud_account = CloudAccount(
                account_id=validated_data['account_id'],
                account_name=validated_data['account_name'],
                provider=provider,
                credentials=credentials,
                regions=validated_data.get('regions', []),
                cost_allocation_tags=validated_data.get('cost_allocation_tags', {}),
                monthly_budget=Decimal(str(validated_data['monthly_budget'])) if validated_data.get('monthly_budget') else None,
                currency=validated_data.get('currency', Currency.USD)
            )
            
            # Add account to client
            client.add_cloud_account(cloud_account)
            
            # Save client
            await self.client_manager.update_client(client)
            
            return self.response.success(
                data={
                    'message': 'Cloud account added successfully',
                    'account_id': cloud_account.account_id,
                    'provider': cloud_account.provider.value
                }
            )
            
        except ValidationError as e:
            return self.response.error(
                message=e.message,
                status_code=400,
                field_errors=getattr(e, 'field_errors', None)
            )
        except Exception as e:
            logger.error(f"Failed to add client account: {e}")
            return self.response.error(
                message="Failed to add cloud account",
                status_code=500
            )
    
    async def _remove_client_account(self, user_context: Dict[str, Any], account_id: str) -> Dict[str, Any]:
        """Remove a cloud account from the client."""
        try:
            # Check permission
            self.api_access_control.authorize_request(
                user_context, Permission.CLIENT_CONFIG_WRITE
            )
            
            tenant_id = user_context['tenant_id']
            
            client = await self.client_manager.get_client(tenant_id)
            if not client:
                return self.response.error(
                    message="Client not found",
                    status_code=404
                )
            
            # Find and remove account
            removed = False
            for provider in CloudProvider:
                if client.remove_cloud_account(provider, account_id):
                    removed = True
                    break
            
            if not removed:
                return self.response.error(
                    message="Account not found",
                    status_code=404
                )
            
            # Save client
            await self.client_manager.update_client(client)
            
            return self.response.success(
                data={
                    'message': 'Cloud account removed successfully',
                    'account_id': account_id
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to remove client account: {e}")
            return self.response.error(
                message="Failed to remove cloud account",
                status_code=500
            )
    
    async def _handle_webhook_endpoints(self, method: str, path: str, user_context: Dict[str, Any],
                                      query_params: Dict[str, str], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle webhook related endpoints."""
        try:
            if method == 'GET' and path == '/api/v1/webhooks':
                return await self._list_webhooks(user_context, query_params)
            
            elif method == 'POST' and path == '/api/v1/webhooks':
                return await self._create_webhook(user_context, request_data)
            
            elif method == 'GET' and path.startswith('/api/v1/webhooks/'):
                webhook_id = path.split('/')[-1]
                return await self._get_webhook(user_context, webhook_id)
            
            elif method == 'PUT' and path.startswith('/api/v1/webhooks/'):
                webhook_id = path.split('/')[-1]
                return await self._update_webhook(user_context, webhook_id, request_data)
            
            elif method == 'DELETE' and path.startswith('/api/v1/webhooks/'):
                webhook_id = path.split('/')[-1]
                return await self._delete_webhook(user_context, webhook_id)
            
            elif method == 'POST' and path.endswith('/test'):
                webhook_id = path.split('/')[-2]
                return await self._test_webhook(user_context, webhook_id)
            
            else:
                return self.response.error(
                    message="Webhook endpoint not found",
                    status_code=404
                )
                
        except AuthorizationError as e:
            return self.response.error(message=str(e), status_code=403)
        except Exception as e:
            logger.error(f"Webhook endpoint error: {e}")
            return self.response.error(
                message="Failed to process webhook request",
                status_code=500
            )
    
    async def _list_webhooks(self, user_context: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
        """List user's webhooks."""
        try:
            # Check permission
            self.api_access_control.authorize_request(
                user_context, Permission.WEBHOOK_READ
            )
            
            user_id = user_context['user_id']
            
            # Get webhooks from webhook service
            from ..services.webhook_service import WebhookService
            webhook_service = WebhookService(
                table_name="webhooks",
                queue_name="webhook-delivery",
                region=AWS_REGION
            )
            
            webhooks = webhook_service.list_user_webhooks(user_id)
            
            # Format response
            webhooks_data = []
            for webhook in webhooks:
                webhooks_data.append({
                    'webhook_id': webhook.webhook_id,
                    'name': webhook.name,
                    'url': webhook.url,
                    'events': [event.value for event in webhook.events],
                    'status': webhook.status.value,
                    'created_at': webhook.created_at.isoformat(),
                    'updated_at': webhook.updated_at.isoformat(),
                    'last_delivery_at': webhook.last_delivery_at.isoformat() if webhook.last_delivery_at else None,
                    'success_count': webhook.success_count,
                    'failure_count': webhook.failure_count,
                    'headers': webhook.headers,
                    'timeout_seconds': webhook.timeout_seconds,
                    'retry_count': webhook.retry_count
                })
            
            return self.response.success(
                data={
                    'webhooks': webhooks_data,
                    'summary': {
                        'total_webhooks': len(webhooks_data),
                        'active_webhooks': len([w for w in webhooks_data if w['status'] == 'active'])
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to list webhooks: {e}")
            return self.response.error(
                message="Failed to retrieve webhooks",
                status_code=500
            )
    
    async def _create_webhook(self, user_context: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new webhook."""
        try:
            # Check permission
            self.api_access_control.authorize_request(
                user_context, Permission.WEBHOOK_WRITE
            )
            
            # Validate request data
            from ..utils.validation import validate_request_data, WEBHOOK_SCHEMA
            validated_data = validate_request_data(request_data, WEBHOOK_SCHEMA)
            
            user_id = user_context['user_id']
            tenant_id = user_context['tenant_id']
            
            # Create webhook
            from ..services.webhook_service import WebhookService, WebhookEventType
            webhook_service = WebhookService(
                table_name="webhooks",
                queue_name="webhook-delivery",
                region=AWS_REGION
            )
            
            # Convert event strings to enum
            events = [WebhookEventType(event) for event in validated_data['events']]
            
            webhook_id = webhook_service.create_webhook(
                user_id=user_id,
                tenant_id=tenant_id,
                name=validated_data['name'],
                url=validated_data['url'],
                events=events,
                secret=validated_data.get('secret'),
                headers=validated_data.get('headers', {}),
                timeout_seconds=validated_data.get('timeout_seconds', 30),
                retry_count=validated_data.get('retry_count', 3),
                metadata=validated_data.get('metadata', {})
            )
            
            return self.response.success(
                data={
                    'webhook_id': webhook_id,
                    'message': 'Webhook created successfully'
                }
            )
            
        except ValidationError as e:
            return self.response.error(
                message=e.message,
                status_code=400,
                field_errors=getattr(e, 'field_errors', None)
            )
        except Exception as e:
            logger.error(f"Failed to create webhook: {e}")
            return self.response.error(
                message="Failed to create webhook",
                status_code=500
            )
    
    async def _handle_notification_endpoints(self, method: str, path: str, user_context: Dict[str, Any],
                                           query_params: Dict[str, str], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle notification related endpoints."""
        try:
            if method == 'POST' and path == '/api/v1/notifications/send':
                return await self._send_notification(user_context, request_data)
            
            elif method == 'GET' and path == '/api/v1/notifications/history':
                return await self._get_notification_history(user_context, query_params)
            
            elif method == 'GET' and path == '/api/v1/notifications/preferences':
                return await self._get_notification_preferences(user_context)
            
            elif method == 'PUT' and path == '/api/v1/notifications/preferences':
                return await self._update_notification_preferences(user_context, request_data)
            
            else:
                return self.response.error(
                    message="Notification endpoint not found",
                    status_code=404
                )
                
        except AuthorizationError as e:
            return self.response.error(message=str(e), status_code=403)
        except Exception as e:
            logger.error(f"Notification endpoint error: {e}")
            return self.response.error(
                message="Failed to process notification request",
                status_code=500
            )
    
    async def _send_notification(self, user_context: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a notification."""
        try:
            # Check permission
            self.api_access_control.authorize_request(
                user_context, Permission.NOTIFICATION_SEND
            )
            
            tenant_id = user_context['tenant_id']
            user_id = user_context['user_id']
            
            # Validate required fields
            required_fields = ['template_id', 'variables', 'recipients']
            for field in required_fields:
                if field not in request_data:
                    return self.response.error(
                        message=f"Missing required field: {field}",
                        status_code=400
                    )
            
            # Create notification service
            from ..services.enhanced_notification_service import EnhancedNotificationService, NotificationPriority
            notification_service = EnhancedNotificationService(
                region=AWS_REGION,
                table_name="notifications"
            )
            
            # Parse priority
            priority_str = request_data.get('priority', 'medium')
            priority = NotificationPriority(priority_str.lower())
            
            # Send notification
            notification_ids = await notification_service.send_notification(
                tenant_id=tenant_id,
                template_id=request_data['template_id'],
                variables=request_data['variables'],
                recipients=request_data['recipients'],
                priority=priority,
                user_id=user_id,
                metadata=request_data.get('metadata', {})
            )
            
            return self.response.success(
                data={
                    'notification_ids': notification_ids,
                    'message': f'Sent {len(notification_ids)} notifications'
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return self.response.error(
                message="Failed to send notification",
                status_code=500
            )