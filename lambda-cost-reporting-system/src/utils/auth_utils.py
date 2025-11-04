"""
Authorization utilities for protected endpoints
"""
import json
import boto3
from botocore.exceptions import ClientError

def validate_authorization(event, cors_headers):
    """
    Validate authorization token from request headers
    Returns: (is_valid, error_response, user_info)
    """
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization') or headers.get('authorization', '')
    
    if not auth_header.startswith('Bearer '):
        error_response = {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Unauthorized'})
        }
        return False, error_response, None
    
    access_token = auth_header.replace('Bearer ', '')
    
    try:
        # Validate token with Cognito
        cognito = boto3.client('cognito-idp', region_name='us-east-1')
        response = cognito.get_user(AccessToken=access_token)
        
        # Extract user info
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
        error_code = e.response['Error']['Code']
        if error_code in ['NotAuthorizedException', 'UserNotFoundException']:
            error_response = {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Unauthorized'})
            }
        else:
            error_response = {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({'error': f'Auth validation error: {str(e)}'})
            }
        return False, error_response, None
    
    except Exception as e:
        error_response = {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Auth error: {str(e)}'})
        }
        return False, error_response, None
