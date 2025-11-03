"""
Scheduling Logic for Lambda Cost Reporting System

This module handles EventBridge rule processing, client-specific scheduling,
execution tracking, and duplicate prevention for the cost reporting system.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from ..models import ClientConfig, ReportType, ClientStatus
from ..services import ClientConfigManager
from ..utils import create_logger


logger = create_logger(__name__)


class ScheduleFrequency(Enum):
    """Schedule frequency enumeration."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    DAILY = "daily"  # For testing purposes


@dataclass
class ExecutionTracker:
    """Tracks execution state to prevent duplicates."""
    client_id: str
    report_type: str
    scheduled_time: datetime
    execution_id: str
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class SchedulingManager:
    """
    Manages scheduling logic for cost reporting system.
    
    Handles EventBridge rule processing, client-specific scheduling configuration,
    execution tracking, and duplicate prevention.
    """
    
    def __init__(self, config_manager: ClientConfigManager):
        """
        Initialize the scheduling manager.
        
        Args:
            config_manager: Client configuration manager instance
        """
        self.config_manager = config_manager
        self.execution_trackers: Dict[str, ExecutionTracker] = {}
        self.logger = create_logger(f"{__name__}.SchedulingManager")
    
    def process_eventbridge_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process EventBridge scheduled event.
        
        Args:
            event: EventBridge event data
            
        Returns:
            Dictionary with processing instructions
        """
        try:
            self.logger.info("Processing EventBridge scheduled event", extra={"event": event})
            
            # Extract schedule information from event
            schedule_info = self._parse_eventbridge_event(event)
            
            if not schedule_info:
                raise ValueError("Unable to parse EventBridge event")
            
            # Get eligible clients for this schedule
            eligible_clients = self._get_eligible_clients(
                schedule_info['report_type'],
                schedule_info['scheduled_time']
            )
            
            if not eligible_clients:
                self.logger.info(f"No eligible clients found for {schedule_info['report_type']} reports")
                return {
                    'action': 'skip',
                    'reason': 'No eligible clients',
                    'schedule_info': schedule_info
                }
            
            # Check for duplicate executions
            filtered_clients = self._filter_duplicate_executions(
                eligible_clients,
                schedule_info['report_type'],
                schedule_info['scheduled_time']
            )
            
            if not filtered_clients:
                self.logger.info("All eligible clients have recent executions, skipping")
                return {
                    'action': 'skip',
                    'reason': 'All clients have recent executions',
                    'schedule_info': schedule_info
                }
            
            # Create execution plan
            execution_plan = self._create_execution_plan(
                filtered_clients,
                schedule_info
            )
            
            self.logger.info(f"Created execution plan for {len(filtered_clients)} clients")
            
            return {
                'action': 'execute',
                'execution_plan': execution_plan,
                'schedule_info': schedule_info,
                'clients_count': len(filtered_clients)
            }
            
        except Exception as e:
            error_msg = f"Error processing EventBridge event: {str(e)}"
            self.logger.error(error_msg, extra={"event": event, "error": str(e)})
            raise
    
    def _parse_eventbridge_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse EventBridge event to extract schedule information."""
        try:
            # Standard EventBridge scheduled event structure
            if event.get('source') == 'aws.events':
                detail_type = event.get('detail-type', '')
                scheduled_time = datetime.fromisoformat(event.get('time', '').replace('Z', '+00:00'))
                
                # Determine report type from detail-type or rule name
                report_type = 'monthly'  # default
                
                if 'weekly' in detail_type.lower():
                    report_type = 'weekly'
                elif 'monthly' in detail_type.lower():
                    report_type = 'monthly'
                elif 'daily' in detail_type.lower():
                    report_type = 'daily'
                
                # Extract additional details
                detail = event.get('detail', {})
                rule_name = event.get('resources', [None])[0]
                if rule_name:
                    rule_name = rule_name.split('/')[-1]  # Extract rule name from ARN
                
                return {
                    'report_type': report_type,
                    'scheduled_time': scheduled_time,
                    'detail_type': detail_type,
                    'rule_name': rule_name,
                    'detail': detail
                }
            
            # Manual trigger with schedule info
            elif 'schedule' in event:
                schedule = event['schedule']
                return {
                    'report_type': schedule.get('report_type', 'monthly'),
                    'scheduled_time': datetime.fromisoformat(schedule.get('scheduled_time', datetime.utcnow().isoformat())),
                    'detail_type': 'manual',
                    'rule_name': 'manual',
                    'detail': schedule
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing EventBridge event: {str(e)}")
            return None
    
    def _get_eligible_clients(self, report_type: str, scheduled_time: datetime) -> List[ClientConfig]:
        """
        Get clients eligible for the specified report type and schedule.
        
        Args:
            report_type: Type of report (weekly/monthly)
            scheduled_time: Scheduled execution time
            
        Returns:
            List of eligible client configurations
        """
        try:
            # Get all active clients
            all_clients = self.config_manager.get_all_active_clients()
            
            eligible_clients = []
            
            for client in all_clients:
                if self._is_client_eligible(client, report_type, scheduled_time):
                    eligible_clients.append(client)
            
            self.logger.info(f"Found {len(eligible_clients)} eligible clients out of {len(all_clients)} total")
            
            return eligible_clients
            
        except Exception as e:
            self.logger.error(f"Error getting eligible clients: {str(e)}")
            raise
    
    def _is_client_eligible(self, client: ClientConfig, report_type: str, scheduled_time: datetime) -> bool:
        """
        Check if a client is eligible for the specified report type and schedule.
        
        Args:
            client: Client configuration
            report_type: Type of report
            scheduled_time: Scheduled execution time
            
        Returns:
            True if client is eligible
        """
        try:
            # Check if client is active
            if not client.is_active():
                return False
            
            # Check if report type is enabled
            if report_type == 'weekly' and not client.report_config.weekly_enabled:
                return False
            elif report_type == 'monthly' and not client.report_config.monthly_enabled:
                return False
            
            # Check if client has valid AWS accounts
            if not client.aws_accounts:
                self.logger.warning(f"Client {client.client_id} has no AWS accounts configured")
                return False
            
            # Check if client has recipients configured
            if not client.report_config.recipients:
                self.logger.warning(f"Client {client.client_id} has no email recipients configured")
                return False
            
            # Check last execution time to avoid too frequent executions
            last_execution = client.last_execution.get(report_type)
            if last_execution:
                time_since_last = scheduled_time - last_execution
                
                # Minimum intervals to prevent duplicate executions
                min_intervals = {
                    'daily': timedelta(hours=20),    # Allow daily reports once per day
                    'weekly': timedelta(days=6),     # Allow weekly reports once per week
                    'monthly': timedelta(days=25)    # Allow monthly reports once per month
                }
                
                min_interval = min_intervals.get(report_type, timedelta(days=1))
                
                if time_since_last < min_interval:
                    self.logger.debug(f"Client {client.client_id} executed {report_type} report too recently")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking client eligibility for {client.client_id}: {str(e)}")
            return False
    
    def _filter_duplicate_executions(self, clients: List[ClientConfig], report_type: str, 
                                   scheduled_time: datetime) -> List[ClientConfig]:
        """
        Filter out clients that have duplicate executions in progress or recently completed.
        
        Args:
            clients: List of client configurations
            report_type: Type of report
            scheduled_time: Scheduled execution time
            
        Returns:
            Filtered list of clients
        """
        filtered_clients = []
        
        for client in clients:
            execution_key = f"{client.client_id}_{report_type}_{scheduled_time.strftime('%Y%m%d_%H')}"
            
            # Check if execution is already tracked
            if execution_key in self.execution_trackers:
                tracker = self.execution_trackers[execution_key]
                
                # Skip if execution is running or recently completed
                if tracker.status in ['running', 'completed']:
                    self.logger.debug(f"Skipping duplicate execution for client {client.client_id}")
                    continue
                
                # Reset failed executions after some time
                if tracker.status == 'failed' and tracker.completed_at:
                    time_since_failure = scheduled_time - tracker.completed_at
                    if time_since_failure < timedelta(hours=1):
                        self.logger.debug(f"Skipping recent failed execution for client {client.client_id}")
                        continue
            
            filtered_clients.append(client)
        
        return filtered_clients
    
    def _create_execution_plan(self, clients: List[ClientConfig], 
                             schedule_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create execution plan for the given clients and schedule.
        
        Args:
            clients: List of client configurations
            schedule_info: Schedule information
            
        Returns:
            Execution plan dictionary
        """
        execution_id = f"exec_{schedule_info['scheduled_time'].strftime('%Y%m%d_%H%M%S')}"
        
        # Create execution trackers
        client_executions = []
        
        for client in clients:
            tracker_key = f"{client.client_id}_{schedule_info['report_type']}_{schedule_info['scheduled_time'].strftime('%Y%m%d_%H')}"
            
            tracker = ExecutionTracker(
                client_id=client.client_id,
                report_type=schedule_info['report_type'],
                scheduled_time=schedule_info['scheduled_time'],
                execution_id=execution_id,
                status='pending'
            )
            
            self.execution_trackers[tracker_key] = tracker
            
            client_executions.append({
                'client_id': client.client_id,
                'client_name': client.client_name,
                'report_type': schedule_info['report_type'],
                'tracker_key': tracker_key
            })
        
        return {
            'execution_id': execution_id,
            'report_type': schedule_info['report_type'],
            'scheduled_time': schedule_info['scheduled_time'].isoformat(),
            'clients': client_executions,
            'total_clients': len(client_executions)
        }
    
    def start_execution(self, tracker_key: str) -> bool:
        """
        Mark execution as started.
        
        Args:
            tracker_key: Execution tracker key
            
        Returns:
            True if successfully started
        """
        try:
            if tracker_key in self.execution_trackers:
                tracker = self.execution_trackers[tracker_key]
                tracker.status = 'running'
                tracker.started_at = datetime.utcnow()
                
                self.logger.info(f"Started execution for client {tracker.client_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error starting execution {tracker_key}: {str(e)}")
            return False
    
    def complete_execution(self, tracker_key: str, success: bool, error_message: Optional[str] = None) -> bool:
        """
        Mark execution as completed.
        
        Args:
            tracker_key: Execution tracker key
            success: Whether execution was successful
            error_message: Error message if execution failed
            
        Returns:
            True if successfully completed
        """
        try:
            if tracker_key in self.execution_trackers:
                tracker = self.execution_trackers[tracker_key]
                tracker.status = 'completed' if success else 'failed'
                tracker.completed_at = datetime.utcnow()
                tracker.error_message = error_message
                
                self.logger.info(f"Completed execution for client {tracker.client_id}: {'success' if success else 'failed'}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error completing execution {tracker_key}: {str(e)}")
            return False
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of all executions for a given execution ID.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Dictionary with execution status
        """
        try:
            matching_trackers = [
                tracker for tracker in self.execution_trackers.values()
                if tracker.execution_id == execution_id
            ]
            
            if not matching_trackers:
                return {'error': 'Execution not found'}
            
            status_summary = {
                'execution_id': execution_id,
                'total_clients': len(matching_trackers),
                'pending': 0,
                'running': 0,
                'completed': 0,
                'failed': 0,
                'clients': []
            }
            
            for tracker in matching_trackers:
                status_summary[tracker.status] += 1
                
                client_status = {
                    'client_id': tracker.client_id,
                    'report_type': tracker.report_type,
                    'status': tracker.status,
                    'scheduled_time': tracker.scheduled_time.isoformat(),
                    'started_at': tracker.started_at.isoformat() if tracker.started_at else None,
                    'completed_at': tracker.completed_at.isoformat() if tracker.completed_at else None,
                    'error_message': tracker.error_message
                }
                
                status_summary['clients'].append(client_status)
            
            return status_summary
            
        except Exception as e:
            self.logger.error(f"Error getting execution status for {execution_id}: {str(e)}")
            return {'error': str(e)}
    
    def cleanup_old_trackers(self, max_age_hours: int = 24) -> int:
        """
        Clean up old execution trackers.
        
        Args:
            max_age_hours: Maximum age of trackers to keep
            
        Returns:
            Number of trackers cleaned up
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            keys_to_remove = []
            
            for key, tracker in self.execution_trackers.items():
                # Remove trackers that are old and completed/failed
                if tracker.status in ['completed', 'failed'] and tracker.completed_at:
                    if tracker.completed_at < cutoff_time:
                        keys_to_remove.append(key)
                # Remove very old pending trackers (likely stale)
                elif tracker.status == 'pending':
                    if tracker.scheduled_time < cutoff_time:
                        keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.execution_trackers[key]
            
            if keys_to_remove:
                self.logger.info(f"Cleaned up {len(keys_to_remove)} old execution trackers")
            
            return len(keys_to_remove)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old trackers: {str(e)}")
            return 0
    
    def get_client_schedule_info(self, client_id: str) -> Dict[str, Any]:
        """
        Get scheduling information for a specific client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dictionary with client schedule information
        """
        try:
            client_config = self.config_manager.get_client_config(client_id)
            
            schedule_info = {
                'client_id': client_id,
                'client_name': client_config.client_name,
                'status': client_config.status.value,
                'weekly_enabled': client_config.report_config.weekly_enabled,
                'monthly_enabled': client_config.report_config.monthly_enabled,
                'last_execution': {
                    'weekly': client_config.last_execution.get('weekly').isoformat() if client_config.last_execution.get('weekly') else None,
                    'monthly': client_config.last_execution.get('monthly').isoformat() if client_config.last_execution.get('monthly') else None
                },
                'recipients_count': len(client_config.report_config.recipients),
                'accounts_count': len(client_config.aws_accounts)
            }
            
            # Add next scheduled execution estimates
            now = datetime.utcnow()
            
            if client_config.report_config.weekly_enabled:
                last_weekly = client_config.last_execution.get('weekly')
                if last_weekly:
                    next_weekly = last_weekly + timedelta(days=7)
                    schedule_info['next_weekly_estimate'] = next_weekly.isoformat()
                else:
                    schedule_info['next_weekly_estimate'] = 'Not scheduled yet'
            
            if client_config.report_config.monthly_enabled:
                last_monthly = client_config.last_execution.get('monthly')
                if last_monthly:
                    # Estimate next month (approximate)
                    next_monthly = last_monthly + timedelta(days=30)
                    schedule_info['next_monthly_estimate'] = next_monthly.isoformat()
                else:
                    schedule_info['next_monthly_estimate'] = 'Not scheduled yet'
            
            return schedule_info
            
        except Exception as e:
            self.logger.error(f"Error getting schedule info for client {client_id}: {str(e)}")
            return {'error': str(e)}
    
    def validate_schedule_configuration(self) -> Dict[str, Any]:
        """
        Validate the overall schedule configuration.
        
        Returns:
            Dictionary with validation results
        """
        try:
            validation_results = {
                'total_clients': 0,
                'active_clients': 0,
                'weekly_enabled': 0,
                'monthly_enabled': 0,
                'clients_without_accounts': 0,
                'clients_without_recipients': 0,
                'issues': []
            }
            
            all_clients = self.config_manager.get_clients_by_status(ClientStatus.ACTIVE)
            validation_results['total_clients'] = len(all_clients)
            
            for client in all_clients:
                validation_results['active_clients'] += 1
                
                if client.report_config.weekly_enabled:
                    validation_results['weekly_enabled'] += 1
                
                if client.report_config.monthly_enabled:
                    validation_results['monthly_enabled'] += 1
                
                # Check for configuration issues
                if not client.aws_accounts:
                    validation_results['clients_without_accounts'] += 1
                    validation_results['issues'].append(f"Client {client.client_id} has no AWS accounts")
                
                if not client.report_config.recipients:
                    validation_results['clients_without_recipients'] += 1
                    validation_results['issues'].append(f"Client {client.client_id} has no email recipients")
            
            # Add summary
            validation_results['summary'] = {
                'healthy_clients': validation_results['active_clients'] - len(validation_results['issues']),
                'clients_with_issues': len(validation_results['issues']),
                'weekly_coverage': f"{validation_results['weekly_enabled']}/{validation_results['active_clients']}",
                'monthly_coverage': f"{validation_results['monthly_enabled']}/{validation_results['active_clients']}"
            }
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Error validating schedule configuration: {str(e)}")
            return {'error': str(e)}


def create_scheduling_manager(table_name: str = None, region: str = None, kms_key_id: str = None) -> SchedulingManager:
    """
    Create a scheduling manager instance.
    
    Args:
        table_name: DynamoDB table name
        region: AWS region
        kms_key_id: KMS key ID for encryption
        
    Returns:
        SchedulingManager instance
    """
    config_manager = ClientConfigManager(
        table_name=table_name or 'cost-reporting-clients',
        region=region or 'us-east-1',
        kms_key_id=kms_key_id
    )
    
    return SchedulingManager(config_manager)