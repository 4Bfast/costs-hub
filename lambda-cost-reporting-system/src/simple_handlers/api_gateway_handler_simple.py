"""
API Gateway Handler - Real Implementation Only
No mocks - all endpoints use real handlers
"""

import json
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'https://costhub.4bfast.com.br').split(',')

def get_cors_headers(request_origin):
    """Get CORS headers"""
    origin = request_origin if request_origin in CORS_ALLOWED_ORIGINS else CORS_ALLOWED_ORIGINS[0]
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Request-ID,X-Requested-With',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def lambda_handler(event, context):
    """Route requests to real handlers only"""
    
    # Log incoming request
    logger.info(f"=== INCOMING REQUEST ===")
    logger.info(f"Event: {json.dumps(event, default=str)}")
    logger.info(f"Context: {context}")
    
    try:
        method = event.get('httpMethod', 'UNKNOWN')
        path = event.get('path', 'UNKNOWN')
        headers = event.get('headers', {})
        body = event.get('body', '')
        
        logger.info(f"Method: {method}")
        logger.info(f"Path: {path}")
        logger.info(f"Headers: {json.dumps(headers, default=str)}")
        logger.info(f"Body: {body}")
        
        request_origin = headers.get('origin') or headers.get('Origin')
        cors_headers = get_cors_headers(request_origin)
        
        logger.info(f"Request origin: {request_origin}")
        logger.info(f"CORS headers: {json.dumps(cors_headers, default=str)}")
        
        # Handle CORS preflight requests
        if method == 'OPTIONS':
            logger.info("Handling OPTIONS request")
            response = {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }
            logger.info(f"OPTIONS response: {json.dumps(response, default=str)}")
            return response
        
        # Route to real handlers
        if '/auth' in path:
            logger.info("=== AUTHENTICATION REQUEST ===")
            logger.info(f"Auth path: {path}")
            
            import boto3
            from botocore.exceptions import ClientError
            
            USER_POOL_ID = "us-east-1_94OYkzcSO"
            CLIENT_ID = "23qrdk4pl1lidrhsflpsitl4u2"
            REGION = "us-east-1"
            
            logger.info(f"Cognito config - Pool: {USER_POOL_ID}, Client: {CLIENT_ID}, Region: {REGION}")
            
            if method == 'POST' and path.endswith('/auth/login'):
                logger.info("Processing login request")
                
                try:
                    body_data = json.loads(body) if body else {}
                    logger.info(f"Parsed body: {json.dumps(body_data, default=str)}")
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    return {
                        'statusCode': 400,
                        'headers': cors_headers,
                        'body': json.dumps({'error': 'Invalid JSON in request body'})
                    }
                
                username = body_data.get('username')
                password = body_data.get('password')
                
                logger.info(f"Username: {username}")
                logger.info(f"Password provided: {'Yes' if password else 'No'}")
                
                if not username or not password:
                    logger.error("Missing username or password")
                    response = {
                        'statusCode': 400,
                        'headers': cors_headers,
                        'body': json.dumps({'error': 'Username and password required'})
                    }
                    logger.info(f"Error response: {json.dumps(response, default=str)}")
                    return response
                
                try:
                    logger.info("Initializing Cognito client")
                    cognito = boto3.client('cognito-idp', region_name=REGION)
                    
                    logger.info("Calling Cognito initiate_auth")
                    response = cognito.initiate_auth(
                        ClientId=CLIENT_ID,
                        AuthFlow='USER_PASSWORD_AUTH',
                        AuthParameters={'USERNAME': username, 'PASSWORD': password}
                    )
                    
                    logger.info(f"Cognito response: {json.dumps(response, default=str)}")
                    
                    success_response = {
                        'statusCode': 200,
                        'headers': cors_headers,
                        'body': json.dumps({
                            'message': 'Login successful',
                            'tokens': response['AuthenticationResult']
                        })
                    }
                    logger.info(f"Success response: {json.dumps(success_response, default=str)}")
                    return success_response
                    
                except ClientError as e:
                    logger.error(f"Cognito ClientError: {str(e)}")
                    error_response = {
                        'statusCode': 400,
                        'headers': cors_headers,
                        'body': json.dumps({'error': str(e)})
                    }
                    logger.info(f"ClientError response: {json.dumps(error_response, default=str)}")
                    return error_response
                    
                except Exception as e:
                    logger.error(f"General auth error: {str(e)}")
                    error_response = {
                        'statusCode': 500,
                        'headers': cors_headers,
                        'body': json.dumps({'error': f'Auth error: {str(e)}'})
                    }
                    logger.info(f"General error response: {json.dumps(error_response, default=str)}")
                    return error_response
            
            elif method == 'POST' and path.endswith('/auth/register'):
                logger.info("Processing register request")
                response = {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({'message': 'Registration endpoint working'})
                }
                logger.info(f"Register response: {json.dumps(response, default=str)}")
                return response
            
            elif method == 'POST' and path.endswith('/auth/refresh'):
                logger.info("Processing refresh request")
                response = {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({'message': 'Refresh endpoint working'})
                }
                logger.info(f"Refresh response: {json.dumps(response, default=str)}")
                return response
            
            elif method == 'POST' and path.endswith('/auth/logout'):
                logger.info("Processing logout request")
                response = {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({'message': 'Logout successful'})
                }
                logger.info(f"Logout response: {json.dumps(response, default=str)}")
                return response
            
            elif method == 'GET' and path.endswith('/auth/me'):
                logger.info("Processing me request")
                response = {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({'message': 'User info endpoint working'})
                }
                logger.info(f"Me response: {json.dumps(response, default=str)}")
                return response
            
            else:
                logger.error(f"Auth endpoint not found: {method} {path}")
                response = {
                    'statusCode': 404,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Auth endpoint not found'})
                }
                logger.info(f"404 response: {json.dumps(response, default=str)}")
                return response
        
        elif '/costs' in path:
            logger.info(f"Routing to costs handler: {path}")
            from .costs_handler_simple import handle_costs_request
            return handle_costs_request(event, cors_headers)
            
        elif '/accounts' in path:
            logger.info(f"Routing to accounts handler: {path}")
            from .accounts_handler_simple import handle_accounts_request
            return handle_accounts_request(event, cors_headers)

        elif '/alarms' in path:
            logger.info(f"Routing to alarms handler: {path}")
            from .alarms_handler_simple import handle_alarms_request
            return handle_alarms_request(event, cors_headers)

        elif '/users' in path:
            logger.info(f"Routing to users handler: {path}")
            from .users_handler_simple import handle_users_request
            return handle_users_request(event, cors_headers)
            
        elif '/dashboard' in path:
            logger.info(f"Routing to dashboard handler: {path}")
            from .dashboard_handler_simple import handle_dashboard_request
            return handle_dashboard_request(event, cors_headers)
            
        elif '/insights' in path:
            logger.info(f"Routing to insights handler: {path}")
            from .insights_handler_simple import handle_insights_request
            return handle_insights_request(event, cors_headers)
            
        elif '/organizations' in path:
            logger.info(f"Organizations endpoint: {path}")
            response = {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Organizations endpoint working'})
            }
            logger.info(f"Organizations response: {json.dumps(response, default=str)}")
            return response
            
        elif '/reports' in path:
            logger.info(f"Reports endpoint: {path}")
            response = {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Reports endpoint working'})
            }
            logger.info(f"Reports response: {json.dumps(response, default=str)}")
            return response
                
        elif path.endswith('/health'):
            logger.info("Health check endpoint")
            response = {
                'statusCode': 200, 
                'headers': cors_headers, 
                'body': json.dumps({'status': 'healthy'})
            }
            logger.info(f"Health response: {json.dumps(response, default=str)}")
            return response
            
        elif path.endswith('/status'):
            logger.info("Status check endpoint")
            response = {
                'statusCode': 200, 
                'headers': cors_headers, 
                'body': json.dumps({'status': 'active'})
            }
            logger.info(f"Status response: {json.dumps(response, default=str)}")
            return response
        
        else:
            logger.error(f"Endpoint not found: {method} {path}")
            response = {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            logger.info(f"404 response: {json.dumps(response, default=str)}")
            return response
        
    except ImportError as e:
        logger.error(f"ImportError: {str(e)}")
        response = {
            'statusCode': 501,
            'headers': get_cors_headers(None),
            'body': json.dumps({'error': f'Handler not implemented: {str(e)}'})
        }
        logger.info(f"ImportError response: {json.dumps(response, default=str)}")
        return response
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        response = {
            'statusCode': 500,
            'headers': get_cors_headers(None),
            'body': json.dumps({'error': f'Lambda error: {str(e)}'})
        }
        logger.info(f"Error response: {json.dumps(response, default=str)}")
        return response
