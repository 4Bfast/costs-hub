"""
API Gateway Handler - Standardized REST API Layer
Maps frontend expectations to existing backend services
"""

import json
import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Backend API Configuration
BACKEND_BASE_URL = os.environ.get('BACKEND_BASE_URL', 'https://jrltysmyg5.execute-api.us-east-1.amazonaws.com')

class APIGatewayHandler:
    """Handles API Gateway requests and maps to backend services"""
    
    def __init__(self):
        self.backend_url = BACKEND_BASE_URL
    
    async def handle_request(self, event: Dict[str, Any], context) -> Dict[str, Any]:
        """Main request handler"""
        
        try:
            method = event['httpMethod']
            path = event['path']
            headers = event.get('headers', {})
            query_params = event.get('queryStringParameters') or {}
            body = event.get('body')
            
            # Extract user context from authorizer
            user_context = event.get('requestContext', {}).get('authorizer', {})
            
            # Route request
            if path.startswith('/api/v1/auth'):
                return await self.handle_auth_endpoints(method, path, body, user_context)
            elif path.startswith('/api/v1/dashboard'):
                return await self.handle_dashboard_endpoints(method, path, query_params, user_context)
            elif path.startswith('/api/v1/costs') or path.startswith('/api/v1/cost-data'):
                return await self.handle_cost_endpoints(method, path, query_params, user_context)
            elif path.startswith('/api/v1/insights'):
                return await self.handle_insights_endpoints(method, path, query_params, user_context)
            elif path.startswith('/api/v1/accounts'):
                return await self.handle_accounts_endpoints(method, path, query_params, body, user_context)
            else:
                return self.error_response('Endpoint not found', 404)
                
        except Exception as e:
            print(f"Request handling error: {str(e)}")
            return self.error_response('Internal server error', 500)
    
    async def handle_auth_endpoints(self, method: str, path: str, body: str, user_context: Dict) -> Dict[str, Any]:
        """Handle authentication endpoints"""
        
        if method == 'POST' and path == '/api/v1/auth/login':
            return await self.auth_login(json.loads(body) if body else {})
        elif method == 'GET' and path == '/api/v1/auth/me':
            return await self.auth_me(user_context)
        elif method == 'POST' and path == '/api/v1/auth/logout':
            return await self.auth_logout()
        else:
            return self.error_response('Auth endpoint not found', 404)
    
    async def handle_dashboard_endpoints(self, method: str, path: str, params: Dict, user_context: Dict) -> Dict[str, Any]:
        """Handle dashboard endpoints"""
        
        if method != 'GET':
            return self.error_response('Method not allowed', 405)
        
        if path == '/api/v1/dashboard/metrics':
            return await self.dashboard_metrics()
        elif path == '/api/v1/dashboard/cost-overview':
            return await self.dashboard_cost_overview(params)
        elif path == '/api/v1/dashboard/service-breakdown':
            return await self.dashboard_service_breakdown(params)
        elif path == '/api/v1/dashboard/recent-alarms':
            return await self.dashboard_recent_alarms(params)
        elif path == '/api/v1/dashboard/insights-summary':
            return await self.dashboard_insights_summary()
        else:
            return self.error_response('Dashboard endpoint not found', 404)
    
    async def handle_cost_endpoints(self, method: str, path: str, params: Dict, user_context: Dict) -> Dict[str, Any]:
        """Handle cost data endpoints"""
        
        if method != 'GET':
            return self.error_response('Method not allowed', 405)
        
        if path in ['/api/v1/costs', '/api/v1/cost-data']:
            return await self.get_costs(params)
        elif path == '/api/v1/cost-data/summary':
            return await self.get_cost_summary(params)
        elif path == '/api/v1/cost-data/trends':
            return await self.get_cost_trends(params)
        else:
            return self.error_response('Cost endpoint not found', 404)
    
    async def handle_insights_endpoints(self, method: str, path: str, params: Dict, user_context: Dict) -> Dict[str, Any]:
        """Handle insights endpoints"""
        
        if method != 'GET':
            return self.error_response('Method not allowed', 405)
        
        if path == '/api/v1/insights':
            return await self.get_insights(params)
        elif path == '/api/v1/insights/summary':
            return await self.get_insights_summary()
        elif path == '/api/v1/insights/anomalies':
            return await self.get_anomalies(params)
        elif path == '/api/v1/insights/recommendations':
            return await self.get_recommendations(params)
        else:
            return self.error_response('Insights endpoint not found', 404)
    
    async def handle_accounts_endpoints(self, method: str, path: str, params: Dict, body: str, user_context: Dict) -> Dict[str, Any]:
        """Handle accounts endpoints"""
        
        if method == 'GET' and path == '/api/v1/accounts':
            return await self.get_accounts(params)
        else:
            return self.error_response('Accounts endpoint not implemented', 501)
    
    # Authentication Methods
    async def auth_login(self, credentials: Dict) -> Dict[str, Any]:
        """Mock login - generates JWT token"""
        from .api_gateway_authorizer import generate_mock_jwt
        
        # Mock validation - accept any credentials for development
        if credentials.get('email') and credentials.get('password'):
            user_data = {
                'id': 'aws-user-123',
                'email': credentials['email'],
                'role': 'ADMIN',
                'organization_id': 'aws-org-123'
            }
            
            token = generate_mock_jwt(user_data)
            
            return self.success_response({
                'user': {
                    'id': user_data['id'],
                    'name': 'AWS User',
                    'email': user_data['email'],
                    'role': user_data['role'],
                    'organization_id': user_data['organization_id']
                },
                'organization': {
                    'id': user_data['organization_id'],
                    'name': '4bfast Organization'
                },
                'token': token
            })
        
        return self.error_response('Invalid credentials', 401)
    
    async def auth_me(self, user_context: Dict) -> Dict[str, Any]:
        """Get current user info from JWT context"""
        return self.success_response({
            'user': {
                'id': user_context.get('userId', 'unknown'),
                'name': 'AWS User',
                'email': user_context.get('email', 'unknown'),
                'role': user_context.get('role', 'USER'),
                'organization_id': user_context.get('organizationId', 'unknown')
            },
            'organization': {
                'id': user_context.get('organizationId', 'unknown'),
                'name': '4bfast Organization'
            }
        })
    
    async def auth_logout(self) -> Dict[str, Any]:
        """Logout - token invalidation handled client-side"""
        return self.success_response({})
    
    # Dashboard Methods
    async def dashboard_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics from backend /costs"""
        backend_data = await self.call_backend('/costs')
        
        if not backend_data:
            return self.error_response('Failed to fetch metrics', 500)
        
        # Transform to expected format
        metrics = {
            'total_monthly_cost': backend_data.get('totalCost', 0),
            'month_over_month_change': backend_data.get('costVariation', 0),
            'connected_accounts': len(backend_data.get('accountBreakdown', [])),
            'active_alarms': backend_data.get('anomaliesCount', 0),
            'unread_insights': backend_data.get('recommendationsCount', 0),
            'top_service': None
        }
        
        # Extract top service
        services = backend_data.get('serviceBreakdown', [])
        if services:
            top_service = services[0]
            metrics['top_service'] = {
                'service_name': top_service.get('service', 'Unknown'),
                'cost': top_service.get('cost', 0),
                'percentage': (top_service.get('cost', 0) / backend_data.get('totalCost', 1)) * 100
            }
        
        return self.success_response(metrics)
    
    async def dashboard_cost_overview(self, params: Dict) -> Dict[str, Any]:
        """Get cost overview"""
        backend_data = await self.call_backend('/costs')
        
        if not backend_data:
            return self.error_response('Failed to fetch cost overview', 500)
        
        overview = {
            'current_period': {
                'total_cost': backend_data.get('totalCost', 0),
                'start_date': backend_data.get('startDate', ''),
                'end_date': backend_data.get('endDate', '')
            },
            'daily_breakdown': []  # Backend doesn't provide daily data
        }
        
        return self.success_response(overview)
    
    async def dashboard_service_breakdown(self, params: Dict) -> Dict[str, Any]:
        """Get service breakdown"""
        backend_data = await self.call_backend('/costs')
        
        if not backend_data:
            return self.error_response('Failed to fetch service breakdown', 500)
        
        services = []
        total_cost = backend_data.get('totalCost', 1)
        
        for service in backend_data.get('serviceBreakdown', [])[:5]:  # Top 5
            services.append({
                'service_name': service.get('service', 'Unknown'),
                'cost': service.get('cost', 0),
                'percentage': round((service.get('cost', 0) / total_cost) * 100, 1),
                'trend': 0,  # Not available in backend
                'provider': 'aws'
            })
        
        return self.success_response(services)
    
    async def dashboard_recent_alarms(self, params: Dict) -> Dict[str, Any]:
        """Get recent alarms - mock for now"""
        return self.success_response([])
    
    async def dashboard_insights_summary(self) -> Dict[str, Any]:
        """Get insights summary"""
        insights_data = await self.call_backend('/insights')
        
        summary = {
            'total_new_insights': insights_data.get('count', 0) if insights_data else 0,
            'high_priority_count': 0,
            'potential_monthly_savings': 0,
            'recent_insights': []
        }
        
        if insights_data and insights_data.get('insights'):
            for i, insight in enumerate(insights_data['insights'][:3]):
                summary['recent_insights'].append({
                    'id': f'insight-{i}',
                    'type': 'recommendation',
                    'severity': 'medium',
                    'title': insight.get('title', 'Insight'),
                    'description': insight.get('description', ''),
                    'created_at': datetime.utcnow().isoformat()
                })
        
        return self.success_response(summary)
    
    # Cost Methods
    async def get_costs(self, params: Dict) -> Dict[str, Any]:
        """Get cost data"""
        backend_data = await self.call_backend('/costs')
        return self.success_response(backend_data) if backend_data else self.error_response('Failed to fetch costs', 500)
    
    async def get_cost_summary(self, params: Dict) -> Dict[str, Any]:
        """Get cost summary"""
        backend_data = await self.call_backend('/costs/total')
        return self.success_response(backend_data) if backend_data else self.error_response('Failed to fetch cost summary', 500)
    
    async def get_cost_trends(self, params: Dict) -> Dict[str, Any]:
        """Get cost trends - calculated from historical data"""
        return self.success_response({'trends': []})  # Mock for now
    
    # Insights Methods
    async def get_insights(self, params: Dict) -> Dict[str, Any]:
        """Get insights"""
        backend_data = await self.call_backend('/insights')
        return self.success_response(backend_data) if backend_data else self.error_response('Failed to fetch insights', 500)
    
    async def get_insights_summary(self) -> Dict[str, Any]:
        """Get insights summary"""
        return await self.dashboard_insights_summary()
    
    async def get_anomalies(self, params: Dict) -> Dict[str, Any]:
        """Get anomalies"""
        backend_data = await self.call_backend('/anomalies')
        return self.success_response(backend_data) if backend_data else self.error_response('Failed to fetch anomalies', 500)
    
    async def get_recommendations(self, params: Dict) -> Dict[str, Any]:
        """Get recommendations"""
        backend_data = await self.call_backend('/recommendations')
        return self.success_response(backend_data) if backend_data else self.error_response('Failed to fetch recommendations', 500)
    
    # Accounts Methods
    async def get_accounts(self, params: Dict) -> Dict[str, Any]:
        """Get accounts"""
        backend_data = await self.call_backend('/accounts')
        return self.success_response(backend_data) if backend_data else self.error_response('Failed to fetch accounts', 500)
    
    # Utility Methods
    async def call_backend(self, endpoint: str) -> Optional[Dict]:
        """Call existing backend API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.backend_url}{endpoint}"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
        except Exception as e:
            print(f"Backend call failed: {str(e)}")
            return None
    
    def success_response(self, data: Any) -> Dict[str, Any]:
        """Generate standardized success response"""
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Request-ID',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'data': data
            })
        }
    
    def error_response(self, message: str, status_code: int = 400) -> Dict[str, Any]:
        """Generate standardized error response"""
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Request-ID',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'success': False,
                'errors': [message]
            })
        }

# Lambda handler
def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Main Lambda handler"""
    
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Request-ID',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
                'Access-Control-Max-Age': '86400'
            },
            'body': json.dumps({'success': True})
        }
    
    # Handle async request
    handler = APIGatewayHandler()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(handler.handle_request(event, context))
    finally:
        loop.close()
