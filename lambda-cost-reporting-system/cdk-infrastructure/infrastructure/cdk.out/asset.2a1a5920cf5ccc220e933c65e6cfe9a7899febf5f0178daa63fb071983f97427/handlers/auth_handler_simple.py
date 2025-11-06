"""
Simple Authentication Handler - Cognito Integration
Minimal implementation for auth endpoints: login, register, logout, refresh, me
"""

import json
import boto3
import os
from botocore.exceptions import ClientError

# Cognito configuration
USER_POOL_ID = "us-east-1_94OYkzcSO"
CLIENT_ID = "23qrdk4pl1lidrhsflpsitl4u2"
REGION = "us-east-1"

def get_cors_headers():
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': 'https://costhub.4bfast.com.br',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def handle_login(event):
    """Handle user login"""
    try:
        body = json.loads(event.get('body', '{}'))
        username = body.get('username')
        password = body.get('password')
        
        if not username or not password:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Username and password required'})
            }
        
        cognito = boto3.client('cognito-idp', region_name=REGION)
        
        response = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': 'Login successful',
                'tokens': response['AuthenticationResult']
            })
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NotAuthorizedException':
            return {
                'statusCode': 401,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Invalid credentials'})
            }
        else:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': str(e)})
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def handle_register(event):
    """Handle user registration"""
    try:
        body = json.loads(event.get('body', '{}'))
        username = body.get('username')
        password = body.get('password')
        email = body.get('email')
        
        if not username or not password or not email:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Username, password and email required'})
            }
        
        cognito = boto3.client('cognito-idp', region_name=REGION)
        
        response = cognito.sign_up(
            ClientId=CLIENT_ID,
            Username=username,
            Password=password,
            UserAttributes=[
                {'Name': 'email', 'Value': email}
            ]
        )
        
        return {
            'statusCode': 201,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': 'User registered successfully',
                'userSub': response['UserSub']
            })
        }
        
    except ClientError as e:
        return {
            'statusCode': 400,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def handle_logout(event):
    """Handle user logout"""
    try:
        body = json.loads(event.get('body', '{}'))
        access_token = body.get('access_token')
        
        if not access_token:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Access token required'})
            }
        
        cognito = boto3.client('cognito-idp', region_name=REGION)
        
        cognito.global_sign_out(AccessToken=access_token)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': 'Logout successful'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def handle_refresh(event):
    """Handle token refresh"""
    try:
        body = json.loads(event.get('body', '{}'))
        refresh_token = body.get('refresh_token')
        
        if not refresh_token:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Refresh token required'})
            }
        
        cognito = boto3.client('cognito-idp', region_name=REGION)
        
        response = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token
            }
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': 'Token refreshed successfully',
                'tokens': response['AuthenticationResult']
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def handle_me(event):
    """Handle get user info"""
    try:
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Authorization token required'})
            }
        
        access_token = auth_header.replace('Bearer ', '')
        
        cognito = boto3.client('cognito-idp', region_name=REGION)
        
        response = cognito.get_user(AccessToken=access_token)
        
        user_attributes = {}
        for attr in response['UserAttributes']:
            user_attributes[attr['Name']] = attr['Value']
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'username': response['Username'],
                'attributes': user_attributes
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def lambda_handler(event, context):
    """Main handler for auth endpoints"""
    
    method = event['httpMethod']
    path = event['path']
    
    try:
        if method == 'POST' and path.endswith('/auth/login'):
            return handle_login(event)
        elif method == 'POST' and path.endswith('/auth/register'):
            return handle_register(event)
        elif method == 'POST' and path.endswith('/auth/logout'):
            return handle_logout(event)
        elif method == 'POST' and path.endswith('/auth/refresh'):
            return handle_refresh(event)
        elif method == 'GET' and path.endswith('/auth/me'):
            return handle_me(event)
        else:
            return {
                'statusCode': 404,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }
