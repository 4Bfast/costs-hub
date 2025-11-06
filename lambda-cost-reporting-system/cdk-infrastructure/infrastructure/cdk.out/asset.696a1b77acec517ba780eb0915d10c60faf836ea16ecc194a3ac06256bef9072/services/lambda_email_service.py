"""
Lambda Email Service for AWS SES

Handles email sending with client branding, retry logic, and error handling.
Optimized for Lambda environment with AWS SES integration.
"""

import boto3
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from botocore.exceptions import ClientError

try:
    from ..models.config_models import ClientConfig, BrandingConfig
    from ..utils.logging import create_logger as get_logger
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.config_models import ClientConfig, BrandingConfig
    from utils.logging import create_logger
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class LambdaEmailService:
    """AWS SES email service optimized for Lambda environment"""
    
    def __init__(self, region: str = "us-east-1", sender_email: str = None):
        """
        Initialize Lambda Email Service
        
        Args:
            region: AWS region for SES
            sender_email: Default sender email address
        """
        self.region = region
        self.sender_email = sender_email
        self.ses_client = boto3.client('ses', region_name=region)
        
    def send_client_report(self, report_data: Dict[str, Any], 
                          client_config: ClientConfig,
                          alert_results: Optional[Any] = None) -> bool:
        """
        Send cost analysis report to client with branding
        
        Args:
            report_data: Report data including cost analysis and metadata
            client_config: Client configuration including recipients and branding
            alert_results: Optional threshold evaluation results for alerts
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            logger.info(f"Sending report email for client {client_config.client_id}")
            
            # Generate email content with client branding and alerts
            email_content = self._create_email_template(report_data, client_config, alert_results)
            
            # Send email with retry logic
            success = self.send_with_retry(email_content, max_retries=3)
            
            if success:
                logger.info(f"Report email sent successfully for client {client_config.client_id}")
            else:
                logger.error(f"Failed to send report email for client {client_config.client_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending report email for client {client_config.client_id}: {e}")
            return False
    
    def _create_email_template(self, report_data: Dict[str, Any], 
                              client_config: ClientConfig,
                              alert_results: Optional[Any] = None) -> Dict[str, Any]:
        """Create email template with client branding"""
        
        cost_data = report_data.get('cost_data', {})
        periods_data = cost_data.get('periods_data', cost_data.get('months_data', []))
        changes = cost_data.get('changes', {})
        top_services = cost_data.get('top_services', [])
        metadata = cost_data.get('metadata', {})
        forecast_analysis = cost_data.get('forecast_analysis', {})
        
        # Generate subject line with alert information
        subject = self._generate_subject(changes, metadata, forecast_analysis, client_config, alert_results)
        
        # Generate HTML body with alert information
        html_body = self._generate_html_body(
            periods_data, changes, top_services, metadata, 
            forecast_analysis, client_config, alert_results
        )
        
        # Generate text body (fallback)
        text_body = self._generate_text_body(
            periods_data, changes, top_services, metadata, 
            forecast_analysis, client_config
        )
        
        return {
            'subject': subject,
            'html_body': html_body,
            'text_body': text_body,
            'recipients': client_config.report_config.recipients,
            'cc_recipients': client_config.report_config.cc_recipients,
            'sender': self.sender_email,
            'client_id': client_config.client_id
        }
    
    def _generate_subject(self, changes: Dict, metadata: Dict, 
                         forecast_analysis: Dict, client_config: ClientConfig,
                         alert_results: Optional[Any] = None) -> str:
        """Generate email subject line with client branding"""
        
        analysis_type = metadata.get('analysis_type', 'monthly').title()
        company_name = client_config.branding.company_name or client_config.client_name
        current_cost = changes.get('current_period', {}).get('total_cost', 0)
        change_percent = changes.get('total_percent_change', 0)
        
        # Check for threshold alerts first (highest priority)
        if alert_results and hasattr(alert_results, 'has_critical_alerts') and alert_results.has_critical_alerts():
            return f"🚨 {company_name} CRITICAL ALERT: Cost Thresholds Exceeded - ${current_cost:,.0f}"
        elif alert_results and hasattr(alert_results, 'has_any_alerts') and alert_results.has_any_alerts():
            alert_count = getattr(alert_results, 'triggered_alerts_count', 0)
            return f"⚠️ {company_name} Alert: {alert_count} Cost Threshold(s) Exceeded - ${current_cost:,.0f}"
        
        # Check for forecast alerts
        if forecast_analysis and not forecast_analysis.get('error'):
            forecast_percent = forecast_analysis.get('summary', {}).get('forecast_increase_percent', 0)
            if forecast_percent > 10:
                return f"🚨 {company_name} Alert: AWS Costs Projected +{forecast_percent:.1f}% - ${current_cost:,.0f}"
            elif forecast_percent > 4:
                return f"⚠️ {company_name} Warning: AWS Costs Trending Up +{forecast_percent:.1f}% - ${current_cost:,.0f}"
        
        # Regular change-based subject
        if abs(change_percent) > 10:
            trend = "📈" if change_percent > 0 else "📉"
            return f"{trend} {company_name} {analysis_type} Report: AWS Costs {change_percent:+.1f}% - ${current_cost:,.0f}"
        else:
            return f"📊 {company_name} {analysis_type} Report: AWS Costs ${current_cost:,.0f} ({change_percent:+.1f}%)"
    
    def _generate_html_body(self, periods_data: List[Dict], changes: Dict, 
                           top_services: List[Dict], metadata: Dict, 
                           forecast_analysis: Dict, client_config: ClientConfig,
                           alert_results: Optional[Any] = None) -> str:
        """Generate HTML email body with client branding"""
        
        analysis_type = metadata.get('analysis_type', 'monthly')
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{client_config.branding.company_name or client_config.client_name} AWS Cost Report</title>
    {self._get_email_css_styles(client_config.branding)}
</head>
<body>
    <div class="email-container">
        {self._build_email_header(metadata, client_config)}
        {self._build_email_alert_section(alert_results) if alert_results else ''}
        {self._build_forecast_email_alert(forecast_analysis) if forecast_analysis and not forecast_analysis.get('error') else ''}
        {self._build_email_executive_summary(changes, analysis_type)}
        {self._build_email_top_services(top_services, changes)}
        {self._build_email_key_changes(changes, analysis_type)}
        {self._build_email_cta(client_config)}
        {self._build_email_footer(client_config)}
    </div>
</body>
</html>"""
    
    def _get_email_css_styles(self, branding: BrandingConfig) -> str:
        """Get email-optimized CSS styles with client branding"""
        
        primary_color = branding.primary_color
        secondary_color = branding.secondary_color
        
        return f"""
    <style>
        /* Email-safe CSS with client branding */
        body {{ 
            font-family: Arial, Helvetica, sans-serif; 
            margin: 0; 
            padding: 0; 
            background-color: #f1f5f9; 
        }}
        
        .email-container {{ 
            max-width: 600px; 
            margin: 0 auto; 
            background-color: #ffffff; 
        }}
        
        /* Header with client branding */
        .email-header {{ 
            background: linear-gradient(135deg, {primary_color}, {self._lighten_color(primary_color, 0.1)}); 
            color: #ffffff; 
            padding: 30px 20px; 
            text-align: center; 
        }}
        
        .email-logo-container {{ 
            margin-bottom: 12px; 
        }}
        
        .email-logo-container img {{ 
            max-width: 240px; 
            height: auto; 
            filter: brightness(0) invert(1); 
        }}
        
        .company-name {{ 
            font-size: 32px; 
            font-weight: bold; 
            margin: 0 0 8px 0; 
        }}
        
        .company-tagline {{ 
            font-size: 14px; 
            opacity: 0.9; 
            margin: 0; 
        }}
        
        /* Content */
        .email-content {{ 
            padding: 30px 20px; 
        }}
        
        /* Summary with client colors */
        .email-summary {{ 
            background: linear-gradient(135deg, {primary_color}, {self._lighten_color(primary_color, 0.1)}); 
            color: #ffffff; 
            padding: 25px; 
            margin: 20px 0; 
            border-radius: 8px; 
            text-align: center; 
        }}
        
        .email-summary h2 {{ 
            margin: 0 0 15px 0; 
            font-size: 24px; 
        }}
        
        .summary-grid {{ 
            display: table; 
            width: 100%; 
            margin-top: 15px; 
        }}
        
        .summary-item {{ 
            display: table-cell; 
            text-align: center; 
            padding: 10px; 
        }}
        
        .summary-value {{ 
            font-size: 24px; 
            font-weight: bold; 
            margin: 5px 0; 
        }}
        
        .summary-label {{ 
            font-size: 14px; 
            opacity: 0.9; 
        }}
        
        /* Alerts */
        .forecast-alert {{ 
            padding: 20px; 
            margin: 20px 0; 
            border-radius: 8px; 
            text-align: center; 
        }}
        
        .forecast-alert.high {{ 
            background-color: #dc2626; 
            color: #ffffff; 
        }}
        
        .forecast-alert.warning {{ 
            background-color: #f59e0b; 
            color: #ffffff; 
        }}
        
        .forecast-alert.good {{ 
            background-color: #059669; 
            color: #ffffff; 
        }}
        
        /* Services Table */
        .services-table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0; 
        }}
        
        .services-table th {{ 
            background-color: {primary_color}; 
            color: #ffffff; 
            padding: 12px 8px; 
            text-align: left; 
            font-size: 14px; 
        }}
        
        .services-table td {{ 
            padding: 12px 8px; 
            border-bottom: 1px solid #e5e7eb; 
            font-size: 14px; 
        }}
        
        .services-table tr:nth-child(even) {{ 
            background-color: #f8fafc; 
        }}
        
        /* Changes */
        .changes-section {{ 
            margin: 25px 0; 
        }}
        
        .change-item {{ 
            background-color: #f8fafc; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 6px; 
            border-left: 4px solid {secondary_color}; 
        }}
        
        .change-service {{ 
            font-weight: bold; 
            color: {primary_color}; 
            margin-bottom: 5px; 
        }}
        
        .change-amount {{ 
            font-size: 16px; 
        }}
        
        .increase {{ 
            color: #dc2626; 
        }}
        
        .decrease {{ 
            color: #059669; 
        }}
        
        /* CTA */
        .email-cta {{ 
            text-align: center; 
            margin: 30px 0; 
        }}
        
        .cta-button {{ 
            background-color: {secondary_color}; 
            color: {primary_color}; 
            padding: 15px 30px; 
            text-decoration: none; 
            border-radius: 8px; 
            font-weight: bold; 
            display: inline-block; 
        }}
        
        /* Footer */
        .email-footer {{ 
            background-color: #f8fafc; 
            padding: 20px; 
            text-align: center; 
            color: #6b7280; 
            font-size: 12px; 
        }}
        
        /* Badges */
        .badge {{ 
            padding: 4px 8px; 
            border-radius: 12px; 
            font-size: 11px; 
            font-weight: bold; 
        }}
        
        .badge-danger {{ 
            background-color: #fee2e2; 
            color: #991b1b; 
        }}
        
        .badge-success {{ 
            background-color: #d1fae5; 
            color: #065f46; 
        }}
        
        .badge-info {{ 
            background-color: #dbeafe; 
            color: {primary_color}; 
        }}
        
        /* Responsive */
        @media only screen and (max-width: 600px) {{
            .email-container {{ 
                width: 100% !important; 
            }}
            
            .email-content {{ 
                padding: 20px 15px !important; 
            }}
            
            .summary-item {{ 
                display: block !important; 
                margin: 10px 0 !important; 
            }}
        }}
        
        /* Email Alert Styles */
        .email-alert-section {{ 
            margin: 20px 0; 
        }}
        
        .email-alert-summary {{ 
            background: linear-gradient(135deg, #fee2e2, #fecaca); 
            border: 2px solid #dc2626; 
            border-radius: 8px; 
            padding: 20px; 
            margin-bottom: 15px; 
            text-align: center; 
        }}
        
        .email-alert-summary.no-alerts {{ 
            background: linear-gradient(135deg, #d1fae5, #a7f3d0); 
            border-color: #059669; 
        }}
        
        .email-alert-summary h3 {{ 
            color: #dc2626; 
            margin: 0 0 10px 0; 
            font-size: 18px; 
        }}
        
        .email-alert-summary.no-alerts h3 {{ 
            color: #059669; 
        }}
        
        .email-alert-item {{ 
            background: rgba(255, 255, 255, 0.8); 
            border-radius: 6px; 
            padding: 12px; 
            margin: 10px 0; 
            text-align: left; 
            border-left: 4px solid #6b7280; 
        }}
        
        .email-alert-item.critical {{ 
            border-left-color: #dc2626; 
        }}
        
        .email-alert-item.high {{ 
            border-left-color: #f59e0b; 
        }}
        
        .email-alert-item.medium {{ 
            border-left-color: #3b82f6; 
        }}
        
        .email-alert-item.low {{ 
            border-left-color: #6b7280; 
        }}
        }}
    </style>"""
    
    def _lighten_color(self, hex_color: str, factor: float) -> str:
        """Lighten a hex color by a factor (0.0 to 1.0)"""
        try:
            # Remove # if present
            hex_color = hex_color.lstrip('#')
            
            # Convert to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Lighten
            r = min(255, int(r + (255 - r) * factor))
            g = min(255, int(g + (255 - g) * factor))
            b = min(255, int(b + (255 - b) * factor))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color  # Return original if parsing fails
    
    def _build_email_header(self, metadata: Dict, client_config: ClientConfig) -> str:
        """Build email header with client branding"""
        analysis_type = metadata.get('analysis_type', 'monthly').title()
        company_name = client_config.branding.company_name or client_config.client_name
        
        # Get email-optimized logo if available
        logo_html = ""
        if client_config.branding.logo_s3_key:
            try:
                # For email, we'll use a placeholder for now
                # In production, this would be a presigned URL or embedded image
                logo_html = f'<div class="company-name">{company_name}</div>'
            except Exception as e:
                logger.warning(f"Could not load logo for email: {e}")
                logo_html = f'<div class="company-name">{company_name}</div>'
        else:
            logo_html = f'<div class="company-name">{company_name}</div>'
        
        return f"""
        <div class="email-header">
            <div class="email-logo-container">
                {logo_html}
            </div>
            <div class="company-tagline">{analysis_type} AWS Cost Analysis Report</div>
        </div>"""
    
    def _build_email_alert_section(self, alert_results: Any) -> str:
        """Build alert section for email"""
        if not alert_results or not hasattr(alert_results, 'alerts'):
            return ""
        
        # Import here to avoid circular imports
        try:
            from ..utils.cost_data_converter import format_alert_summary
        except ImportError:
            # Fallback implementation
            def format_alert_summary(alerts):
                triggered_alerts = [a for a in alerts if a.triggered]
                return {
                    'has_alerts': len(triggered_alerts) > 0,
                    'total_alerts': len(triggered_alerts),
                    'critical_alerts': len([a for a in triggered_alerts if a.severity.value == 'critical']),
                    'high_alerts': len([a for a in triggered_alerts if a.severity.value == 'high']),
                    'alert_messages': [{'severity': a.severity.value, 'message': a.message, 'threshold_name': a.threshold_config.name} for a in triggered_alerts]
                }
        
        alert_summary = format_alert_summary(alert_results.alerts)
        
        if not alert_summary['has_alerts']:
            return f"""
        <div class="email-alert-section">
            <div class="email-alert-summary no-alerts">
                <h3>✅ All Cost Thresholds OK</h3>
                <p>No cost thresholds have been exceeded. Your AWS spending is within configured limits.</p>
            </div>
        </div>"""
        
        # Build alert items for email
        alert_items_html = ""
        for alert_msg in alert_summary['alert_messages'][:3]:  # Limit to top 3 alerts in email
            severity = alert_msg['severity']
            severity_icon = {
                'critical': '🚨',
                'high': '⚠️',
                'medium': '📊',
                'low': 'ℹ️'
            }.get(severity, '📊')
            
            alert_items_html += f"""
            <div class="email-alert-item {severity}">
                <strong>{severity_icon} {alert_msg['threshold_name']}</strong><br>
                {alert_msg['message']}
            </div>"""
        
        # Add "view more" if there are more than 3 alerts
        more_alerts_text = ""
        if alert_summary['total_alerts'] > 3:
            remaining = alert_summary['total_alerts'] - 3
            more_alerts_text = f"<p><em>+ {remaining} more alert(s) in the full report</em></p>"
        
        return f"""
        <div class="email-alert-section">
            <div class="email-alert-summary">
                <h3>🚨 Cost Threshold Alerts</h3>
                <p><strong>{alert_summary['total_alerts']} threshold(s) exceeded</strong> - Immediate attention required</p>
                {alert_items_html}
                {more_alerts_text}
            </div>
        </div>"""
    
    def _build_email_executive_summary(self, changes: Dict, analysis_type: str) -> str:
        """Build executive summary for email"""
        current = changes.get('current_period', {})
        previous = changes.get('previous_period', {})
        
        trend_icon = '📈' if changes.get('total_change', 0) > 0 else '📉' if changes.get('total_change', 0) < 0 else '➡️'
        
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
                        <div class="summary-value">${previous.get('total_cost', 0):,.0f}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">Current {period_label}</div>
                        <div class="summary-value">${current.get('total_cost', 0):,.0f}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">Change</div>
                        <div class="summary-value">{trend_icon} ${abs(changes.get('total_change', 0)):,.0f}</div>
                        <div class="summary-label">({changes.get('total_percent_change', 0):+.1f}%)</div>
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
            <h2 style="color: var(--primary-color, #1e40af); border-left: 4px solid var(--secondary-color, #fbbf24); padding-left: 15px;">🔝 Top Services</h2>
            <table class="services-table">
                <thead>
                    <tr><th>Service</th><th>Cost</th><th>Status</th></tr>
                </thead>
                <tbody>"""
        
        for service in top_services[:5]:  # Top 5 for email
            service_name = service.get('service', 'Unknown')
            service_cost = service.get('cost', 0)
            status_badge = ""
            
            if service_name in changes.get('service_changes', {}):
                change_data = changes['service_changes'][service_name]
                if change_data.get('change', 0) > 0:
                    status_badge = f'<span class="badge badge-danger">+{change_data.get("percent_change", 0):.1f}%</span>'
                else:
                    status_badge = f'<span class="badge badge-success">{change_data.get("percent_change", 0):.1f}%</span>'
            elif service_name in [s.get('service', '') for s in changes.get('new_services', [])]:
                status_badge = '<span class="badge badge-info">NEW</span>'
            else:
                status_badge = '<span class="badge badge-success">Stable</span>'
            
            # Truncate long service names for email
            display_name = service_name[:30] + '...' if len(service_name) > 30 else service_name
            
            html += f"""
                <tr>
                    <td>{display_name}</td>
                    <td>${service_cost:,.0f}</td>
                    <td>{status_badge}</td>
                </tr>"""
        
        html += """
                </tbody>
            </table>
        </div>"""
        return html
    
    def _build_email_key_changes(self, changes: Dict, analysis_type: str) -> str:
        """Build key changes section for email"""
        if not changes.get('service_changes'):
            return ""
        
        period_label = {
            'monthly': 'Monthly',
            'weekly': 'Weekly',
            'daily': 'Daily'
        }.get(analysis_type, 'Period')
        
        html = f"""
        <div class="email-content">
            <h2 style="color: var(--primary-color, #1e40af); border-left: 4px solid var(--secondary-color, #fbbf24); padding-left: 15px;">📈 Key {period_label} Changes</h2>
            <div class="changes-section">"""
        
        # Show top 5 changes
        count = 0
        for service, data in changes['service_changes'].items():
            if count >= 5:
                break
            
            change_class = 'increase' if data.get('change', 0) > 0 else 'decrease'
            display_name = service[:40] + '...' if len(service) > 40 else service
            
            html += f"""
            <div class="change-item">
                <div class="change-service">{display_name}</div>
                <div class="change-amount">
                    <span class="{change_class}">${data.get('change', 0):+,.0f} ({data.get('percent_change', 0):+.1f}%)</span>
                    <br><small>${data.get('previous', 0):,.0f} → ${data.get('current', 0):,.0f}</small>
                </div>
            </div>"""
            count += 1
        
        html += """
            </div>
        </div>"""
        return html
    
    def _build_email_cta(self, client_config: ClientConfig) -> str:
        """Build call-to-action section"""
        company_name = client_config.branding.company_name or client_config.client_name
        
        return f"""
        <div class="email-content">
            <div class="email-cta">
                <a href="#" class="cta-button">View Full Report</a>
                <p style="margin-top: 15px; color: #6b7280; font-size: 14px;">
                    Access detailed analysis, charts, and optimization recommendations for {company_name}
                </p>
            </div>
        </div>"""
    
    def _build_email_footer(self, client_config: ClientConfig) -> str:
        """Build email footer with client branding"""
        company_name = client_config.branding.company_name or client_config.client_name
        email_footer = client_config.branding.email_footer
        
        footer_content = f"""
        <div class="email-footer">
            <p>
                <strong>{company_name}</strong> - AWS Cost Analysis Report<br>
                Data sourced from AWS Cost Explorer API<br>
        """
        
        if email_footer:
            footer_content += f"{email_footer}<br>"
        
        footer_content += """
                <small>This is an automated report. Please do not reply to this email.</small>
            </p>
        </div>"""
        
        return footer_content
    
    def _generate_text_body(self, periods_data: List[Dict], changes: Dict, 
                           top_services: List[Dict], metadata: Dict, 
                           forecast_analysis: Dict, client_config: ClientConfig) -> str:
        """Generate plain text email body (fallback)"""
        
        analysis_type = metadata.get('analysis_type', 'monthly').title()
        company_name = client_config.branding.company_name or client_config.client_name
        current = changes.get('current_period', {})
        previous = changes.get('previous_period', {})
        
        text = f"""{company_name} - {analysis_type} AWS Cost Analysis Report
{'=' * 60}

