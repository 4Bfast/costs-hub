"""
Email Report Generator for AWS SES
Generates email-optimized cost analysis reports
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import logging
import json
from .asset_manager import AssetManager

logger = logging.getLogger(__name__)

class EmailReportGenerator:
    """Generate email-optimized reports for AWS SES"""
    
    def __init__(self, report_config):
        self.config = report_config
        self.asset_manager = AssetManager()
        
    def generate_email_report(self, analysis_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate email report with subject and HTML body"""
        
        periods_data = analysis_data.get('periods_data', analysis_data.get('months_data', []))
        changes = analysis_data['changes']
        top_services = analysis_data['top_services']
        metadata = analysis_data.get('metadata', {})
        forecast_analysis = analysis_data.get('forecast_analysis', {})
        
        # Generate email subject
        subject = self._generate_subject(changes, metadata, forecast_analysis)
        
        # Generate HTML body
        html_body = self._generate_html_body(
            periods_data, changes, top_services, metadata, forecast_analysis, analysis_data
        )
        
        # Generate text body (fallback)
        text_body = self._generate_text_body(
            periods_data, changes, top_services, metadata, forecast_analysis
        )
        
        return {
            'subject': subject,
            'html_body': html_body,
            'text_body': text_body,
            'metadata': {
                'analysis_type': metadata.get('analysis_type', 'monthly'),
                'generated_at': datetime.now().isoformat(),
                'total_cost': periods_data[0]['total_cost'] if periods_data else 0,
                'cost_change': changes.get('total_change', 0),
                'cost_change_percent': changes.get('total_percent_change', 0)
            }
        }
    
    def _generate_subject(self, changes: Dict, metadata: Dict, forecast_analysis: Dict) -> str:
        """Generate email subject line"""
        
        analysis_type = metadata.get('analysis_type', 'monthly').title()
        current_cost = changes.get('current_period', {}).get('total_cost', 0)
        change_percent = changes.get('total_percent_change', 0)
        
        # Check for forecast alerts
        if forecast_analysis and not forecast_analysis.get('error'):
            forecast_percent = forecast_analysis.get('summary', {}).get('forecast_increase_percent', 0)
            if forecast_percent > 10:
                return f"🚨 CostHub Alert: AWS Costs Projected +{forecast_percent:.1f}% - ${current_cost:,.0f}"
            elif forecast_percent > 4:
                return f"⚠️ CostHub Warning: AWS Costs Trending Up +{forecast_percent:.1f}% - ${current_cost:,.0f}"
        
        # Regular change-based subject
        if abs(change_percent) > 10:
            trend = "📈" if change_percent > 0 else "📉"
            return f"{trend} CostHub {analysis_type} Report: AWS Costs {change_percent:+.1f}% - ${current_cost:,.0f}"
        else:
            return f"📊 CostHub {analysis_type} Report: AWS Costs ${current_cost:,.0f} ({change_percent:+.1f}%)"
    
    def _generate_html_body(self, periods_data: List[Dict], changes: Dict, 
                           top_services: List[Dict], metadata: Dict, 
                           forecast_analysis: Dict, analysis_data: Dict) -> str:
        """Generate HTML email body"""
        
        analysis_type = metadata.get('analysis_type', 'monthly')
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CostHub AWS Cost Report</title>
    {self._get_email_css_styles()}
</head>
<body>
    <div class="email-container">
        {self._build_email_header(metadata)}
        {self._build_forecast_email_alert(forecast_analysis) if forecast_analysis and not forecast_analysis.get('error') else ''}
        {self._build_email_executive_summary(changes, analysis_type)}
        {self._build_email_top_services(top_services, changes)}
        {self._build_email_key_changes(changes, analysis_type)}
        {self._build_email_cta()}
        {self._build_email_footer()}
    </div>
