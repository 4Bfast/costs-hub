"""
Trend Analysis Service for Cost Analytics

Provides comprehensive trend analysis including time series analysis,
seasonal decomposition, pattern recognition, and growth rate calculations.
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
import math

try:
    from ..models.multi_cloud_models import UnifiedCostRecord
    from ..utils.logging import create_logger as get_logger
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.multi_cloud_models import UnifiedCostRecord
    from utils.logging import create_logger
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class TrendDirection(Enum):
    """Trend direction classifications"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class TrendSignificance(Enum):
    """Trend significance levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class SeasonalPattern(Enum):
    """Seasonal pattern types"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    WEEKLY = "weekly"
    YEARLY = "yearly"
    NONE = "none"


@dataclass
class TrendMetrics:
    """Trend analysis metrics"""
    direction: TrendDirection
    slope: float
    r_squared: float
    growth_rate: float
    volatility: float
    significance: TrendSignificance
    confidence_interval: Tuple[float, float]
    trend_strength: float


@dataclass
class SeasonalDecomposition:
    """Seasonal decomposition results"""
    trend_component: List[float]
    seasonal_component: List[float]
    residual_component: List[float]
    seasonal_pattern: SeasonalPattern
    seasonal_strength: float
    trend_strength: float


@dataclass
class TrendAnalysis:
    """Complete trend analysis results"""
    overall_trend: TrendMetrics
    service_trends: Dict[str, TrendMetrics]
    seasonal_patterns: SeasonalDecomposition
    growth_rates: Dict[str, float]
    trend_confidence: float
    key_insights: List[str]
    metadata: Dict[str, Any]


