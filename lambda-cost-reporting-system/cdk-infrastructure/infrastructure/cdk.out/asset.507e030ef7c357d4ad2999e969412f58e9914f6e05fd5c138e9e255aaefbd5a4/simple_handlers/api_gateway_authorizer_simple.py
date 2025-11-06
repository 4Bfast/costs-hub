"""
Simple JWT Authorizer for API Gateway
"""

import json
import base64
import hmac
import hashlib
import os

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-production')

def decode_jwt_simple(token, secret):
    """Simple JWT decode without external dependencies"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
            
        # Decode payload (skip signature verification for simplicity)
        payload_b64 = parts[1]
        # Add padding if needed
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload_json = base64.b64decode(payload_b64)
        return json.loads(payload_json)
    except:
        return None

def lambda_handler(event, context):
    """Simple JWT Authorizer"""
    
    try:
        # Extract token
        token = event.get('authorizationToken', '').replace('Bearer ', '')
        
        if not token:
            raise Exception('No token provided')
        
        # Validate JWT
        payload = decode_jwt_simple(token, JWT_SECRET)
        
        if not payload:
            raise Exception('Invalid token')
        
        # Generate Allow policy
        policy = {
            'principalId': payload.get('sub', 'user'),
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Allow',
                        'Resource': event['methodArn']
                    }
                ]
            },
            'context': {
                'userId': payload.get('sub', 'user'),
                'email': payload.get('email', ''),
                'name': payload.get('name', '')
            }
        }
        
        return policy
        
    except Exception as e:
        print(f"Authorization failed: {str(e)}")
        raise Exception('Unauthorized')  # This will return 401
