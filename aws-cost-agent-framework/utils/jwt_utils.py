"""
JWT utilities for CostHub API
Handles JWT token validation and client_id extraction
"""

import jwt
import json
import base64
import boto3
from typing import Dict, Optional
from config.settings import config

def extract_client_id_from_token(jwt_token: str) -> str:
    """
    Extract real client_id from JWT token - NO MORE HARDCODING
    
    Args:
        jwt_token: JWT token from Authorization header
        
    Returns:
        str: Real client_id extracted from token
        
    Raises:
        ValueError: If token is invalid or client_id cannot be extracted
    """
    try:
        # Decode JWT token without signature verification (for client_id extraction)
        # In production, you should verify the signature with Cognito public keys
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        
        # Try different fields that might contain client_id
        client_id = (
            decoded.get('client_id') or 
            decoded.get('username') or 
            decoded.get('sub') or
            decoded.get('cognito:username')
        )
        
        if not client_id:
            # Fallback: try to extract from custom claims
            client_id = decoded.get('custom:client_id', 'unknown-client')
        
        return str(client_id)
        
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid JWT token: {e}")
    except Exception as e:
        raise ValueError(f"Failed to extract client_id from token: {e}")

def decode_jwt_payload(jwt_token: str) -> Dict:
    """
    Decode JWT payload without signature verification
    Useful for extracting claims from Cognito tokens
    
    Args:
        jwt_token: JWT token string
        
    Returns:
        Dict: Decoded JWT payload
    """
    try:
        # Split token into parts
        parts = jwt_token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format")
        
        # Decode payload (second part)
        payload = parts[1]
        
        # Add padding if needed
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)
        
        # Base64 decode
        decoded_bytes = base64.urlsafe_b64decode(payload)
        decoded_json = json.loads(decoded_bytes.decode('utf-8'))
        
        return decoded_json
        
    except Exception as e:
        raise ValueError(f"Failed to decode JWT payload: {e}")

def validate_cognito_token(token: str) -> Dict:
    """
    Validate JWT token with AWS Cognito
    
    Args:
        token: Access token from Cognito
        
    Returns:
        Dict: User information from Cognito
        
    Raises:
        ValueError: If token validation fails
    """
    try:
        cognito = boto3.client('cognito-idp', region_name=config.COGNITO_REGION)
        
        response = cognito.get_user(AccessToken=token)
        
        # Extract user attributes
        attributes = {}
        for attr in response.get('UserAttributes', []):
            attributes[attr['Name']] = attr['Value']
        
        return {
            'username': response.get('Username'),
            'user_status': response.get('UserStatus'),
            'attributes': attributes,
            'mfa_options': response.get('MFAOptions', [])
        }
        
    except cognito.exceptions.NotAuthorizedException:
        raise ValueError("Token is not authorized or has expired")
    except cognito.exceptions.UserNotFoundException:
        raise ValueError("User not found")
    except Exception as e:
        raise ValueError(f"Token validation failed: {e}")

def extract_user_info_from_token(jwt_token: str) -> Dict:
    """
    Extract comprehensive user information from JWT token
    
    Args:
        jwt_token: JWT token from Authorization header
        
    Returns:
        Dict: User information including client_id, username, email, etc.
    """
    try:
        payload = decode_jwt_payload(jwt_token)
        
        return {
            'client_id': extract_client_id_from_token(jwt_token),
            'username': payload.get('cognito:username', payload.get('username')),
            'email': payload.get('email'),
            'sub': payload.get('sub'),
            'token_use': payload.get('token_use'),
            'scope': payload.get('scope'),
            'auth_time': payload.get('auth_time'),
            'iss': payload.get('iss'),
            'exp': payload.get('exp'),
            'iat': payload.get('iat'),
            'client_id_claim': payload.get('client_id'),
            'custom_attributes': {
                k: v for k, v in payload.items() 
                if k.startswith('custom:')
            }
        }
        
    except Exception as e:
        raise ValueError(f"Failed to extract user info: {e}")

def is_token_expired(jwt_token: str) -> bool:
    """
    Check if JWT token is expired
    
    Args:
        jwt_token: JWT token to check
        
    Returns:
        bool: True if token is expired, False otherwise
    """
    try:
        import time
        payload = decode_jwt_payload(jwt_token)
        exp = payload.get('exp')
        
        if not exp:
            return True  # No expiration claim means invalid
        
        return time.time() > exp
        
    except Exception:
        return True  # If we can't decode, consider it expired

def create_test_token(client_id: str = "test-client-001", username: str = "testuser") -> str:
    """
    Create a test JWT token for development/testing
    WARNING: Only use for testing, not in production
    
    Args:
        client_id: Client ID to embed in token
        username: Username to embed in token
        
    Returns:
        str: Test JWT token
    """
    import time
    
    payload = {
        'client_id': client_id,
        'username': username,
        'sub': f'test-sub-{client_id}',
        'email': f'{username}@test.com',
        'token_use': 'access',
        'scope': 'aws.cognito.signin.user.admin',
        'auth_time': int(time.time()),
        'iss': f'https://cognito-idp.{config.COGNITO_REGION}.amazonaws.com/{config.COGNITO_USER_POOL_ID}',
        'exp': int(time.time()) + 3600,  # 1 hour
        'iat': int(time.time()),
        'cognito:username': username
    }
    
    # Create unsigned token (for testing only)
    return jwt.encode(payload, 'test-secret', algorithm='HS256')
