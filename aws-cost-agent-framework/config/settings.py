"""
Configuration settings for CostHub Backend API
"""

from dataclasses import dataclass
from typing import Optional, List
import os
from pathlib import Path

@dataclass
class CostHubConfig:
    """CostHub API Configuration"""
    # AWS Configuration (Production)
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCOUNT_ID: str = os.getenv('AWS_ACCOUNT_ID', '008195334540')
    AWS_PROFILE: str = os.getenv('AWS_PROFILE', '4bfast')
    
    # Cognito Configuration (Production)
    COGNITO_USER_POOL_ID: str = os.getenv('COGNITO_USER_POOL_ID', 'us-east-1_94OYkzcSO')
    COGNITO_CLIENT_ID: str = os.getenv('COGNITO_CLIENT_ID', '23qrdk4pl1lidrhsflpsitl4u2')
    COGNITO_REGION: str = os.getenv('COGNITO_REGION', 'us-east-1')
    
    # DynamoDB Tables
    DYNAMODB_ACCOUNTS_TABLE: str = os.getenv('DYNAMODB_ACCOUNTS_TABLE', 'costhub-accounts')
    DYNAMODB_ALARMS_TABLE: str = os.getenv('DYNAMODB_ALARMS_TABLE', 'costhub-alarms')
    DYNAMODB_COSTS_TABLE: str = os.getenv('DYNAMODB_COSTS_TABLE', 'costhub-costs')
    
    # Lambda Configuration
    LAMBDA_FUNCTION_NAME: str = os.getenv('LAMBDA_FUNCTION_NAME', 'costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV')
    
    # CORS Configuration
    CORS_ALLOWED_ORIGINS: str = os.getenv('CORS_ALLOWED_ORIGINS', 'https://costhub.4bfast.com.br,https://www.costhub.4bfast.com.br')
    
    # Feature Flags
    ENABLE_AI_INSIGHTS: bool = os.getenv('ENABLE_AI_INSIGHTS', 'true').lower() == 'true'
    ENABLE_COST_ALERTS: bool = os.getenv('ENABLE_COST_ALERTS', 'true').lower() == 'true'
    ENABLE_MULTI_ACCOUNT: bool = os.getenv('ENABLE_MULTI_ACCOUNT', 'true').lower() == 'true'
    
    # Cost Explorer Configuration
    COST_EXPLORER_REGION: str = 'us-east-1'  # Cost Explorer is only available in us-east-1
    DEFAULT_COST_PERIOD_DAYS: int = int(os.getenv('DEFAULT_COST_PERIOD_DAYS', '30'))
    
    # Bedrock Configuration (for AI insights)
    BEDROCK_REGION: str = os.getenv('BEDROCK_REGION', 'us-east-1')
    BEDROCK_MODEL_ID: str = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')

# Singleton instance
config = CostHubConfig()

@dataclass
class AWSConfig:
    """AWS-specific configuration"""
    profile_name: str = "billing"
    region: str = "us-east-2"
    cost_explorer_region: str = "us-east-1"  # Cost Explorer is only in us-east-1

@dataclass
class AnalysisConfig:
    """Analysis configuration"""
    # Time period configuration
    analysis_type: str = "monthly"  # "monthly", "weekly", "daily"
    periods_to_analyze: int = 3  # Number of periods (months/weeks/days)
    
    # Legacy support
    months_to_analyze: int = 3
    
    # Thresholds and limits
    min_cost_threshold: float = 1.0  # Ignore changes < $1
    top_services_count: int = 10
    top_accounts_count: int = 10
    max_service_changes: int = 15
    max_account_changes: int = 15
    
    # Feature flags
    include_new_services: bool = True
    include_removed_services: bool = True
    include_account_analysis: bool = True
    include_new_accounts: bool = True
    include_removed_accounts: bool = True
    include_charts: bool = True
    
    def __post_init__(self):
        """Ensure backward compatibility"""
        if self.analysis_type == "monthly":
            self.periods_to_analyze = self.months_to_analyze

@dataclass
class ReportConfig:
    """Report generation configuration"""
    output_dir: Path = Path("reports")
    template_dir: Path = Path("templates")
    auto_open: bool = True
    include_charts: bool = True
    format: str = "html"  # html, pdf, json
    language: str = "pt-BR"  # Language for reports
    
@dataclass
class AIConfig:
    """AI-powered features configuration"""
    enabled: bool = True
    aws_profile: str = "4bfast"  # Profile for Bedrock access
    region: str = "us-east-1"  # Bedrock region
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    include_summary: bool = True
    include_service_explanations: bool = True
    include_recommendations: bool = True

@dataclass
class Settings:
    """Main settings class"""
    aws: AWSConfig
    analysis: AnalysisConfig
    report: ReportConfig
    ai: AIConfig
    
    def __init__(self):
        self.aws = AWSConfig(
            profile_name=os.getenv("AWS_PROFILE"),
            region=os.getenv("AWS_REGION", "us-east-2")
        )
        self.analysis = AnalysisConfig()
        self.report = ReportConfig()
        self.ai = AIConfig()
        
        # Ensure output directory exists
        self.report.output_dir.mkdir(exist_ok=True)
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Settings':
        """Load settings from configuration file"""
        # Future: implement YAML/JSON config loading
        return cls()
    
    def validate(self) -> bool:
        """Validate configuration"""
        if self.analysis.months_to_analyze < 1:
            raise ValueError("months_to_analyze must be >= 1")
        if self.analysis.top_services_count < 1:
            raise ValueError("top_services_count must be >= 1")
        return True
