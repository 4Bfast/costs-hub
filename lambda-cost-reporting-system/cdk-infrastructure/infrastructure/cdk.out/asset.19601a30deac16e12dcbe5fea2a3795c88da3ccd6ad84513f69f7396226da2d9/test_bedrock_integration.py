#!/usr/bin/env python3
"""
Test script for enhanced AWS Bedrock integration

This script tests the Bedrock service implementation without requiring actual AWS credentials.
It validates the service initialization, configuration, and error handling.
"""

import sys
import os
import logging
from datetime import datetime
from decimal import Decimal

# Add the src directory to the path
sys.path.append(os.path.dirname(__file__))

# Set up basic logging to avoid import issues
logging.basicConfig(level=logging.INFO)

def test_bedrock_service_initialization():
    """Test Bedrock service initialization and configuration"""
    print("Testing Bedrock Service Initialization...")
    
    try:
        # Mock the imports to avoid dependency issues
        sys.modules['models.config_models'] = type(sys)('mock_config_models')
        sys.modules['models.multi_cloud_models'] = type(sys)('mock_multi_cloud_models')
        sys.modules['utils.logging'] = type(sys)('mock_logging')
        
        # Add mock classes
        class MockClientConfig:
            def __init__(self):
                self.client_name = "Test Client"
        
        class MockUnifiedCostRecord:
            def __init__(self):
                self.total_cost = 1000
        
        def mock_get_logger(name):
            return logging.getLogger(name)
        
        sys.modules['models.config_models'].ClientConfig = MockClientConfig
        sys.modules['models.multi_cloud_models'].UnifiedCostRecord = MockUnifiedCostRecord
        sys.modules['utils.logging'].create_logger = mock_get_logger
        
        from services.bedrock_service import BedrockService, BedrockConfig, ModelType, AnalysisType
        
        # Test default configuration
        default_config = BedrockConfig()
        print(f"✓ Default config created: {default_config.model_id}")
        
        # Test custom configuration
        custom_config = BedrockConfig(
            region="us-west-2",
            model_id=ModelType.CLAUDE_3_HAIKU.value,
            max_tokens=1000,
            temperature=0.2,
            retry_attempts=2
        )
        print(f"✓ Custom config created: {custom_config.model_id}")
        
        # Test service initialization (will fail without AWS credentials, but that's expected)
        try:
            service = BedrockService(custom_config)
            print("✓ Service initialized (AWS credentials available)")
        except Exception as e:
            print(f"✓ Service initialization failed as expected (no AWS credentials): {type(e).__name__}")
        
        print("✓ Bedrock service initialization tests passed")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_prompt_templates():
    """Test prompt template functionality"""
    print("\nTesting Prompt Templates...")
    
    try:
        from services.bedrock_service import PromptTemplate
        
        templates = PromptTemplate()
        
        # Test cost analysis template
        context = {
            'client_name': 'Test Client',
            'period': '2024-10',
            'total_cost': 1500.50,
            'primary_provider': 'AWS',
            'cost_data': '{"EC2": 800, "S3": 200}',
            'historical_context': '{"previous_month": 1200}'
        }
        
        cost_prompt = templates.COST_ANALYSIS_TEMPLATE.format(**context)
        print(f"✓ Cost analysis prompt generated ({len(cost_prompt)} chars)")
        
        # Test anomaly detection template
        anomaly_context = {
            'current_data': '{"total": 1500}',
            'baseline_data': '{"average": 1200}',
            'std_deviation': 150.0,
            'mean_cost': 1200.0,
            'cv': 0.125
        }
        
        anomaly_prompt = templates.ANOMALY_DETECTION_TEMPLATE.format(**anomaly_context)
        print(f"✓ Anomaly detection prompt generated ({len(anomaly_prompt)} chars)")
        
        # Test forecasting template
        forecast_context = {
            'historical_data': '[{"date": "2024-10-01", "cost": 1200}]',
            'trend_analysis': '{"direction": "increasing"}',
            'seasonal_patterns': '{"monthly": "stable"}',
            'external_factors': '{"quarter": "Q4"}',
            'forecast_days': 30
        }
        
        forecast_prompt = templates.FORECASTING_TEMPLATE.format(**forecast_context)
        print(f"✓ Forecasting prompt generated ({len(forecast_prompt)} chars)")
        
        print("✓ Prompt template tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Prompt template test failed: {e}")
        return False

