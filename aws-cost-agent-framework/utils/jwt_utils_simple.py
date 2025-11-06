"""
Simplified JWT utilities for CostHub API (without PyJWT dependency)
Handles basic JWT token parsing and client_id extraction
"""

import json
import base64
from typing import Dict, Optional
from config.settings import config

def extract_client_id_from_token(jwt_token: str) -> str:
    """
    Extract client_id from JWT token using simple base64 decoding
    No signature verification (for development/testing)
    
    Args:
        jwt_token: JWT token from Authorization header
        
    Returns:
        str: client_id extracted from token or fallback
    """
    try:
        # Split token into parts
        parts = jwt_token.split('.')
        if len(parts) != 3:
            print(f"Invalid JWT token format: {len(parts)} parts")
            return "fallback-client-001"
        
        # Decode payload (second part) 
        payload = parts[1]
        
        # Add padding if needed
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)
        
        # Base64 decode
        try:
            decoded_bytes = base64.urlsafe_b64decode(payload)
            decoded_json = json.loads(decoded_bytes.decode('utf-8'))
            
            # Try different fields that might contain client_id
            client_id = (
                decoded_json.get('client_id') or 
                decoded_json.get('username') or 
                decoded_json.get('sub') or
                decoded_json.get('cognito:username')
            )
            
            if client_id:
                print(f"Extracted client_id: {client_id}")
                return str(client_id)
            else:
                print("No client_id found in token, using fallback")
                return "fallback-client-001"
                
        except Exception as decode_error:
            print(f"Failed to decode JWT payload: {decode_error}")
            return "fallback-client-001"
        
    except Exception as e:
        print(f"JWT parsing error: {e}")
        return "fallback-client-001"

def decode_jwt_payload(jwt_token: str) -> Dict:
    """
    Decode JWT payload without signature verification
    
    Args:
        jwt_token: JWT token string
        
    Returns:
        Dict: Decoded JWT payload or empty dict
    """
    try:
        parts = jwt_token.split('.')
        if len(parts) != 3:
            return {}
        
        payload = parts[1]
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)
        
        decoded_bytes = base64.urlsafe_b64decode(payload)
        return json.loads(decoded_bytes.decode('utf-8'))
        
    except Exception as e:
        print(f"Failed to decode JWT payload: {e}")
        return {}

def extract_user_info_from_token(jwt_token: str) -> Dict:
    """
    Extract user information from JWT token
    
    Args:
        jwt_token: JWT token from Authorization header
        
    Returns:
        Dict: User information
    """
    try:
        payload = decode_jwt_payload(jwt_token)
        
        return {
            'client_id': extract_client_id_from_token(jwt_token),
            'username': payload.get('cognito:username', payload.get('username', 'unknown')),
            'email': payload.get('email', 'unknown@example.com'),
            'sub': payload.get('sub', 'unknown-sub'),
            'token_use': payload.get('token_use', 'access'),
            'exp': payload.get('exp'),
            'iat': payload.get('iat')
        }
        
    except Exception as e:
        print(f"Failed to extract user info: {e}")
        return {
            'client_id': 'fallback-client-001',
            'username': 'unknown',
            'email': 'unknown@example.com'
        }

def is_token_expired(jwt_token: str) -> bool:
    """
    Check if JWT token is expired (basic check)
    
    Args:
        jwt_token: JWT token to check
        
    Returns:
        bool: True if token appears expired, False otherwise
    """
    try:
        import time
        payload = decode_jwt_payload(jwt_token)
        exp = payload.get('exp')
        
        if not exp:
            return False  # No expiration claim, assume valid for now
        
        return time.time() > exp
        
    except Exception:
        return False  # If we can't decode, assume valid for now
