"""
Accounts Handler - Account management
"""
import json
import boto3
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
        return True, None, {'username': response['Username']}
    except:
        return False, {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Unauthorized'})
        }, None

def handle_accounts_request(event, cors_headers):
    """Handle accounts endpoints"""
    # Validate authorization first
    is_valid, error_response, user_info = validate_authorization_inline(event, cors_headers)
    if not is_valid:
        return error_response
    
    path = event['path']
    method = event['httpMethod']
    
    try:
        if method == 'GET' and path.endswith('/accounts'):
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Accounts endpoint working',
                    'accounts': []
                })
            }
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Accounts endpoint not found'})
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Accounts error: {str(e)}'})
        }
