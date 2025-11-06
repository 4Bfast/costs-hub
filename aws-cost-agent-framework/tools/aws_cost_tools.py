"""
AWS Cost Explorer tools and utilities
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class AWSCostTools:
    """Tools for interacting with AWS Cost Explorer"""
    
    def __init__(self, aws_config):
        self.aws_config = aws_config
        self.session = boto3.Session(
            profile_name=aws_config.profile_name,
            region_name=aws_config.cost_explorer_region
        )
        self.ce_client = self.session.client('ce')
    
    def get_date_ranges(self, periods: int, analysis_type: str = "monthly") -> List[Dict[str, str]]:
        """Generate date ranges for the last N periods (months/weeks/days)"""
        today = datetime.now()
        ranges = []
        
        if analysis_type == "monthly":
            current_month_start = today.replace(day=1)
            
            for i in range(periods):
                if i == 0:
                    # Previous complete month
                    end_date = current_month_start
                    start_date = (end_date - timedelta(days=1)).replace(day=1)
                else:
                    # Go back one more month
                    end_date = start_date
                    start_date = (end_date - timedelta(days=1)).replace(day=1)
                
                ranges.append({
                    'name': start_date.strftime('%B %Y'),
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'period_key': start_date.strftime('%Y-%m'),
                    'analysis_type': 'monthly'
                })
        
        elif analysis_type == "weekly":
            # Calculate weeks starting from Monday
            current_date = today
            
            for i in range(periods):
                if i == 0:
                    # Current week or last complete week
                    days_since_monday = current_date.weekday()
                    if days_since_monday == 0 and current_date.hour < 12:
                        # If it's Monday morning, use previous week
                        week_start = current_date - timedelta(days=7)
                    else:
                        # Use current week up to today
                        week_start = current_date - timedelta(days=days_since_monday)
                    
                    week_end = week_start + timedelta(days=6)
                    if week_end > today:
                        week_end = today
                else:
                    # Go back one more week
                    week_start = week_start - timedelta(days=7)
                    week_end = week_start + timedelta(days=6)
                
                ranges.append({
                    'name': f"Week of {week_start.strftime('%b %d, %Y')}",
                    'start_date': week_start.strftime('%Y-%m-%d'),
                    'end_date': (week_end + timedelta(days=1)).strftime('%Y-%m-%d'),  # AWS API expects exclusive end date
                    'period_key': f"{week_start.strftime('%Y-W%U')}",
                    'analysis_type': 'weekly'
                })
        
        elif analysis_type == "daily":
            current_date = today
            
            for i in range(periods):
                if i == 0:
                    # Yesterday (most recent complete day)
                    target_date = current_date - timedelta(days=1)
                else:
                    # Go back one more day
                    target_date = current_date - timedelta(days=i + 1)
                
                ranges.append({
                    'name': target_date.strftime('%B %d, %Y'),
                    'start_date': target_date.strftime('%Y-%m-%d'),
                    'end_date': (target_date + timedelta(days=1)).strftime('%Y-%m-%d'),
                    'period_key': target_date.strftime('%Y-%m-%d'),
                    'analysis_type': 'daily'
                })
        
        return ranges
    
    def get_date_ranges_legacy(self, months: int) -> List[Dict[str, str]]:
        """Legacy method for backward compatibility"""
        return self.get_date_ranges(months, "monthly")
    
    async def get_cost_forecast(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get cost forecast for a specific period"""
        try:
            # Ensure forecast starts from today or later
            today = datetime.now()
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            
            # If start date is in the past, use today
            if start_dt < today:
                forecast_start = today.strftime('%Y-%m-%d')
                logger.debug(f"Adjusting forecast start date from {start_date} to {forecast_start}")
            else:
                forecast_start = start_date
            
            logger.debug(f"Fetching cost forecast for {forecast_start} to {end_date}")
            
            response = self.ce_client.get_cost_forecast(
                TimePeriod={
                    'Start': forecast_start,
                    'End': end_date
                },
                Metric='UNBLENDED_COST',
                Granularity='MONTHLY'
            )
            
            total_forecast = 0
            if response['Total']:
                total_forecast = float(response['Total']['Amount'])
            
            return {
                'total_forecast': total_forecast,
                'period': f"{forecast_start} to {end_date}",
                'currency': response['Total']['Unit'] if response['Total'] else 'USD',
                'forecast_start_adjusted': forecast_start != start_date
            }
            
        except Exception as e:
            logger.error(f"Error fetching cost forecast for {start_date}-{end_date}: {e}")
            return {
                'total_forecast': 0,
                'period': f"{start_date} to {end_date}",
                'currency': 'USD',
                'error': str(e)
            }
    
    async def get_current_month_costs(self) -> Dict[str, Any]:
        """Get costs for current month up to today"""
        try:
            today = datetime.now()
            month_start = today.replace(day=1)
            
            logger.debug(f"Fetching current month costs from {month_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")
            
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': month_start.strftime('%Y-%m-%d'),
                    'End': today.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )
            
            # Aggregate services across all days
            services = {}
            total_cost = 0
            
            if response['ResultsByTime']:
                for time_period in response['ResultsByTime']:
                    for group in time_period['Groups']:
                        service_name = group['Keys'][0]
                        cost = float(group['Metrics']['UnblendedCost']['Amount'])
                        
                        if cost > 0:
                            if service_name in services:
                                services[service_name] += cost
                            else:
                                services[service_name] = cost
                            total_cost += cost
            
            return {
                'services': services,
                'total_cost': total_cost,
                'period': f"{month_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}",
                'service_count': len(services),
                'days_elapsed': (today - month_start).days + 1
            }
            
        except Exception as e:
            logger.error(f"Error fetching current month costs: {e}")
            return {
                'services': {},
                'total_cost': 0,
                'period': 'current month',
                'service_count': 0,
                'days_elapsed': 0,
                'error': str(e)
            }
    
    async def analyze_weekly_projection(self) -> Dict[str, Any]:
        """Analyze weekly cost projection based on current spending trends"""
        try:
            today = datetime.now()
            
            # Get current week (Monday to Sunday)
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            
            # Get current week costs
            current_week_costs = await self.get_period_costs(
                week_start.strftime('%Y-%m-%d'),
                today.strftime('%Y-%m-%d'),
                "daily"
            )
            
            # Get previous week for comparison
            prev_week_start = week_start - timedelta(days=7)
            prev_week_end = week_start
            
            prev_week_costs = await self.get_period_costs(
                prev_week_start.strftime('%Y-%m-%d'),
                prev_week_end.strftime('%Y-%m-%d'),
                "daily"
            )
            
            # Calculate projections
            days_elapsed = days_since_monday + 1
            days_remaining = 7 - days_elapsed
            
            # Project current week to end of week
            if days_elapsed > 0:
                daily_average = current_week_costs['total_cost'] / days_elapsed
                projected_week_total = daily_average * 7
            else:
                projected_week_total = 0
            
            # Calculate changes
            week_vs_previous = projected_week_total - prev_week_costs['total_cost']
            week_vs_previous_percent = (
                (week_vs_previous / prev_week_costs['total_cost'] * 100) 
                if prev_week_costs['total_cost'] > 0 else 0
            )
            
            # Analyze service-level projections
            current_services = current_week_costs['services']
            previous_services = prev_week_costs['services']
            
            service_projections = {}
            for service, current_cost in current_services.items():
                if days_elapsed > 0:
                    projected_service_cost = (current_cost / days_elapsed) * 7
                    previous_service_cost = previous_services.get(service, 0)
                    
                    change = projected_service_cost - previous_service_cost
                    percent_change = (
                        (change / previous_service_cost * 100) 
                        if previous_service_cost > 0 else 100
                    )
                    
                    service_projections[service] = {
                        'current_cost': current_cost,
                        'projected_cost': projected_service_cost,
                        'previous_cost': previous_service_cost,
                        'projected_change': change,
                        'projected_percent_change': percent_change,
                        'contribution_to_increase': change if change > 0 else 0
                    }
            
            # Sort by contribution to increase
            top_drivers = dict(sorted(
                service_projections.items(),
                key=lambda x: x[1]['contribution_to_increase'],
                reverse=True
            ))
            
            return {
                'current_week': {
                    'total_cost': current_week_costs['total_cost'],
                    'days_elapsed': days_elapsed,
                    'days_remaining': days_remaining,
                    'week_start': week_start.strftime('%Y-%m-%d'),
                    'week_end': week_end.strftime('%Y-%m-%d'),
                    'services': current_services
                },
                'previous_week': {
                    'total_cost': prev_week_costs['total_cost'],
                    'services': previous_services
                },
                'projection': {
                    'projected_total': projected_week_total,
                    'vs_previous_change': week_vs_previous,
                    'vs_previous_percent': week_vs_previous_percent,
                    'daily_average': daily_average if days_elapsed > 0 else 0
                },
                'service_drivers': top_drivers,
                'summary': {
                    'is_trending_up': week_vs_previous_percent > 10,  # Higher threshold for weekly
                    'week_increase_percent': week_vs_previous_percent,
                    'top_driver': list(top_drivers.keys())[0] if top_drivers else None,
                    'top_driver_increase': list(top_drivers.values())[0]['projected_change'] if top_drivers else 0
                },
                'analysis_type': 'weekly'
            }
            
        except Exception as e:
            logger.error(f"Error analyzing weekly projection: {e}")
            return {
                'error': str(e),
                'summary': {
                    'is_trending_up': False,
                    'week_increase_percent': 0
                },
                'analysis_type': 'weekly'
            }

    async def analyze_forecast_vs_current(self) -> Dict[str, Any]:
        """Analyze forecast vs current month spending to identify cost drivers"""
        try:
            today = datetime.now()
            month_start = today.replace(day=1)
            
            # Calculate end of current month
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            
            # Get current month costs
            current_costs = await self.get_current_month_costs()
            
            # Try to get AWS forecast, but calculate our own if it fails
            forecast = await self.get_cost_forecast(
                today.strftime('%Y-%m-%d'),
                next_month.strftime('%Y-%m-%d')
            )
            
            # If AWS forecast fails or returns 0, calculate based on current trend
            if forecast.get('error') or forecast.get('total_forecast', 0) == 0:
                days_in_month = (next_month - month_start).days
                days_elapsed = current_costs['days_elapsed']
                
                if days_elapsed > 0:
                    daily_average = current_costs['total_cost'] / days_elapsed
                    calculated_forecast = daily_average * days_in_month
                    
                    forecast = {
                        'total_forecast': calculated_forecast,
                        'period': f"{month_start.strftime('%Y-%m-%d')} to {next_month.strftime('%Y-%m-%d')}",
                        'currency': 'USD',
                        'calculated': True,
                        'note': 'Calculated from current spending trend (AWS forecast unavailable)'
                    }
                else:
                    forecast = {
                        'total_forecast': 0,
                        'period': f"{month_start.strftime('%Y-%m-%d')} to {next_month.strftime('%Y-%m-%d')}",
                        'currency': 'USD',
                        'error': 'Insufficient data for forecast'
                    }
            
            # Get previous month for comparison
            prev_month_end = month_start
            if prev_month_end.month == 1:
                prev_month_start = prev_month_end.replace(year=prev_month_end.year - 1, month=12, day=1)
            else:
                prev_month_start = prev_month_end.replace(month=prev_month_end.month - 1, day=1)
            
            prev_month_costs = await self.get_period_costs(
                prev_month_start.strftime('%Y-%m-%d'),
                prev_month_end.strftime('%Y-%m-%d'),
                "monthly"
            )
            
            # Calculate projections and changes
            days_in_month = (next_month - month_start).days
            days_elapsed = current_costs['days_elapsed']
            days_remaining = days_in_month - days_elapsed
            
            # Project current spending to end of month
            if days_elapsed > 0:
                daily_average = current_costs['total_cost'] / days_elapsed
                projected_total = daily_average * days_in_month
            else:
                projected_total = 0
            
            # Calculate changes
            forecast_vs_previous = forecast['total_forecast'] - prev_month_costs['total_cost']
            forecast_vs_previous_percent = (
                (forecast_vs_previous / prev_month_costs['total_cost'] * 100) 
                if prev_month_costs['total_cost'] > 0 else 0
            )
            
            projected_vs_previous = projected_total - prev_month_costs['total_cost']
            projected_vs_previous_percent = (
                (projected_vs_previous / prev_month_costs['total_cost'] * 100) 
                if prev_month_costs['total_cost'] > 0 else 0
            )
            
            # Identify top cost drivers in current month
            current_services = current_costs['services']
            previous_services = prev_month_costs['services']
            
            service_projections = {}
            for service, current_cost in current_services.items():
                if days_elapsed > 0:
                    projected_service_cost = (current_cost / days_elapsed) * days_in_month
                    previous_service_cost = previous_services.get(service, 0)
                    
                    change = projected_service_cost - previous_service_cost
                    percent_change = (
                        (change / previous_service_cost * 100) 
                        if previous_service_cost > 0 else 100
                    )
                    
                    service_projections[service] = {
                        'current_cost': current_cost,
                        'projected_cost': projected_service_cost,
                        'previous_cost': previous_service_cost,
                        'projected_change': change,
                        'projected_percent_change': percent_change,
                        'contribution_to_increase': change if change > 0 else 0
                    }
            
            # Sort by contribution to increase
            top_drivers = dict(sorted(
                service_projections.items(),
                key=lambda x: x[1]['contribution_to_increase'],
                reverse=True
            ))
            
            return {
                'current_month': {
                    'total_cost': current_costs['total_cost'],
                    'days_elapsed': days_elapsed,
                    'days_remaining': days_remaining,
                    'services': current_services
                },
                'previous_month': {
                    'total_cost': prev_month_costs['total_cost'],
                    'services': previous_services
                },
                'forecast': {
                    'total_forecast': forecast['total_forecast'],
                    'vs_previous_change': forecast_vs_previous,
                    'vs_previous_percent': forecast_vs_previous_percent
                },
                'projection': {
                    'projected_total': projected_total,
                    'vs_previous_change': projected_vs_previous,
                    'vs_previous_percent': projected_vs_previous_percent
                },
                'service_drivers': top_drivers,
                'summary': {
                    'is_trending_up': forecast_vs_previous_percent > 4,
                    'forecast_increase_percent': forecast_vs_previous_percent,
                    'top_driver': list(top_drivers.keys())[0] if top_drivers else None,
                    'top_driver_increase': list(top_drivers.values())[0]['projected_change'] if top_drivers else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing forecast vs current: {e}")
            return {
                'error': str(e),
                'summary': {
                    'is_trending_up': False,
                    'forecast_increase_percent': 0
                }
            }

    async def get_period_costs(self, start_date: str, end_date: str, analysis_type: str = "monthly") -> Dict[str, Any]:
        """Get cost breakdown by service for a specific period (monthly/weekly/daily)"""
        try:
            logger.debug(f"Fetching {analysis_type} costs for {start_date} to {end_date}")
            
            # Determine granularity based on analysis type
            granularity = 'MONTHLY'
            if analysis_type == 'weekly':
                granularity = 'DAILY'  # AWS doesn't have weekly, so we use daily and aggregate
            elif analysis_type == 'daily':
                granularity = 'DAILY'
            
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity=granularity,
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )
            
            # Parse response and aggregate if needed
            services = {}
            total_cost = 0
            
            if response['ResultsByTime']:
                # For weekly/daily, we might have multiple time periods to aggregate
                for time_period in response['ResultsByTime']:
                    for group in time_period['Groups']:
                        service_name = group['Keys'][0]
                        cost = float(group['Metrics']['UnblendedCost']['Amount'])
                        
                        if cost > 0:
                            if service_name in services:
                                services[service_name] += cost
                            else:
                                services[service_name] = cost
                            total_cost += cost
            
            return {
                'services': services,
                'total_cost': total_cost,
                'period': f"{start_date} to {end_date}",
                'service_count': len(services),
                'analysis_type': analysis_type
            }
            
        except Exception as e:
            logger.error(f"Error fetching {analysis_type} costs for {start_date}-{end_date}: {e}")
            return {
                'services': {},
                'total_cost': 0,
                'period': f"{start_date} to {end_date}",
                'service_count': 0,
                'analysis_type': analysis_type,
                'error': str(e)
            }
    
    async def get_monthly_costs(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Legacy method for backward compatibility"""
        return await self.get_period_costs(start_date, end_date, "monthly")
    
    async def get_period_costs_by_account(self, start_date: str, end_date: str, analysis_type: str = "monthly") -> Dict[str, Any]:
        """Get cost breakdown by account for a specific period (monthly/weekly/daily)"""
        try:
            logger.debug(f"Fetching {analysis_type} costs by account for {start_date} to {end_date}")
            
            # Determine granularity based on analysis type
            granularity = 'MONTHLY'
            if analysis_type == 'weekly':
                granularity = 'DAILY'
            elif analysis_type == 'daily':
                granularity = 'DAILY'
            
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity=granularity,
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'LINKED_ACCOUNT'
                    }
                ]
            )
            
            # Parse response and aggregate if needed
            accounts = {}
            total_cost = 0
            
            if response['ResultsByTime']:
                for time_period in response['ResultsByTime']:
                    for group in time_period['Groups']:
                        account_id = group['Keys'][0]
                        cost = float(group['Metrics']['UnblendedCost']['Amount'])
                        
                        if cost > 0:
                            if account_id in accounts:
                                accounts[account_id] += cost
                            else:
                                accounts[account_id] = cost
                            total_cost += cost
            
            return {
                'accounts': accounts,
                'total_cost': total_cost,
                'period': f"{start_date} to {end_date}",
                'account_count': len(accounts),
                'analysis_type': analysis_type
            }
            
        except Exception as e:
            logger.error(f"Error fetching {analysis_type} costs by account for {start_date}-{end_date}: {e}")
            return {
                'accounts': {},
                'total_cost': 0,
                'period': f"{start_date} to {end_date}",
                'account_count': 0,
                'analysis_type': analysis_type,
                'error': str(e)
            }
    
    async def get_monthly_costs_by_account(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Legacy method for backward compatibility"""
        return await self.get_period_costs_by_account(start_date, end_date, "monthly")
    
    def analyze_cost_changes(self, current_data: Dict, previous_data: Dict, 
                           min_threshold: float = 1.0) -> Dict[str, Any]:
        """Analyze cost changes between two periods"""
        
        changes = {}
        new_services = []
        removed_services = []
        
        current_services = current_data['services']
        previous_services = previous_data['services']
        
        # Analyze existing services
        for service, current_cost in current_services.items():
            if service in previous_services:
                previous_cost = previous_services[service]
                change = current_cost - previous_cost
                
                if abs(change) >= min_threshold:
                    changes[service] = {
                        'current': current_cost,
                        'previous': previous_cost,
                        'change': change,
                        'percent_change': (change / previous_cost * 100) if previous_cost > 0 else 0,
                        'change_type': 'increase' if change > 0 else 'decrease'
                    }
            else:
                # New service
                if current_cost >= min_threshold:
                    new_services.append({
                        'service': service,
                        'cost': current_cost
                    })
        
        # Find removed services
        for service, previous_cost in previous_services.items():
            if service not in current_services and previous_cost >= min_threshold:
                removed_services.append({
                    'service': service,
                    'cost': previous_cost
                })
        
        # Sort changes by absolute change amount
        sorted_changes = dict(sorted(
            changes.items(),
            key=lambda x: abs(x[1]['change']),
            reverse=True
        ))
        
        # Calculate totals
        total_change = current_data['total_cost'] - previous_data['total_cost']
        total_percent_change = (
            (total_change / previous_data['total_cost'] * 100) 
            if previous_data['total_cost'] > 0 else 0
        )
        
        return {
            'total_change': total_change,
            'total_percent_change': total_percent_change,
            'service_changes': sorted_changes,
            'new_services': sorted(new_services, key=lambda x: x['cost'], reverse=True),
            'removed_services': sorted(removed_services, key=lambda x: x['cost'], reverse=True),
            'current_period': current_data,
            'previous_period': previous_data,
            'summary': {
                'services_analyzed': len(set(current_services.keys()) | set(previous_services.keys())),
                'services_changed': len(sorted_changes),
                'services_added': len(new_services),
                'services_removed': len(removed_services)
            }
        }
    
    def get_top_services(self, cost_data: Dict, top_n: int = 10) -> List[Dict]:
        """Get top N services by cost"""
        services = cost_data['services']
        sorted_services = sorted(services.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                'service': service,
                'cost': cost,
                'percentage': (cost / cost_data['total_cost'] * 100) if cost_data['total_cost'] > 0 else 0
            }
            for service, cost in sorted_services[:top_n]
        ]
    
    def get_top_accounts(self, cost_data: Dict, top_n: int = 10) -> List[Dict]:
        """Get top N accounts by cost"""
        accounts = cost_data['accounts']
        sorted_accounts = sorted(accounts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                'account_id': account_id,
                'cost': cost,
                'percentage': (cost / cost_data['total_cost'] * 100) if cost_data['total_cost'] > 0 else 0
            }
            for account_id, cost in sorted_accounts[:top_n]
        ]
    
    def analyze_account_changes(self, current_data: Dict, previous_data: Dict, 
                              min_threshold: float = 1.0) -> Dict[str, Any]:
        """Analyze cost changes between two periods by account"""
        
        changes = {}
        new_accounts = []
        removed_accounts = []
        
        current_accounts = current_data['accounts']
        previous_accounts = previous_data['accounts']
        
        # Analyze existing accounts
        for account_id, current_cost in current_accounts.items():
            if account_id in previous_accounts:
                previous_cost = previous_accounts[account_id]
                change = current_cost - previous_cost
                
                if abs(change) >= min_threshold:
                    changes[account_id] = {
                        'current': current_cost,
                        'previous': previous_cost,
                        'change': change,
                        'percent_change': (change / previous_cost * 100) if previous_cost > 0 else 0,
                        'change_type': 'increase' if change > 0 else 'decrease'
                    }
            else:
                # New account
                if current_cost >= min_threshold:
                    new_accounts.append({
                        'account_id': account_id,
                        'cost': current_cost
                    })
        
        # Find removed accounts
        for account_id, previous_cost in previous_accounts.items():
            if account_id not in current_accounts and previous_cost >= min_threshold:
                removed_accounts.append({
                    'account_id': account_id,
                    'cost': previous_cost
                })
        
        # Sort changes by absolute change amount
        sorted_changes = dict(sorted(
            changes.items(),
            key=lambda x: abs(x[1]['change']),
            reverse=True
        ))
        
        # Calculate totals
        total_change = current_data['total_cost'] - previous_data['total_cost']
        total_percent_change = (
            (total_change / previous_data['total_cost'] * 100) 
            if previous_data['total_cost'] > 0 else 0
        )
        
        return {
            'total_change': total_change,
            'total_percent_change': total_percent_change,
            'account_changes': sorted_changes,
            'new_accounts': sorted(new_accounts, key=lambda x: x['cost'], reverse=True),
            'removed_accounts': sorted(removed_accounts, key=lambda x: x['cost'], reverse=True),
            'current_period': current_data,
            'previous_period': previous_data,
            'summary': {
                'accounts_analyzed': len(set(current_accounts.keys()) | set(previous_accounts.keys())),
                'accounts_changed': len(sorted_changes),
                'accounts_added': len(new_accounts),
                'accounts_removed': len(removed_accounts)
            }
        }
