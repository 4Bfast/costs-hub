"""
Dashboard Handler - Real-time cost analytics
"""
import json
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

def validate_authorization_inline(event, cors_headers):
    """Inline authorization validation"""
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization') or headers.get('authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return False, {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Unauthorized'})
        }, None
    
    access_token = auth_header.replace('Bearer ', '')
    
    try:
        cognito = boto3.client('cognito-idp', region_name='us-east-1')
        response = cognito.get_user(AccessToken=access_token)
        
        user_attributes = {}
        for attr in response['UserAttributes']:
            user_attributes[attr['Name']] = attr['Value']
        
        user_info = {
            'username': response['Username'],
            'email': user_attributes.get('email'),
            'attributes': user_attributes
        }
        
        return True, None, user_info
        
    except ClientError as e:
        return False, {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Unauthorized'})
        }, None
    except Exception as e:
        return False, {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Auth error: {str(e)}'})
        }, None

def handle_dashboard_request(event, cors_headers):
    """Handle dashboard endpoints"""
    # Validate authorization first
    is_valid, error_response, user_info = validate_authorization_inline(event, cors_headers)
    if not is_valid:
        return error_response
    
    path = event['path']
    method = event['httpMethod']
    
    try:
        if method == 'GET' and path.endswith('/dashboard/metrics'):
            # Return mock dashboard metrics
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'total_monthly_cost': 1250.75,
                    'month_over_month_change': 5.2,
                    'connected_accounts': 3,
                    'active_alarms': 2,
                    'unread_insights': 5,
                    'cost_trend_7d': [
                        {'date': '2025-10-28', 'cost': 42.50},
                        {'date': '2025-10-29', 'cost': 38.75},
                        {'date': '2025-10-30', 'cost': 45.20},
                        {'date': '2025-10-31', 'cost': 41.80},
                        {'date': '2025-11-01', 'cost': 39.90},
                        {'date': '2025-11-02', 'cost': 43.15},
                        {'date': '2025-11-03', 'cost': 40.25}
                    ],
                    'top_service': {
                        'service_name': 'Amazon EC2',
                        'cost': 485.30,
                        'percentage': 38.8
                    },
                    'provider_distribution': [
                        {
                            'provider': 'AWS',
                            'cost': 1250.75,
                            'percentage': 100.0,
                            'account_count': 3
                        }
                    ],
                    'recent_activity': [
                        {
                            'type': 'cost_spike',
                            'title': 'EC2 Cost Spike Detected',
                            'description': 'EC2 costs increased by 15% in the last 24 hours',
                            'timestamp': '2025-11-03T20:30:00Z',
                            'severity': 'medium'
                        },
                        {
                            'type': 'new_insight',
                            'title': 'New Optimization Opportunity',
                            'description': 'Potential savings of $120/month identified',
                            'timestamp': '2025-11-03T18:15:00Z',
                            'severity': 'low'
                        }
                    ]
                })
            }
        
        elif method == 'GET' and path.endswith('/dashboard'):
            # Return basic dashboard data
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Dashboard endpoint working',
                    'total_cost': 1250.75,
                    'accounts': 3,
                    'services': 12
                })
            }
        
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Dashboard endpoint not found'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Dashboard error: {str(e)}'})
        }
