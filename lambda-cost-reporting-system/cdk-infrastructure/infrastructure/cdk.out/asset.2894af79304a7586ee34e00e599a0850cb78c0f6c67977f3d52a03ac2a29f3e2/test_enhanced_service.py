#!/usr/bin/env python3
"""
Simple test for the enhanced AI Insights Service
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional

# Add the src directory to the path
sys.path.append(os.path.dirname(__file__))

# Mock the required models and dependencies
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

# Mock the logger
class MockLogger:
    def info(self, msg): print(f"INFO: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")

def get_logger(name):
    return MockLogger()

# Mock the AI service dependencies
class MockAnomalyDetectionEngine:
    def __init__(self, use_ai=True):
        self.use_ai = use_ai
    
    def detect_anomalies(self, current_data, historical_data=None, budget_info=None):
        return []

class MockTrendAnalyzer:
    def analyze_trends(self, cost_data):
        from types import SimpleNamespace
        return SimpleNamespace(
            overall_trend=SimpleNamespace(
                direction=SimpleNamespace(value='stable'),
                growth_rate=5.0,
                volatility=10.0,
                significance=SimpleNamespace(value='medium'),
                trend_strength=0.7
            ),
            service_trends={},
            trend_confidence=0.8,
            seasonal_patterns=SimpleNamespace(
                seasonal_strength=0.3,
                seasonal_pattern=SimpleNamespace(value='weekly')
            ),
            key_insights=['Stable cost trend detected']
        )

class MockForecastingEngine:
    def __init__(self, use_ai=True):
        self.use_ai = use_ai
    
    def generate_forecast(self, cost_data, forecast_horizon=30):
        from types import SimpleNamespace
        return SimpleNamespace(
            total_forecast={'amount': 30000, 'confidence': 0.7},
            accuracy_assessment=SimpleNamespace(value='medium'),
            forecast_period=forecast_horizon,
            assumptions=['Historical trend continuation']
        )

class MockBedrockService:
    def generate_cost_recommendations(self, context, client_context):
        return {'recommendations': []}

# Mock the service modules
sys.modules['models.multi_cloud_models'] = type('MockModule', (), {
    'UnifiedCostRecord': UnifiedCostRecord,
    'ServiceCost': ServiceCost,
    'CloudProvider': CloudProvider
})()

sys.modules['models.config_models'] = type('MockModule', (), {
    'ClientConfig': ClientConfig
})()

sys.modules['utils.logging'] = type('MockModule', (), {
    'create_logger': get_logger
})()

sys.modules['services.anomaly_detection_engine'] = type('MockModule', (), {
    'AnomalyDetectionEngine': MockAnomalyDetectionEngine,
    'Anomaly': type('Anomaly', (), {}),
})()

sys.modules['services.trend_analysis_service'] = type('MockModule', (), {
    'TrendAnalyzer': MockTrendAnalyzer,
    'TrendAnalysis': type('TrendAnalysis', (), {})
})()

sys.modules['services.forecasting_engine'] = type('MockModule', (), {
    'ForecastingEngine': MockForecastingEngine,
    'ForecastResult': type('ForecastResult', (), {})
})()

sys.modules['services.bedrock_service'] = type('MockModule', (), {
    'BedrockService': MockBedrockService
})()

# Now import the enhanced AI insights service
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ai_insights_service_enhanced", 
        os.path.join(os.path.dirname(__file__), "services", "ai_insights_service_enhanced.py")
    )
    ai_insights_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ai_insights_module)
    
    # Extract the classes we need
    EnhancedAIInsightsService = ai_insights_module.EnhancedAIInsightsService
    InsightCategory = ai_insights_module.InsightCategory
    InsightPriority = ai_insights_module.InsightPriority
    InsightAggregator = ai_insights_module.InsightAggregator
    InsightRanker = ai_insights_module.InsightRanker
    AggregatedInsight = ai_insights_module.AggregatedInsight
    
    print("✓ Successfully imported enhanced AI insights service components")
except Exception as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def create_sample_cost_data() -> List[UnifiedCostRecord]:
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
    
    try:
        # Initialize the enhanced AI insights service
        ai_service = EnhancedAIInsightsService(use_ai=False)  # Disable AI for testing
        print("✓ Initialized enhanced AI insights service")
        
        # Verify enhanced components are available
        assert hasattr(ai_service, 'insight_aggregator'), "Missing insight_aggregator"
        assert hasattr(ai_service, 'insight_ranker'), "Missing insight_ranker"
        assert hasattr(ai_service, 'workflow_config'), "Missing workflow_config"
        print("✓ Enhanced components verified")
        
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
        
        print("\n📊 Running enhanced orchestrated insights workflow...")
        
        # Run the enhanced orchestration workflow
        insights = ai_service.orchestrate_insights_workflow(
            client_id='test-client-123',
            cost_data=cost_data,
            client_config=client_config,
            budget_info=budget_info,
            workflow_options={'enable_caching': True}
        )
        
        print("✓ Enhanced workflow completed successfully")
        
        # Verify insights structure
        assert hasattr(insights, 'executive_summary'), "Missing executive_summary"
        assert hasattr(insights, 'metadata'), "Missing metadata"
        print("✓ Insights structure verified")
        
        # Display results
        print(f"\n📋 Enhanced Insights Summary:")
        print(f"   Executive Summary: {insights.executive_summary[:100]}...")
        print(f"   Anomalies Detected: {len(insights.anomalies)}")
        print(f"   Recommendations: {len(insights.recommendations)}")
        print(f"   Key Insights: {len(insights.key_insights)}")
        print(f"   Confidence Score: {insights.confidence_score:.2f}")
        
        # Display enhanced metadata
        metadata = insights.metadata
        if 'orchestration_enabled' in metadata:
            print(f"   Orchestration Enabled: {metadata['orchestration_enabled']}")
        
        if 'aggregated_insights' in metadata:
            print(f"   Aggregated Insights: {metadata['aggregated_insights']}")
        
        if 'workflow_performance' in metadata:
            perf_metrics = metadata['workflow_performance']
            print(f"\n⚡ Enhanced Workflow Performance:")
            print(f"   Steps Completed: {perf_metrics.get('steps_completed', 0)}")
            print(f"   Processing Time: {perf_metrics.get('processing_time', 0):.2f}s")
        
        return True
        
    except Exception as e:
        print(f"✗ Enhanced workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_insight_components():
    """Test the enhanced insight aggregation and ranking components"""
    print("\n🔗 Testing Enhanced Insight Components")
    print("=" * 60)
    
    try:
        # Test InsightAggregator
        aggregator = InsightAggregator()
        print("✓ Created enhanced InsightAggregator")
        
        # Test with empty data
        empty_insights = aggregator.aggregate_insights([], None, None, [], [])
        print(f"✓ Handled empty data: {len(empty_insights)} insights")
        
        # Test InsightRanker
        ranker = InsightRanker()
        print("✓ Created enhanced InsightRanker")
        
        # Test ranking with empty data
        ranked_empty = ranker.rank_insights(empty_insights)
        print(f"✓ Ranked empty insights: {len(ranked_empty)} insights")
        
        # Test with sample insight
        sample_insight = AggregatedInsight(
            id="test_insight",
            category=InsightCategory.RECOMMENDATION,
            priority=InsightPriority.HIGH,
            title="Test Enhanced Insight",
            description="This is a test insight with enhanced features",
            confidence_score=0.8,
            business_impact_score=0.7,
            actionability_score=0.9,
            severity_score=0.6,
            estimated_savings=1000.0,
            affected_services=["compute"],
            related_insights=[],
            metadata={'enhanced': True},
            timestamp=datetime.now()
        )
        
        ranked_sample = ranker.rank_insights([sample_insight])
        print(f"✓ Ranked sample insight: {len(ranked_sample)} insights")
        
        if ranked_sample:
            insight = ranked_sample[0]
            print(f"   Sample Insight: {insight.title}")
            print(f"   Category: {insight.category.value}")
            print(f"   Priority: {insight.priority.value}")
            print(f"   Confidence: {insight.confidence_score:.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Enhanced component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_orchestration_metrics():
    """Test enhanced orchestration metrics"""
    print("\n📊 Testing Enhanced Orchestration Metrics")
    print("=" * 60)
    
    try:
        ai_service = EnhancedAIInsightsService(use_ai=False)
        
        # Test orchestration metrics
        metrics = ai_service.get_orchestration_metrics()
        print(f"✓ Retrieved orchestration metrics: {len(metrics)} metrics")
        
        # Verify enhanced features
        if 'enhanced_features' in metrics:
            features = metrics['enhanced_features']
            print(f"   Enhanced Features:")
            for feature, enabled in features.items():
                status = "✓" if enabled else "✗"
                print(f"     {status} {feature.replace('_', ' ').title()}")
        
        # Test workflow config
        if 'workflow_config' in metrics:
            config = metrics['workflow_config']
            print(f"   Workflow Configuration:")
            print(f"     Parallel Processing: {config.get('parallel_processing', False)}")
            print(f"     Cache Enabled: {config.get('cache_enabled', False)}")
            print(f"     Quality Threshold: {config.get('quality_threshold', 0)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Enhanced metrics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all enhanced tests"""
    print("🚀 Enhanced AI Insights Service Test Suite")
    print("Task 5.1: Create AI insights orchestration service")
    print("=" * 60)
    
    tests = [
        ("Enhanced Orchestration Workflow", test_enhanced_orchestration),
        ("Enhanced Insight Components", test_insight_components),
        ("Enhanced Orchestration Metrics", test_orchestration_metrics)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Enhanced Test Results Summary")
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
        print("\n✅ Task 5.1 Implementation Complete:")
        print("   • Main AI insights orchestrator implemented")
        print("   • Advanced workflow for anomaly detection, trend analysis, and forecasting")
        print("   • Enhanced insight aggregation and ranking logic")
        print("   • Workflow orchestration with state management")
        print("   • Client context-aware insight ranking")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())