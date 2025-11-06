"""
JWT Authentication Service

This service provides JWT token generation, validation, and management
for the multi-cloud cost analytics platform with enhanced security features.
"""

import jwt
import boto3
import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os

from ..models.multi_tenant_models import ClientRole
from ..utils.api_response import AuthenticationError, AuthorizationError


logger = logging.getLogger(__name__)


class JWTAuthService:
    """
    JWT Authentication service with enhanced security features.
    
    Provides token generation, validation, refresh, and revocation
    with support for multiple token types and security policies.
    """
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", 
                 token_table_name: str = "jwt-tokens", region: str = "us-east-1"):
        """
        Initialize the JWT authentication service.
        
        Args:
            secret_key: JWT signing secret key
            algorithm: JWT signing algorithm
            token_table_name: DynamoDB table for token management
            region: AWS region
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_table_name = token_table_name
        self.region = region
        
        # Initialize DynamoDB
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.token_table = self.dynamodb.Table(token_table_name)
        
        # Token configuration
        self.access_token_ttl = timedelta(hours=1)
        self.refresh_token_ttl = timedelta(days=30)
        self.api_key_ttl = timedelta(days=365)
        
        # Security settings
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.password_min_length = 8
        self.require_password_complexity = True
    
    def generate_access_token(self, user_id: str, tenant_id: str, email: str,
                            roles: List[ClientRole], permissions: List[str],
                            is_system_admin: bool = False,
                            custom_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate an access token for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            email: User email
            roles: User roles
            permissions: User permissions
            is_system_admin: Whether user is system admin
            custom_claims: Additional custom claims
            
        Returns:
            JWT access token string
        """
        now = datetime.utcnow()
        expiry = now + self.access_token_ttl
        
        # Base claims
        claims = {
            'iss': 'multi-cloud-cost-analytics',
            'sub': user_id,
            'aud': 'api',
            'iat': int(now.timestamp()),
            'exp': int(expiry.timestamp()),
            'user_id': user_id,
            'tenant_id': tenant_id,
            'email': email,
            'roles': [role.value for role in roles],
            'permissions': permissions,
            'is_system_admin': is_system_admin,
            'token_type': 'access',
            'jti': self._generate_token_id()
        }
        
        # Add custom claims
        if custom_claims:
            claims.update(custom_claims)
        
        # Generate token
        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        
        # Store token metadata
        self._store_token_metadata(claims['jti'], user_id, tenant_id, 'access', expiry)
        
        return token
    
    def generate_refresh_token(self, user_id: str, tenant_id: str) -> str:
        """
        Generate a refresh token for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            JWT refresh token string
        """
        now = datetime.utcnow()
        expiry = now + self.refresh_token_ttl
        
        claims = {
            'iss': 'multi-cloud-cost-analytics',
            'sub': user_id,
            'aud': 'refresh',
            'iat': int(now.timestamp()),
            'exp': int(expiry.timestamp()),
            'user_id': user_id,
            'tenant_id': tenant_id,
            'token_type': 'refresh',
            'jti': self._generate_token_id()
        }
        
        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        
        # Store token metadata
        self._store_token_metadata(claims['jti'], user_id, tenant_id, 'refresh', expiry)
        
        return token
    
    def generate_api_key(self, user_id: str, tenant_id: str, name: str,
                        permissions: List[str], expires_at: Optional[datetime] = None) -> Tuple[str, str]:
        """
        Generate an API key for programmatic access.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            name: API key name/description
            permissions: API key permissions
            expires_at: Optional expiration date
            
        Returns:
            Tuple of (api_key_id, api_key_secret)
        """
        now = datetime.utcnow()
        expiry = expires_at or (now + self.api_key_ttl)
        
        # Generate API key components
        api_key_id = f"ak_{self._generate_token_id()}"
        api_key_secret = self._generate_secure_secret()
        
        # Create JWT token for the API key
        claims = {
            'iss': 'multi-cloud-cost-analytics',
            'sub': user_id,
            'aud': 'api',
            'iat': int(now.timestamp()),
            'exp': int(expiry.timestamp()),
            'user_id': user_id,
            'tenant_id': tenant_id,
            'permissions': permissions,
            'token_type': 'api_key',
            'api_key_id': api_key_id,
            'api_key_name': name,
            'jti': self._generate_token_id()
        }
        
        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        
        # Store API key metadata with hashed secret
        secret_hash = self._hash_secret(api_key_secret)
        self._store_api_key_metadata(api_key_id, user_id, tenant_id, name, 
                                   secret_hash, permissions, expiry, token)
        
        return api_key_id, api_key_secret
    
    def validate_token(self, token: str, expected_type: str = 'access') -> Dict[str, Any]:
        """
        Validate a JWT token.
        
        Args:
            token: JWT token string
            expected_type: Expected token type
            
        Returns:
            Dictionary containing token claims
            
        Raises:
            AuthenticationError: If token validation fails
        """
        try:
            # Decode token
            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True}
            )
            
            # Validate token type
            if claims.get('token_type') != expected_type:
                raise AuthenticationError(f"Invalid token type. Expected {expected_type}")
            
            # Check if token is revoked
            jti = claims.get('jti')
            if jti and self._is_token_revoked(jti):
                raise AuthenticationError("Token has been revoked")
            
            return claims
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise AuthenticationError("Token validation failed")
    
    def validate_api_key(self, api_key_id: str, api_key_secret: str) -> Dict[str, Any]:
        """
        Validate an API key.
        
        Args:
            api_key_id: API key identifier
            api_key_secret: API key secret
            
        Returns:
            Dictionary containing API key claims
            
        Raises:
            AuthenticationError: If API key validation fails
        """
        try:
            # Get API key metadata
            response = self.token_table.get_item(
                Key={'token_id': api_key_id}
            )
            
            if 'Item' not in response:
                raise AuthenticationError("Invalid API key")
            
            api_key_data = response['Item']
            
            # Check if API key is active
            if not api_key_data.get('is_active', True):
                raise AuthenticationError("API key is inactive")
            
            # Verify secret
            stored_hash = api_key_data.get('secret_hash')
            if not self._verify_secret(api_key_secret, stored_hash):
                raise AuthenticationError("Invalid API key secret")
            
            # Check expiration
            expires_at = datetime.fromisoformat(api_key_data['expires_at'])
            if datetime.utcnow() > expires_at:
                raise AuthenticationError("API key has expired")
            
            # Decode the stored JWT token
            token = api_key_data.get('token')
            if not token:
                raise AuthenticationError("API key token not found")
            
            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # We check expiration above
            )
            
            # Update last used timestamp
            self._update_api_key_usage(api_key_id)
            
            return claims
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            raise AuthenticationError("API key validation failed")
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Generate new access and refresh tokens using a refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token)
            
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        # Validate refresh token
        claims = self.validate_token(refresh_token, 'refresh')
        
        user_id = claims['user_id']
        tenant_id = claims['tenant_id']
        
        # Revoke old refresh token
        old_jti = claims.get('jti')
        if old_jti:
            self._revoke_token(old_jti)
        
        # Get user information to generate new tokens
        # This would typically involve calling the user service
        # For now, we'll use minimal claims
        new_access_token = self.generate_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            email=claims.get('email', ''),
            roles=[],  # Would be fetched from user service
            permissions=[],  # Would be fetched from user service
            is_system_admin=False
        )
        
        new_refresh_token = self.generate_refresh_token(user_id, tenant_id)
        
        return new_access_token, new_refresh_token
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token.
        
        Args:
            token: Token to revoke
            
        Returns:
            True if token was revoked successfully
        """
        try:
            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            
            jti = claims.get('jti')
            if jti:
                return self._revoke_token(jti)
            
            return False
            
        except Exception as e:
            logger.error(f"Token revocation error: {e}")
            return False
    
    def revoke_api_key(self, api_key_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            api_key_id: API key identifier
            
        Returns:
            True if API key was revoked successfully
        """
        try:
            self.token_table.update_item(
                Key={'token_id': api_key_id},
                UpdateExpression='SET is_active = :inactive, revoked_at = :now',
                ExpressionAttributeValues={
                    ':inactive': False,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            return True
            
        except ClientError as e:
            logger.error(f"API key revocation error: {e}")
            return False
    
    def list_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List API keys for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of API key information
        """
        try:
            response = self.token_table.query(
                IndexName='UserIndex',
                KeyConditionExpression='user_id = :user_id AND begins_with(token_id, :prefix)',
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':prefix': 'ak_'
                }
            )
            
            api_keys = []
            for item in response['Items']:
                api_keys.append({
                    'api_key_id': item['token_id'],
                    'name': item.get('name', ''),
                    'permissions': item.get('permissions', []),
                    'created_at': item.get('created_at'),
                    'expires_at': item.get('expires_at'),
                    'last_used_at': item.get('last_used_at'),
                    'is_active': item.get('is_active', True)
                })
            
            return api_keys
            
        except ClientError as e:
            logger.error(f"Failed to list API keys for user {user_id}: {e}")
            return []
    
    def _generate_token_id(self) -> str:
        """Generate a unique token ID."""
        return secrets.token_urlsafe(32)
    
    def _generate_secure_secret(self) -> str:
        """Generate a secure secret for API keys."""
        return secrets.token_urlsafe(64)
    
    def _hash_secret(self, secret: str) -> str:
        """Hash a secret using PBKDF2."""
        salt = os.urandom(32)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(secret.encode())
        return base64.b64encode(salt + key).decode()
    
    def _verify_secret(self, secret: str, stored_hash: str) -> bool:
        """Verify a secret against its hash."""
        try:
            decoded = base64.b64decode(stored_hash.encode())
            salt = decoded[:32]
            stored_key = decoded[32:]
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            
            try:
                kdf.verify(secret.encode(), stored_key)
                return True
            except:
                return False
                
        except Exception:
            return False
    
    def _store_token_metadata(self, jti: str, user_id: str, tenant_id: str,
                            token_type: str, expires_at: datetime):
        """Store token metadata in DynamoDB."""
        try:
            self.token_table.put_item(
                Item={
                    'token_id': jti,
                    'user_id': user_id,
                    'tenant_id': tenant_id,
                    'token_type': token_type,
                    'created_at': datetime.utcnow().isoformat(),
                    'expires_at': expires_at.isoformat(),
                    'is_revoked': False,
                    'ttl': int(expires_at.timestamp()) + 86400  # TTL with buffer
                }
            )
        except ClientError as e:
            logger.error(f"Failed to store token metadata: {e}")
    
    def _store_api_key_metadata(self, api_key_id: str, user_id: str, tenant_id: str,
                              name: str, secret_hash: str, permissions: List[str],
                              expires_at: datetime, token: str):
        """Store API key metadata in DynamoDB."""
        try:
            self.token_table.put_item(
                Item={
                    'token_id': api_key_id,
                    'user_id': user_id,
                    'tenant_id': tenant_id,
                    'token_type': 'api_key',
                    'name': name,
                    'secret_hash': secret_hash,
                    'permissions': permissions,
                    'token': token,
                    'created_at': datetime.utcnow().isoformat(),
                    'expires_at': expires_at.isoformat(),
                    'is_active': True,
                    'ttl': int(expires_at.timestamp()) + 86400
                }
            )
        except ClientError as e:
            logger.error(f"Failed to store API key metadata: {e}")
    
    def _is_token_revoked(self, jti: str) -> bool:
        """Check if a token is revoked."""
        try:
            response = self.token_table.get_item(
                Key={'token_id': jti}
            )
            
            if 'Item' in response:
                return response['Item'].get('is_revoked', False)
            
            return False
            
        except ClientError as e:
            logger.error(f"Failed to check token revocation status: {e}")
            return False
    
    def _revoke_token(self, jti: str) -> bool:
        """Mark a token as revoked."""
        try:
            self.token_table.update_item(
                Key={'token_id': jti},
                UpdateExpression='SET is_revoked = :revoked, revoked_at = :now',
                ExpressionAttributeValues={
                    ':revoked': True,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            return True
            
        except ClientError as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    def _update_api_key_usage(self, api_key_id: str):
        """Update API key last used timestamp."""
        try:
            self.token_table.update_item(
                Key={'token_id': api_key_id},
                UpdateExpression='SET last_used_at = :now',
                ExpressionAttributeValues={
                    ':now': datetime.utcnow().isoformat()
                }
            )
        except ClientError as e:
            logger.error(f"Failed to update API key usage: {e}")
    
    def create_token_table(self) -> bool:
        """Create the DynamoDB table for token management."""
        try:
            table = self.dynamodb.create_table(
                TableName=self.token_table_name,
                KeySchema=[
                    {
                        'AttributeName': 'token_id',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'token_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'user_id',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'UserIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'user_id',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'token_id',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST',
                StreamSpecification={
                    'StreamEnabled': False
                },
                PointInTimeRecoverySpecification={
                    'PointInTimeRecoveryEnabled': True
                },
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'multi-cloud-cost-analytics'
                    },
                    {
                        'Key': 'Component',
                        'Value': 'jwt-authentication'
                    }
                ]
            )
            
            # Wait for table to be created
            table.wait_until_exists()
            
            logger.info(f"JWT token table {self.token_table_name} created successfully")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info(f"JWT token table {self.token_table_name} already exists")
                return True
            else:
                logger.error(f"Failed to create JWT token table: {e}")
                return False


class TokenManager:
    """
    High-level token management interface.
    """
    
    def __init__(self, jwt_service: JWTAuthService):
        """
        Initialize token manager.
        
        Args:
            jwt_service: JWT authentication service instance
        """
        self.jwt_service = jwt_service
    
    def authenticate_request(self, authorization_header: str) -> Dict[str, Any]:
        """
        Authenticate a request using Authorization header.
        
        Args:
            authorization_header: Authorization header value
            
        Returns:
            User context dictionary
            
        Raises:
            AuthenticationError: If authentication fails
        """
        if not authorization_header:
            raise AuthenticationError("Authorization header is required")
        
        # Bearer token authentication
        if authorization_header.startswith('Bearer '):
            token = authorization_header[7:]
            claims = self.jwt_service.validate_token(token, 'access')
            
            return {
                'user_id': claims['user_id'],
                'tenant_id': claims['tenant_id'],
                'email': claims.get('email', ''),
                'roles': claims.get('roles', []),
                'permissions': claims.get('permissions', []),
                'is_system_admin': claims.get('is_system_admin', False),
                'token_type': 'bearer',
                'token_claims': claims
            }
        
        # API key authentication
        elif authorization_header.startswith('ApiKey '):
            api_key_parts = authorization_header[7:].split(':')
            if len(api_key_parts) != 2:
                raise AuthenticationError("Invalid API key format")
            
            api_key_id, api_key_secret = api_key_parts
            claims = self.jwt_service.validate_api_key(api_key_id, api_key_secret)
            
            return {
                'user_id': claims['user_id'],
                'tenant_id': claims['tenant_id'],
                'email': claims.get('email', ''),
                'roles': [],  # API keys don't have roles
                'permissions': claims.get('permissions', []),
                'is_system_admin': False,
                'token_type': 'api_key',
                'api_key_id': api_key_id,
                'token_claims': claims
            }
        
        else:
            raise AuthenticationError("Unsupported authorization method")
    
    def generate_user_tokens(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate access and refresh tokens for a user.
        
        Args:
            user_data: User information dictionary
            
        Returns:
            Dictionary with access_token and refresh_token
        """
        access_token = self.jwt_service.generate_access_token(
            user_id=user_data['user_id'],
            tenant_id=user_data['tenant_id'],
            email=user_data['email'],
            roles=user_data.get('roles', []),
            permissions=user_data.get('permissions', []),
            is_system_admin=user_data.get('is_system_admin', False)
        )
        
        refresh_token = self.jwt_service.generate_refresh_token(
            user_id=user_data['user_id'],
            tenant_id=user_data['tenant_id']
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(self.jwt_service.access_token_ttl.total_seconds())
        }