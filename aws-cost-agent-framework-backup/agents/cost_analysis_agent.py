"""
Cost Analysis Agent - Main agent for AWS cost analysis
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
from .base_agent import BaseAgent, AgentResult
from tools.aws_cost_tools import AWSCostTools
from tools.report_generator import ReportGenerator
from tools.chart_generator import ChartGenerator
from tools.email_report_generator import EmailReportGenerator

class CostAnalysisAgent(BaseAgent):
    """
    Main agent for AWS cost analysis
    
    Responsibilities:
    - Orchestrate cost data collection
    - Perform analysis across multiple months
    - Generate comprehensive reports
    - Handle errors and edge cases
    """
    
    def __init__(self, settings):
        super().__init__(settings, "CostAnalysisAgent")
        
        # Initialize tools
        self.cost_tools = AWSCostTools(settings.aws)
        self.report_generator = ReportGenerator(settings.report)
        self.chart_generator = ChartGenerator(settings.report.output_dir)
        self.email_generator = EmailReportGenerator(settings.report)
        
        # Store settings for easy access
        self.analysis_config = settings.analysis
        self.report_config = settings.report
    
    async def _execute_core(self) -> AgentResult:
        """Core execution logic for cost analysis"""
        
        try:
            # Step 1: Get date ranges
            analysis_type = self.analysis_config.analysis_type
            periods = self.analysis_config.periods_to_analyze
            
            self.logger.info(f"📅 Calculating date ranges for {periods} {analysis_type} periods")
            date_ranges = self.cost_tools.get_date_ranges(periods, analysis_type)
            
            # Step 1.5: Analyze forecast if monthly analysis
            forecast_analysis = {}
            if analysis_type == "monthly":
                self.logger.info("🔮 Analyzing current month forecast vs spending...")
                forecast_analysis = await self.cost_tools.analyze_forecast_vs_current()
            
            # Step 2: Collect cost data for each period
            self.logger.info(f"💰 Collecting {analysis_type} cost data...")
            periods_data = await self._collect_period_data(date_ranges)
            
            if not periods_data:
                return self._create_error_result("No cost data collected")
            
            # Step 3: Collect account data if enabled
            accounts_data = []
            if self.analysis_config.include_account_analysis:
                self.logger.info(f"🏢 Collecting {analysis_type} account cost data...")
                accounts_data = await self._collect_period_account_data(date_ranges)
            
            # Step 4: Analyze cost changes
            self.logger.info("🔍 Analyzing cost changes...")
            changes = self._analyze_changes(periods_data)
            
            # Step 5: Analyze account changes if enabled
            account_changes = {}
            if self.analysis_config.include_account_analysis and accounts_data:
                self.logger.info("🔍 Analyzing account changes...")
                account_changes = self._analyze_account_changes(accounts_data)
            
            # Step 6: Get top services and accounts
            self.logger.info("🔝 Identifying top services...")
            top_services = self.cost_tools.get_top_services(
                periods_data[0], 
                self.analysis_config.top_services_count
            )
            
            top_accounts = []
            if self.analysis_config.include_account_analysis and accounts_data:
                self.logger.info("🔝 Identifying top accounts...")
                top_accounts = self.cost_tools.get_top_accounts(
                    accounts_data[0],
                    self.analysis_config.top_accounts_count
                )
            
            # Step 7: Prepare analysis data
            analysis_data = {
                'periods_data': periods_data,
                'months_data': periods_data,  # For backward compatibility
                'accounts_data': accounts_data,
                'changes': changes,
                'account_changes': account_changes,
                'top_services': top_services,
                'top_accounts': top_accounts,
                'forecast_analysis': forecast_analysis,  # New forecast data
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'analysis_type': analysis_type,
                    'periods_analyzed': len(periods_data),
                    'months_analyzed': len(periods_data),  # For backward compatibility
                    'accounts_analyzed': len(accounts_data) if accounts_data else 0,
                    'total_services': len(set().union(*[p['services'].keys() for p in periods_data])),
                    'total_accounts': len(set().union(*[a['accounts'].keys() for a in accounts_data])) if accounts_data else 0,
                    'has_forecast': bool(forecast_analysis and not forecast_analysis.get('error')),
                    'analysis_config': {
                        'analysis_type': analysis_type,
                        'periods_to_analyze': periods,
                        'months_to_analyze': self.analysis_config.months_to_analyze,  # Legacy
                        'min_cost_threshold': self.analysis_config.min_cost_threshold,
                        'top_services_count': self.analysis_config.top_services_count,
                        'top_accounts_count': self.analysis_config.top_accounts_count,
                        'include_account_analysis': self.analysis_config.include_account_analysis
                    }
                }
            }
            
            # Step 8: Generate charts
            chart_paths = []
            if self.analysis_config.include_charts:
                self.logger.info("📊 Generating interactive charts...")
                
                # Main comparison chart
                chart_path = self.chart_generator.generate_monthly_comparison_chart(
                    periods_data, changes, analysis_type
                )
                if chart_path:
                    chart_paths.append(chart_path)
                
                # Forecast chart (if available)
                if forecast_analysis and not forecast_analysis.get('error'):
                    forecast_chart_path = self.chart_generator.generate_forecast_chart(forecast_analysis)
                    if forecast_chart_path:
                        chart_paths.append(forecast_chart_path)
                
                # Service trends chart
                service_trends_path = self.chart_generator.generate_service_trend_chart(periods_data)
                if service_trends_path:
                    chart_paths.append(service_trends_path)
            
            # Step 9: Generate report
            self.logger.info("📄 Generating report...")
            report_path = self.report_generator.generate_html_report(analysis_data)
            
            # Step 10: Generate email report
            self.logger.info("📧 Generating email report...")
            email_template_path = self.email_generator.save_email_template(analysis_data)
            
            # Step 11: Return success result
            return self._create_success_result(
                data=analysis_data,
                report_path=report_path,
                chart_paths=chart_paths,
                email_template_path=email_template_path,
                metadata=analysis_data['metadata']
            )
            
        except Exception as e:
            self.logger.error(f"Error in cost analysis: {e}")
            return self._create_error_result(f"Analysis failed: {str(e)}")
    
    async def _collect_period_data(self, date_ranges: List[Dict]) -> List[Dict]:
        """Collect cost data for all periods (months/weeks/days)"""
        periods_data = []
        
        # Create tasks for concurrent data collection
        tasks = []
        for period_info in date_ranges:
            analysis_type = period_info.get('analysis_type', 'monthly')
            task = self.cost_tools.get_period_costs(
                period_info['start_date'],
                period_info['end_date'],
                analysis_type
            )
            tasks.append((period_info, task))
        
        # Execute tasks concurrently
        for period_info, task in tasks:
            try:
                self.logger.debug(f"Collecting data for {period_info['name']}")
                cost_data = await task
                
                # Add period metadata
                cost_data.update({
                    'name': period_info['name'],
                    'start_date': period_info['start_date'],
                    'end_date': period_info['end_date'],
                    'period_key': period_info['period_key'],
                    'analysis_type': period_info.get('analysis_type', 'monthly')
                })
                
                periods_data.append(cost_data)
                
                period_type = period_info.get('analysis_type', 'monthly').title()
                self.logger.info(
                    f"✅ {period_info['name']}: ${cost_data['total_cost']:,.2f} "
                    f"({cost_data['service_count']} services) [{period_type}]"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to collect data for {period_info['name']}: {e}")
                continue
        
        return periods_data
    
    async def _collect_monthly_data(self, date_ranges: List[Dict]) -> List[Dict]:
        """Legacy method for backward compatibility"""
        return await self._collect_period_data(date_ranges)
    
    async def _collect_period_account_data(self, date_ranges: List[Dict]) -> List[Dict]:
        """Collect account cost data for all periods (months/weeks/days)"""
        accounts_data = []
        
        # Create tasks for concurrent data collection
        tasks = []
        for period_info in date_ranges:
            analysis_type = period_info.get('analysis_type', 'monthly')
            task = self.cost_tools.get_period_costs_by_account(
                period_info['start_date'],
                period_info['end_date'],
                analysis_type
            )
            tasks.append((period_info, task))
        
        # Execute tasks concurrently
        for period_info, task in tasks:
            try:
                self.logger.debug(f"Collecting account data for {period_info['name']}")
                cost_data = await task
                
                # Add period metadata
                cost_data.update({
                    'name': period_info['name'],
                    'start_date': period_info['start_date'],
                    'end_date': period_info['end_date'],
                    'period_key': period_info['period_key'],
                    'analysis_type': period_info.get('analysis_type', 'monthly')
                })
                
                accounts_data.append(cost_data)
                
                period_type = period_info.get('analysis_type', 'monthly').title()
                self.logger.info(
                    f"✅ {period_info['name']} accounts: ${cost_data['total_cost']:,.2f} "
                    f"({cost_data['account_count']} accounts) [{period_type}]"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to collect account data for {period_info['name']}: {e}")
                continue
        
        return accounts_data
    
    async def _collect_monthly_account_data(self, date_ranges: List[Dict]) -> List[Dict]:
        """Legacy method for backward compatibility"""
        return await self._collect_period_account_data(date_ranges)
    
    def _analyze_changes(self, months_data: List[Dict]) -> Dict[str, Any]:
        """Analyze changes between months"""
        if len(months_data) < 2:
            self.logger.warning("Not enough data for change analysis")
            return {
                'total_change': 0,
                'total_percent_change': 0,
                'service_changes': {},
                'new_services': [],
                'removed_services': [],
                'current_period': months_data[0] if months_data else {},
                'previous_period': {},
                'summary': {
                    'services_analyzed': 0,
                    'services_changed': 0,
                    'services_added': 0,
                    'services_removed': 0
                }
            }
        
        # Compare most recent month with previous month
        current_month = months_data[0]
        previous_month = months_data[1]
        
        changes = self.cost_tools.analyze_cost_changes(
            current_month,
            previous_month,
            self.analysis_config.min_cost_threshold
        )
        
        # Log summary
        summary = changes['summary']
        self.logger.info(
            f"📊 Analysis summary: {summary['services_changed']} changed, "
            f"{summary['services_added']} added, {summary['services_removed']} removed"
        )
        
        return changes
    
    def _analyze_account_changes(self, accounts_data: List[Dict]) -> Dict[str, Any]:
        """Analyze account changes between months"""
        if len(accounts_data) < 2:
            self.logger.warning("Not enough account data for change analysis")
            return {
                'total_change': 0,
                'total_percent_change': 0,
                'account_changes': {},
                'new_accounts': [],
                'removed_accounts': [],
                'current_period': accounts_data[0] if accounts_data else {},
                'previous_period': {},
                'summary': {
                    'accounts_analyzed': 0,
                    'accounts_changed': 0,
                    'accounts_added': 0,
                    'accounts_removed': 0
                }
            }
        
        # Compare most recent month with previous month
        current_month = accounts_data[0]
        previous_month = accounts_data[1]
        
        changes = self.cost_tools.analyze_account_changes(
            current_month,
            previous_month,
            self.analysis_config.min_cost_threshold
        )
        
        # Log summary
        summary = changes['summary']
        self.logger.info(
            f"📊 Account analysis summary: {summary['accounts_changed']} changed, "
            f"{summary['accounts_added']} added, {summary['accounts_removed']} removed"
        )
        
        return changes
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get a quick summary of the analysis capabilities"""
        return {
            'agent_name': self.name,
            'capabilities': [
                'Multi-month cost analysis',
                'Service-level cost breakdown',
                'Change detection and analysis',
                'Top services identification',
                'New/removed services tracking',
                'HTML report generation'
            ],
            'configuration': {
                'months_analyzed': self.analysis_config.months_to_analyze,
                'min_cost_threshold': self.analysis_config.min_cost_threshold,
                'top_services_count': self.analysis_config.top_services_count,
                'aws_profile': self.cost_tools.aws_config.profile_name,
                'aws_region': self.cost_tools.aws_config.region
            }
        }
