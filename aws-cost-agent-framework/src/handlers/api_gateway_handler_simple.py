import json
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from handlers.costs_handler_real import handle_costs_request
from handlers.ai_handler import handle_ai_request
from utils.jwt_utils_simple import extract_client_id_from_token
from config.settings import config

def lambda_handler(event, context):
    """Main Lambda handler for CostHub API Gateway"""
    
    # CORS headers
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': config.CORS_ALLOWED_ORIGINS.split(',')[0],
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Request-ID,X-Requested-With',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    try:
        method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        print(f"Request: {method} {path}")
        
        # Handle OPTIONS for CORS
        if method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }
        
        # Health check endpoint
        if method == 'GET' and path == '/health':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'status': 'healthy',
                    'service': 'costhub-api',
                    'version': '2.0',
                    'timestamp': context.aws_request_id if context else 'local',
                    'endpoints_active': 9,
                    'cost_explorer_integration': 'active'
                })
            }
        
        # Route to AI endpoints (NEW - Phase 4)
        if '/ai' in path:
            return handle_ai_request(event, cors_headers)
        
        # Route to cost endpoints (Real implementation)
        if '/costs' in path:
            return handle_costs_request(event, cors_headers)
        
        # Route to alarms endpoints (NEW - Real implementation)
        if '/alarms' in path:
            from handlers.alarms_handler_real import handle_alarms_request as handle_alarms_real
            return handle_alarms_real(event, cors_headers)
        
        # Route to accounts endpoints (existing)
        if '/accounts' in path:
            return handle_accounts_request(event, cors_headers)
        
        # Route to other endpoints (placeholders for now)
        if '/dashboard' in path:
            return handle_dashboard_request(event, cors_headers)
        
        if '/insights' in path:
            return handle_insights_request(event, cors_headers)
        
        if '/alarms' in path:
            return handle_alarms_request(event, cors_headers)
        
        # Route to auth endpoints (NEW - Real implementation)
        if '/auth' in path:
            from handlers.auth_handler_real import handle_auth_request as handle_auth_real
            return handle_auth_real(event, cors_headers)
        
        # Route to users endpoints (NEW - Real implementation)
        if '/users' in path:
            from handlers.users_handler_real import handle_users_request as handle_users_real
            return handle_users_real(event, cors_headers)
        
        # Default 404
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Endpoint not found: {method} {path}'})
        }
        
    except Exception as e:
        print(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def handle_accounts_request(event, cors_headers):
    """Handle accounts endpoints (existing implementation)"""
    # Import existing accounts handler logic here
    # For now, return placeholder
    return {
        'statusCode': 200,
        'headers': cors_headers,
        'body': json.dumps({
            'success': True,
            'message': 'Accounts endpoint - existing implementation',
            'path': event.get('path')
        })
    }

def handle_dashboard_request(event, cors_headers):
    """Handle dashboard endpoints (placeholder)"""
    try:
        # Extract client_id for multi-tenant
        auth_header = event.get('headers', {}).get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            client_id = extract_client_id_from_token(token)
        else:
            client_id = 'anonymous'
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': {
                    'total_cost': 1250.75,
                    'monthly_trend': 5.2,
                    'top_services': ['EC2', 'S3', 'RDS'],
                    'alerts_count': 2,
                    'client_id': client_id
                },
                'note': 'Dashboard endpoint - placeholder data'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Dashboard error: {str(e)}'})
        }

def handle_insights_request(event, cors_headers):
    """Handle insights endpoints (placeholder)"""
    return {
        'statusCode': 200,
        'headers': cors_headers,
        'body': json.dumps({
            'success': True,
            'data': {
                'recommendations': [
                    {
                        'type': 'rightsizing',
                        'service': 'EC2',
                        'potential_savings': 150.00,
                        'description': 'Resize underutilized instances'
                    }
                ]
            },
            'note': 'Insights endpoint - placeholder data (AWS Bedrock integration pending)'
        })
    }




