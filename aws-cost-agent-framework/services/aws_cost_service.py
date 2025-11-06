import boto3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config.settings import config

class AWSCostService:
    """Real AWS Cost Explorer integration service"""
    
    def __init__(self, account_config: Dict):
        """Initialize with account-specific credentials"""
        self.account_id = account_config.get('account_id')
        self.role_arn = account_config.get('configuration', {}).get('role_arn')
        self.external_id = account_config.get('configuration', {}).get('external_id')
        self.cost_explorer = self._get_cost_explorer_client()
    
    def _get_cost_explorer_client(self):
        """Get Cost Explorer client with assume role if configured"""
        try:
            if self.role_arn:
                sts = boto3.client('sts', region_name=config.AWS_REGION)
                assumed_role = sts.assume_role(
                    RoleArn=self.role_arn,
                    RoleSessionName='costhub-cost-analysis',
                    ExternalId=self.external_id
                )
                credentials = assumed_role['Credentials']
                return boto3.client(
                    'ce',
                    region_name='us-east-1',  # Cost Explorer is only in us-east-1
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
            else:
                return boto3.client('ce', region_name='us-east-1')
        except Exception as e:
            print(f"Error creating Cost Explorer client: {e}")
            return boto3.client('ce', region_name='us-east-1')
    
    def get_cost_summary(self, start_date: str, end_date: str) -> Dict:
        """Get real cost summary from AWS Cost Explorer"""
        try:
            response = self.cost_explorer.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=['BlendedCost', 'UsageQuantity'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            return self._process_cost_summary_response(response)
        except Exception as e:
            print(f"Error getting cost summary: {e}")
            return self._get_fallback_summary()
    
    def get_cost_trends(self, days: int = 30) -> Dict:
        """Get cost trends for specified period"""
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            response = self.cost_explorer.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='DAILY',
                Metrics=['BlendedCost']
            )
            return self._process_trend_response(response)
        except Exception as e:
            print(f"Error getting cost trends: {e}")
            return self._get_fallback_trends()
    
    def get_cost_breakdown(self, group_by: str = 'SERVICE', days: int = 30) -> Dict:
        """Get cost breakdown by dimension"""
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            response = self.cost_explorer.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': group_by}]
            )
            return self._process_breakdown_response(response, group_by)
        except Exception as e:
            print(f"Error getting cost breakdown: {e}")
            return self._get_fallback_breakdown(group_by)
    
    def get_cost_by_service(self, days: int = 30) -> Dict:
        """Get costs grouped by AWS service"""
        return self.get_cost_breakdown('SERVICE', days)
    
    def get_cost_by_region(self, days: int = 30) -> Dict:
        """Get costs grouped by AWS region"""
        return self.get_cost_breakdown('REGION', days)
    
    def _process_cost_summary_response(self, response: Dict) -> Dict:
        """Process Cost Explorer response for summary"""
        results = response.get('ResultsByTime', [])
        if not results:
            return self._get_fallback_summary()
        
        total_cost = 0
        services = {}
        
        for result in results:
            period_start = result['TimePeriod']['Start']
            period_end = result['TimePeriod']['End']
            
            for group in result.get('Groups', []):
                service_name = group['Keys'][0] if group['Keys'] else 'Unknown'
                cost_amount = float(group['Metrics']['BlendedCost']['Amount'])
                
                if service_name not in services:
                    services[service_name] = 0
                services[service_name] += cost_amount
                total_cost += cost_amount
        
        # Sort services by cost
        sorted_services = dict(sorted(services.items(), key=lambda x: x[1], reverse=True))
        
        return {
            'total_cost': round(total_cost, 2),
            'currency': 'USD',
            'period': {
                'start': results[0]['TimePeriod']['Start'],
                'end': results[-1]['TimePeriod']['End']
            },
            'services': sorted_services,
            'top_services': dict(list(sorted_services.items())[:10]),
            'service_count': len(services),
            'account_id': self.account_id
        }
    
    def _process_trend_response(self, response: Dict) -> Dict:
        """Process Cost Explorer response for trends"""
        results = response.get('ResultsByTime', [])
        if not results:
            return self._get_fallback_trends()
        
        daily_costs = []
        total_cost = 0
        
        for result in results:
            date = result['TimePeriod']['Start']
            cost = float(result['Total']['BlendedCost']['Amount'])
            daily_costs.append({
                'date': date,
                'cost': round(cost, 2)
            })
            total_cost += cost
        
        # Calculate trend
        if len(daily_costs) >= 2:
            first_week = sum(day['cost'] for day in daily_costs[:7])
            last_week = sum(day['cost'] for day in daily_costs[-7:])
            trend_percent = ((last_week - first_week) / first_week * 100) if first_week > 0 else 0
        else:
            trend_percent = 0
        
        return {
            'daily_costs': daily_costs,
            'total_cost': round(total_cost, 2),
            'average_daily_cost': round(total_cost / len(daily_costs), 2) if daily_costs else 0,
            'trend_percent': round(trend_percent, 2),
            'period_days': len(daily_costs),
            'account_id': self.account_id
        }
    
    def _process_breakdown_response(self, response: Dict, group_by: str) -> Dict:
        """Process Cost Explorer response for breakdown"""
        results = response.get('ResultsByTime', [])
        if not results:
            return self._get_fallback_breakdown(group_by)
        
        breakdown = {}
        total_cost = 0
        
        for result in results:
            for group in result.get('Groups', []):
                key = group['Keys'][0] if group['Keys'] else 'Unknown'
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                
                if key not in breakdown:
                    breakdown[key] = 0
                breakdown[key] += cost
                total_cost += cost
        
        # Sort by cost
        sorted_breakdown = dict(sorted(breakdown.items(), key=lambda x: x[1], reverse=True))
        
        return {
            'breakdown': sorted_breakdown,
            'total_cost': round(total_cost, 2),
            'group_by': group_by,
            'top_10': dict(list(sorted_breakdown.items())[:10]),
            'item_count': len(breakdown),
            'account_id': self.account_id
        }
    
    def _get_fallback_summary(self) -> Dict:
        """Fallback data when Cost Explorer fails"""
        return {
            'total_cost': 0.0,
            'currency': 'USD',
            'period': {
                'start': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                'end': datetime.now().strftime('%Y-%m-%d')
            },
            'services': {},
            'top_services': {},
            'service_count': 0,
            'account_id': self.account_id,
            'note': 'Cost Explorer data unavailable - using fallback'
        }
    
    def _get_fallback_trends(self) -> Dict:
        """Fallback trends when Cost Explorer fails"""
        return {
            'daily_costs': [],
            'total_cost': 0.0,
            'average_daily_cost': 0.0,
            'trend_percent': 0.0,
            'period_days': 0,
            'account_id': self.account_id,
            'note': 'Cost Explorer data unavailable - using fallback'
        }
    
    def _get_fallback_breakdown(self, group_by: str) -> Dict:
        """Fallback breakdown when Cost Explorer fails"""
        return {
            'breakdown': {},
            'total_cost': 0.0,
            'group_by': group_by,
            'top_10': {},
            'item_count': 0,
            'account_id': self.account_id,
            'note': 'Cost Explorer data unavailable - using fallback'
        }
