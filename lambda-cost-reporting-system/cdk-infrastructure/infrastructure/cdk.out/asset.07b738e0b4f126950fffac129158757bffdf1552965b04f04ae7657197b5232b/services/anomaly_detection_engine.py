"""
Anomaly Detection Engine for Cost Analytics

Provides comprehensive anomaly detection using statistical methods,
machine learning approaches, and rule-based detection for cost data.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics
from collections import defaultdict

try:
    from ..models.multi_cloud_models import UnifiedCostRecord
    from ..utils.logging import create_logger as get_logger
    from .bedrock_service import BedrockService
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.multi_cloud_models import UnifiedCostRecord
    from utils.logging import create_logger
    from bedrock_service import BedrockService
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class AnomalyType(Enum):
    """Types of cost anomalies"""
    COST_SPIKE = "cost_spike"
    COST_DROP = "cost_drop"
    NEW_SERVICE = "new_service"
    SERVICE_DISAPPEARANCE = "service_disappearance"
    UNUSUAL_PATTERN = "unusual_pattern"
    BUDGET_DEVIATION = "budget_deviation"
    SEASONAL_ANOMALY = "seasonal_anomaly"
    USAGE_ANOMALY = "usage_anomaly"


class Severity(Enum):
    """Anomaly severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Anomaly:
    """Anomaly detection result"""
    type: AnomalyType
    severity: Severity
    description: str
    affected_services: List[str]
    cost_impact: float
    detection_method: str
    confidence_score: float
    recommended_actions: List[str]
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class StatisticalMetrics:
    """Statistical metrics for anomaly detection"""
    mean: float
    std_deviation: float
    median: float
    q1: float
    q3: float
    iqr: float
    coefficient_variation: float
    z_score_threshold: float = 2.0
    iqr_multiplier: float = 1.5


