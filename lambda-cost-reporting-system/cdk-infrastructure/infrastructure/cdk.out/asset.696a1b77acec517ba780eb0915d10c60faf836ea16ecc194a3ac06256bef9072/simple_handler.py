"""
Simple Lambda Handler for testing
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Simple Lambda handler for testing
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    if event.get('health_check'):
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Health check successful',
                'environment': 'dev',
                'timestamp': context.aws_request_id
            })
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Lambda function is working',
            'event': event
        })
    }