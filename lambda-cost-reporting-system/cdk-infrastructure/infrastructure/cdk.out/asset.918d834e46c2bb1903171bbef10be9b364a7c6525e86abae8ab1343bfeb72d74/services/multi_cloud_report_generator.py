"""
Multi-Cloud Report Generator

Enhanced report generator that handles multi-provider cost data with:
- Cross-provider cost comparison sections
- Unified service category reporting
- Provider-specific breakdowns
- Multi-cloud cost analytics
"""

import boto3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import tempfile
import os
from decimal import Decimal

try:
    from ..models.multi_cloud_models import UnifiedCostRecord, CloudProvider, ServiceCategory
    from ..models.config_models import ClientConfig, BrandingConfig
    from ..utils.logging import create_logger as get_logger
    from .lambda_report_generator import LambdaReportGenerator
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.multi_cloud_models import UnifiedCostRecord, CloudProvider, ServiceCategory
    from models.config_models import ClientConfig, BrandingConfig
    from utils.logging import create_logger
    from lambda_report_generator import LambdaReportGenerator
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class MultiCloudReportGenerator(LambdaReportGenerator):
    """Enhanced report generator for multi-cloud cost data"""
    
    def __init__(self, s3_bucket: str, s3_prefix: str = "reports"):
        """
        Initialize Multi-Cloud Report Generator
        
        Args:
            s3_bucket: S3 bucket name for storing reports
            s3_prefix: S3 prefix for report storage
        """
        super().__init__(s3_bucket, s3_prefix)
        
        # Multi-cloud specific configurations
        self.provider_colors = {
            CloudProvider.AWS: "#FF9900",
            CloudProvider.GCP: "#4285F4", 
            CloudProvider.AZURE: "#0078D4"
        }
        
        self.service_category_icons = {
            ServiceCategory.COMPUTE: "🖥️",
            ServiceCategory.STORAGE: "💾",
            ServiceCategory.DATABASE: "🗄️",
            ServiceCategory.NETWORKING: "🌐",
            ServiceCategory.ANALYTICS: "📊",
            ServiceCategory.SECURITY: "🔒",
            ServiceCategory.MANAGEMENT: "⚙️",
            ServiceCategory.OTHER: "📦"
        }
    
    def generate_multi_cloud_report(
        self, 
        unified_cost_data: List[UnifiedCostRecord], 
        client_config: ClientConfig,
        ai_insights: Optional[Any] = None,
        alert_results: Optional[Any] = None
    ) -> str:
        """
        Generate comprehensive multi-cloud HTML report
        
        Args:
            unified_cost_data: List of unified cost records from all providers
            client_config: Client configuration including branding
            ai_insights: Optional AI insights for enhanced reporting
            alert_results: Optional threshold evaluation results
            
        Returns:
            S3 URL of the generated report
        """
        try:
            logger.info(f"Generating multi-cloud report for client {client_config.client_id}")
            
            # Process and aggregate multi-cloud data
            processed_data = self._process_multi_cloud_data(unified_cost_data)
            
            # Generate HTML content with multi-cloud sections
            html_content = self._build_multi_cloud_html_content(
                processed_data, client_config, ai_insights, alert_results
            )
            
            # Upload to S3 and return URL
            s3_key = self._upload_report_to_s3(html_content, client_config)
            
            logger.info(f"Multi-cloud report generated successfully for client {client_config.client_id}")
            return f"s3://{self.s3_bucket}/{s3_key}"
            
        except Exception as e:
            logger.error(f"Error generating multi-cloud report for client {client_config.client_id}: {e}")
            raise
    
    def _process_multi_cloud_data(self, unified_cost_data: List[UnifiedCostRecord]) -> Dict[str, Any]:
        """Process unified cost data for multi-cloud reporting"""
        
        # Group data by provider and date
        provider_data = {}
        total_costs = {}
        service_categories = {}
        date_range = set()
        
        for record in unified_cost_data:
            provider = record.provider
            date = record.date
            
            date_range.add(date)
            
            # Initialize provider data structure
            if provider not in provider_data:
                provider_data[provider] = {}
                total_costs[provider] = Decimal('0')
                service_categories[provider] = {}
            
            if date not in provider_data[provider]:
                provider_data[provider][date] = {
                    'total_cost': Decimal('0'),
                    'services': {},
                    'accounts': record.accounts,
                    'regions': record.regions
                }
            
            # Aggregate costs
            provider_data[provider][date]['total_cost'] += record.total_cost
            total_costs[provider] += record.total_cost
            
            # Aggregate services by unified categories
            for service_name, service_cost in record.services.items():
                category = service_cost.unified_category
                
                if category not in service_categories[provider]:
                    service_categories[provider][category] = Decimal('0')
                
                service_categories[provider][category] += service_cost.cost
                
                if service_name not in provider_data[provider][date]['services']:
                    provider_data[provider][date]['services'][service_name] = Decimal('0')
                
                provider_data[provider][date]['services'][service_name] += service_cost.cost
        
        # Calculate cross-provider comparisons
        cross_provider_comparison = self._calculate_cross_provider_comparison(
            provider_data, total_costs, service_categories
        )
        
        # Calculate trends and changes
        trends = self._calculate_multi_cloud_trends(provider_data, date_range)
        
        return {
            'provider_data': provider_data,
            'total_costs': total_costs,
            'service_categories': service_categories,
            'cross_provider_comparison': cross_provider_comparison,
            'trends': trends,
            'date_range': sorted(date_range),
            'metadata': {
                'total_providers': len(provider_data),
                'total_records': len(unified_cost_data),
                'date_range_days': len(date_range)
            }
        }
    
    def _calculate_cross_provider_comparison(
        self, 
        provider_data: Dict, 
        total_costs: Dict, 
        service_categories: Dict
    ) -> Dict[str, Any]:
        """Calculate cross-provider cost comparisons"""
        
        # Overall cost distribution
        total_all_providers = sum(total_costs.values())
        cost_distribution = {}
        
        for provider, cost in total_costs.items():
            cost_distribution[provider] = {
                'cost': cost,
                'percentage': float(cost / total_all_providers * 100) if total_all_providers > 0 else 0
            }
        
        # Service category comparison across providers
        all_categories = set()
        for provider_categories in service_categories.values():
            all_categories.update(provider_categories.keys())
        
        category_comparison = {}
        for category in all_categories:
            category_comparison[category] = {}
            category_total = Decimal('0')
            
            for provider in provider_data.keys():
                provider_cost = service_categories.get(provider, {}).get(category, Decimal('0'))
                category_comparison[category][provider] = provider_cost
                category_total += provider_cost
            
            # Calculate percentages
            for provider in provider_data.keys():
                provider_cost = category_comparison[category][provider]
                category_comparison[category][f"{provider}_percentage"] = (
                    float(provider_cost / category_total * 100) if category_total > 0 else 0
                )
        
        # Find most cost-effective provider per category
        cost_leader_by_category = {}
        for category, providers in category_comparison.items():
            min_cost = float('inf')
            leader = None
            
            for provider in provider_data.keys():
                cost = providers.get(provider, Decimal('0'))
                if cost > 0 and cost < min_cost:
                    min_cost = cost
                    leader = provider
            
            if leader:
                cost_leader_by_category[category] = {
                    'provider': leader,
                    'cost': min_cost
                }
        
        return {
            'cost_distribution': cost_distribution,
            'category_comparison': category_comparison,
            'cost_leaders': cost_leader_by_category,
            'total_cost': total_all_providers
        }
    
    def _calculate_multi_cloud_trends(self, provider_data: Dict, date_range: set) -> Dict[str, Any]:
        """Calculate trends across providers and time"""
        
        sorted_dates = sorted(date_range)
        if len(sorted_dates) < 2:
            return {'insufficient_data': True}
        
        # Calculate daily trends per provider
        provider_trends = {}
        for provider, dates_data in provider_data.items():
            daily_costs = []
            for date in sorted_dates:
                cost = dates_data.get(date, {}).get('total_cost', Decimal('0'))
                daily_costs.append(float(cost))
            
            if len(daily_costs) >= 2:
                # Simple trend calculation
                start_cost = daily_costs[0]
                end_cost = daily_costs[-1]
                
                if start_cost > 0:
                    change_percentage = ((end_cost - start_cost) / start_cost) * 100
                else:
                    change_percentage = 0
                
                provider_trends[provider] = {
                    'start_cost': start_cost,
                    'end_cost': end_cost,
                    'change_amount': end_cost - start_cost,
                    'change_percentage': change_percentage,
                    'trend_direction': 'increasing' if change_percentage > 5 else 'decreasing' if change_percentage < -5 else 'stable'
                }
        
        # Overall multi-cloud trend
        total_daily_costs = []
        for date in sorted_dates:
            daily_total = Decimal('0')
            for provider_dates in provider_data.values():
                daily_total += provider_dates.get(date, {}).get('total_cost', Decimal('0'))
            total_daily_costs.append(float(daily_total))
        
        overall_trend = None
        if len(total_daily_costs) >= 2:
            start_total = total_daily_costs[0]
            end_total = total_daily_costs[-1]
            
            if start_total > 0:
                overall_change = ((end_total - start_total) / start_total) * 100
            else:
                overall_change = 0
            
            overall_trend = {
                'start_cost': start_total,
                'end_cost': end_total,
                'change_amount': end_total - start_total,
                'change_percentage': overall_change,
                'trend_direction': 'increasing' if overall_change > 5 else 'decreasing' if overall_change < -5 else 'stable'
            }
        
        return {
            'provider_trends': provider_trends,
            'overall_trend': overall_trend,
            'analysis_period': f"{sorted_dates[0]} to {sorted_dates[-1]}"
        }
    
    def _build_multi_cloud_html_content(
        self, 
        processed_data: Dict[str, Any], 
        client_config: ClientConfig,
        ai_insights: Optional[Any] = None,
        alert_results: Optional[Any] = None
    ) -> str:
        """Build complete multi-cloud HTML content"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{client_config.branding.company_name or client_config.client_name} - Multi-Cloud Cost Analysis</title>
    {self._get_multi_cloud_css_styles(client_config.branding)}
</head>
<body>
    <div class="container">
        {self._build_multi_cloud_header(processed_data['metadata'], client_config)}
        {self._build_alert_section(alert_results) if alert_results else ''}
        {self._build_multi_cloud_executive_summary(processed_data)}
        {self._build_provider_overview_section(processed_data)}
        {self._build_cross_provider_comparison_section(processed_data)}
        {self._build_unified_service_categories_section(processed_data)}
        {self._build_multi_cloud_trends_section(processed_data)}
        {self._build_cost_optimization_opportunities(processed_data)}
        {self._build_footer(processed_data['metadata'], client_config)}
    </div>
</body>
</html>"""
    
    def _get_multi_cloud_css_styles(self, branding: BrandingConfig) -> str:
        """Get enhanced CSS styles for multi-cloud reporting"""
        
        base_styles = super()._get_css_styles(branding)
        
        multi_cloud_styles = """
        /* Multi-Cloud Specific Styles */
        .provider-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin: 25px 0;
        }
        
        .provider-card {
            background: linear-gradient(135deg, #f8fafc, #e2e8f0);
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-left: 5px solid var(--provider-color);
        }
        
        .provider-card.aws {
            --provider-color: #FF9900;
        }
        
        .provider-card.gcp {
            --provider-color: #4285F4;
        }
        
        .provider-card.azure {
            --provider-color: #0078D4;
        }
        
        .provider-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .provider-logo {
            width: 40px;
            height: 40px;
            margin-right: 15px;
            border-radius: 8px;
        }
        
        .provider-name {
            font-size: 20px;
            font-weight: bold;
            color: var(--provider-color);
        }
        
        .cost-comparison-chart {
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin: 25px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .service-category-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }
        
        .category-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-top: 4px solid var(--primary-color);
        }
        
        .category-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .category-icon {
            font-size: 24px;
            margin-right: 10px;
        }
        
        .category-name {
            font-size: 16px;
            font-weight: bold;
            color: var(--primary-color);
        }
        
        .provider-breakdown {
            margin-top: 15px;
        }
        
        .provider-cost-bar {
            display: flex;
            align-items: center;
            margin: 8px 0;
        }
        
        .provider-cost-label {
            min-width: 60px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .cost-bar {
            flex: 1;
            height: 20px;
            background: #e2e8f0;
            border-radius: 10px;
            margin: 0 10px;
            overflow: hidden;
        }
        
        .cost-bar-fill {
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        
        .cost-amount {
            min-width: 80px;
            text-align: right;
            font-size: 12px;
            font-weight: bold;
        }
        
        .trend-indicator {
            display: inline-flex;
            align-items: center;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .trend-increasing {
            background: #fee2e2;
            color: #dc2626;
        }
        
        .trend-decreasing {
            background: #d1fae5;
            color: #059669;
        }
        
        .trend-stable {
            background: #e5e7eb;
            color: #6b7280;
        }
        
        .optimization-opportunity {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
            border-left: 5px solid #f59e0b;
        }
        
        .opportunity-header {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .opportunity-icon {
            font-size: 20px;
            margin-right: 10px;
        }
        
        .opportunity-title {
            font-weight: bold;
            color: #92400e;
        }
        
        .savings-estimate {
            background: rgba(255, 255, 255, 0.8);
            padding: 10px;
            border-radius: 6px;
            margin-top: 10px;
            text-align: center;
        }
        
        .savings-amount {
            font-size: 18px;
            font-weight: bold;
            color: #059669;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .provider-grid {
                grid-template-columns: 1fr;
            }
            
            .service-category-grid {
                grid-template-columns: 1fr;
            }
            
            .provider-cost-bar {
                flex-direction: column;
                align-items: stretch;
            }
            
            .cost-bar {
                margin: 5px 0;
            }
        }
        """
        
        return base_styles + multi_cloud_styles
    
    def _build_multi_cloud_header(self, metadata: Dict, client_config: ClientConfig) -> str:
        """Build multi-cloud report header"""
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
            <div class="client-tagline">Multi-Cloud Cost Analysis Report</div>
        </div>
        <h1>Multi-Cloud Cost Analysis Report</h1>
        <div style="text-align: center; margin-bottom: 25px;">
            <span class="client-badge">Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}</span>
            <br>
            <small style="color: #6b7280; margin-top: 10px; display: block;">
                Analyzing {metadata['total_providers']} cloud providers • {metadata['total_records']} cost records • {metadata['date_range_days']} days of data
            </small>
        </div>"""
    
    def _build_multi_cloud_executive_summary(self, processed_data: Dict[str, Any]) -> str:
        """Build executive summary for multi-cloud costs"""
        
        total_cost = processed_data['cross_provider_comparison']['total_cost']
        cost_distribution = processed_data['cross_provider_comparison']['cost_distribution']
        trends = processed_data['trends']
        
        # Find dominant provider
        dominant_provider = max(cost_distribution.items(), key=lambda x: x[1]['cost'])
        
        # Overall trend
        overall_trend = trends.get('overall_trend', {})
        trend_icon = '📈' if overall_trend.get('change_percentage', 0) > 5 else '📉' if overall_trend.get('change_percentage', 0) < -5 else '➡️'
        
        return f"""
        <div class="summary">
            <h3>🌐 Multi-Cloud Executive Summary</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 15px;">
                <div>
                    <h4>Total Multi-Cloud Spend</h4>
                    <p style="font-size: 28px; margin: 5px 0; color: white;">${total_cost:,.2f}</p>
                </div>
                <div>
                    <h4>Dominant Provider</h4>
                    <p style="font-size: 20px; margin: 5px 0; color: white;">
                        {dominant_provider[0].value}<br>
                        <span style="font-size: 16px;">{dominant_provider[1]['percentage']:.1f}% of total</span>
                    </p>
                </div>
                <div>
                    <h4>Overall Trend</h4>
                    <p style="font-size: 20px; margin: 5px 0; color: white;">
                        {trend_icon} {overall_trend.get('change_percentage', 0):+.1f}%<br>
                        <span style="font-size: 16px;">{overall_trend.get('trend_direction', 'stable').title()}</span>
                    </p>
                </div>
            </div>
        </div>"""   
 
    def _build_provider_overview_section(self, processed_data: Dict[str, Any]) -> str:
        """Build provider overview section with individual provider cards"""
        
        provider_data = processed_data['provider_data']
        total_costs = processed_data['total_costs']
        trends = processed_data['trends']
        
        html = """
        <h2>☁️ Cloud Provider Overview</h2>
        <div class="provider-grid">"""
        
        for provider, cost in total_costs.items():
            provider_name = provider.value
            provider_class = provider_name.lower()
            
            # Get trend data
            provider_trend = trends.get('provider_trends', {}).get(provider, {})
            trend_direction = provider_trend.get('trend_direction', 'stable')
            trend_percentage = provider_trend.get('change_percentage', 0)
            
            trend_class = f"trend-{trend_direction}"
            trend_icon = '📈' if trend_direction == 'increasing' else '📉' if trend_direction == 'decreasing' else '➡️'
            
            # Calculate provider statistics
            provider_dates = provider_data.get(provider, {})
            total_services = set()
            total_accounts = set()
            
            for date_data in provider_dates.values():
                total_services.update(date_data.get('services', {}).keys())
                total_accounts.update(date_data.get('accounts', {}).keys())
            
            html += f"""
            <div class="provider-card {provider_class}">
                <div class="provider-header">
                    <div class="provider-name">{provider_name}</div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                    <div>
                        <strong>Total Cost:</strong><br>
                        <span style="font-size: 24px; color: var(--provider-color);">${cost:,.2f}</span>
                    </div>
                    <div>
                        <strong>Trend:</strong><br>
                        <span class="{trend_class}">{trend_icon} {trend_percentage:+.1f}%</span>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; font-size: 14px; color: #6b7280;">
                    <div>
                        <strong>Services:</strong> {len(total_services)}
                    </div>
                    <div>
                        <strong>Accounts:</strong> {len(total_accounts)}
                    </div>
                </div>
            </div>"""
        
        html += "</div>"
        return html
    
    def _build_cross_provider_comparison_section(self, processed_data: Dict[str, Any]) -> str:
        """Build cross-provider cost comparison section"""
        
        cost_distribution = processed_data['cross_provider_comparison']['cost_distribution']
        total_cost = processed_data['cross_provider_comparison']['total_cost']
        
        html = """
        <h2>⚖️ Cross-Provider Cost Comparison</h2>
        <div class="cost-comparison-chart">
            <h3>Cost Distribution by Provider</h3>
            <div style="margin: 20px 0;">"""
        
        for provider, data in cost_distribution.items():
            provider_name = provider.value
            cost = data['cost']
            percentage = data['percentage']
            
            # Get provider color
            provider_color = self.provider_colors.get(provider, "#6b7280")
            
            html += f"""
                <div class="provider-cost-bar">
                    <div class="provider-cost-label" style="color: {provider_color};">
                        <strong>{provider_name}</strong>
                    </div>
                    <div class="cost-bar">
                        <div class="cost-bar-fill" style="width: {percentage}%; background-color: {provider_color};"></div>
                    </div>
                    <div class="cost-amount">
                        ${cost:,.2f} ({percentage:.1f}%)
                    </div>
                </div>"""
        
        html += """
            </div>
        </div>"""
        
        # Add cost efficiency insights
        cost_leaders = processed_data['cross_provider_comparison']['cost_leaders']
        if cost_leaders:
            html += """
            <div class="cost-comparison-chart">
                <h3>💡 Cost Leadership by Service Category</h3>
                <p style="color: #6b7280; margin-bottom: 20px;">
                    Most cost-effective provider for each service category:
                </p>"""
            
            for category, leader_data in cost_leaders.items():
                provider = leader_data['provider']
                cost = leader_data['cost']
                provider_color = self.provider_colors.get(provider, "#6b7280")
                category_icon = self.service_category_icons.get(ServiceCategory(category), "📦")
                
                html += f"""
                <div style="display: flex; align-items: center; margin: 10px 0; padding: 10px; background: #f8fafc; border-radius: 8px;">
                    <span style="font-size: 20px; margin-right: 15px;">{category_icon}</span>
                    <div style="flex: 1;">
                        <strong>{category.replace('_', ' ').title()}</strong>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: {provider_color}; font-weight: bold;">{provider.value}</span><br>
                        <small style="color: #6b7280;">${cost:,.2f}</small>
                    </div>
                </div>"""
            
            html += "</div>"
        
        return html
    
    def _build_unified_service_categories_section(self, processed_data: Dict[str, Any]) -> str:
        """Build unified service categories section"""
        
        category_comparison = processed_data['cross_provider_comparison']['category_comparison']
        provider_data = processed_data['provider_data']
        
        html = """
        <h2>🏷️ Unified Service Categories</h2>
        <div class="service-category-grid">"""
        
        # Sort categories by total cost
        category_totals = {}
        for category, providers in category_comparison.items():
            if not category.endswith('_percentage'):
                total = sum(cost for provider, cost in providers.items() 
                           if isinstance(cost, (int, float, Decimal)) and not provider.endswith('_percentage'))
                category_totals[category] = total
        
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        
        for category, total_cost in sorted_categories[:8]:  # Show top 8 categories
            if total_cost == 0:
                continue
                
            category_icon = self.service_category_icons.get(ServiceCategory(category), "📦")
            
            html += f"""
            <div class="category-card">
                <div class="category-header">
                    <span class="category-icon">{category_icon}</span>
                    <div class="category-name">{category.replace('_', ' ').title()}</div>
                </div>
                <div style="text-align: center; margin: 15px 0;">
                    <div style="font-size: 24px; font-weight: bold; color: var(--primary-color);">
                        ${total_cost:,.2f}
                    </div>
                    <div style="font-size: 12px; color: #6b7280;">Total across all providers</div>
                </div>
                <div class="provider-breakdown">"""
            
            # Show breakdown by provider
            providers_in_category = category_comparison[category]
            for provider in provider_data.keys():
                provider_cost = providers_in_category.get(provider, Decimal('0'))
                percentage = providers_in_category.get(f"{provider}_percentage", 0)
                
                if provider_cost > 0:
                    provider_color = self.provider_colors.get(provider, "#6b7280")
                    
                    html += f"""
                    <div class="provider-cost-bar">
                        <div class="provider-cost-label" style="color: {provider_color};">
                            {provider.value}
                        </div>
                        <div class="cost-bar">
                            <div class="cost-bar-fill" style="width: {percentage}%; background-color: {provider_color};"></div>
                        </div>
                        <div class="cost-amount">
                            ${provider_cost:,.2f}
                        </div>
                    </div>"""
            
            html += """
                </div>
            </div>"""
        
        html += "</div>"
        return html
    
    def _build_multi_cloud_trends_section(self, processed_data: Dict[str, Any]) -> str:
        """Build multi-cloud trends analysis section"""
        
        trends = processed_data['trends']
        
        if trends.get('insufficient_data'):
            return """
            <h2>📈 Multi-Cloud Trends</h2>
            <div class="metric-card">
                <p>Insufficient data for trend analysis. More historical data needed.</p>
            </div>"""
        
        provider_trends = trends.get('provider_trends', {})
        overall_trend = trends.get('overall_trend', {})
        
        html = f"""
        <h2>📈 Multi-Cloud Trends</h2>
        <div class="metric-card">
            <h3>Overall Multi-Cloud Trend</h3>
            <p><strong>Analysis Period:</strong> {trends.get('analysis_period', 'N/A')}</p>"""
        
        if overall_trend:
            change_amount = overall_trend.get('change_amount', 0)
            change_percentage = overall_trend.get('change_percentage', 0)
            trend_direction = overall_trend.get('trend_direction', 'stable')
            
            trend_class = f"trend-{trend_direction}"
            trend_icon = '📈' if trend_direction == 'increasing' else '📉' if trend_direction == 'decreasing' else '➡️'
            
            html += f"""
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 15px 0;">
                <div>
                    <strong>Cost Change:</strong><br>
                    <span style="font-size: 20px;">${change_amount:+,.2f}</span>
                </div>
                <div>
                    <strong>Percentage Change:</strong><br>
                    <span class="{trend_class}" style="font-size: 20px;">{trend_icon} {change_percentage:+.1f}%</span>
                </div>
                <div>
                    <strong>Trend Direction:</strong><br>
                    <span style="font-size: 20px;">{trend_direction.title()}</span>
                </div>
            </div>"""
        
        html += "</div>"
        
        # Provider-specific trends
        if provider_trends:
            html += """
            <h3>Provider-Specific Trends</h3>
            <div class="provider-grid">"""
            
            for provider, trend_data in provider_trends.items():
                provider_name = provider.value
                provider_class = provider_name.lower()
                
                change_amount = trend_data.get('change_amount', 0)
                change_percentage = trend_data.get('change_percentage', 0)
                trend_direction = trend_data.get('trend_direction', 'stable')
                
                trend_class = f"trend-{trend_direction}"
                trend_icon = '📈' if trend_direction == 'increasing' else '📉' if trend_direction == 'decreasing' else '➡️'
                
                html += f"""
                <div class="provider-card {provider_class}">
                    <div class="provider-header">
                        <div class="provider-name">{provider_name} Trend</div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                        <div>
                            <strong>Change:</strong><br>
                            <span style="font-size: 18px;">${change_amount:+,.2f}</span>
                        </div>
                        <div>
                            <strong>Percentage:</strong><br>
                            <span class="{trend_class}" style="font-size: 18px;">{trend_icon} {change_percentage:+.1f}%</span>
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <span class="trend-indicator {trend_class}">
                            {trend_direction.title()} Trend
                        </span>
                    </div>
                </div>"""
            
            html += "</div>"
        
        return html
    
    def _build_cost_optimization_opportunities(self, processed_data: Dict[str, Any]) -> str:
        """Build cost optimization opportunities section"""
        
        cost_distribution = processed_data['cross_provider_comparison']['cost_distribution']
        cost_leaders = processed_data['cross_provider_comparison']['cost_leaders']
        trends = processed_data['trends']
        
        html = """
        <h2>💡 Cost Optimization Opportunities</h2>"""
        
        opportunities = []
        
        # Identify high-cost providers with increasing trends
        provider_trends = trends.get('provider_trends', {})
        for provider, data in cost_distribution.items():
            if data['percentage'] > 40:  # Dominant provider
                trend_data = provider_trends.get(provider, {})
                if trend_data.get('change_percentage', 0) > 10:
                    opportunities.append({
                        'title': f'Review {provider.value} Cost Growth',
                        'description': f'{provider.value} accounts for {data["percentage"]:.1f}% of total costs and is growing at {trend_data.get("change_percentage", 0):+.1f}%',
                        'savings_estimate': data['cost'] * 0.15,  # Assume 15% potential savings
                        'icon': '📊'
                    })
        
        # Service consolidation opportunities
        category_comparison = processed_data['cross_provider_comparison']['category_comparison']
        for category, providers in category_comparison.items():
            if not category.endswith('_percentage'):
                active_providers = sum(1 for provider, cost in providers.items() 
                                     if isinstance(cost, (int, float, Decimal)) and cost > 0 and not provider.endswith('_percentage'))
                
                if active_providers > 1:
                    total_category_cost = sum(cost for provider, cost in providers.items() 
                                            if isinstance(cost, (int, float, Decimal)) and not provider.endswith('_percentage'))
                    
                    if total_category_cost > 1000:  # Significant cost
                        opportunities.append({
                            'title': f'Consolidate {category.replace("_", " ").title()} Services',
                            'description': f'You\'re using {active_providers} providers for {category.replace("_", " ")} services. Consider consolidating to reduce complexity and potentially lower costs.',
                            'savings_estimate': total_category_cost * 0.10,  # Assume 10% savings from consolidation
                            'icon': '🔄'
                        })
        
        # Cost leadership opportunities
        for category, leader_data in cost_leaders.items():
            category_providers = category_comparison.get(category, {})
            for provider, cost in category_providers.items():
                if (isinstance(cost, (int, float, Decimal)) and not provider.endswith('_percentage') 
                    and provider != leader_data['provider'] and cost > leader_data['cost'] * 1.2):
                    
                    potential_savings = cost - leader_data['cost']
                    opportunities.append({
                        'title': f'Switch {category.replace("_", " ").title()} to {leader_data["provider"].value}',
                        'description': f'Your {provider.value} {category.replace("_", " ")} costs are ${cost:,.2f}, while {leader_data["provider"].value} offers similar services for ${leader_data["cost"]:,.2f}',
                        'savings_estimate': potential_savings,
                        'icon': '💰'
                    })
        
        # Sort opportunities by savings potential
        opportunities.sort(key=lambda x: x['savings_estimate'], reverse=True)
        
        if opportunities:
            total_potential_savings = sum(opp['savings_estimate'] for opp in opportunities[:5])
            
            html += f"""
            <div class="summary" style="background: linear-gradient(135deg, #059669, #10b981);">
                <h3>💰 Total Potential Savings</h3>
                <p style="font-size: 32px; margin: 10px 0; color: white;">
                    ${total_potential_savings:,.2f}
                </p>
                <p style="color: white; opacity: 0.9;">
                    Based on top {min(len(opportunities), 5)} optimization opportunities
                </p>
            </div>"""
            
            for i, opportunity in enumerate(opportunities[:5]):  # Show top 5 opportunities
                html += f"""
                <div class="optimization-opportunity">
                    <div class="opportunity-header">
                        <span class="opportunity-icon">{opportunity['icon']}</span>
                        <div class="opportunity-title">{opportunity['title']}</div>
                    </div>
                    <p>{opportunity['description']}</p>
                    <div class="savings-estimate">
                        <div class="savings-amount">Potential Savings: ${opportunity['savings_estimate']:,.2f}</div>
                    </div>
                </div>"""
        else:
            html += """
            <div class="metric-card">
                <p>No immediate optimization opportunities identified. Your multi-cloud setup appears well-optimized.</p>
            </div>"""
        
        return html
    
    def _upload_report_to_s3(self, html_content: str, client_config: ClientConfig) -> str:
        """Upload multi-cloud report to S3 and return the key"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"multi_cloud_report_{client_config.client_id}_{timestamp}.html"
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
                    'report_type': 'multi_cloud',
                    'generated_at': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Multi-cloud report uploaded to S3: s3://{self.s3_bucket}/{s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error uploading multi-cloud report to S3: {e}")
            raise