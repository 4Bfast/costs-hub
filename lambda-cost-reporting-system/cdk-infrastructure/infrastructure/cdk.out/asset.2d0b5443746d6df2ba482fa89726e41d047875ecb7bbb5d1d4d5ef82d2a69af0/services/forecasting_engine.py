"""
Forecasting Engine for Cost Analytics

Provides comprehensive cost forecasting using multiple models including
ARIMA, Prophet-like seasonal forecasting, ML-based forecasting, and ensemble methods.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics
import math
from collections import defaultdict

try:
    from ..models.multi_cloud_models import UnifiedCostRecord
    from ..utils.logging import create_logger as get_logger
    from .trend_analysis_service import TrendAnalyzer, TrendAnalysis
    from .bedrock_service import BedrockService
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.multi_cloud_models import UnifiedCostRecord
    from utils.logging import create_logger
    from trend_analysis_service import TrendAnalyzer, TrendAnalysis
    from bedrock_service import BedrockService
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class ForecastMethod(Enum):
    """Forecasting method types"""
    ARIMA = "arima"
    PROPHET = "prophet"
    LINEAR_REGRESSION = "linear_regression"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    SEASONAL_NAIVE = "seasonal_naive"
    ENSEMBLE = "ensemble"


class ForecastAccuracy(Enum):
    """Forecast accuracy levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class ForecastPoint:
    """Individual forecast point"""
    date: str
    predicted_cost: float
    confidence_interval: Tuple[float, float]
    method_used: ForecastMethod
    confidence_score: float
    key_drivers: List[str]


@dataclass
class ForecastResult:
    """Complete forecast result"""
    forecast_period: str
    predictions: List[ForecastPoint]
    total_forecast: Dict[str, Any]
    model_performance: Dict[str, float]
    assumptions: List[str]
    methodology: str
    accuracy_assessment: ForecastAccuracy
    metadata: Dict[str, Any]


