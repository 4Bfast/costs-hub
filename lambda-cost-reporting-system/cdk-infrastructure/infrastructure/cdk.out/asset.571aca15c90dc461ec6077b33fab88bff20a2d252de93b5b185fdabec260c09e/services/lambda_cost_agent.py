"""
Lambda Cost Agent - Serverless adaptation of the CostAnalysisAgent for Lambda environment.

This module provides the LambdaCostAgent class that adapts the existing CostAnalysisAgent
for serverless execution in AWS Lambda, with multi-account access using access keys
instead of assume role.
"""

import asyncio
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

from ..models import ClientConfig, AccountConfig
from ..utils import create_logger


logger = create_logger(__name__)


class LambdaCostAgentError(Exception):
    """Base exception for LambdaCostAgent errors."""
    pass


class AccountAccessError(LambdaCostAgentError):
    """Raised when account access fails."""
    pass


class CostDataError(LambdaCostAgentError):
    """Raised when cost data collection fails."""
    pass


class ClientCostData:
    """Container for client cost data across multiple accounts."""
    
    def __init__(self, client_id: str, client_name: str):
        self.client_id = client_id
        self.client_name = client_name
        self.accounts_data: List[Dict[str, Any]] = []
        self.aggregated_data: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.total_cost: float = 0.0
        self.service_count: int = 0
        self.account_count: int = 0
        self.collection_time: Optional[datetime] = None
    
    def add_account_data(self, account_id: str, cost_data: Dict[str, Any]) -> None:
        """Add cost data for a specific account."""
        account_data = {
            'account_id': account_id,
            'cost_data': cost_data
        }
        self.accounts_data.append(account_data)
        
        # Update aggregated totals
        self.total_cost += cost_data.get('total_cost', 0)
        self.account_count += 1
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
    
    def finalize(self) -> None:
        """Finalize the cost data collection."""
        self.collection_time = datetime.utcnow()
        self._aggregate_services()
    
    def _aggregate_services(self) -> None:
        """Aggregate service costs across all accounts."""
        services = {}
        
        for account_data in self.accounts_data:
            account_services = account_data['cost_data'].get('services', {})
            for service, cost in account_services.items():
                if service in services:
                    services[service] += cost
                else:
                    services[service] = cost
        
        self.service_count = len(services)
        self.aggregated_data = {
            'services': services,
            'total_cost': self.total_cost,
            'service_count': self.service_count,
            'account_count': self.account_count,
            'accounts_data': self.accounts_data,
            'errors': self.errors,
            'collection_time': self.collection_time.isoformat() if self.collection_time else None
        }


