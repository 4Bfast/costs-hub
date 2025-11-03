"""
Example of comprehensive logging integration in the Lambda Cost Reporting System.

This example demonstrates how to use structured logging, correlation IDs,
and monitoring integration throughout the application components.
"""

import os
import time
from datetime import datetime

# Set up structured logging for the example
os.environ['USE_STRUCTURED_LOGGING'] = 'true'
os.environ['LOG_LEVEL'] = 'INFO'

from src.utils.logging import create_logger, log_execution_context, mask_sensitive_data_in_object
from src.services.monitoring_service import MonitoringService, AlertSeverity


def example_main_handler_integration():
    """Example of integrating monitoring and logging in the main handler"""
    
    # Initialize monitoring service (creates correlation ID)
    monitoring = MonitoringService(namespace="CostReporting/Example")
    
    # Create logger with correlation ID
    logger = create_logger(__name__, correlation_id=monitoring.execution_id)
    
    # Start execution tracking
    execution_id = monitoring.start_execution(report_type="weekly", client_count=3)
    
    logger.info("Lambda handler started", extra={
        "execution_id": execution_id,
        "report_type": "weekly",
        "environment": "example"
    })
    
    # Simulate processing multiple clients
    clients = ["client-001", "client-002", "client-003"]
    
    for client_id in clients:
        with log_execution_context(logger, "process_client", client_id=client_id) as ctx:
            try:
                # Simulate client processing
                process_client_example(client_id, monitoring, logger)
                
                # Update context with results
                ctx.update({
                    "reports_generated": 1,
                    "emails_sent": 1,
                    "total_cost": 1234.56
                })
                
            except Exception as e:
                # Record error with monitoring service
                monitoring.record_error(
                    error=e,
                    component="client_processing",
                    client_id=client_id,
                    context=ctx,
                    severity=AlertSeverity.HIGH
                )
                raise
    
    # End execution tracking
    final_metrics = monitoring.end_execution(success=True)
    
    logger.info("Lambda handler completed", extra={
        "execution_id": execution_id,
        "final_metrics": final_metrics.clients_processed,
        "duration_seconds": final_metrics.duration_seconds
    })


def process_client_example(client_id: str, monitoring: MonitoringService, logger):
    """Example of client processing with monitoring and logging"""
    
    start_time = time.time()
    
    try:
        # Step 1: Load client configuration
        with monitoring.track_operation("load_client_config", client_id):
            config = load_client_config_example(client_id, logger)
        
        # Step 2: Collect cost data
        with monitoring.track_operation("collect_cost_data", client_id):
            cost_data = collect_cost_data_example(client_id, config, logger)
        
        # Step 3: Generate report
        with monitoring.track_operation("generate_report", client_id):
            report_url = generate_report_example(client_id, cost_data, logger)
        
        # Step 4: Send email
        with monitoring.track_operation("send_email", client_id):
            email_success = send_email_example(client_id, report_url, logger)
        
        # Record successful client processing
        duration = time.time() - start_time
        monitoring.record_client_processing(
            client_id=client_id,
            success=True,
            duration_seconds=duration
        )
        
        logger.info(f"Client {client_id} processed successfully", extra={
            "client_id": client_id,
            "duration_seconds": duration,
            "report_url": report_url,
            "email_sent": email_success
        })
        
    except Exception as e:
        duration = time.time() - start_time
        monitoring.record_client_processing(
            client_id=client_id,
            success=False,
            duration_seconds=duration,
            error=str(e)
        )
        raise


def load_client_config_example(client_id: str, logger):
    """Example of loading client configuration with sensitive data masking"""
    
    logger.info(f"Loading configuration for client {client_id}")
    
    # Simulate loading configuration with sensitive data
    raw_config = {
        "client_id": client_id,
        "client_name": "Example Corp",
        "aws_accounts": [
            {
                "account_id": "123456789012",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "region": "us-east-1"
            }
        ],
        "report_config": {
            "recipients": ["admin@example.com"],
            "weekly_enabled": True
        }
    }
    
    # Log configuration (sensitive data will be automatically masked)
    logger.info("Client configuration loaded", extra={
        "client_id": client_id,
        "config": mask_sensitive_data_in_object(raw_config)
    })
    
    return raw_config


