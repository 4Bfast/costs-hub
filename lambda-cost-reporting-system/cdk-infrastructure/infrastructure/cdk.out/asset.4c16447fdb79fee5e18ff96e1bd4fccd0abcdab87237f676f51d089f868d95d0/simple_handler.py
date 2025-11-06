"""
Main Lambda Handler for Multi-Cloud Cost Analytics API

This handler routes requests between the API Gateway handler and other event sources.
"""

import json
import logging
import os
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler that routes requests to appropriate handlers.
    
    Args:
        event: Lambda event data
        context: Lambda context object
        
    Returns:
        Response based on event source
    """
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Determine event source and route accordingly
        if is_api_gateway_event(event):
            # Route to API Gateway handler
            from handlers.api_handler import lambda_handler as api_handler
            return api_handler(event, context)
            
        elif is_eventbridge_event(event):
            # Route to scheduled report handler
            from handlers.main_handler import lambda_handler as main_handler
            return main_handler(event, context)
            
        elif event.get('health_check'):
            # Health check for direct invocation
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': True,
                    'data': {
                        'message': 'Multi-Cloud Cost Analytics API is healthy',
                        'environment': os.environ.get('ENVIRONMENT', 'dev'),
                        'version': '1.0.0',
                        'timestamp': context.aws_request_id,
                        'services': {
                            'api_gateway': 'healthy',
                            'lambda': 'healthy',
                            'dynamodb': 'healthy'
                        }
                    }
                })
            }
            
        else:
            # Default handler for unknown event types
            logger.warning(f"Unknown event type: {event}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'success': False,
                    'error': {
                        'message': 'Unknown event type',
                        'code': 400
                    }
                })
            }
            
    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'success': False,
                'error': {
                    'message': 'Internal server error',
                    'code': 500,
                    'request_id': context.aws_request_id if context else None
                }
            })
        }


def is_api_gateway_event(event: Dict[str, Any]) -> bool:
    """
    Check if the event is from API Gateway.
    
    Args:
        event: Lambda event data
        
    Returns:
        True if event is from API Gateway
    """
    return (
        'httpMethod' in event and
        'path' in event and
        'requestContext' in event
    )


def is_eventbridge_event(event: Dict[str, Any]) -> bool:
    """
    Check if the event is from EventBridge.
    
    Args:
        event: Lambda event data
        
    Returns:
        True if event is from EventBridge
    """
    return (
        'source' in event and
        event.get('source') == 'aws.events' and
        'detail-type' in event
    ) or (
        'source' in event and
        event.get('source') == 'eventbridge'
    )