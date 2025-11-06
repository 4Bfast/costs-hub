"""
Lambda Report Generator for AWS Cost Analysis

Adapts the existing ReportGenerator for serverless Lambda environment with:
- Client branding application (logos, colors, themes)
- S3 integration for temporary report storage
- Optimized for Lambda execution constraints
"""

import boto3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import tempfile
import os

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


class LambdaReportGenerator:
    """Generate HTML reports optimized for Lambda environment with client branding"""
    
    def __init__(self, s3_bucket: str, s3_prefix: str = "reports"):
        """
        Initialize Lambda Report Generator
        
        Args:
            s3_bucket: S3 bucket name for storing reports
            s3_prefix: S3 prefix for report storage
        """
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.s3_client = boto3.client('s3')
        
    def generate_client_report(self, cost_data: Dict[str, Any], 
                             client_config: ClientConfig,
                             alert_results: Optional[Any] = None) -> str:
        """
        Generate HTML report for a specific client with branding
        
        Args:
            cost_data: Cost analysis data
            client_config: Client configuration including branding
            alert_results: Optional threshold evaluation results for alerts
            
        Returns:
            S3 URL of the generated report
        """
        try:
            logger.info(f"Generating report for client {client_config.client_id}")
            
            # Generate HTML content with client branding and alerts
            html_content = self._build_html_content(cost_data, client_config, alert_results)
            
            # Upload to S3 and return URL
            s3_key = self._upload_report_to_s3(html_content, client_config)
            
            logger.info(f"Report generated successfully for client {client_config.client_id}")
            return f"s3://{self.s3_bucket}/{s3_key}"
            
        except Exception as e:
            logger.error(f"Error generating report for client {client_config.client_id}: {e}")
            raise
    
    def _build_html_content(self, cost_data: Dict[str, Any], 
                           client_config: ClientConfig,
                           alert_results: Optional[Any] = None) -> str:
        """Build complete HTML content with client branding"""
        
        periods_data = cost_data.get('periods_data', cost_data.get('months_data', []))
        accounts_data = cost_data.get('accounts_data', [])
        changes = cost_data['changes']
        account_changes = cost_data.get('account_changes', {})
        top_services = cost_data['top_services']
        top_accounts = cost_data.get('top_accounts', [])
        metadata = cost_data.get('metadata', {})
        forecast_analysis = cost_data.get('forecast_analysis', {})
        
        analysis_type = metadata.get('analysis_type', 'monthly')
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{client_config.branding.company_name or client_config.client_name} - AWS Cost Analysis</title>
    {self._get_css_styles(client_config.branding)}
</head>
<body>
    <div class="container">
        {self._build_header(metadata, client_config)}
        {self._build_alert_section(alert_results) if alert_results else ''}
        {self._build_forecast_alert(forecast_analysis) if forecast_analysis and not forecast_analysis.get('error') else ''}
        {self._build_executive_summary(changes, analysis_type)}
        {self._build_forecast_analysis(forecast_analysis) if forecast_analysis and not forecast_analysis.get('error') else ''}
        {self._build_periods_overview(periods_data, analysis_type)}
        {self._build_top_services_section(top_services, changes)}
        {self._build_top_accounts_section(top_accounts, account_changes) if top_accounts else ''}
        {self._build_changes_section(changes, analysis_type)}
        {self._build_account_changes_section(account_changes, analysis_type) if account_changes.get('account_changes') else ''}
        {self._build_new_services_section(changes)}
        {self._build_new_accounts_section(account_changes) if account_changes.get('new_accounts') else ''}
        {self._build_footer(metadata, client_config)}
    </div>