class ARIMAForecaster:
    """Simplified ARIMA-like forecasting implementation"""
    
    def __init__(self, p: int = 1, d: int = 1, q: int = 1):
        """
        Initialize ARIMA forecaster
        
        Args:
            p: Autoregressive order
            d: Differencing order
            q: Moving average order
        """
        self.p = p
        self.d = d
        self.q = q
    
    def forecast(
        self, 
        values: List[float], 
        forecast_horizon: int,
        dates: List[str]
    ) -> List[ForecastPoint]:
        """
        Generate ARIMA-like forecast
        
        Args:
            values: Historical values
            forecast_horizon: Number of periods to forecast
            dates: Historical dates
            
        Returns:
            List of forecast points
        """
        if len(values) < max(self.p, self.q) + self.d:
            return self._fallback_forecast(values, forecast_horizon, dates)
        
        try:
            # Simple differencing for stationarity
            diff_values = self._difference_series(values, self.d)
            
            # Calculate autoregressive parameters (simplified)
            ar_params = self._estimate_ar_parameters(diff_values, self.p)
            
            # Calculate moving average parameters (simplified)
            ma_params = self._estimate_ma_parameters(diff_values, self.q)
            
            # Generate forecasts
            forecasts = []
            last_values = diff_values[-self.p:] if self.p > 0 else []
            last_errors = [0.0] * self.q  # Simplified error terms
            
            for i in range(forecast_horizon):
                # AR component
                ar_component = sum(
                    ar_params[j] * last_values[-(j+1)] 
                    for j in range(min(len(ar_params), len(last_values)))
                )
                
                # MA component
                ma_component = sum(
                    ma_params[j] * last_errors[-(j+1)]
                    for j in range(min(len(ma_params), len(last_errors)))
                )
                
                # Forecast value
                forecast_diff = ar_component + ma_component
                
                # Integrate back to original scale
                if self.d == 1:
                    forecast_value = values[-1] + forecast_diff
                else:
                    forecast_value = forecast_diff
                
                # Calculate confidence interval (simplified)
                std_error = statistics.stdev(diff_values) if len(diff_values) > 1 else 0
                confidence_interval = (
                    forecast_value - 1.96 * std_error,
                    forecast_value + 1.96 * std_error
                )
                
                # Generate forecast date
                last_date = datetime.fromisoformat(dates[-1])
                forecast_date = (last_date + timedelta(days=i+1)).isoformat()[:10]
                
                forecast_point = ForecastPoint(
                    date=forecast_date,
                    predicted_cost=max(0, forecast_value),  # Ensure non-negative
                    confidence_interval=confidence_interval,
                    method_used=ForecastMethod.ARIMA,
                    confidence_score=max(0.3, 1.0 - (i * 0.1)),  # Decreasing confidence
                    key_drivers=["historical_trend", "autoregressive_pattern"]
                )
                
                forecasts.append(forecast_point)
                
                # Update for next iteration
                last_values.append(forecast_diff)
                if len(last_values) > self.p:
                    last_values.pop(0)
                
                last_errors.append(0.0)  # Simplified error
                if len(last_errors) > self.q:
                    last_errors.pop(0)
            
            return forecasts
            
        except Exception as e:
            logger.error(f"ARIMA forecasting failed: {e}")
            return self._fallback_forecast(values, forecast_horizon, dates)
    
    def _difference_series(self, values: List[float], d: int) -> List[float]:
        """Apply differencing to make series stationary"""
        diff_values = values.copy()
        
        for _ in range(d):
            if len(diff_values) <= 1:
                break
            diff_values = [diff_values[i] - diff_values[i-1] for i in range(1, len(diff_values))]
        
        return diff_values
    
    def _estimate_ar_parameters(self, values: List[float], p: int) -> List[float]:
        """Estimate autoregressive parameters using Yule-Walker equations (simplified)"""
        if len(values) < p + 1:
            return [0.0] * p
        
        # Simple estimation using correlation
        params = []
        for lag in range(1, p + 1):
            if len(values) > lag:
                correlation = self._calculate_autocorrelation(values, lag)
                params.append(correlation * 0.5)  # Simplified coefficient
            else:
                params.append(0.0)
        
        return params
    
    def _estimate_ma_parameters(self, values: List[float], q: int) -> List[float]:
        """Estimate moving average parameters (simplified)"""
        if len(values) < q + 1:
            return [0.0] * q
        
        # Simple estimation
        params = []
        residuals = self._calculate_residuals(values)
        
        for lag in range(1, q + 1):
            if len(residuals) > lag:
                correlation = self._calculate_autocorrelation(residuals, lag)
                params.append(correlation * 0.3)  # Simplified coefficient
            else:
                params.append(0.0)
        
        return params
    
    def _calculate_autocorrelation(self, values: List[float], lag: int) -> float:
        """Calculate autocorrelation at given lag"""
        if len(values) <= lag:
            return 0.0
        
        n = len(values) - lag
        if n <= 1:
            return 0.0
        
        mean_val = statistics.mean(values)
        
        numerator = sum(
            (values[i] - mean_val) * (values[i + lag] - mean_val)
            for i in range(n)
        )
        
        denominator = sum((v - mean_val) ** 2 for v in values)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def _calculate_residuals(self, values: List[float]) -> List[float]:
        """Calculate residuals for MA parameter estimation"""
        if len(values) < 2:
            return values
        
        # Simple residuals using moving average
        window = min(3, len(values))
        residuals = []
        
        for i in range(len(values)):
            start = max(0, i - window // 2)
            end = min(len(values), i + window // 2 + 1)
            window_mean = sum(values[start:end]) / (end - start)
            residuals.append(values[i] - window_mean)
        
        return residuals
    
    def _fallback_forecast(
        self, 
        values: List[float], 
        forecast_horizon: int, 
        dates: List[str]
    ) -> List[ForecastPoint]:
        """Fallback to simple trend-based forecast"""
        if not values:
            return []
        
        # Simple linear trend
        if len(values) >= 2:
            slope = (values[-1] - values[0]) / (len(values) - 1)
        else:
            slope = 0
        
        forecasts = []
        last_value = values[-1]
        
        for i in range(forecast_horizon):
            forecast_value = last_value + slope * (i + 1)
            
            last_date = datetime.fromisoformat(dates[-1])
            forecast_date = (last_date + timedelta(days=i+1)).isoformat()[:10]
            
            forecasts.append(ForecastPoint(
                date=forecast_date,
                predicted_cost=max(0, forecast_value),
                confidence_interval=(forecast_value * 0.8, forecast_value * 1.2),
                method_used=ForecastMethod.LINEAR_REGRESSION,
                confidence_score=0.3,
                key_drivers=["linear_trend"]
            ))
        
        return forecasts


class ProphetLikeForecaster:
    """Prophet-like seasonal forecasting implementation"""
    
    def __init__(self):
        """Initialize Prophet-like forecaster"""
        self.trend_component = None
        self.seasonal_component = None
        self.holiday_component = None
    
    def forecast(
        self, 
        values: List[float], 
        dates: List[str],
        forecast_horizon: int
    ) -> List[ForecastPoint]:
        """
        Generate Prophet-like forecast with trend and seasonality
        
        Args:
            values: Historical values
            dates: Historical dates
            forecast_horizon: Number of periods to forecast
            
        Returns:
            List of forecast points
        """
        if len(values) < 14:  # Need at least 2 weeks
            return self._simple_seasonal_forecast(values, dates, forecast_horizon)
        
        try:
            # Decompose into trend and seasonal components
            trend = self._extract_trend(values, dates)
            seasonal = self._extract_seasonal(values, dates)
            
            # Generate forecasts
            forecasts = []
            
            for i in range(forecast_horizon):
                # Forecast date
                last_date = datetime.fromisoformat(dates[-1])
                forecast_date = (last_date + timedelta(days=i+1)).isoformat()[:10]
                
                # Trend component
                trend_value = self._forecast_trend(trend, i + 1)
                
                # Seasonal component
                seasonal_value = self._forecast_seasonal(seasonal, dates, i + 1)
                
                # Combined forecast
                forecast_value = trend_value + seasonal_value
                
                # Confidence interval based on historical variance
                historical_variance = statistics.variance(values) if len(values) > 1 else 0
                std_error = math.sqrt(historical_variance) * (1 + i * 0.1)  # Increasing uncertainty
                
                confidence_interval = (
                    forecast_value - 1.96 * std_error,
                    forecast_value + 1.96 * std_error
                )
                
                forecasts.append(ForecastPoint(
                    date=forecast_date,
                    predicted_cost=max(0, forecast_value),
                    confidence_interval=confidence_interval,
                    method_used=ForecastMethod.PROPHET,
                    confidence_score=max(0.2, 0.8 - (i * 0.05)),
                    key_drivers=["trend", "seasonality"]
                ))
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Prophet-like forecasting failed: {e}")
            return self._simple_seasonal_forecast(values, dates, forecast_horizon)
    
    def _extract_trend(self, values: List[float], dates: List[str]) -> List[float]:
        """Extract trend component using moving average"""
        window_size = min(7, len(values) // 3)  # Weekly or adaptive window
        trend = []
        
        for i in range(len(values)):
            start = max(0, i - window_size // 2)
            end = min(len(values), i + window_size // 2 + 1)
            window_values = values[start:end]
            trend.append(sum(window_values) / len(window_values))
        
        return trend
    
    def _extract_seasonal(self, values: List[float], dates: List[str]) -> Dict[int, float]:
        """Extract seasonal component (weekly pattern)"""
        seasonal_data = defaultdict(list)
        
        for i, date_str in enumerate(dates):
            date_obj = datetime.fromisoformat(date_str)
            day_of_week = date_obj.weekday()
            seasonal_data[day_of_week].append(values[i])
        
        # Calculate average for each day of week
        seasonal_averages = {}
        overall_mean = statistics.mean(values)
        
        for day, day_values in seasonal_data.items():
            day_mean = statistics.mean(day_values)
            seasonal_averages[day] = day_mean - overall_mean
        
        return seasonal_averages
    
    def _forecast_trend(self, trend: List[float], steps_ahead: int) -> float:
        """Forecast trend component"""
        if len(trend) < 2:
            return trend[-1] if trend else 0
        
        # Simple linear extrapolation
        recent_trend = trend[-min(7, len(trend)):]  # Use last week
        if len(recent_trend) >= 2:
            slope = (recent_trend[-1] - recent_trend[0]) / (len(recent_trend) - 1)
            return trend[-1] + slope * steps_ahead
        else:
            return trend[-1]
    
    def _forecast_seasonal(
        self, 
        seasonal: Dict[int, float], 
        dates: List[str], 
        steps_ahead: int
    ) -> float:
        """Forecast seasonal component"""
        if not seasonal or not dates:
            return 0
        
        # Determine day of week for forecast
        last_date = datetime.fromisoformat(dates[-1])
        forecast_date = last_date + timedelta(days=steps_ahead)
        forecast_day = forecast_date.weekday()
        
        return seasonal.get(forecast_day, 0)
    
    def _simple_seasonal_forecast(
        self, 
        values: List[float], 
        dates: List[str], 
        forecast_horizon: int
    ) -> List[ForecastPoint]:
        """Simple seasonal forecast for insufficient data"""
        if not values:
            return []
        
        # Use last value with small random variation
        last_value = values[-1]
        recent_mean = statistics.mean(values[-7:]) if len(values) >= 7 else last_value
        
        forecasts = []
        for i in range(forecast_horizon):
            # Simple forecast with slight trend
            forecast_value = recent_mean * (1 + 0.001 * i)  # Very small growth
            
            last_date = datetime.fromisoformat(dates[-1])
            forecast_date = (last_date + timedelta(days=i+1)).isoformat()[:10]
            
            forecasts.append(ForecastPoint(
                date=forecast_date,
                predicted_cost=max(0, forecast_value),
                confidence_interval=(forecast_value * 0.9, forecast_value * 1.1),
                method_used=ForecastMethod.SEASONAL_NAIVE,
                confidence_score=0.4,
                key_drivers=["historical_average"]
            ))
        
        return forecasts


class ExponentialSmoothingForecaster:
    """Exponential smoothing forecasting implementation"""
    
    def __init__(self, alpha: float = 0.3, beta: float = 0.1, gamma: float = 0.1):
        """
        Initialize exponential smoothing forecaster
        
        Args:
            alpha: Level smoothing parameter
            beta: Trend smoothing parameter
            gamma: Seasonal smoothing parameter
        """
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
    
    def forecast(
        self, 
        values: List[float], 
        dates: List[str],
        forecast_horizon: int
    ) -> List[ForecastPoint]:
        """
        Generate exponential smoothing forecast
        
        Args:
            values: Historical values
            dates: Historical dates
            forecast_horizon: Number of periods to forecast
            
        Returns:
            List of forecast points
        """
        if len(values) < 3:
            return self._simple_exponential_forecast(values, dates, forecast_horizon)
        
        try:
            # Initialize components
            level = values[0]
            trend = (values[1] - values[0]) if len(values) > 1 else 0
            seasonal = self._initialize_seasonal(values)
            
            # Update components through historical data
            for i in range(1, len(values)):
                prev_level = level
                
                # Update level
                level = self.alpha * values[i] + (1 - self.alpha) * (level + trend)
                
                # Update trend
                trend = self.beta * (level - prev_level) + (1 - self.beta) * trend
                
                # Update seasonal (simplified)
                if seasonal and i >= len(seasonal):
                    seasonal_index = i % len(seasonal)
                    seasonal[seasonal_index] = (
                        self.gamma * (values[i] - level) + 
                        (1 - self.gamma) * seasonal[seasonal_index]
                    )
            
            # Generate forecasts
            forecasts = []
            for i in range(forecast_horizon):
                # Forecast components
                forecast_level = level + trend * (i + 1)
                seasonal_component = seasonal[i % len(seasonal)] if seasonal else 0
                forecast_value = forecast_level + seasonal_component
                
                # Calculate confidence interval
                error_variance = self._calculate_error_variance(values, level, trend, seasonal)
                std_error = math.sqrt(error_variance) * (1 + i * 0.1)
                
                confidence_interval = (
                    forecast_value - 1.96 * std_error,
                    forecast_value + 1.96 * std_error
                )
                
                # Generate forecast date
                last_date = datetime.fromisoformat(dates[-1])
                forecast_date = (last_date + timedelta(days=i+1)).isoformat()[:10]
                
                forecasts.append(ForecastPoint(
                    date=forecast_date,
                    predicted_cost=max(0, forecast_value),
                    confidence_interval=confidence_interval,
                    method_used=ForecastMethod.EXPONENTIAL_SMOOTHING,
                    confidence_score=max(0.3, 0.7 - (i * 0.05)),
                    key_drivers=["exponential_smoothing", "trend", "seasonality"]
                ))
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Exponential smoothing failed: {e}")
            return self._simple_exponential_forecast(values, dates, forecast_horizon)
    
    def _initialize_seasonal(self, values: List[float]) -> Optional[List[float]]:
        """Initialize seasonal components"""
        if len(values) < 14:  # Need at least 2 weeks for weekly seasonality
            return None
        
        # Simple weekly seasonality initialization
        seasonal_length = 7
        seasonal = [0.0] * seasonal_length
        
        for i in range(len(values)):
            seasonal_index = i % seasonal_length
            seasonal[seasonal_index] += values[i]
        
        # Average and center around zero
        counts = [0] * seasonal_length
        for i in range(len(values)):
            counts[i % seasonal_length] += 1
        
        for i in range(seasonal_length):
            if counts[i] > 0:
                seasonal[i] /= counts[i]
        
        overall_mean = sum(seasonal) / len(seasonal)
        seasonal = [s - overall_mean for s in seasonal]
        
        return seasonal
    
    def _calculate_error_variance(
        self, 
        values: List[float], 
        level: float, 
        trend: float, 
        seasonal: Optional[List[float]]
    ) -> float:
        """Calculate error variance for confidence intervals"""
        if len(values) < 2:
            return 0
        
        errors = []
        current_level = values[0]
        current_trend = (values[1] - values[0]) if len(values) > 1 else 0
        
        for i in range(1, len(values)):
            # Predicted value
            seasonal_component = seasonal[i % len(seasonal)] if seasonal else 0
            predicted = current_level + current_trend + seasonal_component
            
            # Error
            error = values[i] - predicted
            errors.append(error ** 2)
            
            # Update for next iteration
            prev_level = current_level
            current_level = self.alpha * values[i] + (1 - self.alpha) * (current_level + current_trend)
            current_trend = self.beta * (current_level - prev_level) + (1 - self.beta) * current_trend
        
        return statistics.mean(errors) if errors else 0
    
    def _simple_exponential_forecast(
        self, 
        values: List[float], 
        dates: List[str], 
        forecast_horizon: int
    ) -> List[ForecastPoint]:
        """Simple exponential smoothing for insufficient data"""
        if not values:
            return []
        
        # Simple exponential smoothing
        smoothed_value = values[0]
        for value in values[1:]:
            smoothed_value = self.alpha * value + (1 - self.alpha) * smoothed_value
        
        forecasts = []
        for i in range(forecast_horizon):
            last_date = datetime.fromisoformat(dates[-1])
            forecast_date = (last_date + timedelta(days=i+1)).isoformat()[:10]
            
            forecasts.append(ForecastPoint(
                date=forecast_date,
                predicted_cost=max(0, smoothed_value),
                confidence_interval=(smoothed_value * 0.8, smoothed_value * 1.2),
                method_used=ForecastMethod.EXPONENTIAL_SMOOTHING,
                confidence_score=0.4,
                key_drivers=["exponential_smoothing"]
            ))
        
        return forecasts


class ForecastingEngine:
    """Main forecasting engine with ensemble methods"""
    
    def __init__(self, use_ai: bool = True):
        """
        Initialize forecasting engine
        
        Args:
            use_ai: Whether to use AI-powered forecasting
        """
        self.arima_forecaster = ARIMAForecaster()
        self.prophet_forecaster = ProphetLikeForecaster()
        self.exponential_forecaster = ExponentialSmoothingForecaster()
        self.trend_analyzer = TrendAnalyzer()
        self.use_ai = use_ai
        
        if use_ai:
            try:
                self.bedrock_service = BedrockService()
            except Exception as e:
                logger.warning(f"AI service unavailable for forecasting: {e}")
                self.use_ai = False
    
    def generate_forecast(
        self, 
        cost_records: List[UnifiedCostRecord],
        forecast_horizon: int = 30,
        methods: Optional[List[ForecastMethod]] = None
    ) -> ForecastResult:
        """
        Generate comprehensive cost forecast using multiple methods
        
        Args:
            cost_records: Historical cost records
            forecast_horizon: Number of days to forecast
            methods: Specific methods to use (None for all)
            
        Returns:
            Complete forecast result
        """
        try:
            if len(cost_records) < 7:
                return self._get_minimal_forecast(cost_records, forecast_horizon)
            
            # Prepare data
            dates = [record.date for record in cost_records]
            values = [record.total_cost for record in cost_records]
            
            # Generate forecasts using different methods
            forecasts = {}
            
            if not methods or ForecastMethod.ARIMA in methods:
                forecasts['arima'] = self.arima_forecaster.forecast(values, forecast_horizon, dates)
            
            if not methods or ForecastMethod.PROPHET in methods:
                forecasts['prophet'] = self.prophet_forecaster.forecast(values, dates, forecast_horizon)
            
            if not methods or ForecastMethod.EXPONENTIAL_SMOOTHING in methods:
                forecasts['exponential'] = self.exponential_forecaster.forecast(values, dates, forecast_horizon)
            
            # AI-powered forecast (if available)
            if self.use_ai and (not methods or ForecastMethod.ENSEMBLE in methods):
                ai_forecast = self._generate_ai_forecast(cost_records, forecast_horizon)
                if ai_forecast:
                    forecasts['ai'] = ai_forecast
            
            # Create ensemble forecast
            ensemble_forecast = self._create_ensemble_forecast(forecasts)
            
            # Calculate model performance
            model_performance = self._evaluate_model_performance(forecasts, values[-30:] if len(values) >= 30 else values)
            
            # Generate assumptions and methodology
            assumptions = self._generate_assumptions(cost_records)
            methodology = self._generate_methodology(forecasts.keys())
            
            # Assess accuracy
            accuracy = self._assess_forecast_accuracy(len(cost_records), model_performance)
            
            # Calculate total forecast
            total_forecast = self._calculate_total_forecast(ensemble_forecast)
            
            return ForecastResult(
                forecast_period=f"{forecast_horizon} days",
                predictions=ensemble_forecast,
                total_forecast=total_forecast,
                model_performance=model_performance,
                assumptions=assumptions,
                methodology=methodology,
                accuracy_assessment=accuracy,
                metadata={
                    'forecast_generated': datetime.utcnow().isoformat(),
                    'data_points_used': len(cost_records),
                    'methods_used': list(forecasts.keys()),
                    'forecast_horizon': forecast_horizon
                }
            )
            
        except Exception as e:
            logger.error(f"Forecasting failed: {e}")
            return self._get_minimal_forecast(cost_records, forecast_horizon)
    
    def _generate_ai_forecast(
        self, 
        cost_records: List[UnifiedCostRecord], 
        forecast_horizon: int
    ) -> Optional[List[ForecastPoint]]:
        """Generate AI-powered forecast using Bedrock"""
        try:
            # Prepare data for AI
            historical_data = [
                {
                    'date': record.date,
                    'total_cost': record.total_cost,
                    'services': {k: v.cost for k, v in record.services.items()}
                }
                for record in cost_records[-60:]  # Last 60 days
            ]
            
            # Analyze trends
            trend_analysis = self.trend_analyzer.analyze_trends(cost_records)
            
            # Generate AI forecast
            ai_result = self.bedrock_service.generate_forecast_with_ai(
                historical_data, trend_analysis.__dict__, forecast_horizon
            )
            
            # Convert AI result to ForecastPoint objects
            forecasts = []
            for prediction in ai_result.get('predictions', []):
                forecasts.append(ForecastPoint(
                    date=prediction['date'],
                    predicted_cost=prediction['predicted_cost'],
                    confidence_interval=(
                        prediction['confidence_interval']['lower'],
                        prediction['confidence_interval']['upper']
                    ),
                    method_used=ForecastMethod.ENSEMBLE,
                    confidence_score=ai_result.get('total_forecast', {}).get('confidence', 0.5),
                    key_drivers=prediction.get('key_drivers', ['ai_analysis'])
                ))
            
            return forecasts
            
        except Exception as e:
            logger.error(f"AI forecasting failed: {e}")
            return None
    
    def _create_ensemble_forecast(self, forecasts: Dict[str, List[ForecastPoint]]) -> List[ForecastPoint]:
        """Create ensemble forecast by combining multiple methods"""
        if not forecasts:
            return []
        
        # Get the maximum forecast horizon
        max_horizon = max(len(forecast_list) for forecast_list in forecasts.values())
        
        ensemble_forecast = []
        
        for i in range(max_horizon):
            # Collect predictions for this time step
            predictions = []
            confidence_scores = []
            all_drivers = set()
            
            for method, forecast_list in forecasts.items():
                if i < len(forecast_list):
                    predictions.append(forecast_list[i].predicted_cost)
                    confidence_scores.append(forecast_list[i].confidence_score)
                    all_drivers.update(forecast_list[i].key_drivers)
            
            if not predictions:
                continue
            
            # Calculate weighted average (weight by confidence)
            if sum(confidence_scores) > 0:
                weights = [score / sum(confidence_scores) for score in confidence_scores]
                ensemble_prediction = sum(pred * weight for pred, weight in zip(predictions, weights))
            else:
                ensemble_prediction = statistics.mean(predictions)
            
            # Calculate ensemble confidence interval
            prediction_std = statistics.stdev(predictions) if len(predictions) > 1 else 0
            ensemble_confidence = statistics.mean(confidence_scores) if confidence_scores else 0.5
            
            confidence_interval = (
                ensemble_prediction - 1.96 * prediction_std,
                ensemble_prediction + 1.96 * prediction_std
            )
            
            # Use date from first available forecast
            forecast_date = None
            for forecast_list in forecasts.values():
                if i < len(forecast_list):
                    forecast_date = forecast_list[i].date
                    break
            
            if forecast_date:
                ensemble_forecast.append(ForecastPoint(
                    date=forecast_date,
                    predicted_cost=max(0, ensemble_prediction),
                    confidence_interval=confidence_interval,
                    method_used=ForecastMethod.ENSEMBLE,
                    confidence_score=ensemble_confidence,
                    key_drivers=list(all_drivers)
                ))
        
        return ensemble_forecast
    
    def _evaluate_model_performance(
        self, 
        forecasts: Dict[str, List[ForecastPoint]], 
        recent_values: List[float]
    ) -> Dict[str, float]:
        """Evaluate model performance using recent data"""
        performance = {}
        
        if len(recent_values) < 7:
            return {'insufficient_data': 1.0}
        
        # Simple performance evaluation
        for method, forecast_list in forecasts.items():
            if not forecast_list:
                continue
            
            # Calculate mean absolute percentage error (MAPE) approximation
            recent_mean = statistics.mean(recent_values)
            forecast_mean = statistics.mean([fp.predicted_cost for fp in forecast_list[:7]])
            
            if recent_mean > 0:
                mape = abs(forecast_mean - recent_mean) / recent_mean
                performance[method] = max(0, 1 - mape)  # Convert to accuracy score
            else:
                performance[method] = 0.5
        
        return performance
    
    def _generate_assumptions(self, cost_records: List[UnifiedCostRecord]) -> List[str]:
        """Generate forecast assumptions"""
        assumptions = [
            "Historical patterns will continue",
            "No major infrastructure changes",
            "Current usage patterns remain stable"
        ]
        
        # Add data-specific assumptions
        if len(cost_records) < 30:
            assumptions.append("Limited historical data available")
        
        # Check for recent trends
        if len(cost_records) >= 14:
            recent_costs = [record.total_cost for record in cost_records[-14:]]
            older_costs = [record.total_cost for record in cost_records[-28:-14]] if len(cost_records) >= 28 else []
            
            if older_costs:
                recent_mean = statistics.mean(recent_costs)
                older_mean = statistics.mean(older_costs)
                
                if recent_mean > older_mean * 1.1:
                    assumptions.append("Recent upward trend continues")
                elif recent_mean < older_mean * 0.9:
                    assumptions.append("Recent downward trend continues")
        
        return assumptions
    
    def _generate_methodology(self, methods_used: List[str]) -> str:
        """Generate methodology description"""
        method_descriptions = {
            'arima': 'ARIMA time series modeling',
            'prophet': 'Seasonal decomposition with trend analysis',
            'exponential': 'Exponential smoothing',
            'ai': 'AI-powered analysis using large language models'
        }
        
        used_descriptions = [method_descriptions.get(method, method) for method in methods_used]
        
        if len(used_descriptions) > 1:
            return f"Ensemble forecast combining {', '.join(used_descriptions[:-1])} and {used_descriptions[-1]}"
        elif used_descriptions:
            return f"Forecast generated using {used_descriptions[0]}"
        else:
            return "Simple trend-based forecasting"
    
    def _assess_forecast_accuracy(
        self, 
        data_points: int, 
        model_performance: Dict[str, float]
    ) -> ForecastAccuracy:
        """Assess overall forecast accuracy"""
        if data_points < 7:
            return ForecastAccuracy.VERY_LOW
        
        if model_performance:
            avg_performance = statistics.mean(model_performance.values())
            
            if avg_performance > 0.8 and data_points >= 30:
                return ForecastAccuracy.HIGH
            elif avg_performance > 0.6 and data_points >= 14:
                return ForecastAccuracy.MEDIUM
            elif avg_performance > 0.4:
                return ForecastAccuracy.LOW
            else:
                return ForecastAccuracy.VERY_LOW
        
        # Fallback based on data points
        if data_points >= 30:
            return ForecastAccuracy.MEDIUM
        elif data_points >= 14:
            return ForecastAccuracy.LOW
        else:
            return ForecastAccuracy.VERY_LOW
    
    def _calculate_total_forecast(self, predictions: List[ForecastPoint]) -> Dict[str, Any]:
        """Calculate total forecast summary"""
        if not predictions:
            return {'amount': 0, 'confidence': 0.0}
        
        total_amount = sum(fp.predicted_cost for fp in predictions)
        avg_confidence = statistics.mean([fp.confidence_score for fp in predictions])
        
        # Calculate variance range
        min_total = sum(fp.confidence_interval[0] for fp in predictions)
        max_total = sum(fp.confidence_interval[1] for fp in predictions)
        
        return {
            'amount': total_amount,
            'confidence': avg_confidence,
            'variance_range': {
                'min': max(0, min_total),
                'max': max_total
            }
        }
    
    def _get_minimal_forecast(
        self, 
        cost_records: List[UnifiedCostRecord], 
        forecast_horizon: int
    ) -> ForecastResult:
        """Generate minimal forecast for insufficient data"""
        if not cost_records:
            return ForecastResult(
                forecast_period=f"{forecast_horizon} days",
                predictions=[],
                total_forecast={'amount': 0, 'confidence': 0.0},
                model_performance={},
                assumptions=["Insufficient historical data"],
                methodology="No forecast possible",
                accuracy_assessment=ForecastAccuracy.VERY_LOW,
                metadata={'insufficient_data': True}
            )
        
        # Simple forecast using last known value
        last_cost = cost_records[-1].total_cost
        last_date = datetime.fromisoformat(cost_records[-1].date)
        
        predictions = []
        for i in range(forecast_horizon):
            forecast_date = (last_date + timedelta(days=i+1)).isoformat()[:10]
            predictions.append(ForecastPoint(
                date=forecast_date,
                predicted_cost=last_cost,
                confidence_interval=(last_cost * 0.8, last_cost * 1.2),
                method_used=ForecastMethod.SEASONAL_NAIVE,
                confidence_score=0.3,
                key_drivers=["last_known_value"]
            ))
        
        return ForecastResult(
            forecast_period=f"{forecast_horizon} days",
            predictions=predictions,
            total_forecast={
                'amount': last_cost * forecast_horizon,
                'confidence': 0.3,
                'variance_range': {
                    'min': last_cost * forecast_horizon * 0.8,
                    'max': last_cost * forecast_horizon * 1.2
                }
            },
            model_performance={'naive': 0.3},
            assumptions=["Using last known cost value", "No trend analysis possible"],
            methodology="Naive forecast using last known value",
            accuracy_assessment=ForecastAccuracy.VERY_LOW,
            metadata={'minimal_data': True, 'data_points': len(cost_records)}
        )