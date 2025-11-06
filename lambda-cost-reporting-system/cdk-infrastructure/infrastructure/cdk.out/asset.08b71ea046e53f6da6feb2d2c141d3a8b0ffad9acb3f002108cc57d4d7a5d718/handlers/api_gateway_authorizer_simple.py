"""
Simple JWT Authorizer for API Gateway
"""

import json
import jwt
import os

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-production')

def lambda_handler(event, context):
    """Simple JWT Authorizer"""
    
    try:
        # Extract token
        token = event.get('authorizationToken', '').replace('Bearer ', '')
        
        if not token:
            raise Exception('No token provided')
        
        # Validate JWT
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
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
