"""
API Gateway Handler - Real Implementation Only
No mocks - all endpoints use real handlers
"""

import json
import os

CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'https://costhub.4bfast.com.br').split(',')

def get_cors_headers(request_origin):
    """Get CORS headers"""
    origin = request_origin if request_origin in CORS_ALLOWED_ORIGINS else CORS_ALLOWED_ORIGINS[0]
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Request-ID,X-Requested-With',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def lambda_handler(event, context):
    """Route requests to real handlers only"""
    
    try:
        method = event['httpMethod']
        path = event['path']
        request_origin = event.get('headers', {}).get('origin') or event.get('headers', {}).get('Origin')
        cors_headers = get_cors_headers(request_origin)
        
        # Route to real handlers
        if '/auth' in path:
            from handlers.auth_handler import lambda_handler as auth_handler
            return auth_handler(event, context)
            
        elif '/accounts' in path:
            from handlers.accounts_handler import lambda_handler as accounts_handler
            return accounts_handler(event, context)
        
        elif '/costs' in path:
            from handlers.costs_handler import lambda_handler as costs_handler
            return costs_handler(event, context)
            
        elif '/alarms' in path:
            from handlers.alarms_handler import lambda_handler as alarms_handler
            return alarms_handler(event, context)
            
        elif '/users' in path:
            from handlers.users_handler import lambda_handler as users_handler
            return users_handler(event, context)
        
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
        
    except ImportError as e:
        return {
            'statusCode': 501,
            'headers': get_cors_headers(None),
            'body': json.dumps({'error': f'Handler not implemented: {str(e)}'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(None),
            'body': json.dumps({'error': str(e)})
        }