</body>
</html>"""
    
    def _get_css_styles(self, branding: BrandingConfig) -> str:
        """Get CSS styles with client branding colors"""
        
        primary_color = branding.primary_color
        secondary_color = branding.secondary_color
        
        return f"""
    <style>
        :root {{
            --primary-color: {primary_color};
            --secondary-color: {secondary_color};
            --primary-light: {self._lighten_color(primary_color, 0.1)};
            --primary-dark: {self._darken_color(primary_color, 0.1)};
        }}
        
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: #f1f5f9; 
            line-height: 1.6; 
        }}
        
        .container {{ 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 12px; 
            box-shadow: 0 4px 25px rgba(0,0,0,0.15); 
        }}
        
        /* Client Branded Header */
        .client-header {{ 
            background: linear-gradient(135deg, var(--primary-color), var(--primary-light)); 
            color: white; 
            padding: 25px; 
            border-radius: 12px 12px 0 0; 
            margin: -30px -30px 30px -30px; 
            text-align: center; 
        }}
        
        .client-logo-container {{ 
            margin-bottom: 12px; 
        }}
        
        .client-logo-container img {{ 
            max-width: 280px; 
            height: auto; 
            filter: brightness(0) invert(1); 
        }}
        
        .client-name {{ 
            font-size: 28px; 
            font-weight: bold; 
            margin-bottom: 8px; 
        }}
        
        .client-tagline {{ 
            font-size: 14px; 
            opacity: 0.9; 
        }}
        
        h1 {{ 
            color: var(--primary-color); 
            text-align: center; 
            border-bottom: 3px solid var(--secondary-color); 
            padding-bottom: 15px; 
            margin-bottom: 25px; 
        }}
        
        h2 {{ 
            color: var(--primary-color); 
            border-left: 5px solid var(--secondary-color); 
            padding-left: 20px; 
            margin-top: 35px; 
            background: #f8fafc; 
            padding: 15px 20px; 
            border-radius: 8px; 
        }}
        
        h3 {{ 
            color: var(--primary-color); 
            margin-top: 25px; 
        }}
        
        /* Summary Section */
        .summary {{ 
            background: linear-gradient(135deg, var(--primary-color), var(--primary-light)); 
            color: white; 
            padding: 25px; 
            border-radius: 12px; 
            margin: 25px 0; 
            text-align: center; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.3); 
        }}
        
        .summary h3 {{ 
            color: white; 
            margin-top: 0; 
        }}
        
        /* Cards and Grids */
        .month-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); 
            gap: 20px; 
            margin: 25px 0; 
        }}
        
        .month-card {{ 
            background: linear-gradient(135deg, #eff6ff, #dbeafe); 
            padding: 20px; 
            border-radius: 10px; 
            text-align: center; 
            border-left: 5px solid var(--secondary-color); 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }}
        
        .month-card h4 {{ 
            color: var(--primary-color); 
            margin-top: 0; 
        }}
        
        .metric-card {{ 
            background: linear-gradient(135deg, #fef3c7, #fde68a); 
            padding: 20px; 
            border-radius: 10px; 
            margin: 15px 0; 
            border-left: 5px solid var(--primary-color); 
        }}
        
        /* Tables */
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin: 25px 0; 
            border-radius: 8px; 
            overflow: hidden; 
            box-shadow: 0 2px 15px rgba(0,0,0,0.1); 
        }}
        
        th, td {{ 
            border: none; 
            padding: 15px 12px; 
            text-align: left; 
        }}
        
        th {{ 
            background: linear-gradient(135deg, var(--primary-color), var(--primary-light)); 
            color: white; 
            font-weight: 600; 
        }}
        
        tr:nth-child(even) {{ 
            background-color: #f8fafc; 
        }}
        
        tr:hover {{ 
            background-color: #eff6ff; 
        }}
        
        /* Status Colors */
        .increase {{ 
            color: #dc2626; 
            font-weight: bold; 
        }}
        
        .decrease {{ 
            color: #059669; 
            font-weight: bold; 
        }}
        
        .stable {{ 
            color: #6b7280; 
        }}
        
        /* Badges */
        .badge {{ 
            display: inline-block; 
            padding: 6px 12px; 
            border-radius: 20px; 
            font-size: 11px; 
            font-weight: bold; 
            text-transform: uppercase; 
        }}
        
        .badge-success {{ 
            background: #d1fae5; 
            color: #065f46; 
        }}
        
        .badge-danger {{ 
            background: #fee2e2; 
            color: #991b1b; 
        }}
        
        .badge-warning {{ 
            background: #fef3c7; 
            color: #92400e; 
        }}
        
        .badge-info {{ 
            background: #dbeafe; 
            color: var(--primary-color); 
        }}
        
        /* New Services */
        .new-service {{ 
            background: linear-gradient(135deg, #dbeafe, #bfdbfe); 
            padding: 15px; 
            margin: 8px 0; 
            border-radius: 8px; 
            border-left: 5px solid var(--secondary-color); 
        }}
        
        /* Forecast Alerts */
        .forecast-alert {{ 
            padding: 25px; 
            border-radius: 12px; 
            margin: 25px 0; 
            text-align: center; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.2); 
        }}
        
        .forecast-alert.high {{ 
            background: linear-gradient(135deg, #dc2626, #ef4444); 
            color: white; 
        }}
        
        .forecast-alert.warning {{ 
            background: linear-gradient(135deg, #f59e0b, #fbbf24); 
            color: white; 
        }}
        
        .forecast-alert.good {{ 
            background: linear-gradient(135deg, #059669, #10b981); 
            color: white; 
        }}
        
        .forecast-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
            gap: 25px; 
            margin: 25px 0; 
        }}
        
        .forecast-card {{ 
            background: #f8fafc; 
            padding: 25px; 
            border-radius: 12px; 
            border-left: 5px solid var(--secondary-color); 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }}
        
        .forecast-card.alert {{ 
            border-left-color: #dc2626; 
            background: #fef2f2; 
        }}
        
        .forecast-card h4 {{ 
            color: var(--primary-color); 
            margin-top: 0; 
        }}
        
        .cost-driver {{ 
            background: linear-gradient(135deg, #fef3c7, #fde68a); 
            padding: 20px; 
            margin: 15px 0; 
            border-radius: 10px; 
            border-left: 5px solid var(--primary-color); 
        }}
        
        .cost-driver.high {{ 
            border-left-color: #dc2626; 
            background: linear-gradient(135deg, #fee2e2, #fecaca); 
        }}
        
        /* Footer */
        .footer {{ 
            text-align: center; 
            margin-top: 40px; 
            padding-top: 25px; 
            border-top: 2px solid #e5e7eb; 
            color: #6b7280; 
        }}
        
        .client-badge {{ 
            background: linear-gradient(135deg, var(--primary-color), var(--primary-light)); 
            color: white; 
            padding: 8px 16px; 
            border-radius: 25px; 
            font-size: 12px; 
            font-weight: bold; 
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .container {{ 
                padding: 15px; 
            }}
            
            .month-grid, .forecast-grid {{ 
                grid-template-columns: 1fr; 
            }}
            
            table {{ 
                font-size: 14px; 
            }}
            
            th, td {{ 
                padding: 10px 8px; 
            }}
        }}
        
        /* Alert Styles */
        .alert-section {{ 
            margin: 25px 0; 
            padding: 0; 
        }}
        
        .alert-summary {{ 
            background: linear-gradient(135deg, #fee2e2, #fecaca); 
            border: 2px solid #dc2626; 
            border-radius: 12px; 
            padding: 25px; 
            margin-bottom: 20px; 
            text-align: center; 
            box-shadow: 0 4px 15px rgba(220, 38, 38, 0.2); 
        }}
        
        .alert-summary.no-alerts {{ 
            background: linear-gradient(135deg, #d1fae5, #a7f3d0); 
            border-color: #059669; 
            box-shadow: 0 4px 15px rgba(5, 150, 105, 0.2); 
        }}
        
        .alert-summary h3 {{ 
            color: #dc2626; 
            margin-top: 0; 
            margin-bottom: 15px; 
        }}
        
        .alert-summary.no-alerts h3 {{ 
            color: #059669; 
        }}
        
        .alert-stats {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); 
            gap: 15px; 
            margin: 20px 0; 
        }}
        
        .alert-stat {{ 
            background: rgba(255, 255, 255, 0.8); 
            padding: 15px; 
            border-radius: 8px; 
            text-align: center; 
        }}
        
        .alert-stat-number {{ 
            font-size: 24px; 
            font-weight: bold; 
            margin-bottom: 5px; 
        }}
        
        .alert-stat-label {{ 
            font-size: 12px; 
            text-transform: uppercase; 
            opacity: 0.8; 
        }}
        
        .alert-list {{ 
            margin-top: 20px; 
        }}
        
        .alert-item {{ 
            background: white; 
            border-radius: 8px; 
            padding: 20px; 
            margin: 15px 0; 
            border-left: 5px solid #6b7280; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }}
        
        .alert-item.critical {{ 
            border-left-color: #dc2626; 
            background: linear-gradient(135deg, #fef2f2, #fee2e2); 
        }}
        
        .alert-item.high {{ 
            border-left-color: #f59e0b; 
            background: linear-gradient(135deg, #fffbeb, #fef3c7); 
        }}
        
        .alert-item.medium {{ 
            border-left-color: #3b82f6; 
            background: linear-gradient(135deg, #eff6ff, #dbeafe); 
        }}
        
        .alert-item.low {{ 
            border-left-color: #6b7280; 
            background: linear-gradient(135deg, #f9fafb, #f3f4f6); 
        }}
        
        .alert-header {{ 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 10px; 
        }}
        
        .alert-title {{ 
            font-weight: bold; 
            font-size: 16px; 
        }}
        
        .alert-severity {{ 
            padding: 4px 12px; 
            border-radius: 20px; 
            font-size: 11px; 
            font-weight: bold; 
            text-transform: uppercase; 
        }}
        
        .alert-severity.critical {{ 
            background: #dc2626; 
            color: white; 
        }}
        
        .alert-severity.high {{ 
            background: #f59e0b; 
            color: white; 
        }}
        
        .alert-severity.medium {{ 
            background: #3b82f6; 
            color: white; 
        }}
        
        .alert-severity.low {{ 
            background: #6b7280; 
            color: white; 
        }}
        
        .alert-message {{ 
            color: #374151; 
            line-height: 1.5; 
            margin-bottom: 10px; 
        }}
        
        .alert-details {{ 
            font-size: 14px; 
            color: #6b7280; 
            background: rgba(255, 255, 255, 0.6); 
            padding: 10px; 
            border-radius: 6px; 
            margin-top: 10px; 
        }}
        
        .alert-value {{ 
            font-weight: bold; 
            color: #374151; 
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
    
    def _darken_color(self, hex_color: str, factor: float) -> str:
        """Darken a hex color by a factor (0.0 to 1.0)"""
        try:
            # Remove # if present
            hex_color = hex_color.lstrip('#')
            
            # Convert to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Darken
            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color  # Return original if parsing fails
    
    def _build_header(self, metadata: Dict, client_config: ClientConfig) -> str:
        """Build report header with client branding"""
        analysis_type = metadata.get('analysis_type', 'monthly').title()
        company_name = client_config.branding.company_name or client_config.client_name
        
        # Get logo HTML if available
        logo_html = ""
        if client_config.branding.logo_s3_key:
            try:
                logo_url = self._get_s3_presigned_url(client_config.branding.logo_s3_key)
                logo_html = f'<img src="{logo_url}" alt="{company_name} Logo" style="max-width: 280px; height: auto;">'
            except Exception as e:
                logger.warning(f"Could not load logo for client {client_config.client_id}: {e}")
                logo_html = f'<div class="client-name">{company_name}</div>'
        else:
            logo_html = f'<div class="client-name">{company_name}</div>'
        
        return f"""
        <div class="client-header">
            <div class="client-logo-container">
                {logo_html}
            </div>
            <div class="client-tagline">AWS Cost Analysis Report</div>
        </div>
        <h1>{analysis_type} Cost Analysis Report</h1>
        <div style="text-align: center; margin-bottom: 25px;">
            <span class="client-badge">Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}</span>
        </div>"""
    
    def _build_alert_section(self, alert_results: Any) -> str:
        """Build alert section with threshold violations"""
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
                    'medium_alerts': len([a for a in triggered_alerts if a.severity.value == 'medium']),
                    'low_alerts': len([a for a in triggered_alerts if a.severity.value == 'low']),
                    'alert_messages': [{'severity': a.severity.value, 'message': a.message, 'threshold_name': a.threshold_config.name} for a in triggered_alerts]
                }
        
        alert_summary = format_alert_summary(alert_results.alerts)
        
        if not alert_summary['has_alerts']:
            return f"""
        <div class="alert-section">
            <div class="alert-summary no-alerts">
                <h3>✅ All Cost Thresholds OK</h3>
                <p>No cost thresholds have been exceeded. Your AWS spending is within configured limits.</p>
                <div class="alert-stats">
                    <div class="alert-stat">
                        <div class="alert-stat-number">{alert_results.total_thresholds_checked}</div>
                        <div class="alert-stat-label">Thresholds Checked</div>
                    </div>
                    <div class="alert-stat">
                        <div class="alert-stat-number">0</div>
                        <div class="alert-stat-label">Alerts Triggered</div>
                    </div>
                </div>
            </div>
        </div>"""
        
        # Build alert summary with statistics
        alert_stats_html = f"""
            <div class="alert-stats">
                <div class="alert-stat">
                    <div class="alert-stat-number">{alert_summary['total_alerts']}</div>
                    <div class="alert-stat-label">Total Alerts</div>
                </div>"""
        
        if alert_summary['critical_alerts'] > 0:
            alert_stats_html += f"""
                <div class="alert-stat">
                    <div class="alert-stat-number" style="color: #dc2626;">{alert_summary['critical_alerts']}</div>
                    <div class="alert-stat-label">Critical</div>
                </div>"""
        
        if alert_summary['high_alerts'] > 0:
            alert_stats_html += f"""
                <div class="alert-stat">
                    <div class="alert-stat-number" style="color: #f59e0b;">{alert_summary['high_alerts']}</div>
                    <div class="alert-stat-label">High</div>
                </div>"""
        
        if alert_summary['medium_alerts'] > 0:
            alert_stats_html += f"""
                <div class="alert-stat">
                    <div class="alert-stat-number" style="color: #3b82f6;">{alert_summary['medium_alerts']}</div>
                    <div class="alert-stat-label">Medium</div>
                </div>"""
        
        if alert_summary['low_alerts'] > 0:
            alert_stats_html += f"""
                <div class="alert-stat">
                    <div class="alert-stat-number" style="color: #6b7280;">{alert_summary['low_alerts']}</div>
                    <div class="alert-stat-label">Low</div>
                </div>"""
        
        alert_stats_html += """
            </div>"""
        
        # Build individual alert items
        alert_items_html = ""
        for alert_msg in alert_summary['alert_messages']:
            severity = alert_msg['severity']
            severity_icon = {
                'critical': '🚨',
                'high': '⚠️',
                'medium': '📊',
                'low': 'ℹ️'
            }.get(severity, '📊')
            
            alert_items_html += f"""
            <div class="alert-item {severity}">
                <div class="alert-header">
                    <div class="alert-title">{severity_icon} {alert_msg['threshold_name']}</div>
                    <div class="alert-severity {severity}">{severity.upper()}</div>
                </div>
                <div class="alert-message">{alert_msg['message']}</div>
            </div>"""
        
        return f"""
        <div class="alert-section">
            <div class="alert-summary">
                <h3>🚨 Cost Threshold Alerts</h3>
                <p>The following cost thresholds have been exceeded and require attention:</p>
                {alert_stats_html}
            </div>
            <div class="alert-list">
                {alert_items_html}
            </div>
        </div>"""
    
    def _build_executive_summary(self, changes: Dict, analysis_type: str = "monthly") -> str:
        """Build executive summary section"""
        current = changes['current_period']
        previous = changes['previous_period']
        
        trend_icon = '📈' if changes['total_change'] > 0 else '📉' if changes['total_change'] < 0 else '➡️'
        
        period_label = {
            'monthly': 'Month',
            'weekly': 'Week', 
            'daily': 'Day'
        }.get(analysis_type, 'Period')
        
        return f"""
        <div class="summary">
            <h3>📊 Executive Summary</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 15px;">
                <div>
                    <h4>Previous {period_label}</h4>
                    <p style="font-size: 24px; margin: 5px 0;">${previous['total_cost']:,.2f}</p>
                </div>
                <div>
                    <h4>Current {period_label}</h4>
                    <p style="font-size: 24px; margin: 5px 0;">${current['total_cost']:,.2f}</p>
                </div>
                <div>
                    <h4>Change</h4>
                    <p style="font-size: 24px; margin: 5px 0;">
                        {trend_icon} ${abs(changes['total_change']):,.2f}<br>
                        <span style="font-size: 18px;">({changes['total_percent_change']:+.1f}%)</span>
                    </p>
                </div>
            </div>
        </div>"""
    
    def _build_periods_overview(self, periods_data: List[Dict], analysis_type: str = "monthly") -> str:
        """Build periods overview section"""
        
        section_title = {
            'monthly': '📅 Monthly Overview',
            'weekly': '📅 Weekly Overview',
            'daily': '📅 Daily Overview'
        }.get(analysis_type, '📅 Periods Overview')
        
        html = f"""
        <h2>{section_title}</h2>
        <div class="month-grid">"""
        
        for period in periods_data:
            html += f"""
            <div class="month-card">
                <h4>{period['name']}</h4>
                <p style="font-size: 20px; color: var(--primary-color); margin: 10px 0;">
                    <strong>${period['total_cost']:,.2f}</strong>
                </p>
                <p style="font-size: 14px; color: #6b7280;">
                    {period['service_count']} services
                </p>
            </div>"""
        
        html += "</div>"
        return html
    
    def _build_top_services_section(self, top_services: List[Dict], changes: Dict) -> str:
        """Build top services section"""
        html = """
        <h2>🔝 Top Services by Cost</h2>
        <table>
            <thead>
                <tr><th>Service</th><th>Current Cost</th><th>% of Total</th><th>Status</th></tr>
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
                status_badge = '<span class="badge badge-info">NEW</span>'
            else:
                status_badge = '<span class="badge badge-success">Stable</span>'
            
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
        
        period_label = {
            'monthly': 'Monthly',
            'weekly': 'Weekly',
            'daily': 'Daily'
        }.get(analysis_type, 'Period')
        
        html = f"""
        <h2>📈 Main {period_label} Cost Changes</h2>
        <table>
            <thead>
                <tr><th>Service</th><th>Previous</th><th>Current</th><th>Change</th><th>%</th></tr>
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
        
        html = "<h2>🆕 New Services</h2>"
        
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
            alert_class = "forecast-alert high"
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
    
    def _build_footer(self, metadata: Dict, client_config: ClientConfig) -> str:
        """Build report footer with client branding"""
        company_name = client_config.branding.company_name or client_config.client_name
        email_footer = client_config.branding.email_footer
        
        footer_content = f"""
        <div class="footer">
            <p>
                <span class="client-badge">{company_name}</span><br>
                <strong>AWS Cost Analysis Report</strong><br>
                <small>Data sourced from AWS Cost Explorer API</small>
        """
        
        if email_footer:
            footer_content += f"<br><small>{email_footer}</small>"
        
        footer_content += """
            </p>
        </div>"""
        
        return footer_content
    
    def _upload_report_to_s3(self, html_content: str, client_config: ClientConfig) -> str:
        """Upload report to S3 and return the key"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"cost_report_{client_config.client_id}_{timestamp}.html"
        s3_key = f"{self.s3_prefix}/{client_config.client_id}/{filename}"
        
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=html_content.encode('utf-8'),
                ContentType='text/html',
                Metadata={
                    'client_id': client_config.client_id,
                    'client_name': client_config.client_name,
                    'generated_at': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Report uploaded to S3: s3://{self.s3_bucket}/{s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error uploading report to S3: {e}")
            raise
    
    def _get_s3_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for S3 object"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.s3_bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL for {s3_key}: {e}")
            raise
    
    def apply_client_branding(self, html_content: str, branding: BrandingConfig) -> str:
        """Apply client branding to existing HTML content (legacy method)"""
        # This method is for backward compatibility
        # The main implementation now generates branded content directly
        logger.warning("apply_client_branding is deprecated. Use generate_client_report instead.")
        return html_content
    
    def upload_report_to_s3(self, report_content: str, client_id: str) -> str:
        """Upload report to S3 (legacy method)"""
        # This method is for backward compatibility
        logger.warning("upload_report_to_s3 is deprecated. Use _upload_report_to_s3 instead.")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"cost_report_{client_id}_{timestamp}.html"
        s3_key = f"{self.s3_prefix}/{client_id}/{filename}"
        
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=report_content.encode('utf-8'),
                ContentType='text/html'
            )
            
            return f"s3://{self.s3_bucket}/{s3_key}"
            
        except Exception as e:
            logger.error(f"Error uploading report to S3: {e}")
            raise