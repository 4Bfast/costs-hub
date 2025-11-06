"""
AI-Enhanced Report Generator

Integrates AI insights into multi-cloud reports with:
- AI-generated executive summaries
- Anomaly detection results with explanations
- Trend analysis and forecasting sections
- Natural language insights and recommendations
"""

import boto3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal

try:
    from ..models.multi_cloud_models import UnifiedCostRecord, CloudProvider, ServiceCategory
    from ..models.config_models import ClientConfig, BrandingConfig
    from ..utils.logging import create_logger as get_logger
    from .multi_cloud_report_generator import MultiCloudReportGenerator
    from .ai_insights_service_enhanced import EnhancedAIInsightsService, AIInsights, AggregatedInsight
    from .anomaly_detection_engine import Anomaly
    from .trend_analysis_service import TrendAnalysis
    from .forecasting_engine import ForecastResult
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.multi_cloud_models import UnifiedCostRecord, CloudProvider, ServiceCategory
    from models.config_models import ClientConfig, BrandingConfig
    from utils.logging import create_logger
    from multi_cloud_report_generator import MultiCloudReportGenerator
    from ai_insights_service_enhanced import EnhancedAIInsightsService, AIInsights, AggregatedInsight
    from anomaly_detection_engine import Anomaly
    from trend_analysis_service import TrendAnalysis
    from forecasting_engine import ForecastResult
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class AIEnhancedReportGenerator(MultiCloudReportGenerator):
    """Enhanced report generator with integrated AI insights"""
    
    def __init__(self, s3_bucket: str, s3_prefix: str = "reports", use_ai: bool = True):
        """
        Initialize AI-Enhanced Report Generator
        
        Args:
            s3_bucket: S3 bucket name for storing reports
            s3_prefix: S3 prefix for report storage
            use_ai: Whether to use AI-powered insights
        """
        super().__init__(s3_bucket, s3_prefix)
        self.use_ai = use_ai
        
        if use_ai:
            try:
                self.ai_insights_service = EnhancedAIInsightsService(use_ai=True)
            except Exception as e:
                logger.warning(f"AI insights service unavailable: {e}")
                self.use_ai = False
                self.ai_insights_service = None
        else:
            self.ai_insights_service = None
    
    def generate_ai_enhanced_report(
        self, 
        unified_cost_data: List[UnifiedCostRecord], 
        client_config: ClientConfig,
        alert_results: Optional[Any] = None,
        budget_info: Optional[Dict[str, float]] = None
    ) -> str:
        """
        Generate comprehensive AI-enhanced multi-cloud report
        
        Args:
            unified_cost_data: List of unified cost records from all providers
            client_config: Client configuration including branding
            alert_results: Optional threshold evaluation results
            budget_info: Optional budget information for AI context
            
        Returns:
            S3 URL of the generated report
        """
        try:
            logger.info(f"Generating AI-enhanced report for client {client_config.client_id}")
            
            # Generate AI insights if available
            ai_insights = None
            if self.use_ai and self.ai_insights_service and unified_cost_data:
                try:
                    ai_insights = self.ai_insights_service.orchestrate_insights_workflow(
                        client_id=client_config.client_id,
                        cost_data=unified_cost_data,
                        client_config=client_config,
                        budget_info=budget_info
                    )
                    logger.info(f"AI insights generated successfully for client {client_config.client_id}")
                except Exception as e:
                    logger.warning(f"Failed to generate AI insights: {e}")
                    ai_insights = None
            
            # Process multi-cloud data
            processed_data = self._process_multi_cloud_data(unified_cost_data)
            
            # Generate HTML content with AI insights integration
            html_content = self._build_ai_enhanced_html_content(
                processed_data, client_config, ai_insights, alert_results
            )
            
            # Upload to S3 and return URL
            s3_key = self._upload_ai_enhanced_report_to_s3(html_content, client_config)
            
            logger.info(f"AI-enhanced report generated successfully for client {client_config.client_id}")
            return f"s3://{self.s3_bucket}/{s3_key}"
            
        except Exception as e:
            logger.error(f"Error generating AI-enhanced report for client {client_config.client_id}: {e}")
            raise
    
    def _build_ai_enhanced_html_content(
        self, 
        processed_data: Dict[str, Any], 
        client_config: ClientConfig,
        ai_insights: Optional[AIInsights] = None,
        alert_results: Optional[Any] = None
    ) -> str:
        """Build complete AI-enhanced HTML content"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{client_config.branding.company_name or client_config.client_name} - AI-Enhanced Multi-Cloud Cost Analysis</title>
    {self._get_ai_enhanced_css_styles(client_config.branding)}
</head>
<body>
    <div class="container">
        {self._build_ai_enhanced_header(processed_data['metadata'], client_config, ai_insights)}
        {self._build_alert_section(alert_results) if alert_results else ''}
        {self._build_ai_executive_summary(processed_data, ai_insights)}
        {self._build_ai_insights_overview(ai_insights) if ai_insights else ''}
        {self._build_anomaly_detection_section(ai_insights) if ai_insights and ai_insights.anomalies else ''}
        {self._build_trend_analysis_section(ai_insights) if ai_insights and ai_insights.trends else ''}
        {self._build_forecasting_section(ai_insights) if ai_insights and ai_insights.forecasts else ''}
        {self._build_provider_overview_section(processed_data)}
        {self._build_cross_provider_comparison_section(processed_data)}
        {self._build_unified_service_categories_section(processed_data)}
        {self._build_multi_cloud_trends_section(processed_data)}
        {self._build_ai_risk_assessment(ai_insights) if ai_insights else ''}
        {self._build_cost_optimization_opportunities(processed_data)}
        {self._build_footer(processed_data['metadata'], client_config)}
    </div>
</body>
</html>"""
    
    def _get_ai_enhanced_css_styles(self, branding: BrandingConfig) -> str:
        """Get enhanced CSS styles for AI-enhanced reporting"""
        
        base_styles = super()._get_multi_cloud_css_styles(branding)
        
        ai_styles = """
        /* AI-Enhanced Specific Styles */
        .ai-insight-card {
            background: linear-gradient(135deg, #eff6ff, #dbeafe);
            border-radius: 12px;
            padding: 25px;
            margin: 20px 0;
            border-left: 5px solid #3b82f6;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.1);
        }
        
        .ai-insight-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .ai-icon {
            font-size: 24px;
            margin-right: 12px;
        }
        
        .ai-insight-title {
            font-size: 18px;
            font-weight: bold;
            color: #1e40af;
        }
        
        .ai-confidence-badge {
            margin-left: auto;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .confidence-high {
            background: #d1fae5;
            color: #065f46;
        }
        
        .confidence-medium {
            background: #fef3c7;
            color: #92400e;
        }
        
        .confidence-low {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .anomaly-card {
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            border-left: 5px solid #dc2626;
            box-shadow: 0 4px 15px rgba(220, 38, 38, 0.1);
        }
        
        .anomaly-card.critical {
            border-left-color: #dc2626;
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
        }
        
        .anomaly-card.high {
            border-left-color: #f59e0b;
            background: linear-gradient(135deg, #fffbeb, #fef3c7);
        }
        
        .anomaly-card.medium {
            border-left-color: #3b82f6;
            background: linear-gradient(135deg, #eff6ff, #dbeafe);
        }
        
        .anomaly-card.low {
            border-left-color: #6b7280;
            background: linear-gradient(135deg, #f9fafb, #f3f4f6);
        }
        
        .anomaly-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }
        
        .anomaly-title {
            font-weight: bold;
            font-size: 16px;
        }
        
        .anomaly-severity {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            color: white;
        }
        
        .severity-critical {
            background: #dc2626;
        }
        
        .severity-high {
            background: #f59e0b;
        }
        
        .severity-medium {
            background: #3b82f6;
        }
        
        .severity-low {
            background: #6b7280;
        }
        
        .trend-card {
            background: linear-gradient(135deg, #f0fdf4, #dcfce7);
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            border-left: 5px solid #059669;
            box-shadow: 0 4px 15px rgba(5, 150, 105, 0.1);
        }
        
        .forecast-card {
            background: linear-gradient(135deg, #fefbeb, #fef3c7);
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            border-left: 5px solid #f59e0b;
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.1);
        }
        
        .forecast-card.warning {
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-left-color: #dc2626;
        }
        
        .ai-narrative {
            background: linear-gradient(135deg, #f8fafc, #e2e8f0);
            border-radius: 12px;
            padding: 25px;
            margin: 25px 0;
            border-left: 5px solid var(--primary-color);
            font-size: 16px;
            line-height: 1.6;
            color: #374151;
        }
        
        .ai-narrative h4 {
            color: var(--primary-color);
            margin-top: 0;
            margin-bottom: 15px;
        }
        
        .risk-assessment {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-radius: 12px;
            padding: 25px;
            margin: 25px 0;
            border-left: 5px solid #f59e0b;
        }
        
        .risk-level {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 25px;
            font-size: 14px;
            font-weight: bold;
            text-transform: uppercase;
            margin: 5px 5px 5px 0;
        }
        
        .risk-low {
            background: #d1fae5;
            color: #065f46;
        }
        
        .risk-medium {
            background: #fef3c7;
            color: #92400e;
        }
        
        .risk-high {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .risk-critical {
            background: #dc2626;
            color: white;
        }
        
        .insight-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }
        
        .key-insight {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-top: 4px solid var(--primary-color);
        }
        
        .insight-icon {
            font-size: 32px;
            margin-bottom: 15px;
            display: block;
        }
        
        .insight-text {
            font-size: 14px;
            color: #374151;
            line-height: 1.5;
        }
        
        .ai-powered-badge {
            display: inline-flex;
            align-items: center;
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }
        
        .ai-powered-badge::before {
            content: "🤖";
            margin-right: 6px;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .insight-grid {
                grid-template-columns: 1fr;
            }
            
            .ai-insight-header {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .ai-confidence-badge {
                margin-left: 0;
                margin-top: 10px;
            }
        }
        """
        
        return base_styles + ai_styles
    
    def _build_ai_enhanced_header(self, metadata: Dict, client_config: ClientConfig, ai_insights: Optional[AIInsights]) -> str:
        """Build AI-enhanced report header"""
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
        
        ai_badge = '<span class="ai-powered-badge">AI-Powered</span>' if ai_insights else ''
        
        return f"""
        <div class="client-header">
            <div class="client-logo-container">
                {logo_html}
            </div>
            <div class="client-tagline">AI-Enhanced Multi-Cloud Cost Analysis Report{ai_badge}</div>
        </div>
        <h1>AI-Enhanced Multi-Cloud Cost Analysis Report</h1>
        <div style="text-align: center; margin-bottom: 25px;">
            <span class="client-badge">Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}</span>
            <br>
            <small style="color: #6b7280; margin-top: 10px; display: block;">
                Analyzing {metadata['total_providers']} cloud providers • {metadata['total_records']} cost records • {metadata['date_range_days']} days of data
                {f" • AI Confidence: {ai_insights.confidence_score:.1%}" if ai_insights else ""}
            </small>
        </div>"""
    
    def _build_ai_executive_summary(self, processed_data: Dict[str, Any], ai_insights: Optional[AIInsights]) -> str:
        """Build AI-generated executive summary"""
        
        # Base multi-cloud summary
        base_summary = super()._build_multi_cloud_executive_summary(processed_data)
        
        if not ai_insights or not ai_insights.executive_summary:
            return base_summary
        
        # Enhanced with AI narrative
        ai_summary = f"""
        <div class="ai-narrative">
            <h4>🤖 AI-Generated Executive Summary</h4>
            <p>{ai_insights.executive_summary}</p>
        </div>"""
        
        return base_summary + ai_summary
    
    def _build_ai_insights_overview(self, ai_insights: AIInsights) -> str:
        """Build AI insights overview section"""
        
        if not ai_insights.key_insights:
            return ""
        
        html = """
        <h2>🧠 AI Insights Overview</h2>
        <div class="insight-grid">"""
        
        insight_icons = ["💡", "📊", "⚡", "🎯", "🔍"]
        
        for i, insight in enumerate(ai_insights.key_insights[:5]):
            icon = insight_icons[i % len(insight_icons)]
            
            html += f"""
            <div class="key-insight">
                <span class="insight-icon">{icon}</span>
                <div class="insight-text">{insight}</div>
            </div>"""
        
        html += "</div>"
        return html
    
    def _build_anomaly_detection_section(self, ai_insights: AIInsights) -> str:
        """Build anomaly detection results section"""
        
        if not ai_insights.anomalies:
            return """
            <h2>🔍 Anomaly Detection</h2>
            <div class="ai-insight-card">
                <div class="ai-insight-header">
                    <span class="ai-icon">✅</span>
                    <div class="ai-insight-title">No Anomalies Detected</div>
                    <span class="ai-confidence-badge confidence-high">High Confidence</span>
                </div>
                <p>AI analysis found no significant cost anomalies in your multi-cloud environment. Your spending patterns appear normal and consistent.</p>
            </div>"""
        
        html = f"""
        <h2>🔍 Anomaly Detection</h2>
        <div class="ai-insight-card">
            <div class="ai-insight-header">
                <span class="ai-icon">🚨</span>
                <div class="ai-insight-title">{len(ai_insights.anomalies)} Anomalies Detected</div>
                <span class="ai-confidence-badge confidence-high">AI-Powered</span>
            </div>
            <p>AI analysis has identified unusual spending patterns that require attention:</p>
        </div>"""
        
        # Sort anomalies by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_anomalies = sorted(ai_insights.anomalies, 
                                key=lambda x: severity_order.get(x.severity.value, 4))
        
        for anomaly in sorted_anomalies:
            severity = anomaly.severity.value
            anomaly_icon = {
                'critical': '🚨',
                'high': '⚠️',
                'medium': '📊',
                'low': 'ℹ️'
            }.get(severity, '📊')
            
            html += f"""
            <div class="anomaly-card {severity}">
                <div class="anomaly-header">
                    <div class="anomaly-title">{anomaly_icon} {anomaly.type.value.replace('_', ' ').title()}</div>
                    <span class="anomaly-severity severity-{severity}">{severity.upper()}</span>
                </div>
                <p><strong>Description:</strong> {anomaly.description}</p>
                <p><strong>Cost Impact:</strong> ${abs(anomaly.cost_impact):,.2f}</p>
                <p><strong>Affected Services:</strong> {', '.join(anomaly.affected_services[:3])}{'...' if len(anomaly.affected_services) > 3 else ''}</p>
                <p><strong>Detection Method:</strong> {anomaly.detection_method}</p>
                <p><strong>Confidence:</strong> {anomaly.confidence_score:.1%}</p>
                {f'<p><strong>Recommended Actions:</strong></p><ul>{"".join(f"<li>{action}</li>" for action in anomaly.recommended_actions)}</ul>' if anomaly.recommended_actions else ''}
            </div>"""
        
        return html
    
    def _build_trend_analysis_section(self, ai_insights: AIInsights) -> str:
        """Build AI-powered trend analysis section"""
        
        trends = ai_insights.trends
        if not trends:
            return ""
        
        html = """
        <h2>📈 AI Trend Analysis</h2>"""
        
        # Overall trend
        if trends.overall_trend:
            trend = trends.overall_trend
            trend_icon = '📈' if trend.growth_rate > 5 else '📉' if trend.growth_rate < -5 else '➡️'
            
            html += f"""
            <div class="trend-card">
                <div class="ai-insight-header">
                    <span class="ai-icon">{trend_icon}</span>
                    <div class="ai-insight-title">Overall Cost Trend: {trend.direction.value.title()}</div>
                    <span class="ai-confidence-badge confidence-high">AI Analysis</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 15px 0;">
                    <div>
                        <strong>Growth Rate:</strong><br>
                        <span style="font-size: 20px;">{trend.growth_rate:+.1f}%</span>
                    </div>
                    <div>
                        <strong>Volatility:</strong><br>
                        <span style="font-size: 20px;">{trend.volatility:.1f}</span>
                    </div>
                    <div>
                        <strong>Trend Strength:</strong><br>
                        <span style="font-size: 20px;">{trend.trend_strength:.1f}</span>
                    </div>
                </div>
                <p><strong>AI Interpretation:</strong> {trend.significance.value.replace('_', ' ').title()} trend detected with {trends.trend_confidence:.1%} confidence.</p>
            </div>"""
        
        # Service-specific trends (top 5)
        if trends.service_trends:
            html += """
            <h3>Service-Specific Trends</h3>"""
            
            # Sort by growth rate magnitude
            sorted_service_trends = sorted(trends.service_trends.items(), 
                                         key=lambda x: abs(x[1].growth_rate), reverse=True)
            
            for service, trend in sorted_service_trends[:5]:
                trend_icon = '📈' if trend.growth_rate > 5 else '📉' if trend.growth_rate < -5 else '➡️'
                
                html += f"""
                <div class="trend-card">
                    <div class="ai-insight-header">
                        <span class="ai-icon">{trend_icon}</span>
                        <div class="ai-insight-title">{service} Trend</div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div>
                            <strong>Growth Rate:</strong> {trend.growth_rate:+.1f}%
                        </div>
                        <div>
                            <strong>Direction:</strong> {trend.direction.value.title()}
                        </div>
                    </div>
                </div>"""
        
        return html
    
    def _build_forecasting_section(self, ai_insights: AIInsights) -> str:
        """Build AI forecasting section"""
        
        forecasts = ai_insights.forecasts
        if not forecasts:
            return ""
        
        html = """
        <h2>🔮 AI Cost Forecasting</h2>"""
        
        # Overall forecast
        if forecasts.total_forecast:
            forecast_amount = forecasts.total_forecast.get('amount', 0)
            confidence = forecasts.total_forecast.get('confidence', 0)
            
            # Determine forecast severity
            forecast_class = "forecast-card"
            if forecast_amount > 0:
                # Assume current cost for comparison (simplified)
                change_percentage = 15  # Placeholder - would calculate from actual data
                if change_percentage > 25:
                    forecast_class += " warning"
            
            confidence_level = 'high' if confidence > 0.8 else 'medium' if confidence > 0.6 else 'low'
            
            html += f"""
            <div class="{forecast_class}">
                <div class="ai-insight-header">
                    <span class="ai-icon">🎯</span>
                    <div class="ai-insight-title">Cost Forecast</div>
                    <span class="ai-confidence-badge confidence-{confidence_level}">{confidence:.1%} Confidence</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 15px 0;">
                    <div>
                        <strong>Forecasted Amount:</strong><br>
                        <span style="font-size: 24px;">${forecast_amount:,.2f}</span>
                    </div>
                    <div>
                        <strong>Forecast Period:</strong><br>
                        <span style="font-size: 18px;">{forecasts.forecast_period} days</span>
                    </div>
                    <div>
                        <strong>Model Accuracy:</strong><br>
                        <span style="font-size: 18px;">{forecasts.accuracy_assessment.value.title()}</span>
                    </div>
                </div>
                <p><strong>AI Analysis:</strong> Based on historical patterns and current trends, the forecast model predicts the above spending with {confidence:.1%} confidence.</p>
            </div>"""
        
        # Service-level forecasts (if available)
        if hasattr(forecasts, 'service_forecasts') and forecasts.service_forecasts:
            html += """
            <h3>Service-Level Forecasts</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">"""
            
            for service, service_forecast in list(forecasts.service_forecasts.items())[:6]:
                amount = service_forecast.get('amount', 0)
                confidence = service_forecast.get('confidence', 0)
                
                html += f"""
                <div class="forecast-card">
                    <h4>{service}</h4>
                    <p><strong>Forecast:</strong> ${amount:,.2f}</p>
                    <p><strong>Confidence:</strong> {confidence:.1%}</p>
                </div>"""
            
            html += "</div>"
        
        return html
    
    def _build_ai_risk_assessment(self, ai_insights: AIInsights) -> str:
        """Build AI risk assessment section"""
        
        if not ai_insights.risk_assessment:
            return ""
        
        risk_assessment = ai_insights.risk_assessment
        
        html = """
        <h2>⚠️ AI Risk Assessment</h2>
        <div class="risk-assessment">
            <div class="ai-insight-header">
                <span class="ai-icon">🛡️</span>
                <div class="ai-insight-title">Multi-Cloud Risk Analysis</div>
                <span class="ai-confidence-badge confidence-high">AI-Powered</span>
            </div>"""
        
        # Overall risk level
        overall_risk = risk_assessment.get('overall_risk_level', 'medium')
        risk_score = risk_assessment.get('risk_score', 0.5)
        
        html += f"""
            <div style="text-align: center; margin: 20px 0;">
                <div style="font-size: 18px; margin-bottom: 10px;">Overall Risk Level</div>
                <span class="risk-level risk-{overall_risk}">{overall_risk.upper()}</span>
                <div style="font-size: 14px; color: #6b7280; margin-top: 10px;">
                    Risk Score: {risk_score:.2f}/1.0
                </div>
            </div>"""
        
        # Risk categories
        risk_categories = risk_assessment.get('risk_categories', {})
        if risk_categories:
            html += """
            <h4>Risk Categories</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">"""
            
            for category, risk_data in risk_categories.items():
                risk_level = risk_data.get('level', 'medium')
                description = risk_data.get('description', 'No description available')
                
                html += f"""
                <div style="background: rgba(255, 255, 255, 0.8); padding: 15px; border-radius: 8px;">
                    <h5 style="margin-top: 0;">{category.replace('_', ' ').title()}</h5>
                    <span class="risk-level risk-{risk_level}">{risk_level.upper()}</span>
                    <p style="font-size: 14px; margin-top: 10px;">{description}</p>
                </div>"""
            
            html += "</div>"
        
        # Risk mitigation recommendations
        risk_recommendations = risk_assessment.get('recommendations', [])
        if risk_recommendations:
            html += """
            <h4>Risk Mitigation Recommendations</h4>
            <ul>"""
            
            for recommendation in risk_recommendations[:5]:
                html += f"<li>{recommendation}</li>"
            
            html += "</ul>"
        
        html += "</div>"
        return html
    
    def _upload_ai_enhanced_report_to_s3(self, html_content: str, client_config: ClientConfig) -> str:
        """Upload AI-enhanced report to S3 and return the key"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ai_enhanced_report_{client_config.client_id}_{timestamp}.html"
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
                    'report_type': 'ai_enhanced_multi_cloud',
                    'generated_at': datetime.now().isoformat(),
                    'ai_powered': 'true'
                }
            )
            
            logger.info(f"AI-enhanced report uploaded to S3: s3://{self.s3_bucket}/{s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error uploading AI-enhanced report to S3: {e}")
            raise