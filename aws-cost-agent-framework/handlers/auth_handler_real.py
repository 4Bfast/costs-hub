import json
from services.cognito_service import CognitoService

def handle_auth_request(event, cors_headers):
    """Handle authentication endpoints with real Cognito integration"""
    
    try:
        path = event.get('path', '')
        method = event['httpMethod']
        
        cognito_service = CognitoService()
        
        # Route to specific auth endpoint
        if method == 'POST' and '/auth/login' in path:
            return handle_login(event, cognito_service, cors_headers)
        elif method == 'POST' and '/auth/register' in path:
            return handle_register(event, cognito_service, cors_headers)
        elif method == 'POST' and '/auth/refresh' in path:
            return handle_refresh(event, cognito_service, cors_headers)
        elif method == 'POST' and '/auth/logout' in path:
            return handle_logout(event, cognito_service, cors_headers)
        elif method == 'GET' and '/auth/me' in path:
            return handle_me(event, cognito_service, cors_headers)
        
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Auth endpoint not found: {method} {path}'})
        }
        
    except Exception as e:
        print(f"Error in auth handler: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def handle_login(event, cognito_service, cors_headers):
    """Handle POST /auth/login"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        email = body.get('email')
        password = body.get('password')
        
        if not email or not password:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Email and password are required'})
            }
        
        # Authenticate with Cognito
        result = cognito_service.authenticate_user(email, password)
        
        if result['success']:
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
            
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Login failed: {str(e)}'})
        }

def handle_register(event, cognito_service, cors_headers):
    """Handle POST /auth/register"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        email = body.get('email')
        password = body.get('password')
        name = body.get('name')
        
        if not email or not password:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Email and password are required'})
            }
        
        # Register with Cognito
        result = cognito_service.register_user(email, password, name)
        
        if result['success']:
            return {
                'statusCode': 201,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
            
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Registration failed: {str(e)}'})
        }

def handle_refresh(event, cognito_service, cors_headers):
    """Handle POST /auth/refresh"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        refresh_token = body.get('refresh_token')
        if not refresh_token:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Refresh token is required'})
            }
        
        # Refresh token with Cognito
        result = cognito_service.refresh_token(refresh_token)
        
        if result['success']:
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
            
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Token refresh failed: {str(e)}'})
        }

def handle_logout(event, cognito_service, cors_headers):
    """Handle POST /auth/logout"""
    try:
        # Get access token from header
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Bearer token required'})
            }
        
        access_token = auth_header.replace('Bearer ', '')
        
        # Logout with Cognito
        result = cognito_service.logout_user(access_token)
        
        if result['success']:
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Logout failed: {str(e)}'})
        }

def handle_me(event, cognito_service, cors_headers):
    """Handle GET /auth/me"""
    try:
        # Get access token from header
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Bearer token required'})
            }
        
        access_token = auth_header.replace('Bearer ', '')
        
        # Get user info from Cognito
        try:
            user_info = cognito_service.get_user_by_token(access_token)
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'success': True,
                    'data': user_info
                })
            }
            
        except ValueError as e:
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps({'error': str(e)})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to get user info: {str(e)}'})
        }
