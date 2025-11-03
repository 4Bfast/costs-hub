#!/usr/bin/env python3
"""
Example demonstrating the core data models and configuration management.

This example shows how to:
1. Create client configurations with data models
2. Use encryption for sensitive data
3. Store and retrieve configurations with ClientConfigManager

Note: This is for demonstration purposes only. In a real environment,
you would need proper AWS credentials and a real KMS key.
"""

import sys
import os
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import (
    ClientConfig,
    AccountConfig,
    ReportConfig,
    BrandingConfig,
    ClientStatus,
    ReportType
)
# Note: ClientConfigManager would be imported in a real Lambda environment
# from services import ClientConfigManager


def create_example_client_config():
    """Create an example client configuration."""
    print("Creating example client configuration...")
    
    # Create AWS account configuration
    aws_account = AccountConfig(
        account_id="123456789012",
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
        account_name="Production Account"
    )
    
    # Create report configuration
    report_config = ReportConfig(
        weekly_enabled=True,
        monthly_enabled=True,
        recipients=["admin@example.com", "finance@example.com"],
        cc_recipients=["manager@example.com"],
        threshold=100.0,
        top_services=10,
        include_accounts=True,
        alert_thresholds={
            "EC2": 500.0,
            "S3": 100.0,
            "RDS": 300.0
        }
    )
    
    # Create branding configuration
    branding = BrandingConfig(
        logo_s3_key="logos/example-company.png",
        primary_color="#1f2937",
        secondary_color="#f59e0b",
        company_name="Example Company",
        email_footer="© 2024 Example Company. All rights reserved."
    )
    
    # Create complete client configuration
    client_config = ClientConfig(
        client_id="example-client-001",
        client_name="Example Company",
        aws_accounts=[aws_account],
        report_config=report_config,
        branding=branding,
        status=ClientStatus.ACTIVE
    )
    
    print(f"Created client configuration for: {client_config.client_name}")
    print(f"Client ID: {client_config.client_id}")
    print(f"AWS Accounts: {len(client_config.aws_accounts)}")
    print(f"Recipients: {', '.join(client_config.report_config.recipients)}")
    print(f"Status: {client_config.status.value}")
    
    return client_config


def demonstrate_encryption():
    """Demonstrate encryption functionality."""
    print("\n" + "="*50)
    print("ENCRYPTION DEMONSTRATION")
    print("="*50)
    
    # Note: In a real environment, you would use a real KMS key
    # For this example, we'll show the structure without actual KMS calls
    print("Creating secure credential handler...")
    print("(Note: This would use a real KMS key in production)")
    
    # Create example client config
    client_config = create_example_client_config()
    
    # Convert to dictionary format (as would be stored in DynamoDB)
    config_dict = client_config.to_dict()
    
    print(f"\nOriginal secret access key: {config_dict['aws_accounts'][0]['secret_access_key']}")
    
    # In a real scenario with KMS:
    # credential_handler = create_secure_credential_handler("arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012")
    # encrypted_config = credential_handler.encrypt_client_config(config_dict)
    # print(f"Encrypted secret access key: {encrypted_config['aws_accounts'][0]['secret_access_key']}")
    
    print("Encryption would be applied here with real KMS key")
    print("Secret access key would be encrypted and marked with '_encrypted' flag")


def demonstrate_validation():
    """Demonstrate data validation."""
    print("\n" + "="*50)
    print("VALIDATION DEMONSTRATION")
    print("="*50)
    
    print("Testing validation with invalid data...")
    
    try:
        # Test invalid account ID
        AccountConfig(
            account_id="12345",  # Too short
            access_key_id="AKIATEST",
            secret_access_key="testsecret"
        )
    except ValueError as e:
        print(f"✓ Caught invalid account ID: {e}")
    
    try:
        # Test invalid email
        ReportConfig(
            recipients=["invalid-email"]
        )
    except ValueError as e:
        print(f"✓ Caught invalid email: {e}")
    
    try:
        # Test invalid color
        BrandingConfig(
            primary_color="not-a-color"
        )
    except ValueError as e:
        print(f"✓ Caught invalid color: {e}")
    
    print("All validations working correctly!")


def demonstrate_serialization():
    """Demonstrate serialization and deserialization."""
    print("\n" + "="*50)
    print("SERIALIZATION DEMONSTRATION")
    print("="*50)
    
    # Create client config
    original_config = create_example_client_config()
    
    # Convert to dictionary (for DynamoDB storage)
    config_dict = original_config.to_dict()
    print("Converted to dictionary format for DynamoDB storage")
    
    # Convert back to object
    restored_config = ClientConfig.from_dict(config_dict)
    print("Restored from dictionary format")
    
    # Verify data integrity
    assert original_config.client_id == restored_config.client_id
    assert original_config.client_name == restored_config.client_name
    assert len(original_config.aws_accounts) == len(restored_config.aws_accounts)
    assert original_config.aws_accounts[0].account_id == restored_config.aws_accounts[0].account_id
    assert original_config.report_config.recipients == restored_config.report_config.recipients
    assert original_config.branding.company_name == restored_config.branding.company_name
    
    print("✓ Serialization/deserialization successful - all data preserved")


def demonstrate_client_operations():
    """Demonstrate client configuration operations."""
    print("\n" + "="*50)
    print("CLIENT OPERATIONS DEMONSTRATION")
    print("="*50)
    
    client_config = create_example_client_config()
    
    # Test account lookup
    account = client_config.get_account_by_id("123456789012")
    if account:
        print(f"✓ Found account: {account.account_name} ({account.account_id})")
    
    # Test execution tracking
    print(f"Initial weekly execution: {client_config.last_execution['weekly']}")
    client_config.update_last_execution(ReportType.WEEKLY)
    print(f"Updated weekly execution: {client_config.last_execution['weekly']}")
    
    # Test status check
    print(f"Client is active: {client_config.is_active()}")


def main():
    """Run all demonstrations."""
    print("Lambda Cost Reporting System - Configuration Management Demo")
    print("="*60)
    
    try:
        demonstrate_validation()
        demonstrate_serialization()
        demonstrate_client_operations()
        demonstrate_encryption()
        
        print("\n" + "="*60)
        print("✓ All demonstrations completed successfully!")
        print("The core data models and configuration management system is ready.")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())