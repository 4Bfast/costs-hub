"""
Simple API Gateway Handler - Proxy to backend
"""

import json
import urllib.request
import urllib.parse
import os

BACKEND_BASE_URL = os.environ.get('BACKEND_BASE_URL', 'https://jrltysmyg5.execute-api.us-east-1.amazonaws.com')

def lambda_handler(event, context):
    """Simple proxy handler"""
    
    try:
        method = event['httpMethod']
        path = event['path']
        
        # Get origin from request headers
        origin = event.get('headers', {}).get('origin', 'https://costhub.4bfast.com.br')
        
        # Map /api/v1/* to backend /*
        backend_path = path.replace('/api/v1', '')
        if not backend_path:
            backend_path = '/'
        
        backend_url = f"{BACKEND_BASE_URL}{backend_path}"
        
        # Simple GET request to backend
        if method == 'GET':
            try:
                with urllib.request.urlopen(backend_url) as response:
                    data = response.read().decode('utf-8')
                    
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': origin,
                        'Access-Control-Allow-Credentials': 'true',
                        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Request-ID,X-Requested-With',
                        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
                    },
                    'body': data
                }
            except Exception as e:
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': origin,
                        'Access-Control-Allow-Credentials': 'true'
                    },
                    'body': json.dumps({'error': str(e)})
                }
        
        return {
            'statusCode': 405,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': origin,
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({'error': 'Method not allowed'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': origin,
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({'error': str(e)})
        }
