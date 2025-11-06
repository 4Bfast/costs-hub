"""
CostHub Configuration - Centralized settings
Removes all hardcoded values from handlers
"""
import os
from dataclasses import dataclass

@dataclass
class CostHubConfig:
    """Centralized configuration for CostHub backend"""
    
    # AWS Configuration
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCOUNT_ID: str = os.getenv('AWS_ACCOUNT_ID', '008195334540')
    
    # Cognito Configuration (Production)
    COGNITO_USER_POOL_ID: str = os.getenv('COGNITO_USER_POOL_ID', 'us-east-1_94OYkzcSO')
    COGNITO_CLIENT_ID: str = os.getenv('COGNITO_CLIENT_ID', '23qrdk4pl1lidrhsflpsitl4u2')
    COGNITO_REGION: str = os.getenv('COGNITO_REGION', 'us-east-1')
    
    # DynamoDB Tables
    DYNAMODB_ACCOUNTS_TABLE: str = os.getenv('DYNAMODB_ACCOUNTS_TABLE', 'costhub-accounts')
    DYNAMODB_ALARMS_TABLE: str = os.getenv('DYNAMODB_ALARMS_TABLE', 'costhub-alarms')
    DYNAMODB_COSTS_TABLE: str = os.getenv('DYNAMODB_COSTS_TABLE', 'costhub-costs')
    
    # CORS Configuration
    CORS_ALLOWED_ORIGINS: str = os.getenv('CORS_ALLOWED_ORIGINS', 'https://costhub.4bfast.com.br,https://www.costhub.4bfast.com.br')
    
    # Feature Flags
    ENABLE_AI_INSIGHTS: bool = os.getenv('ENABLE_AI_INSIGHTS', 'true').lower() == 'true'
    ENABLE_COST_ALERTS: bool = os.getenv('ENABLE_COST_ALERTS', 'true').lower() == 'true'
    ENABLE_DEBUG_LOGGING: bool = os.getenv('ENABLE_DEBUG_LOGGING', 'false').lower() == 'true'
    
    # Security
    JWT_SECRET: str = os.getenv('JWT_SECRET', '')  # Should be set in production
    
    def get_cors_origins_list(self) -> list:
        """Get CORS origins as list"""
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(',')]

# Singleton instance
config = CostHubConfig()
