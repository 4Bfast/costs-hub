"""
Enhanced AI Insights Service - Main Orchestrator

This is the enhanced version implementing task 5.1 requirements:
- Main orchestrator for AI-powered cost analysis
- Advanced workflow for anomaly detection, trend analysis, and forecasting
- Enhanced insight aggregation and ranking logic
"""

import logging
import math
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum

try:
    from models.multi_cloud_models import UnifiedCostRecord
    from models.config_models import ClientConfig
    from utils.logging import create_logger as get_logger
    from services.bedrock_service import BedrockService
    from services.anomaly_detection_engine import AnomalyDetectionEngine, Anomaly
    from services.trend_analysis_service import TrendAnalyzer, TrendAnalysis
    from services.forecasting_engine import ForecastingEngine, ForecastResult
except ImportError:
    # Mock imports for testing
    UnifiedCostRecord = None
    ClientConfig = None
    BedrockService = None
    AnomalyDetectionEngine = None
    Anomaly = None
    TrendAnalyzer = None
    TrendAnalysis = None
    ForecastingEngine = None
    ForecastResult = None
    
    def get_logger(name):
        class MockLogger:
            def info(self, msg): print(f"INFO: {msg}")
            def warning(self, msg): print(f"WARNING: {msg}")
            def error(self, msg): print(f"ERROR: {msg}")
        return MockLogger()

try:
    logger = get_logger(__name__)
except:
    class MockLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
    logger = MockLogger()


class InsightCategory(Enum):
    """Categories for insight classification"""
    ANOMALY = "anomaly"
    TREND = "trend"
    FORECAST = "forecast"
    RECOMMENDATION = "recommendation"
    RISK = "risk"
    OPPORTUNITY = "opportunity"


