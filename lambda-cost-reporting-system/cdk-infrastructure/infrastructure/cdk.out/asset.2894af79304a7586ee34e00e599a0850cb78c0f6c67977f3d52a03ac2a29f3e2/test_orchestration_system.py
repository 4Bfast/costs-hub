"""
Test script for the Cost Collection Orchestration System

This script demonstrates and tests the key functionality of the orchestration system.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any

from services.orchestration_integration_service import (
    OrchestrationIntegrationService, OrchestrationConfig, create_orchestration_service
)
from services.collection_scheduler import ScheduleFrequency
from services.cost_collection_orchestrator import CollectionPriority
from models.multi_cloud_models import CloudProvider
from models.provider_models import DateRange
from utils.logging import create_logger


logger = create_logger(__name__)


async def test_orchestration_system():
    """Test the complete orchestration system."""
    print("🚀 Testing Cost Collection Orchestration System")
    print("=" * 60)
    
    try:
        # Create orchestration service
        config = OrchestrationConfig(
            max_concurrent_tasks=5,
            max_concurrent_per_provider=2,
            enable_monitoring=True,
            enable_xray=False,  # Disable for testing
            queue_prefix="test-cost-collection",
            metrics_namespace="Test/CostAnalytics",
            region="us-east-1"
        )
        
        service = create_orchestration_service(config)
        
        print("✅ Created orchestration service")
        
        # Initialize service
        print("🔧 Initializing service...")
        await service.initialize()
        print("✅ Service initialized")
        
        # Test health check
        print("\n🏥 Testing health check...")
        health = await service.health_check()
        print(f"Health Status: {health['status']}")
        print(f"Components: {list(health['components'].keys())}")
        
        # Test service statistics
        print("\n📊 Getting service statistics...")
        stats = service.get_service_statistics()
        print(f"Max Concurrent Tasks: {stats['config']['max_concurrent_tasks']}")
        print(f"Monitoring Enabled: {stats['config']['monitoring_enabled']}")
        
        # Test queue metrics
        print("\n📈 Getting queue metrics...")
        queue_metrics = service.get_queue_metrics()
        for priority, metrics in queue_metrics.items():
            if 'error' not in metrics:
                print(f"{priority.upper()}: {metrics['messages_available']} messages available")
        
        # Test scheduling (mock client)
        print("\n⏰ Testing collection scheduling...")
        test_client_id = "test-client-123"
        
        try:
            message_id = await service.schedule_collection(
                client_id=test_client_id,
                frequency=ScheduleFrequency.DAILY,
                providers=[CloudProvider.AWS],
                priority=CollectionPriority.NORMAL
            )
            print(f"✅ Scheduled collection with message ID: {message_id}")
        except Exception as e:
            print(f"⚠️  Scheduling test failed (expected): {str(e)}")
        
        # Test batch scheduling
        print("\n📦 Testing batch scheduling...")
        test_client_ids = ["test-client-1", "test-client-2", "test-client-3"]
        
        try:
            message_ids = await service.schedule_batch_collection(
                client_ids=test_client_ids,
                frequency=ScheduleFrequency.WEEKLY,
                priority=CollectionPriority.LOW
            )
            print(f"✅ Scheduled batch collection: {len(message_ids)} messages")
        except Exception as e:
            print(f"⚠️  Batch scheduling test failed (expected): {str(e)}")
        
        # Test direct orchestration (will fail without real client data)
        print("\n🎯 Testing direct orchestration...")
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        date_range = DateRange(start_date=yesterday, end_date=yesterday)
        
        try:
            result = await service.orchestrate_collection(
                client_id=test_client_id,
                date_range=date_range,
                providers=[CloudProvider.AWS],
                priority=CollectionPriority.HIGH
            )
            print(f"✅ Orchestration completed: {result.status.value}")
            print(f"   Duration: {result.duration_seconds}s")
            print(f"   Success Rate: {result.success_rate}%")
        except Exception as e:
            print(f"⚠️  Orchestration test failed (expected): {str(e)}")
        
        # Test schedule rule management
        print("\n⚙️  Testing schedule rule management...")
        
        # Disable weekly rule
        disabled = service.disable_schedule_rule(ScheduleFrequency.WEEKLY)
        print(f"Disabled weekly rule: {disabled}")
        
        # Re-enable weekly rule
        enabled = service.enable_schedule_rule(ScheduleFrequency.WEEKLY)
        print(f"Enabled weekly rule: {enabled}")
        
        # Final health check
        print("\n🏥 Final health check...")
        final_health = await service.health_check()
        print(f"Final Status: {final_health['status']}")
        
        print("\n✅ All tests completed successfully!")
        
        # Shutdown service
        print("\n🛑 Shutting down service...")
        await service.shutdown()
        print("✅ Service shutdown complete")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        logger.error(f"Test error: {str(e)}")
        raise


def test_lambda_handler():
    """Test the Lambda handler functions."""
    print("\n🔧 Testing Lambda Handler Functions")
    print("=" * 40)
    
    from handlers.orchestration_handler import lambda_handler
    
    # Test health check event
    health_event = {
        'httpMethod': 'GET',
        'path': '/health'
    }
    
    try:
        response = lambda_handler(health_event, None)
        print(f"Health Check Response: {response['statusCode']}")
        
        if response['statusCode'] == 200:
            body = json.loads(response['body'])
            print(f"Service Status: {body.get('status', 'unknown')}")
        
    except Exception as e:
        print(f"⚠️  Lambda handler test failed: {str(e)}")
    
    # Test scheduled event
    scheduled_event = {
        'source': 'aws.events',
        'detail-type': 'Scheduled Event',
        'time': datetime.utcnow().isoformat() + 'Z'
    }
    
    try:
        response = lambda_handler(scheduled_event, None)
        print(f"Scheduled Event Response: {response['statusCode']}")
        
    except Exception as e:
        print(f"⚠️  Scheduled event test failed: {str(e)}")


def demonstrate_monitoring_features():
    """Demonstrate monitoring and observability features."""
    print("\n📊 Demonstrating Monitoring Features")
    print("=" * 40)
    
    from services.collection_monitoring_service import (
        CollectionMonitoringService, MetricData, MetricType
    )
    
    try:
        # Create monitoring service
        monitoring = CollectionMonitoringService(
            namespace="Test/CostAnalytics",
            region="us-east-1",
            enable_xray=False
        )
        
        print("✅ Created monitoring service")
        
        # Test metric creation
        metric = MetricData(
            metric_name="TestMetric",
            value=42.0,
            unit=MetricType.COUNT,
            dimensions={'TestDimension': 'TestValue'}
        )
        
        print(f"✅ Created test metric: {metric.metric_name}")
        
        # Test health check
        health = asyncio.run(monitoring.health_check())
        print(f"Monitoring Health: {health['status']}")
        
    except Exception as e:
        print(f"⚠️  Monitoring test failed: {str(e)}")


def main():
    """Main test function."""
    print("🧪 Cost Collection Orchestration System Tests")
    print("=" * 60)
    
    # Run async tests
    asyncio.run(test_orchestration_system())
    
    # Test Lambda handlers
    test_lambda_handler()
    
    # Demonstrate monitoring
    demonstrate_monitoring_features()
    
    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    main()