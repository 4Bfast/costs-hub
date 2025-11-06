import boto3
import json
from datetime import datetime
from config.settings import config

class CognitoService:
    """AWS Cognito integration service for user management"""
    
    def __init__(self):
        self.cognito = boto3.client('cognito-idp', region_name=config.AWS_REGION)
        self.user_pool_id = config.COGNITO_USER_POOL_ID
        self.client_id = config.COGNITO_CLIENT_ID
    
    def authenticate_user(self, email: str, password: str) -> dict:
        """Authenticate user with Cognito"""
        try:
            response = self.cognito.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password
                }
            )
            
            auth_result = response['AuthenticationResult']
            
            # Get user info
            user_info = self.get_user_by_token(auth_result['AccessToken'])
            
            return {
                'success': True,
                'data': {
                    'access_token': auth_result['AccessToken'],
                    'refresh_token': auth_result.get('RefreshToken'),
                    'expires_in': auth_result['ExpiresIn'],
                    'user': user_info
                }
            }
            
        except self.cognito.exceptions.NotAuthorizedException:
            return {'success': False, 'error': 'Invalid email or password'}
        except self.cognito.exceptions.UserNotConfirmedException:
            return {'success': False, 'error': 'User email not confirmed'}
        except Exception as e:
            return {'success': False, 'error': f'Authentication failed: {str(e)}'}
    
    def register_user(self, email: str, password: str, name: str = None) -> dict:
        """Register new user in Cognito"""
        try:
            user_attributes = [
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'}
            ]
            
            if name:
                user_attributes.append({'Name': 'name', 'Value': name})
            
            response = self.cognito.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=user_attributes,
                TemporaryPassword=password,
                MessageAction='SUPPRESS'  # Don't send welcome email
            )
            
            # Set permanent password
            self.cognito.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=email,
                Password=password,
                Permanent=True
            )
            
            return {
                'success': True,
                'data': {
                    'user_id': response['User']['Username'],
                    'email': email,
                    'status': response['User']['UserStatus'],
                    'message': 'User created successfully'
                }
            }
            
        except self.cognito.exceptions.UsernameExistsException:
            return {'success': False, 'error': 'User already exists'}
        except Exception as e:
            return {'success': False, 'error': f'Registration failed: {str(e)}'}
    
    def refresh_token(self, refresh_token: str) -> dict:
        """Refresh access token"""
        try:
            response = self.cognito.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            auth_result = response['AuthenticationResult']
            
            return {
                'success': True,
                'data': {
                    'access_token': auth_result['AccessToken'],
                    'expires_in': auth_result['ExpiresIn']
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Token refresh failed: {str(e)}'}
    
    def logout_user(self, access_token: str) -> dict:
        """Logout user (invalidate token)"""
        try:
            self.cognito.global_sign_out(AccessToken=access_token)
            return {'success': True, 'message': 'Logged out successfully'}
        except Exception as e:
            return {'success': False, 'error': f'Logout failed: {str(e)}'}
    
    def get_user_by_token(self, access_token: str) -> dict:
        """Get user info from access token"""
        try:
            response = self.cognito.get_user(AccessToken=access_token)
            
            # Parse user attributes
            attributes = {}
            for attr in response.get('UserAttributes', []):
                attributes[attr['Name']] = attr['Value']
            
            return {
                'id': response['Username'],
                'email': attributes.get('email'),
                'name': attributes.get('name'),
                'email_verified': attributes.get('email_verified') == 'true',
                'created_at': attributes.get('created_at'),
                'status': 'CONFIRMED'
            }
            
        except Exception as e:
            raise ValueError(f'Failed to get user info: {str(e)}')
    
    def list_users(self) -> dict:
        """List all users in the user pool (admin only)"""
        try:
            response = self.cognito.list_users(UserPoolId=self.user_pool_id)
            
            users = []
            for user in response.get('Users', []):
                # Parse user attributes
                attributes = {}
                for attr in user.get('Attributes', []):
                    attributes[attr['Name']] = attr['Value']
                
                users.append({
                    'id': user['Username'],
                    'email': attributes.get('email'),
                    'name': attributes.get('name'),
                    'status': user['UserStatus'],
                    'enabled': user['Enabled'],
                    'created_at': user['UserCreateDate'].isoformat(),
                    'last_modified': user['UserLastModifiedDate'].isoformat()
                })
            
            return {
                'success': True,
                'data': {
                    'users': users,
                    'count': len(users)
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to list users: {str(e)}'}
    
    def update_user_profile(self, access_token: str, attributes: dict) -> dict:
        """Update user profile attributes"""
        try:
            # Get current user
            current_user = self.get_user_by_token(access_token)
            
            # Prepare attributes for update
            user_attributes = []
            for key, value in attributes.items():
                if key in ['name', 'email']:  # Only allow certain attributes
                    user_attributes.append({
                        'Name': key,
                        'Value': str(value)
                    })
            
            if user_attributes:
                self.cognito.update_user_attributes(
                    AccessToken=access_token,
                    UserAttributes=user_attributes
                )
            
            # Return updated user info
            updated_user = self.get_user_by_token(access_token)
            
            return {
                'success': True,
                'data': updated_user
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Profile update failed: {str(e)}'}
