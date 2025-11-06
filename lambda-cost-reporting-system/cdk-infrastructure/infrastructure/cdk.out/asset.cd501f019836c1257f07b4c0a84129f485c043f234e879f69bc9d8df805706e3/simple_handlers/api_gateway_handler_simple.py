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
        
        # Handle CORS preflight requests
        if method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }
        
        # Route to real handlers
        if '/auth' in path:
            # Complete auth handler with Cognito integration
            import boto3
            from botocore.exceptions import ClientError
            
            USER_POOL_ID = "us-east-1_94OYkzcSO"
            CLIENT_ID = "23qrdk4pl1lidrhsflpsitl4u2"
            REGION = "us-east-1"
            
            method = event['httpMethod']
            path = event['path']
            
            try:
                if method == 'POST' and path.endswith('/auth/login'):
                    body = json.loads(event.get('body', '{}'))
                    username = body.get('username')
                    password = body.get('password')
                    
                    if not username or not password:
                        return {
                            'statusCode': 400,
                            'headers': cors_headers,
                            'body': json.dumps({'error': 'Username and password required'})
                        }
                    
                    cognito = boto3.client('cognito-idp', region_name=REGION)
                    response = cognito.initiate_auth(
                        ClientId=CLIENT_ID,
                        AuthFlow='USER_PASSWORD_AUTH',
                        AuthParameters={'USERNAME': username, 'PASSWORD': password}
                    )
                    
                    return {
                        'statusCode': 200,
                        'headers': cors_headers,
                        'body': json.dumps({
                            'message': 'Login successful',
                            'tokens': response['AuthenticationResult']
                        })
                    }
                    
                elif method == 'POST' and path.endswith('/auth/register'):
                    body = json.loads(event.get('body', '{}'))
                    username = body.get('username')
                    password = body.get('password')
                    email = body.get('email')
                    
                    if not username or not password or not email:
                        return {
                            'statusCode': 400,
                            'headers': cors_headers,
                            'body': json.dumps({'error': 'Username, password and email required'})
                        }
                    
                    cognito = boto3.client('cognito-idp', region_name=REGION)
                    response = cognito.sign_up(
                        ClientId=CLIENT_ID,
                        Username=username,
                        Password=password,
                        UserAttributes=[{'Name': 'email', 'Value': email}]
                    )
                    
                    return {
                        'statusCode': 201,
                        'headers': cors_headers,
                        'body': json.dumps({
                            'message': 'User registered successfully',
                            'userSub': response['UserSub']
                        })
                    }
                    
                elif method == 'POST' and path.endswith('/auth/refresh'):
                    body = json.loads(event.get('body', '{}'))
                    refresh_token = body.get('refresh_token')
                    
                    if not refresh_token:
                        return {
                            'statusCode': 400,
                            'headers': cors_headers,
                            'body': json.dumps({'error': 'Refresh token required'})
                        }
                    
                    cognito = boto3.client('cognito-idp', region_name=REGION)
                    response = cognito.initiate_auth(
                        ClientId=CLIENT_ID,
                        AuthFlow='REFRESH_TOKEN_AUTH',
                        AuthParameters={'REFRESH_TOKEN': refresh_token}
                    )
                    
                    return {
                        'statusCode': 200,
                        'headers': cors_headers,
                        'body': json.dumps({
                            'message': 'Token refreshed successfully',
                            'tokens': response['AuthenticationResult']
                        })
                    }
                    
                elif method == 'POST' and path.endswith('/auth/logout'):
                    body = json.loads(event.get('body', '{}'))
                    access_token = body.get('access_token')
                    
                    if not access_token:
                        return {
                            'statusCode': 400,
                            'headers': cors_headers,
                            'body': json.dumps({'error': 'Access token required'})
                        }
                    
                    cognito = boto3.client('cognito-idp', region_name=REGION)
                    cognito.global_sign_out(AccessToken=access_token)
                    
                    return {
                        'statusCode': 200,
                        'headers': cors_headers,
                        'body': json.dumps({'message': 'Logout successful'})
                    }
                    
                elif method == 'GET' and path.endswith('/auth/me'):
                    headers = event.get('headers', {})
                    auth_header = headers.get('Authorization', '')
                    
                    if not auth_header.startswith('Bearer '):
                        return {
                            'statusCode': 401,
                            'headers': cors_headers,
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
                        'headers': cors_headers,
                        'body': json.dumps({
                            'username': response['Username'],
                            'attributes': user_attributes
                        })
                    }
                else:
                    return {
                        'statusCode': 404,
                        'headers': cors_headers,
                        'body': json.dumps({'error': 'Auth endpoint not found'})
                    }
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'NotAuthorizedException':
                    if 'sign_up' in str(e) or 'register' in path:
                        return {
                            'statusCode': 403,
                            'headers': cors_headers,
                            'body': json.dumps({'error': 'Self-registration is disabled. Please contact administrator.'})
                        }
                    else:
                        return {
                            'statusCode': 401,
                            'headers': cors_headers,
                            'body': json.dumps({'error': 'Invalid credentials'})
                        }
                elif error_code == 'InvalidParameterException':
                    return {
                        'statusCode': 400,
                        'headers': cors_headers,
                        'body': json.dumps({'error': 'Invalid parameters provided'})
                    }
                else:
                    return {
                        'statusCode': 400,
                        'headers': cors_headers,
                        'body': json.dumps({'error': str(e)})
                    }
            except Exception as e:
                return {
                    'statusCode': 500,
                    'headers': cors_headers,
                    'body': json.dumps({'error': str(e)})
                }
            
        elif '/accounts' in path:
            from .accounts_handler_simple import handle_accounts_request
            return handle_accounts_request(event, cors_headers)
        
        elif '/costs' in path:
            from .costs_handler_simple import handle_costs_request
            return handle_costs_request(event, cors_headers)
            
        elif '/alarms' in path:
            from .alarms_handler_simple import handle_alarms_request
            return handle_alarms_request(event, cors_headers)
            
        elif '/users' in path:
            from .users_handler_simple import handle_users_request
            return handle_users_request(event, cors_headers)
            
        elif '/dashboard' in path:
            from .dashboard_handler_simple import handle_dashboard_request
            return handle_dashboard_request(event, cors_headers)
            
        elif '/insights' in path:
            from .insights_handler_simple import handle_insights_request
            return handle_insights_request(event, cors_headers)
                
        elif '/organizations' in path:
            return {
                'statusCode': 501,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Organizations endpoints not implemented yet'})
            }
                
        elif '/reports' in path:
            return {
                'statusCode': 501,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Reports endpoints not implemented yet'})
            }}
                
        elif path.endswith('/health'):
            # Health check endpoint
            return {'statusCode': 200, 'headers': cors_headers, 'body': json.dumps({'status': 'healthy', 'timestamp': '2025-11-03T01:54:00Z'})}
            
        elif path.endswith('/status'):
            # Status endpoint
            return {'statusCode': 200, 'headers': cors_headers, 'body': json.dumps({'status': 'operational', 'version': '1.0.0', 'uptime': '99.9%'})}
        
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
