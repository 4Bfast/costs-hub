"""
Threshold evaluation engine for cost alerting system.

This module provides the core logic for evaluating cost thresholds
and generating alerts based on current and historical cost data.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP

from ..models.threshold_models import (
    ThresholdConfig,
    ThresholdType,
    AlertSeverity,
    ComparisonPeriod,
    CostData,
    AlertResult,
    ThresholdEvaluationResult
)
from ..models.config_models import ClientConfig

logger = logging.getLogger(__name__)


class ThresholdEvaluator:
    """
    Engine for evaluating cost thresholds and generating alerts.
    
    This class handles the evaluation of different types of cost thresholds
    including absolute amounts, percentage increases, and service/account-specific limits.
    """
    
    def __init__(self):
        """Initialize the threshold evaluator."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def evaluate_client_thresholds(
        self,
        client_config: ClientConfig,
        current_costs: CostData,
        historical_costs: Optional[Dict[str, CostData]] = None
    ) -> ThresholdEvaluationResult:
        """
        Evaluate all thresholds for a client.
        
        Args:
            client_config: Client configuration containing thresholds
            current_costs: Current period cost data
            historical_costs: Historical cost data for comparison (optional)
            
        Returns:
            ThresholdEvaluationResult containing all alert results
        """
        self.logger.info(f"Evaluating thresholds for client {client_config.client_id}")
        
        evaluation_time = datetime.utcnow()
        alerts = []
        
        # Get thresholds from client configuration
        thresholds = client_config.report_config.alert_thresholds
        
        if not thresholds:
            self.logger.info(f"No thresholds configured for client {client_config.client_id}")
            return ThresholdEvaluationResult(
                client_id=client_config.client_id,
                evaluation_time=evaluation_time,
                alerts=[],
                total_thresholds_checked=0
            )
        
        # Evaluate each threshold
        for threshold in thresholds:
            if not threshold.enabled:
                self.logger.debug(f"Skipping disabled threshold: {threshold.name}")
                continue
            
            try:
                alert_result = self._evaluate_single_threshold(
                    threshold, current_costs, historical_costs
                )
                alerts.append(alert_result)
                
                if alert_result.triggered:
                    self.logger.warning(
                        f"Threshold triggered: {threshold.name} - {alert_result.message}"
                    )
                else:
                    self.logger.debug(f"Threshold OK: {threshold.name}")
                    
            except Exception as e:
                self.logger.error(
                    f"Error evaluating threshold {threshold.name}: {str(e)}"
                )
                # Create error alert
                error_alert = AlertResult(
                    threshold_config=threshold,
                    triggered=True,
                    current_value=0.0,
                    threshold_value=threshold.value,
                    severity=AlertSeverity.HIGH,
                    message=f"Error evaluating threshold: {str(e)}",
                    details={"error": str(e)}
                )
                alerts.append(error_alert)
        
        result = ThresholdEvaluationResult(
            client_id=client_config.client_id,
            evaluation_time=evaluation_time,
            alerts=alerts,
            total_thresholds_checked=len([t for t in thresholds if t.enabled])
        )
        
        self.logger.info(
            f"Threshold evaluation complete for client {client_config.client_id}: "
            f"{result.triggered_alerts_count}/{result.total_thresholds_checked} alerts triggered"
        )
        
        return result
    
    def _evaluate_single_threshold(
        self,
        threshold: ThresholdConfig,
        current_costs: CostData,
        historical_costs: Optional[Dict[str, CostData]] = None
    ) -> AlertResult:
        """
        Evaluate a single threshold configuration.
        
        Args:
            threshold: Threshold configuration to evaluate
            current_costs: Current period cost data
            historical_costs: Historical cost data for comparison
            
        Returns:
            AlertResult with evaluation outcome
        """
        self.logger.debug(f"Evaluating threshold: {threshold.name} ({threshold.threshold_type.value})")
        
        if threshold.threshold_type == ThresholdType.ABSOLUTE:
            return self._evaluate_absolute_threshold(threshold, current_costs)
        
        elif threshold.threshold_type == ThresholdType.PERCENTAGE:
            return self._evaluate_percentage_threshold(threshold, current_costs, historical_costs)
        
        elif threshold.threshold_type == ThresholdType.SERVICE_SPECIFIC:
            return self._evaluate_service_threshold(threshold, current_costs)
        
        elif threshold.threshold_type == ThresholdType.ACCOUNT_SPECIFIC:
            return self._evaluate_account_threshold(threshold, current_costs)
        
        else:
            raise ValueError(f"Unsupported threshold type: {threshold.threshold_type}")
    
    def _evaluate_absolute_threshold(
        self,
        threshold: ThresholdConfig,
        current_costs: CostData
    ) -> AlertResult:
        """Evaluate absolute cost threshold."""
        current_value = current_costs.total_cost
        threshold_value = threshold.value
        triggered = current_value > threshold_value
        
        if triggered:
            message = (
                f"Total cost ${current_value:.2f} exceeds absolute threshold "
                f"${threshold_value:.2f}"
            )
        else:
            message = (
                f"Total cost ${current_value:.2f} is within absolute threshold "
                f"${threshold_value:.2f}"
            )
        
        return AlertResult(
            threshold_config=threshold,
            triggered=triggered,
            current_value=current_value,
            threshold_value=threshold_value,
            severity=threshold.severity,
            message=message,
            details={
                "threshold_type": "absolute",
                "total_cost": current_value
            }
        )
    
    def _evaluate_percentage_threshold(
        self,
        threshold: ThresholdConfig,
        current_costs: CostData,
        historical_costs: Optional[Dict[str, CostData]] = None
    ) -> AlertResult:
        """Evaluate percentage increase threshold."""
        if not historical_costs or not threshold.comparison_period:
            return AlertResult(
                threshold_config=threshold,
                triggered=False,
                current_value=0.0,
                threshold_value=threshold.value,
                severity=threshold.severity,
                message="No historical data available for percentage comparison",
                details={"error": "missing_historical_data"}
            )
        
        # Get comparison period data
        comparison_key = threshold.comparison_period.value
        comparison_costs = historical_costs.get(comparison_key)
        
        if not comparison_costs:
            return AlertResult(
                threshold_config=threshold,
                triggered=False,
                current_value=0.0,
                threshold_value=threshold.value,
                severity=threshold.severity,
                message=f"No historical data available for {comparison_key}",
                details={"error": "missing_comparison_data", "period": comparison_key}
            )
        
        current_value = current_costs.total_cost
        comparison_value = comparison_costs.total_cost
        
        if comparison_value == 0:
            # Avoid division by zero
            percentage_change = 0.0 if current_value == 0 else float('inf')
        else:
            percentage_change = ((current_value - comparison_value) / comparison_value) * 100
        
        threshold_value = threshold.value
        triggered = percentage_change > threshold_value
        
        if triggered:
            message = (
                f"Cost increased {percentage_change:.1f}% from {comparison_key} "
                f"(${comparison_value:.2f} → ${current_value:.2f}), "
                f"exceeding threshold of {threshold_value:.1f}%"
            )
        else:
            message = (
                f"Cost change {percentage_change:.1f}% from {comparison_key} "
                f"is within threshold of {threshold_value:.1f}%"
            )
        
        return AlertResult(
            threshold_config=threshold,
            triggered=triggered,
            current_value=percentage_change,
            threshold_value=threshold_value,
            severity=threshold.severity,
            message=message,
            details={
                "threshold_type": "percentage",
                "current_cost": current_value,
                "comparison_cost": comparison_value,
                "percentage_change": percentage_change,
                "comparison_period": comparison_key
            }
        )
    
    def _evaluate_service_threshold(
        self,
        threshold: ThresholdConfig,
        current_costs: CostData
    ) -> AlertResult:
        """Evaluate service-specific threshold."""
        service_name = threshold.service_name
        if not service_name:
            raise ValueError("Service name is required for service-specific threshold")
        
        current_value = current_costs.get_service_cost(service_name)
        threshold_value = threshold.value
        triggered = current_value > threshold_value
        
        if triggered:
            message = (
                f"Service '{service_name}' cost ${current_value:.2f} exceeds "
                f"threshold ${threshold_value:.2f}"
            )
        else:
            message = (
                f"Service '{service_name}' cost ${current_value:.2f} is within "
                f"threshold ${threshold_value:.2f}"
            )
        
        return AlertResult(
            threshold_config=threshold,
            triggered=triggered,
            current_value=current_value,
            threshold_value=threshold_value,
            severity=threshold.severity,
            message=message,
            details={
                "threshold_type": "service_specific",
                "service_name": service_name,
                "service_cost": current_value
            }
        )
    
    def _evaluate_account_threshold(
        self,
        threshold: ThresholdConfig,
        current_costs: CostData
    ) -> AlertResult:
        """Evaluate account-specific threshold."""
        account_id = threshold.account_id
        if not account_id:
            raise ValueError("Account ID is required for account-specific threshold")
        
        current_value = current_costs.get_account_cost(account_id)
        threshold_value = threshold.value
        triggered = current_value > threshold_value
        
        if triggered:
            message = (
                f"Account '{account_id}' cost ${current_value:.2f} exceeds "
                f"threshold ${threshold_value:.2f}"
            )
        else:
            message = (
                f"Account '{account_id}' cost ${current_value:.2f} is within "
                f"threshold ${threshold_value:.2f}"
            )
        
        return AlertResult(
            threshold_config=threshold,
            triggered=triggered,
            current_value=current_value,
            threshold_value=threshold_value,
            severity=threshold.severity,
            message=message,
            details={
                "threshold_type": "account_specific",
                "account_id": account_id,
                "account_cost": current_value
            }
        )
    
    def get_historical_cost_periods(
        self,
        current_period_start: datetime,
        current_period_end: datetime
    ) -> Dict[str, Tuple[datetime, datetime]]:
        """
        Calculate date ranges for historical comparison periods.
        
        Args:
            current_period_start: Start of current reporting period
            current_period_end: End of current reporting period
            
        Returns:
            Dictionary mapping period names to (start, end) date tuples
        """
        periods = {}
        
        # Calculate period duration
        period_duration = current_period_end - current_period_start
        
        # Previous week/month (same duration, shifted back)
        prev_end = current_period_start
        prev_start = prev_end - period_duration
        periods[ComparisonPeriod.PREVIOUS_WEEK.value] = (prev_start, prev_end)
        periods[ComparisonPeriod.PREVIOUS_MONTH.value] = (prev_start, prev_end)
        
        # Same week last month (4 weeks ago)
        if period_duration.days <= 7:  # Weekly report
            same_week_start = current_period_start - timedelta(weeks=4)
            same_week_end = current_period_end - timedelta(weeks=4)
            periods[ComparisonPeriod.SAME_WEEK_LAST_MONTH.value] = (same_week_start, same_week_end)
        
        # Same month last year (365 days ago)
        same_month_start = current_period_start - timedelta(days=365)
        same_month_end = current_period_end - timedelta(days=365)
        periods[ComparisonPeriod.SAME_MONTH_LAST_YEAR.value] = (same_month_start, same_month_end)
        
        return periods
    
    def format_currency(self, amount: float) -> str:
        """Format currency amount for display."""
        return f"${amount:,.2f}"
    
    def calculate_percentage_change(self, current: float, previous: float) -> float:
        """Calculate percentage change between two values."""
        if previous == 0:
            return 0.0 if current == 0 else float('inf')
        return ((current - previous) / previous) * 100