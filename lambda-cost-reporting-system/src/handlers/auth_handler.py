"""
Authentication Handler - Cognito Integration
Implements auth endpoints: login, register, logout, refresh, me
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
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }

def handle_login(event):
    """POST /auth/login - Authenticate user with Cognito"""
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        password = body.get('password')
        
        if not email or not password:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Email and password required'})
            }
        
        client = boto3.client('cognito-idp', region_name=REGION)
        
        response = client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        auth_result = response['AuthenticationResult']
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': 'Login successful',
                'accessToken': auth_result['AccessToken'],
                'idToken': auth_result['IdToken'],
                'refreshToken': auth_result['RefreshToken'],
                'expiresIn': auth_result['ExpiresIn']
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
    """POST /auth/register - Register new user"""
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        password = body.get('password')
        name = body.get('name', '')
        
        if not email or not password:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Email and password required'})
            }
        
        client = boto3.client('cognito-idp', region_name=REGION)
        
        response = client.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'name', 'Value': name}
            ]
        )
        
        return {
            'statusCode': 201,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': 'User registered successfully',
                'userSub': response['UserSub'],
                'confirmationRequired': not response.get('UserConfirmed', False)
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
    """POST /auth/logout - Logout user"""
    try:
        # Extract access token from Authorization header
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Invalid authorization header'})
            }
        
        access_token = auth_header[7:]  # Remove 'Bearer '
        
        client = boto3.client('cognito-idp', region_name=REGION)
        client.global_sign_out(AccessToken=access_token)
        
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
    """POST /auth/refresh - Refresh tokens"""
    try:
        body = json.loads(event.get('body', '{}'))
        refresh_token = body.get('refreshToken')
        
        if not refresh_token:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Refresh token required'})
            }
        
        client = boto3.client('cognito-idp', region_name=REGION)
        
        response = client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token
            }
        )
        
        auth_result = response['AuthenticationResult']
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': 'Tokens refreshed',
                'accessToken': auth_result['AccessToken'],
                'idToken': auth_result['IdToken'],
                'expiresIn': auth_result['ExpiresIn']
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def handle_me(event):
    """GET /auth/me - Get current user info"""
    try:
        # Extract access token from Authorization header
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Invalid authorization header'})
            }
        
        access_token = auth_header[7:]  # Remove 'Bearer '
        
        client = boto3.client('cognito-idp', region_name=REGION)
        response = client.get_user(AccessToken=access_token)
        
        # Extract user attributes
        user_attributes = {}
        for attr in response.get('UserAttributes', []):
            user_attributes[attr['Name']] = attr['Value']
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'username': response['Username'],
                'email': user_attributes.get('email'),
                'name': user_attributes.get('name'),
                'email_verified': user_attributes.get('email_verified') == 'true',
                'user_status': response.get('UserStatus')
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