def collect_cost_data_example(client_id: str, config: dict, logger):
    """Example of cost data collection with error handling"""
    
    logger.info(f"Collecting cost data for client {client_id}", extra={
        "client_id": client_id,
        "account_count": len(config["aws_accounts"])
    })
    
    # Simulate cost data collection
    time.sleep(0.1)  # Simulate API call
    
    cost_data = {
        "total_cost": 1234.56,
        "service_count": 15,
        "account_count": len(config["aws_accounts"]),
        "periods_data": [
            {"period": "2024-01", "total_cost": 1234.56},
            {"period": "2023-12", "total_cost": 1100.00}
        ]
    }
    
    logger.info("Cost data collected successfully", extra={
        "client_id": client_id,
        "total_cost": cost_data["total_cost"],
        "service_count": cost_data["service_count"],
        "account_count": cost_data["account_count"]
    })
    
    return cost_data


def generate_report_example(client_id: str, cost_data: dict, logger):
    """Example of report generation with performance tracking"""
    
    start_time = time.time()
    
    logger.info(f"Generating report for client {client_id}", extra={
        "client_id": client_id,
        "total_cost": cost_data["total_cost"]
    })
    
    # Simulate report generation
    time.sleep(0.2)  # Simulate report processing
    
    report_url = f"s3://cost-reports/{client_id}/report-{datetime.now().strftime('%Y%m%d')}.html"
    
    duration = time.time() - start_time
    
    logger.info("Report generated successfully", extra={
        "client_id": client_id,
        "report_url": report_url,
        "generation_duration_seconds": duration
    })
    
    return report_url


def send_email_example(client_id: str, report_url: str, logger):
    """Example of email sending with retry logic logging"""
    
    logger.info(f"Sending email report for client {client_id}", extra={
        "client_id": client_id,
        "report_url": report_url
    })
    
    # Simulate email sending with potential retry
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Email send attempt {attempt}", extra={
                "client_id": client_id,
                "attempt": attempt,
                "max_retries": max_retries
            })
            
            # Simulate email API call
            time.sleep(0.1)
            
            # Simulate occasional failure
            if attempt == 1 and client_id == "client-002":
                raise Exception("Temporary SES throttling")
            
            logger.info("Email sent successfully", extra={
                "client_id": client_id,
                "attempt": attempt,
                "recipients": ["admin@example.com"]
            })
            
            return True
            
        except Exception as e:
            logger.warning(f"Email send attempt {attempt} failed", extra={
                "client_id": client_id,
                "attempt": attempt,
                "error": str(e)
            })
            
            if attempt == max_retries:
                logger.error("All email send attempts failed", extra={
                    "client_id": client_id,
                    "total_attempts": max_retries,
                    "final_error": str(e)
                })
                return False
            
            time.sleep(2 ** attempt)  # Exponential backoff
    
    return False


def example_error_scenarios():
    """Example of different error scenarios and their logging"""
    
    monitoring = MonitoringService(namespace="CostReporting/ErrorExample")
    logger = create_logger(__name__, correlation_id=monitoring.execution_id)
    
    # Example 1: Configuration error (medium severity)
    try:
        raise ValueError("Invalid client configuration: missing AWS account")
    except Exception as e:
        monitoring.record_error(
            error=e,
            component="config_validation",
            client_id="client-001",
            context={"validation_step": "aws_accounts"},
            severity=AlertSeverity.MEDIUM
        )
    
    # Example 2: AWS API error (high severity)
    try:
        raise Exception("AWS Cost Explorer API throttling: Rate exceeded")
    except Exception as e:
        monitoring.record_error(
            error=e,
            component="cost_collection",
            client_id="client-002",
            context={"api": "cost_explorer", "operation": "get_cost_and_usage"},
            severity=AlertSeverity.HIGH
        )
    
    # Example 3: Critical system error
    try:
        raise Exception("DynamoDB table not found: cost-reporting-clients")
    except Exception as e:
        monitoring.record_error(
            error=e,
            component="database",
            context={"table": "cost-reporting-clients", "operation": "get_item"},
            severity=AlertSeverity.CRITICAL
        )


if __name__ == "__main__":
    print("Running logging integration examples...")
    
    print("\n1. Main handler integration example:")
    example_main_handler_integration()
    
    print("\n2. Error scenarios example:")
    example_error_scenarios()
    
    print("\nExamples completed. Check CloudWatch logs for structured output.")