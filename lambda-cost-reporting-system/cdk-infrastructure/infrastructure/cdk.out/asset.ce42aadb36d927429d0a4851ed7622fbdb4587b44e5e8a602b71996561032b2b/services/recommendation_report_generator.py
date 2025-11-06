"""
Recommendation Report Generator

Enhanced report generator with comprehensive cost optimization recommendations:
- Cost optimization recommendations with estimated savings
- Implementation guidance and priority-based ordering
- Actionable insights with step-by-step instructions
- ROI calculations and impact assessments
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
    from .ai_enhanced_report_generator import AIEnhancedReportGenerator
    from .ai_insights_service_enhanced import AIInsights, Recommendation
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.multi_cloud_models import UnifiedCostRecord, CloudProvider, ServiceCategory
    from models.config_models import ClientConfig, BrandingConfig
    from utils.logging import create_logger
    from ai_enhanced_report_generator import AIEnhancedReportGenerator
    from ai_insights_service_enhanced import AIInsights, Recommendation
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class RecommendationReportGenerator(AIEnhancedReportGenerator):
    """Enhanced report generator with comprehensive recommendation sections"""
    
    def __init__(self, s3_bucket: str, s3_prefix: str = "reports", use_ai: bool = True):
        """
        Initialize Recommendation Report Generator
        
        Args:
            s3_bucket: S3 bucket name for storing reports
            s3_prefix: S3 prefix for report storage
            use_ai: Whether to use AI-powered recommendations
        """
        super().__init__(s3_bucket, s3_prefix, use_ai)
        
        # Recommendation categories and their icons
        self.recommendation_categories = {
            'cost_optimization': {'icon': '💰', 'title': 'Cost Optimization'},
            'resource_optimization': {'icon': '⚡', 'title': 'Resource Optimization'},
            'security': {'icon': '🔒', 'title': 'Security & Compliance'},
            'performance': {'icon': '🚀', 'title': 'Performance Enhancement'},
            'architecture_optimization': {'icon': '🏗️', 'title': 'Architecture Optimization'},
            'automation': {'icon': '🤖', 'title': 'Automation & Efficiency'},
            'governance': {'icon': '📋', 'title': 'Governance & Management'},
            'sustainability': {'icon': '🌱', 'title': 'Sustainability & Green Computing'}
        }
        
        # Priority levels and their styling
        self.priority_styles = {
            'critical': {'color': '#dc2626', 'bg': '#fef2f2', 'icon': '🚨'},
            'high': {'color': '#f59e0b', 'bg': '#fffbeb', 'icon': '⚠️'},
            'medium': {'color': '#3b82f6', 'bg': '#eff6ff', 'icon': '📊'},
            'low': {'color': '#6b7280', 'bg': '#f9fafb', 'icon': 'ℹ️'}
        }
        
        # Implementation effort indicators
        self.effort_indicators = {
            'low': {'icon': '🟢', 'text': 'Quick Win', 'description': 'Can be implemented within days'},
            'medium': {'icon': '🟡', 'text': 'Moderate Effort', 'description': 'Requires weeks to implement'},
            'high': {'icon': '🔴', 'text': 'Major Project', 'description': 'Requires months and significant resources'}
        }
    
    def generate_recommendation_enhanced_report(
        self, 
        unified_cost_data: List[UnifiedCostRecord], 
        client_config: ClientConfig,
        alert_results: Optional[Any] = None,
        budget_info: Optional[Dict[str, float]] = None,
        custom_recommendations: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate comprehensive report with enhanced recommendation sections
        
        Args:
            unified_cost_data: List of unified cost records from all providers
            client_config: Client configuration including branding
            alert_results: Optional threshold evaluation results
            budget_info: Optional budget information for context
            custom_recommendations: Optional custom recommendations to include
            
        Returns:
            S3 URL of the generated report
        """
        try:
            logger.info(f"Generating recommendation-enhanced report for client {client_config.client_id}")
            
            # Generate AI insights with recommendations
            ai_insights = None
            if self.use_ai and self.ai_insights_service and unified_cost_data:
                try:
                    ai_insights = self.ai_insights_service.orchestrate_insights_workflow(
                        client_id=client_config.client_id,
                        cost_data=unified_cost_data,
                        client_config=client_config,
                        budget_info=budget_info
                    )
                    logger.info(f"AI insights with recommendations generated for client {client_config.client_id}")
                except Exception as e:
                    logger.warning(f"Failed to generate AI insights: {e}")
                    ai_insights = None
            
            # Process multi-cloud data
            processed_data = self._process_multi_cloud_data(unified_cost_data)
            
            # Generate additional recommendations based on data analysis
            data_driven_recommendations = self._generate_data_driven_recommendations(
                processed_data, budget_info
            )
            
            # Combine all recommendations
            all_recommendations = []
            if ai_insights and ai_insights.recommendations:
                all_recommendations.extend(ai_insights.recommendations)
            if data_driven_recommendations:
                all_recommendations.extend(data_driven_recommendations)
            if custom_recommendations:
                all_recommendations.extend([self._convert_custom_recommendation(rec) for rec in custom_recommendations])
            
            # Process and prioritize recommendations
            processed_recommendations = self._process_and_prioritize_recommendations(
                all_recommendations, processed_data, budget_info
            )
            
            # Generate HTML content with enhanced recommendation sections
            html_content = self._build_recommendation_enhanced_html_content(
                processed_data, client_config, ai_insights, alert_results, processed_recommendations
            )
            
            # Upload to S3 and return URL
            s3_key = self._upload_recommendation_report_to_s3(html_content, client_config)
            
            logger.info(f"Recommendation-enhanced report generated successfully for client {client_config.client_id}")
            return f"s3://{self.s3_bucket}/{s3_key}"
            
        except Exception as e:
            logger.error(f"Error generating recommendation-enhanced report for client {client_config.client_id}: {e}")
            raise
    
    def _generate_data_driven_recommendations(
        self, 
        processed_data: Dict[str, Any], 
        budget_info: Optional[Dict[str, float]] = None
    ) -> List[Recommendation]:
        """Generate recommendations based on data analysis"""
        
        recommendations = []
        cost_distribution = processed_data['cross_provider_comparison']['cost_distribution']
        trends = processed_data['trends']
        
        # High-cost provider recommendations
        for provider, data in cost_distribution.items():
            if data['percentage'] > 60:  # Dominant provider
                recommendations.append(Recommendation(
                    title=f"Diversify from {provider.value} Dependency",
                    description=f"{provider.value} accounts for {data['percentage']:.1f}% of your total cloud spend (${data['cost']:,.2f}). Consider diversifying to reduce vendor lock-in and potentially lower costs through multi-cloud strategies.",
                    estimated_savings=float(data['cost']) * 0.12,  # 12% potential savings
                    implementation_effort="high",
                    priority="medium",
                    category="architecture_optimization",
                    affected_services=["all"],
                    confidence_score=0.75,
                    implementation_steps=[
                        "Conduct cost analysis of equivalent services across providers",
                        "Identify workloads suitable for migration",
                        "Develop migration strategy and timeline",
                        "Implement pilot migration for non-critical workloads",
                        "Monitor performance and costs post-migration"
                    ]
                ))
        
        # Trend-based recommendations
        if trends and not trends.get('insufficient_data'):
            provider_trends = trends.get('provider_trends', {})
            for provider, trend_data in provider_trends.items():
                if trend_data.get('change_percentage', 0) > 25:  # High growth
                    recommendations.append(Recommendation(
                        title=f"Investigate {provider.value} Cost Spike",
                        description=f"{provider.value} costs have increased by {trend_data['change_percentage']:.1f}% (${trend_data['change_amount']:,.2f}). This rapid growth warrants immediate investigation and optimization.",
                        estimated_savings=abs(trend_data['change_amount']) * 0.4,  # 40% of increase recoverable
                        implementation_effort="medium",
                        priority="high",
                        category="cost_optimization",
                        affected_services=[provider.value],
                        confidence_score=0.85,
                        implementation_steps=[
                            "Review detailed billing for cost spike drivers",
                            "Identify new or scaled resources causing increases",
                            "Evaluate necessity of increased spending",
                            "Implement cost controls and monitoring",
                            "Optimize or rightsize resources as needed"
                        ]
                    ))
        
        # Service consolidation recommendations
        category_comparison = processed_data['cross_provider_comparison']['category_comparison']
        for category, providers in category_comparison.items():
            if not category.endswith('_percentage'):
                active_providers = [p for p, cost in providers.items() 
                                 if isinstance(cost, (int, float, Decimal)) and cost > 100 and not p.endswith('_percentage')]
                
                if len(active_providers) > 2:  # Using multiple providers for same category
                    total_cost = sum(cost for p, cost in providers.items() 
                                   if isinstance(cost, (int, float, Decimal)) and not p.endswith('_percentage'))
                    
                    recommendations.append(Recommendation(
                        title=f"Consolidate {category.replace('_', ' ').title()} Services",
                        description=f"You're using {len(active_providers)} different providers for {category.replace('_', ' ')} services (total: ${total_cost:,.2f}). Consolidating to 1-2 providers could reduce complexity and costs.",
                        estimated_savings=float(total_cost) * 0.08,  # 8% savings from consolidation
                        implementation_effort="medium",
                        priority="medium",
                        category="architecture_optimization",
                        affected_services=[category],
                        confidence_score=0.70,
                        implementation_steps=[
                            "Compare service offerings and pricing across providers",
                            "Identify best-fit provider for your use case",
                            "Plan migration strategy for consolidation",
                            "Implement gradual migration with testing",
                            "Monitor performance and cost improvements"
                        ]
                    ))
        
        # Budget-based recommendations
        if budget_info:
            total_cost = float(processed_data['cross_provider_comparison']['total_cost'])
            monthly_budget = budget_info.get('monthly_budget', 0)
            
            if monthly_budget > 0 and total_cost > monthly_budget * 0.8:  # Approaching budget
                recommendations.append(Recommendation(
                    title="Implement Proactive Budget Controls",
                    description=f"Current spending (${total_cost:,.2f}) is approaching your monthly budget (${monthly_budget:,.2f}). Implement automated controls to prevent overruns.",
                    estimated_savings=max(total_cost - monthly_budget, 0),
                    implementation_effort="low",
                    priority="high",
                    category="governance",
                    affected_services=["all"],
                    confidence_score=0.90,
                    implementation_steps=[
                        "Set up billing alerts at 50%, 75%, and 90% of budget",
                        "Implement automatic resource scaling limits",
                        "Create approval workflows for large expenditures",
                        "Establish regular budget review meetings",
                        "Deploy cost monitoring dashboards"
                    ]
                ))
        
        return recommendations
    
    def _convert_custom_recommendation(self, custom_rec: Dict[str, Any]) -> Recommendation:
        """Convert custom recommendation dictionary to Recommendation object"""
        
        return Recommendation(
            title=custom_rec.get('title', 'Custom Recommendation'),
            description=custom_rec.get('description', 'No description provided'),
            estimated_savings=custom_rec.get('estimated_savings', 0),
            implementation_effort=custom_rec.get('implementation_effort', 'medium'),
            priority=custom_rec.get('priority', 'medium'),
            category=custom_rec.get('category', 'cost_optimization'),
            affected_services=custom_rec.get('affected_services', []),
            confidence_score=custom_rec.get('confidence_score', 0.5),
            implementation_steps=custom_rec.get('implementation_steps', [])
        )
    
    def _process_and_prioritize_recommendations(
        self, 
        recommendations: List[Recommendation], 
        processed_data: Dict[str, Any],
        budget_info: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Process and prioritize recommendations"""
        
        if not recommendations:
            return {'recommendations': [], 'total_savings': 0, 'categories': {}}
        
        # Calculate ROI and impact scores
        for rec in recommendations:
            # ROI calculation (simplified)
            implementation_cost = self._estimate_implementation_cost(rec.implementation_effort)
            rec.roi = (rec.estimated_savings / implementation_cost) if implementation_cost > 0 else 0
            
            # Impact score (combination of savings and confidence)
            rec.impact_score = (rec.estimated_savings * rec.confidence_score) / 1000  # Normalize
        
        # Sort by priority, then by impact score
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda x: (priority_order.get(x.priority, 4), -x.impact_score))
        
        # Group by category
        categories = {}
        for rec in recommendations:
            if rec.category not in categories:
                categories[rec.category] = []
            categories[rec.category].append(rec)
        
        # Calculate total potential savings
        total_savings = sum(rec.estimated_savings for rec in recommendations)
        
        # Calculate quick wins (low effort, high impact)
        quick_wins = [rec for rec in recommendations 
                     if rec.implementation_effort == 'low' and rec.estimated_savings > 500]
        
        # Calculate high-impact recommendations
        high_impact = [rec for rec in recommendations 
                      if rec.estimated_savings > 2000 or rec.priority in ['critical', 'high']]
        
        return {
            'recommendations': recommendations,
            'total_savings': total_savings,
            'categories': categories,
            'quick_wins': quick_wins,
            'high_impact': high_impact,
            'stats': {
                'total_recommendations': len(recommendations),
                'critical_priority': len([r for r in recommendations if r.priority == 'critical']),
                'high_priority': len([r for r in recommendations if r.priority == 'high']),
                'quick_wins_count': len(quick_wins),
                'high_impact_count': len(high_impact)
            }
        }
    
    def _estimate_implementation_cost(self, effort: str) -> float:
        """Estimate implementation cost based on effort level"""
        
        effort_costs = {
            'low': 1000,      # $1,000 for quick wins
            'medium': 5000,   # $5,000 for moderate effort
            'high': 20000     # $20,000 for major projects
        }
        
        return effort_costs.get(effort, 5000)
    
    def _build_recommendation_enhanced_html_content(
        self, 
        processed_data: Dict[str, Any], 
        client_config: ClientConfig,
        ai_insights: Optional[AIInsights] = None,
        alert_results: Optional[Any] = None,
        processed_recommendations: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build complete HTML content with enhanced recommendation sections"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{client_config.branding.company_name or client_config.client_name} - Cost Optimization Recommendations</title>
    {self._get_recommendation_enhanced_css_styles(client_config.branding)}
</head>
<body>
    <div class="container">
        {self._build_recommendation_header(processed_data['metadata'], client_config, processed_recommendations)}
        {self._build_alert_section(alert_results) if alert_results else ''}
        {self._build_recommendations_executive_summary(processed_data, processed_recommendations)}
        {self._build_quick_wins_section(processed_recommendations) if processed_recommendations else ''}
        {self._build_high_impact_recommendations(processed_recommendations) if processed_recommendations else ''}
        {self._build_recommendations_by_category(processed_recommendations) if processed_recommendations else ''}
        {self._build_implementation_roadmap(processed_recommendations) if processed_recommendations else ''}
        {self._build_ai_executive_summary(processed_data, ai_insights)}
        {self._build_ai_insights_overview(ai_insights) if ai_insights else ''}
        {self._build_provider_overview_section(processed_data)}
        {self._build_cross_provider_comparison_section(processed_data)}
        {self._build_roi_analysis_section(processed_recommendations) if processed_recommendations else ''}
        {self._build_footer(processed_data['metadata'], client_config)}
    </div>
</body>
</html>"""
    
    def _get_recommendation_enhanced_css_styles(self, branding: BrandingConfig) -> str:
        """Get enhanced CSS styles for recommendation reporting"""
        
        base_styles = super()._get_ai_enhanced_css_styles(branding)
        
        recommendation_styles = """
        /* Recommendation-Enhanced Specific Styles */
        .recommendation-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-left: 5px solid var(--rec-priority-color);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .recommendation-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        }
        
        .recommendation-card.critical {
            --rec-priority-color: #dc2626;
            background: linear-gradient(135deg, #fef2f2, #ffffff);
        }
        
        .recommendation-card.high {
            --rec-priority-color: #f59e0b;
            background: linear-gradient(135deg, #fffbeb, #ffffff);
        }
        
        .recommendation-card.medium {
            --rec-priority-color: #3b82f6;
            background: linear-gradient(135deg, #eff6ff, #ffffff);
        }
        
        .recommendation-card.low {
            --rec-priority-color: #6b7280;
            background: linear-gradient(135deg, #f9fafb, #ffffff);
        }
        
        .recommendation-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 15px;
        }
        
        .recommendation-title {
            font-size: 18px;
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 5px;
        }
        
        .recommendation-category {
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        
        .recommendation-badges {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
        }
        
        .priority-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            color: white;
        }
        
        .priority-critical {
            background: #dc2626;
        }
        
        .priority-high {
            background: #f59e0b;
        }
        
        .priority-medium {
            background: #3b82f6;
        }
        
        .priority-low {
            background: #6b7280;
        }
        
        .effort-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .effort-low {
            background: #d1fae5;
            color: #065f46;
        }
        
        .effort-medium {
            background: #fef3c7;
            color: #92400e;
        }
        
        .effort-high {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .savings-highlight {
            background: linear-gradient(135deg, #059669, #10b981);
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin: 15px 0;
        }
        
        .savings-amount {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .savings-label {
            font-size: 12px;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .implementation-steps {
            background: #f8fafc;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }
        
        .implementation-steps h5 {
            margin-top: 0;
            margin-bottom: 10px;
            color: #374151;
        }
        
        .implementation-steps ol {
            margin: 0;
            padding-left: 20px;
        }
        
        .implementation-steps li {
            margin-bottom: 5px;
            color: #6b7280;
            font-size: 14px;
        }
        
        .quick-wins-section {
            background: linear-gradient(135deg, #d1fae5, #a7f3d0);
            border-radius: 12px;
            padding: 25px;
            margin: 25px 0;
            border-left: 5px solid #059669;
        }
        
        .high-impact-section {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-radius: 12px;
            padding: 25px;
            margin: 25px 0;
            border-left: 5px solid #f59e0b;
        }
        
        .category-section {
            margin: 30px 0;
        }
        
        .category-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px;
            background: #f8fafc;
            border-radius: 10px;
        }
        
        .category-icon {
            font-size: 24px;
            margin-right: 15px;
        }
        
        .category-title {
            font-size: 20px;
            font-weight: bold;
            color: #1f2937;
        }
        
        .category-count {
            margin-left: auto;
            background: var(--primary-color);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .roadmap-timeline {
            position: relative;
            padding-left: 30px;
        }
        
        .roadmap-timeline::before {
            content: '';
            position: absolute;
            left: 15px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: var(--primary-color);
        }
        
        .roadmap-item {
            position: relative;
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .roadmap-item::before {
            content: '';
            position: absolute;
            left: -22px;
            top: 25px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--primary-color);
            border: 3px solid white;
            box-shadow: 0 0 0 2px var(--primary-color);
        }
        
        .roadmap-phase {
            font-size: 14px;
            color: var(--primary-color);
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }
        
        .roi-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }
        
        .roi-metric {
            background: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-top: 4px solid var(--primary-color);
        }
        
        .roi-value {
            font-size: 28px;
            font-weight: bold;
            color: var(--primary-color);
            margin-bottom: 5px;
        }
        
        .roi-label {
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .confidence-meter {
            display: flex;
            align-items: center;
            margin-top: 10px;
        }
        
        .confidence-bar {
            flex: 1;
            height: 6px;
            background: #e5e7eb;
            border-radius: 3px;
            margin: 0 10px;
            overflow: hidden;
        }
        
        .confidence-fill {
            height: 100%;
            background: linear-gradient(90deg, #dc2626, #f59e0b, #059669);
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        
        .confidence-label {
            font-size: 12px;
            color: #6b7280;
            min-width: 80px;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .recommendation-header {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .recommendation-badges {
                flex-direction: row;
                align-items: flex-start;
                margin-top: 10px;
            }
            
            .roi-metrics {
                grid-template-columns: 1fr;
            }
            
            .roadmap-timeline {
                padding-left: 20px;
            }
            
            .roadmap-item::before {
                left: -17px;
            }
        }
        """
        
        return base_styles + recommendation_styles 
   
    def _build_recommendation_header(self, metadata: Dict, client_config: ClientConfig, processed_recommendations: Optional[Dict[str, Any]]) -> str:
        """Build recommendation-focused report header"""
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
        
        recommendations_count = processed_recommendations['stats']['total_recommendations'] if processed_recommendations else 0
        total_savings = processed_recommendations['total_savings'] if processed_recommendations else 0
        
        return f"""
        <div class="client-header">
            <div class="client-logo-container">
                {logo_html}
            </div>
            <div class="client-tagline">Cost Optimization Recommendations Report</div>
        </div>
        <h1>Cost Optimization Recommendations Report</h1>
        <div style="text-align: center; margin-bottom: 25px;">
            <span class="client-badge">Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}</span>
            <br>
            <small style="color: #6b7280; margin-top: 10px; display: block;">
                {recommendations_count} recommendations • ${total_savings:,.0f} potential savings • {metadata['total_providers']} cloud providers analyzed
            </small>
        </div>"""
    
    def _build_recommendations_executive_summary(self, processed_data: Dict[str, Any], processed_recommendations: Optional[Dict[str, Any]]) -> str:
        """Build executive summary focused on recommendations"""
        
        if not processed_recommendations:
            return """
            <div class="summary">
                <h3>📊 Executive Summary</h3>
                <p>No specific recommendations available. Your multi-cloud setup appears well-optimized.</p>
            </div>"""
        
        stats = processed_recommendations['stats']
        total_savings = processed_recommendations['total_savings']
        
        return f"""
        <div class="summary">
            <h3>💡 Cost Optimization Executive Summary</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 15px;">
                <div>
                    <h4>Total Recommendations</h4>
                    <p style="font-size: 28px; margin: 5px 0; color: white;">{stats['total_recommendations']}</p>
                </div>
                <div>
                    <h4>Potential Savings</h4>
                    <p style="font-size: 28px; margin: 5px 0; color: white;">${total_savings:,.0f}</p>
                </div>
                <div>
                    <h4>Quick Wins</h4>
                    <p style="font-size: 28px; margin: 5px 0; color: white;">
                        {stats['quick_wins_count']}<br>
                        <span style="font-size: 16px;">Low effort, high impact</span>
                    </p>
                </div>
                <div>
                    <h4>High Priority</h4>
                    <p style="font-size: 28px; margin: 5px 0; color: white;">
                        {stats['critical_priority'] + stats['high_priority']}<br>
                        <span style="font-size: 16px;">Require immediate attention</span>
                    </p>
                </div>
            </div>
        </div>"""
    
    def _build_quick_wins_section(self, processed_recommendations: Dict[str, Any]) -> str:
        """Build quick wins section"""
        
        quick_wins = processed_recommendations.get('quick_wins', [])
        
        if not quick_wins:
            return ""
        
        total_quick_savings = sum(rec.estimated_savings for rec in quick_wins)
        
        html = f"""
        <div class="quick-wins-section">
            <h2>🚀 Quick Wins - Immediate Impact</h2>
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 24px; font-weight: bold; color: #065f46;">
                    ${total_quick_savings:,.0f} in potential savings
                </div>
                <div style="font-size: 14px; color: #059669; margin-top: 5px;">
                    {len(quick_wins)} recommendations that can be implemented quickly
                </div>
            </div>"""
        
        for rec in quick_wins[:5]:  # Show top 5 quick wins
            effort_info = self.effort_indicators.get(rec.implementation_effort, self.effort_indicators['medium'])
            
            html += f"""
            <div class="recommendation-card {rec.priority}">
                <div class="recommendation-header">
                    <div>
                        <div class="recommendation-title">{rec.title}</div>
                        <div class="recommendation-category">
                            {self.recommendation_categories.get(rec.category, {}).get('icon', '📦')} 
                            {self.recommendation_categories.get(rec.category, {}).get('title', rec.category.replace('_', ' ').title())}
                        </div>
                    </div>
                    <div class="recommendation-badges">
                        <span class="effort-badge effort-{rec.implementation_effort}">
                            {effort_info['icon']} {effort_info['text']}
                        </span>
                    </div>
                </div>
                <p>{rec.description}</p>
                <div class="savings-highlight">
                    <div class="savings-amount">${rec.estimated_savings:,.0f}</div>
                    <div class="savings-label">Estimated Annual Savings</div>
                </div>
                <div class="confidence-meter">
                    <span class="confidence-label">Confidence:</span>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: {rec.confidence_score * 100}%;"></div>
                    </div>
                    <span class="confidence-label">{rec.confidence_score:.0%}</span>
                </div>
            </div>"""
        
        html += "</div>"
        return html
    
    def _build_high_impact_recommendations(self, processed_recommendations: Dict[str, Any]) -> str:
        """Build high impact recommendations section"""
        
        high_impact = processed_recommendations.get('high_impact', [])
        
        if not high_impact:
            return ""
        
        total_high_impact_savings = sum(rec.estimated_savings for rec in high_impact)
        
        html = f"""
        <div class="high-impact-section">
            <h2>🎯 High-Impact Recommendations</h2>
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 24px; font-weight: bold; color: #92400e;">
                    ${total_high_impact_savings:,.0f} in potential savings
                </div>
                <div style="font-size: 14px; color: #f59e0b; margin-top: 5px;">
                    {len(high_impact)} high-priority recommendations for maximum impact
                </div>
            </div>"""
        
        for rec in high_impact[:3]:  # Show top 3 high impact
            priority_style = self.priority_styles.get(rec.priority, self.priority_styles['medium'])
            effort_info = self.effort_indicators.get(rec.implementation_effort, self.effort_indicators['medium'])
            
            html += f"""
            <div class="recommendation-card {rec.priority}">
                <div class="recommendation-header">
                    <div>
                        <div class="recommendation-title">{rec.title}</div>
                        <div class="recommendation-category">
                            {self.recommendation_categories.get(rec.category, {}).get('icon', '📦')} 
                            {self.recommendation_categories.get(rec.category, {}).get('title', rec.category.replace('_', ' ').title())}
                        </div>
                    </div>
                    <div class="recommendation-badges">
                        <span class="priority-badge priority-{rec.priority}">
                            {priority_style['icon']} {rec.priority.upper()}
                        </span>
                        <span class="effort-badge effort-{rec.implementation_effort}">
                            {effort_info['icon']} {effort_info['text']}
                        </span>
                    </div>
                </div>
                <p>{rec.description}</p>
                <div class="savings-highlight">
                    <div class="savings-amount">${rec.estimated_savings:,.0f}</div>
                    <div class="savings-label">Estimated Annual Savings</div>
                </div>
                <div class="confidence-meter">
                    <span class="confidence-label">Confidence:</span>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: {rec.confidence_score * 100}%;"></div>
                    </div>
                    <span class="confidence-label">{rec.confidence_score:.0%}</span>
                </div>
                {self._build_implementation_steps(rec.implementation_steps)}
            </div>"""
        
        html += "</div>"
        return html
    
    def _build_recommendations_by_category(self, processed_recommendations: Dict[str, Any]) -> str:
        """Build recommendations organized by category"""
        
        categories = processed_recommendations.get('categories', {})
        
        if not categories:
            return ""
        
        html = """
        <h2>📋 Recommendations by Category</h2>"""
        
        # Sort categories by total savings potential
        category_savings = {}
        for category, recs in categories.items():
            category_savings[category] = sum(rec.estimated_savings for rec in recs)
        
        sorted_categories = sorted(category_savings.items(), key=lambda x: x[1], reverse=True)
        
        for category, total_savings in sorted_categories:
            recommendations = categories[category]
            category_info = self.recommendation_categories.get(category, {'icon': '📦', 'title': category.replace('_', ' ').title()})
            
            html += f"""
            <div class="category-section">
                <div class="category-header">
                    <span class="category-icon">{category_info['icon']}</span>
                    <div class="category-title">{category_info['title']}</div>
                    <div class="category-count">{len(recommendations)} recommendations</div>
                </div>
                <div style="text-align: center; margin-bottom: 20px;">
                    <div style="font-size: 20px; font-weight: bold; color: var(--primary-color);">
                        ${total_savings:,.0f} potential savings
                    </div>
                </div>"""
            
            for rec in recommendations:
                priority_style = self.priority_styles.get(rec.priority, self.priority_styles['medium'])
                effort_info = self.effort_indicators.get(rec.implementation_effort, self.effort_indicators['medium'])
                
                html += f"""
                <div class="recommendation-card {rec.priority}">
                    <div class="recommendation-header">
                        <div>
                            <div class="recommendation-title">{rec.title}</div>
                        </div>
                        <div class="recommendation-badges">
                            <span class="priority-badge priority-{rec.priority}">
                                {priority_style['icon']} {rec.priority.upper()}
                            </span>
                            <span class="effort-badge effort-{rec.implementation_effort}">
                                {effort_info['icon']} {effort_info['text']}
                            </span>
                        </div>
                    </div>
                    <p>{rec.description}</p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                        <div class="savings-highlight">
                            <div class="savings-amount">${rec.estimated_savings:,.0f}</div>
                            <div class="savings-label">Estimated Savings</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 18px; font-weight: bold; color: #374151;">
                                {rec.roi:.1f}x
                            </div>
                            <div style="font-size: 12px; color: #6b7280;">ROI Estimate</div>
                        </div>
                    </div>
                    <div class="confidence-meter">
                        <span class="confidence-label">Confidence:</span>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: {rec.confidence_score * 100}%;"></div>
                        </div>
                        <span class="confidence-label">{rec.confidence_score:.0%}</span>
                    </div>
                </div>"""
            
            html += "</div>"
        
        return html
    
    def _build_implementation_roadmap(self, processed_recommendations: Dict[str, Any]) -> str:
        """Build implementation roadmap section"""
        
        recommendations = processed_recommendations.get('recommendations', [])
        
        if not recommendations:
            return ""
        
        # Group recommendations by implementation phases
        quick_wins = [rec for rec in recommendations if rec.implementation_effort == 'low']
        medium_term = [rec for rec in recommendations if rec.implementation_effort == 'medium']
        long_term = [rec for rec in recommendations if rec.implementation_effort == 'high']
        
        html = """
        <h2>🗺️ Implementation Roadmap</h2>
        <div class="roadmap-timeline">"""
        
        # Phase 1: Quick Wins (0-30 days)
        if quick_wins:
            phase1_savings = sum(rec.estimated_savings for rec in quick_wins)
            html += f"""
            <div class="roadmap-item">
                <div class="roadmap-phase">Phase 1: Quick Wins (0-30 days)</div>
                <h4>Immediate Impact Opportunities</h4>
                <p>Focus on low-effort, high-impact recommendations that can be implemented quickly.</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 15px 0;">
                    <div>
                        <strong>Recommendations:</strong> {len(quick_wins)}
                    </div>
                    <div>
                        <strong>Potential Savings:</strong> ${phase1_savings:,.0f}
                    </div>
                </div>
                <div style="background: #f8fafc; padding: 15px; border-radius: 8px; margin-top: 15px;">
                    <strong>Key Actions:</strong>
                    <ul style="margin: 10px 0; padding-left: 20px;">"""
            
            for rec in quick_wins[:3]:
                html += f"<li>{rec.title}</li>"
            
            if len(quick_wins) > 3:
                html += f"<li>...and {len(quick_wins) - 3} more quick wins</li>"
            
            html += """
                    </ul>
                </div>
            </div>"""
        
        # Phase 2: Medium-term (1-3 months)
        if medium_term:
            phase2_savings = sum(rec.estimated_savings for rec in medium_term)
            html += f"""
            <div class="roadmap-item">
                <div class="roadmap-phase">Phase 2: Strategic Improvements (1-3 months)</div>
                <h4>Moderate Effort, High Value</h4>
                <p>Implement strategic changes that require more planning and coordination.</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 15px 0;">
                    <div>
                        <strong>Recommendations:</strong> {len(medium_term)}
                    </div>
                    <div>
                        <strong>Potential Savings:</strong> ${phase2_savings:,.0f}
                    </div>
                </div>
                <div style="background: #f8fafc; padding: 15px; border-radius: 8px; margin-top: 15px;">
                    <strong>Key Actions:</strong>
                    <ul style="margin: 10px 0; padding-left: 20px;">"""
            
            for rec in medium_term[:3]:
                html += f"<li>{rec.title}</li>"
            
            if len(medium_term) > 3:
                html += f"<li>...and {len(medium_term) - 3} more strategic improvements</li>"
            
            html += """
                    </ul>
                </div>
            </div>"""
        
        # Phase 3: Long-term (3-12 months)
        if long_term:
            phase3_savings = sum(rec.estimated_savings for rec in long_term)
            html += f"""
            <div class="roadmap-item">
                <div class="roadmap-phase">Phase 3: Transformational Changes (3-12 months)</div>
                <h4>Major Projects, Maximum Impact</h4>
                <p>Large-scale initiatives that require significant resources but offer substantial returns.</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 15px 0;">
                    <div>
                        <strong>Recommendations:</strong> {len(long_term)}
                    </div>
                    <div>
                        <strong>Potential Savings:</strong> ${phase3_savings:,.0f}
                    </div>
                </div>
                <div style="background: #f8fafc; padding: 15px; border-radius: 8px; margin-top: 15px;">
                    <strong>Key Actions:</strong>
                    <ul style="margin: 10px 0; padding-left: 20px;">"""
            
            for rec in long_term[:3]:
                html += f"<li>{rec.title}</li>"
            
            if len(long_term) > 3:
                html += f"<li>...and {len(long_term) - 3} more transformational changes</li>"
            
            html += """
                    </ul>
                </div>
            </div>"""
        
        html += "</div>"
        return html
    
    def _build_roi_analysis_section(self, processed_recommendations: Dict[str, Any]) -> str:
        """Build ROI analysis section"""
        
        recommendations = processed_recommendations.get('recommendations', [])
        
        if not recommendations:
            return ""
        
        # Calculate aggregate metrics
        total_savings = processed_recommendations['total_savings']
        total_implementation_cost = sum(self._estimate_implementation_cost(rec.implementation_effort) for rec in recommendations)
        average_roi = sum(rec.roi for rec in recommendations) / len(recommendations) if recommendations else 0
        average_confidence = sum(rec.confidence_score for rec in recommendations) / len(recommendations) if recommendations else 0
        
        # Payback period (simplified calculation)
        monthly_savings = total_savings / 12
        payback_months = (total_implementation_cost / monthly_savings) if monthly_savings > 0 else 0
        
        html = f"""
        <h2>📊 ROI Analysis</h2>
        <div class="roi-metrics">
            <div class="roi-metric">
                <div class="roi-value">${total_savings:,.0f}</div>
                <div class="roi-label">Total Potential Savings</div>
            </div>
            <div class="roi-metric">
                <div class="roi-value">${total_implementation_cost:,.0f}</div>
                <div class="roi-label">Estimated Implementation Cost</div>
            </div>
            <div class="roi-metric">
                <div class="roi-value">{average_roi:.1f}x</div>
                <div class="roi-label">Average ROI</div>
            </div>
            <div class="roi-metric">
                <div class="roi-value">{payback_months:.1f}</div>
                <div class="roi-label">Payback Period (Months)</div>
            </div>
            <div class="roi-metric">
                <div class="roi-value">{average_confidence:.0%}</div>
                <div class="roi-label">Average Confidence</div>
            </div>
            <div class="roi-metric">
                <div class="roi-value">{len(recommendations)}</div>
                <div class="roi-label">Total Recommendations</div>
            </div>
        </div>"""
        
        # ROI breakdown by category
        categories = processed_recommendations.get('categories', {})
        if categories:
            html += """
            <h3>ROI by Category</h3>
            <div style="background: white; border-radius: 12px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">"""
            
            for category, recs in categories.items():
                category_savings = sum(rec.estimated_savings for rec in recs)
                category_cost = sum(self._estimate_implementation_cost(rec.implementation_effort) for rec in recs)
                category_roi = (category_savings / category_cost) if category_cost > 0 else 0
                category_info = self.recommendation_categories.get(category, {'icon': '📦', 'title': category.replace('_', ' ').title()})
                
                html += f"""
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 15px; margin: 10px 0; background: #f8fafc; border-radius: 8px;">
                    <div style="display: flex; align-items: center;">
                        <span style="font-size: 20px; margin-right: 15px;">{category_info['icon']}</span>
                        <div>
                            <div style="font-weight: bold;">{category_info['title']}</div>
                            <div style="font-size: 12px; color: #6b7280;">{len(recs)} recommendations</div>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 18px; font-weight: bold; color: var(--primary-color);">{category_roi:.1f}x ROI</div>
                        <div style="font-size: 12px; color: #6b7280;">${category_savings:,.0f} savings</div>
                    </div>
                </div>"""
            
            html += "</div>"
        
        return html
    
    def _build_implementation_steps(self, steps: List[str]) -> str:
        """Build implementation steps section"""
        
        if not steps:
            return ""
        
        html = """
        <div class="implementation-steps">
            <h5>Implementation Steps:</h5>
            <ol>"""
        
        for step in steps:
            html += f"<li>{step}</li>"
        
        html += """
            </ol>
        </div>"""
        
        return html
    
    def _upload_recommendation_report_to_s3(self, html_content: str, client_config: ClientConfig) -> str:
        """Upload recommendation report to S3 and return the key"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"recommendation_report_{client_config.client_id}_{timestamp}.html"
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
                    'report_type': 'recommendation_enhanced',
                    'generated_at': datetime.now().isoformat(),
                    'ai_powered': 'true'
                }
            )
            
            logger.info(f"Recommendation report uploaded to S3: s3://{self.s3_bucket}/{s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error uploading recommendation report to S3: {e}")
            raise