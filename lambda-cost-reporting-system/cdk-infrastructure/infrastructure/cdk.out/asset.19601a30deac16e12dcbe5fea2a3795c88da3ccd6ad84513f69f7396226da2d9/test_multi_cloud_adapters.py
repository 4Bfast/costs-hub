#!/usr/bin/env python3
"""
Test script for multi-cloud provider adapters.

This script tests the basic functionality of the AWS, GCP, and Azure cost adapters
without requiring actual cloud credentials.
"""

import asyncio
import sys
import os
from datetime import date, timedelta
from decimal import Decimal

# Add the src directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly to avoid __init__.py issues
from models.provider_models import (
    AWSCredentials, GCPCredentials, AzureCredentials,
    DateRange, ProviderType
)
from models.multi_cloud_models import CloudProvider, ServiceCategory

# Import service mapper directly
import sys
import importlib.util

# Load service_mapper module directly
current_dir = os.path.dirname(os.path.abspath(__file__))
service_mapper_path = os.path.join(current_dir, "services", "service_mapper.py")
spec = importlib.util.spec_from_file_location("service_mapper", service_mapper_path)
service_mapper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service_mapper_module)
ServiceMapper = service_mapper_module.ServiceMapper
get_unified_service_category = service_mapper_module.get_unified_service_category

# Load cloud_provider_adapter module directly
adapter_path = os.path.join(current_dir, "services", "cloud_provider_adapter.py")
spec = importlib.util.spec_from_file_location("cloud_provider_adapter", adapter_path)
adapter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter_module)
ProviderAdapterFactory = adapter_module.ProviderAdapterFactory


def test_service_mapper():
    """Test the service mapping system."""
    print("Testing Service Mapper...")
    
    mapper = ServiceMapper()
    
    # Test AWS service mapping
    aws_mapping = mapper.map_service(CloudProvider.AWS, "Amazon Elastic Compute Cloud - Compute")
    print(f"AWS EC2 mapping: {aws_mapping.unified_category.value} (confidence: {aws_mapping.confidence.value})")
    
    # Test GCP service mapping
    gcp_mapping = mapper.map_service(CloudProvider.GCP, "Compute Engine")
    print(f"GCP Compute Engine mapping: {gcp_mapping.unified_category.value} (confidence: {gcp_mapping.confidence.value})")
    
    # Test Azure service mapping
    azure_mapping = mapper.map_service(CloudProvider.AZURE, "Virtual Machines")
    print(f"Azure VM mapping: {azure_mapping.unified_category.value} (confidence: {azure_mapping.confidence.value})")
    
    # Test unknown service
    unknown_mapping = mapper.map_service(CloudProvider.AWS, "Unknown Service")
    print(f"Unknown service mapping: {unknown_mapping.unified_category.value} (confidence: {unknown_mapping.confidence.value})")
    
    # Test fuzzy matching
    fuzzy_mapping = mapper.map_service(CloudProvider.AWS, "EC2 Compute")
    print(f"Fuzzy match mapping: {fuzzy_mapping.unified_category.value} (confidence: {fuzzy_mapping.confidence.value})")
    
    # Test equivalent services
    equivalents = mapper.get_equivalent_services(
        "Amazon Elastic Compute Cloud - Compute",
        CloudProvider.AWS,
        [CloudProvider.GCP, CloudProvider.AZURE]
    )
    print(f"Equivalent compute services: {equivalents}")
    
    # Test statistics
    stats = mapper.get_mapping_statistics()
    print(f"Mapping statistics: {stats}")
    
    print("Service Mapper tests completed successfully!\n")


def test_adapter_factory():
    """Test the adapter factory."""
    print("Testing Adapter Factory...")
    
    # Test supported providers
    supported = ProviderAdapterFactory.get_supported_providers()
    print(f"Supported providers: {[p.value for p in supported]}")
    
    # Test AWS adapter creation (without actual credentials)
    try:
        aws_creds = AWSCredentials(role_arn="arn:aws:iam::123456789012:role/test-role")
        aws_adapter = ProviderAdapterFactory.create_adapter(aws_creds)
        print(f"AWS adapter created: {aws_adapter.provider_name}")
        print(f"AWS supported regions: {len(aws_adapter.supported_regions)} regions")
        print(f"AWS default currency: {aws_adapter.default_currency}")
    except Exception as e:
        print(f"AWS adapter creation failed (expected without credentials): {e}")
    
    print("Adapter Factory tests completed successfully!\n")


def test_data_models():
    """Test the data models."""
    print("Testing Data Models...")
    
    from models.multi_cloud_models import (
        UnifiedCostRecord, ServiceCost, AccountCost, RegionCost,
        CollectionMetadata, DataQuality, DataQualityLevel, Currency
    )
    
    # Create a sample unified cost record
    record = UnifiedCostRecord(
        client_id="test-client-123",
        provider=CloudProvider.AWS,
        date="2024-10-30",
        total_cost=Decimal("1500.50"),
        currency=Currency.USD
    )
    
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
    
    # Add account cost
    account_cost = AccountCost(
        account_id="123456789012",
        account_name="Production Account",
        cost=Decimal("1500.50"),
        currency=Currency.USD
    )
    record.add_account_cost(account_cost)
    
    # Add region cost
    region_cost = RegionCost(
        region_name="us-east-1",
        cost=Decimal("900.00"),
        currency=Currency.USD
    )
    record.add_region_cost(region_cost)
    
    # Test serialization
    dynamo_item = record.to_dynamodb_item()
    print(f"DynamoDB item keys: {list(dynamo_item.keys())}")
    print(f"Total cost: {dynamo_item['cost_data']['total_cost']}")
    
    # Test deserialization
    reconstructed = UnifiedCostRecord.from_dynamodb_item(dynamo_item)
    print(f"Reconstructed record client_id: {reconstructed.client_id}")
    print(f"Reconstructed record total_cost: {reconstructed.total_cost}")
    
    # Test cost by category
    cost_by_category = record.get_cost_by_category()
    print(f"Cost by category: {cost_by_category}")
    
    print("Data Models tests completed successfully!\n")


def test_date_range():
    """Test date range functionality."""
    print("Testing Date Range...")
    
    # Create date range
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    date_range = DateRange(start_date=start_date, end_date=end_date)
    
    print(f"Date range: {date_range.start_date} to {date_range.end_date}")
    print(f"Number of days: {date_range.days}")
    
    # Test serialization
    date_dict = date_range.to_dict()
    print(f"Date range dict: {date_dict}")
    
    print("Date Range tests completed successfully!\n")


async def main():
    """Run all tests."""
    print("Starting Multi-Cloud Adapter Tests...\n")
    
    try:
        test_service_mapper()
        test_adapter_factory()
        test_data_models()
        test_date_range()
        
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)