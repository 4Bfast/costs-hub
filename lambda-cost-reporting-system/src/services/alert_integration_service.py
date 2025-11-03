"""
Alert Integration Service

This service integrates the threshold evaluator with the existing cost reporting system,
providing a bridge between cost data collection and alert evaluation.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ..models.config_models import ClientConfig
from ..models.threshold_models import ThresholdEvaluationResult, CostData
from ..utils.cost_data_converter import convert_client_cost_data_to_cost_data, extract_historical_cost_data
from .threshold_evaluator import ThresholdEvaluator
from .lambda_cost_agent import LambdaCostAgent, ClientCostData

logger = logging.getLogger(__name__)


class AlertIntegrationService:
    """
    Service to integrate threshold evaluation with cost reporting workflow.
    
    This service coordinates between the cost agent, threshold evaluator,
    and reporting services to provide comprehensive cost alerting.
    """
    
    def __init__(self):
        """Initialize the alert integration service."""
        self.threshold_evaluator = ThresholdEvaluator()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def evaluate_client_alerts(
        self,
        client_config: ClientConfig,
        client_cost_data: Dict[str, Any],
        report_period_start: Optional[datetime] = None,
        report_period_end: Optional[datetime] = None
    ) -> Optional[ThresholdEvaluationResult]:
        """
        Evaluate alerts for a client based on their cost data.
        
        Args:
            client_config: Client configuration with thresholds
            client_cost_data: Cost data from LambdaCostAgent
            report_period_start: Start of the reporting period
            report_period_end: End of the reporting period
            
        Returns:
            ThresholdEvaluationResult or None if no thresholds configured
        """
        try:
            self.logger.info(f"Evaluating alerts for client {client_config.client_id}")
            
            # Check if client has any thresholds configured
            if not client_config.report_config.alert_thresholds:
                self.logger.info(f"No thresholds configured for client {client_config.client_id}")
                return None
            
            # Convert cost data to CostData format
            current_costs = convert_client_cost_data_to_cost_data(
                client_cost_data,
                period_start=report_period_start,
                period_end=report_period_end
            )
            
            # Extract historical data for comparison
            historical_costs = self._extract_historical_costs(
                client_cost_data,
                report_period_start,
                report_period_end
            )
            
            # Evaluate thresholds
            alert_results = self.threshold_evaluator.evaluate_client_thresholds(
                client_config,
                current_costs,
                historical_costs
            )
            
            self.logger.info(
                f"Alert evaluation complete for client {client_config.client_id}: "
                f"{alert_results.triggered_alerts_count} alerts triggered"
            )
            
            return alert_results
            
        except Exception as e:
            self.logger.error(f"Error evaluating alerts for client {client_config.client_id}: {str(e)}")
            return None
    
    def _extract_historical_costs(
        self,
        client_cost_data: Dict[str, Any],
        current_period_start: Optional[datetime],
        current_period_end: Optional[datetime]
    ) -> Dict[str, CostData]:
        """
        Extract historical cost data for comparison periods.
        
        Args:
            client_cost_data: Cost data from LambdaCostAgent
            current_period_start: Start of current period
            current_period_end: End of current period
            
        Returns:
            Dictionary mapping period names to CostData objects
        """
        historical_costs = {}
        
        try:
            # If we have period information, calculate comparison periods
            if current_period_start and current_period_end:
                period_mappings = self.threshold_evaluator.get_historical_cost_periods(
                    current_period_start,
                    current_period_end
                )
                
                # Extract historical data using the converter utility
                historical_costs = extract_historical_cost_data(
                    client_cost_data,
                    period_mappings
                )
            
            self.logger.debug(f"Extracted {len(historical_costs)} historical cost periods")
            
        except Exception as e:
            self.logger.warning(f"Could not extract historical costs: {str(e)}")
        
        return historical_costs
    
    def get_alert_summary_for_reporting(
        self,
        alert_results: Optional[ThresholdEvaluationResult]
    ) -> Dict[str, Any]:
        """
        Get alert summary formatted for inclusion in reports.
        
        Args:
            alert_results: Threshold evaluation results
            
        Returns:
            Dictionary with alert summary information
        """
        if not alert_results:
            return {
                'has_alerts': False,
                'alert_count': 0,
                'critical_count': 0,
                'summary_text': 'No cost thresholds configured'
            }
        
        try:
            from ..utils.cost_data_converter import format_alert_summary
            return format_alert_summary(alert_results.alerts)
        except ImportError:
            # Fallback implementation
            triggered_alerts = [alert for alert in alert_results.alerts if alert.triggered]
            
            return {
                'has_alerts': len(triggered_alerts) > 0,
                'alert_count': len(triggered_alerts),
                'critical_count': len([a for a in triggered_alerts if a.severity.value == 'critical']),
                'summary_text': f"{len(triggered_alerts)} threshold(s) exceeded" if triggered_alerts else "All thresholds OK"
            }
    
    def should_send_immediate_alert(
        self,
        alert_results: Optional[ThresholdEvaluationResult]
    ) -> bool:
        """
        Determine if immediate alerting is required based on alert severity.
        
        Args:
            alert_results: Threshold evaluation results
            
        Returns:
            True if immediate alert should be sent
        """
        if not alert_results:
            return False
        
        # Send immediate alert for critical alerts
        return alert_results.has_critical_alerts()
    
    def get_alert_context_for_subject(
        self,
        alert_results: Optional[ThresholdEvaluationResult]
    ) -> Dict[str, Any]:
        """
        Get alert context for email subject line generation.
        
        Args:
            alert_results: Threshold evaluation results
            
        Returns:
            Dictionary with alert context for subject generation
        """
        if not alert_results or not alert_results.has_any_alerts():
            return {
                'has_alerts': False,
                'is_critical': False,
                'alert_count': 0
            }
        
        return {
            'has_alerts': True,
            'is_critical': alert_results.has_critical_alerts(),
            'alert_count': alert_results.triggered_alerts_count,
            'severity_summary': self._get_severity_summary(alert_results)
        }
    
    def _get_severity_summary(self, alert_results: ThresholdEvaluationResult) -> str:
        """Get a summary of alert severities."""
        from ..models.threshold_models import AlertSeverity
        
        critical_count = len(alert_results.get_alerts_by_severity(AlertSeverity.CRITICAL))
        high_count = len(alert_results.get_alerts_by_severity(AlertSeverity.HIGH))
        medium_count = len(alert_results.get_alerts_by_severity(AlertSeverity.MEDIUM))
        low_count = len(alert_results.get_alerts_by_severity(AlertSeverity.LOW))
        
        if critical_count > 0:
            return f"{critical_count} critical"
        elif high_count > 0:
            return f"{high_count} high"
        elif medium_count > 0:
            return f"{medium_count} medium"
        else:
            return f"{low_count} low"