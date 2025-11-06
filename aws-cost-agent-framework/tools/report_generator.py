"""
Report generation tools for AWS Cost Analysis
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import logging
from .asset_manager import AssetManager
from .i18n import I18n
from .ai_summary_generator import AISummaryGenerator

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate HTML reports from analysis data"""
    
    def __init__(self, report_config, ai_config=None):
        self.config = report_config
        self.ai_config = ai_config
        self.asset_manager = AssetManager()
        self.i18n = I18n(language=report_config.language)
        
        # Initialize AI generator if enabled
        self.ai_generator = None
        if ai_config and ai_config.enabled:
            try:
                self.ai_generator = AISummaryGenerator(
                    aws_profile=ai_config.aws_profile,
                    region=ai_config.region
                )
                logger.info("✅ AI Summary Generator initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize AI generator: {str(e)}")
                self.ai_generator = None
        
    def generate_html_report(self, analysis_data: Dict[str, Any]) -> str:
        """Generate comprehensive HTML report"""
        
        periods_data = analysis_data.get('periods_data', analysis_data.get('months_data', []))
        accounts_data = analysis_data.get('accounts_data', [])
        changes = analysis_data['changes']
        account_changes = analysis_data.get('account_changes', {})
        top_services = analysis_data['top_services']
        top_accounts = analysis_data.get('top_accounts', [])
        metadata = analysis_data.get('metadata', {})
        
        # Generate filename based on analysis type
        analysis_type = metadata.get('analysis_type', 'monthly')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"aws_cost_analysis_{analysis_type}_{timestamp}.html"
        filepath = self.config.output_dir / filename
        
        # Generate HTML content
        html_content = self._build_html_content(
            periods_data, accounts_data, changes, account_changes, 
            top_services, top_accounts, metadata, analysis_data
        )
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Report generated: {filepath}")
        return str(filepath)
    
    def _build_html_content(self, periods_data: List[Dict], accounts_data: List[Dict],
                           changes: Dict, account_changes: Dict, top_services: List[Dict], 
                           top_accounts: List[Dict], metadata: Dict, analysis_data: Dict) -> str:
        """Build the complete HTML content"""
        
        analysis_type = metadata.get('analysis_type', 'monthly')
        
        forecast_analysis = analysis_data.get('forecast_analysis', {})
        
        return f"""<!DOCTYPE html>
<html lang="{self.i18n.language[:2]}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.i18n.get_analysis_title(analysis_type)} - CostHub</title>
    {self._get_css_styles()}
</head>
<body>
    <div class="container">
        {self._build_header(metadata)}
        {self._build_ai_summary(analysis_data) if self.ai_generator and self.ai_config.include_summary else ''}
        {self._build_forecast_alert(forecast_analysis) if forecast_analysis and not forecast_analysis.get('error') else ''}
        {self._build_executive_summary(changes, analysis_type)}
        {self._build_forecast_analysis(forecast_analysis) if forecast_analysis and not forecast_analysis.get('error') else ''}
        {self._build_periods_overview(periods_data, analysis_type)}
        {self._build_top_services_section(top_services, changes)}
        {self._build_changes_section(changes, analysis_type)}
        {self._build_new_services_section(changes)}
        {self._build_ai_recommendations(analysis_data) if self.ai_generator and self.ai_config.include_recommendations else ''}
        {self._build_footer(metadata)}
    </div>
</body>
</html>"""
    
    def _get_css_styles(self) -> str:
        """Get CSS styles for the report with CostHub branding"""
        return """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f1f5f9; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 25px rgba(30,58,138,0.15); }
        .email-container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; font-family: Arial, sans-serif; }
        
        /* CostHub Branding */
        .costhub-header { background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 25px; border-radius: 12px 12px 0 0; margin: -30px -30px 30px -30px; text-align: center; }
        .costhub-logo-container { margin-bottom: 12px; }
        .costhub-logo-container img { max-width: 280px; height: auto; filter: brightness(0) invert(1); }
        .costhub-logo { font-size: 28px; font-weight: bold; margin-bottom: 8px; }
        .costhub-tagline { font-size: 14px; opacity: 0.9; }
        
        h1 { color: #1e40af; text-align: center; border-bottom: 3px solid #fbbf24; padding-bottom: 15px; margin-bottom: 25px; }
        h2 { color: #1e40af; border-left: 5px solid #fbbf24; padding-left: 20px; margin-top: 35px; background: #f8fafc; padding: 15px 20px; border-radius: 8px; }
        h3 { color: #1e40af; margin-top: 25px; }
        
        /* Summary Section */
        .summary { background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 25px; border-radius: 12px; margin: 25px 0; text-align: center; box-shadow: 0 4px 15px rgba(30,64,175,0.3); }
        .summary h3 { color: white; margin-top: 0; }
        
        /* Cards and Grids */
        .month-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin: 25px 0; }
        .month-card { background: linear-gradient(135deg, #eff6ff, #dbeafe); padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid #fbbf24; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .month-card h4 { color: #1e40af; margin-top: 0; }
        
        .metric-card { background: linear-gradient(135deg, #fef3c7, #fde68a); padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 5px solid #1e40af; }
        
        /* Tables */
        table { width: 100%; border-collapse: collapse; margin: 25px 0; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 15px rgba(0,0,0,0.1); }
        th, td { border: none; padding: 15px 12px; text-align: left; }
        th { background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; font-weight: 600; }
        tr:nth-child(even) { background-color: #f8fafc; }
        tr:hover { background-color: #eff6ff; }
        
        /* Status Colors */
        .increase { color: #dc2626; font-weight: bold; }
        .decrease { color: #059669; font-weight: bold; }
        .stable { color: #6b7280; }
        
        /* Badges */
        .badge { display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 11px; font-weight: bold; text-transform: uppercase; }
        .badge-success { background: #d1fae5; color: #065f46; }
        .badge-danger { background: #fee2e2; color: #991b1b; }
        .badge-warning { background: #fef3c7; color: #92400e; }
        .badge-info { background: #dbeafe; color: #1e40af; }
        
        /* New Services */
        .new-service { background: linear-gradient(135deg, #dbeafe, #bfdbfe); padding: 15px; margin: 8px 0; border-radius: 8px; border-left: 5px solid #fbbf24; }
        
        /* Forecast Alerts */
        .forecast-alert { padding: 25px; border-radius: 12px; margin: 25px 0; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        .forecast-alert.high { background: linear-gradient(135deg, #dc2626, #ef4444); color: white; }
        .forecast-alert.warning { background: linear-gradient(135deg, #f59e0b, #fbbf24); color: white; }
        .forecast-alert.good { background: linear-gradient(135deg, #059669, #10b981); color: white; }
        
        .forecast-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 25px; margin: 25px 0; }
        .forecast-card { background: #f8fafc; padding: 25px; border-radius: 12px; border-left: 5px solid #fbbf24; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .forecast-card.alert { border-left-color: #dc2626; background: #fef2f2; }
        .forecast-card h4 { color: #1e40af; margin-top: 0; }
        
        .cost-driver { background: linear-gradient(135deg, #fef3c7, #fde68a); padding: 20px; margin: 15px 0; border-radius: 10px; border-left: 5px solid #1e40af; }
        .cost-driver.high { border-left-color: #dc2626; background: linear-gradient(135deg, #fee2e2, #fecaca); }
        
        /* AI Sections */
        .ai-summary { background: linear-gradient(135deg, #f0f9ff, #e0f2fe); padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 5px solid #0ea5e9; box-shadow: 0 4px 15px rgba(14,165,233,0.2); }
        .ai-summary h2 { color: #0369a1; margin-top: 0; }
        .ai-content { font-size: 16px; line-height: 1.7; color: #374151; }
        .ai-recommendations { background: linear-gradient(135deg, #f0fdf4, #dcfce7); padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 5px solid #22c55e; box-shadow: 0 4px 15px rgba(34,197,94,0.2); }
        .ai-recommendations h2 { color: #15803d; margin-top: 0; }
        
        /* Footer */
        .footer { text-align: center; margin-top: 40px; padding-top: 25px; border-top: 2px solid #e5e7eb; color: #6b7280; }
        .costhub-badge { background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 8px 16px; border-radius: 25px; font-size: 12px; font-weight: bold; }
        
        /* Email Specific Styles */
        .email-header { background: #1e40af; color: white; padding: 20px; text-align: center; }
        .email-summary { background: #f8fafc; padding: 20px; border-left: 5px solid #fbbf24; margin: 20px 0; }
        .email-cta { background: #fbbf24; color: #1e40af; padding: 15px 30px; border-radius: 8px; text-decoration: none; font-weight: bold; display: inline-block; margin: 20px 0; }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container, .email-container { padding: 15px; }
            .month-grid, .forecast-grid { grid-template-columns: 1fr; }
            table { font-size: 14px; }
            th, td { padding: 10px 8px; }
        }
    </style>"""
    
    def _build_ai_summary(self, analysis_data: Dict[str, Any]) -> str:
        """Build AI-powered summary section"""
        try:
            ai_summary = self.ai_generator.generate_cost_summary(analysis_data)
            
            if not ai_summary:
                return ""
            
            return f"""
            <div class="ai-summary">
                <h2>🤖 {self.i18n.t('ai_insights')}</h2>
                <div class="ai-content">
                    <p>{ai_summary}</p>
                </div>
            </div>"""
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {str(e)}")
            return ""
    
    def _build_ai_recommendations(self, analysis_data: Dict[str, Any]) -> str:
        """Build AI-powered recommendations section"""
        try:
            recommendations = self.ai_generator.generate_optimization_recommendations(analysis_data)
            
            if not recommendations:
                return ""
            
            return f"""
            <div class="ai-recommendations">
                <h2>💡 Recomendações de Otimização</h2>
                <div class="ai-content">
                    <div style="white-space: pre-line;">{recommendations}</div>
                </div>
            </div>"""
            
        except Exception as e:
            logger.error(f"Error generating AI recommendations: {str(e)}")
            return ""
    
    def _build_header(self, metadata: Dict) -> str:
        """Build report header with CostHub branding"""
        analysis_type = metadata.get('analysis_type', 'monthly')
        
        # Get logo HTML
        logo_html = self.asset_manager.get_logo_html(
            width="200px", 
            height="auto",
            alt_text="CostHub"
        )
        
        return f"""
        <div class="costhub-header">
            <div class="costhub-logo-container">
                {logo_html}
            </div>
            <div class="costhub-tagline">{self.i18n.t('cost_optimization_platform')}</div>
        </div>
        <h1>{self.i18n.get_analysis_title(analysis_type)}</h1>
        <div style="text-align: center; margin-bottom: 25px;">
            <span class="costhub-badge">{self.i18n.t('generated_on')} {datetime.now().strftime('%d/%m/%Y às %H:%M')}</span>
        </div>"""
        """Build report header with CostHub branding"""
        analysis_type = metadata.get('analysis_type', 'monthly').title()
        
        # Get logo HTML
        logo_html = self.asset_manager.get_logo_html(
            width="200px", 
            height="auto",
            alt_text="CostHub"
        )
        
        return f"""
        <div class="costhub-header">
            <div class="costhub-logo-container">
                {logo_html}
            </div>
            <div class="costhub-tagline">AWS Cost Analysis & Optimization Platform</div>
        </div>
        <h1>{analysis_type} Cost Analysis Report</h1>
        <div style="text-align: center; margin-bottom: 25px;">
            <span class="costhub-badge">Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}</span>
        </div>"""

    def _build_executive_summary(self, changes: Dict, analysis_type: str = "monthly") -> str:
        """Build executive summary section"""
        current = changes['current_period']
        previous = changes['previous_period']
        
        trend_icon = '📈' if changes['total_change'] > 0 else '📉' if changes['total_change'] < 0 else '➡️'
        
        return f"""
        <div class="summary">
            <h3>📊 {self.i18n.t('executive_summary')}</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 15px;">
                <div>
                    <h4>{self.i18n.get_period_label(analysis_type, is_previous=True)}</h4>
                    <p style="font-size: 24px; margin: 5px 0;">${previous['total_cost']:,.2f}</p>
                </div>
                <div>
                    <h4>{self.i18n.get_period_label(analysis_type, is_previous=False)}</h4>
                    <p style="font-size: 24px; margin: 5px 0;">${current['total_cost']:,.2f}</p>
                </div>
                <div>
                    <h4>{self.i18n.t('change')}</h4>
                    <p style="font-size: 24px; margin: 5px 0;">
                        {trend_icon} ${abs(changes['total_change']):,.2f}<br>
                        <span style="font-size: 18px;">({changes['total_percent_change']:+.1f}%)</span>
                    </p>
                </div>
            </div>
        </div>"""
    
    def _build_periods_overview(self, periods_data: List[Dict], analysis_type: str = "monthly") -> str:
        """Build periods overview section"""
        
        html = f"""
        <h2>{self.i18n.get_overview_title(analysis_type)}</h2>
        <div class="month-grid">"""
        
        for period in periods_data:
            html += f"""
            <div class="month-card">
                <h4>{period['name']}</h4>
                <p style="font-size: 20px; color: #2563eb; margin: 10px 0;">
                    <strong>${period['total_cost']:,.2f}</strong>
                </p>
                <p style="font-size: 14px; color: #6b7280;">
                    {period['service_count']} {self.i18n.t('services')}
                </p>
            </div>"""
        
        html += "</div>"
        return html
    
    def _build_monthly_overview(self, months_data: List[Dict]) -> str:
        """Legacy method for backward compatibility"""
        return self._build_periods_overview(months_data, "monthly")
    
    def _build_top_services_section(self, top_services: List[Dict], changes: Dict) -> str:
        """Build top services section"""
        html = f"""
        <h2>🔝 {self.i18n.t('top_services_by_cost')}</h2>
        <table>
            <thead>
                <tr><th>{self.i18n.t('service')}</th><th>{self.i18n.t('current_cost')}</th><th>{self.i18n.t('percent_of_total')}</th><th>{self.i18n.t('status')}</th></tr>
            </thead>
            <tbody>"""
        
        for service in top_services:
            # Check if service has changes
            service_name = service['service']
            status_badge = ""
            
            if service_name in changes['service_changes']:
                change_data = changes['service_changes'][service_name]
                if change_data['change'] > 0:
                    status_badge = f'<span class="badge badge-danger">+{change_data["percent_change"]:.1f}%</span>'
                else:
                    status_badge = f'<span class="badge badge-success">{change_data["percent_change"]:.1f}%</span>'
            elif service_name in [s['service'] for s in changes['new_services']]:
                status_badge = f'<span class="badge badge-info">{self.i18n.t("new")}</span>'
            else:
                status_badge = f'<span class="badge badge-success">{self.i18n.t("stable")}</span>'
            
            html += f"""
                <tr>
                    <td>{service_name}</td>
                    <td>${service['cost']:,.2f}</td>
                    <td>{service['percentage']:.1f}%</td>
                    <td>{status_badge}</td>
                </tr>"""
        
        html += "</tbody></table>"
        return html
    
    def _build_changes_section(self, changes: Dict, analysis_type: str = "monthly") -> str:
        """Build service changes section"""
        if not changes['service_changes']:
            return ""
        
        html = f"""
        <h2>{self.i18n.get_changes_title(analysis_type)}</h2>
        <table>
            <thead>
                <tr><th>{self.i18n.t('service')}</th><th>{self.i18n.t('previous_cost')}</th><th>{self.i18n.t('current_cost')}</th><th>{self.i18n.t('change')}</th><th>%</th></tr>
            </thead>
            <tbody>"""
        
        # Show top 15 changes
        for service, data in list(changes['service_changes'].items())[:15]:
            change_class = 'increase' if data['change'] > 0 else 'decrease'
            html += f"""
                <tr>
                    <td>{service}</td>
                    <td>${data['previous']:,.2f}</td>
                    <td>${data['current']:,.2f}</td>
                    <td class="{change_class}">${data['change']:+,.2f}</td>
                    <td class="{change_class}">{data['percent_change']:+.1f}%</td>
                </tr>"""
        
        html += "</tbody></table>"
        return html
    
    def _build_new_services_section(self, changes: Dict) -> str:
        """Build new services section"""
        if not changes['new_services']:
            return ""
        
        html = f"<h2>🆕 {self.i18n.t('new_services')}</h2>"
        
        for service in changes['new_services'][:10]:
            html += f"""
            <div class="new-service">
                <strong>{service['service']}</strong>: ${service['cost']:,.2f}
            </div>"""
        
        return html
    
    def _build_top_accounts_section(self, top_accounts: List[Dict], account_changes: Dict) -> str:
        """Build top accounts section"""
        if not top_accounts:
            return ""
            
        html = """
        <h2>🔝 Top Accounts by Cost</h2>
        <table>
            <thead>
                <tr><th>Account ID</th><th>Current Cost</th><th>% of Total</th><th>Status</th></tr>
            </thead>
            <tbody>"""
        
        for account in top_accounts:
            # Check if account has changes
            account_id = account['account_id']
            status_badge = ""
            
            if account_id in account_changes.get('account_changes', {}):
                change_data = account_changes['account_changes'][account_id]
                if change_data['change'] > 0:
                    status_badge = f'<span class="badge badge-danger">+{change_data["percent_change"]:.1f}%</span>'
                else:
                    status_badge = f'<span class="badge badge-success">{change_data["percent_change"]:.1f}%</span>'
            elif account_id in [a['account_id'] for a in account_changes.get('new_accounts', [])]:
                status_badge = '<span class="badge badge-info">NEW</span>'
            else:
                status_badge = '<span class="badge badge-success">Stable</span>'
            
            html += f"""
                <tr>
                    <td>{account_id}</td>
                    <td>${account['cost']:,.2f}</td>
                    <td>{account['percentage']:.1f}%</td>
                    <td>{status_badge}</td>
                </tr>"""
        
        html += "</tbody></table>"
        return html
    
    def _build_account_changes_section(self, account_changes: Dict, analysis_type: str = "monthly") -> str:
        """Build account changes section"""
        if not account_changes.get('account_changes'):
            return ""
        
        period_label = {
            'monthly': 'Monthly',
            'weekly': 'Weekly',
            'daily': 'Daily'
        }.get(analysis_type, 'Period')
        
        html = f"""
        <h2>📈 Main {period_label} Account Cost Changes</h2>
        <table>
            <thead>
                <tr><th>Account ID</th><th>Previous</th><th>Current</th><th>Change</th><th>%</th></tr>
            </thead>
            <tbody>"""
        
        # Show top 15 changes
        for account_id, data in list(account_changes['account_changes'].items())[:15]:
            change_class = 'increase' if data['change'] > 0 else 'decrease'
            html += f"""
                <tr>
                    <td>{account_id}</td>
                    <td>${data['previous']:,.2f}</td>
                    <td>${data['current']:,.2f}</td>
                    <td class="{change_class}">${data['change']:+,.2f}</td>
                    <td class="{change_class}">{data['percent_change']:+.1f}%</td>
                </tr>"""
        
        html += "</tbody></table>"
        return html
    
    def _build_new_accounts_section(self, account_changes: Dict) -> str:
        """Build new accounts section"""
        if not account_changes.get('new_accounts'):
            return ""
        
        html = "<h2>🆕 New Accounts</h2>"
        
        for account in account_changes['new_accounts'][:10]:
            html += f"""
            <div class="new-service">
                <strong>Account {account['account_id']}</strong>: ${account['cost']:,.2f}
            </div>"""
        
        return html
    
    def _build_forecast_alert(self, forecast_analysis: Dict) -> str:
        """Build forecast alert section"""
        if not forecast_analysis or forecast_analysis.get('error'):
            return ""
        
        summary = forecast_analysis.get('summary', {})
        forecast_percent = summary.get('forecast_increase_percent', 0)
        
        # Determine alert level
        if forecast_percent > 10:
            alert_class = "forecast-alert"
            icon = "🚨"
            title = "HIGH COST INCREASE ALERT"
        elif forecast_percent > 4:
            alert_class = "forecast-alert warning"
            icon = "⚠️"
            title = "COST INCREASE WARNING"
        else:
            alert_class = "forecast-alert good"
            icon = "✅"
            title = "COSTS UNDER CONTROL"
        
        top_driver = summary.get('top_driver', 'Unknown')
        top_driver_increase = summary.get('top_driver_increase', 0)
        
        return f"""
        <div class="{alert_class}">
            <h3>{icon} {title}</h3>
            <p style="font-size: 18px; margin: 10px 0;">
                Forecasted month-end increase: <strong>{forecast_percent:+.1f}%</strong>
            </p>
            {f'<p>Primary cost driver: <strong>{top_driver}</strong> (+${top_driver_increase:,.2f})</p>' if top_driver != 'Unknown' else ''}
        </div>"""
    
    def _build_forecast_analysis(self, forecast_analysis: Dict) -> str:
        """Build detailed forecast analysis section"""
        if not forecast_analysis or forecast_analysis.get('error'):
            return ""
        
        current = forecast_analysis.get('current_month', {})
        previous = forecast_analysis.get('previous_month', {})
        forecast = forecast_analysis.get('forecast', {})
        projection = forecast_analysis.get('projection', {})
        service_drivers = forecast_analysis.get('service_drivers', {})
        
        html = """
        <h2>🔮 Month-End Forecast Analysis</h2>
        <div class="forecast-grid">"""
        
        # Current month progress
        days_elapsed = current.get('days_elapsed', 0)
        days_remaining = current.get('days_remaining', 0)
        total_days = days_elapsed + days_remaining
        progress_percent = (days_elapsed / total_days * 100) if total_days > 0 else 0
        
        html += f"""
            <div class="forecast-card">
                <h4>📅 Current Month Progress</h4>
                <p><strong>Days elapsed:</strong> {days_elapsed} of {total_days} ({progress_percent:.0f}%)</p>
                <p><strong>Spent so far:</strong> ${current.get('total_cost', 0):,.2f}</p>
                <p><strong>Daily average:</strong> ${(current.get('total_cost', 0) / days_elapsed):,.2f}</p>
            </div>"""
        
        # Forecast comparison
        forecast_change = forecast.get('vs_previous_change', 0)
        forecast_percent = forecast.get('vs_previous_percent', 0)
        card_class = "forecast-card alert" if forecast_percent > 4 else "forecast-card"
        
        html += f"""
            <div class="{card_class}">
                <h4>🎯 AWS Forecast</h4>
                <p><strong>Forecasted total:</strong> ${forecast.get('total_forecast', 0):,.2f}</p>
                <p><strong>Previous month:</strong> ${previous.get('total_cost', 0):,.2f}</p>
                <p><strong>Projected change:</strong> ${forecast_change:+,.2f} ({forecast_percent:+.1f}%)</p>
            </div>"""
        
        # Current trend projection
        proj_change = projection.get('vs_previous_change', 0)
        proj_percent = projection.get('vs_previous_percent', 0)
        
        html += f"""
            <div class="forecast-card">
                <h4>📈 Current Trend</h4>
                <p><strong>Projected total:</strong> ${projection.get('projected_total', 0):,.2f}</p>
                <p><strong>Trend change:</strong> ${proj_change:+,.2f} ({proj_percent:+.1f}%)</p>
                <p><strong>vs AWS Forecast:</strong> ${abs(projection.get('projected_total', 0) - forecast.get('total_forecast', 0)):,.2f} difference</p>
            </div>"""
        
        html += "</div>"
        
        # Top cost drivers
        if service_drivers:
            html += """
            <h3>🎯 Top Cost Drivers This Month</h3>"""
            
            count = 0
            for service, data in service_drivers.items():
                if count >= 10:  # Show top 10
                    break
                
                change = data.get('projected_change', 0)
                if change <= 0:
                    continue
                
                percent_change = data.get('projected_percent_change', 0)
                current_cost = data.get('current_cost', 0)
                projected_cost = data.get('projected_cost', 0)
                
                driver_class = "cost-driver high" if change > 100 else "cost-driver"
                
                html += f"""
                <div class="{driver_class}">
                    <h4>{service}</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                        <div>
                            <strong>Current (MTD):</strong> ${current_cost:,.2f}<br>
                            <strong>Projected:</strong> ${projected_cost:,.2f}
                        </div>
                        <div>
                            <strong>Increase:</strong> ${change:+,.2f}<br>
                            <strong>% Change:</strong> {percent_change:+.1f}%
                        </div>
                    </div>
                </div>"""
                
                count += 1
        
        return html
    
    def _build_footer(self, metadata: Dict) -> str:
        """Build report footer with CostHub branding"""
        return f"""
        <div class="footer">
            <p>
                <span class="costhub-badge">CostHub</span><br>
                <strong>{self.i18n.t('cost_optimization_platform')}</strong><br>
                <small>{self.i18n.t('data_source')}</small>
            </p>
        </div>"""