class TimeSeriesAnalyzer:
    """Time series analysis for cost trends"""
    
    def __init__(self, min_data_points: int = 7):
        """
        Initialize time series analyzer
        
        Args:
            min_data_points: Minimum data points required for analysis
        """
        self.min_data_points = min_data_points
    
    def calculate_linear_trend(self, values: List[float], dates: List[str]) -> TrendMetrics:
        """
        Calculate linear trend using least squares regression
        
        Args:
            values: Cost values
            dates: Corresponding dates
            
        Returns:
            Trend metrics
        """
        if len(values) < self.min_data_points:
            return self._get_default_trend_metrics()
        
        try:
            # Convert dates to numeric values (days since first date)
            date_objects = [datetime.fromisoformat(date) for date in dates]
            first_date = min(date_objects)
            x_values = [(date - first_date).days for date in date_objects]
            
            # Calculate linear regression
            n = len(values)
            sum_x = sum(x_values)
            sum_y = sum(values)
            sum_xy = sum(x * y for x, y in zip(x_values, values))
            sum_x2 = sum(x * x for x in x_values)
            sum_y2 = sum(y * y for y in values)
            
            # Calculate slope and intercept
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            intercept = (sum_y - slope * sum_x) / n
            
            # Calculate R-squared
            y_mean = sum_y / n
            ss_tot = sum((y - y_mean) ** 2 for y in values)
            ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, values))
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            # Calculate growth rate (slope as percentage of mean)
            growth_rate = (slope / y_mean * 100) if y_mean != 0 else 0
            
            # Calculate volatility (coefficient of variation)
            volatility = (statistics.stdev(values) / y_mean * 100) if y_mean != 0 else 0
            
            # Determine trend direction
            direction = self._classify_trend_direction(slope, volatility)
            
            # Calculate significance
            significance = self._calculate_trend_significance(r_squared, len(values))
            
            # Calculate confidence interval (simplified)
            std_error = math.sqrt(ss_res / (n - 2)) if n > 2 else 0
            confidence_interval = (slope - 1.96 * std_error, slope + 1.96 * std_error)
            
            # Calculate trend strength
            trend_strength = min(abs(slope) * r_squared, 1.0)
            
            return TrendMetrics(
                direction=direction,
                slope=slope,
                r_squared=r_squared,
                growth_rate=growth_rate,
                volatility=volatility,
                significance=significance,
                confidence_interval=confidence_interval,
                trend_strength=trend_strength
            )
            
        except Exception as e:
            logger.error(f"Linear trend calculation failed: {e}")
            return self._get_default_trend_metrics()
    
    def calculate_moving_averages(
        self, 
        values: List[float], 
        windows: List[int] = [7, 14, 30]
    ) -> Dict[int, List[float]]:
        """
        Calculate moving averages for different window sizes
        
        Args:
            values: Cost values
            windows: Window sizes for moving averages
            
        Returns:
            Dictionary of window size to moving average values
        """
        moving_averages = {}
        
        for window in windows:
            if len(values) >= window:
                ma_values = []
                for i in range(len(values)):
                    if i >= window - 1:
                        window_values = values[i - window + 1:i + 1]
                        ma_values.append(sum(window_values) / len(window_values))
                    else:
                        ma_values.append(values[i])  # Use actual value for insufficient data
                moving_averages[window] = ma_values
        
        return moving_averages
    
    def detect_trend_changes(
        self, 
        values: List[float], 
        dates: List[str],
        window_size: int = 14
    ) -> List[Dict[str, Any]]:
        """
        Detect significant trend changes (breakpoints)
        
        Args:
            values: Cost values
            dates: Corresponding dates
            window_size: Window size for trend comparison
            
        Returns:
            List of trend change points
        """
        if len(values) < window_size * 2:
            return []
        
        trend_changes = []
        
        for i in range(window_size, len(values) - window_size):
            # Calculate trends before and after the point
            before_values = values[i - window_size:i]
            after_values = values[i:i + window_size]
            before_dates = dates[i - window_size:i]
            after_dates = dates[i:i + window_size]
            
            before_trend = self.calculate_linear_trend(before_values, before_dates)
            after_trend = self.calculate_linear_trend(after_values, after_dates)
            
            # Check for significant change in slope
            slope_change = abs(after_trend.slope - before_trend.slope)
            if slope_change > 0.1 and before_trend.r_squared > 0.3 and after_trend.r_squared > 0.3:
                trend_changes.append({
                    'date': dates[i],
                    'index': i,
                    'before_slope': before_trend.slope,
                    'after_slope': after_trend.slope,
                    'slope_change': slope_change,
                    'significance': 'high' if slope_change > 0.5 else 'medium'
                })
        
        return trend_changes
    
    def _classify_trend_direction(self, slope: float, volatility: float) -> TrendDirection:
        """Classify trend direction based on slope and volatility"""
        if volatility > 50:  # High volatility
            return TrendDirection.VOLATILE
        elif abs(slope) < 0.01:  # Very small slope
            return TrendDirection.STABLE
        elif slope > 0:
            return TrendDirection.INCREASING
        else:
            return TrendDirection.DECREASING
    
    def _calculate_trend_significance(self, r_squared: float, n: int) -> TrendSignificance:
        """Calculate trend significance based on R-squared and sample size"""
        if r_squared > 0.7 and n >= 30:
            return TrendSignificance.HIGH
        elif r_squared > 0.5 and n >= 14:
            return TrendSignificance.MEDIUM
        elif r_squared > 0.3 and n >= 7:
            return TrendSignificance.LOW
        else:
            return TrendSignificance.NONE
    
    def _get_default_trend_metrics(self) -> TrendMetrics:
        """Get default trend metrics for insufficient data"""
        return TrendMetrics(
            direction=TrendDirection.STABLE,
            slope=0.0,
            r_squared=0.0,
            growth_rate=0.0,
            volatility=0.0,
            significance=TrendSignificance.NONE,
            confidence_interval=(0.0, 0.0),
            trend_strength=0.0
        )


