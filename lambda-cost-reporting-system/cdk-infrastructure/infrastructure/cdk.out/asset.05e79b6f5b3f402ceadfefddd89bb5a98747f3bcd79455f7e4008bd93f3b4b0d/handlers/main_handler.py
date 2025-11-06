"""
Main Lambda Handler for Cost Reporting System

This module provides the main entry point for the Lambda function that orchestrates
the execution of cost reports for all active clients. It handles both scheduled
and manual executions with comprehensive error handling and retry logic.
"""

import json
import logging
import os
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit

from ..models import ClientConfig, ReportType, ClientStatus
from ..services import (
    ClientConfigManager,
    LambdaCostAgent,
    LambdaReportGenerator,
    LambdaEmailService,
    LambdaAssetManager,
    AlertIntegrationService
)
from ..utils import create_logger, log_execution_context
from ..services.monitoring_service import MonitoringService, AlertSeverity
from .scheduler import SchedulingManager
from .error_handler import ErrorHandler, handle_component_error, retry_operation, with_error_handling


# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Environment variables
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'cost-reporting-clients')
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'cost-reporting-bucket')
KMS_KEY_ID = os.environ.get('KMS_KEY_ID')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')


class LambdaCostReportHandler:
    """
    Main handler class for Lambda cost reporting system.
    
    Orchestrates the execution of cost reports for all active clients,
    handling both scheduled and manual executions with comprehensive
    error handling and retry logic.
    """
    
    def __init__(self):
        """Initialize the handler with required services."""
        # Initialize monitoring service first to get correlation ID
        environment = os.environ.get('ENVIRONMENT', 'dev')
        self.monitoring = MonitoringService(
            region=AWS_REGION,
            namespace=f"CostReporting/{environment.title()}"
        )
        
        # Create structured logger with correlation ID
        self.structured_logger = create_logger(
            __name__, 
            correlation_id=self.monitoring.execution_id
        )
        
        self.config_manager = ClientConfigManager(
            table_name=TABLE_NAME,
            region=AWS_REGION,
            kms_key_id=KMS_KEY_ID
        )
        
        self.report_generator = LambdaReportGenerator(
            s3_bucket=S3_BUCKET,
            s3_prefix="reports"
        )
        
        self.email_service = LambdaEmailService(
            region=AWS_REGION,
            sender_email=SENDER_EMAIL
        )
        
        self.asset_manager = LambdaAssetManager(
            s3_bucket=S3_BUCKET,
            s3_prefix="assets"
        )
        
        self.alert_service = AlertIntegrationService()
        self.scheduler = SchedulingManager(self.config_manager)
        self.error_handler = ErrorHandler()
        
        # Execution statistics (kept for backward compatibility)
        self.execution_stats = {
            'clients_processed': 0,
            'clients_succeeded': 0,
            'clients_failed': 0,
            'reports_generated': 0,
            'emails_sent': 0,
            'errors': []
        }
    
    @tracer.capture_lambda_handler
    @logger.inject_lambda_context(correlation_id_path=correlation_paths.EVENT_BRIDGE)
    def lambda_handler(self, event: Dict[str, Any], context) -> Dict[str, Any]:
        """
        Main Lambda handler entry point.
        
        Args:
            event: Lambda event data
            context: Lambda context object
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Determine execution parameters first
            execution_type = self._determine_execution_type(event)
            report_type = self._get_report_type(event)
            
            # Start monitoring with context
            self.monitoring.start_execution(
                report_type=report_type,
                client_count=0  # Will be updated later
            )
            
            # Log execution start with structured logging
            self.structured_logger.info("Lambda cost reporting execution started", extra={
                "event_source": event.get('source'),
                "execution_type": execution_type,
                "report_type": report_type,
                "remaining_time_ms": context.get_remaining_time_in_millis() if context else None,
                "lambda_request_id": context.aws_request_id if context else None
            })
            
            # Legacy powertools logging
            logger.info("Starting Lambda cost reporting execution", extra={
                "event": event,
                "remaining_time_ms": context.get_remaining_time_in_millis() if context else None
            })
            
            # Add custom metrics
            metrics.add_metric(name="ExecutionStarted", unit=MetricUnit.Count, value=1)
            
            self.structured_logger.info("Execution parameters determined", extra={
                "execution_type": execution_type,
                "report_type": report_type
            })
            
            # Process based on execution type
            if execution_type == "scheduled":
                # Use scheduler to process EventBridge events
                schedule_result = self.scheduler.process_eventbridge_event(event)
                
                if schedule_result['action'] == 'skip':
                    logger.info(f"Skipping execution: {schedule_result['reason']}")
                    result = {
                        'message': f"Execution skipped: {schedule_result['reason']}",
                        'schedule_info': schedule_result.get('schedule_info', {})
                    }
                else:
                    result = self.process_scheduled_reports(report_type, context, schedule_result)
            elif execution_type == "manual":
                client_id = event.get('client_id')
                if client_id:
                    result = self.process_single_client(client_id, report_type, context)
                else:
                    result = self.process_scheduled_reports(report_type, context)
            else:
                raise ValueError(f"Unknown execution type: {execution_type}")
            
            # End monitoring with success
            final_metrics = self.monitoring.end_execution(success=True)
            
            # Add success metrics (legacy powertools)
            metrics.add_metric(name="ExecutionSucceeded", unit=MetricUnit.Count, value=1)
            metrics.add_metric(name="ClientsProcessed", unit=MetricUnit.Count, 
                             value=self.execution_stats['clients_processed'])
            metrics.add_metric(name="ReportsGenerated", unit=MetricUnit.Count, 
                             value=self.execution_stats['reports_generated'])
            metrics.add_metric(name="EmailsSent", unit=MetricUnit.Count, 
                             value=self.execution_stats['emails_sent'])
            
            # Structured logging for completion
            self.structured_logger.info("Lambda execution completed successfully", extra={
                "execution_stats": self.execution_stats,
                "final_metrics": {
                    "duration_seconds": final_metrics.duration_seconds,
                    "clients_processed": final_metrics.clients_processed,
                    "success_rate": (final_metrics.clients_succeeded / final_metrics.clients_processed * 100) 
                                  if final_metrics.clients_processed > 0 else 100
                },
                "result_summary": {
                    "status": "success",
                    "clients_processed": len(result.get('results', [])) if isinstance(result, dict) else 0
                }
            })
            
            # Legacy logging
            logger.info("Lambda execution completed successfully", extra={
                "execution_stats": self.execution_stats,
                "result": result
            })
            
            return {
                'statusCode': 200,
                'body': json.dumps(result),
                'execution_stats': self.execution_stats
            }
            
        except Exception as e:
            # Record error with monitoring service
            self.monitoring.record_error(
                error=e,
                component="lambda_handler",
                context={
                    "event_source": event.get('source'),
                    "execution_type": execution_type if 'execution_type' in locals() else 'unknown',
                    "report_type": report_type if 'report_type' in locals() else 'unknown',
                    "remaining_time_ms": context.get_remaining_time_in_millis() if context else None,
                    "lambda_request_id": context.aws_request_id if context else None
                },
                severity=AlertSeverity.CRITICAL
            )
            
            # End monitoring with failure
            self.monitoring.end_execution(success=False)
            
            # Handle error using error handler (legacy)
            handling_result = handle_component_error(e, "lambda_handler", context={
                "event": event,
                "remaining_time_ms": context.get_remaining_time_in_millis() if context else None
            })
            
            error_msg = f"Lambda execution failed: {str(e)}"
            
            # Structured error logging
            self.structured_logger.error("Lambda execution failed", extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "event_source": event.get('source'),
                "lambda_request_id": context.aws_request_id if context else None,
                "execution_stats": self.execution_stats
            }, exc_info=True)
            
            # Legacy error logging
            logger.error(error_msg, extra={
                "error": str(e),
                "traceback": traceback.format_exc(),
                "event": event,
                "error_handling": handling_result
            })
            
            # Add failure metrics
            metrics.add_metric(name="ExecutionFailed", unit=MetricUnit.Count, value=1)
            
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': error_msg,
                    'execution_stats': self.execution_stats,
                    'error_handling': handling_result
                })
            }
    
    def process_scheduled_reports(self, report_type: str, context=None, schedule_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process scheduled reports for all active clients.
        
        Args:
            report_type: Type of report (weekly/monthly)
            context: Lambda context for timeout monitoring
            schedule_result: Optional schedule result from scheduler
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Processing scheduled {report_type} reports")
            
            # Use scheduler result if available, otherwise fall back to legacy method
            if schedule_result and schedule_result.get('execution_plan'):
                execution_plan = schedule_result['execution_plan']
                client_ids = [client['client_id'] for client in execution_plan['clients']]
                
                # Get client configurations
                eligible_clients = []
                for client_id in client_ids:
                    try:
                        client_config = self.config_manager.get_client_config(client_id)
                        eligible_clients.append(client_config)
                    except Exception as e:
                        logger.error(f"Failed to get config for client {client_id}: {str(e)}")
                        continue
            else:
                # Legacy method - get all active clients and filter
                active_clients = self.config_manager.get_all_active_clients()
                
                if not active_clients:
                    logger.warning("No active clients found")
                    return {
                        'message': 'No active clients found',
                        'clients_processed': 0
                    }
                
                # Filter clients based on report type configuration
                eligible_clients = self._filter_clients_for_report_type(active_clients, report_type)
            
            logger.info(f"Found {len(eligible_clients)} eligible clients for {report_type} reports")
            
            results = []
            
            # Process each client
            for client_config in eligible_clients:
                # Check remaining time
                if context and context.get_remaining_time_in_millis() < 60000:  # 1 minute buffer
                    logger.warning("Approaching timeout, stopping client processing")
                    break
                
                # Mark execution as started in scheduler if we have execution plan
                tracker_key = None
                if schedule_result and schedule_result.get('execution_plan'):
                    execution_plan = schedule_result['execution_plan']
                    scheduled_time = datetime.fromisoformat(execution_plan['scheduled_time'])
                    tracker_key = f"{client_config.client_id}_{report_type}_{scheduled_time.strftime('%Y%m%d_%H')}"
                    self.scheduler.start_execution(tracker_key)
                
                try:
                    result = self.process_single_client(
                        client_config.client_id, 
                        report_type, 
                        context,
                        client_config=client_config
                    )
                    results.append(result)
                    
                    # Mark execution as completed
                    if tracker_key:
                        self.scheduler.complete_execution(tracker_key, True)
                    
                except Exception as e:
                    # Handle error using error handler
                    handling_result = handle_component_error(e, "scheduled_reports", client_config.client_id, {
                        "report_type": report_type,
                        "client_name": client_config.client_name
                    })
                    
                    error_msg = f"Failed to process client {client_config.client_id}: {str(e)}"
                    logger.error(error_msg, extra={"error_handling": handling_result})
                    self.execution_stats['errors'].append(error_msg)
                    self.execution_stats['clients_failed'] += 1
                    
                    # Mark execution as failed
                    if tracker_key:
                        self.scheduler.complete_execution(tracker_key, False, error_msg)
                    
                    results.append({
                        'client_id': client_config.client_id,
                        'status': 'failed',
                        'error': error_msg,
                        'error_handling': handling_result
                    })
            
            return {
                'message': f'Processed {len(results)} clients for {report_type} reports',
                'clients_processed': len(results),
                'results': results,
                'execution_stats': self.execution_stats
            }
            
        except Exception as e:
            error_msg = f"Failed to process scheduled reports: {str(e)}"
            logger.error(error_msg)
            raise
    
    def process_single_client(self, client_id: str, report_type: str, context=None, 
                            client_config: Optional[ClientConfig] = None) -> Dict[str, Any]:
        """
        Process cost report for a single client.
        
        Args:
            client_id: Client identifier
            report_type: Type of report (weekly/monthly)
            context: Lambda context for timeout monitoring
            client_config: Pre-loaded client configuration (optional)
            
        Returns:
            Dictionary with processing results
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Processing {report_type} report for client {client_id}")
            self.execution_stats['clients_processed'] += 1
            
            # Get client configuration if not provided
            if not client_config:
                client_config = self.config_manager.get_client_config(client_id)
            
            # Validate client is active and report type is enabled
            if not client_config.is_active():
                raise ValueError(f"Client {client_id} is not active")
            
            if not self._is_report_type_enabled(client_config, report_type):
                logger.info(f"Report type {report_type} is disabled for client {client_id}")
                return {
                    'client_id': client_id,
                    'status': 'skipped',
                    'message': f'{report_type} reports are disabled'
                }
            
            # Step 1: Collect cost data with retry logic
            logger.info(f"Collecting cost data for client {client_id}")
            
            def collect_cost_data():
                cost_agent = LambdaCostAgent(client_config)
                # Determine number of periods based on report type
                periods = 2 if report_type == 'monthly' else 4 if report_type == 'weekly' else 7
                return cost_agent.collect_client_costs(report_type, periods)
            
            client_cost_data = retry_operation(
                collect_cost_data,
                "cost_collection",
                max_attempts=2,
                base_delay=2.0,
                context={"client_id": client_id, "report_type": report_type}
            )
            
            if client_cost_data.account_count == 0:
                raise ValueError(f"No cost data collected for client {client_id}")
            
            # Step 2: Aggregate and analyze data
            logger.info(f"Aggregating cost data for client {client_id}")
            aggregated_data = cost_agent.aggregate_multi_account_data(client_cost_data)
            
            # Step 2.5: Evaluate cost thresholds and alerts
            logger.info(f"Evaluating cost thresholds for client {client_id}")
            alert_results = None
            try:
                # Determine report period for threshold evaluation
                report_period_start, report_period_end = self._get_report_period(report_type)
                
                alert_results = self.alert_service.evaluate_client_alerts(
                    client_config,
                    aggregated_data,
                    report_period_start,
                    report_period_end
                )
                
                if alert_results and alert_results.has_any_alerts():
                    logger.warning(
                        f"Client {client_id} has {alert_results.triggered_alerts_count} "
                        f"threshold alerts (Critical: {alert_results.has_critical_alerts()})"
                    )
                    self.execution_stats.setdefault('alerts_triggered', 0)
                    self.execution_stats['alerts_triggered'] += alert_results.triggered_alerts_count
                
            except Exception as e:
                logger.error(f"Error evaluating thresholds for client {client_id}: {str(e)}")
                # Don't fail the entire process for threshold evaluation errors
            
            # Step 3: Generate report with retry logic
            logger.info(f"Generating report for client {client_id}")
            
            # Prepare report data with analysis
            report_data = self._prepare_report_data(aggregated_data, report_type)
            
            # Generate HTML report with retry (including alerts)
            def generate_report():
                return self.report_generator.generate_client_report(report_data, client_config, alert_results)
            
            report_s3_url = retry_operation(
                generate_report,
                "report_generation",
                max_attempts=2,
                base_delay=1.0,
                context={"client_id": client_id, "report_type": report_type}
            )
            
            self.execution_stats['reports_generated'] += 1
            
            # Step 4: Send email with retry logic
            logger.info(f"Sending email report for client {client_id}")
            
            def send_email():
                return self.email_service.send_client_report(
                    {'cost_data': report_data}, client_config, alert_results
                )
            
            try:
                email_success = retry_operation(
                    send_email,
                    "email_delivery",
                    max_attempts=3,
                    base_delay=2.0,
                    context={"client_id": client_id, "report_type": report_type}
                )
            except Exception as e:
                # Email failure shouldn't fail the entire process
                handling_result = handle_component_error(e, "email_delivery", client_id)
                logger.warning(f"Email delivery failed for client {client_id}, continuing: {str(e)}")
                email_success = False
            
            if email_success:
                self.execution_stats['emails_sent'] += 1
            
            # Step 5: Update last execution timestamp
            self.config_manager.update_last_execution(
                client_id, 
                ReportType(report_type),
                start_time
            )
            
            # Clean up resources
            cost_agent.clear_cache()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Get alert summary for result
            alert_summary = self.alert_service.get_alert_summary_for_reporting(alert_results)
            
            result = {
                'client_id': client_id,
                'status': 'success',
                'report_type': report_type,
                'total_cost': client_cost_data.total_cost,
                'accounts_processed': client_cost_data.account_count,
                'services_analyzed': client_cost_data.service_count,
                'report_url': report_s3_url,
                'email_sent': email_success,
                'execution_time_seconds': execution_time,
                'errors': client_cost_data.errors,
                'alerts': alert_summary
            }
            
            self.execution_stats['clients_succeeded'] += 1
            
            logger.info(f"Successfully processed client {client_id}", extra=result)
            
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Handle error using error handler
            handling_result = handle_component_error(e, "single_client_processing", client_id, {
                "report_type": report_type,
                "execution_time_seconds": execution_time,
                "client_name": client_config.client_name if client_config else None
            })
            
            error_msg = f"Failed to process client {client_id}: {str(e)}"
            
            logger.error(error_msg, extra={
                "client_id": client_id,
                "report_type": report_type,
                "execution_time_seconds": execution_time,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "error_handling": handling_result
            })
            
            self.execution_stats['clients_failed'] += 1
            self.execution_stats['errors'].append(error_msg)
            
            return {
                'client_id': client_id,
                'status': 'failed',
                'report_type': report_type,
                'error': error_msg,
                'execution_time_seconds': execution_time,
                'error_handling': handling_result
            }
    
    def _determine_execution_type(self, event: Dict[str, Any]) -> str:
        """Determine if this is a scheduled or manual execution."""
        # EventBridge scheduled events
        if event.get('source') == 'aws.events':
            return 'scheduled'
        
        # Manual invocation
        if 'client_id' in event or 'report_type' in event:
            return 'manual'
        
        # Default to scheduled
        return 'scheduled'
    
    def _get_report_type(self, event: Dict[str, Any]) -> str:
        """Extract report type from event."""
        # Direct specification
        if 'report_type' in event:
            return event['report_type']
        
        # EventBridge rule name pattern
        if event.get('source') == 'aws.events':
            detail_type = event.get('detail-type', '')
            if 'weekly' in detail_type.lower():
                return 'weekly'
            elif 'monthly' in detail_type.lower():
                return 'monthly'
        
        # Default to monthly
        return 'monthly'
    
    def _filter_clients_for_report_type(self, clients: List[ClientConfig], 
                                      report_type: str) -> List[ClientConfig]:
        """Filter clients based on report type configuration."""
        eligible_clients = []
        
        for client in clients:
            if self._is_report_type_enabled(client, report_type):
                eligible_clients.append(client)
        
        return eligible_clients
    
    def _is_report_type_enabled(self, client_config: ClientConfig, report_type: str) -> bool:
        """Check if report type is enabled for client."""
        if report_type == 'weekly':
            return client_config.report_config.weekly_enabled
        elif report_type == 'monthly':
            return client_config.report_config.monthly_enabled
        else:
            return False
    
    def _get_report_period(self, report_type: str) -> tuple:
        """
        Get the start and end dates for the current reporting period.
        
        Args:
            report_type: Type of report (weekly/monthly)
            
        Returns:
            Tuple of (start_date, end_date) as datetime objects
        """
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        
        if report_type == 'weekly':
            # Current week (Monday to Sunday)
            days_since_monday = now.weekday()
            start_date = now - timedelta(days=days_since_monday)
            end_date = start_date + timedelta(days=6)
        elif report_type == 'monthly':
            # Current month
            start_date = now.replace(day=1)
            # Get last day of current month
            if now.month == 12:
                end_date = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = now.replace(month=now.month + 1, day=1) - timedelta(days=1)
        else:
            # Default to current month
            start_date = now.replace(day=1)
            if now.month == 12:
                end_date = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = now.replace(month=now.month + 1, day=1) - timedelta(days=1)
        
        # Set time to beginning/end of day
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return start_date, end_date
    
    def _prepare_report_data(self, aggregated_data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
        """Prepare report data with analysis and formatting."""
        try:
            # Extract periods data
            periods_data = aggregated_data.get('periods_data', [])
            
            if len(periods_data) < 2:
                logger.warning("Insufficient periods data for comparison analysis")
                # Create minimal report data
                return {
                    'periods_data': periods_data,
                    'months_data': periods_data,  # For backward compatibility
                    'services': aggregated_data.get('services', {}),
                    'total_cost': aggregated_data.get('total_cost', 0),
                    'changes': {
                        'current_period': periods_data[0] if periods_data else {'total_cost': 0},
                        'previous_period': {'total_cost': 0},
                        'total_change': 0,
                        'total_percent_change': 0,
                        'service_changes': {},
                        'new_services': []
                    },
                    'top_services': self._get_top_services(aggregated_data.get('services', {})),
                    'metadata': aggregated_data.get('metadata', {})
                }
            
            # Analyze changes between periods
            current_period = periods_data[0]
            previous_period = periods_data[1]
            
            changes = self._analyze_period_changes(current_period, previous_period)
            
            # Get top services
            top_services = self._get_top_services(aggregated_data.get('services', {}))
            
            # Prepare final report data
            report_data = {
                'periods_data': periods_data,
                'months_data': periods_data,  # For backward compatibility
                'services': aggregated_data.get('services', {}),
                'total_cost': aggregated_data.get('total_cost', 0),
                'changes': changes,
                'top_services': top_services,
                'accounts_data': aggregated_data.get('accounts_data', []),
                'metadata': aggregated_data.get('metadata', {})
            }
            
            # Add account-level analysis if multiple accounts
            if len(aggregated_data.get('accounts_data', [])) > 1:
                account_changes = self._analyze_account_changes(aggregated_data.get('accounts_data', []))
                report_data['account_changes'] = account_changes
                report_data['top_accounts'] = self._get_top_accounts(aggregated_data.get('accounts_data', []))
            
            return report_data
            
        except Exception as e:
            # Handle error using error handler
            handling_result = handle_component_error(e, "report_data_preparation", context={
                "report_type": report_type,
                "periods_count": len(aggregated_data.get('periods_data', []))
            })
            
            logger.error(f"Error preparing report data: {str(e)}", extra={"error_handling": handling_result})
            # Return minimal data structure to prevent complete failure
            return {
                'periods_data': aggregated_data.get('periods_data', []),
                'months_data': aggregated_data.get('periods_data', []),
                'services': aggregated_data.get('services', {}),
                'total_cost': aggregated_data.get('total_cost', 0),
                'changes': {
                    'current_period': {'total_cost': aggregated_data.get('total_cost', 0)},
                    'previous_period': {'total_cost': 0},
                    'total_change': 0,
                    'total_percent_change': 0,
                    'service_changes': {},
                    'new_services': []
                },
                'top_services': [],
                'metadata': aggregated_data.get('metadata', {})
            }
    
    def _analyze_period_changes(self, current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze changes between two periods."""
        current_cost = current.get('total_cost', 0)
        previous_cost = previous.get('total_cost', 0)
        
        total_change = current_cost - previous_cost
        total_percent_change = (total_change / previous_cost * 100) if previous_cost > 0 else 0
        
        # Analyze service-level changes
        current_services = current.get('services', {})
        previous_services = previous.get('services', {})
        
        service_changes = {}
        new_services = []
        
        # Check all current services
        for service, current_service_cost in current_services.items():
            if service in previous_services:
                previous_service_cost = previous_services[service]
                change = current_service_cost - previous_service_cost
                percent_change = (change / previous_service_cost * 100) if previous_service_cost > 0 else 0
                
                if abs(percent_change) > 1:  # Only include significant changes
                    service_changes[service] = {
                        'current': current_service_cost,
                        'previous': previous_service_cost,
                        'change': change,
                        'percent_change': percent_change
                    }
            else:
                # New service
                new_services.append({
                    'service': service,
                    'cost': current_service_cost
                })
        
        # Sort service changes by absolute change amount
        service_changes = dict(sorted(
            service_changes.items(),
            key=lambda x: abs(x[1]['change']),
            reverse=True
        ))
        
        # Sort new services by cost
        new_services = sorted(new_services, key=lambda x: x['cost'], reverse=True)
        
        return {
            'current_period': current,
            'previous_period': previous,
            'total_change': total_change,
            'total_percent_change': total_percent_change,
            'service_changes': service_changes,
            'new_services': new_services
        }
    
    def _get_top_services(self, services: Dict[str, float], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top services by cost."""
        if not services:
            return []
        
        total_cost = sum(services.values())
        
        top_services = []
        for service, cost in sorted(services.items(), key=lambda x: x[1], reverse=True)[:limit]:
            percentage = (cost / total_cost * 100) if total_cost > 0 else 0
            top_services.append({
                'service': service,
                'cost': cost,
                'percentage': percentage
            })
        
        return top_services
    
    def _analyze_account_changes(self, accounts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze changes between accounts across periods."""
        if len(accounts_data) < 2:
            return {'account_changes': {}, 'new_accounts': []}
        
        # Get current and previous period data for each account
        account_changes = {}
        new_accounts = []
        
        # Build account cost maps for each period
        current_accounts = {}
        previous_accounts = {}
        
        for account_data in accounts_data:
            account_id = account_data.get('account_id')
            periods_data = account_data.get('cost_data', {}).get('periods_data', [])
            
            if len(periods_data) >= 1:
                current_accounts[account_id] = periods_data[0].get('total_cost', 0)
            
            if len(periods_data) >= 2:
                previous_accounts[account_id] = periods_data[1].get('total_cost', 0)
        
        # Analyze changes
        for account_id, current_cost in current_accounts.items():
            if account_id in previous_accounts:
                previous_cost = previous_accounts[account_id]
                change = current_cost - previous_cost
                percent_change = (change / previous_cost * 100) if previous_cost > 0 else 0
                
                if abs(percent_change) > 1:  # Only include significant changes
                    account_changes[account_id] = {
                        'current': current_cost,
                        'previous': previous_cost,
                        'change': change,
                        'percent_change': percent_change
                    }
            else:
                # New account
                new_accounts.append({
                    'account_id': account_id,
                    'cost': current_cost
                })
        
        # Sort by absolute change amount
        account_changes = dict(sorted(
            account_changes.items(),
            key=lambda x: abs(x[1]['change']),
            reverse=True
        ))
        
        return {
            'account_changes': account_changes,
            'new_accounts': new_accounts
        }
    
    def _get_top_accounts(self, accounts_data: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top accounts by cost."""
        if not accounts_data:
            return []
        
        account_costs = []
        total_cost = 0
        
        for account_data in accounts_data:
            account_id = account_data.get('account_id')
            cost = account_data.get('cost_data', {}).get('total_cost', 0)
            account_costs.append({'account_id': account_id, 'cost': cost})
            total_cost += cost
        
        # Sort by cost and calculate percentages
        top_accounts = []
        for account in sorted(account_costs, key=lambda x: x['cost'], reverse=True)[:limit]:
            percentage = (account['cost'] / total_cost * 100) if total_cost > 0 else 0
            top_accounts.append({
                'account_id': account['account_id'],
                'cost': account['cost'],
                'percentage': percentage
            })
        
        return top_accounts


# Global handler instance
handler = LambdaCostReportHandler()


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda entry point.
    
    Args:
        event: Lambda event data
        context: Lambda context object
        
    Returns:
        Dictionary with execution results
    """
    return handler.lambda_handler(event, context)