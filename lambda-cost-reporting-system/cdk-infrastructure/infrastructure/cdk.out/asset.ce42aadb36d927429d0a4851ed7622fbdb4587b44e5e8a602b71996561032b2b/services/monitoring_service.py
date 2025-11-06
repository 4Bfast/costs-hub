"""
Monitoring Service for Lambda Cost Reporting System

This module provides comprehensive monitoring capabilities including:
- Custom CloudWatch metrics
- Structured logging with correlation IDs
- Performance tracking
- Error categorization and alerting
- Business metrics collection
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import contextmanager

import boto3
from botocore.exceptions import ClientError


class MetricUnit(Enum):
    """CloudWatch metric units"""
    COUNT = "Count"
    SECONDS = "Seconds"
    MILLISECONDS = "Milliseconds"
    PERCENT = "Percent"
    BYTES = "Bytes"
    KILOBYTES = "Kilobytes"
    MEGABYTES = "Megabytes"
    GIGABYTES = "Gigabytes"


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class ExecutionMetrics:
    """Execution metrics data structure"""
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    clients_processed: int = 0
    clients_succeeded: int = 0
    clients_failed: int = 0
    reports_generated: int = 0
    emails_sent: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class MonitoringService:
    """
    Comprehensive monitoring service for Lambda Cost Reporting System.
    
    Provides CloudWatch metrics, structured logging, and alerting capabilities.
    """
    
    def __init__(self, region: str = 'us-east-1', namespace: str = 'CostReporting'):
        """
        Initialize monitoring service.
        
        Args:
            region: AWS region for CloudWatch
            namespace: CloudWatch namespace for custom metrics
        """
        self.region = region
        self.namespace = namespace
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        
        # Current execution context
        self.execution_id = str(uuid.uuid4())
        self.execution_metrics = ExecutionMetrics(
            execution_id=self.execution_id,
            start_time=datetime.now(timezone.utc)
        )
        
        # Logger with correlation ID
        self.logger = self._setup_logger()
        
        # Metrics buffer for batch publishing
        self._metrics_buffer: List[Dict[str, Any]] = []
        self._max_buffer_size = 20  # CloudWatch limit    

    def _setup_logger(self) -> logging.Logger:
        """Setup structured logger with correlation ID"""
        logger = logging.getLogger(f"{__name__}.{self.execution_id}")
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
            
        logger.setLevel(logging.INFO)
        
        # Create formatter with correlation ID
        formatter = logging.Formatter(
            fmt=f'%(asctime)s - %(name)s - %(levelname)s - [EXEC:{self.execution_id}] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
        
        return logger
    
    def start_execution(self, report_type: str = None, client_count: int = 0) -> str:
        """
        Start execution tracking.
        
        Args:
            report_type: Type of report being executed
            client_count: Number of clients to process
            
        Returns:
            Execution ID for correlation
        """
        self.execution_metrics.start_time = datetime.now(timezone.utc)
        
        self.logger.info("Execution started", extra={
            "execution_id": self.execution_id,
            "report_type": report_type,
            "client_count": client_count,
            "timestamp": self.execution_metrics.start_time.isoformat()
        })
        
        # Publish execution started metric
        self.put_metric("ExecutionStarted", 1, MetricUnit.COUNT, {
            "ReportType": report_type or "unknown"
        })
        
        return self.execution_id
    
    def end_execution(self, success: bool = True) -> ExecutionMetrics:
        """
        End execution tracking and publish final metrics.
        
        Args:
            success: Whether execution was successful
            
        Returns:
            Final execution metrics
        """
        self.execution_metrics.end_time = datetime.now(timezone.utc)
        self.execution_metrics.duration_seconds = (
            self.execution_metrics.end_time - self.execution_metrics.start_time
        ).total_seconds()
        
        # Log execution summary
        self.logger.info("Execution completed", extra={
            "execution_id": self.execution_id,
            "success": success,
            "duration_seconds": self.execution_metrics.duration_seconds,
            "clients_processed": self.execution_metrics.clients_processed,
            "clients_succeeded": self.execution_metrics.clients_succeeded,
            "clients_failed": self.execution_metrics.clients_failed,
            "reports_generated": self.execution_metrics.reports_generated,
            "emails_sent": self.execution_metrics.emails_sent,
            "error_count": len(self.execution_metrics.errors)
        })
        
        # Publish final metrics
        if success:
            self.put_metric("ExecutionSucceeded", 1, MetricUnit.COUNT)
        else:
            self.put_metric("ExecutionFailed", 1, MetricUnit.COUNT)
        
        self.put_metric("ExecutionDuration", self.execution_metrics.duration_seconds, MetricUnit.SECONDS)
        self.put_metric("ClientsProcessed", self.execution_metrics.clients_processed, MetricUnit.COUNT)
        self.put_metric("ClientsSucceeded", self.execution_metrics.clients_succeeded, MetricUnit.COUNT)
        self.put_metric("ClientsFailed", self.execution_metrics.clients_failed, MetricUnit.COUNT)
        self.put_metric("ReportsGenerated", self.execution_metrics.reports_generated, MetricUnit.COUNT)
        self.put_metric("EmailsSent", self.execution_metrics.emails_sent, MetricUnit.COUNT)
        
        # Calculate success rate
        if self.execution_metrics.clients_processed > 0:
            success_rate = (self.execution_metrics.clients_succeeded / 
                          self.execution_metrics.clients_processed) * 100
            self.put_metric("ClientSuccessRate", success_rate, MetricUnit.PERCENT)
        
        # Flush remaining metrics
        self.flush_metrics()
        
        return self.execution_metrics    
  
  def put_metric(self, metric_name: str, value: Union[int, float], 
                   unit: MetricUnit, dimensions: Dict[str, str] = None) -> None:
        """
        Add metric to buffer for batch publishing.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit
            dimensions: Optional dimensions for the metric
        """
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit.value,
            'Timestamp': datetime.now(timezone.utc)
        }
        
        if dimensions:
            metric_data['Dimensions'] = [
                {'Name': k, 'Value': v} for k, v in dimensions.items()
            ]
        
        self._metrics_buffer.append(metric_data)
        
        # Auto-flush if buffer is full
        if len(self._metrics_buffer) >= self._max_buffer_size:
            self.flush_metrics()
    
    def flush_metrics(self) -> None:
        """Flush metrics buffer to CloudWatch"""
        if not self._metrics_buffer:
            return
        
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=self._metrics_buffer
            )
            
            self.logger.debug(f"Published {len(self._metrics_buffer)} metrics to CloudWatch")
            self._metrics_buffer.clear()
            
        except ClientError as e:
            self.logger.error(f"Failed to publish metrics to CloudWatch: {e}")
    
    def record_client_processing(self, client_id: str, success: bool, 
                               duration_seconds: float, error: str = None) -> None:
        """
        Record client processing metrics.
        
        Args:
            client_id: Client identifier
            success: Whether processing was successful
            duration_seconds: Processing duration
            error: Error message if failed
        """
        self.execution_metrics.clients_processed += 1
        
        if success:
            self.execution_metrics.clients_succeeded += 1
            self.logger.info(f"Client {client_id} processed successfully", extra={
                "client_id": client_id,
                "duration_seconds": duration_seconds,
                "execution_id": self.execution_id
            })
        else:
            self.execution_metrics.clients_failed += 1
            if error:
                self.execution_metrics.errors.append(f"Client {client_id}: {error}")
            
            self.logger.error(f"Client {client_id} processing failed", extra={
                "client_id": client_id,
                "duration_seconds": duration_seconds,
                "error": error,
                "execution_id": self.execution_id
            })
        
        # Publish client-level metrics
        self.put_metric("ClientProcessingDuration", duration_seconds, MetricUnit.SECONDS, {
            "ClientId": client_id,
            "Success": str(success)
        })
    
    def record_report_generation(self, client_id: str, success: bool, 
                               report_type: str, duration_seconds: float) -> None:
        """
        Record report generation metrics.
        
        Args:
            client_id: Client identifier
            success: Whether generation was successful
            report_type: Type of report generated
            duration_seconds: Generation duration
        """
        if success:
            self.execution_metrics.reports_generated += 1
            
        self.logger.info(f"Report generation for client {client_id}", extra={
            "client_id": client_id,
            "report_type": report_type,
            "success": success,
            "duration_seconds": duration_seconds,
            "execution_id": self.execution_id
        })
        
        self.put_metric("ReportGenerationDuration", duration_seconds, MetricUnit.SECONDS, {
            "ClientId": client_id,
            "ReportType": report_type,
            "Success": str(success)
        })
    
    def record_email_delivery(self, client_id: str, success: bool, 
                            recipient_count: int, duration_seconds: float) -> None:
        """
        Record email delivery metrics.
        
        Args:
            client_id: Client identifier
            success: Whether delivery was successful
            recipient_count: Number of recipients
            duration_seconds: Delivery duration
        """
        if success:
            self.execution_metrics.emails_sent += 1
            
        self.logger.info(f"Email delivery for client {client_id}", extra={
            "client_id": client_id,
            "success": success,
            "recipient_count": recipient_count,
            "duration_seconds": duration_seconds,
            "execution_id": self.execution_id
        })
        
        self.put_metric("EmailDeliveryDuration", duration_seconds, MetricUnit.SECONDS, {
            "ClientId": client_id,
            "Success": str(success)
        })
        
        if success:
            self.put_metric("EmailRecipients", recipient_count, MetricUnit.COUNT, {
                "ClientId": client_id
            })  
  
    def record_error(self, error: Exception, component: str, client_id: str = None, 
                    context: Dict[str, Any] = None, severity: AlertSeverity = AlertSeverity.MEDIUM) -> None:
        """
        Record error with categorization and alerting.
        
        Args:
            error: Exception that occurred
            component: Component where error occurred
            client_id: Optional client identifier
            context: Additional context information
            severity: Error severity level
        """
        error_msg = str(error)
        error_type = type(error).__name__
        
        # Add to execution metrics
        full_error_msg = f"{component}: {error_msg}"
        if client_id:
            full_error_msg = f"Client {client_id} - {full_error_msg}"
        
        self.execution_metrics.errors.append(full_error_msg)
        
        # Log structured error
        log_extra = {
            "error_type": error_type,
            "error_message": error_msg,
            "component": component,
            "severity": severity.value,
            "execution_id": self.execution_id
        }
        
        if client_id:
            log_extra["client_id"] = client_id
        
        if context:
            log_extra["context"] = context
        
        self.logger.error(f"Error in {component}: {error_msg}", extra=log_extra)
        
        # Publish error metrics
        dimensions = {
            "Component": component,
            "ErrorType": error_type,
            "Severity": severity.value
        }
        
        if client_id:
            dimensions["ClientId"] = client_id
        
        self.put_metric("ComponentError", 1, MetricUnit.COUNT, dimensions)
        
        # Send alert for high/critical severity errors
        if severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            self._send_alert(error_msg, component, client_id, severity, context)
    
    def _send_alert(self, error_msg: str, component: str, client_id: str = None,
                   severity: AlertSeverity = AlertSeverity.MEDIUM, 
                   context: Dict[str, Any] = None) -> None:
        """
        Send alert notification via SNS.
        
        Args:
            error_msg: Error message
            component: Component where error occurred
            client_id: Optional client identifier
            severity: Error severity
            context: Additional context
        """
        try:
            import os
            sns_topic_arn = os.environ.get('SNS_ALERT_TOPIC_ARN')
            
            if not sns_topic_arn:
                self.logger.warning("SNS_ALERT_TOPIC_ARN not configured, skipping alert")
                return
            
            # Prepare alert message
            alert_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_id": self.execution_id,
                "severity": severity.value,
                "component": component,
                "error_message": error_msg,
                "client_id": client_id,
                "context": context or {}
            }
            
            subject = f"[{severity.value}] Cost Reporting Alert - {component}"
            if client_id:
                subject += f" (Client: {client_id})"
            
            message = json.dumps(alert_data, indent=2, default=str)
            
            self.sns.publish(
                TopicArn=sns_topic_arn,
                Subject=subject,
                Message=message
            )
            
            self.logger.info(f"Alert sent for {severity.value} error in {component}")
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
    
    @contextmanager
    def track_operation(self, operation_name: str, client_id: str = None):
        """
        Context manager to track operation duration and success.
        
        Args:
            operation_name: Name of the operation
            client_id: Optional client identifier
            
        Yields:
            Operation tracker context
        """
        start_time = time.time()
        
        log_extra = {
            "operation": operation_name,
            "execution_id": self.execution_id
        }
        if client_id:
            log_extra["client_id"] = client_id
        
        self.logger.info(f"Starting {operation_name}", extra=log_extra)
        
        try:
            yield
            
            duration = time.time() - start_time
            self.logger.info(f"Completed {operation_name} in {duration:.2f}s", 
                           extra={**log_extra, "duration_seconds": duration})
            
            # Record success metric
            dimensions = {"Operation": operation_name}
            if client_id:
                dimensions["ClientId"] = client_id
            
            self.put_metric("OperationDuration", duration, MetricUnit.SECONDS, dimensions)
            self.put_metric("OperationSuccess", 1, MetricUnit.COUNT, dimensions)
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Failed {operation_name} after {duration:.2f}s: {e}", 
                            extra={**log_extra, "duration_seconds": duration, "error": str(e)})
            
            # Record failure metric
            dimensions = {"Operation": operation_name}
            if client_id:
                dimensions["ClientId"] = client_id
            
            self.put_metric("OperationDuration", duration, MetricUnit.SECONDS, dimensions)
            self.put_metric("OperationFailure", 1, MetricUnit.COUNT, dimensions)
            
            raise
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get current execution summary"""
        return {
            "execution_id": self.execution_id,
            "metrics": asdict(self.execution_metrics),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }