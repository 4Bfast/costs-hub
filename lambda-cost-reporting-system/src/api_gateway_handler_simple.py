"""
API Gateway Handler - Main entry point
"""

from simple_handlers.api_gateway_handler_simple import lambda_handler

# Re-export the lambda_handler function
__all__ = ['lambda_handler']
