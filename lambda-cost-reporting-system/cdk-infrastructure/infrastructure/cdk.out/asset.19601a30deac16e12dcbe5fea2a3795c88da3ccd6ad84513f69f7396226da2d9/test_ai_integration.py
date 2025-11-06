"""
Test script for AI and ML foundation components
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add the src directory to the path
sys.path.append(os.path.dirname(__file__))

try:
    from models.multi_cloud_models import UnifiedCostRecord, ServiceCost, CloudProvider
    from services.ai_insights_service import AIInsightsService
    from services.bedrock_service import BedrockService, BedrockConfig
    from services.anomaly_detection_engine import AnomalyDetectionEngine
    from services.trend_analysis_service import TrendAnalyzer
    from services.forecasting_engine import ForecastingEngine
    
    print("✓ All AI components imported successfully")
    
    # Create sample data
    sample_data = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(30):
        date = (base_date + timedelta(days=i)).isoformat()[:10]
        
        # Create sample service costs with some variation
        services = {
            'EC2': ServiceCost(
                service_name='EC2',
                unified_category='compute',
                cost=Decimal(str(100 + i * 2 + (i % 7) * 10)),  # Weekly pattern
                usage_metrics={},
                provider_specific_data={}
            ),
            'S3': ServiceCost(
                service_name='S3',
                unified_category='storage',
                cost=Decimal(str(50 + i * 0.5)),
                usage_metrics={},
                provider_specific_data={}
            )
        }
        
        total_cost = sum(service.cost for service in services.values())
        
        record = UnifiedCostRecord(
            client_id='test-client',
            provider=CloudProvider.AWS,
            date=date,
            total_cost=total_cost,
            currency='USD',
            services=services,
            accounts={},
            regions={},
            collection_metadata={},
            data_quality={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        sample_data.append(record)
    
    print(f"✓ Created {len(sample_data)} sample cost records")
    
    # Test individual components (without AI to avoid AWS dependencies)
    print("\nTesting individual components:")
    
    # Test Anomaly Detection Engine
    anomaly_detector = AnomalyDetectionEngine(use_ai=False)
    anomalies = anomaly_detector.detect_anomalies(
        sample_data[-7:], sample_data[:-7], None
    )
    print(f"✓ Anomaly Detection: Found {len(anomalies)} anomalies")
    
    # Test Trend Analyzer
    trend_analyzer = TrendAnalyzer()
    trends = trend_analyzer.analyze_trends(sample_data)
    print(f"✓ Trend Analysis: Overall trend direction is {trends.overall_trend.direction.value}")
    
    # Test Forecasting Engine
    forecasting_engine = ForecastingEngine(use_ai=False)
    forecasts = forecasting_engine.generate_forecast(sample_data, forecast_horizon=7)
    print(f"✓ Forecasting: Generated {len(forecasts.predictions)} forecast points")
    
    # Test AI Insights Service (without AI)
    ai_insights_service = AIInsightsService(use_ai=False)
    insights = ai_insights_service.generate_insights(
        'test-client', sample_data, None, None
    )
    print(f"✓ AI Insights: Generated {len(insights.recommendations)} recommendations")
    print(f"  Executive Summary: {insights.executive_summary[:100]}...")
    
    print("\n✅ All AI and ML foundation components are working correctly!")
    print("\nNote: AI features (Bedrock integration) were not tested to avoid AWS dependencies.")
    print("To test AI features, ensure AWS credentials are configured and Bedrock is available.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all dependencies are installed and paths are correct.")
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()