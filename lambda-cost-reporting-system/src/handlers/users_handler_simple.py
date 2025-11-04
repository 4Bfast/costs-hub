"""
Users Handler - Cognito integration
"""
import json
import boto3
from botocore.exceptions import ClientError

USER_POOL_ID = "us-east-1_94OYkzcSO"
REGION = "us-east-1"

def handle_users_request(event, cors_headers):
    """Handle users endpoints"""
    path = event['path']
    method = event['httpMethod']
    
    cognito = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        if method == 'GET' and path.endswith('/users'):
            # GET /users - List all users
            response = cognito.list_users(UserPoolId=USER_POOL_ID)
            users = []
            
            for user in response.get('Users', []):
                user_data = {
                    'username': user['Username'],
                    'status': user['UserStatus'],
                    'created': user['UserCreateDate'].isoformat(),
                    'attributes': {}
                }
                
                for attr in user.get('Attributes', []):
                    user_data['attributes'][attr['Name']] = attr['Value']
                
                users.append(user_data)
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Users retrieved successfully',
                    'data': {
                        'users': users,
                        'count': len(users)
                    }
                })
            }
            
        elif method == 'GET' and path.endswith('/users/profile'):
            # GET /users/profile - Get current user profile
            headers = event.get('headers', {})
            auth_header = headers.get('Authorization', '')
            
            if not auth_header.startswith('Bearer '):
                return {
                    'statusCode': 401,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Authorization token required'})
                }
            
            access_token = auth_header.replace('Bearer ', '')
            response = cognito.get_user(AccessToken=access_token)
            
            user_attributes = {}
            for attr in response['UserAttributes']:
                user_attributes[attr['Name']] = attr['Value']
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Profile retrieved successfully',
                    'data': {
                        'username': response['Username'],
                        'attributes': user_attributes
                    }
                })
            }
            
        elif method == 'GET' and path.endswith('/users/stats'):
            # GET /users/stats - Get user statistics
            response = cognito.list_users(UserPoolId=USER_POOL_ID)
            users = response.get('Users', [])
            
            # Count users by status
            active_users = len([u for u in users if u['UserStatus'] == 'CONFIRMED'])
            pending_users = len([u for u in users if u['UserStatus'] in ['UNCONFIRMED', 'FORCE_CHANGE_PASSWORD']])
            
            # Count by role (assuming role is stored in custom attributes)
            admin_count = 0
            member_count = 0
            
            for user in users:
                role = 'MEMBER'  # default
                for attr in user.get('Attributes', []):
                    if attr['Name'] == 'custom:role':
                        role = attr['Value']
                        break
                
                if role == 'ADMIN':
                    admin_count += 1
                else:
                    member_count += 1
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'User stats retrieved successfully',
                    'data': {
                        'total_users': len(users),
                        'active_users': active_users,
                        'pending_invitations': pending_users,
                        'admin_count': admin_count,
                        'member_count': member_count,
                        'last_activity': '2025-11-03T23:00:00Z'
                    }
                })
            }
            
        elif method == 'GET' and path.endswith('/users/limits'):
            # GET /users/limits - Get organization member limits
            response = cognito.list_users(UserPoolId=USER_POOL_ID)
            current_count = len(response.get('Users', []))
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'User limits retrieved successfully',
                    'data': {
                        'current_count': current_count,
                        'max_allowed': 10,  # Default limit
                        'pending_invitations': 0,  # Would need separate tracking
                        'can_invite_more': current_count < 10
                    }
                })
            }
            
        elif method == 'PUT' and path.endswith('/users/profile'):
            # PUT /users/profile - Update user profile
            headers = event.get('headers', {})
            auth_header = headers.get('Authorization', '')
            
            if not auth_header.startswith('Bearer '):
                return {
                    'statusCode': 401,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Authorization token required'})
                }
            
            access_token = auth_header.replace('Bearer ', '')
            body = json.loads(event.get('body', '{}'))
            
            # Update user attributes
            user_attributes = []
            if body.get('email'):
                user_attributes.append({'Name': 'email', 'Value': body['email']})
            if body.get('name'):
                user_attributes.append({'Name': 'name', 'Value': body['name']})
            if body.get('phone_number'):
                user_attributes.append({'Name': 'phone_number', 'Value': body['phone_number']})
            
            if user_attributes:
                cognito.update_user_attributes(
                    AccessToken=access_token,
                    UserAttributes=user_attributes
                )
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Profile updated successfully',
                    'data': {'updated_attributes': len(user_attributes)}
                })
            }
        
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': 'User endpoint not found'})
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NotAuthorizedException':
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid or expired token'})
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
            'body': json.dumps({'error': f'User operation error: {str(e)}'})
        }
