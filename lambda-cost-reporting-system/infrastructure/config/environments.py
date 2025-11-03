"""
Environment-specific configuration for CDK deployment
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class EnvironmentConfig:
    """Configuration for a specific environment"""
    name: str
    account: str
    region: str
    lambda_memory: int
    lambda_timeout_minutes: int
    log_retention_days: int
    enable_point_in_time_recovery: bool
    removal_policy: str  # "DESTROY" or "RETAIN"
    
    # API Gateway configuration
    api_domain_name: Optional[str] = None
    certificate_arn: Optional[str] = None
    hosted_zone_id: Optional[str] = None
    cors_allowed_origins: List[str] = None
    restrict_api_access: bool = False
    allowed_ip_ranges: List[str] = None
    enable_waf: bool = False
    api_throttle_rate_limit: int = 1000
    api_throttle_burst_limit: int = 2000
    jwt_secret: str = "default-jwt-secret-change-in-production"
    
    def __post_init__(self):
        """Set default values after initialization"""
        if self.cors_allowed_origins is None:
            self.cors_allowed_origins = ["*"]
        if self.allowed_ip_ranges is None:
            self.allowed_ip_ranges = ["0.0.0.0/0"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CDK parameters"""
        return {
            "environment": self.name,
            "lambda_memory": self.lambda_memory,
            "lambda_timeout_minutes": self.lambda_timeout_minutes,
            "log_retention_days": self.log_retention_days,
            "enable_point_in_time_recovery": self.enable_point_in_time_recovery,
            "removal_policy": self.removal_policy,
            "api_domain_name": self.api_domain_name,
            "certificate_arn": self.certificate_arn,
            "hosted_zone_id": self.hosted_zone_id,
            "cors_allowed_origins": self.cors_allowed_origins,
            "restrict_api_access": self.restrict_api_access,
            "allowed_ip_ranges": self.allowed_ip_ranges,
            "enable_waf": self.enable_waf,
            "api_throttle_rate_limit": self.api_throttle_rate_limit,
            "api_throttle_burst_limit": self.api_throttle_burst_limit,
            "jwt_secret": self.jwt_secret
        }


# Environment configurations
ENVIRONMENTS = {
    "dev": EnvironmentConfig(
        name="dev",
        account="",  # Will be set from environment
        region="us-east-1",
        lambda_memory=512,
        lambda_timeout_minutes=5,
        log_retention_days=7,
        enable_point_in_time_recovery=False,
        removal_policy="DESTROY",
        cors_allowed_origins=["*"],
        restrict_api_access=False,
        enable_waf=False,
        api_throttle_rate_limit=100,
        api_throttle_burst_limit=200,
        jwt_secret="dev-jwt-secret-change-me"
    ),
    "staging": EnvironmentConfig(
        name="staging",
        account="",  # Will be set from environment
        region="us-east-1",
        lambda_memory=1024,
        lambda_timeout_minutes=10,
        log_retention_days=30,
        enable_point_in_time_recovery=True,
        removal_policy="RETAIN",
        cors_allowed_origins=["https://staging.example.com"],
        restrict_api_access=True,
        allowed_ip_ranges=["10.0.0.0/8", "172.16.0.0/12"],
        enable_waf=True,
        api_throttle_rate_limit=500,
        api_throttle_burst_limit=1000,
        jwt_secret="staging-jwt-secret-from-secrets-manager"
    ),
    "prod": EnvironmentConfig(
        name="prod",
        account="",  # Will be set from environment
        region="us-east-1",
        lambda_memory=1024,
        lambda_timeout_minutes=15,
        log_retention_days=90,
        enable_point_in_time_recovery=True,
        removal_policy="RETAIN",
        api_domain_name="api.multicloudsanalytics.com",
        cors_allowed_origins=["https://app.multicloudsanalytics.com"],
        restrict_api_access=True,
        allowed_ip_ranges=["10.0.0.0/8", "172.16.0.0/12"],
        enable_waf=True,
        api_throttle_rate_limit=1000,
        api_throttle_burst_limit=2000,
        jwt_secret="prod-jwt-secret-from-secrets-manager"
    )
}


def get_environment_config(env_name: str) -> EnvironmentConfig:
    """Get configuration for specified environment"""
    if env_name not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {env_name}. Available: {list(ENVIRONMENTS.keys())}")
    
    return ENVIRONMENTS[env_name]