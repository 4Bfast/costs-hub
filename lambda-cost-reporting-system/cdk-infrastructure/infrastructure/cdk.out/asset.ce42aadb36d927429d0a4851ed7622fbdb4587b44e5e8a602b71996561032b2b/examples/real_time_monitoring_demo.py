"""
Real-Time Monitoring Demo

Demonstrates how to use the real-time cost monitoring system with
AI insights, threshold monitoring, and multi-channel notifications.
"""

import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal

# Import the services
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.multi_cloud_models import UnifiedCostRecord, CloudProvider, ServiceCost, DataQuality
from models.config_models import ClientConfig
from services.real_time_integration_service import RealTimeIntegrationService
from services.real_time_monitoring_service import AlertSeverity, AlertType
from services.notification_service import NotificationChannel


async def demo_real_time_monitoring():
    """Demonstrate real-time monitoring capabilities"""
    
    print("🚀 Starting Real-Time Cost Monitoring Demo")
    print("=" * 50)
    
    # Initialize the integration service
    integration_service = RealTimeIntegrationService(use_ai=True, region="us-east-1")
    await integration_service.start_service()
    
    # Demo client configuration
    client_id = "demo-client-001"
    client_config = ClientConfig(
        client_id=client_id,
        client_name="Demo Company",
        aws_account_id="123456789012",
        region="us-east-1",
        cost_allocation_tags={"Environment": "Production", "Team": "Platform"}
    )
    
    # Monitoring configuration
    monitoring_config = {
        "enabled": True,
        "thresholds": [
            {
                "threshold_id": "daily_cost_limit",
                "threshold_type": "absolute",
                "threshold_value": 1000.0,
                "comparison_operator": "gt",
                "time_window_minutes": 5,
                "evaluation_periods": 1,
                "alert_severity": "high",
                "enabled": True,
                "metadata": {"description": "Daily cost limit threshold"}
            },
            {
                "threshold_id": "cost_rate_spike",
                "threshold_type": "rate",
                "threshold_value": 50.0,
                "comparison_operator": "gt",
                "time_window_minutes": 5,
                "evaluation_periods": 2,
                "alert_severity": "critical",
                "enabled": True,
                "metadata": {"description": "Cost rate spike detection"}
            }
        ],
        "notifications": [
            {
                "channel": "email",
                "enabled": True,
                "config": {
                    "email_address": "alerts@demo-company.com"
                },
                "severity_filter": ["critical", "high", "medium"],
                "alert_type_filter": [],
                "rate_limit": {
                    "max_notifications": 5,
                    "window_minutes": 60
                }
            },
            {
                "channel": "slack",
                "enabled": True,
                "config": {
                    "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
                },
                "severity_filter": ["critical", "high"],
                "alert_type_filter": ["cost_threshold", "anomaly_detected", "spike_detected"]
            }
        ]
    }
    
    print(f"📋 Setting up monitoring for client: {client_id}")
    
    # Setup client monitoring
    await integration_service.setup_client_monitoring(
        client_id, client_config, monitoring_config
    )
    
    print("✅ Monitoring setup completed")
    print()
    
    # Simulate cost data over time
    print("📊 Simulating cost data processing...")
    
    base_date = datetime.utcnow() - timedelta(days=30)
    
    # Generate historical data (normal costs)
    for day in range(30):
        cost_date = base_date + timedelta(days=day)
        
        # Normal daily cost with some variation
        base_cost = 800 + (day * 5)  # Gradual increase
        daily_variation = 50 if day % 7 < 5 else -30  # Weekday/weekend pattern
        total_cost = base_cost + daily_variation
        
        cost_record = create_sample_cost_record(
            client_id, cost_date.isoformat()[:10], total_cost
        )
        
        result = await integration_service.process_cost_data(
            client_id, cost_record, store_historical=True
        )
        
        if day % 10 == 0:  # Print progress every 10 days
            print(f"  📅 Processed day {day + 1}/30: ${total_cost:.2f}")
    
    print("✅ Historical data processing completed")
    print()
    
    # Simulate real-time events
    print("🔥 Simulating real-time cost events...")
    
    # Event 1: Normal cost update
    print("  📈 Event 1: Normal cost update")
    normal_cost_record = create_sample_cost_record(
        client_id, datetime.utcnow().isoformat()[:10], 950.0
    )
    
    result = await integration_service.process_cost_data(client_id, normal_cost_record)
    print(f"     Alerts generated: {result['alerts_generated']}")
    
    await asyncio.sleep(2)
    
    # Event 2: Cost spike (should trigger threshold alert)
    print("  🚨 Event 2: Cost spike (threshold breach)")
    spike_cost_record = create_sample_cost_record(
        client_id, datetime.utcnow().isoformat()[:10], 1200.0  # Above threshold
    )
    
    result = await integration_service.process_cost_data(client_id, spike_cost_record)
    print(f"     Alerts generated: {result['alerts_generated']}")
    
    if result['alerts']:
        for alert in result['alerts']:
            print(f"     🔔 Alert: {alert['title']} ({alert['severity']})")
    
    await asyncio.sleep(2)
    
    # Event 3: Anomalous service cost
    print("  ⚠️  Event 3: Anomalous service cost pattern")
    anomaly_cost_record = create_anomalous_cost_record(client_id)
    
    result = await integration_service.process_cost_data(client_id, anomaly_cost_record)
    print(f"     Alerts generated: {result['alerts_generated']}")
    
    if result['alerts']:
        for alert in result['alerts']:
            print(f"     🔔 Alert: {alert['title']} ({alert['severity']})")
    
    await asyncio.sleep(2)
    
    # Get real-time insights
    print("🧠 Getting AI-powered real-time insights...")
    insights = await integration_service.get_real_time_insights(client_id, include_ai_analysis=True)
    
    print(f"  📊 Monitoring Status: {insights['monitoring_status']['monitoring_enabled']}")
    print(f"  🚨 Active Alerts: {len(insights['active_alerts'])}")
    print(f"  📧 Notification Channels: {len(insights['notification_status']['configured_channels'])}")
    
    if 'ai_analysis' in insights and 'error' not in insights['ai_analysis']:
        ai_analysis = insights['ai_analysis']
        print(f"  🤖 AI Confidence: {ai_analysis['confidence_score']:.1%}")
        print(f"  ⚠️  Risk Level: {ai_analysis['risk_level']}")
        print(f"  💡 Key Insights: {len(ai_analysis['key_insights'])}")
        
        if ai_analysis['key_insights']:
            print("     Top insights:")
            for i, insight in enumerate(ai_analysis['key_insights'][:3], 1):
                print(f"     {i}. {insight}")
    
    print()
    
    # Demonstrate configuration updates
    print("⚙️  Demonstrating configuration updates...")
    
    config_updates = {
        "thresholds": [
            {
                "threshold_id": "updated_daily_limit",
                "threshold_type": "absolute",
                "threshold_value": 1500.0,  # Increased threshold
                "comparison_operator": "gt",
                "time_window_minutes": 5,
                "evaluation_periods": 1,
                "alert_severity": "high",
                "enabled": True,
                "metadata": {"description": "Updated daily cost limit"}
            }
        ]
    }
    
    await integration_service.update_monitoring_configuration(client_id, config_updates)
    print("✅ Configuration updated successfully")
    
    # Get service status
    print()
    print("📈 Service Status and Metrics:")
    status = integration_service.get_service_status()
    
    print(f"  🟢 Service Running: {status['service_running']}")
    print(f"  🌍 Region: {status['region']}")
    print(f"  🤖 AI Enabled: {status['ai_enabled']}")
    print(f"  👥 Clients Configured: {status['clients_configured']}")
    
    monitoring_metrics = status['monitoring_metrics']
    print(f"  📊 Active Clients: {monitoring_metrics['active_clients']}")
    print(f"  🚨 Total Active Alerts: {monitoring_metrics['total_active_alerts']}")
    print(f"  ⚡ Total Thresholds: {monitoring_metrics['total_thresholds']}")
    
    print()
    print("🎉 Real-Time Monitoring Demo Completed!")
    print("=" * 50)
    
    # Stop the service
    await integration_service.stop_service()