class LambdaCostAgent:
    """
    Lambda-optimized cost analysis agent for serverless execution.
    
    Adapts the existing CostAnalysisAgent for Lambda environment with:
    - Multi-account access using access keys instead of assume role
    - Optimized for Lambda execution constraints (memory, timeout)
    - Parallel processing for multiple accounts per client
    - Comprehensive error handling for individual account failures
    """
    
    def __init__(self, client_config: ClientConfig, max_workers: int = 5, timeout_per_account: int = 30):
        """
        Initialize the Lambda Cost Agent.
        
        Args:
            client_config: Client configuration with AWS accounts and settings
            max_workers: Maximum number of concurrent workers for parallel processing
            timeout_per_account: Timeout in seconds for each account operation
        """
        self.client_config = client_config
        self.max_workers = max_workers
        self.timeout_per_account = timeout_per_account
        self.logger = create_logger(f"{__name__}.{client_config.client_id}")
        
        # Connection pool for reusing AWS clients with Lambda optimizations
        self._session_cache: Dict[str, boto3.Session] = {}
        self._client_cache: Dict[str, boto3.client] = {}
        
        # Optimized boto3 configuration for Lambda
        self._boto_config = Config(
            region_name='us-east-1',
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=max_workers * 2,
            connect_timeout=min(30, timeout_per_account // 2),
            read_timeout=timeout_per_account
        )
    
    def create_session_for_account(self, account_config: AccountConfig) -> boto3.Session:
        """
        Create or retrieve cached AWS session for an account using access keys.
        
        Args:
            account_config: Account configuration with credentials
            
        Returns:
            Configured boto3 Session
            
        Raises:
            AccountAccessError: If session creation fails
        """
        cache_key = f"{account_config.account_id}_{account_config.region}"
        
        # Return cached session if available
        if cache_key in self._session_cache:
            return self._session_cache[cache_key]
        
        try:
            self.logger.debug(f"Creating session for account {account_config.account_id}")
            
            session = boto3.Session(
                aws_access_key_id=account_config.access_key_id,
                aws_secret_access_key=account_config.secret_access_key,
                region_name=account_config.region
            )
            
            # Test the session by calling STS get_caller_identity
            sts = session.client('sts')
            response = sts.get_caller_identity()
            
            # Verify account ID matches
            if response.get('Account') != account_config.account_id:
                raise AccountAccessError(
                    f"Account ID mismatch for {account_config.account_id}: "
                    f"expected {account_config.account_id}, got {response.get('Account')}"
                )
            
            # Cache the session
            self._session_cache[cache_key] = session
            
            self.logger.debug(f"Successfully created session for account {account_config.account_id}")
            return session
            
        except ClientError as e:
            error_msg = f"Failed to create session for account {account_config.account_id}: {e}"
            self.logger.error(error_msg)
            raise AccountAccessError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error creating session for account {account_config.account_id}: {e}"
            self.logger.error(error_msg)
            raise AccountAccessError(error_msg) from e
    
    def get_cost_explorer_client(self, account_config: AccountConfig) -> boto3.client:
        """
        Get or create cached Cost Explorer client for an account.
        
        Args:
            account_config: Account configuration
            
        Returns:
            Cost Explorer client
        """
        cache_key = f"ce_{account_config.account_id}_{account_config.region}"
        
        if cache_key not in self._client_cache:
            # Limit cache size for memory optimization
            if len(self._client_cache) >= self.max_workers * 2:
                # Remove oldest client
                oldest_key = next(iter(self._client_cache))
                del self._client_cache[oldest_key]
                self.logger.debug(f"Removed oldest client {oldest_key} from cache")
            
            session = self.create_session_for_account(account_config)
            # Cost Explorer is only available in us-east-1 with optimized config
            self._client_cache[cache_key] = session.client('ce', region_name='us-east-1', config=self._boto_config)
        
        return self._client_cache[cache_key]
    
    async def collect_client_costs(self, report_type: str = "monthly", periods: int = 2) -> ClientCostData:
        """
        Collect cost data for all accounts of a client.
        
        Args:
            report_type: Type of report (monthly, weekly, daily)
            periods: Number of periods to analyze
            
        Returns:
            ClientCostData object with aggregated cost information
            
        Raises:
            CostDataError: If cost data collection fails completely
        """
        self.logger.info(f"Starting cost collection for client {self.client_config.client_id} ({report_type})")
        
        client_data = ClientCostData(self.client_config.client_id, self.client_config.client_name)
        
        try:
            # Generate date ranges for analysis
            date_ranges = self._get_date_ranges(periods, report_type)
            
            # Collect data from all accounts in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit tasks for each account
                future_to_account = {}
                for account in self.client_config.aws_accounts:
                    future = executor.submit(
                        self._collect_account_costs_sync,
                        account,
                        date_ranges,
                        report_type
                    )
                    future_to_account[future] = account
                
                # Collect results as they complete
                for future in as_completed(future_to_account, timeout=self.timeout_per_account * len(self.client_config.aws_accounts)):
                    account = future_to_account[future]
                    try:
                        account_cost_data = future.result(timeout=self.timeout_per_account)
                        client_data.add_account_data(account.account_id, account_cost_data)
                        
                        self.logger.info(
                            f"✅ Account {account.account_id}: ${account_cost_data.get('total_cost', 0):,.2f} "
                            f"({account_cost_data.get('service_count', 0)} services)"
                        )
                        
                    except Exception as e:
                        error_msg = f"Failed to collect costs for account {account.account_id}: {str(e)}"
                        self.logger.error(error_msg)
                        client_data.add_error(error_msg)
            
            # Finalize the client data
            client_data.finalize()
            
            if client_data.account_count == 0:
                raise CostDataError(f"No cost data collected for any account of client {self.client_config.client_id}")
            
            self.logger.info(
                f"✅ Client {self.client_config.client_id}: ${client_data.total_cost:,.2f} "
                f"({client_data.service_count} services, {client_data.account_count} accounts)"
            )
            
            return client_data
            
        except Exception as e:
            error_msg = f"Failed to collect client costs for {self.client_config.client_id}: {str(e)}"
            self.logger.error(error_msg)
            raise CostDataError(error_msg) from e
    
    def _collect_account_costs_sync(self, account_config: AccountConfig, date_ranges: List[Dict], report_type: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for collecting account costs (for use with ThreadPoolExecutor).
        
        Args:
            account_config: Account configuration
            date_ranges: List of date ranges to analyze
            report_type: Type of report
            
        Returns:
            Dictionary with account cost data
        """
        return asyncio.run(self._collect_account_costs(account_config, date_ranges, report_type))
    
    async def _collect_account_costs(self, account_config: AccountConfig, date_ranges: List[Dict], report_type: str) -> Dict[str, Any]:
        """
        Collect cost data for a single account across multiple periods.
        
        Args:
            account_config: Account configuration
            date_ranges: List of date ranges to analyze
            report_type: Type of report
            
        Returns:
            Dictionary with account cost data
        """
        try:
            ce_client = self.get_cost_explorer_client(account_config)
            
            periods_data = []
            total_cost = 0.0
            all_services = {}
            
            # Collect data for each period
            for period_info in date_ranges:
                try:
                    period_data = await self._get_period_costs(
                        ce_client,
                        period_info['start_date'],
                        period_info['end_date'],
                        report_type
                    )
                    
                    # Add period metadata
                    period_data.update({
                        'name': period_info['name'],
                        'start_date': period_info['start_date'],
                        'end_date': period_info['end_date'],
                        'period_key': period_info['period_key'],
                        'analysis_type': report_type,
                        'account_id': account_config.account_id
                    })
                    
                    periods_data.append(period_data)
                    total_cost += period_data.get('total_cost', 0)
                    
                    # Aggregate services
                    for service, cost in period_data.get('services', {}).items():
                        if service in all_services:
                            all_services[service] += cost
                        else:
                            all_services[service] = cost
                    
                except Exception as e:
                    self.logger.error(f"Failed to collect data for period {period_info['name']} in account {account_config.account_id}: {e}")
                    continue
            
            return {
                'account_id': account_config.account_id,
                'account_name': account_config.account_name,
                'periods_data': periods_data,
                'services': all_services,
                'total_cost': total_cost,
                'service_count': len(all_services),
                'periods_count': len(periods_data),
                'analysis_type': report_type
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting costs for account {account_config.account_id}: {e}")
            raise
    
    async def _get_period_costs(self, ce_client: boto3.client, start_date: str, end_date: str, analysis_type: str) -> Dict[str, Any]:
        """
        Get cost breakdown by service for a specific period using Cost Explorer.
        
        Args:
            ce_client: Cost Explorer client
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            analysis_type: Type of analysis (monthly, weekly, daily)
            
        Returns:
            Dictionary with cost data
        """
        try:
            # Determine granularity based on analysis type
            granularity = 'MONTHLY'
            if analysis_type == 'weekly':
                granularity = 'DAILY'  # AWS doesn't have weekly, so we use daily and aggregate
            elif analysis_type == 'daily':
                granularity = 'DAILY'
            
            self.logger.debug(f"Fetching {analysis_type} costs for {start_date} to {end_date}")
            
            response = ce_client.get_cost_and_usage(
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
            self.logger.error(f"Error fetching {analysis_type} costs for {start_date}-{end_date}: {e}")
            return {
                'services': {},
                'total_cost': 0,
                'period': f"{start_date} to {end_date}",
                'service_count': 0,
                'analysis_type': analysis_type,
                'error': str(e)
            }
    
    def _get_date_ranges(self, periods: int, analysis_type: str = "monthly") -> List[Dict[str, str]]:
        """
        Generate date ranges for the last N periods (months/weeks/days).
        
        Args:
            periods: Number of periods to analyze
            analysis_type: Type of analysis (monthly, weekly, daily)
            
        Returns:
            List of date range dictionaries
        """
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
    
    def aggregate_multi_account_data(self, client_data: ClientCostData) -> Dict[str, Any]:
        """
        Aggregate cost data from multiple accounts into a unified view.
        
        Args:
            client_data: ClientCostData object with account data
            
        Returns:
            Dictionary with aggregated data compatible with existing report generators
        """
        try:
            # Get the aggregated data
            aggregated = client_data.aggregated_data
            
            # Create periods data by aggregating across accounts
            periods_data = []
            if client_data.accounts_data:
                # Determine the number of periods from the first account
                first_account = client_data.accounts_data[0]
                periods_count = len(first_account['cost_data'].get('periods_data', []))
                
                # Aggregate each period across all accounts
                for period_idx in range(periods_count):
                    period_services = {}
                    period_total = 0.0
                    period_info = None
                    
                    for account_data in client_data.accounts_data:
                        account_periods = account_data['cost_data'].get('periods_data', [])
                        if period_idx < len(account_periods):
                            period = account_periods[period_idx]
                            
                            # Store period info from first account
                            if period_info is None:
                                period_info = {
                                    'name': period.get('name'),
                                    'start_date': period.get('start_date'),
                                    'end_date': period.get('end_date'),
                                    'period_key': period.get('period_key'),
                                    'analysis_type': period.get('analysis_type')
                                }
                            
                            # Aggregate services
                            for service, cost in period.get('services', {}).items():
                                if service in period_services:
                                    period_services[service] += cost
                                else:
                                    period_services[service] = cost
                                period_total += cost
                    
                    if period_info:
                        periods_data.append({
                            **period_info,
                            'services': period_services,
                            'total_cost': period_total,
                            'service_count': len(period_services)
                        })
            
            # Create the final aggregated structure
            result = {
                'client_id': client_data.client_id,
                'client_name': client_data.client_name,
                'periods_data': periods_data,
                'months_data': periods_data,  # For backward compatibility
                'services': aggregated.get('services', {}),
                'total_cost': aggregated.get('total_cost', 0),
                'service_count': aggregated.get('service_count', 0),
                'account_count': aggregated.get('account_count', 0),
                'accounts_data': client_data.accounts_data,
                'errors': client_data.errors,
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'collection_time': aggregated.get('collection_time'),
                    'analysis_type': periods_data[0].get('analysis_type', 'monthly') if periods_data else 'monthly',
                    'periods_analyzed': len(periods_data),
                    'months_analyzed': len(periods_data),  # For backward compatibility
                    'accounts_analyzed': client_data.account_count,
                    'total_services': client_data.service_count,
                    'has_errors': len(client_data.errors) > 0,
                    'client_config': {
                        'client_id': self.client_config.client_id,
                        'client_name': self.client_config.client_name,
                        'account_count': len(self.client_config.aws_accounts),
                        'report_config': self.client_config.report_config.to_dict()
                    }
                }
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to aggregate multi-account data for client {client_data.client_id}: {str(e)}"
            self.logger.error(error_msg)
            raise CostDataError(error_msg) from e
    
    def clear_cache(self) -> None:
        """Clear all cached sessions and clients to free memory."""
        self._session_cache.clear()
        self._client_cache.clear()
        self.logger.debug("Cleared session and client cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring."""
        return {
            'sessions_cached': len(self._session_cache),
            'clients_cached': len(self._client_cache)
        }
    
    async def collect_multiple_clients_costs(self, client_configs: List[ClientConfig], report_type: str = "monthly", periods: int = 2) -> Dict[str, ClientCostData]:
        """
        Collect cost data for multiple clients in parallel.
        
        Args:
            client_configs: List of client configurations
            report_type: Type of report (monthly, weekly, daily)
            periods: Number of periods to analyze
            
        Returns:
            Dictionary mapping client_id to ClientCostData
        """
        self.logger.info(f"Starting cost collection for {len(client_configs)} clients ({report_type})")
        
        results = {}
        
        # Process clients in parallel with limited concurrency
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(client_configs))) as executor:
            # Submit tasks for each client
            future_to_client = {}
            for client_config in client_configs:
                # Create a new agent instance for each client to avoid conflicts
                agent = LambdaCostAgent(client_config, self.max_workers, self.timeout_per_account)
                future = executor.submit(
                    self._collect_client_costs_sync,
                    agent,
                    report_type,
                    periods
                )
                future_to_client[future] = client_config
            
            # Collect results as they complete
            for future in as_completed(future_to_client, timeout=self.timeout_per_account * 10):
                client_config = future_to_client[future]
                try:
                    client_data = future.result(timeout=self.timeout_per_account * 5)
                    results[client_config.client_id] = client_data
                    
                    self.logger.info(
                        f"✅ Client {client_config.client_id}: ${client_data.total_cost:,.2f} "
                        f"({client_data.service_count} services, {client_data.account_count} accounts)"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Failed to collect costs for client {client_config.client_id}: {str(e)}")
                    # Create empty result with error
                    error_data = ClientCostData(client_config.client_id, client_config.client_name)
                    error_data.add_error(f"Cost collection failed: {str(e)}")
                    error_data.finalize()
                    results[client_config.client_id] = error_data
        
        self.logger.info(f"Completed cost collection for {len(results)} clients")
        return results
    
    def _collect_client_costs_sync(self, agent: 'LambdaCostAgent', report_type: str, periods: int) -> ClientCostData:
        """
        Synchronous wrapper for collecting client costs (for use with ThreadPoolExecutor).
        
        Args:
            agent: LambdaCostAgent instance
            report_type: Type of report
            periods: Number of periods to analyze
            
        Returns:
            ClientCostData object
        """
        return asyncio.run(agent.collect_client_costs(report_type, periods))
    
    def validate_account_access(self, account_config: AccountConfig) -> Tuple[bool, Optional[str]]:
        """
        Validate access to a single AWS account.
        
        Args:
            account_config: Account configuration to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            session = self.create_session_for_account(account_config)
            
            # Test Cost Explorer access
            ce_client = session.client('ce', region_name='us-east-1')
            
            # Try a simple Cost Explorer call
            today = datetime.now()
            yesterday = today - timedelta(days=1)
            
            ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': yesterday.strftime('%Y-%m-%d'),
                    'End': today.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost']
            )
            
            self.logger.info(f"Successfully validated access to account {account_config.account_id}")
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to validate access to account {account_config.account_id}: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def validate_all_accounts_access(self) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        Validate access to all accounts in the client configuration.
        
        Returns:
            Dictionary mapping account_id to (is_valid, error_message)
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit validation tasks for each account
            future_to_account = {}
            for account in self.client_config.aws_accounts:
                future = executor.submit(self.validate_account_access, account)
                future_to_account[future] = account
            
            # Collect results
            for future in as_completed(future_to_account, timeout=self.timeout_per_account):
                account = future_to_account[future]
                try:
                    is_valid, error_msg = future.result(timeout=self.timeout_per_account)
                    results[account.account_id] = (is_valid, error_msg)
                except Exception as e:
                    results[account.account_id] = (False, f"Validation timeout or error: {str(e)}")
        
        return results
    
    def get_account_cost_summary(self, account_config: AccountConfig, days: int = 30) -> Dict[str, Any]:
        """
        Get a quick cost summary for a single account over the last N days.
        
        Args:
            account_config: Account configuration
            days: Number of days to analyze
            
        Returns:
            Dictionary with cost summary
        """
        try:
            ce_client = self.get_cost_explorer_client(account_config)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            response = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )
            
            services = {}
            total_cost = 0
            
            if response['ResultsByTime']:
                for time_period in response['ResultsByTime']:
                    for group in time_period['Groups']:
                        service_name = group['Keys'][0]
                        cost = float(group['Metrics']['UnblendedCost']['Amount'])
                        
                        if cost > 0:
                            services[service_name] = cost
                            total_cost += cost
            
            # Sort services by cost
            sorted_services = dict(sorted(services.items(), key=lambda x: x[1], reverse=True))
            
            return {
                'account_id': account_config.account_id,
                'account_name': account_config.account_name,
                'period_days': days,
                'total_cost': total_cost,
                'service_count': len(services),
                'top_services': dict(list(sorted_services.items())[:10]),
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cost summary for account {account_config.account_id}: {e}")
            return {
                'account_id': account_config.account_id,
                'account_name': account_config.account_name,
                'period_days': days,
                'total_cost': 0,
                'service_count': 0,
                'top_services': {},
                'error': str(e)
            }
    
    def optimize_for_lambda_constraints(self, lambda_context=None) -> None:
        """
        Apply Lambda-specific optimizations.
        
        Args:
            lambda_context: Lambda context object for timeout information
        """
        # Adjust timeouts based on Lambda context
        if lambda_context and hasattr(lambda_context, 'get_remaining_time_in_millis'):
            remaining_ms = lambda_context.get_remaining_time_in_millis()
            remaining_seconds = remaining_ms // 1000
            
            # Reserve 30 seconds for cleanup
            available_time = max(30, remaining_seconds - 30)
            
            # Adjust per-account timeout
            account_count = len(self.client_config.aws_accounts)
            if account_count > 0:
                self.timeout_per_account = min(
                    self.timeout_per_account,
                    available_time // account_count
                )
            
            self.logger.info(f"Optimized timeouts: {remaining_seconds}s remaining, {self.timeout_per_account}s per account")
        
        # Optimize worker count based on account count
        optimal_workers = min(self.max_workers, len(self.client_config.aws_accounts), 5)
        if optimal_workers != self.max_workers:
            self.max_workers = optimal_workers
            self.logger.info(f"Optimized worker count to {self.max_workers}")
    
    def cleanup_resources(self) -> None:
        """Clean up resources to free memory."""
        import gc
        
        # Clear caches
        self.clear_cache()
        
        # Force garbage collection
        collected = gc.collect()
        
        self.logger.debug(f"Resource cleanup: {collected} objects collected")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current memory usage statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent(),
                'cache_stats': self.get_cache_stats()
            }
        except ImportError:
            return {
                'rss_mb': 0,
                'vms_mb': 0,
                'percent': 0,
                'cache_stats': self.get_cache_stats(),
                'note': 'psutil not available'
            }
    
    def should_continue_processing(self, lambda_context=None, buffer_seconds: int = 60) -> bool:
        """
        Check if there's enough time to continue processing.
        
        Args:
            lambda_context: Lambda context object
            buffer_seconds: Buffer time to reserve
            
        Returns:
            True if processing should continue
        """
        if lambda_context and hasattr(lambda_context, 'get_remaining_time_in_millis'):
            remaining_ms = lambda_context.get_remaining_time_in_millis()
            remaining_seconds = remaining_ms // 1000
            
            should_continue = remaining_seconds > buffer_seconds
            
            if not should_continue:
                self.logger.warning(f"Stopping processing: only {remaining_seconds}s remaining")
            
            return should_continue
        
        return True  # Continue if no context available
    
    def process_with_lambda_optimization(self, 
                                       report_type: str = "monthly", 
                                       periods: int = 2,
                                       lambda_context=None) -> ClientCostData:
        """
        Process cost collection with Lambda optimizations.
        
        Args:
            report_type: Type of report
            periods: Number of periods to analyze
            lambda_context: Lambda context object
            
        Returns:
            ClientCostData object
        """
        # Apply optimizations
        self.optimize_for_lambda_constraints(lambda_context)
        
        try:
            # Collect costs with timeout monitoring
            client_data = asyncio.run(self._collect_costs_with_monitoring(
                report_type, periods, lambda_context
            ))
            
            return client_data
            
        finally:
            # Always cleanup resources
            self.cleanup_resources()
    
    async def _collect_costs_with_monitoring(self, 
                                           report_type: str, 
                                           periods: int,
                                           lambda_context=None) -> ClientCostData:
        """
        Collect costs with timeout and memory monitoring.
        
        Args:
            report_type: Type of report
            periods: Number of periods
            lambda_context: Lambda context
            
        Returns:
            ClientCostData object
        """
        self.logger.info(f"Starting monitored cost collection for client {self.client_config.client_id}")
        
        client_data = ClientCostData(self.client_config.client_id, self.client_config.client_name)
        
        # Generate date ranges
        date_ranges = self._get_date_ranges(periods, report_type)
        
        # Process accounts with monitoring
        processed_accounts = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks for accounts
            future_to_account = {}
            for account in self.client_config.aws_accounts:
                if not self.should_continue_processing(lambda_context, 90):
                    self.logger.warning("Timeout approaching, stopping account submission")
                    break
                
                future = executor.submit(
                    self._collect_account_costs_sync,
                    account,
                    date_ranges,
                    report_type
                )
                future_to_account[future] = account
            
            # Collect results with timeout monitoring
            for future in as_completed(future_to_account, timeout=self.timeout_per_account * 2):
                if not self.should_continue_processing(lambda_context, 60):
                    self.logger.warning("Timeout approaching, stopping result collection")
                    break
                
                account = future_to_account[future]
                try:
                    account_cost_data = future.result(timeout=self.timeout_per_account)
                    client_data.add_account_data(account.account_id, account_cost_data)
                    processed_accounts += 1
                    
                    self.logger.info(
                        f"✅ Account {account.account_id} ({processed_accounts}/{len(self.client_config.aws_accounts)}): "
                        f"${account_cost_data.get('total_cost', 0):,.2f}"
                    )
                    
                    # Periodic cleanup
                    if processed_accounts % 3 == 0:
                        self.cleanup_resources()
                    
                except Exception as e:
                    error_msg = f"Failed to collect costs for account {account.account_id}: {str(e)}"
                    self.logger.error(error_msg)
                    client_data.add_error(error_msg)
        
        # Finalize data
        client_data.finalize()
        
        self.logger.info(
            f"Completed monitored collection: {processed_accounts} accounts, "
            f"${client_data.total_cost:,.2f} total"
        )
        
        return client_data