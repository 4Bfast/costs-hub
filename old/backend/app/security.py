# app/security.py

import time
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from flask import request, jsonify, current_app, g
import jwt
from .models import User, db
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    In-memory rate limiter for API endpoints.
    In production, this should use Redis for distributed rate limiting.
    """
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.blocked_ips = defaultdict(float)
    
    def is_allowed(self, key: str, limit: int, window: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed based on rate limiting rules.
        
        Args:
            key: Unique identifier (IP, user_id, API key, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        now = time.time()
        
        # Check if IP is temporarily blocked
        if key in self.blocked_ips and now < self.blocked_ips[key]:
            return False, {
                'error': 'IP temporarily blocked due to rate limit violations',
                'retry_after': int(self.blocked_ips[key] - now),
                'limit': limit,
                'window': window
            }
        
        # Clean old requests outside the window
        self.requests[key] = [req_time for req_time in self.requests[key] if now - req_time < window]
        
        # Check if limit is exceeded
        if len(self.requests[key]) >= limit:
            # Block IP for 5 minutes on repeated violations
            if len(self.requests[key]) > limit * 2:
                self.blocked_ips[key] = now + 300  # 5 minutes
                logger.warning(f"IP {key} blocked for 5 minutes due to excessive rate limit violations")
            
            return False, {
                'error': 'Rate limit exceeded',
                'limit': limit,
                'window': window,
                'retry_after': int(window - (now - self.requests[key][0])) if self.requests[key] else window
            }
        
        # Add current request
        self.requests[key].append(now)
        
        return True, {
            'limit': limit,
            'remaining': limit - len(self.requests[key]),
            'reset': int(now + window),
            'window': window
        }

class APIKeyManager:
    """
    Manages API keys for external integrations.
    """
    
    @staticmethod
    def generate_api_key() -> Tuple[str, str]:
        """
        Generate a new API key pair.
        
        Returns:
            Tuple of (api_key_id, api_key_secret)
        """
        # Generate API key ID with prefix
        api_key_id = f"ak_{uuid.uuid4().hex[:16]}"
        
        # Generate secure random secret
        api_key_secret = secrets.token_urlsafe(32)
        
        return api_key_id, api_key_secret
    
    @staticmethod
    def hash_secret(secret: str) -> str:
        """Hash API key secret for secure storage."""
        return hashlib.sha256(secret.encode()).hexdigest()
    
    @staticmethod
    def verify_secret(secret: str, hashed: str) -> bool:
        """Verify API key secret against hash."""
        return hashlib.sha256(secret.encode()).hexdigest() == hashed

class EnhancedJWTAuth:
    """
    Enhanced JWT authentication with role validation and security features.
    """
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
    
    def generate_tokens(self, user: User) -> Dict[str, Any]:
        """
        Generate access and refresh tokens for a user.
        
        Args:
            user: User object
            
        Returns:
            Dictionary containing tokens and metadata
        """
        now = datetime.now(timezone.utc)
        
        # Access token (short-lived)
        access_payload = {
            'iat': now,
            'exp': now + timedelta(hours=1),
            'sub': user.id,
            'org_id': user.organization_id,
            'role': user.role,
            'email': user.email,
            'token_type': 'access',
            'jti': uuid.uuid4().hex
        }
        
        # Refresh token (long-lived)
        refresh_payload = {
            'iat': now,
            'exp': now + timedelta(days=30),
            'sub': user.id,
            'org_id': user.organization_id,
            'token_type': 'refresh',
            'jti': uuid.uuid4().hex
        }
        
        access_token = jwt.encode(access_payload, current_app.config['SECRET_KEY'], algorithm='HS256')
        refresh_token = jwt.encode(refresh_payload, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,  # 1 hour
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'organization_id': user.organization_id,
                'is_email_verified': user.is_email_verified
            }
        }
    
    def validate_token(self, token: str, expected_type: str = 'access') -> Dict[str, Any]:
        """
        Validate JWT token and return claims.
        
        Args:
            token: JWT token string
            expected_type: Expected token type ('access' or 'refresh')
            
        Returns:
            Dictionary containing token claims
            
        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
        """
        try:
            claims = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # Verify token type
            if claims.get('token_type') != expected_type:
                raise jwt.InvalidTokenError(f"Invalid token type. Expected {expected_type}")
            
            # Verify user still exists and is active
            user = User.query.get(claims['sub'])
            if not user or not user.is_active():
                raise jwt.InvalidTokenError("User not found or inactive")
            
            # Add user object to claims for convenience
            claims['user'] = user
            
            return claims
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired {expected_type} token used")
            raise
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid {expected_type} token: {e}")
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise jwt.InvalidTokenError("Token validation failed")

# Global instances
rate_limiter = RateLimiter()
api_key_manager = APIKeyManager()
jwt_auth = EnhancedJWTAuth()

def rate_limit(limit: int = 100, window: int = 3600, per: str = 'ip'):
    """
    Rate limiting decorator.
    
    Args:
        limit: Maximum requests allowed
        window: Time window in seconds (default: 1 hour)
        per: Rate limit key type ('ip', 'user', 'org')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Determine rate limit key
            if per == 'ip':
                key = request.remote_addr
            elif per == 'user' and hasattr(g, 'current_user'):
                key = f"user_{g.current_user.id}"
            elif per == 'org' and hasattr(g, 'current_user'):
                key = f"org_{g.current_user.organization_id}"
            else:
                key = request.remote_addr
            
            # Check rate limit
            allowed, info = rate_limiter.is_allowed(key, limit, window)
            
            if not allowed:
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': info.get('error', 'Too many requests'),
                    'retry_after': info.get('retry_after', window)
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(info.get('retry_after', window))
                return response
            
            # Add rate limit headers to response
            response = f(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = str(info.get('remaining', 0))
                response.headers['X-RateLimit-Reset'] = str(info.get('reset', 0))
            
            return response
        return decorated_function
    return decorator

def enhanced_token_required(roles: Optional[List[str]] = None, allow_api_key: bool = False):
    """
    Enhanced token authentication decorator with role validation and API key support.
    
    Args:
        roles: List of allowed roles (None means any authenticated user)
        allow_api_key: Whether to allow API key authentication
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None
            auth_type = None
            
            # Check for Authorization header
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    auth_parts = auth_header.split(" ")
                    if len(auth_parts) == 2:
                        auth_type, token = auth_parts
                except IndexError:
                    return jsonify({'error': 'Malformed Authorization header'}), 401
            
            if not token:
                return jsonify({'error': 'Authorization token is missing'}), 401
            
            try:
                if auth_type == 'Bearer':
                    # JWT token authentication
                    claims = jwt_auth.validate_token(token, 'access')
                    current_user = claims['user']
                    
                elif auth_type == 'ApiKey' and allow_api_key:
                    # API key authentication (implement if needed)
                    return jsonify({'error': 'API key authentication not yet implemented'}), 501
                    
                else:
                    return jsonify({'error': 'Invalid authorization type'}), 401
                
                # Role validation
                if roles and current_user.role not in roles:
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'required_roles': roles,
                        'user_role': current_user.role
                    }), 403
                
                # Store current user in Flask's g object
                g.current_user = current_user
                
                # Call the original function
                return f(current_user, *args, **kwargs)
                
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token has expired'}), 401
            except jwt.InvalidTokenError as e:
                return jsonify({'error': f'Invalid token: {str(e)}'}), 401
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return jsonify({'error': 'Authentication failed'}), 401
                
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator that requires ADMIN role."""
    return enhanced_token_required(roles=['ADMIN'])(f)

def api_key_auth_required(f):
    """Decorator that requires API key authentication."""
    return enhanced_token_required(allow_api_key=True)(f)