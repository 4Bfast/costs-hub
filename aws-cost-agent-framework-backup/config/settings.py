"""
Configuration settings for AWS Cost Analysis Agent Framework
"""

from dataclasses import dataclass
from typing import Optional, List
import os
from pathlib import Path

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

@dataclass
class Settings:
    """Main settings class"""
    aws: AWSConfig
    analysis: AnalysisConfig
    report: ReportConfig
    
    def __init__(self):
        self.aws = AWSConfig(
            profile_name=os.getenv("AWS_PROFILE", "billing"),
            region=os.getenv("AWS_REGION", "us-east-2")
        )
        self.analysis = AnalysisConfig()
        self.report = ReportConfig()
        
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
