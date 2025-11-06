#!/usr/bin/env python3
"""
Simple test for multi-cloud models without complex imports.
"""

import sys
import os
from datetime import date, timedelta
from decimal import Decimal

# Add the src directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_models():
    """Test the basic data models."""
    print("Testing Multi-Cloud Data Models...")
    
    from models.multi_cloud_models import (
        UnifiedCostRecord, ServiceCost, AccountCost, RegionCost,
        CloudProvider, ServiceCategory, Currency, DataQuality, DataQualityLevel
    )
    
    # Create a sample unified cost record
    record = UnifiedCostRecord(
        client_id="test-client-123",
        provider=CloudProvider.AWS,
        date="2024-10-30",
        total_cost=Decimal("1500.50"),
        currency=Currency.USD
    )
    
    print(f"Created record for client: {record.client_id}")
    print(f"Provider: {record.provider.value}")
    print(f"Total cost: {record.total_cost}")
    
    # Add service cost
    service_cost = ServiceCost(
        service_name="Amazon EC2",
        unified_category=ServiceCategory.COMPUTE,
        cost=Decimal("800.00"),
        currency=Currency.USD,
        usage_metrics={"hours": 720},
        provider_specific_data={"instance_type": "t3.medium"}
    )
    record.add_service_cost(service_cost)
    
    print(f"Added service: {service_cost.service_name} - ${service_cost.cost}")
    print(f"Service category: {service_cost.unified_category.value}")
    
    # Test serialization
    dynamo_item = record.to_dynamodb_item()
    print(f"DynamoDB item created with keys: {list(dynamo_item.keys())}")
    
    # Test deserialization
    reconstructed = UnifiedCostRecord.from_dynamodb_item(dynamo_item)
    print(f"Reconstructed record matches: {reconstructed.client_id == record.client_id}")
    
    print("Multi-Cloud Data Models test completed successfully!\n")


def test_provider_models():
    """Test provider-specific models."""
    print("Testing Provider Models...")
    
    from models.provider_models import (
        AWSCredentials, DateRange, ProviderType, ValidationStatus
    )
    
    # Test AWS credentials
    aws_creds = AWSCredentials(role_arn="arn:aws:iam::123456789012:role/test-role")
    print(f"AWS credentials created: {aws_creds.provider.value}")
    print(f"Credential type: {aws_creds.credential_type.value}")
    print(f"Role ARN: {aws_creds.role_arn}")
    
    # Test date range
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    date_range = DateRange(start_date=start_date, end_date=end_date)
    
    print(f"Date range: {date_range.start_date} to {date_range.end_date}")
    print(f"Number of days: {date_range.days}")
    
    print("Provider Models test completed successfully!\n")


def test_service_categories():
    """Test service category mappings."""
    print("Testing Service Category Mappings...")
    
    from models.multi_cloud_models import (
        SERVICE_CATEGORY_MAPPING, CloudProvider, ServiceCategory,
        get_unified_service_category
    )
    
    # Test AWS mappings
    aws_mappings = SERVICE_CATEGORY_MAPPING.get(CloudProvider.AWS, {})
    print(f"AWS services mapped: {len(aws_mappings)}")
    
    # Test specific mappings
    ec2_category = get_unified_service_category(CloudProvider.AWS, "EC2")
    print(f"AWS EC2 maps to: {ec2_category.value}")
    
    lambda_category = get_unified_service_category(CloudProvider.AWS, "Lambda")
    print(f"AWS Lambda maps to: {lambda_category.value}")
    
    # Test GCP mappings
    gcp_mappings = SERVICE_CATEGORY_MAPPING.get(CloudProvider.GCP, {})
    print(f"GCP services mapped: {len(gcp_mappings)}")
    
    compute_engine_category = get_unified_service_category(CloudProvider.GCP, "Compute Engine")
    print(f"GCP Compute Engine maps to: {compute_engine_category.value}")
    
    # Test Azure mappings
    azure_mappings = SERVICE_CATEGORY_MAPPING.get(CloudProvider.AZURE, {})
    print(f"Azure services mapped: {len(azure_mappings)}")
    
    vm_category = get_unified_service_category(CloudProvider.AZURE, "Virtual Machines")
    print(f"Azure VMs map to: {vm_category.value}")
    
    print("Service Category Mappings test completed successfully!\n")


def main():
    """Run all tests."""
    print("Starting Simple Multi-Cloud Tests...\n")
    
    try:
        test_models()
        test_provider_models()
        test_service_categories()
        
        print("All tests completed successfully!")
        return 0
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)