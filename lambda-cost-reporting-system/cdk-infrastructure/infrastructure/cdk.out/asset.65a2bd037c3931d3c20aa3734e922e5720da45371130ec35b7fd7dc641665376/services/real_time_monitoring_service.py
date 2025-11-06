"""
Real-Time Cost Monitoring Service

Provides real-time cost monitoring capabilities with EventBridge integration,
immediate anomaly alerting, and threshold-based monitoring with AI context.
"""

import boto3
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from collections import defaultdict, deque
import statistics

try:
    from ..models.multi_cloud_models import UnifiedCostRecord, CloudProvider
    from ..utils.logging import create_logger as get_logger
    from .ai_insights_service import AIInsightsService, Anomaly, AnomalyType, Severity
    from .anomaly_detection_engine import AnomalyDetectionEngine
    from .threshold_evaluator import ThresholdEvaluator
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.multi_cloud_models import UnifiedCostRecord, CloudProvider
    from utils.logging import create_logger
    from ai_insights_service import AIInsightsService, Anomaly, AnomalyType, Severity
    from anomaly_detection_engine import AnomalyDetectionEngine
    from threshold_evaluator import ThresholdEvaluator
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(Enum):
    """Types of real-time alerts"""
    COST_THRESHOLD = "cost_threshold"
    ANOMALY_DETECTED = "anomaly_detected"
    BUDGET_EXCEEDED = "budget_exceeded"
    SPIKE_DETECTED = "spike_detected"
    SERVICE_ALERT = "service_alert"
    TREND_ALERT = "trend_alert"
    AI_INSIGHT = "ai_insight"


@dataclass
class MonitoringThreshold:
    """Cost monitoring threshold configuration"""
    threshold_id: str
    client_id: str
    threshold_type: str  # absolute, percentage, rate
    threshold_value: float
    comparison_operator: str  # gt, lt, gte, lte
    time_window_minutes: int
    evaluation_periods: int
    alert_severity: AlertSeverity
    enabled: bool
    metadata: Dict[str, Any]


@dataclass
class RealTimeAlert:
    """Real-time cost alert"""
    alert_id: str
    client_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    current_value: float
    threshold_value: Optional[float]
    affected_services: List[str]
    timestamp: datetime
    ai_context: Optional[Dict[str, Any]]
    recommended_actions: List[str]
    metadata: Dict[str, Any]


@dataclass
class MonitoringMetrics:
    """Real-time monitoring metrics"""
    client_id: str
    timestamp: datetime
    total_cost: float
    service_costs: Dict[str, float]
    cost_rate_per_hour: float
    anomaly_score: float
    trend_indicator: str
    active_alerts: int
    metadata: Dict[str, Any]


