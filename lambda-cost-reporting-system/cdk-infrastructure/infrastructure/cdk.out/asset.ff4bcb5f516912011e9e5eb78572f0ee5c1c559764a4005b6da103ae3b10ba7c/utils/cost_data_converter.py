"""
Utility functions for converting between different cost data formats.

This module provides functions to convert between the existing cost data format
used by the Lambda Cost Agent and the new CostData format used by the threshold evaluator.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from ..models.threshold_models import CostData


def convert_client_cost_data_to_cost_data(
    client_cost_data: Dict[str, Any],
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None
) -> CostData:
    """
    Convert ClientCostData format to CostData format for threshold evaluation.
    
    Args:
        client_cost_data: Cost data in ClientCostData format
        period_start: Start of the reporting period
        period_end: End of the reporting period
        
    Returns:
        CostData object for threshold evaluation
    """
    # Extract total cost
    total_cost = client_cost_data.get('total_cost', 0.0)
    
    # Extract service costs from aggregated data
    service_costs = {}
    if 'top_services' in client_cost_data:
        for service_data in client_cost_data['top_services']:
            if isinstance(service_data, dict):
                service_name = service_data.get('service', service_data.get('name', ''))
                service_cost = service_data.get('cost', service_data.get('total_cost', 0.0))
                if service_name:
                    service_costs[service_name] = float(service_cost)
    
    # If top_services is not available, try to extract from accounts_data
    if not service_costs and 'accounts_data' in client_cost_data:
        for account_data in client_cost_data['accounts_data']:
            if 'services' in account_data:
                for service_name, service_cost in account_data['services'].items():
                    if service_name in service_costs:
                        service_costs[service_name] += float(service_cost)
                    else:
                        service_costs[service_name] = float(service_cost)
    
    # Extract account costs
    account_costs = {}
    if 'accounts_data' in client_cost_data:
        for account_data in client_cost_data['accounts_data']:
            account_id = account_data.get('account_id', '')
            account_cost = account_data.get('total_cost', 0.0)
            if account_id:
                account_costs[account_id] = float(account_cost)
    
    # If accounts_data is not available, try top_accounts
    if not account_costs and 'top_accounts' in client_cost_data:
        for account_data in client_cost_data['top_accounts']:
            if isinstance(account_data, dict):
                account_id = account_data.get('account_id', account_data.get('account', ''))
                account_cost = account_data.get('cost', account_data.get('total_cost', 0.0))
                if account_id:
                    account_costs[account_id] = float(account_cost)
    
    return CostData(
        total_cost=float(total_cost),
        service_costs=service_costs,
        account_costs=account_costs,
        period_start=period_start,
        period_end=period_end
    )


def extract_historical_cost_data(
    client_cost_data: Dict[str, Any],
    period_mappings: Dict[str, str]
) -> Dict[str, CostData]:
    """
    Extract historical cost data for comparison periods.
    
    Args:
        client_cost_data: Cost data in ClientCostData format
        period_mappings: Mapping of comparison period names to data keys
        
    Returns:
        Dictionary mapping period names to CostData objects
    """
    historical_data = {}
    
    # Try to extract from periods_data or months_data
    periods_data = client_cost_data.get('periods_data', client_cost_data.get('months_data', []))
    
    if periods_data and len(periods_data) > 1:
        # Assume the first period is current, second is previous
        if len(periods_data) >= 2:
            previous_period = periods_data[1]
            
            # Convert previous period to CostData
            previous_cost_data = CostData(
                total_cost=float(previous_period.get('total_cost', 0.0)),
                service_costs={k: float(v) for k, v in previous_period.get('services', {}).items()},
                account_costs={},  # Account breakdown not available in period data
                period_start=datetime.fromisoformat(previous_period['start_date']) if 'start_date' in previous_period else None,
                period_end=datetime.fromisoformat(previous_period['end_date']) if 'end_date' in previous_period else None
            )
            
            # Map to all comparison periods (simplified approach)
            for period_name in period_mappings.keys():
                historical_data[period_name] = previous_cost_data
    
    return historical_data


def format_alert_summary(alerts: list) -> Dict[str, Any]:
    """
    Format alerts for display in reports.
    
    Args:
        alerts: List of AlertResult objects
        
    Returns:
        Dictionary with formatted alert summary
    """
    if not alerts:
        return {
            'has_alerts': False,
            'total_alerts': 0,
            'critical_alerts': 0,
            'high_alerts': 0,
            'medium_alerts': 0,
            'low_alerts': 0,
            'alerts_by_severity': {},
            'alert_messages': []
        }
    
    # Count alerts by severity
    severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    alerts_by_severity = {'critical': [], 'high': [], 'medium': [], 'low': []}
    alert_messages = []
    
    for alert in alerts:
        if alert.triggered:
            severity = alert.severity.value.lower()
            severity_counts[severity] += 1
            alerts_by_severity[severity].append(alert)
            alert_messages.append({
                'severity': severity,
                'message': alert.message,
                'threshold_name': alert.threshold_config.name,
                'current_value': alert.current_value,
                'threshold_value': alert.threshold_value
            })
    
    return {
        'has_alerts': sum(severity_counts.values()) > 0,
        'total_alerts': sum(severity_counts.values()),
        'critical_alerts': severity_counts['critical'],
        'high_alerts': severity_counts['high'],
        'medium_alerts': severity_counts['medium'],
        'low_alerts': severity_counts['low'],
        'alerts_by_severity': alerts_by_severity,
        'alert_messages': alert_messages
    }