class InsightPriority(Enum):
    """Priority levels for insights"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AggregatedInsight:
    """Aggregated insight with enhanced metadata"""
    id: str
    category: InsightCategory
    priority: InsightPriority
    title: str
    description: str
    confidence_score: float
    business_impact_score: float
    actionability_score: float
    severity_score: float
    estimated_savings: float
    affected_services: List[str]
    related_insights: List[str]
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class Recommendation:
    """Cost optimization recommendation"""
    title: str
    description: str
    estimated_savings: float
    implementation_effort: str  # low, medium, high
    priority: str  # high, medium, low
    category: str  # cost_optimization, security, performance
    affected_services: List[str]
    confidence_score: float
    implementation_steps: List[str]


@dataclass
class AIInsights:
    """Complete AI insights result"""
    executive_summary: str
    anomalies: List[Anomaly]
    trends: TrendAnalysis
    forecasts: ForecastResult
    recommendations: List[Recommendation]
    key_insights: List[str]
    risk_assessment: Dict[str, Any]
    confidence_score: float
    metadata: Dict[str, Any]


class InsightAggregator:
    """
    Advanced insight aggregation engine that combines insights from multiple sources
    and creates unified, actionable insights with proper deduplication and correlation.
    """
    
    def __init__(self):
        self.deduplication_threshold = 0.8
        self.correlation_threshold = 0.7
        
    def aggregate_insights(
        self,
        anomalies: List[Anomaly],
        trends: TrendAnalysis,
        forecasts: ForecastResult,
        recommendations: List[Recommendation],
        cost_data: List[UnifiedCostRecord]
    ) -> List[AggregatedInsight]:
        """
        Aggregate insights from all analysis components
        
        Args:
            anomalies: Detected anomalies
            trends: Trend analysis results
            forecasts: Forecast results
            recommendations: Generated recommendations
            cost_data: Historical cost data
            
        Returns:
            List of aggregated insights
        """
        aggregated_insights = []
        
        # Convert anomalies to insights
        anomaly_insights = self._convert_anomalies_to_insights(anomalies, cost_data)
        aggregated_insights.extend(anomaly_insights)
        
        # Convert trends to insights
        if trends:
            trend_insights = self._convert_trends_to_insights(trends, cost_data)
            aggregated_insights.extend(trend_insights)
        
        # Convert forecasts to insights
        if forecasts:
            forecast_insights = self._convert_forecasts_to_insights(forecasts, cost_data)
            aggregated_insights.extend(forecast_insights)
        
        # Convert recommendations to insights
        recommendation_insights = self._convert_recommendations_to_insights(recommendations)
        aggregated_insights.extend(recommendation_insights)
        
        # Deduplicate and correlate insights
        deduplicated_insights = self._deduplicate_insights(aggregated_insights)
        correlated_insights = self._correlate_insights(deduplicated_insights)
        
        return correlated_insights
    
    def _convert_anomalies_to_insights(
        self, 
        anomalies: List[Anomaly], 
        cost_data: List[UnifiedCostRecord]
    ) -> List[AggregatedInsight]:
        """Convert anomalies to aggregated insights"""
        insights = []
        
        for i, anomaly in enumerate(anomalies):
            # Calculate business impact based on cost impact and affected services
            business_impact = min(abs(anomaly.cost_impact) / 1000, 1.0)  # Normalize to $1000
            
            # Calculate actionability based on recommended actions
            actionability = 0.8 if anomaly.recommended_actions else 0.3
            
            # Map severity to score
            severity_map = {'critical': 1.0, 'high': 0.8, 'medium': 0.6, 'low': 0.4}
            severity_score = severity_map.get(anomaly.severity.value, 0.5)
            
            insight = AggregatedInsight(
                id=f"anomaly_{i}_{anomaly.type.value}",
                category=InsightCategory.ANOMALY,
                priority=InsightPriority(anomaly.severity.value),
                title=f"Anomaly Detected: {anomaly.type.value.replace('_', ' ').title()}",
                description=anomaly.description,
                confidence_score=anomaly.confidence_score,
                business_impact_score=business_impact,
                actionability_score=actionability,
                severity_score=severity_score,
                estimated_savings=abs(anomaly.cost_impact) * 0.7,  # Assume 70% recoverable
                affected_services=anomaly.affected_services,
                related_insights=[],
                metadata={
                    'anomaly_type': anomaly.type.value,
                    'detection_method': anomaly.detection_method,
                    'cost_impact': anomaly.cost_impact,
                    'recommended_actions': anomaly.recommended_actions
                },
                timestamp=anomaly.timestamp
            )
            insights.append(insight)
        
        return insights
    
    def _convert_trends_to_insights(
        self, 
        trends: TrendAnalysis, 
        cost_data: List[UnifiedCostRecord]
    ) -> List[AggregatedInsight]:
        """Convert trend analysis to aggregated insights"""
        insights = []
        
        # Overall trend insight
        if trends.overall_trend.significance.value != 'none':
            priority = InsightPriority.HIGH if trends.overall_trend.growth_rate > 25 else InsightPriority.MEDIUM
            
            insight = AggregatedInsight(
                id="trend_overall",
                category=InsightCategory.TREND,
                priority=priority,
                title=f"Overall Cost Trend: {trends.overall_trend.direction.value.title()}",
                description=f"Costs are {trends.overall_trend.direction.value} at {trends.overall_trend.growth_rate:.1f}% rate",
                confidence_score=trends.trend_confidence,
                business_impact_score=min(abs(trends.overall_trend.growth_rate) / 50, 1.0),
                actionability_score=0.7,
                severity_score=min(abs(trends.overall_trend.growth_rate) / 30, 1.0),
                estimated_savings=0,  # Trend insights don't directly provide savings
                affected_services=["all"],
                related_insights=[],
                metadata={
                    'growth_rate': trends.overall_trend.growth_rate,
                    'volatility': trends.overall_trend.volatility,
                    'trend_strength': trends.overall_trend.trend_strength
                },
                timestamp=datetime.utcnow()
            )
            insights.append(insight)
        
        return insights
    
    def _convert_forecasts_to_insights(
        self, 
        forecasts: ForecastResult, 
        cost_data: List[UnifiedCostRecord]
    ) -> List[AggregatedInsight]:
        """Convert forecast results to aggregated insights"""
        insights = []
        
        if forecasts.accuracy_assessment.value in ['high', 'medium']:
            current_cost = sum(record.total_cost for record in cost_data[-30:]) if cost_data else 0
            forecast_amount = forecasts.total_forecast.get('amount', 0)
            
            if forecast_amount > 0 and current_cost > 0:
                change_percentage = ((forecast_amount - current_cost) / current_cost) * 100
                
                if abs(change_percentage) > 10:  # Significant change
                    priority = InsightPriority.HIGH if abs(change_percentage) > 25 else InsightPriority.MEDIUM
                    
                    insight = AggregatedInsight(
                        id="forecast_overall",
                        category=InsightCategory.FORECAST,
                        priority=priority,
                        title=f"Cost Forecast: {change_percentage:+.1f}% Change Expected",
                        description=f"Forecasted costs: ${forecast_amount:.2f} ({change_percentage:+.1f}% change)",
                        confidence_score=forecasts.total_forecast.get('confidence', 0.5),
                        business_impact_score=min(abs(change_percentage) / 50, 1.0),
                        actionability_score=0.6,
                        severity_score=min(abs(change_percentage) / 30, 1.0),
                        estimated_savings=0,
                        affected_services=["all"],
                        related_insights=[],
                        metadata={
                            'forecast_amount': forecast_amount,
                            'current_amount': current_cost,
                            'change_percentage': change_percentage,
                            'forecast_period': forecasts.forecast_period
                        },
                        timestamp=datetime.utcnow()
                    )
                    insights.append(insight)
        
        return insights
    
    def _convert_recommendations_to_insights(
        self, 
        recommendations: List[Recommendation]
    ) -> List[AggregatedInsight]:
        """Convert recommendations to aggregated insights"""
        insights = []
        
        for i, rec in enumerate(recommendations):
            # Map recommendation priority to insight priority
            priority_map = {
                'critical': InsightPriority.CRITICAL,
                'high': InsightPriority.HIGH,
                'medium': InsightPriority.MEDIUM,
                'low': InsightPriority.LOW
            }
            
            # Calculate actionability based on implementation effort
            effort_to_actionability = {'low': 0.9, 'medium': 0.7, 'high': 0.4}
            actionability = effort_to_actionability.get(rec.implementation_effort, 0.5)
            
            insight = AggregatedInsight(
                id=f"recommendation_{i}",
                category=InsightCategory.RECOMMENDATION,
                priority=priority_map.get(rec.priority, InsightPriority.MEDIUM),
                title=rec.title,
                description=rec.description,
                confidence_score=rec.confidence_score,
                business_impact_score=min(rec.estimated_savings / 1000, 1.0),  # Normalize to $1000
                actionability_score=actionability,
                severity_score=0.5,  # Recommendations are opportunities, not problems
                estimated_savings=rec.estimated_savings,
                affected_services=rec.affected_services,
                related_insights=[],
                metadata={
                    'category': rec.category,
                    'implementation_effort': rec.implementation_effort,
                    'implementation_steps': rec.implementation_steps
                },
                timestamp=datetime.utcnow()
            )
            insights.append(insight)
        
        return insights
    
    def _deduplicate_insights(self, insights: List[AggregatedInsight]) -> List[AggregatedInsight]:
        """Remove duplicate insights based on similarity"""
        if not insights:
            return insights
        
        unique_insights = []
        
        for insight in insights:
            is_duplicate = False
            
            for existing_insight in unique_insights:
                similarity = self._calculate_insight_similarity(insight, existing_insight)
                
                if similarity > self.deduplication_threshold:
                    # Keep the insight with higher confidence or business impact
                    if (insight.confidence_score > existing_insight.confidence_score or
                        insight.business_impact_score > existing_insight.business_impact_score):
                        # Replace existing insight
                        unique_insights.remove(existing_insight)
                        unique_insights.append(insight)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_insights.append(insight)
        
        return unique_insights
    
    def _correlate_insights(self, insights: List[AggregatedInsight]) -> List[AggregatedInsight]:
        """Find correlations between insights and update related_insights"""
        for i, insight1 in enumerate(insights):
            for j, insight2 in enumerate(insights[i+1:], i+1):
                correlation = self._calculate_insight_correlation(insight1, insight2)
                
                if correlation > self.correlation_threshold:
                    insight1.related_insights.append(insight2.id)
                    insight2.related_insights.append(insight1.id)
        
        return insights
    
    def _calculate_insight_similarity(
        self, 
        insight1: AggregatedInsight, 
        insight2: AggregatedInsight
    ) -> float:
        """Calculate similarity between two insights"""
        # Same category and similar affected services
        if insight1.category != insight2.category:
            return 0.0
        
        # Calculate service overlap
        services1 = set(insight1.affected_services)
        services2 = set(insight2.affected_services)
        
        if not services1 or not services2:
            return 0.0
        
        service_overlap = len(services1.intersection(services2)) / len(services1.union(services2))
        
        # Calculate title similarity (simple word overlap)
        words1 = set(insight1.title.lower().split())
        words2 = set(insight2.title.lower().split())
        title_similarity = len(words1.intersection(words2)) / len(words1.union(words2)) if words1.union(words2) else 0
        
        # Combined similarity
        return (service_overlap * 0.6 + title_similarity * 0.4)
    
    def _calculate_insight_correlation(
        self, 
        insight1: AggregatedInsight, 
        insight2: AggregatedInsight
    ) -> float:
        """Calculate correlation between two insights"""
        # Different categories can be correlated
        correlation_score = 0.0
        
        # Service overlap correlation
        services1 = set(insight1.affected_services)
        services2 = set(insight2.affected_services)
        
        if services1 and services2:
            service_overlap = len(services1.intersection(services2)) / len(services1.union(services2))
            correlation_score += service_overlap * 0.4
        
        # Category correlation (some categories naturally correlate)
        category_correlations = {
            (InsightCategory.ANOMALY, InsightCategory.RECOMMENDATION): 0.8,
            (InsightCategory.TREND, InsightCategory.FORECAST): 0.7,
            (InsightCategory.TREND, InsightCategory.RECOMMENDATION): 0.6,
            (InsightCategory.FORECAST, InsightCategory.RECOMMENDATION): 0.5
        }
        
        category_pair = (insight1.category, insight2.category)
        reverse_pair = (insight2.category, insight1.category)
        
        if category_pair in category_correlations:
            correlation_score += category_correlations[category_pair] * 0.3
        elif reverse_pair in category_correlations:
            correlation_score += category_correlations[reverse_pair] * 0.3
        
        # Time correlation (insights from similar time periods)
        time_diff = abs((insight1.timestamp - insight2.timestamp).total_seconds())
        time_correlation = max(0, 1 - (time_diff / 86400))  # 1 day = 0 correlation
        correlation_score += time_correlation * 0.3
        
        return min(correlation_score, 1.0)


class InsightRanker:
    """
    Advanced insight ranking engine that prioritizes insights based on multiple
    criteria including business impact, confidence, actionability, and urgency.
    """
    
    def __init__(self, ranking_weights: Optional[Dict[str, float]] = None):
        """
        Initialize insight ranker
        
        Args:
            ranking_weights: Custom weights for ranking criteria
        """
        self.ranking_weights = ranking_weights or {
            'severity': 0.3,
            'confidence': 0.25,
            'business_impact': 0.25,
            'actionability': 0.2
        }
    
    def rank_insights(
        self, 
        insights: List[AggregatedInsight],
        client_context: Optional[Dict[str, Any]] = None
    ) -> List[AggregatedInsight]:
        """
        Rank insights by importance and relevance
        
        Args:
            insights: List of aggregated insights
            client_context: Client-specific context for ranking
            
        Returns:
            Ranked list of insights
        """
        if not insights:
            return insights
        
        # Calculate ranking scores
        scored_insights = []
        for insight in insights:
            score = self._calculate_ranking_score(insight, client_context)
            scored_insights.append((insight, score))
        
        # Sort by score (descending)
        scored_insights.sort(key=lambda x: x[1], reverse=True)
        
        # Update priorities based on ranking
        ranked_insights = []
        for i, (insight, score) in enumerate(scored_insights):
            # Adjust priority based on final ranking
            if i < len(scored_insights) * 0.2:  # Top 20%
                if insight.priority != InsightPriority.CRITICAL:
                    insight.priority = InsightPriority.HIGH
            elif i < len(scored_insights) * 0.5:  # Top 50%
                if insight.priority == InsightPriority.LOW:
                    insight.priority = InsightPriority.MEDIUM
            
            ranked_insights.append(insight)
        
        return ranked_insights
    
    def _calculate_ranking_score(
        self, 
        insight: AggregatedInsight,
        client_context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate comprehensive ranking score for an insight"""
        
        # Base scores (already normalized 0-1)
        severity_score = insight.severity_score
        confidence_score = insight.confidence_score
        business_impact_score = insight.business_impact_score
        actionability_score = insight.actionability_score
        
        # Apply client context adjustments
        if client_context:
            # Boost cost optimization insights for budget-constrained clients
            if (client_context.get('budget_constraints') and 
                insight.category in [InsightCategory.RECOMMENDATION, InsightCategory.ANOMALY]):
                business_impact_score = min(business_impact_score * 1.2, 1.0)
            
            # Boost capacity planning insights for growing clients
            if (client_context.get('growth_stage') == 'scaling' and
                insight.category == InsightCategory.FORECAST):
                business_impact_score = min(business_impact_score * 1.1, 1.0)
        
        # Calculate weighted score
        final_score = (
            severity_score * self.ranking_weights['severity'] +
            confidence_score * self.ranking_weights['confidence'] +
            business_impact_score * self.ranking_weights['business_impact'] +
            actionability_score * self.ranking_weights['actionability']
        )
        
        # Apply category-specific boosts
        category_boosts = {
            InsightCategory.ANOMALY: 1.1,  # Anomalies are urgent
            InsightCategory.RECOMMENDATION: 1.05,  # Recommendations are actionable
            InsightCategory.TREND: 1.0,
            InsightCategory.FORECAST: 0.95,  # Forecasts are less urgent
            InsightCategory.RISK: 1.1,
            InsightCategory.OPPORTUNITY: 1.0
        }
        
        final_score *= category_boosts.get(insight.category, 1.0)
        
        return min(final_score, 1.0)