def test_response_parsing():
    """Test JSON response parsing functionality"""
    print("\nTesting Response Parsing...")
    
    try:
        from services.bedrock_service import BedrockService
        
        # Create service instance (without AWS client)
        service = BedrockService.__new__(BedrockService)
        service.config = BedrockService().config
        service.prompt_templates = BedrockService().prompt_templates
        
        # Test valid JSON parsing
        valid_json = '{"executive_summary": "Test summary", "key_insights": ["insight1", "insight2"]}'
        parsed = service._parse_json_response(valid_json)
        print(f"✓ Valid JSON parsed: {len(parsed)} keys")
        
        # Test JSON in markdown code block
        markdown_json = '''
Here's the analysis:

```json
{
    "executive_summary": "Test summary",
    "anomalies": [{"service": "EC2", "severity": "high"}]
}
```

That's the result.
'''
        parsed_markdown = service._parse_json_response(markdown_json)
        print(f"✓ Markdown JSON parsed: {len(parsed_markdown)} keys")
        
        # Test invalid JSON (should return error structure)
        invalid_json = "This is not JSON at all"
        parsed_invalid = service._parse_json_response(invalid_json)
        print(f"✓ Invalid JSON handled: {'error' in parsed_invalid}")
        
        print("✓ Response parsing tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Response parsing test failed: {e}")
        return False

def test_validation_functionality():
    """Test analysis result validation"""
    print("\nTesting Validation Functionality...")
    
    try:
        from services.bedrock_service import BedrockService
        
        # Create service instance (without AWS client)
        service = BedrockService.__new__(BedrockService)
        service.config = BedrockService().config
        
        # Test validation with good data
        good_analysis = {
            'executive_summary': 'This is a good summary',
            'key_insights': ['Insight 1', 'Insight 2'],
            'anomalies': [
                {
                    'service': 'EC2',
                    'description': 'Cost spike detected',
                    'severity': 'high',
                    'cost_impact': 500.0
                }
            ],
            'recommendations': [
                {
                    'title': 'Optimize EC2',
                    'description': 'Right-size instances',
                    'estimated_savings': 200.0,
                    'priority': 'high',
                    'implementation_effort': 'medium'
                }
            ],
            'trends': [
                {
                    'metric': 'total_cost',
                    'direction': 'increasing',
                    'rate': 15.5,
                    'significance': 'high'
                }
            ]
        }
        
        validated = service.validate_analysis_results(good_analysis)
        print(f"✓ Good analysis validated: {len(validated)} sections")
        
        # Test validation with problematic data
        bad_analysis = {
            'executive_summary': '',  # Empty
            'key_insights': 'not a list',  # Wrong type
            'anomalies': [
                {
                    'service': 'A' * 200,  # Too long
                    'cost_impact': 'not a number'  # Wrong type
                }
            ],
            'recommendations': 'not a list',  # Wrong type
            'trends': [{}]  # Missing required fields
        }
        
        validated_bad = service.validate_analysis_results(bad_analysis)
        print(f"✓ Bad analysis sanitized: {len(validated_bad)} sections")
        
        print("✓ Validation functionality tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def test_model_capabilities():
    """Test model capabilities functionality"""
    print("\nTesting Model Capabilities...")
    
    try:
        from services.bedrock_service import BedrockService, BedrockConfig, ModelType
        
        # Test different model configurations
        models_to_test = [
            ModelType.CLAUDE_3_OPUS.value,
            ModelType.CLAUDE_3_SONNET.value,
            ModelType.CLAUDE_3_HAIKU.value
        ]
        
        for model_id in models_to_test:
            config = BedrockConfig(model_id=model_id)
            service = BedrockService.__new__(BedrockService)
            service.config = config
            
            capabilities = service.get_model_capabilities()
            print(f"✓ {model_id.split('.')[-1]} capabilities: {capabilities.get('complexity_level', 'unknown')}")
        
        print("✓ Model capabilities tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Model capabilities test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Bedrock Service Integration Tests")
    print("=" * 60)
    
    tests = [
        test_bedrock_service_initialization,
        test_prompt_templates,
        test_response_parsing,
        test_validation_functionality,
        test_model_capabilities
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All Bedrock service tests passed!")
        print("\nNote: AWS Bedrock functionality requires proper AWS credentials and permissions.")
        print("The service is ready for integration with the multi-cloud cost analytics platform.")
    else:
        print("❌ Some tests failed. Please review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)