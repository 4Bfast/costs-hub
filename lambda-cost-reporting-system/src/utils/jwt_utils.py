"""
JWT Utilities - NO MORE HARDCODING
Extracts real client_id from JWT tokens
"""
import json
import base64
import boto3
from typing import Dict, Optional
from config.settings import config

def extract_client_id_from_token(jwt_token: str) -> str:
    """
    Extract real client_id from JWT token - REMOVES 'test-client-001' hardcode
    
    Args:
        jwt_token: JWT token from Cognito
        
    Returns:
        str: Real client_id from token
        
    Raises:
        ValueError: If token is invalid or client_id not found
    """
    try:
        # Decode JWT payload (without signature verification for client_id extraction)
        parts = jwt_token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format")
        
        # Decode payload
        payload = parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        decoded_bytes = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded_bytes.decode('utf-8'))
        
        # Extract client_id from token (try multiple fields)
        client_id = (
            payload_data.get('client_id') or 
            payload_data.get('aud') or  # audience 
            payload_data.get('username') or 
            payload_data.get('sub')  # subject
        )
        
        if not client_id:
            raise ValueError("No client_id found in JWT token")
            
        return str(client_id)
        
    except Exception as e:
        raise ValueError(f"Failed to extract client_id from JWT: {e}")

def validate_cognito_token(access_token: str) -> Dict:
    """
    Validate JWT token with AWS Cognito
    
    Args:
        access_token: Cognito access token
        
    Returns:
        dict: User information from Cognito
        
    Raises:
        ValueError: If token validation fails
    """
    try:
        cognito = boto3.client('cognito-idp', region_name=config.COGNITO_REGION)
        
        response = cognito.get_user(AccessToken=access_token)
        
        # Extract user attributes
        attributes = {}
        for attr in response.get('UserAttributes', []):
            attributes[attr['Name']] = attr['Value']
        
        return {
            'username': response['Username'],
            'user_status': response.get('UserStatus'),
            'attributes': attributes,
            'mfa_options': response.get('MFAOptions', [])
        }
        
    except Exception as e:
        raise ValueError(f"Cognito token validation failed: {e}")

def get_client_id_for_user(username: str) -> str:
    """
    Get client_id for a given username - REPLACES hardcoded mapping
    
    For now, we'll use a simple mapping but this should be stored in DynamoDB
    in the future for proper multi-tenant support.
    
    Args:
        username: Cognito username
        
    Returns:
        str: Client ID for the user
    """
    # TODO: Replace with DynamoDB lookup for proper multi-tenant support
    # For now, map all users to a default client based on username
    
    if username:
        # Use username as client_id for now (simple 1:1 mapping)
        return f"client-{username}"
    
    # Fallback (but should not happen with proper validation)
    return "default-client"
