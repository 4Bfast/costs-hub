"""
Example usage of the main Lambda handler for cost reporting system.

This example demonstrates how to use the main handler for both scheduled
and manual executions.
"""

import json
from datetime import datetime
from src.handlers import lambda_handler


def example_scheduled_weekly_event():
    """Example EventBridge scheduled event for weekly reports."""
    return {
        "version": "0",
        "id": "12345678-1234-1234-1234-123456789012",
        "detail-type": "Scheduled Event - Weekly Cost Reports",
        "source": "aws.events",
        "account": "123456789012",
        "time": datetime.utcnow().isoformat() + "Z",
        "region": "us-east-1",
        "resources": [
            "arn:aws:events:us-east-1:123456789012:rule/cost-reporting-weekly"
        ],
        "detail": {
            "report_type": "weekly"
        }
    }


def example_scheduled_monthly_event():
    """Example EventBridge scheduled event for monthly reports."""
    return {
        "version": "0",
        "id": "12345678-1234-1234-1234-123456789012",
        "detail-type": "Scheduled Event - Monthly Cost Reports",
        "source": "aws.events",
        "account": "123456789012",
        "time": datetime.utcnow().isoformat() + "Z",
        "region": "us-east-1",
        "resources": [
            "arn:aws:events:us-east-1:123456789012:rule/cost-reporting-monthly"
        ],
        "detail": {
            "report_type": "monthly"
        }
    }


def example_manual_single_client_event():
    """Example manual execution for a single client."""
    return {
        "client_id": "client-123",
        "report_type": "monthly"
    }


def example_manual_all_clients_event():
    """Example manual execution for all clients."""
    return {
        "report_type": "weekly"
    }


class MockLambdaContext:
    """Mock Lambda context for testing."""
    
    def __init__(self, remaining_time_ms=300000):  # 5 minutes
        self.remaining_time_ms = remaining_time_ms
    
    def get_remaining_time_in_millis(self):
        return self.remaining_time_ms


def run_example(event, description):
    """Run an example with the given event."""
    print(f"\n{'='*60}")
    print(f"Example: {description}")
    print(f"{'='*60}")
    
    print("Event:")
    print(json.dumps(event, indent=2, default=str))
    
    try:
        context = MockLambdaContext()
        result = lambda_handler(event, context)
        
        print("\nResult:")
        print(json.dumps(result, indent=2, default=str))
        
        print(f"\nStatus: {'SUCCESS' if result['statusCode'] == 200 else 'FAILED'}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        print(f"Status: FAILED")


def main():
    """Run all examples."""
    print("Lambda Cost Reporting Handler Examples")
    print("=" * 60)
    
    # Note: These examples will fail without proper AWS configuration
    # and DynamoDB table setup, but they demonstrate the event structure
    
    examples = [
        (example_scheduled_weekly_event(), "Scheduled Weekly Reports"),
        (example_scheduled_monthly_event(), "Scheduled Monthly Reports"),
        (example_manual_single_client_event(), "Manual Single Client Report"),
        (example_manual_all_clients_event(), "Manual All Clients Report")
    ]
    
    for event, description in examples:
        run_example(event, description)
    
    print(f"\n{'='*60}")
    print("Examples completed!")
    print("Note: These examples require proper AWS configuration and DynamoDB setup to run successfully.")


if __name__ == "__main__":
    main()