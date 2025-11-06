#!/usr/bin/env python3
"""
Standalone test for enhanced AI Insights Service orchestration

This test directly imports and tests the AI insights service components
without relying on the full services package.
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional
from collections import defaultdict

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

# Mock the dependencies
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
    
    def _get_default_analysis(self):
        return self.analyze_trends([])

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
    
    def _get_minimal_forecast(self, cost_data, horizon):
        return self.generate_forecast(cost_data, horizon)

class MockRecommendationEngine:
    def __init__(self, use_ai=True):
        self.use_ai = use_ai
    
    def generate_recommendations(self, cost_data, anomalies, trends, forecasts, client_context=None):
        return []

class MockBedrockService:
    def generate_cost_recommendations(self, context, client_context):
        return {'recommendations': []}

# Create proper enum classes
class AnomalyType(Enum):
    COST_SPIKE = 'cost_spike'
    COST_DROP = 'cost_drop'

class Severity(Enum):
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'
    CRITICAL = 'critical'

@dataclass
class Anomaly:
    type: AnomalyType
    severity: Severity
    description: str
    affected_services: List[str]
    cost_impact: float
    detection_method: str
    confidence_score: float
    recommended_actions: List[str]
    timestamp: datetime

# Mock the service modules
sys.modules['services.anomaly_detection_engine'] = type('MockModule', (), {
    'AnomalyDetectionEngine': MockAnomalyDetectionEngine,
    'Anomaly': Anomaly,
    'AnomalyType': AnomalyType,
    'Severity': Severity
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

# Now import the AI insights service directly
try:
    # Import directly from the file to avoid services package issues
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ai_insights_service", 
        os.path.join(os.path.dirname(__file__), "services", "ai_insights_service.py")
    )
    ai_insights_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ai_insights_module)
    
    # Extract the classes we need
    AIInsightsService = ai_insights_module.AIInsightsService
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
        ai_service = AIInsightsService(use_ai=False)  # Disable AI for testing
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
        
        print("\n📊 Running orchestrated insights workflow...")
        
        # Run the enhanced orchestration workflow
        insights = ai_service.orchestrate_insights_workflow(
            client_id='test-client-123',
            cost_data=cost_data,
            client_config=client_config,
            budget_info=budget_info,
            workflow_options={'enable_caching': True}
        )
        
        print("✓ Workflow completed successfully")
        
        # Verify insights structure
        assert hasattr(insights, 'executive_summary'), "Missing executive_summary"
        assert hasattr(insights, 'metadata'), "Missing metadata"
        print("✓ Insights structure verified")
        
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
        
        return True
        
    except Exception as e:
        print(f"✗ Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_insight_components():
    """Test the insight aggregation and ranking components"""
    print("\n🔗 Testing Insight Aggregation and Ranking Components")
    print("=" * 60)
    
    try:
        # Test InsightAggregator
        aggregator = InsightAggregator()
        print("✓ Created InsightAggregator")
        
        # Test with empty data
        empty_insights = aggregator.aggregate_insights([], None, None, [], [])
        print(f"✓ Handled empty data: {len(empty_insights)} insights")
        
        # Test InsightRanker
        ranker = InsightRanker()
        print("✓ Created InsightRanker")
        
        # Test ranking with empty data
        ranked_empty = ranker.rank_insights(empty_insights)
        print(f"✓ Ranked empty insights: {len(ranked_empty)} insights")
        
        # Test with sample insight
        sample_insight = AggregatedInsight(
            id="test_insight",
            category=InsightCategory.RECOMMENDATION,
            priority=InsightPriority.HIGH,
            title="Test Insight",
            description="This is a test insight",
            confidence_score=0.8,
            business_impact_score=0.7,
            actionability_score=0.9,
            severity_score=0.6,
            estimated_savings=1000.0,
            affected_services=["compute"],
            related_insights=[],
            metadata={},
            timestamp=datetime.now()
        )
        
        ranked_sample = ranker.rank_insights([sample_insight])
        print(f"✓ Ranked sample insight: {len(ranked_sample)} insights")
        
        return True
        
    except Exception as e:
        print(f"✗ Component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_management():
    """Test workflow management features"""
    print("\n📊 Testing Workflow Management")
    print("=" * 60)
    
    try:
        ai_service = AIInsightsService(use_ai=False)
        
        # Test performance metrics
        metrics = ai_service.get_insights_performance_metrics()
        print(f"✓ Retrieved performance metrics: {len(metrics)} metrics")
        
        # Test active workflows
        active = ai_service.list_active_workflows()
        print(f"✓ Listed active workflows: {len(active)} active")
        
        # Test workflow cleanup
        ai_service.cleanup_completed_workflows(max_age_hours=0)
        print("✓ Tested workflow cleanup")
        
        return True
        
    except Exception as e:
        print(f"✗ Workflow management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("🚀 Enhanced AI Insights Service Test Suite")
    print("=" * 60)
    
    tests = [
        ("Enhanced Orchestration", test_enhanced_orchestration),
        ("Insight Components", test_insight_components),
        ("Workflow Management", test_workflow_management)
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