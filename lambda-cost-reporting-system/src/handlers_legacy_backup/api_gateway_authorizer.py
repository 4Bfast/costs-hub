"""
API Gateway Lambda Authorizer for JWT Authentication
"""

import json
import jwt
import os
from typing import Dict, Any, Optional

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda Authorizer for API Gateway
    Validates JWT tokens and returns IAM policy
    """
    
    try:
        # Extract token from Authorization header
        token = extract_token(event)
        if not token:
            raise Exception('No token provided')
        
        # Validate JWT token
        payload = validate_jwt_token(token)
        
        # Generate IAM policy
        policy = generate_policy(payload['sub'], 'Allow', event['methodArn'])
        
        # Add user context
        policy['context'] = {
            'userId': payload['sub'],
            'email': payload.get('email', ''),
            'role': payload.get('role', 'USER'),
            'organizationId': payload.get('organization_id', '')
        }
        
        return policy
        
    except Exception as e:
        print(f"Authorization failed: {str(e)}")
        # Return Deny policy
        return generate_policy('user', 'Deny', event['methodArn'])

def extract_token(event: Dict[str, Any]) -> Optional[str]:
    """Extract JWT token from Authorization header"""
    
    auth_header = event.get('headers', {}).get('Authorization') or \
                  event.get('headers', {}).get('authorization')
    
    if not auth_header:
        return None
    
    # Handle "Bearer <token>" format
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    
    return auth_header

def validate_jwt_token(token: str) -> Dict[str, Any]:
    """Validate JWT token and return payload"""
    
    try:
        # Decode and validate JWT
        payload = jwt.decode(
            token, 
            JWT_SECRET, 
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True}
        )
        
        # Validate required fields
        if 'sub' not in payload:
            raise Exception('Invalid token: missing subject')
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token')

def generate_policy(principal_id: str, effect: str, resource: str) -> Dict[str, Any]:
    """Generate IAM policy for API Gateway"""
    
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    return policy

# Mock JWT generator for development
def generate_mock_jwt(user_data: Dict[str, Any]) -> str:
    """Generate mock JWT for development/testing"""
    
    import time
    
    payload = {
        'sub': user_data.get('id', 'dev-user-123'),
        'email': user_data.get('email', 'dev@4bfast.com'),
        'role': user_data.get('role', 'ADMIN'),
        'organization_id': user_data.get('organization_id', 'dev-org-123'),
        'iat': int(time.time()),
        'exp': int(time.time()) + 3600  # 1 hour expiration
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
