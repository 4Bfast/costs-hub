"""
API Access Control Middleware

This service provides API-level access control integration with the RBAC system,
including JWT token validation, permission enforcement, and request filtering.
"""

import boto3
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from functools import wraps
import json
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from ..services.rbac_service import RBACService, Permission, ResourceType, ActionType
from ..models.multi_tenant_models import ClientRole


logger = logging.getLogger(__name__)


class APIAccessControlError(Exception):
    """Base exception for API access control errors."""
    pass


class AuthenticationError(APIAccessControlError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(APIAccessControlError):
    """Raised when authorization fails."""
    pass


class TokenValidationError(APIAccessControlError):
    """Raised when token validation fails."""
    pass


class APIAccessControl:
    """
    API Access Control middleware for multi-tenant cost analytics.
    
    Provides JWT token validation, permission enforcement, and request filtering
    integrated with the RBAC system.
    """
    
    def __init__(self, rbac_service: RBACService, jwt_secret: str, jwt_algorithm: str = "HS256"):
        """
        Initialize the APIAccessControl.
        
        Args:
            rbac_service: RBACService instance
            jwt_secret: JWT secret key for token validation
            jwt_algorithm: JWT algorithm (default: HS256)
        """
        self.rbac_service = rbac_service
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        
        # Token cache to avoid repeated validation
        self._token_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and extract claims.
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary containing token claims
            
        Raises:
            TokenValidationError: If token validation fails
        """
        try:
            # Check cache first
            if token in self._token_cache:
                cached_data = self._token_cache[token]
                if datetime.utcnow() < cached_data['expires_at']:
                    return cached_data['claims']
                else:
                    # Remove expired token from cache
                    del self._token_cache[token]
            
            # Decode and validate token
            claims = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_exp": True}
            )
            
            # Validate required claims
            required_claims = ['user_id', 'tenant_id', 'email', 'exp']
            for claim in required_claims:
                if claim not in claims:
                    raise TokenValidationError(f"Missing required claim: {claim}")
            
            # Cache valid token
            self._token_cache[token] = {
                'claims': claims,
                'expires_at': datetime.utcnow() + self._cache_ttl
            }
            
            return claims
            
        except ExpiredSignatureError:
            raise TokenValidationError("Token has expired")
        except InvalidTokenError as e:
            raise TokenValidationError(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise TokenValidationError(f"Token validation failed: {e}")
    
    def authenticate_request(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Authenticate API request using JWT token.
        
        Args:
            headers: Request headers
            
        Returns:
            Dictionary containing user information
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Extract token from Authorization header
            auth_header = headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                raise AuthenticationError("Missing or invalid Authorization header")
            
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Validate token
            claims = self.validate_jwt_token(token)
            
            # Get user information
            user = self.rbac_service.get_user(claims['user_id'])
            
            # Check if user is active
            if not user.is_active:
                raise AuthenticationError("User account is inactive")
            
            # Return user context
            return {
                'user_id': user.user_id,
                'email': user.email,
                'tenant_id': user.tenant_id,
                'roles': [role.value for role in user.roles],
                'permissions': [perm.value for perm in user.permissions],
                'is_system_admin': user.is_system_admin,
                'token_claims': claims
            }
            
        except (TokenValidationError, AuthenticationError):
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError(f"Authentication failed: {e}")
    
    def authorize_request(self, user_context: Dict[str, Any], required_permission: Permission,
                         resource_id: Optional[str] = None, tenant_id: Optional[str] = None) -> bool:
        """
        Authorize API request based on user permissions.
        
        Args:
            user_context: User context from authentication
            required_permission: Required permission
            resource_id: Optional resource ID
            tenant_id: Optional tenant ID (for cross-tenant access)
            
        Returns:
            True if authorized, False otherwise
            
        Raises:
            AuthorizationError: If authorization fails
        """
        try:
            user_id = user_context['user_id']
            user_tenant_id = user_context['tenant_id']
            
            # Check tenant isolation (unless system admin)
            if tenant_id and tenant_id != user_tenant_id and not user_context['is_system_admin']:
                raise AuthorizationError(f"Cross-tenant access denied: user tenant {user_tenant_id}, requested tenant {tenant_id}")
            
            # Check permission
            has_permission = self.rbac_service.check_permission(user_id, required_permission, resource_id)
            
            if not has_permission:
                raise AuthorizationError(f"Permission denied: {required_permission.value}")
            
            return True
            
        except AuthorizationError:
            raise
        except Exception as e:
            logger.error(f"Authorization error: {e}")
            raise AuthorizationError(f"Authorization failed: {e}")
    
    def require_permission(self, permission: Permission, resource_id: Optional[str] = None):
        """
        Decorator to require specific permission for API endpoint.
        
        Args:
            permission: Required permission
            resource_id: Optional resource ID
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract request context (this would depend on your web framework)
                # For Lambda/API Gateway, you might extract from event
                # For Flask/FastAPI, you might use request context
                
                # This is a simplified example - adapt to your framework
                request_context = kwargs.get('request_context') or {}
                headers = request_context.get('headers', {})
                
                try:
                    # Authenticate request
                    user_context = self.authenticate_request(headers)
                    
                    # Authorize request
                    self.authorize_request(user_context, permission, resource_id)
                    
                    # Add user context to kwargs for the endpoint function
                    kwargs['user_context'] = user_context
                    
                    # Call the original function
                    return func(*args, **kwargs)
                    
                except (AuthenticationError, AuthorizationError) as e:
                    # Return appropriate HTTP error response
                    return {
                        'statusCode': 401 if isinstance(e, AuthenticationError) else 403,
                        'body': json.dumps({
                            'error': str(e),
                            'type': type(e).__name__
                        }),
                        'headers': {
                            'Content-Type': 'application/json'
                        }
                    }
                except Exception as e:
                    logger.error(f"Access control error: {e}")
                    return {
                        'statusCode': 500,
                        'body': json.dumps({
                            'error': 'Internal server error',
                            'type': 'InternalError'
                        }),
                        'headers': {
                            'Content-Type': 'application/json'
                        }
                    }
            
            return wrapper
        return decorator
    
    def require_role(self, role: ClientRole):
        """
        Decorator to require specific role for API endpoint.
        
        Args:
            role: Required role
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                request_context = kwargs.get('request_context') or {}
                headers = request_context.get('headers', {})
                
                try:
                    # Authenticate request
                    user_context = self.authenticate_request(headers)
                    
                    # Check role
                    user_roles = [ClientRole(r) for r in user_context['roles']]
                    if role not in user_roles and not user_context['is_system_admin']:
                        raise AuthorizationError(f"Role required: {role.value}")
                    
                    # Add user context to kwargs
                    kwargs['user_context'] = user_context
                    
                    return func(*args, **kwargs)
                    
                except (AuthenticationError, AuthorizationError) as e:
                    return {
                        'statusCode': 401 if isinstance(e, AuthenticationError) else 403,
                        'body': json.dumps({
                            'error': str(e),
                            'type': type(e).__name__
                        }),
                        'headers': {
                            'Content-Type': 'application/json'
                        }
                    }
                except Exception as e:
                    logger.error(f"Role check error: {e}")
                    return {
                        'statusCode': 500,
                        'body': json.dumps({
                            'error': 'Internal server error',
                            'type': 'InternalError'
                        }),
                        'headers': {
                            'Content-Type': 'application/json'
                        }
                    }
            
            return wrapper
        return decorator
    
    def filter_response_data(self, user_context: Dict[str, Any], data: Any, 
                           resource_type: ResourceType) -> Any:
        """
        Filter response data based on user permissions and tenant isolation.
        
        Args:
            user_context: User context
            data: Response data to filter
            resource_type: Type of resource being filtered
            
        Returns:
            Filtered response data
        """
        try:
            user_tenant_id = user_context['tenant_id']
            is_system_admin = user_context['is_system_admin']
            
            # System admins see everything
            if is_system_admin:
                return data
            
            # Filter based on resource type
            if resource_type == ResourceType.COST_DATA:
                return self._filter_cost_data(data, user_tenant_id)
            elif resource_type == ResourceType.USERS:
                return self._filter_user_data(data, user_tenant_id)
            elif resource_type == ResourceType.AUDIT_LOGS:
                return self._filter_audit_logs(data, user_tenant_id)
            else:
                # Default: filter by tenant_id if present
                return self._filter_by_tenant(data, user_tenant_id)
            
        except Exception as e:
            logger.error(f"Error filtering response data: {e}")
            # Return empty data on error to be safe
            return [] if isinstance(data, list) else {}
    
    def log_api_access(self, user_context: Dict[str, Any], endpoint: str, method: str,
                      resource_type: ResourceType, resource_id: Optional[str] = None,
                      success: bool = True, ip_address: Optional[str] = None) -> None:
        """
        Log API access for audit purposes.
        
        Args:
            user_context: User context
            endpoint: API endpoint
            method: HTTP method
            resource_type: Resource type accessed
            resource_id: Optional resource ID
            success: Whether the request was successful
            ip_address: Client IP address
        """
        try:
            # Map HTTP methods to actions
            method_to_action = {
                'GET': ActionType.READ,
                'POST': ActionType.CREATE,
                'PUT': ActionType.UPDATE,
                'PATCH': ActionType.UPDATE,
                'DELETE': ActionType.DELETE
            }
            
            action = method_to_action.get(method.upper(), ActionType.READ)
            
            # Log through RBAC service
            self.rbac_service._log_audit_entry(
                user_id=user_context['user_id'],
                tenant_id=user_context['tenant_id'],
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details={
                    'endpoint': endpoint,
                    'method': method,
                    'user_agent': user_context.get('token_claims', {}).get('user_agent'),
                    'api_access': True
                },
                ip_address=ip_address,
                success=success
            )
            
        except Exception as e:
            logger.error(f"Error logging API access: {e}")
    
    def _filter_cost_data(self, data: Any, tenant_id: str) -> Any:
        """Filter cost data by tenant."""
        if isinstance(data, list):
            return [item for item in data if item.get('tenant_id') == tenant_id]
        elif isinstance(data, dict):
            if data.get('tenant_id') == tenant_id:
                return data
            else:
                return {}
        return data
    
    def _filter_user_data(self, data: Any, tenant_id: str) -> Any:
        """Filter user data by tenant."""
        if isinstance(data, list):
            filtered_data = []
            for item in data:
                if item.get('tenant_id') == tenant_id:
                    # Remove sensitive fields
                    filtered_item = {k: v for k, v in item.items() 
                                   if k not in ['password_hash', 'api_keys']}
                    filtered_data.append(filtered_item)
            return filtered_data
        elif isinstance(data, dict):
            if data.get('tenant_id') == tenant_id:
                return {k: v for k, v in data.items() 
                       if k not in ['password_hash', 'api_keys']}
            else:
                return {}
        return data
    
    def _filter_audit_logs(self, data: Any, tenant_id: str) -> Any:
        """Filter audit logs by tenant."""
        if isinstance(data, list):
            return [item for item in data if item.get('tenant_id') == tenant_id]
        elif isinstance(data, dict):
            if data.get('tenant_id') == tenant_id:
                return data
            else:
                return {}
        return data
    
    def _filter_by_tenant(self, data: Any, tenant_id: str) -> Any:
        """Generic tenant-based filtering."""
        if isinstance(data, list):
            return [item for item in data if item.get('tenant_id') == tenant_id]
        elif isinstance(data, dict):
            if data.get('tenant_id') == tenant_id:
                return data
            else:
                return {}
        return data
    
    def create_jwt_token(self, user_id: str, email: str, tenant_id: str, 
                        roles: List[str], expires_in_hours: int = 24) -> str:
        """
        Create JWT token for authenticated user.
        
        Args:
            user_id: User ID
            email: User email
            tenant_id: Tenant ID
            roles: User roles
            expires_in_hours: Token expiration in hours
            
        Returns:
            JWT token string
        """
        try:
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=expires_in_hours)
            
            claims = {
                'user_id': user_id,
                'email': email,
                'tenant_id': tenant_id,
                'roles': roles,
                'iat': int(now.timestamp()),
                'exp': int(expires_at.timestamp()),
                'iss': 'multi-cloud-cost-analytics',
                'aud': 'api'
            }
            
            token = jwt.encode(claims, self.jwt_secret, algorithm=self.jwt_algorithm)
            return token
            
        except Exception as e:
            logger.error(f"Error creating JWT token: {e}")
            raise APIAccessControlError(f"Token creation failed: {e}")
    
    def refresh_jwt_token(self, token: str, expires_in_hours: int = 24) -> str:
        """
        Refresh JWT token with new expiration.
        
        Args:
            token: Current JWT token
            expires_in_hours: New expiration in hours
            
        Returns:
            New JWT token string
            
        Raises:
            TokenValidationError: If current token is invalid
        """
        try:
            # Validate current token (ignore expiration for refresh)
            claims = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_exp": False}
            )
            
            # Create new token with updated expiration
            return self.create_jwt_token(
                user_id=claims['user_id'],
                email=claims['email'],
                tenant_id=claims['tenant_id'],
                roles=claims.get('roles', []),
                expires_in_hours=expires_in_hours
            )
            
        except InvalidTokenError as e:
            raise TokenValidationError(f"Invalid token for refresh: {e}")
        except Exception as e:
            logger.error(f"Error refreshing JWT token: {e}")
            raise APIAccessControlError(f"Token refresh failed: {e}")


# Example usage decorators for common API patterns

def require_admin(api_access_control: APIAccessControl):
    """Decorator to require admin role."""
    return api_access_control.require_role(ClientRole.ADMIN)

def require_cost_data_read(api_access_control: APIAccessControl):
    """Decorator to require cost data read permission."""
    return api_access_control.require_permission(Permission.COST_DATA_READ)

def require_user_management(api_access_control: APIAccessControl):
    """Decorator to require user management permission."""
    return api_access_control.require_permission(Permission.USERS_MANAGE)

def require_settings_update(api_access_control: APIAccessControl):
    """Decorator to require settings update permission."""
    return api_access_control.require_permission(Permission.SETTINGS_UPDATE)


# Example API endpoint implementations

def example_get_cost_data(api_access_control: APIAccessControl):
    """Example API endpoint with access control."""
    
    @api_access_control.require_permission(Permission.COST_DATA_READ)
    def get_cost_data(event, context, user_context=None):
        """Get cost data with proper access control."""
        try:
            # Extract query parameters
            query_params = event.get('queryStringParameters') or {}
            
            # Get cost data (this would call your cost data service)
            # cost_data = cost_service.get_cost_data(user_context['tenant_id'], query_params)
            cost_data = []  # Placeholder
            
            # Filter response data
            filtered_data = api_access_control.filter_response_data(
                user_context, cost_data, ResourceType.COST_DATA
            )
            
            # Log API access
            api_access_control.log_api_access(
                user_context=user_context,
                endpoint='/api/v1/cost-data',
                method='GET',
                resource_type=ResourceType.COST_DATA,
                success=True,
                ip_address=event.get('requestContext', {}).get('identity', {}).get('sourceIp')
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'data': filtered_data,
                    'count': len(filtered_data) if isinstance(filtered_data, list) else 1
                }),
                'headers': {
                    'Content-Type': 'application/json'
                }
            }
            
        except Exception as e:
            logger.error(f"Error in get_cost_data: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Internal server error',
                    'type': 'InternalError'
                }),
                'headers': {
                    'Content-Type': 'application/json'
                }
            }
    
    return get_cost_data