EXECUTIVE SUMMARY:
Previous Period: ${previous.get('total_cost', 0):,.2f}
Current Period: ${current.get('total_cost', 0):,.2f}
Change: ${changes.get('total_change', 0):+,.2f} ({changes.get('total_percent_change', 0):+.1f}%)

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
            text += f"{i}. {service.get('service', 'Unknown')}: ${service.get('cost', 0):,.2f}\n"
        
        # Key changes
        if changes.get('service_changes'):
            text += "\nKEY CHANGES:\n"
            count = 0
            for service, data in changes['service_changes'].items():
                if count >= 5:
                    break
                text += f"• {service}: ${data.get('change', 0):+,.2f} ({data.get('percent_change', 0):+.1f}%)\n"
                count += 1
        
        # Footer
        text += f"""
---
{company_name} - AWS Cost Analysis Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        if client_config.branding.email_footer:
            text += f"\n{client_config.branding.email_footer}"
        
        return text
    
    def send_with_retry(self, email_data: Dict[str, Any], max_retries: int = 3) -> bool:
        """
        Send email with retry logic and exponential backoff
        
        Args:
            email_data: Email data including subject, body, recipients
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if email sent successfully, False otherwise
        """
        for attempt in range(max_retries + 1):
            try:
                # Send email using SES
                response = self._send_ses_email(email_data)
                
                if response:
                    logger.info(f"Email sent successfully on attempt {attempt + 1}")
                    return True
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Don't retry for certain errors
                if error_code in ['MessageRejected', 'InvalidParameterValue']:
                    logger.error(f"Non-retryable SES error: {error_code} - {e}")
                    return False
                
                logger.warning(f"SES error on attempt {attempt + 1}: {error_code} - {e}")
                
            except Exception as e:
                logger.warning(f"Email send attempt {attempt + 1} failed: {e}")
            
            # Wait before retry (exponential backoff)
            if attempt < max_retries:
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                logger.info(f"Retrying email send in {wait_time} seconds...")
                time.sleep(wait_time)
        
        logger.error(f"Failed to send email after {max_retries + 1} attempts")
        return False
    
    def _send_ses_email(self, email_data: Dict[str, Any]) -> bool:
        """Send email using AWS SES"""
        
        try:
            # Prepare email parameters
            destination = {
                'ToAddresses': email_data['recipients']
            }
            
            if email_data.get('cc_recipients'):
                destination['CcAddresses'] = email_data['cc_recipients']
            
            message = {
                'Subject': {
                    'Data': email_data['subject'],
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': email_data['html_body'],
                        'Charset': 'UTF-8'
                    },
                    'Text': {
                        'Data': email_data['text_body'],
                        'Charset': 'UTF-8'
                    }
                }
            }
            
            # Send email
            response = self.ses_client.send_email(
                Source=email_data['sender'] or self.sender_email,
                Destination=destination,
                Message=message
            )
            
            message_id = response.get('MessageId')
            logger.info(f"Email sent successfully. MessageId: {message_id}")
            
            return True
            
        except ClientError as e:
            logger.error(f"SES ClientError: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Error sending SES email: {e}")
            raise
    
    def verify_email_address(self, email: str) -> bool:
        """
        Verify an email address with SES (for development/testing)
        
        Args:
            email: Email address to verify
            
        Returns:
            True if verification initiated successfully
        """
        try:
            response = self.ses_client.verify_email_identity(EmailAddress=email)
            logger.info(f"Email verification initiated for: {email}")
            return True
            
        except ClientError as e:
            logger.error(f"Error verifying email {email}: {e}")
            return False
    
    def get_send_quota(self) -> Dict[str, Any]:
        """Get SES sending quota and statistics"""
        try:
            quota = self.ses_client.get_send_quota()
            stats = self.ses_client.get_send_statistics()
            
            return {
                'quota': quota,
                'statistics': stats
            }
            
        except ClientError as e:
            logger.error(f"Error getting SES quota: {e}")
            return {}
    
    def create_email_template(self, cost_data: Dict, branding: BrandingConfig) -> str:
        """Legacy method for backward compatibility"""
        logger.warning("create_email_template is deprecated. Use _create_email_template instead.")
        
        # Create a minimal client config for compatibility
        from ..models.config_models import ClientConfig, ReportConfig
        
        client_config = ClientConfig(
            client_id="legacy",
            client_name="Legacy Client",
            aws_accounts=[],
            report_config=ReportConfig(recipients=["test@example.com"]),
            branding=branding
        )
        
        report_data = {'cost_data': cost_data}
        email_content = self._create_email_template(report_data, client_config)
        
        return email_content['html_body']