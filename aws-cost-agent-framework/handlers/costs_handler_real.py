import json
import boto3
from datetime import datetime, timedelta
from services.aws_cost_service import AWSCostService
from utils.jwt_utils_simple import extract_client_id_from_token
from config.settings import config

def handle_costs_request(event, cors_headers):
    """Handle costs endpoints with real AWS Cost Explorer data"""
    
    try:
        # Extract client_id from JWT token
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Unauthorized - Bearer token required'})
            }
        
        token = auth_header.replace('Bearer ', '')
        client_id = extract_client_id_from_token(token)
        
        # Get account configuration from DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
        accounts_table = dynamodb.Table(config.DYNAMODB_ACCOUNTS_TABLE)
        
        # Get accounts for this client
        response = accounts_table.scan(
            FilterExpression='client_id = :client_id AND #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':client_id': client_id,
                ':status': 'active'
            }
        )
        accounts = response.get('Items', [])
        
        if not accounts:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': 'No active accounts configured for this client',
                    'client_id': client_id
                })
            }
        
        path = event['path']
        method = event['httpMethod']
        query_params = event.get('queryStringParameters') or {}
        
        # Route to specific cost endpoint
        if method == 'GET':
            if path.endswith('/costs') or path.endswith('/costs/'):
                return handle_general_costs(accounts, client_id, query_params, cors_headers)
            elif path.endswith('/costs/summary'):
                return handle_cost_summary(accounts, client_id, query_params, cors_headers)
            elif path.endswith('/costs/trends'):
                return handle_cost_trends(accounts, client_id, query_params, cors_headers)
            elif path.endswith('/costs/breakdown'):
                return handle_cost_breakdown(accounts, client_id, query_params, cors_headers)
            elif path.endswith('/costs/by-service'):
                return handle_cost_by_service(accounts, client_id, query_params, cors_headers)
            elif path.endswith('/costs/by-region'):
                return handle_cost_by_region(accounts, client_id, query_params, cors_headers)
        
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Cost endpoint not found: {method} {path}'})
        }
        
    except Exception as e:
        print(f"Error in costs handler: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def handle_general_costs(accounts, client_id, query_params, cors_headers):
    """Handle GET /costs - general cost overview"""
    try:
        # Use first account for now (multi-account aggregation in future)
        cost_service = AWSCostService(accounts[0])
        
        # Get date range from query params or default to last 30 days
        days = int(query_params.get('days', 30))
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Get summary and trends
        summary = cost_service.get_cost_summary(start_date, end_date)
        trends = cost_service.get_cost_trends(days)
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': {
                    'summary': summary,
                    'trends': trends,
                    'client_id': client_id,
                    'accounts_count': len(accounts),
                    'period_days': days
                }
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to get general costs: {str(e)}'})
        }

def handle_cost_summary(accounts, client_id, query_params, cors_headers):
    """Handle GET /costs/summary"""
    try:
        cost_service = AWSCostService(accounts[0])
        
        # Get date range from query params
        start_date = query_params.get('start_date')
        end_date = query_params.get('end_date')
        
        if not start_date or not end_date:
            # Default to current month
            now = datetime.now()
            start_date = now.replace(day=1).strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')
        
        data = cost_service.get_cost_summary(start_date, end_date)
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': data,
                'client_id': client_id,
                'accounts_count': len(accounts)
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to get cost summary: {str(e)}'})
        }

def handle_cost_trends(accounts, client_id, query_params, cors_headers):
    """Handle GET /costs/trends"""
    try:
        cost_service = AWSCostService(accounts[0])
        
        days = int(query_params.get('days', 30))
        data = cost_service.get_cost_trends(days)
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': data,
                'client_id': client_id
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to get cost trends: {str(e)}'})
        }

def handle_cost_breakdown(accounts, client_id, query_params, cors_headers):
    """Handle GET /costs/breakdown"""
    try:
        cost_service = AWSCostService(accounts[0])
        
        group_by = query_params.get('group_by', 'SERVICE')
        days = int(query_params.get('days', 30))
        
        # Validate group_by parameter
        valid_groups = ['SERVICE', 'REGION', 'USAGE_TYPE', 'INSTANCE_TYPE', 'LINKED_ACCOUNT']
        if group_by not in valid_groups:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': f'Invalid group_by parameter. Valid options: {valid_groups}'
                })
            }
        
        data = cost_service.get_cost_breakdown(group_by, days)
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': data,
                'client_id': client_id
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to get cost breakdown: {str(e)}'})
        }

def handle_cost_by_service(accounts, client_id, query_params, cors_headers):
    """Handle GET /costs/by-service"""
    try:
        cost_service = AWSCostService(accounts[0])
        
        days = int(query_params.get('days', 30))
        data = cost_service.get_cost_by_service(days)
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': data,
                'client_id': client_id
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to get costs by service: {str(e)}'})
        }

def handle_cost_by_region(accounts, client_id, query_params, cors_headers):
    """Handle GET /costs/by-region"""
    try:
        cost_service = AWSCostService(accounts[0])
        
        days = int(query_params.get('days', 30))
        data = cost_service.get_cost_by_region(days)
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': data,
                'client_id': client_id
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to get costs by region: {str(e)}'})
        }
