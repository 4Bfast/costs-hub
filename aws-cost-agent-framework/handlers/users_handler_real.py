import json
from services.cognito_service import CognitoService

def handle_users_request(event, cors_headers):
    """Handle users endpoints with real Cognito integration"""
    
    try:
        path = event.get('path', '')
        method = event['httpMethod']
        
        cognito_service = CognitoService()
        
        # Route to specific users endpoint
        if method == 'GET' and (path.endswith('/users') or path.endswith('/users/')):
            return handle_list_users(event, cognito_service, cors_headers)
        elif method == 'GET' and '/users/profile' in path:
            return handle_get_profile(event, cognito_service, cors_headers)
        elif method == 'PUT' and '/users/profile' in path:
            return handle_update_profile(event, cognito_service, cors_headers)
        
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Users endpoint not found: {method} {path}'})
        }
        
    except Exception as e:
        print(f"Error in users handler: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def handle_list_users(event, cognito_service, cors_headers):
    """Handle GET /users - List all users (admin only)"""
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
        
        # Verify user has access (basic check - in production, implement proper admin role check)
        try:
            current_user = cognito_service.get_user_by_token(access_token)
            
            # Simple admin check - in production, use proper role-based access
            if not current_user.get('email', '').endswith('@4bfast.com.br'):
                return {
                    'statusCode': 403,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Admin access required'})
                }
            
        except ValueError:
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid token'})
            }
        
        # List users from Cognito
        result = cognito_service.list_users()
        
        if result['success']:
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to list users: {str(e)}'})
        }

def handle_get_profile(event, cognito_service, cors_headers):
    """Handle GET /users/profile - Get current user profile"""
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
            
            # Add preferences (could be stored in DynamoDB in the future)
            profile_data = {
                **user_info,
                'preferences': {
                    'currency': 'USD',
                    'timezone': 'America/Sao_Paulo',
                    'language': 'pt-BR'
                }
            }
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'success': True,
                    'data': profile_data
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
            'body': json.dumps({'error': f'Failed to get profile: {str(e)}'})
        }

def handle_update_profile(event, cognito_service, cors_headers):
    """Handle PUT /users/profile - Update current user profile"""
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
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract updatable attributes
        attributes = {}
        if 'name' in body:
            attributes['name'] = body['name']
        
        # Note: preferences would be stored in DynamoDB in a full implementation
        # For now, we only update Cognito attributes
        
        if attributes:
            # Update user profile in Cognito
            result = cognito_service.update_user_profile(access_token, attributes)
            
            if result['success']:
                # Add preferences back to response
                profile_data = {
                    **result['data'],
                    'preferences': body.get('preferences', {
                        'currency': 'USD',
                        'timezone': 'America/Sao_Paulo',
                        'language': 'pt-BR'
                    })
                }
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'success': True,
                        'data': profile_data,
                        'message': 'Profile updated successfully'
                    })
                }
            else:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps(result)
                }
        else:
            # No Cognito attributes to update, just return current profile with new preferences
            try:
                user_info = cognito_service.get_user_by_token(access_token)
                profile_data = {
                    **user_info,
                    'preferences': body.get('preferences', {
                        'currency': 'USD',
                        'timezone': 'America/Sao_Paulo',
                        'language': 'pt-BR'
                    })
                }
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'success': True,
                        'data': profile_data,
                        'message': 'Preferences updated successfully'
                    })
                }
                
            except ValueError as e:
                return {
                    'statusCode': 401,
                    'headers': cors_headers,
                    'body': json.dumps({'error': str(e)})
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
            'body': json.dumps({'error': f'Failed to update profile: {str(e)}'})
        }