class EnhancedAIInsightsService:
    """
    Enhanced AI insights orchestration service implementing task 5.1 requirements:
    - Main orchestrator for AI-powered cost analysis
    - Advanced workflow for anomaly detection, trend analysis, and forecasting
    - Enhanced insight aggregation and ranking logic
    """
    
    def __init__(self, use_ai: bool = True):
        """
        Initialize enhanced AI insights service
        
        Args:
            use_ai: Whether to use AI-powered analysis
        """
        self.use_ai = use_ai
        
        # Core AI analysis engines
        self.anomaly_detector = AnomalyDetectionEngine(use_ai=use_ai)
        self.trend_analyzer = TrendAnalyzer()
        self.forecasting_engine = ForecastingEngine(use_ai=use_ai)
        
        # Enhanced insight processing components
        self.insight_aggregator = InsightAggregator()
        self.insight_ranker = InsightRanker()
        
        # Workflow orchestration state
        self.workflow_state = {}
        self.insight_cache = {}
        
        # Workflow configuration
        self.workflow_config = {
            'parallel_processing': True,
            'cache_enabled': True,
            'quality_threshold': 0.7,
            'max_insights_per_category': 10,
            'insight_ranking_weights': {
                'severity': 0.3,
                'confidence': 0.25,
                'business_impact': 0.25,
                'actionability': 0.2
            }
        }
        
        if use_ai:
            try:
                self.bedrock_service = BedrockService()
            except Exception as e:
                logger.warning(f"AI service unavailable: {e}")
                self.use_ai = False
    
    def orchestrate_insights_workflow(
        self, 
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig] = None,
        budget_info: Optional[Dict[str, float]] = None,
        workflow_options: Optional[Dict[str, Any]] = None
    ) -> AIInsights:
        """
        Enhanced orchestration workflow implementing task 5.1 requirements
        
        Args:
            client_id: Client identifier
            cost_data: Historical cost data
            client_config: Client configuration
            budget_info: Budget information
            workflow_options: Workflow configuration options
            
        Returns:
            Complete AI insights with enhanced aggregation and ranking
        """
        workflow_id = f"{client_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Initialize workflow state
            self.workflow_state[workflow_id] = {
                'client_id': client_id,
                'status': 'initializing',
                'start_time': datetime.utcnow(),
                'steps_completed': [],
                'steps_failed': [],
                'current_step': None
            }
            
            logger.info(f"Starting enhanced insights workflow for client {client_id}")
            
            # Step 1: Anomaly Detection
            self.workflow_state[workflow_id]['current_step'] = 'anomaly_detection'
            anomalies = self._execute_anomaly_detection(cost_data, budget_info)
            self.workflow_state[workflow_id]['steps_completed'].append('anomaly_detection')
            
            # Step 2: Trend Analysis
            self.workflow_state[workflow_id]['current_step'] = 'trend_analysis'
            trends = self._execute_trend_analysis(cost_data)
            self.workflow_state[workflow_id]['steps_completed'].append('trend_analysis')
            
            # Step 3: Forecasting
            self.workflow_state[workflow_id]['current_step'] = 'forecasting'
            forecasts = self._execute_forecasting(cost_data)
            self.workflow_state[workflow_id]['steps_completed'].append('forecasting')
            
            # Step 4: Recommendation Generation (simplified for this implementation)
            self.workflow_state[workflow_id]['current_step'] = 'recommendation_generation'
            recommendations = self._generate_basic_recommendations(anomalies, trends, forecasts)
            self.workflow_state[workflow_id]['steps_completed'].append('recommendation_generation')
            
            # Step 5: Enhanced Insight Aggregation and Ranking
            self.workflow_state[workflow_id]['current_step'] = 'insight_aggregation'
            aggregated_insights = self.insight_aggregator.aggregate_insights(
                anomalies=anomalies,
                trends=trends,
                forecasts=forecasts,
                recommendations=recommendations,
                cost_data=cost_data
            )
            
            # Prepare client context for ranking
            client_context = self._prepare_client_context(client_config, budget_info, cost_data)
            
            # Rank insights
            ranked_insights = self.insight_ranker.rank_insights(
                insights=aggregated_insights,
                client_context=client_context
            )
            self.workflow_state[workflow_id]['steps_completed'].append('insight_aggregation')
            
            # Step 6: Generate Executive Summary
            self.workflow_state[workflow_id]['current_step'] = 'narrative_generation'
            executive_summary = self._generate_executive_summary(
                cost_data, anomalies, trends, forecasts, ranked_insights
            )
            self.workflow_state[workflow_id]['steps_completed'].append('narrative_generation')
            
            # Step 7: Risk Assessment
            risk_assessment = self._assess_risks(anomalies, trends, forecasts, ranked_insights)
            
            # Extract key insights from ranked insights
            key_insights = [insight.title for insight in ranked_insights[:5]]
            
            # Calculate overall confidence
            confidence_scores = [insight.confidence_score for insight in ranked_insights]
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
            
            # Compile final insights
            insights = AIInsights(
                executive_summary=executive_summary,
                anomalies=anomalies,
                trends=trends,
                forecasts=forecasts,
                recommendations=recommendations,
                key_insights=key_insights,
                risk_assessment=risk_assessment,
                confidence_score=overall_confidence,
                metadata={
                    'client_id': client_id,
                    'workflow_id': workflow_id,
                    'analysis_timestamp': datetime.utcnow().isoformat(),
                    'orchestration_enabled': True,
                    'aggregated_insights': len(ranked_insights),
                    'workflow_performance': {
                        'steps_completed': len(self.workflow_state[workflow_id]['steps_completed']),
                        'processing_time': (datetime.utcnow() - self.workflow_state[workflow_id]['start_time']).total_seconds()
                    }
                }
            )
            
            # Update workflow state
            self.workflow_state[workflow_id]['status'] = 'completed'
            self.workflow_state[workflow_id]['end_time'] = datetime.utcnow()
            
            logger.info(f"Enhanced insights workflow completed for client {client_id}")
            return insights
            
        except Exception as e:
            logger.error(f"Enhanced insights workflow failed for client {client_id}: {e}")
            self.workflow_state[workflow_id]['status'] = 'failed'
            self.workflow_state[workflow_id]['error'] = str(e)
            return self._get_minimal_insights(client_id, cost_data)
    
    def _execute_anomaly_detection(
        self, 
        cost_data: List[UnifiedCostRecord], 
        budget_info: Optional[Dict[str, float]]
    ) -> List[Anomaly]:
        """Execute anomaly detection step"""
        if len(cost_data) < 7:
            return []
        
        historical_data = cost_data[:-7] if len(cost_data) > 14 else cost_data[:-1]
        current_data = cost_data[-7:] if len(cost_data) > 14 else cost_data[-1:]
        
        return self.anomaly_detector.detect_anomalies(current_data, historical_data, budget_info)
    
    def _execute_trend_analysis(self, cost_data: List[UnifiedCostRecord]) -> TrendAnalysis:
        """Execute trend analysis step"""
        return self.trend_analyzer.analyze_trends(cost_data)
    
    def _execute_forecasting(self, cost_data: List[UnifiedCostRecord]) -> ForecastResult:
        """Execute forecasting step"""
        return self.forecasting_engine.generate_forecast(cost_data, forecast_horizon=30)
    
    def _generate_basic_recommendations(
        self, 
        anomalies: List[Anomaly], 
        trends: TrendAnalysis, 
        forecasts: ForecastResult
    ) -> List[Recommendation]:
        """Generate basic recommendations (simplified for this implementation)"""
        recommendations = []
        
        # Generate recommendations based on anomalies
        for anomaly in anomalies[:3]:  # Top 3 anomalies
            if anomaly.severity.value in ['critical', 'high']:
                recommendations.append(Recommendation(
                    title=f"Address {anomaly.type.value.replace('_', ' ').title()}",
                    description=f"Investigate and resolve {anomaly.description}",
                    estimated_savings=abs(anomaly.cost_impact) * 0.7,
                    implementation_effort="medium",
                    priority="high",
                    category="anomaly_resolution",
                    affected_services=anomaly.affected_services,
                    confidence_score=anomaly.confidence_score,
                    implementation_steps=anomaly.recommended_actions
                ))
        
        # Generate recommendations based on trends
        if trends.overall_trend.growth_rate > 20:
            recommendations.append(Recommendation(
                title="Control Cost Growth",
                description=f"Costs are growing at {trends.overall_trend.growth_rate:.1f}% rate",
                estimated_savings=1000.0,  # Simplified calculation
                implementation_effort="medium",
                priority="high",
                category="cost_optimization",
                affected_services=["all"],
                confidence_score=trends.trend_confidence,
                implementation_steps=[
                    "Analyze cost growth drivers",
                    "Implement cost controls",
                    "Monitor growth trends"
                ]
            ))
        
        return recommendations
    
    def _prepare_client_context(
        self, 
        client_config: Optional[ClientConfig], 
        budget_info: Optional[Dict[str, float]], 
        cost_data: List[UnifiedCostRecord]
    ) -> Dict[str, Any]:
        """Prepare client context for insight ranking"""
        context = {}
        
        if client_config:
            context.update({
                'budget_constraints': getattr(client_config, 'budget_constraints', False),
                'growth_stage': getattr(client_config, 'growth_stage', 'stable'),
                'security_focus': getattr(client_config, 'security_focus', False)
            })
        
        if budget_info and cost_data:
            current_cost = sum(record.total_cost for record in cost_data[-30:])
            total_budget = sum(budget_info.values())
            if total_budget > 0:
                context['budget_utilization'] = current_cost / total_budget
                context['budget_constraints'] = current_cost > total_budget * 0.8
        
        return context
    
    def _generate_executive_summary(
        self,
        cost_data: List[UnifiedCostRecord],
        anomalies: List[Anomaly],
        trends: TrendAnalysis,
        forecasts: ForecastResult,
        ranked_insights: List[AggregatedInsight]
    ) -> str:
        """Generate executive summary"""
        if not cost_data:
            return "No cost data available for analysis."
        
        total_cost = sum(record.total_cost for record in cost_data[-30:])
        avg_daily_cost = total_cost / min(30, len(cost_data))
        
        summary_parts = [
            f"Total costs over the last {min(30, len(cost_data))} days: ${total_cost:,.2f}",
            f"Average daily cost: ${avg_daily_cost:,.2f}"
        ]
        
        # Add trend information
        if trends.overall_trend.significance.value != 'none':
            trend_direction = trends.overall_trend.direction.value
            growth_rate = abs(trends.overall_trend.growth_rate)
            summary_parts.append(f"Cost trend is {trend_direction} at {growth_rate:.1f}% rate")
        
        # Add anomaly information
        if anomalies:
            critical_anomalies = len([a for a in anomalies if a.severity.value == 'critical'])
            if critical_anomalies > 0:
                summary_parts.append(f"{critical_anomalies} critical anomalies detected requiring immediate attention")
        
        # Add top insights
        if ranked_insights:
            top_insight = ranked_insights[0]
            summary_parts.append(f"Top priority: {top_insight.title}")
        
        return ". ".join(summary_parts) + "."
    
    def _assess_risks(
        self,
        anomalies: List[Anomaly],
        trends: TrendAnalysis,
        forecasts: ForecastResult,
        ranked_insights: List[AggregatedInsight]
    ) -> Dict[str, Any]:
        """Assess risks based on analysis results"""
        risk_score = 0.0
        risk_factors = []
        
        # Assess anomaly risks
        critical_anomalies = [a for a in anomalies if a.severity.value == 'critical']
        if critical_anomalies:
            risk_score += 0.3
            risk_factors.append(f"{len(critical_anomalies)} critical anomalies")
        
        # Assess trend risks
        if trends.overall_trend.growth_rate > 30:
            risk_score += 0.2
            risk_factors.append(f"High cost growth rate: {trends.overall_trend.growth_rate:.1f}%")
        
        # Assess insight risks
        critical_insights = [i for i in ranked_insights if i.priority == InsightPriority.CRITICAL]
        if critical_insights:
            risk_score += 0.2
            risk_factors.append(f"{len(critical_insights)} critical insights")
        
        # Determine overall risk level
        if risk_score >= 0.6:
            risk_level = 'high'
        elif risk_score >= 0.3:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'overall_risk_level': risk_level,
            'risk_score': min(risk_score, 1.0),
            'risk_factors': risk_factors,
            'mitigation_recommendations': [
                "Implement enhanced cost monitoring",
                "Review and optimize high-cost services",
                "Establish cost control procedures"
            ] if risk_score > 0.3 else []
        }
    
    def _get_minimal_insights(
        self, 
        client_id: str, 
        cost_data: List[UnifiedCostRecord]
    ) -> AIInsights:
        """Generate minimal insights for error cases"""
        if not cost_data:
            total_cost = 0
            summary = "No cost data available for analysis."
        else:
            total_cost = sum(record.total_cost for record in cost_data)
            summary = f"Limited analysis available. Total costs: ${total_cost:,.2f} over {len(cost_data)} days."
        
        return AIInsights(
            executive_summary=summary,
            anomalies=[],
            trends=self.trend_analyzer.analyze_trends([]),
            forecasts=self.forecasting_engine.generate_forecast([], 30),
            recommendations=[],
            key_insights=["Insufficient data for comprehensive analysis"],
            risk_assessment={
                'overall_risk_level': 'unknown',
                'risk_score': 0.0,
                'risk_factors': ['Insufficient data'],
                'mitigation_recommendations': ['Collect more historical data']
            },
            confidence_score=0.1,
            metadata={
                'client_id': client_id,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'data_points_analyzed': len(cost_data),
                'insufficient_data': True
            }
        )
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow"""
        return self.workflow_state.get(workflow_id)
    
    def get_orchestration_metrics(self) -> Dict[str, Any]:
        """Get orchestration performance metrics"""
        total_workflows = len(self.workflow_state)
        completed_workflows = len([w for w in self.workflow_state.values() if w.get('status') == 'completed'])
        failed_workflows = len([w for w in self.workflow_state.values() if w.get('status') == 'failed'])
        
        return {
            'total_workflows': total_workflows,
            'completed_workflows': completed_workflows,
            'failed_workflows': failed_workflows,
            'success_rate': completed_workflows / total_workflows if total_workflows > 0 else 0,
            'workflow_config': self.workflow_config,
            'enhanced_features': {
                'insight_aggregation': True,
                'insight_ranking': True,
                'workflow_orchestration': True,
                'client_context_aware': True
            }
        }


# Alias for backward compatibility
AIInsightsService = EnhancedAIInsightsService