def create_sample_cost_record(client_id: str, date: str, total_cost: float) -> UnifiedCostRecord:
    """Create a sample cost record for testing"""
    
    # Distribute cost across services
    services = {
        "EC2-Instance": ServiceCost(
            service_name="EC2-Instance",
            unified_category="compute",
            cost=Decimal(str(total_cost * 0.4)),
            usage_metrics={"instance_hours": 24},
            provider_specific_data={"instance_type": "m5.large"}
        ),
        "S3": ServiceCost(
            service_name="S3",
            unified_category="storage",
            cost=Decimal(str(total_cost * 0.2)),
            usage_metrics={"storage_gb": 1000},
            provider_specific_data={"storage_class": "STANDARD"}
        ),
        "RDS": ServiceCost(
            service_name="RDS",
            unified_category="database",
            cost=Decimal(str(total_cost * 0.3)),
            usage_metrics={"db_hours": 24},
            provider_specific_data={"engine": "mysql"}
        ),
        "Lambda": ServiceCost(
            service_name="Lambda",
            unified_category="compute",
            cost=Decimal(str(total_cost * 0.1)),
            usage_metrics={"invocations": 10000},
            provider_specific_data={"runtime": "python3.9"}
        )
    }
    
    data_quality = DataQuality(
        completeness_score=0.95,
        accuracy_score=0.98,
        timeliness_score=1.0,
        consistency_score=0.97,
        validation_errors=[],
        confidence_level="HIGH"
    )
    
    return UnifiedCostRecord(
        client_id=client_id,
        provider=CloudProvider.AWS,
        date=date,
        total_cost=Decimal(str(total_cost)),
        currency="USD",
        services=services,
        accounts={"123456789012": {"cost": Decimal(str(total_cost)), "name": "Production"}},
        regions={"us-east-1": {"cost": Decimal(str(total_cost * 0.8)), "name": "US East 1"}},
        collection_metadata={
            "collection_timestamp": datetime.utcnow().isoformat(),
            "api_calls_made": 5,
            "processing_time_seconds": 2.5
        },
        data_quality=data_quality,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


def create_anomalous_cost_record(client_id: str) -> UnifiedCostRecord:
    """Create an anomalous cost record to trigger anomaly detection"""
    
    # Create unusual service distribution
    services = {
        "EC2-Instance": ServiceCost(
            service_name="EC2-Instance",
            unified_category="compute",
            cost=Decimal("2000.0"),  # Unusually high
            usage_metrics={"instance_hours": 24},
            provider_specific_data={"instance_type": "m5.large"}
        ),
        "Unknown-Service": ServiceCost(  # New service
            service_name="Unknown-Service",
            unified_category="other",
            cost=Decimal("500.0"),
            usage_metrics={},
            provider_specific_data={}
        ),
        "S3": ServiceCost(
            service_name="S3",
            unified_category="storage",
            cost=Decimal("50.0"),  # Unusually low
            usage_metrics={"storage_gb": 1000},
            provider_specific_data={"storage_class": "STANDARD"}
        )
    }
    
    data_quality = DataQuality(
        completeness_score=0.85,  # Lower quality
        accuracy_score=0.90,
        timeliness_score=1.0,
        consistency_score=0.80,
        validation_errors=["Unknown service detected"],
        confidence_level="MEDIUM"
    )
    
    return UnifiedCostRecord(
        client_id=client_id,
        provider=CloudProvider.AWS,
        date=datetime.utcnow().isoformat()[:10],
        total_cost=Decimal("2550.0"),  # High total
        currency="USD",
        services=services,
        accounts={"123456789012": {"cost": Decimal("2550.0"), "name": "Production"}},
        regions={"us-east-1": {"cost": Decimal("2550.0"), "name": "US East 1"}},
        collection_metadata={
            "collection_timestamp": datetime.utcnow().isoformat(),
            "api_calls_made": 5,
            "processing_time_seconds": 2.5
        },
        data_quality=data_quality,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_real_time_monitoring())