class EventBridgeIntegration:
    """EventBridge integration for real-time events"""
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize EventBridge integration
        
        Args:
            region: AWS region for EventBridge
        """
        self.region = region
        self.eventbridge_client = boto3.client('events', region_name=region)
        self.event_bus_name = "cost-analytics-events"
        self.event_source = "cost-analytics.monitoring"
    
    async def publish_alert(self, alert: RealTimeAlert) -> bool:
        """
        Publish alert to EventBridge
        
        Args:
            alert: Real-time alert to publish
            
        Returns:
            Success status
        """
        try:
            event_detail = {
                'alert_id': alert.alert_id,
                'client_id': alert.client_id,
                'alert_type': alert.alert_type.value,
                'severity': alert.severity.value,
                'title': alert.title,
                'description': alert.description,
                'current_value': alert.current_value,
                'threshold_value': alert.threshold_value,
                'affected_services': alert.affected_services,
                'timestamp': alert.timestamp.isoformat(),
                'ai_context': alert.ai_context,
                'recommended_actions': alert.recommended_actions,
                'metadata': alert.metadata
            }
            
            response = self.eventbridge_client.put_events(
                Entries=[
                    {
                        'Source': self.event_source,
                        'DetailType': f'Cost Alert - {alert.alert_type.value}',
                        'Detail': json.dumps(event_detail),
                        'EventBusName': self.event_bus_name,
                        'Resources': [f"client:{alert.client_id}"]
                    }
                ]
            )
            
            if response['FailedEntryCount'] == 0:
                logger.info(f"Successfully published alert {alert.alert_id} to EventBridge")
                return True
            else:
                logger.error(f"Failed to publish alert {alert.alert_id}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"EventBridge publish failed for alert {alert.alert_id}: {e}")
            return False
    
    async def publish_metrics(self, metrics: MonitoringMetrics) -> bool:
        """
        Publish monitoring metrics to EventBridge
        
        Args:
            metrics: Monitoring metrics to publish
            
        Returns:
            Success status
        """
        try:
            event_detail = asdict(metrics)
            event_detail['timestamp'] = metrics.timestamp.isoformat()
            
            response = self.eventbridge_client.put_events(
                Entries=[
                    {
                        'Source': self.event_source,
                        'DetailType': 'Cost Monitoring Metrics',
                        'Detail': json.dumps(event_detail),
                        'EventBusName': self.event_bus_name,
                        'Resources': [f"client:{metrics.client_id}"]
                    }
                ]
            )
            
            return response['FailedEntryCount'] == 0
            
        except Exception as e:
            logger.error(f"EventBridge metrics publish failed: {e}")
            return False


class ThresholdMonitor:
    """Threshold-based monitoring with AI context"""
    
    def __init__(self, ai_insights_service: AIInsightsService):
        """
        Initialize threshold monitor
        
        Args:
            ai_insights_service: AI insights service for context
        """
        self.ai_insights_service = ai_insights_service
        self.active_thresholds: Dict[str, List[MonitoringThreshold]] = defaultdict(list)
        self.threshold_states: Dict[str, Dict[str, Any]] = defaultdict(dict)
    
    def add_threshold(self, threshold: MonitoringThreshold):
        """Add monitoring threshold for a client"""
        self.active_thresholds[threshold.client_id].append(threshold)
        logger.info(f"Added threshold {threshold.threshold_id} for client {threshold.client_id}")
    
    def remove_threshold(self, client_id: str, threshold_id: str):
        """Remove monitoring threshold"""
        self.active_thresholds[client_id] = [
            t for t in self.active_thresholds[client_id] 
            if t.threshold_id != threshold_id
        ]
        if threshold_id in self.threshold_states[client_id]:
            del self.threshold_states[client_id][threshold_id]
        logger.info(f"Removed threshold {threshold_id} for client {client_id}")
    
    async def evaluate_thresholds(
        self, 
        client_id: str, 
        current_metrics: MonitoringMetrics,
        historical_data: List[UnifiedCostRecord]
    ) -> List[RealTimeAlert]:
        """
        Evaluate all thresholds for a client
        
        Args:
            client_id: Client identifier
            current_metrics: Current monitoring metrics
            historical_data: Historical cost data for context
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        client_thresholds = self.active_thresholds.get(client_id, [])
        
        for threshold in client_thresholds:
            if not threshold.enabled:
                continue
            
            try:
                alert = await self._evaluate_single_threshold(
                    threshold, current_metrics, historical_data
                )
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"Threshold evaluation failed for {threshold.threshold_id}: {e}")
        
        return alerts
    
    async def _evaluate_single_threshold(
        self,
        threshold: MonitoringThreshold,
        current_metrics: MonitoringMetrics,
        historical_data: List[UnifiedCostRecord]
    ) -> Optional[RealTimeAlert]:
        """Evaluate a single threshold"""
        
        # Get current value based on threshold type
        current_value = self._get_threshold_value(threshold, current_metrics)
        
        # Check if threshold is breached
        is_breached = self._check_threshold_breach(
            current_value, threshold.threshold_value, threshold.comparison_operator
        )
        
        if not is_breached:
            # Reset threshold state if not breached
            if threshold.threshold_id in self.threshold_states[threshold.client_id]:
                self.threshold_states[threshold.client_id][threshold.threshold_id] = {
                    'breach_count': 0,
                    'first_breach': None
                }
            return None
        
        # Update threshold state
        state = self.threshold_states[threshold.client_id].get(threshold.threshold_id, {
            'breach_count': 0,
            'first_breach': None
        })
        
        state['breach_count'] += 1
        if state['first_breach'] is None:
            state['first_breach'] = datetime.utcnow()
        
        self.threshold_states[threshold.client_id][threshold.threshold_id] = state
        
        # Check if we've reached the required evaluation periods
        if state['breach_count'] < threshold.evaluation_periods:
            return None
        
        # Generate alert with AI context
        ai_context = await self._generate_ai_context(
            threshold, current_metrics, historical_data
        )
        
        alert = RealTimeAlert(
            alert_id=f"{threshold.threshold_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            client_id=threshold.client_id,
            alert_type=AlertType.COST_THRESHOLD,
            severity=threshold.alert_severity,
            title=f"Cost Threshold Exceeded: {threshold.threshold_type}",
            description=self._generate_threshold_description(threshold, current_value),
            current_value=current_value,
            threshold_value=threshold.threshold_value,
            affected_services=self._identify_affected_services(threshold, current_metrics),
            timestamp=datetime.utcnow(),
            ai_context=ai_context,
            recommended_actions=self._generate_threshold_actions(threshold, ai_context),
            metadata={
                'threshold_id': threshold.threshold_id,
                'breach_count': state['breach_count'],
                'first_breach': state['first_breach'].isoformat() if state['first_breach'] else None,
                'evaluation_periods': threshold.evaluation_periods
            }
        )
        
        # Reset breach count after alert
        state['breach_count'] = 0
        
        return alert
    
    def _get_threshold_value(self, threshold: MonitoringThreshold, metrics: MonitoringMetrics) -> float:
        """Get current value for threshold evaluation"""
        if threshold.threshold_type == 'absolute':
            return metrics.total_cost
        elif threshold.threshold_type == 'rate':
            return metrics.cost_rate_per_hour
        elif threshold.threshold_type == 'percentage':
            # Percentage change from baseline (would need historical baseline)
            return 0.0  # Simplified for now
        else:
            return metrics.total_cost
    
    def _check_threshold_breach(self, current_value: float, threshold_value: float, operator: str) -> bool:
        """Check if threshold is breached"""
        if operator == 'gt':
            return current_value > threshold_value
        elif operator == 'gte':
            return current_value >= threshold_value
        elif operator == 'lt':
            return current_value < threshold_value
        elif operator == 'lte':
            return current_value <= threshold_value
        else:
            return False
    
    async def _generate_ai_context(
        self,
        threshold: MonitoringThreshold,
        current_metrics: MonitoringMetrics,
        historical_data: List[UnifiedCostRecord]
    ) -> Dict[str, Any]:
        """Generate AI context for threshold alert"""
        try:
            # Get recent insights for context
            if len(historical_data) >= 7:
                insights = self.ai_insights_service.generate_insights(
                    threshold.client_id, historical_data[-30:]  # Last 30 days
                )
                
                return {
                    'anomaly_score': current_metrics.anomaly_score,
                    'trend_indicator': current_metrics.trend_indicator,
                    'recent_anomalies': len(insights.anomalies),
                    'confidence_score': insights.confidence_score,
                    'key_insights': insights.key_insights[:3],
                    'risk_level': insights.risk_assessment.get('overall_risk_level', 'unknown')
                }
        except Exception as e:
            logger.error(f"AI context generation failed: {e}")
        
        return {
            'anomaly_score': current_metrics.anomaly_score,
            'trend_indicator': current_metrics.trend_indicator,
            'ai_available': False
        }
    
    def _generate_threshold_description(self, threshold: MonitoringThreshold, current_value: float) -> str:
        """Generate threshold alert description"""
        return (f"{threshold.threshold_type.title()} threshold exceeded: "
                f"current value {current_value:.2f} {threshold.comparison_operator} "
                f"threshold {threshold.threshold_value:.2f}")
    
    def _identify_affected_services(self, threshold: MonitoringThreshold, metrics: MonitoringMetrics) -> List[str]:
        """Identify services affected by threshold breach"""
        if threshold.threshold_type == 'absolute':
            # Return top cost services
            sorted_services = sorted(
                metrics.service_costs.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            return [service for service, _ in sorted_services[:5]]
        else:
            return list(metrics.service_costs.keys())
    
    def _generate_threshold_actions(
        self, 
        threshold: MonitoringThreshold, 
        ai_context: Dict[str, Any]
    ) -> List[str]:
        """Generate recommended actions for threshold alert"""
        actions = [
            "Investigate immediate cost drivers",
            "Review recent resource changes and deployments"
        ]
        
        if ai_context.get('risk_level') in ['high', 'critical']:
            actions.insert(0, "Immediate cost review and potential resource freeze")
        
        if ai_context.get('recent_anomalies', 0) > 0:
            actions.append("Review detected anomalies for root cause")
        
        if threshold.threshold_type == 'rate':
            actions.append("Check for runaway processes or scaling events")
        
        actions.extend([
            "Implement immediate cost controls if necessary",
            "Update monitoring thresholds based on findings"
        ])
        
        return actions


class RealTimeMonitoringService:
    """Main real-time cost monitoring service"""
    
    def __init__(self, use_ai: bool = True, region: str = "us-east-1"):
        """
        Initialize real-time monitoring service
        
        Args:
            use_ai: Whether to use AI-powered insights
            region: AWS region for services
        """
        self.use_ai = use_ai
        self.region = region
        
        # Initialize components
        self.ai_insights_service = AIInsightsService(use_ai=use_ai)
        self.anomaly_detector = AnomalyDetectionEngine(use_ai=use_ai)
        self.threshold_monitor = ThresholdMonitor(self.ai_insights_service)
        self.eventbridge = EventBridgeIntegration(region=region)
        
        # Monitoring state
        self.client_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.active_alerts: Dict[str, List[RealTimeAlert]] = defaultdict(list)
        self.monitoring_enabled: Dict[str, bool] = defaultdict(lambda: True)
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[RealTimeAlert], None]] = []
    
    def add_alert_callback(self, callback: Callable[[RealTimeAlert], None]):
        """Add callback function for alert notifications"""
        self.alert_callbacks.append(callback)
    
    def enable_monitoring(self, client_id: str):
        """Enable monitoring for a client"""
        self.monitoring_enabled[client_id] = True
        logger.info(f"Enabled monitoring for client {client_id}")
    
    def disable_monitoring(self, client_id: str):
        """Disable monitoring for a client"""
        self.monitoring_enabled[client_id] = False
        logger.info(f"Disabled monitoring for client {client_id}")
    
    async def process_cost_update(
        self,
        client_id: str,
        cost_record: UnifiedCostRecord,
        historical_data: Optional[List[UnifiedCostRecord]] = None
    ) -> List[RealTimeAlert]:
        """
        Process real-time cost update and generate alerts
        
        Args:
            client_id: Client identifier
            cost_record: New cost record
            historical_data: Historical cost data for context
            
        Returns:
            List of generated alerts
        """
        if not self.monitoring_enabled[client_id]:
            return []
        
        try:
            # Calculate current metrics
            current_metrics = self._calculate_current_metrics(client_id, cost_record)
            
            # Store metrics
            self.client_metrics[client_id].append(current_metrics)
            
            # Publish metrics to EventBridge
            await self.eventbridge.publish_metrics(current_metrics)
            
            # Generate alerts
            alerts = []
            
            # 1. Threshold-based alerts
            if historical_data:
                threshold_alerts = await self.threshold_monitor.evaluate_thresholds(
                    client_id, current_metrics, historical_data
                )
                alerts.extend(threshold_alerts)
            
            # 2. Anomaly-based alerts
            anomaly_alerts = await self._detect_real_time_anomalies(
                client_id, cost_record, historical_data or []
            )
            alerts.extend(anomaly_alerts)
            
            # 3. Spike detection alerts
            spike_alerts = self._detect_cost_spikes(client_id, current_metrics)
            alerts.extend(spike_alerts)
            
            # 4. AI-powered alerts (if enabled)
            if self.use_ai and historical_data and len(historical_data) >= 7:
                ai_alerts = await self._generate_ai_alerts(
                    client_id, cost_record, historical_data, current_metrics
                )
                alerts.extend(ai_alerts)
            
            # Process and publish alerts
            for alert in alerts:
                await self._process_alert(alert)
            
            # Update active alerts
            self.active_alerts[client_id] = [
                alert for alert in self.active_alerts[client_id]
                if (datetime.utcnow() - alert.timestamp).total_seconds() < 3600  # Keep for 1 hour
            ]
            self.active_alerts[client_id].extend(alerts)
            
            logger.info(f"Processed cost update for client {client_id}, generated {len(alerts)} alerts")
            return alerts
            
        except Exception as e:
            logger.error(f"Real-time monitoring failed for client {client_id}: {e}")
            return []
    
    def _calculate_current_metrics(self, client_id: str, cost_record: UnifiedCostRecord) -> MonitoringMetrics:
        """Calculate current monitoring metrics"""
        
        # Get service costs
        service_costs = {service: cost_info.cost for service, cost_info in cost_record.services.items()}
        
        # Calculate cost rate (simplified - would need time-based calculation)
        cost_rate_per_hour = cost_record.total_cost / 24  # Assume daily cost spread over 24 hours
        
        # Calculate anomaly score (simplified)
        recent_metrics = list(self.client_metrics[client_id])
        if len(recent_metrics) > 1:
            recent_costs = [m.total_cost for m in recent_metrics[-10:]]
            mean_cost = statistics.mean(recent_costs)
            std_cost = statistics.stdev(recent_costs) if len(recent_costs) > 1 else 0
            anomaly_score = abs(cost_record.total_cost - mean_cost) / (std_cost + 1e-6)
        else:
            anomaly_score = 0.0
        
        # Determine trend indicator
        if len(recent_metrics) >= 3:
            recent_trend = [m.total_cost for m in recent_metrics[-3:]]
            if recent_trend[-1] > recent_trend[0] * 1.1:
                trend_indicator = "increasing"
            elif recent_trend[-1] < recent_trend[0] * 0.9:
                trend_indicator = "decreasing"
            else:
                trend_indicator = "stable"
        else:
            trend_indicator = "unknown"
        
        return MonitoringMetrics(
            client_id=client_id,
            timestamp=datetime.utcnow(),
            total_cost=cost_record.total_cost,
            service_costs=service_costs,
            cost_rate_per_hour=cost_rate_per_hour,
            anomaly_score=anomaly_score,
            trend_indicator=trend_indicator,
            active_alerts=len(self.active_alerts[client_id]),
            metadata={
                'provider': cost_record.provider.value,
                'date': cost_record.date,
                'data_quality': cost_record.data_quality.__dict__ if cost_record.data_quality else {}
            }
        )
    
    async def _detect_real_time_anomalies(
        self,
        client_id: str,
        cost_record: UnifiedCostRecord,
        historical_data: List[UnifiedCostRecord]
    ) -> List[RealTimeAlert]:
        """Detect real-time anomalies"""
        alerts = []
        
        if len(historical_data) < 7:
            return alerts
        
        try:
            # Use anomaly detector
            anomalies = self.anomaly_detector.detect_anomalies(
                [cost_record], historical_data[-30:]  # Last 30 days as baseline
            )
            
            # Convert anomalies to real-time alerts
            for anomaly in anomalies:
                if anomaly.severity.value in ['critical', 'high']:
                    alert = RealTimeAlert(
                        alert_id=f"anomaly_{client_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                        client_id=client_id,
                        alert_type=AlertType.ANOMALY_DETECTED,
                        severity=AlertSeverity(anomaly.severity.value),
                        title=f"Real-time Anomaly: {anomaly.type.value.replace('_', ' ').title()}",
                        description=anomaly.description,
                        current_value=abs(anomaly.cost_impact),
                        threshold_value=None,
                        affected_services=anomaly.affected_services,
                        timestamp=datetime.utcnow(),
                        ai_context={
                            'detection_method': anomaly.detection_method,
                            'confidence_score': anomaly.confidence_score,
                            'anomaly_type': anomaly.type.value
                        },
                        recommended_actions=anomaly.recommended_actions,
                        metadata={
                            'anomaly_id': f"{anomaly.type.value}_{anomaly.timestamp.strftime('%Y%m%d_%H%M%S')}",
                            'detection_timestamp': anomaly.timestamp.isoformat()
                        }
                    )
                    alerts.append(alert)
        
        except Exception as e:
            logger.error(f"Real-time anomaly detection failed: {e}")
        
        return alerts
    
    def _detect_cost_spikes(self, client_id: str, current_metrics: MonitoringMetrics) -> List[RealTimeAlert]:
        """Detect immediate cost spikes"""
        alerts = []
        
        recent_metrics = list(self.client_metrics[client_id])
        if len(recent_metrics) < 3:
            return alerts
        
        # Check for significant cost increase
        recent_costs = [m.total_cost for m in recent_metrics[-3:]]
        current_cost = current_metrics.total_cost
        baseline_cost = statistics.mean(recent_costs)
        
        if current_cost > baseline_cost * 1.5:  # 50% spike
            spike_percentage = ((current_cost - baseline_cost) / baseline_cost) * 100
            
            alert = RealTimeAlert(
                alert_id=f"spike_{client_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                client_id=client_id,
                alert_type=AlertType.SPIKE_DETECTED,
                severity=AlertSeverity.HIGH if spike_percentage > 100 else AlertSeverity.MEDIUM,
                title=f"Cost Spike Detected ({spike_percentage:.1f}% increase)",
                description=f"Immediate cost spike detected: ${current_cost:.2f} vs baseline ${baseline_cost:.2f}",
                current_value=current_cost,
                threshold_value=baseline_cost * 1.5,
                affected_services=list(current_metrics.service_costs.keys()),
                timestamp=datetime.utcnow(),
                ai_context={
                    'spike_percentage': spike_percentage,
                    'baseline_cost': baseline_cost,
                    'detection_method': 'real_time_spike'
                },
                recommended_actions=[
                    "Immediately investigate cost spike cause",
                    "Check for scaling events or configuration changes",
                    "Review recent deployments and resource changes",
                    "Consider implementing emergency cost controls"
                ],
                metadata={
                    'spike_percentage': spike_percentage,
                    'baseline_period': '3_recent_periods'
                }
            )
            alerts.append(alert)
        
        return alerts
    
    async def _generate_ai_alerts(
        self,
        client_id: str,
        cost_record: UnifiedCostRecord,
        historical_data: List[UnifiedCostRecord],
        current_metrics: MonitoringMetrics
    ) -> List[RealTimeAlert]:
        """Generate AI-powered alerts"""
        alerts = []
        
        if not self.use_ai:
            return alerts
        
        try:
            # Get AI insights for current data
            insights = self.ai_insights_service.generate_insights(
                client_id, historical_data + [cost_record]
            )
            
            # Generate alerts based on AI insights
            if insights.confidence_score > 0.7:
                # High-confidence insights warrant alerts
                for insight in insights.key_insights[:2]:  # Top 2 insights
                    if any(keyword in insight.lower() for keyword in ['critical', 'urgent', 'immediate']):
                        alert = RealTimeAlert(
                            alert_id=f"ai_{client_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                            client_id=client_id,
                            alert_type=AlertType.AI_INSIGHT,
                            severity=AlertSeverity.MEDIUM,
                            title="AI-Powered Cost Insight",
                            description=insight,
                            current_value=current_metrics.total_cost,
                            threshold_value=None,
                            affected_services=list(current_metrics.service_costs.keys()),
                            timestamp=datetime.utcnow(),
                            ai_context={
                                'confidence_score': insights.confidence_score,
                                'risk_level': insights.risk_assessment.get('overall_risk_level', 'unknown'),
                                'insight_type': 'ai_generated'
                            },
                            recommended_actions=insights.recommendations[:3] if insights.recommendations else [],
                            metadata={
                                'ai_analysis_timestamp': insights.metadata.get('analysis_timestamp'),
                                'insight_category': 'ai_insight'
                            }
                        )
                        alerts.append(alert)
        
        except Exception as e:
            logger.error(f"AI alert generation failed: {e}")
        
        return alerts
    
    async def _process_alert(self, alert: RealTimeAlert):
        """Process and publish alert"""
        try:
            # Publish to EventBridge
            await self.eventbridge.publish_alert(alert)
            
            # Call registered callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
            
            logger.info(f"Processed alert {alert.alert_id} for client {alert.client_id}")
            
        except Exception as e:
            logger.error(f"Alert processing failed for {alert.alert_id}: {e}")
    
    def get_active_alerts(self, client_id: str) -> List[RealTimeAlert]:
        """Get active alerts for a client"""
        return self.active_alerts.get(client_id, [])
    
    def get_monitoring_status(self, client_id: str) -> Dict[str, Any]:
        """Get monitoring status for a client"""
        recent_metrics = list(self.client_metrics[client_id])
        
        return {
            'monitoring_enabled': self.monitoring_enabled[client_id],
            'active_alerts': len(self.active_alerts[client_id]),
            'recent_metrics_count': len(recent_metrics),
            'last_update': recent_metrics[-1].timestamp.isoformat() if recent_metrics else None,
            'thresholds_configured': len(self.threshold_monitor.active_thresholds[client_id]),
            'current_anomaly_score': recent_metrics[-1].anomaly_score if recent_metrics else 0.0,
            'trend_indicator': recent_metrics[-1].trend_indicator if recent_metrics else 'unknown'
        }
    
    def add_threshold(self, threshold: MonitoringThreshold):
        """Add monitoring threshold"""
        self.threshold_monitor.add_threshold(threshold)
    
    def remove_threshold(self, client_id: str, threshold_id: str):
        """Remove monitoring threshold"""
        self.threshold_monitor.remove_threshold(client_id, threshold_id)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get monitoring service performance metrics"""
        total_clients = len(self.monitoring_enabled)
        active_clients = sum(1 for enabled in self.monitoring_enabled.values() if enabled)
        total_alerts = sum(len(alerts) for alerts in self.active_alerts.values())
        total_thresholds = sum(
            len(thresholds) for thresholds in self.threshold_monitor.active_thresholds.values()
        )
        
        return {
            'total_clients': total_clients,
            'active_clients': active_clients,
            'total_active_alerts': total_alerts,
            'total_thresholds': total_thresholds,
            'ai_enabled': self.use_ai,
            'eventbridge_region': self.region,
            'monitoring_uptime': '100%'  # Simplified
        }