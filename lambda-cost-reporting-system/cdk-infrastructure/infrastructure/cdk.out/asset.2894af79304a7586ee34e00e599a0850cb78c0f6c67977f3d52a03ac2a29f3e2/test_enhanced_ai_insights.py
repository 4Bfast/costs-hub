#!/usr/bin/env python3
"""
Test script for enhanced AI Insights Service orchestration

This script tests the enhanced AI insights service with improved workflow orchestration,
insight aggregation, and ranking capabilities.
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add the src directory to the path
sys.path.append(os.path.dirname(__file__))

try:
    # Import only the specific components we need
    from services.ai_insights_service import (
        AIInsightsService, InsightCategory, InsightPriority, 
        InsightAggregator, InsightRanker, AggregatedInsight
    )
    print("✓ Successfully imported enhanced AI insights service components")
    
    # Try to import models, but create mock ones if they fail
    try:
        from models.multi_cloud_models import UnifiedCostRecord, ServiceCost, CloudProvider
        from models.config_models import ClientConfig
        print("✓ Successfully imported data models")
        MODELS_AVAILABLE = True
    except ImportError as e:
        print(f"⚠️  Model import failed ({e}), using mock models")
        MODELS_AVAILABLE = False
        
        # Create mock models
        from dataclasses import dataclass
        from enum import Enum
        from decimal import Decimal
        from typing import Dict, Any
        
        class CloudProvider(Enum):
            AWS = "AWS"
            GCP = "GCP"
            AZURE = "AZURE"
        
        @dataclass
        class ServiceCost:
            service_name: str
            unified_category: str
            cost: Decimal
            usage_metrics: Dict[str, Any]
            provider_specific_data: Dict[str, Any]
        
        @dataclass
        class UnifiedCostRecord:
            client_id: str
            provider: CloudProvider
            date: str
            total_cost: Decimal
            currency: str
            services: Dict[str, ServiceCost]
            accounts: Dict[str, Any]
            regions: Dict[str, Any]
            collection_metadata: Dict[str, Any]
            data_quality: Dict[str, Any]
            created_at: datetime
            updated_at: datetime
        
        @dataclass
        class ClientConfig:
            client_id: str
            organization_name: str
            cloud_accounts: Dict[str, Any]
            billing_preferences: Dict[str, Any]
            ai_preferences: Dict[str, Any]
            status: str
            created_at: datetime
            updated_at: datetime
            
except ImportError as e:
    print(f"✗ Critical import error: {e}")
    sys.exit(1)


def create_sample_cost_data() -> list:
    """Create sample cost data for testing"""
    cost_data = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(30):
        date = base_date + timedelta(days=i)
        
        # Create varying cost patterns
        base_cost = 1000 + (i * 50)  # Growing trend
        if i % 7 == 0:  # Weekly spike
            base_cost *= 1.5
        if i > 20:  # Recent anomaly
            base_cost *= 1.8
        
        services = {
            'compute': ServiceCost(
                service_name='EC2',
                unified_category='compute',
                cost=Decimal(str(base_cost * 0.6)),
                usage_metrics={},
                provider_specific_data={}
            ),
            'storage': ServiceCost(
                service_name='S3',
                unified_category='storage',
                cost=Decimal(str(base_cost * 0.3)),
                usage_metrics={},
                provider_specific_data={}
            ),
            'database': ServiceCost(
                service_name='RDS',
                unified_category='database',
                cost=Decimal(str(base_cost * 0.1)),
                usage_metrics={},
                provider_specific_data={}
            )
        }
        
        record = UnifiedCostRecord(
            client_id='test-client-123',
            provider=CloudProvider.AWS,
            date=date.strftime('%Y-%m-%d'),
            total_cost=Decimal(str(base_cost)),
            currency='USD',
            services=services,
            accounts={},
            regions={},
            collection_metadata={},
            data_quality={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        cost_data.append(record)
    
    return cost_data


def test_enhanced_orchestration():
    """Test the enhanced AI insights orchestration"""
    print("\n🔄 Testing Enhanced AI Insights Orchestration")
    print("=" * 60)
    
    # Initialize the enhanced AI insights service
    ai_service = AIInsightsService(use_ai=False)  # Disable AI for testing
    print("✓ Initialized enhanced AI insights service")
    
    # Create sample data
    cost_data = create_sample_cost_data()
    print(f"✓ Created {len(cost_data)} sample cost records")
    
    # Create client config
    client_config = ClientConfig(
        client_id='test-client-123',
        organization_name='Test Organization',
        cloud_accounts={},
        billing_preferences={},
        ai_preferences={},
        status='active',
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Create budget info
    budget_info = {'monthly_budget': 50000.0}
    
    print("\n📊 Running orchestrated insights workflow...")
    
    # Run the enhanced orchestration workflow
    try:
        insights = ai_service.orchestrate_insights_workflow(
            client_id='test-client-123',
            cost_data=cost_data,
            client_config=client_config,
            budget_info=budget_info,
            workflow_options={'enable_caching': True}
        )
        
        print("✓ Workflow completed successfully")
        
        # Display results
        print(f"\n📋 Insights Summary:")
        print(f"   Executive Summary: {insights.executive_summary[:100]}...")
        print(f"   Anomalies Detected: {len(insights.anomalies)}")
        print(f"   Recommendations: {len(insights.recommendations)}")
        print(f"   Key Insights: {len(insights.key_insights)}")
        print(f"   Confidence Score: {insights.confidence_score:.2f}")
        
        # Display enhanced metadata
        metadata = insights.metadata
        if 'aggregation_metrics' in metadata:
            agg_metrics = metadata['aggregation_metrics']
            print(f"\n🎯 Aggregation Metrics:")
            print(f"   Total Insights: {agg_metrics.get('total_insights', 0)}")
            print(f"   Critical Insights: {agg_metrics.get('critical_insights', 0)}")
            print(f"   High Priority Insights: {agg_metrics.get('high_priority_insights', 0)}")
            print(f"   Total Estimated Savings: ${agg_metrics.get('total_estimated_savings', 0):,.2f}")
            print(f"   Average Confidence: {agg_metrics.get('average_confidence', 0):.2f}")
        
        if 'workflow_performance' in metadata:
            perf_metrics = metadata['workflow_performance']
            print(f"\n⚡ Workflow Performance:")
            print(f"   Steps Completed: {perf_metrics.get('steps_completed', 0)}")
            print(f"   Steps Failed: {perf_metrics.get('steps_failed', 0)}")
            print(f"   Processing Time: {perf_metrics.get('processing_time', 0):.2f}s")
        
        # Test workflow status
        workflow_id = metadata.get('workflow_id')
        if workflow_id:
            status = ai_service.get_workflow_status(workflow_id)
            print(f"\n📈 Workflow Status: {status.get('status', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Workflow failed: {e}")
        return False


def test_insight_aggregation():
    """Test the insight aggregation and ranking components"""
    print("\n🔗 Testing Insight Aggregation and Ranking")
    print("=" * 60)
    
    try:
        ai_service = AIInsightsService(use_ai=False)
        
        # Test aggregator directly
        aggregator = ai_service.insight_aggregator
        ranker = ai_service.insight_ranker
        
        print("✓ Accessed aggregation and ranking components")
        
        # Test with empty data
        empty_insights = aggregator.aggregate_insights([], None, None, [], [])
        print(f"✓ Handled empty data: {len(empty_insights)} insights")
        
        # Test ranker with empty data
        ranked_empty = ranker.rank_insights(empty_insights)
        print(f"✓ Ranked empty insights: {len(ranked_empty)} insights")
        
        return True
        
    except Exception as e:
        print(f"✗ Aggregation test failed: {e}")
        return False


def test_performance_metrics():
    """Test performance metrics collection"""
    print("\n📊 Testing Performance Metrics")
    print("=" * 60)
    
    try:
        ai_service = AIInsightsService(use_ai=False)
        
        # Get initial metrics
        metrics = ai_service.get_insights_performance_metrics()
        print(f"✓ Retrieved performance metrics: {len(metrics)} metrics")
        
        # Test workflow cleanup
        ai_service.cleanup_completed_workflows(max_age_hours=0)  # Clean all
        print("✓ Tested workflow cleanup")
        
        # Test active workflows
        active = ai_service.list_active_workflows()
        print(f"✓ Listed active workflows: {len(active)} active")
        
        return True
        
    except Exception as e:
        print(f"✗ Performance metrics test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Enhanced AI Insights Service Test Suite")
    print("=" * 60)
    
    tests = [
        ("Enhanced Orchestration", test_enhanced_orchestration),
        ("Insight Aggregation", test_insight_aggregation),
        ("Performance Metrics", test_performance_metrics)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:.<40} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Enhanced AI insights service is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())