</body>
</html>"""
    
    def _get_email_css_styles(self) -> str:
        """Get email-optimized CSS styles"""
        return """
    <style>
        /* Email-safe CSS */
        body { font-family: Arial, Helvetica, sans-serif; margin: 0; padding: 0; background-color: #f1f5f9; }
        .email-container { max-width: 600px; margin: 0 auto; background-color: #ffffff; }
        
        /* Header */
        .email-header { background: linear-gradient(135deg, #1e40af, #3b82f6); color: #ffffff; padding: 30px 20px; text-align: center; }
        .email-logo-container { margin-bottom: 12px; }
        .email-logo-container img { max-width: 240px; height: auto; filter: brightness(0) invert(1); }
        .costhub-logo { font-size: 32px; font-weight: bold; margin: 0 0 8px 0; }
        .costhub-tagline { font-size: 14px; opacity: 0.9; margin: 0; }
        
        /* Content */
        .email-content { padding: 30px 20px; }
        
        /* Summary */
        .email-summary { background: linear-gradient(135deg, #1e40af, #3b82f6); color: #ffffff; padding: 25px; margin: 20px 0; border-radius: 8px; text-align: center; }
        .email-summary h2 { margin: 0 0 15px 0; font-size: 24px; }
        .summary-grid { display: table; width: 100%; margin-top: 15px; }
        .summary-item { display: table-cell; text-align: center; padding: 10px; }
        .summary-value { font-size: 24px; font-weight: bold; margin: 5px 0; }
        .summary-label { font-size: 14px; opacity: 0.9; }
        
        /* Alerts */
        .forecast-alert { padding: 20px; margin: 20px 0; border-radius: 8px; text-align: center; }
        .forecast-alert.high { background-color: #dc2626; color: #ffffff; }
        .forecast-alert.warning { background-color: #f59e0b; color: #ffffff; }
        .forecast-alert.good { background-color: #059669; color: #ffffff; }
        
        /* Services Table */
        .services-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .services-table th { background-color: #1e40af; color: #ffffff; padding: 12px 8px; text-align: left; font-size: 14px; }
        .services-table td { padding: 12px 8px; border-bottom: 1px solid #e5e7eb; font-size: 14px; }
        .services-table tr:nth-child(even) { background-color: #f8fafc; }
        
        /* Changes */
        .changes-section { margin: 25px 0; }
        .change-item { background-color: #f8fafc; padding: 15px; margin: 10px 0; border-radius: 6px; border-left: 4px solid #fbbf24; }
        .change-service { font-weight: bold; color: #1e40af; margin-bottom: 5px; }
        .change-amount { font-size: 16px; }
        .increase { color: #dc2626; }
        .decrease { color: #059669; }
        
        /* CTA */
        .email-cta { text-align: center; margin: 30px 0; }
        .cta-button { background-color: #fbbf24; color: #1e40af; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; }
        
        /* Footer */
        .email-footer { background-color: #f8fafc; padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }
        
        /* Badges */
        .badge { padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
        .badge-danger { background-color: #fee2e2; color: #991b1b; }
        .badge-success { background-color: #d1fae5; color: #065f46; }
        .badge-info { background-color: #dbeafe; color: #1e40af; }
        
        /* Responsive */
        @media only screen and (max-width: 600px) {
            .email-container { width: 100% !important; }
            .email-content { padding: 20px 15px !important; }
            .summary-item { display: block !important; margin: 10px 0 !important; }
        }
    </style>"""
    
    def _build_email_header(self, metadata: Dict) -> str:
        """Build email header"""
        analysis_type = metadata.get('analysis_type', 'monthly').title()
        
        # Get email-optimized logo
        logo_html = self.asset_manager.get_email_logo_html(max_width="180px")
        
        return f"""
        <div class="email-header">
            <div class="email-logo-container">
                {logo_html}
            </div>
            <div class="costhub-tagline">{analysis_type} AWS Cost Analysis Report</div>
        </div>"""
    
    def _build_email_executive_summary(self, changes: Dict, analysis_type: str) -> str:
        """Build executive summary for email"""
        current = changes['current_period']
        previous = changes['previous_period']
        
        trend_icon = '📈' if changes['total_change'] > 0 else '📉' if changes['total_change'] < 0 else '➡️'
        
        period_label = {
            'monthly': 'Month',
            'weekly': 'Week', 
            'daily': 'Day'
        }.get(analysis_type, 'Period')
        
        return f"""
        <div class="email-content">
            <div class="email-summary">
                <h2>📊 Executive Summary</h2>
                <div class="summary-grid">
                    <div class="summary-item">
                        <div class="summary-label">Previous {period_label}</div>
                        <div class="summary-value">${previous['total_cost']:,.0f}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">Current {period_label}</div>
                        <div class="summary-value">${current['total_cost']:,.0f}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">Change</div>
                        <div class="summary-value">{trend_icon} ${abs(changes['total_change']):,.0f}</div>
                        <div class="summary-label">({changes['total_percent_change']:+.1f}%)</div>
                    </div>
                </div>
            </div>
        </div>"""
    
    def _build_forecast_email_alert(self, forecast_analysis: Dict) -> str:
        """Build forecast alert for email"""
        if not forecast_analysis or forecast_analysis.get('error'):
            return ""
        
        summary = forecast_analysis.get('summary', {})
        forecast_percent = summary.get('forecast_increase_percent', 0)
        
        if forecast_percent > 10:
            alert_class = "high"
            icon = "🚨"
            title = "HIGH COST INCREASE ALERT"
        elif forecast_percent > 4:
            alert_class = "warning"
            icon = "⚠️"
            title = "COST INCREASE WARNING"
        else:
            alert_class = "good"
            icon = "✅"
            title = "COSTS UNDER CONTROL"
        
        top_driver = summary.get('top_driver', 'Unknown')
        
        return f"""
        <div class="email-content">
            <div class="forecast-alert {alert_class}">
                <h3>{icon} {title}</h3>
                <p style="font-size: 18px; margin: 10px 0;">
                    Forecasted month-end increase: <strong>{forecast_percent:+.1f}%</strong>
                </p>
                {f'<p>Primary cost driver: <strong>{top_driver}</strong></p>' if top_driver != 'Unknown' else ''}
            </div>
        </div>"""
    
    def _build_email_top_services(self, top_services: List[Dict], changes: Dict) -> str:
        """Build top services table for email"""
        html = """
        <div class="email-content">
            <h2 style="color: #1e40af; border-left: 4px solid #fbbf24; padding-left: 15px;">🔝 Top Services</h2>
            <table class="services-table">
                <thead>
                    <tr><th>Service</th><th>Cost</th><th>Status</th></tr>
                </thead>
                <tbody>"""
        
        for service in top_services[:5]:  # Top 5 for email
            service_name = service['service']
            status_badge = ""
            
            if service_name in changes['service_changes']:
                change_data = changes['service_changes'][service_name]
                if change_data['change'] > 0:
                    status_badge = f'<span class="badge badge-danger">+{change_data["percent_change"]:.1f}%</span>'
                else:
                    status_badge = f'<span class="badge badge-success">{change_data["percent_change"]:.1f}%</span>'
            elif service_name in [s['service'] for s in changes['new_services']]:
                status_badge = '<span class="badge badge-info">NEW</span>'
            else:
                status_badge = '<span class="badge badge-success">Stable</span>'
            
            html += f"""
                <tr>
                    <td>{service_name[:30]}{'...' if len(service_name) > 30 else ''}</td>
                    <td>${service['cost']:,.0f}</td>
                    <td>{status_badge}</td>
                </tr>"""
        
        html += """
                </tbody>
            </table>
        </div>"""
        return html
    
    def _build_email_key_changes(self, changes: Dict, analysis_type: str) -> str:
        """Build key changes section for email"""
        if not changes['service_changes']:
            return ""
        
        period_label = {
            'monthly': 'Monthly',
            'weekly': 'Weekly',
            'daily': 'Daily'
        }.get(analysis_type, 'Period')
        
        html = f"""
        <div class="email-content">
            <h2 style="color: #1e40af; border-left: 4px solid #fbbf24; padding-left: 15px;">📈 Key {period_label} Changes</h2>
            <div class="changes-section">"""
        
        # Show top 5 changes
        count = 0
        for service, data in changes['service_changes'].items():
            if count >= 5:
                break
            
            change_class = 'increase' if data['change'] > 0 else 'decrease'
            html += f"""
            <div class="change-item">
                <div class="change-service">{service[:40]}{'...' if len(service) > 40 else ''}</div>
                <div class="change-amount">
                    <span class="{change_class}">${data['change']:+,.0f} ({data['percent_change']:+.1f}%)</span>
                    <br><small>${data['previous']:,.0f} → ${data['current']:,.0f}</small>
                </div>
            </div>"""
            count += 1
        
        html += """
            </div>
        </div>"""
        return html
    
    def _build_email_cta(self) -> str:
        """Build call-to-action section"""
        return """
        <div class="email-content">
            <div class="email-cta">
                <a href="#" class="cta-button">View Full Report</a>
                <p style="margin-top: 15px; color: #6b7280; font-size: 14px;">
                    Access detailed analysis, charts, and optimization recommendations
                </p>
            </div>
        </div>"""
    
    def _build_email_footer(self) -> str:
        """Build email footer"""
        return """
        <div class="email-footer">
            <p>
                <strong>CostHub</strong> - AWS Cost Analysis & Optimization Platform<br>
                Data sourced from AWS Cost Explorer API<br>
                <small>This is an automated report. Please do not reply to this email.</small>
            </p>
        </div>"""
    
    def _generate_text_body(self, periods_data: List[Dict], changes: Dict, 
                           top_services: List[Dict], metadata: Dict, 
                           forecast_analysis: Dict) -> str:
        """Generate plain text email body (fallback)"""
        
        analysis_type = metadata.get('analysis_type', 'monthly').title()
        current = changes['current_period']
        previous = changes['previous_period']
        
        text = f"""CostHub - {analysis_type} AWS Cost Analysis Report
{'=' * 50}

EXECUTIVE SUMMARY:
Previous Period: ${previous['total_cost']:,.2f}
Current Period: ${current['total_cost']:,.2f}
Change: ${changes['total_change']:+,.2f} ({changes['total_percent_change']:+.1f}%)

"""
        
        # Forecast alert
        if forecast_analysis and not forecast_analysis.get('error'):
            summary = forecast_analysis.get('summary', {})
            forecast_percent = summary.get('forecast_increase_percent', 0)
            if forecast_percent > 4:
                text += f"""FORECAST ALERT:
Projected month-end increase: {forecast_percent:+.1f}%
Primary driver: {summary.get('top_driver', 'Unknown')}

"""
        
        # Top services
        text += "TOP SERVICES:\n"
        for i, service in enumerate(top_services[:5], 1):
            text += f"{i}. {service['service']}: ${service['cost']:,.2f}\n"
        
        # Key changes
        if changes['service_changes']:
            text += "\nKEY CHANGES:\n"
            count = 0
            for service, data in changes['service_changes'].items():
                if count >= 5:
                    break
                text += f"• {service}: ${data['change']:+,.2f} ({data['percent_change']:+.1f}%)\n"
                count += 1
        
        text += f"""
---
CostHub - AWS Cost Analysis & Optimization Platform
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        return text
    
    def generate_ses_template(self, template_name: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AWS SES template format"""
        
        email_report = self.generate_email_report(analysis_data)
        
        # SES Template format
        template = {
            "TemplateName": template_name,
            "TemplateData": {
                "subject": email_report['subject'],
                "html_body": email_report['html_body'],
                "text_body": email_report['text_body'],
                "metadata": email_report['metadata']
            }
        }
        
        return template
    
    def save_email_template(self, analysis_data: Dict[str, Any], template_name: str = None) -> str:
        """Save email template to file"""
        
        if not template_name:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            analysis_type = analysis_data.get('metadata', {}).get('analysis_type', 'monthly')
            template_name = f"costhub_email_{analysis_type}_{timestamp}"
        
        email_report = self.generate_email_report(analysis_data)
        
        # Save HTML version
        html_filepath = self.config.output_dir / f"{template_name}.html"
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(email_report['html_body'])
        
        # Save SES template JSON
        ses_template = self.generate_ses_template(template_name, analysis_data)
        json_filepath = self.config.output_dir / f"{template_name}_ses_template.json"
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(ses_template, f, indent=2)
        
        logger.info(f"Email template saved: {html_filepath}")
        logger.info(f"SES template saved: {json_filepath}")
        
        return str(html_filepath)