class SeasonalDecomposer:
    """Seasonal decomposition and pattern analysis"""
    
    def __init__(self, min_periods: int = 2):
        """
        Initialize seasonal decomposer
        
        Args:
            min_periods: Minimum periods required for seasonal analysis
        """
        self.min_periods = min_periods
    
    def decompose_time_series(
        self, 
        values: List[float], 
        dates: List[str],
        period_length: int = 30  # Default to monthly (30 days)
    ) -> SeasonalDecomposition:
        """
        Decompose time series into trend, seasonal, and residual components
        
        Args:
            values: Cost values
            dates: Corresponding dates
            period_length: Length of seasonal period in days
            
        Returns:
            Seasonal decomposition results
        """
        if len(values) < period_length * self.min_periods:
            return self._get_default_decomposition(len(values))
        
        try:
            # Simple seasonal decomposition using moving averages
            trend_component = self._calculate_trend_component(values, period_length)
            seasonal_component = self._calculate_seasonal_component(
                values, trend_component, period_length
            )
            residual_component = self._calculate_residual_component(
                values, trend_component, seasonal_component
            )
            
            # Detect seasonal pattern
            seasonal_pattern = self._detect_seasonal_pattern(seasonal_component, period_length)
            
            # Calculate seasonal and trend strength
            seasonal_strength = self._calculate_seasonal_strength(seasonal_component)
            trend_strength = self._calculate_trend_strength(trend_component)
            
            return SeasonalDecomposition(
                trend_component=trend_component,
                seasonal_component=seasonal_component,
                residual_component=residual_component,
                seasonal_pattern=seasonal_pattern,
                seasonal_strength=seasonal_strength,
                trend_strength=trend_strength
            )
            
        except Exception as e:
            logger.error(f"Seasonal decomposition failed: {e}")
            return self._get_default_decomposition(len(values))
    
    def analyze_seasonality(
        self, 
        cost_records: List[UnifiedCostRecord]
    ) -> Dict[str, Any]:
        """
        Analyze seasonal patterns in cost data
        
        Args:
            cost_records: Historical cost records
            
        Returns:
            Seasonal analysis results
        """
        if len(cost_records) < 30:  # Need at least 30 days
            return {'seasonal_patterns': {}, 'confidence': 0.0}
        
        # Group data by different time periods
        monthly_patterns = self._analyze_monthly_patterns(cost_records)
        weekly_patterns = self._analyze_weekly_patterns(cost_records)
        quarterly_patterns = self._analyze_quarterly_patterns(cost_records)
        
        # Determine strongest seasonal pattern
        patterns = {
            'monthly': monthly_patterns,
            'weekly': weekly_patterns,
            'quarterly': quarterly_patterns
        }
        
        strongest_pattern = max(patterns.items(), key=lambda x: x[1].get('strength', 0))
        
        return {
            'seasonal_patterns': patterns,
            'strongest_pattern': strongest_pattern[0],
            'confidence': strongest_pattern[1].get('strength', 0),
            'recommendations': self._get_seasonal_recommendations(patterns)
        }
    
    def _calculate_trend_component(self, values: List[float], period_length: int) -> List[float]:
        """Calculate trend component using centered moving average"""
        trend = []
        half_period = period_length // 2
        
        for i in range(len(values)):
            if i < half_period or i >= len(values) - half_period:
                # Use simple average for edges
                start = max(0, i - half_period)
                end = min(len(values), i + half_period + 1)
                trend.append(sum(values[start:end]) / (end - start))
            else:
                # Centered moving average
                window = values[i - half_period:i + half_period + 1]
                trend.append(sum(window) / len(window))
        
        return trend
    
    def _calculate_seasonal_component(
        self, 
        values: List[float], 
        trend: List[float], 
        period_length: int
    ) -> List[float]:
        """Calculate seasonal component"""
        # Detrend the data
        detrended = [v - t for v, t in zip(values, trend)]
        
        # Calculate seasonal indices
        seasonal_indices = {}
        for i, value in enumerate(detrended):
            period_index = i % period_length
            if period_index not in seasonal_indices:
                seasonal_indices[period_index] = []
            seasonal_indices[period_index].append(value)
        
        # Average seasonal indices
        avg_seasonal = {}
        for period_index, values_list in seasonal_indices.items():
            avg_seasonal[period_index] = sum(values_list) / len(values_list)
        
        # Create seasonal component
        seasonal = []
        for i in range(len(values)):
            period_index = i % period_length
            seasonal.append(avg_seasonal.get(period_index, 0))
        
        return seasonal
    
    def _calculate_residual_component(
        self, 
        values: List[float], 
        trend: List[float], 
        seasonal: List[float]
    ) -> List[float]:
        """Calculate residual component"""
        return [v - t - s for v, t, s in zip(values, trend, seasonal)]
    
    def _detect_seasonal_pattern(
        self, 
        seasonal_component: List[float], 
        period_length: int
    ) -> SeasonalPattern:
        """Detect the type of seasonal pattern"""
        if period_length <= 7:
            return SeasonalPattern.WEEKLY
        elif period_length <= 31:
            return SeasonalPattern.MONTHLY
        elif period_length <= 93:
            return SeasonalPattern.QUARTERLY
        elif period_length <= 366:
            return SeasonalPattern.YEARLY
        else:
            return SeasonalPattern.NONE
    
    def _calculate_seasonal_strength(self, seasonal_component: List[float]) -> float:
        """Calculate strength of seasonal component"""
        if not seasonal_component:
            return 0.0
        
        seasonal_variance = statistics.variance(seasonal_component) if len(seasonal_component) > 1 else 0
        return min(seasonal_variance / (statistics.mean([abs(x) for x in seasonal_component]) + 1e-6), 1.0)
    
    def _calculate_trend_strength(self, trend_component: List[float]) -> float:
        """Calculate strength of trend component"""
        if len(trend_component) < 2:
            return 0.0
        
        # Calculate trend strength based on monotonicity
        differences = [trend_component[i+1] - trend_component[i] for i in range(len(trend_component)-1)]
        positive_diffs = sum(1 for d in differences if d > 0)
        negative_diffs = sum(1 for d in differences if d < 0)
        
        monotonicity = abs(positive_diffs - negative_diffs) / len(differences)
        return monotonicity
    
    def _analyze_monthly_patterns(self, cost_records: List[UnifiedCostRecord]) -> Dict[str, Any]:
        """Analyze monthly seasonal patterns"""
        monthly_costs = defaultdict(list)
        
        for record in cost_records:
            month = datetime.fromisoformat(record.date).month
            monthly_costs[month].append(record.total_cost)
        
        if len(monthly_costs) < 3:
            return {'strength': 0.0, 'pattern': {}}
        
        monthly_averages = {
            month: sum(costs) / len(costs) 
            for month, costs in monthly_costs.items()
        }
        
        # Calculate coefficient of variation as strength measure
        avg_values = list(monthly_averages.values())
        if len(avg_values) > 1:
            cv = statistics.stdev(avg_values) / statistics.mean(avg_values)
            strength = min(cv, 1.0)
        else:
            strength = 0.0
        
        return {
            'strength': strength,
            'pattern': monthly_averages,
            'peak_month': max(monthly_averages.items(), key=lambda x: x[1])[0] if monthly_averages else None,
            'low_month': min(monthly_averages.items(), key=lambda x: x[1])[0] if monthly_averages else None
        }
    
    def _analyze_weekly_patterns(self, cost_records: List[UnifiedCostRecord]) -> Dict[str, Any]:
        """Analyze weekly seasonal patterns"""
        weekly_costs = defaultdict(list)
        
        for record in cost_records:
            weekday = datetime.fromisoformat(record.date).weekday()
            weekly_costs[weekday].append(record.total_cost)
        
        if len(weekly_costs) < 5:
            return {'strength': 0.0, 'pattern': {}}
        
        weekly_averages = {
            day: sum(costs) / len(costs) 
            for day, costs in weekly_costs.items()
        }
        
        avg_values = list(weekly_averages.values())
        if len(avg_values) > 1:
            cv = statistics.stdev(avg_values) / statistics.mean(avg_values)
            strength = min(cv, 1.0)
        else:
            strength = 0.0
        
        return {
            'strength': strength,
            'pattern': weekly_averages,
            'peak_day': max(weekly_averages.items(), key=lambda x: x[1])[0] if weekly_averages else None,
            'low_day': min(weekly_averages.items(), key=lambda x: x[1])[0] if weekly_averages else None
        }
    
    def _analyze_quarterly_patterns(self, cost_records: List[UnifiedCostRecord]) -> Dict[str, Any]:
        """Analyze quarterly seasonal patterns"""
        quarterly_costs = defaultdict(list)
        
        for record in cost_records:
            quarter = (datetime.fromisoformat(record.date).month - 1) // 3 + 1
            quarterly_costs[quarter].append(record.total_cost)
        
        if len(quarterly_costs) < 2:
            return {'strength': 0.0, 'pattern': {}}
        
        quarterly_averages = {
            quarter: sum(costs) / len(costs) 
            for quarter, costs in quarterly_costs.items()
        }
        
        avg_values = list(quarterly_averages.values())
        if len(avg_values) > 1:
            cv = statistics.stdev(avg_values) / statistics.mean(avg_values)
            strength = min(cv, 1.0)
        else:
            strength = 0.0
        
        return {
            'strength': strength,
            'pattern': quarterly_averages,
            'peak_quarter': max(quarterly_averages.items(), key=lambda x: x[1])[0] if quarterly_averages else None,
            'low_quarter': min(quarterly_averages.items(), key=lambda x: x[1])[0] if quarterly_averages else None
        }
    
    def _get_seasonal_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Get recommendations based on seasonal patterns"""
        recommendations = []
        
        # Find strongest pattern
        strongest = max(patterns.items(), key=lambda x: x[1].get('strength', 0))
        pattern_type, pattern_data = strongest
        
        if pattern_data.get('strength', 0) > 0.3:
            recommendations.append(f"Strong {pattern_type} seasonal pattern detected")
            
            if pattern_type == 'monthly':
                peak_month = pattern_data.get('peak_month')
                if peak_month:
                    recommendations.append(f"Peak costs typically occur in month {peak_month}")
            elif pattern_type == 'quarterly':
                peak_quarter = pattern_data.get('peak_quarter')
                if peak_quarter:
                    recommendations.append(f"Peak costs typically occur in Q{peak_quarter}")
            
            recommendations.append("Consider seasonal budgeting and resource planning")
        
        return recommendations
    
    def _get_default_decomposition(self, length: int) -> SeasonalDecomposition:
        """Get default decomposition for insufficient data"""
        return SeasonalDecomposition(
            trend_component=[0.0] * length,
            seasonal_component=[0.0] * length,
            residual_component=[0.0] * length,
            seasonal_pattern=SeasonalPattern.NONE,
            seasonal_strength=0.0,
            trend_strength=0.0
        )


class TrendAnalyzer:
    """Main trend analysis service"""
    
    def __init__(self):
        """Initialize trend analyzer"""
        self.time_series_analyzer = TimeSeriesAnalyzer()
        self.seasonal_decomposer = SeasonalDecomposer()
    
    def analyze_trends(self, cost_records: List[UnifiedCostRecord]) -> TrendAnalysis:
        """
        Comprehensive trend analysis
        
        Args:
            cost_records: Historical cost records
            
        Returns:
            Complete trend analysis results
        """
        try:
            if len(cost_records) < 7:
                return self._get_default_analysis()
            
            # Prepare data
            dates = [record.date for record in cost_records]
            total_costs = [record.total_cost for record in cost_records]
            
            # Overall trend analysis
            overall_trend = self.time_series_analyzer.calculate_linear_trend(total_costs, dates)
            
            # Service-level trend analysis
            service_trends = self._analyze_service_trends(cost_records)
            
            # Seasonal analysis
            seasonal_patterns = self.seasonal_decomposer.decompose_time_series(total_costs, dates)
            
            # Growth rate calculations
            growth_rates = self._calculate_growth_rates(cost_records)
            
            # Calculate overall confidence
            trend_confidence = self._calculate_trend_confidence(overall_trend, len(cost_records))
            
            # Generate key insights
            key_insights = self._generate_key_insights(
                overall_trend, service_trends, seasonal_patterns, growth_rates
            )
            
            return TrendAnalysis(
                overall_trend=overall_trend,
                service_trends=service_trends,
                seasonal_patterns=seasonal_patterns,
                growth_rates=growth_rates,
                trend_confidence=trend_confidence,
                key_insights=key_insights,
                metadata={
                    'analysis_timestamp': datetime.utcnow().isoformat(),
                    'data_points': len(cost_records),
                    'date_range': {
                        'start': min(dates),
                        'end': max(dates)
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return self._get_default_analysis()
    
    def _analyze_service_trends(self, cost_records: List[UnifiedCostRecord]) -> Dict[str, TrendMetrics]:
        """Analyze trends for individual services"""
        service_data = defaultdict(lambda: {'costs': [], 'dates': []})
        
        # Collect service-level data
        for record in cost_records:
            for service, cost_info in record.services.items():
                service_data[service]['costs'].append(cost_info.cost)
                service_data[service]['dates'].append(record.date)
        
        # Analyze trends for each service
        service_trends = {}
        for service, data in service_data.items():
            if len(data['costs']) >= 7:  # Minimum data points
                trend = self.time_series_analyzer.calculate_linear_trend(
                    data['costs'], data['dates']
                )
                service_trends[service] = trend
        
        return service_trends
    
    def _calculate_growth_rates(self, cost_records: List[UnifiedCostRecord]) -> Dict[str, float]:
        """Calculate various growth rates"""
        if len(cost_records) < 2:
            return {}
        
        # Sort by date
        sorted_records = sorted(cost_records, key=lambda x: x.date)
        
        # Calculate different growth rates
        growth_rates = {}
        
        # Month-over-month growth
        if len(sorted_records) >= 30:
            recent_30_days = sorted_records[-30:]
            previous_30_days = sorted_records[-60:-30] if len(sorted_records) >= 60 else []
            
            if previous_30_days:
                recent_avg = sum(r.total_cost for r in recent_30_days) / len(recent_30_days)
                previous_avg = sum(r.total_cost for r in previous_30_days) / len(previous_30_days)
                
                if previous_avg != 0:
                    growth_rates['month_over_month'] = ((recent_avg - previous_avg) / previous_avg) * 100
        
        # Week-over-week growth
        if len(sorted_records) >= 14:
            recent_7_days = sorted_records[-7:]
            previous_7_days = sorted_records[-14:-7]
            
            recent_avg = sum(r.total_cost for r in recent_7_days) / len(recent_7_days)
            previous_avg = sum(r.total_cost for r in previous_7_days) / len(previous_7_days)
            
            if previous_avg != 0:
                growth_rates['week_over_week'] = ((recent_avg - previous_avg) / previous_avg) * 100
        
        # Overall growth rate (first to last)
        first_cost = sorted_records[0].total_cost
        last_cost = sorted_records[-1].total_cost
        
        if first_cost != 0:
            days_diff = (datetime.fromisoformat(sorted_records[-1].date) - 
                        datetime.fromisoformat(sorted_records[0].date)).days
            if days_diff > 0:
                daily_growth = ((last_cost / first_cost) ** (1/days_diff) - 1) * 100
                growth_rates['daily_compound'] = daily_growth
                growth_rates['annualized'] = ((1 + daily_growth/100) ** 365 - 1) * 100
        
        return growth_rates
    
    def _calculate_trend_confidence(self, trend: TrendMetrics, data_points: int) -> float:
        """Calculate overall confidence in trend analysis"""
        confidence_factors = [
            trend.r_squared,  # How well the trend fits
            min(data_points / 30, 1.0),  # Data sufficiency (30 days = 100%)
            1.0 - min(trend.volatility / 100, 1.0),  # Lower volatility = higher confidence
            {'high': 1.0, 'medium': 0.7, 'low': 0.4, 'none': 0.0}[trend.significance.value]
        ]
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _generate_key_insights(
        self, 
        overall_trend: TrendMetrics,
        service_trends: Dict[str, TrendMetrics],
        seasonal_patterns: SeasonalDecomposition,
        growth_rates: Dict[str, float]
    ) -> List[str]:
        """Generate key insights from trend analysis"""
        insights = []
        
        # Overall trend insights
        if overall_trend.significance != TrendSignificance.NONE:
            direction_text = overall_trend.direction.value
            growth_text = f"{abs(overall_trend.growth_rate):.1f}%"
            insights.append(f"Overall cost trend is {direction_text} at {growth_text} rate")
        
        # Service trend insights
        if service_trends:
            increasing_services = [
                service for service, trend in service_trends.items()
                if trend.direction == TrendDirection.INCREASING and trend.significance != TrendSignificance.NONE
            ]
            
            if increasing_services:
                top_increasing = sorted(
                    increasing_services, 
                    key=lambda s: service_trends[s].growth_rate, 
                    reverse=True
                )[:3]
                insights.append(f"Top increasing services: {', '.join(top_increasing)}")
        
        # Seasonal insights
        if seasonal_patterns.seasonal_strength > 0.3:
            insights.append(f"Strong seasonal pattern detected with {seasonal_patterns.seasonal_pattern.value} cycle")
        
        # Growth rate insights
        if 'month_over_month' in growth_rates:
            mom_growth = growth_rates['month_over_month']
            if abs(mom_growth) > 10:
                direction = "increased" if mom_growth > 0 else "decreased"
                insights.append(f"Costs {direction} by {abs(mom_growth):.1f}% month-over-month")
        
        # Volatility insights
        if overall_trend.volatility > 30:
            insights.append("High cost volatility detected - consider implementing cost controls")
        
        return insights
    
    def _get_default_analysis(self) -> TrendAnalysis:
        """Get default analysis for insufficient data"""
        return TrendAnalysis(
            overall_trend=self.time_series_analyzer._get_default_trend_metrics(),
            service_trends={},
            seasonal_patterns=self.seasonal_decomposer._get_default_decomposition(0),
            growth_rates={},
            trend_confidence=0.0,
            key_insights=["Insufficient data for trend analysis"],
            metadata={
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'data_points': 0,
                'insufficient_data': True
            }
        )