class StatisticalAnomalyDetector:
    """Statistical anomaly detection methods"""
    
    def __init__(self, z_score_threshold: float = 2.0, iqr_multiplier: float = 1.5):
        """
        Initialize statistical detector
        
        Args:
            z_score_threshold: Z-score threshold for anomaly detection
            iqr_multiplier: IQR multiplier for outlier detection
        """
        self.z_score_threshold = z_score_threshold
        self.iqr_multiplier = iqr_multiplier
    
    def detect_z_score_anomalies(
        self, 
        current_costs: List[float], 
        historical_costs: List[float]
    ) -> List[Tuple[int, float, str]]:
        """
        Detect anomalies using Z-score method
        
        Args:
            current_costs: Current period costs
            historical_costs: Historical costs for baseline
            
        Returns:
            List of (index, z_score, description) tuples
        """
        if len(historical_costs) < 3:
            return []
        
        mean_cost = statistics.mean(historical_costs)
        std_cost = statistics.stdev(historical_costs)
        
        if std_cost == 0:
            return []
        
        anomalies = []
        for i, cost in enumerate(current_costs):
            z_score = abs((cost - mean_cost) / std_cost)
            if z_score > self.z_score_threshold:
                direction = "spike" if cost > mean_cost else "drop"
                description = f"Cost {direction}: {z_score:.2f} standard deviations from mean"
                anomalies.append((i, z_score, description))
        
        return anomalies
    
    def detect_iqr_anomalies(
        self, 
        current_costs: List[float], 
        historical_costs: List[float]
    ) -> List[Tuple[int, float, str]]:
        """
        Detect anomalies using Interquartile Range (IQR) method
        
        Args:
            current_costs: Current period costs
            historical_costs: Historical costs for baseline
            
        Returns:
            List of (index, outlier_score, description) tuples
        """
        if len(historical_costs) < 4:
            return []
        
        q1 = np.percentile(historical_costs, 25)
        q3 = np.percentile(historical_costs, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - (self.iqr_multiplier * iqr)
        upper_bound = q3 + (self.iqr_multiplier * iqr)
        
        anomalies = []
        for i, cost in enumerate(current_costs):
            if cost < lower_bound or cost > upper_bound:
                outlier_score = max(
                    abs(cost - lower_bound) / iqr if cost < lower_bound else 0,
                    abs(cost - upper_bound) / iqr if cost > upper_bound else 0
                )
                direction = "above" if cost > upper_bound else "below"
                description = f"Cost outlier: {direction} IQR bounds by {outlier_score:.2f}x"
                anomalies.append((i, outlier_score, description))
        
        return anomalies
    
    def calculate_metrics(self, historical_costs: List[float]) -> StatisticalMetrics:
        """Calculate statistical metrics for the dataset"""
        if not historical_costs:
            return StatisticalMetrics(0, 0, 0, 0, 0, 0, 0)
        
        mean_val = statistics.mean(historical_costs)
        std_val = statistics.stdev(historical_costs) if len(historical_costs) > 1 else 0
        median_val = statistics.median(historical_costs)
        q1 = np.percentile(historical_costs, 25)
        q3 = np.percentile(historical_costs, 75)
        iqr = q3 - q1
        cv = std_val / mean_val if mean_val != 0 else 0
        
        return StatisticalMetrics(
            mean=mean_val,
            std_deviation=std_val,
            median=median_val,
            q1=q1,
            q3=q3,
            iqr=iqr,
            coefficient_variation=cv,
            z_score_threshold=self.z_score_threshold,
            iqr_multiplier=self.iqr_multiplier
        )


class RuleBasedDetector:
    """Rule-based anomaly detection for business logic"""
    
    def __init__(self):
        """Initialize rule-based detector"""
        self.rules = {
            'cost_spike_percentage': 50.0,  # 50% increase
            'cost_drop_percentage': 30.0,   # 30% decrease
            'new_service_threshold': 100.0,  # $100 minimum for new service alert
            'service_disappearance_days': 3,  # Service missing for 3 days
            'budget_deviation_threshold': 20.0,  # 20% over budget
        }
    
    def detect_cost_spikes(
        self, 
        current_data: Dict[str, float], 
        baseline_data: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Detect significant cost spikes"""
        anomalies = []
        
        for service, current_cost in current_data.items():
            baseline_cost = baseline_data.get(service, 0)
            
            if baseline_cost > 0:
                percentage_change = ((current_cost - baseline_cost) / baseline_cost) * 100
                
                if percentage_change > self.rules['cost_spike_percentage']:
                    anomalies.append({
                        'service': service,
                        'type': 'cost_spike',
                        'current_cost': current_cost,
                        'baseline_cost': baseline_cost,
                        'percentage_change': percentage_change,
                        'severity': self._calculate_spike_severity(percentage_change),
                        'description': f"{service} cost increased by {percentage_change:.1f}%"
                    })
        
        return anomalies
    
    def detect_new_services(
        self, 
        current_data: Dict[str, float], 
        historical_services: set
    ) -> List[Dict[str, Any]]:
        """Detect new services with significant costs"""
        anomalies = []
        
        for service, cost in current_data.items():
            if service not in historical_services and cost > self.rules['new_service_threshold']:
                anomalies.append({
                    'service': service,
                    'type': 'new_service',
                    'cost': cost,
                    'severity': self._calculate_new_service_severity(cost),
                    'description': f"New service {service} with ${cost:.2f} cost"
                })
        
        return anomalies
    
    def detect_service_disappearance(
        self, 
        current_services: set, 
        historical_services: set,
        historical_costs: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Detect services that have disappeared"""
        anomalies = []
        
        disappeared_services = historical_services - current_services
        
        for service in disappeared_services:
            historical_cost = historical_costs.get(service, 0)
            if historical_cost > self.rules['new_service_threshold']:
                anomalies.append({
                    'service': service,
                    'type': 'service_disappearance',
                    'historical_cost': historical_cost,
                    'severity': self._calculate_disappearance_severity(historical_cost),
                    'description': f"Service {service} disappeared (was ${historical_cost:.2f})"
                })
        
        return anomalies
    
    def detect_budget_deviations(
        self, 
        current_total: float, 
        budget_amount: float
    ) -> List[Dict[str, Any]]:
        """Detect budget deviations"""
        if budget_amount <= 0:
            return []
        
        deviation_percentage = ((current_total - budget_amount) / budget_amount) * 100
        
        if abs(deviation_percentage) > self.rules['budget_deviation_threshold']:
            return [{
                'type': 'budget_deviation',
                'current_total': current_total,
                'budget_amount': budget_amount,
                'deviation_percentage': deviation_percentage,
                'severity': self._calculate_budget_severity(abs(deviation_percentage)),
                'description': f"Budget deviation: {deviation_percentage:+.1f}% from target"
            }]
        
        return []
    
    def _calculate_spike_severity(self, percentage_change: float) -> str:
        """Calculate severity for cost spikes"""
        if percentage_change > 200:
            return Severity.CRITICAL.value
        elif percentage_change > 100:
            return Severity.HIGH.value
        elif percentage_change > 75:
            return Severity.MEDIUM.value
        else:
            return Severity.LOW.value
    
    def _calculate_new_service_severity(self, cost: float) -> str:
        """Calculate severity for new services"""
        if cost > 1000:
            return Severity.HIGH.value
        elif cost > 500:
            return Severity.MEDIUM.value
        else:
            return Severity.LOW.value
    
    def _calculate_disappearance_severity(self, historical_cost: float) -> str:
        """Calculate severity for service disappearance"""
        if historical_cost > 1000:
            return Severity.HIGH.value
        elif historical_cost > 500:
            return Severity.MEDIUM.value
        else:
            return Severity.LOW.value
    
    def _calculate_budget_severity(self, deviation_percentage: float) -> str:
        """Calculate severity for budget deviations"""
        if deviation_percentage > 50:
            return Severity.CRITICAL.value
        elif deviation_percentage > 30:
            return Severity.HIGH.value
        elif deviation_percentage > 20:
            return Severity.MEDIUM.value
        else:
            return Severity.LOW.value


class AnomalyDetectionEngine:
    """Main anomaly detection engine combining multiple methods"""
    
    def __init__(self, use_ai: bool = True):
        """
        Initialize anomaly detection engine
        
        Args:
            use_ai: Whether to use AI-powered detection
        """
        self.statistical_detector = StatisticalAnomalyDetector()
        self.rule_detector = RuleBasedDetector()
        self.use_ai = use_ai
        
        if use_ai:
            try:
                self.bedrock_service = BedrockService()
            except Exception as e:
                logger.warning(f"AI service unavailable: {e}")
                self.use_ai = False
    
    def detect_anomalies(
        self, 
        current_data: List[UnifiedCostRecord],
        historical_data: List[UnifiedCostRecord],
        budget_info: Optional[Dict[str, float]] = None
    ) -> List[Anomaly]:
        """
        Comprehensive anomaly detection using multiple methods
        
        Args:
            current_data: Current period cost data
            historical_data: Historical cost data for baseline
            budget_info: Budget information for deviation detection
            
        Returns:
            List of detected anomalies
        """
        try:
            anomalies = []
            
            # Prepare data for analysis
            current_costs, historical_costs, service_data = self._prepare_data(
                current_data, historical_data
            )
            
            # 1. Statistical anomaly detection
            statistical_anomalies = self._detect_statistical_anomalies(
                current_costs, historical_costs, service_data
            )
            anomalies.extend(statistical_anomalies)
            
            # 2. Rule-based anomaly detection
            rule_anomalies = self._detect_rule_based_anomalies(
                current_data, historical_data, budget_info
            )
            anomalies.extend(rule_anomalies)
            
            # 3. AI-powered anomaly detection (if available)
            if self.use_ai:
                ai_anomalies = self._detect_ai_anomalies(
                    current_data, historical_data, service_data
                )
                anomalies.extend(ai_anomalies)
            
            # 4. Deduplicate and rank anomalies
            final_anomalies = self._deduplicate_and_rank(anomalies)
            
            logger.info(f"Detected {len(final_anomalies)} anomalies using multiple methods")
            return final_anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return []
    
    def _prepare_data(
        self, 
        current_data: List[UnifiedCostRecord],
        historical_data: List[UnifiedCostRecord]
    ) -> Tuple[List[float], List[float], Dict[str, Any]]:
        """Prepare data for anomaly detection"""
        
        # Extract total costs
        current_costs = [record.total_cost for record in current_data]
        historical_costs = [record.total_cost for record in historical_data]
        
        # Prepare service-level data
        current_services = defaultdict(float)
        historical_services = defaultdict(list)
        
        for record in current_data:
            for service, cost_info in record.services.items():
                current_services[service] += cost_info.cost
        
        for record in historical_data:
            for service, cost_info in record.services.items():
                historical_services[service].append(cost_info.cost)
        
        # Calculate historical averages
        historical_service_averages = {
            service: statistics.mean(costs) 
            for service, costs in historical_services.items()
        }
        
        service_data = {
            'current_services': dict(current_services),
            'historical_services': set(historical_services.keys()),
            'historical_averages': historical_service_averages
        }
        
        return current_costs, historical_costs, service_data
    
    def _detect_statistical_anomalies(
        self, 
        current_costs: List[float],
        historical_costs: List[float],
        service_data: Dict[str, Any]
    ) -> List[Anomaly]:
        """Detect statistical anomalies"""
        anomalies = []
        
        # Z-score anomalies
        z_score_anomalies = self.statistical_detector.detect_z_score_anomalies(
            current_costs, historical_costs
        )
        
        for index, z_score, description in z_score_anomalies:
            anomalies.append(Anomaly(
                type=AnomalyType.COST_SPIKE if "spike" in description else AnomalyType.COST_DROP,
                severity=self._calculate_statistical_severity(z_score),
                description=description,
                affected_services=["total_cost"],
                cost_impact=current_costs[index] if index < len(current_costs) else 0,
                detection_method="z_score",
                confidence_score=min(z_score / 5.0, 1.0),
                recommended_actions=self._get_statistical_recommendations(z_score),
                timestamp=datetime.utcnow(),
                metadata={'z_score': z_score, 'index': index}
            ))
        
        # IQR anomalies
        iqr_anomalies = self.statistical_detector.detect_iqr_anomalies(
            current_costs, historical_costs
        )
        
        for index, outlier_score, description in iqr_anomalies:
            anomalies.append(Anomaly(
                type=AnomalyType.UNUSUAL_PATTERN,
                severity=self._calculate_statistical_severity(outlier_score),
                description=description,
                affected_services=["total_cost"],
                cost_impact=current_costs[index] if index < len(current_costs) else 0,
                detection_method="iqr",
                confidence_score=min(outlier_score / 3.0, 1.0),
                recommended_actions=self._get_statistical_recommendations(outlier_score),
                timestamp=datetime.utcnow(),
                metadata={'outlier_score': outlier_score, 'index': index}
            ))
        
        return anomalies
    
    def _detect_rule_based_anomalies(
        self, 
        current_data: List[UnifiedCostRecord],
        historical_data: List[UnifiedCostRecord],
        budget_info: Optional[Dict[str, float]]
    ) -> List[Anomaly]:
        """Detect rule-based anomalies"""
        anomalies = []
        
        if not current_data or not historical_data:
            return anomalies
        
        # Prepare service data
        current_services = defaultdict(float)
        historical_services = defaultdict(float)
        historical_service_set = set()
        
        for record in current_data:
            for service, cost_info in record.services.items():
                current_services[service] += cost_info.cost
        
        for record in historical_data:
            for service, cost_info in record.services.items():
                historical_services[service] += cost_info.cost
                historical_service_set.add(service)
        
        # Calculate averages for historical data
        historical_averages = {
            service: cost / len(historical_data) 
            for service, cost in historical_services.items()
        }
        
        # Detect cost spikes
        spike_anomalies = self.rule_detector.detect_cost_spikes(
            dict(current_services), historical_averages
        )
        
        for spike in spike_anomalies:
            anomalies.append(Anomaly(
                type=AnomalyType.COST_SPIKE,
                severity=Severity(spike['severity']),
                description=spike['description'],
                affected_services=[spike['service']],
                cost_impact=spike['current_cost'] - spike['baseline_cost'],
                detection_method="rule_based_spike",
                confidence_score=0.8,
                recommended_actions=[
                    f"Investigate {spike['service']} usage patterns",
                    "Review recent configuration changes",
                    "Check for resource scaling events"
                ],
                timestamp=datetime.utcnow(),
                metadata=spike
            ))
        
        # Detect new services
        new_service_anomalies = self.rule_detector.detect_new_services(
            dict(current_services), historical_service_set
        )
        
        for new_service in new_service_anomalies:
            anomalies.append(Anomaly(
                type=AnomalyType.NEW_SERVICE,
                severity=Severity(new_service['severity']),
                description=new_service['description'],
                affected_services=[new_service['service']],
                cost_impact=new_service['cost'],
                detection_method="rule_based_new_service",
                confidence_score=0.9,
                recommended_actions=[
                    f"Verify {new_service['service']} deployment",
                    "Review service configuration",
                    "Confirm service necessity"
                ],
                timestamp=datetime.utcnow(),
                metadata=new_service
            ))
        
        # Detect service disappearance
        disappearance_anomalies = self.rule_detector.detect_service_disappearance(
            set(current_services.keys()), historical_service_set, historical_averages
        )
        
        for disappearance in disappearance_anomalies:
            anomalies.append(Anomaly(
                type=AnomalyType.SERVICE_DISAPPEARANCE,
                severity=Severity(disappearance['severity']),
                description=disappearance['description'],
                affected_services=[disappearance['service']],
                cost_impact=-disappearance['historical_cost'],
                detection_method="rule_based_disappearance",
                confidence_score=0.7,
                recommended_actions=[
                    f"Verify {disappearance['service']} status",
                    "Check for service termination",
                    "Review deployment changes"
                ],
                timestamp=datetime.utcnow(),
                metadata=disappearance
            ))
        
        # Detect budget deviations
        if budget_info:
            current_total = sum(record.total_cost for record in current_data)
            budget_amount = budget_info.get('monthly_budget', 0)
            
            budget_anomalies = self.rule_detector.detect_budget_deviations(
                current_total, budget_amount
            )
            
            for budget_anomaly in budget_anomalies:
                anomalies.append(Anomaly(
                    type=AnomalyType.BUDGET_DEVIATION,
                    severity=Severity(budget_anomaly['severity']),
                    description=budget_anomaly['description'],
                    affected_services=["total_budget"],
                    cost_impact=budget_anomaly['current_total'] - budget_anomaly['budget_amount'],
                    detection_method="rule_based_budget",
                    confidence_score=0.95,
                    recommended_actions=[
                        "Review budget allocation",
                        "Implement cost controls",
                        "Analyze spending patterns"
                    ],
                    timestamp=datetime.utcnow(),
                    metadata=budget_anomaly
                ))
        
        return anomalies
    
    def _detect_ai_anomalies(
        self, 
        current_data: List[UnifiedCostRecord],
        historical_data: List[UnifiedCostRecord],
        service_data: Dict[str, Any]
    ) -> List[Anomaly]:
        """Detect AI-powered anomalies"""
        try:
            # Prepare data for AI analysis
            current_dict = self._convert_records_to_dict(current_data)
            historical_dict = self._convert_records_to_dict(historical_data)
            
            # Calculate statistical context
            historical_costs = [record.total_cost for record in historical_data]
            stats = self.statistical_detector.calculate_metrics(historical_costs)
            
            statistical_context = {
                'mean_cost': stats.mean,
                'std_deviation': stats.std_deviation,
                'cv': stats.coefficient_variation
            }
            
            # Call AI anomaly detection
            ai_results = self.bedrock_service.detect_anomalies_with_ai(
                current_dict, historical_dict, statistical_context
            )
            
            # Convert AI results to Anomaly objects
            anomalies = []
            for ai_anomaly in ai_results.get('anomalies_detected', []):
                anomalies.append(Anomaly(
                    type=AnomalyType(ai_anomaly.get('type', 'unusual_pattern')),
                    severity=self._map_ai_severity(ai_anomaly.get('urgency', 'medium')),
                    description=ai_anomaly.get('description', 'AI-detected anomaly'),
                    affected_services=[ai_anomaly.get('service', 'unknown')],
                    cost_impact=ai_anomaly.get('current_cost', 0) - ai_anomaly.get('expected_cost', 0),
                    detection_method="ai_bedrock",
                    confidence_score=ai_anomaly.get('confidence', 0.5),
                    recommended_actions=ai_anomaly.get('potential_causes', []),
                    timestamp=datetime.utcnow(),
                    metadata=ai_anomaly
                ))
            
            return anomalies
            
        except Exception as e:
            logger.error(f"AI anomaly detection failed: {e}")
            return []
    
    def _convert_records_to_dict(self, records: List[UnifiedCostRecord]) -> Dict[str, Any]:
        """Convert UnifiedCostRecord list to dictionary format"""
        if not records:
            return {}
        
        total_cost = sum(record.total_cost for record in records)
        services = defaultdict(float)
        
        for record in records:
            for service, cost_info in record.services.items():
                services[service] += cost_info.cost
        
        return {
            'total_cost': total_cost,
            'services': dict(services),
            'record_count': len(records),
            'date_range': {
                'start': min(record.date for record in records),
                'end': max(record.date for record in records)
            }
        }
    
    def _calculate_statistical_severity(self, score: float) -> Severity:
        """Calculate severity based on statistical score"""
        if score > 4.0:
            return Severity.CRITICAL
        elif score > 3.0:
            return Severity.HIGH
        elif score > 2.0:
            return Severity.MEDIUM
        else:
            return Severity.LOW
    
    def _map_ai_severity(self, ai_urgency: str) -> Severity:
        """Map AI urgency to severity"""
        mapping = {
            'immediate': Severity.CRITICAL,
            'high': Severity.HIGH,
            'medium': Severity.MEDIUM,
            'low': Severity.LOW
        }
        return mapping.get(ai_urgency.lower(), Severity.MEDIUM)
    
    def _get_statistical_recommendations(self, score: float) -> List[str]:
        """Get recommendations based on statistical score"""
        if score > 3.0:
            return [
                "Immediate investigation required",
                "Review recent changes and deployments",
                "Check for security incidents or misconfigurations"
            ]
        elif score > 2.0:
            return [
                "Monitor closely for continued anomalies",
                "Review usage patterns and trends",
                "Consider cost optimization opportunities"
            ]
        else:
            return [
                "Continue monitoring",
                "Document for trend analysis"
            ]
    
    def _deduplicate_and_rank(self, anomalies: List[Anomaly]) -> List[Anomaly]:
        """Deduplicate and rank anomalies by severity and confidence"""
        if not anomalies:
            return []
        
        # Group similar anomalies
        grouped = defaultdict(list)
        for anomaly in anomalies:
            key = (anomaly.type, tuple(sorted(anomaly.affected_services)))
            grouped[key].append(anomaly)
        
        # Select best anomaly from each group
        final_anomalies = []
        for group in grouped.values():
            # Sort by confidence score and severity
            best_anomaly = max(group, key=lambda a: (
                a.confidence_score,
                {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[a.severity.value]
            ))
            final_anomalies.append(best_anomaly)
        
        # Sort final list by severity and confidence
        final_anomalies.sort(key=lambda a: (
            {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[a.severity.value],
            a.confidence_score
        ), reverse=True)
        
        return final_anomalies