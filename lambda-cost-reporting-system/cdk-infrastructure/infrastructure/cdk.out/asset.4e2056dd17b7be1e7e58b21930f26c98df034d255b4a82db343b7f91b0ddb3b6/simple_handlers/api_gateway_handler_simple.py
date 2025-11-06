"""
API Gateway Handler - Direct Processing (No Proxy)
"""

import json
import os

# Environment variables
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'https://costhub.4bfast.com.br').split(',')

def get_cors_origin(request_origin):
    """Get appropriate CORS origin based on request"""
    if request_origin in CORS_ALLOWED_ORIGINS:
        return request_origin
    # Default to first allowed origin
    return CORS_ALLOWED_ORIGINS[0]

def lambda_handler(event, context):
    """Direct API handler - no proxy needed"""
    
    try:
        method = event['httpMethod']
        path = event['path']
        
        # Get origin from request headers
        request_origin = event.get('headers', {}).get('origin') or event.get('headers', {}).get('Origin')
        cors_origin = get_cors_origin(request_origin)
        
        # Process API requests directly
        if method == 'GET':
            # Example: Handle different endpoints
            if '/costs/summary' in path:
                data = {"message": "Cost summary data", "total": 1234.56}
            elif '/costs/trends' in path:
                data = {"message": "Cost trends data", "trend": "increasing"}
            elif '/costs/breakdown' in path:
                data = {"message": "Cost breakdown data", "services": ["EC2", "S3", "RDS"]}
            elif '/accounts' in path:
                data = {"message": "Accounts data", "accounts": []}
            elif '/alarms' in path:
                data = {"message": "Alarms data", "alarms": []}
            elif '/users' in path:
                data = {"message": "Users data", "users": []}
            else:
                data = {"message": "API endpoint", "path": path}
                
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': cors_origin,
                    'Access-Control-Allow-Credentials': 'true',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Request-ID,X-Requested-With',
                    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
                },
                'body': json.dumps(data)
            }
        
        return {
            'statusCode': 405,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': cors_origin,
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({'error': 'Method not allowed'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': CORS_ALLOWED_ORIGINS[0],
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({'error': str(e)})
        }
