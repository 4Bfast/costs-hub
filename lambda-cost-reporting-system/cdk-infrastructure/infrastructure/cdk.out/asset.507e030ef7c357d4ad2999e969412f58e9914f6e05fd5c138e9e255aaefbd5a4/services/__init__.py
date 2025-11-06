"""
Services module for Lambda Cost Reporting System

This module provides the core services for report generation, email delivery,
and asset management in the Lambda environment.
"""

try:
    from .client_config_manager import ClientConfigManager
    from .lambda_cost_agent import LambdaCostAgent
    from .lambda_report_generator import LambdaReportGenerator
    from .lambda_email_service import LambdaEmailService
    from .lambda_asset_manager import LambdaAssetManager
    from .threshold_evaluator import ThresholdEvaluator
    from .alert_integration_service import AlertIntegrationService
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    try:
        from client_config_manager import ClientConfigManager
    except ImportError:
        ClientConfigManager = None
    
    try:
        from lambda_cost_agent import LambdaCostAgent
    except ImportError:
        LambdaCostAgent = None
    
    try:
        from lambda_report_generator import LambdaReportGenerator
    except ImportError:
        LambdaReportGenerator = None
        
    try:
        from lambda_email_service import LambdaEmailService
    except ImportError:
        LambdaEmailService = None
        
    try:
        from lambda_asset_manager import LambdaAssetManager
    except ImportError:
        LambdaAssetManager = None
        
    try:
        from threshold_evaluator import ThresholdEvaluator
    except ImportError:
        ThresholdEvaluator = None
    from alert_integration_service import AlertIntegrationService

__all__ = [
    'ClientConfigManager',
    'LambdaCostAgent', 
    'LambdaReportGenerator',
    'LambdaEmailService',
    'LambdaAssetManager',
    'ThresholdEvaluator',
    'AlertIntegrationService'
]