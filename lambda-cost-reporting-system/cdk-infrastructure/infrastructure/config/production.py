"""
Production Environment Configuration
Centralized configuration to avoid hardcoded values
"""

import os

class ProductionConfig:
    """Production environment configuration"""
    
    # AWS Account & Region
    AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID', '008195334540')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    
    # Domain & SSL
    DOMAIN_NAME = os.environ.get('DOMAIN_NAME', '4bfast.com.br')
    API_SUBDOMAIN = os.environ.get('API_SUBDOMAIN', 'api-costhub')
    FRONTEND_SUBDOMAIN = os.environ.get('FRONTEND_SUBDOMAIN', 'costhub')
    CERTIFICATE_ARN = os.environ.get('CERTIFICATE_ARN', 'arn:aws:acm:us-east-1:008195334540:certificate/cc33150f-be90-44d0-87ca-63caf5a48b2f')
    
    # Cognito
    COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', 'us-east-1_94OYkzcSO')
    COGNITO_CLIENT_ID = os.environ.get('COGNITO_CLIENT_ID', '23qrdk4pl1lidrhsflpsitl4u2')
    
    # Backend API - REMOVED (no longer needed, direct processing)
    # BACKEND_BASE_URL = os.environ.get('BACKEND_BASE_URL', 'https://jrltysmyg5.execute-api.us-east-1.amazonaws.com')
    
    @property
    def cognito_domain(self) -> str:
        domain_prefix = f"costhub-auth-{self.DOMAIN_NAME.replace('.', '-')}"
        return f"https://{domain_prefix}.auth.{self.AWS_REGION}.amazoncognito.com"
    
    @property
    def cors_allowed_origins(self) -> list:
        return [
            f"https://{self.FRONTEND_SUBDOMAIN}.{self.DOMAIN_NAME}",
            f"https://www.{self.FRONTEND_SUBDOMAIN}.{self.DOMAIN_NAME}"
        ]
    
    @property
    def api_domain_name(self) -> str:
        return f"{self.API_SUBDOMAIN}.{self.DOMAIN_NAME}"
    
    @property
    def frontend_domain_name(self) -> str:
        return f"{self.FRONTEND_SUBDOMAIN}.{self.DOMAIN_NAME}"
    
    @property
    def api_base_url(self) -> str:
        return f"https://{self.api_domain_name}/api/v1"
    
    @property
    def frontend_base_url(self) -> str:
        return f"https://{self.frontend_domain_name}"

# Global instance
config = ProductionConfig()
