"""
JWT Authorizer for API Gateway

This module provides JWT token validation and authorization for API Gateway requests.
"""

import json
import os
import logging
from typing import Dict, Any, Optional
import jwt
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
JWT_SECRET = os.environ.get('JWT_SECRET')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')


class AuthorizerError(Exception):
    """Custom exception for authorization errors"""
    pass


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for API Gateway JWT authorization.
    
    Args:
        event: API Gateway authorizer event
        context: Lambda context object
        
    Returns:
        IAM policy document for API Gateway
    """
    try:
        logger.info(f"Authorization request: {json.dumps(event, default=str)}")
        
        # Extract token from Authorization header
        token = extract_token(event)
        
        if not token:
            logger.warning("No token provided in request")
            raise AuthorizerError("Unauthorized")
        
        # Validate JWT token
        payload = validate_jwt_token(token)
        
        # Extract user information
        user_id = payload.get('user_id')
        tenant_id = payload.get('tenant_id')
        roles = payload.get('roles', [])
        permissions = payload.get('permissions', [])
        
        if not user_id or not tenant_id:
            logger.warning("Invalid token payload: missing user_id or tenant_id")
            raise AuthorizerError("Invalid token")
        
        # Generate IAM policy
        policy = generate_policy(
            principal_id=user_id,
            effect="Allow",
            resource=event['methodArn'],
            context={
                'user_id': user_id,
                'tenant_id': tenant_id,
                'roles': json.dumps(roles),
                'permissions': json.dumps(permissions),
                'token_exp': str(payload.get('exp', 0))
            }
        )
        
        logger.info(f"Authorization successful for user: {user_id}")
        return policy
        
    except AuthorizerError as e:
        logger.warning(f"Authorization failed: {str(e)}")
        raise Exception("Unauthorized")  # This will return 401 to API Gateway
        
    except Exception as e:
        logger.error(f"Authorization error: {str(e)}")
        raise Exception("Unauthorized")


def extract_token(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract JWT token from the authorization header.
    
    Args:
        event: API Gateway authorizer event
        
    Returns:
        JWT token string or None
    """
    # Check Authorization header
    auth_header = event.get('headers', {}).get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Check X-Api-Key header for API key format
    api_key_header = event.get('headers', {}).get('X-Api-Key')
    if api_key_header and api_key_header.startswith('Bearer '):
        return api_key_header[7:]  # Remove 'Bearer ' prefix
    
    # Check query parameters
    token = event.get('queryStringParameters', {})
    if token:
        return token.get('token')
    
    return None


def validate_jwt_token(token: str) -> Dict[str, Any]:
    """
    Validate JWT token and return payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Token payload dictionary
        
    Raises:
        AuthorizerError: If token is invalid
    """
    try:
        if not JWT_SECRET:
            raise AuthorizerError("JWT secret not configured")
        
        # Decode and validate token
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=['HS256'],
            options={
                'verify_exp': True,
                'verify_iat': True,
                'verify_signature': True
            }
        )
        
        # Check token expiration
        exp = payload.get('exp')
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise AuthorizerError("Token expired")
        
        # Validate required fields
        required_fields = ['user_id', 'tenant_id', 'iat', 'exp']
        for field in required_fields:
            if field not in payload:
                raise AuthorizerError(f"Missing required field: {field}")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise AuthorizerError("Token expired")
    except jwt.InvalidTokenError as e:
        raise AuthorizerError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise AuthorizerError(f"Token validation failed: {str(e)}")


def generate_policy(
    principal_id: str,
    effect: str,
    resource: str,
    context: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Generate IAM policy document for API Gateway.
    
    Args:
        principal_id: User identifier
        effect: Allow or Deny
        resource: Resource ARN
        context: Additional context to pass to Lambda
        
    Returns:
        IAM policy document
    """
    # Extract API Gateway ARN components
    arn_parts = resource.split(':')
    if len(arn_parts) >= 6:
        api_gateway_arn = ':'.join(arn_parts[:5]) + ':*'
    else:
        api_gateway_arn = resource
    
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': api_gateway_arn
                }
            ]
        }
    }
    
    # Add context if provided
    if context:
        # API Gateway context values must be strings
        policy['context'] = {k: str(v) for k, v in context.items()}
    
    return policy


def validate_api_key(api_key: str) -> Dict[str, Any]:
    """
    Validate API key format and return associated information.
    
    Args:
        api_key: API key in format "ApiKey {key_id}:{key_secret}"
        
    Returns:
        API key information dictionary
        
    Raises:
        AuthorizerError: If API key is invalid
    """
    try:
        if not api_key.startswith('ApiKey '):
            raise AuthorizerError("Invalid API key format")
        
        key_data = api_key[7:]  # Remove 'ApiKey ' prefix
        
        if ':' not in key_data:
            raise AuthorizerError("Invalid API key format")
        
        key_id, key_secret = key_data.split(':', 1)
        
        if not key_id or not key_secret:
            raise AuthorizerError("Invalid API key format")
        
        # In a real implementation, you would validate the API key
        # against a database or external service
        # For now, we'll return a mock response
        return {
            'key_id': key_id,
            'user_id': f'api_user_{key_id}',
            'tenant_id': f'api_tenant_{key_id}',
            'permissions': ['api_access'],
            'roles': ['api_client']
        }
        
    except Exception as e:
        raise AuthorizerError(f"API key validation failed: {str(e)}")


# For testing purposes
if __name__ == "__main__":
    # Test event
    test_event = {
        "type": "REQUEST",
        "methodArn": "arn:aws:execute-api:us-east-1:123456789012:abcdef123/test/GET/request",
        "resource": "/request",
        "path": "/request",
        "httpMethod": "GET",
        "headers": {
            "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyIiwidGVuYW50X2lkIjoidGVzdF90ZW5hbnQiLCJyb2xlcyI6WyJ1c2VyIl0sInBlcm1pc3Npb25zIjpbImNvc3RfZGF0YV9yZWFkIl0sImlhdCI6MTYzNTc4NzIwMCwiZXhwIjoxNjM1ODczNjAwfQ.test_signature"
        },
        "queryStringParameters": {},
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "abcdef123",
            "httpMethod": "GET",
            "requestId": "test-request-id",
            "resourcePath": "/request",
            "stage": "test"
        }
    }
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = "test-authorizer"
            self.aws_request_id = "test-request-id"
    
    try:
        result = lambda_handler(test_event, MockContext())
        print(f"Authorization result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Authorization failed: {str(e)}")