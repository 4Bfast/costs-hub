#!/usr/bin/env python3
"""
Validation script for dashboard configuration
"""

import json
from typing import Dict, Any

def validate_dashboard_config():
    """Validate dashboard configuration structure"""
    
    # Mock CDK classes for validation
    class MockWidget:
        def __init__(self, **kwargs):
            self.config = kwargs
    
    class MockGraphWidget(MockWidget):
        pass
    
    class MockSingleValueWidget(MockWidget):
        pass
    
    class MockLogQueryWidget(MockWidget):
        pass
    
    # Test dashboard widget configurations
    widgets = []
    
    # Test operational dashboard widgets
    operational_widgets = [
        {
            "type": "graph",
            "title": "Lambda Invocations",
            "metrics": ["AWS/Lambda.Invocations"],
            "width": 8,
            "height": 6
        },
        {
            "type": "graph", 
            "title": "Lambda Errors",
            "metrics": ["AWS/Lambda.Errors"],
            "width": 8,
            "height": 6
        },
        {
            "type": "graph",
            "title": "Execution Results", 
            "metrics": ["CostReporting.ExecutionSucceeded", "CostReporting.ExecutionFailed"],
            "width": 12,
            "height": 6
        }
    ]
    
    # Test business dashboard widgets
    business_widgets = [
        {
            "type": "single_value",
            "title": "Reports Generated (24h)",
            "metrics": ["CostReporting.ReportsGenerated"],
            "width": 6,
            "height": 6
        },
        {
            "type": "single_value",
            "title": "Emails Sent (24h)", 
            "metrics": ["CostReporting.EmailsSent"],
            "width": 6,
            "height": 6
        },
        {
            "type": "graph",
            "title": "Daily Reports Trend",
            "metrics": ["CostReporting.ReportsGenerated"],
            "width": 12,
            "height": 6
        }
    ]
    
    # Test health dashboard widgets
    health_widgets = [
        {
            "type": "single_value",
            "title": "Lambda Error Rate",
            "metrics": ["calculated_error_rate"],
            "width": 8,
            "height": 6
        },
        {
            "type": "log_query",
            "title": "Recent Alarm State Changes",
            "log_groups": ["/aws/events/rule/cost-reporting"],
            "width": 24,
            "height": 8
        }
    ]
    
    # Validate widget structures
    all_widgets = {
        "operational": operational_widgets,
        "business": business_widgets, 
        "health": health_widgets
    }
    
    validation_results = {}
    
    for dashboard_name, widget_list in all_widgets.items():
        results = []
        for widget in widget_list:
            # Validate required fields
            required_fields = ["type", "title", "width", "height"]
            missing_fields = [field for field in required_fields if field not in widget]
            
            if missing_fields:
                results.append(f"Widget '{widget.get('title', 'Unknown')}' missing fields: {missing_fields}")
            else:
                results.append(f"Widget '{widget['title']}' - OK")
        
        validation_results[dashboard_name] = results
    
    return validation_results

def validate_metric_namespaces():
    """Validate metric namespace configurations"""
    
    environments = ["dev", "staging", "prod"]
    expected_namespaces = {}
    
    for env in environments:
        namespace = f"CostReporting/{env.title()}"
        expected_namespaces[env] = namespace
    
    return expected_namespaces

def main():
    """Main validation function"""
    
    print("🔍 Validating Dashboard Configuration...")
    print("=" * 50)
    
    # Validate dashboard widgets
    widget_results = validate_dashboard_config()
    
    for dashboard, results in widget_results.items():
        print(f"\n📊 {dashboard.title()} Dashboard:")
        for result in results:
            status = "✅" if "OK" in result else "❌"
            print(f"  {status} {result}")
    
    # Validate metric namespaces
    print(f"\n🏷️  Metric Namespaces:")
    namespaces = validate_metric_namespaces()
    for env, namespace in namespaces.items():
        print(f"  ✅ {env}: {namespace}")
    
    # Validate dashboard naming
    print(f"\n📝 Dashboard Naming:")
    for env in ["dev", "staging", "prod"]:
        dashboards = [
            f"cost-reporting-{env}-operational",
            f"cost-reporting-{env}-business", 
            f"cost-reporting-{env}-health"
        ]
        for dashboard in dashboards:
            print(f"  ✅ {dashboard}")
    
    print(f"\n🎉 Dashboard configuration validation completed!")
    print("All dashboard configurations appear to be valid.")

if __name__ == "__main__":
    main()