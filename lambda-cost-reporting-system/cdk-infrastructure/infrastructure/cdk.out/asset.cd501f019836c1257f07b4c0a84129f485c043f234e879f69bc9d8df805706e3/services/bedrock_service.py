"""
AWS Bedrock Service for LLM Integration

Provides comprehensive AWS Bedrock integration for cost analysis insights,
including model configuration, prompt engineering, and response validation.

This service implements the AI insights requirements from the multi-cloud cost analytics
specification, providing intelligent analysis through AWS Bedrock LLM models.
"""

import boto3
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from botocore.exceptions import ClientError, BotoCoreError

try:
    from ..models.config_models import ClientConfig
    from ..models.multi_cloud_models import UnifiedCostRecord
    from ..utils.logging import create_logger as get_logger
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.config_models import ClientConfig
    from models.multi_cloud_models import UnifiedCostRecord
    from utils.logging import create_logger
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class ModelType(Enum):
    """Supported Bedrock model types with their capabilities"""
    CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
    CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
    CLAUDE_3_OPUS = "anthropic.claude-3-opus-20240229-v1:0"
    CLAUDE_3_5_SONNET = "anthropic.claude-3-5-sonnet-20241022-v2:0"


class AnalysisType(Enum):
    """Types of AI analysis supported"""
    COST_ANALYSIS = "cost_analysis"
    ANOMALY_DETECTION = "anomaly_detection"
    FORECASTING = "forecasting"
    RECOMMENDATIONS = "recommendations"
    EXECUTIVE_SUMMARY = "executive_summary"


@dataclass
class BedrockConfig:
    """Enhanced configuration for Bedrock service"""
    region: str = "us-east-1"
    model_id: str = ModelType.CLAUDE_3_SONNET.value
    max_tokens: int = 2000
    temperature: float = 0.1
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_streaming: bool = False
    enable_guardrails: bool = True
    guardrail_id: Optional[str] = None
    guardrail_version: Optional[str] = None


@dataclass
class LLMResponse:
    """Structured LLM response with enhanced metadata"""
    content: str
    model_id: str
    tokens_used: int
    processing_time: float
    confidence_score: float
    metadata: Dict[str, Any]
    analysis_type: AnalysisType
    request_id: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage"""
        return {
            'content': self.content,
            'model_id': self.model_id,
            'tokens_used': self.tokens_used,
            'processing_time': self.processing_time,
            'confidence_score': self.confidence_score,
            'metadata': self.metadata,
            'analysis_type': self.analysis_type.value,
            'request_id': self.request_id,
            'timestamp': self.timestamp.isoformat()
        }


class PromptTemplate:
    """Prompt engineering templates for cost analysis"""
    
    COST_ANALYSIS_TEMPLATE = """
You are an expert cloud cost analyst with deep knowledge of AWS, GCP, and Azure services. 
Analyze the following cost data and provide actionable insights.

Context:
- Client: {client_name}
- Analysis Period: {period}
- Total Cost: ${total_cost:,.2f}
- Primary Cloud Provider: {primary_provider}

Cost Data:
{cost_data}

Historical Context:
{historical_context}

Please provide analysis in the following JSON format:
{{
    "executive_summary": "2-3 sentence summary of key findings",
    "key_insights": [
        {{
            "category": "cost_trend|anomaly|optimization",
            "title": "Brief insight title",
            "description": "Detailed explanation",
            "impact": "high|medium|low",
            "confidence": 0.0-1.0
        }}
    ],
    "anomalies": [
        {{
            "service": "service name",
            "description": "What's unusual",
            "cost_impact": dollar_amount,
            "severity": "critical|high|medium|low",
            "recommended_action": "specific action to take"
        }}
    ],
    "recommendations": [
        {{
            "title": "Recommendation title",
            "description": "Detailed recommendation",
            "estimated_savings": dollar_amount,
            "implementation_effort": "low|medium|high",
            "priority": "high|medium|low"
        }}
    ],
    "trends": [
        {{
            "metric": "total_cost|service_cost|usage",
            "direction": "increasing|decreasing|stable",
            "rate": percentage_change,
            "significance": "high|medium|low"
        }}
    ]
}}

Focus on actionable insights that can drive cost optimization decisions.
"""

    ANOMALY_DETECTION_TEMPLATE = """
You are a specialized anomaly detection system for cloud costs. Analyze the cost data for unusual patterns.

Current Period Data:
{current_data}

Historical Baseline (30-day average):
{baseline_data}

Statistical Context:
- Standard Deviation: ${std_deviation:,.2f}
- Mean Cost: ${mean_cost:,.2f}
- Coefficient of Variation: {cv:.2f}

Identify anomalies using these criteria:
1. Cost spikes > 2 standard deviations from mean
2. New services with significant spend
3. Unusual usage patterns
4. Service cost changes > 50%

Return JSON format:
{{
    "anomalies_detected": [
        {{
            "type": "cost_spike|new_service|usage_anomaly|service_change",
            "service": "service name",
            "current_cost": dollar_amount,
            "expected_cost": dollar_amount,
            "deviation_score": 0.0-10.0,
            "confidence": 0.0-1.0,
            "description": "detailed explanation",
            "potential_causes": ["cause1", "cause2"],
            "urgency": "immediate|high|medium|low"
        }}
    ],
    "overall_risk_score": 0.0-10.0,
    "summary": "Brief summary of anomaly analysis"
}}
"""

    FORECASTING_TEMPLATE = """
You are a cloud cost forecasting expert. Analyze historical trends to predict future costs.

Historical Data (last 90 days):
{historical_data}

Current Trends:
{trend_analysis}

Seasonal Patterns:
{seasonal_patterns}

External Factors:
{external_factors}

Generate a forecast in JSON format:
{{
    "forecast_period": "{forecast_days} days",
    "predictions": [
        {{
            "date": "YYYY-MM-DD",
            "predicted_cost": dollar_amount,
            "confidence_interval": {{
                "lower": dollar_amount,
                "upper": dollar_amount
            }},
            "key_drivers": ["driver1", "driver2"]
        }}
    ],
    "total_forecast": {{
        "amount": dollar_amount,
        "confidence": 0.0-1.0,
        "variance_range": {{
            "min": dollar_amount,
            "max": dollar_amount
        }}
    }},
    "assumptions": ["assumption1", "assumption2"],
    "risk_factors": ["risk1", "risk2"],
    "methodology": "Brief explanation of forecasting approach"
}}
"""


class BedrockService:
    """Enhanced AWS Bedrock service for cost analytics with robust error handling"""
    
    def __init__(self, config: BedrockConfig = None):
        """
        Initialize Bedrock service with enhanced configuration
        
        Args:
            config: Bedrock configuration
        """
        self.config = config or BedrockConfig()
        self.prompt_templates = PromptTemplate()
        self._client = None
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize Bedrock client with error handling"""
        try:
            self._client = boto3.client(
                'bedrock-runtime', 
                region_name=self.config.region
            )
            # Test client connectivity
            self._validate_client_access()
            logger.info(f"Bedrock client initialized successfully in region {self.config.region}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            self._client = None
            raise
    
    def _validate_client_access(self):
        """Validate that the client has access to Bedrock"""
        try:
            # Try to list foundation models to validate access
            bedrock_client = boto3.client('bedrock', region_name=self.config.region)
            bedrock_client.list_foundation_models(byProvider='anthropic')
            logger.debug("Bedrock access validated successfully")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'AccessDeniedException':
                logger.error("Access denied to Bedrock. Check IAM permissions.")
            elif error_code == 'UnauthorizedOperation':
                logger.error("Unauthorized operation. Check Bedrock service availability in region.")
            else:
                logger.error(f"Bedrock validation failed: {error_code}")
            raise
        except Exception as e:
            logger.warning(f"Could not validate Bedrock access: {e}")
    
    @property
    def bedrock_client(self):
        """Get Bedrock client with lazy initialization"""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def is_available(self) -> bool:
        """Check if Bedrock service is available"""
        try:
            return self._client is not None
        except:
            return False
        
    def analyze_costs_with_ai(
        self, 
        cost_data: Dict[str, Any],
        historical_data: List[Dict],
        client_config: ClientConfig
    ) -> Dict[str, Any]:
        """
        Comprehensive AI cost analysis
        
        Args:
            cost_data: Current period cost data
            historical_data: Historical cost data for context
            client_config: Client configuration
            
        Returns:
            Structured AI analysis results
        """
        try:
            # Prepare context data
            context = self._prepare_analysis_context(cost_data, historical_data, client_config)
            
            # Generate prompt
            prompt = self.prompt_templates.COST_ANALYSIS_TEMPLATE.format(**context)
            
            # Call Bedrock
            response = self._invoke_model(prompt, AnalysisType.COST_ANALYSIS)
            
            # Parse and validate response
            analysis = self._parse_json_response(response.content)
            
            # Add metadata
            analysis['metadata'] = {
                'model_used': response.model_id,
                'tokens_used': response.tokens_used,
                'processing_time': response.processing_time,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'confidence_score': response.confidence_score
            }
            
            logger.info(f"AI cost analysis completed for client {client_config.client_name}")
            return analysis
            
        except Exception as e:
            logger.error(f"AI cost analysis failed: {e}")
            return self._get_fallback_analysis(cost_data)
    
    def detect_anomalies_with_ai(
        self,
        current_data: Dict[str, Any],
        baseline_data: Dict[str, Any],
        statistical_context: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        AI-powered anomaly detection
        
        Args:
            current_data: Current period data
            baseline_data: Historical baseline data
            statistical_context: Statistical metrics
            
        Returns:
            Anomaly detection results
        """
        try:
            # Prepare anomaly detection context
            context = {
                'current_data': json.dumps(current_data, indent=2),
                'baseline_data': json.dumps(baseline_data, indent=2),
                **statistical_context
            }
            
            # Generate prompt
            prompt = self.prompt_templates.ANOMALY_DETECTION_TEMPLATE.format(**context)
            
            # Call Bedrock
            response = self._invoke_model(prompt, AnalysisType.ANOMALY_DETECTION)
            
            # Parse response
            anomalies = self._parse_json_response(response.content)
            
            # Add metadata
            anomalies['metadata'] = {
                'detection_timestamp': datetime.utcnow().isoformat(),
                'model_confidence': response.confidence_score,
                'processing_time': response.processing_time
            }
            
            logger.info(f"Detected {len(anomalies.get('anomalies_detected', []))} anomalies")
            return anomalies
            
        except Exception as e:
            logger.error(f"AI anomaly detection failed: {e}")
            return {
                'anomalies_detected': [],
                'overall_risk_score': 0.0,
                'summary': 'Anomaly detection unavailable',
                'error': str(e)
            }
    
    def generate_forecast_with_ai(
        self,
        historical_data: List[Dict],
        trend_analysis: Dict[str, Any],
        forecast_days: int = 30
    ) -> Dict[str, Any]:
        """
        AI-powered cost forecasting
        
        Args:
            historical_data: Historical cost data
            trend_analysis: Trend analysis results
            forecast_days: Number of days to forecast
            
        Returns:
            Forecast results
        """
        try:
            # Prepare forecasting context
            context = {
                'historical_data': json.dumps(historical_data[-30:], indent=2),
                'trend_analysis': json.dumps(trend_analysis, indent=2),
                'seasonal_patterns': json.dumps(self._extract_seasonal_patterns(historical_data), indent=2),
                'external_factors': json.dumps(self._get_external_factors(), indent=2),
                'forecast_days': forecast_days
            }
            
            # Generate prompt
            prompt = self.prompt_templates.FORECASTING_TEMPLATE.format(**context)
            
            # Call Bedrock
            response = self._invoke_model(prompt, AnalysisType.FORECASTING)
            
            # Parse response
            forecast = self._parse_json_response(response.content)
            
            # Add metadata
            forecast['metadata'] = {
                'forecast_generated': datetime.utcnow().isoformat(),
                'model_confidence': response.confidence_score,
                'data_points_used': len(historical_data),
                'forecast_horizon': forecast_days
            }
            
            logger.info(f"Generated {forecast_days}-day cost forecast")
            return forecast
            
        except Exception as e:
            logger.error(f"AI forecasting failed: {e}")
            return {
                'forecast_period': f"{forecast_days} days",
                'predictions': [],
                'total_forecast': {'amount': 0, 'confidence': 0.0},
                'error': str(e)
            }
    
    def _invoke_model(
        self, 
        prompt: str, 
        analysis_type: AnalysisType = AnalysisType.COST_ANALYSIS
    ) -> LLMResponse:
        """
        Invoke Bedrock model with enhanced error handling and retry logic
        
        Args:
            prompt: Input prompt
            analysis_type: Type of analysis being performed
            
        Returns:
            LLM response object
        """
        if not self.is_available():
            raise RuntimeError("Bedrock service is not available")
        
        start_time = datetime.utcnow()
        request_id = f"bedrock-{int(time.time())}-{hash(prompt[:100]) % 10000}"
        
        # Validate prompt length
        if len(prompt) > 100000:  # Reasonable limit
            logger.warning(f"Prompt length ({len(prompt)}) exceeds recommended limit")
            prompt = prompt[:100000] + "... [truncated]"
        
        for attempt in range(self.config.retry_attempts):
            try:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                
                # Add guardrails if configured
                invoke_params = {
                    'modelId': self.config.model_id,
                    'body': json.dumps(body)
                }
                
                if self.config.enable_guardrails and self.config.guardrail_id:
                    invoke_params['guardrailIdentifier'] = self.config.guardrail_id
                    if self.config.guardrail_version:
                        invoke_params['guardrailVersion'] = self.config.guardrail_version
                
                logger.debug(f"Invoking Bedrock model {self.config.model_id} (attempt {attempt + 1})")
                
                response = self.bedrock_client.invoke_model(**invoke_params)
                
                response_body = json.loads(response['body'].read())
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Validate response structure
                if 'content' not in response_body or not response_body['content']:
                    raise ValueError("Invalid response structure from Bedrock")
                
                content = response_body['content'][0]['text']
                if not content.strip():
                    raise ValueError("Empty response from Bedrock")
                
                tokens_used = response_body.get('usage', {}).get('output_tokens', 0)
                
                logger.info(f"Bedrock invocation successful: {tokens_used} tokens, {processing_time:.2f}s")
                
                return LLMResponse(
                    content=content,
                    model_id=self.config.model_id,
                    tokens_used=tokens_used,
                    processing_time=processing_time,
                    confidence_score=self._calculate_confidence_score(response_body),
                    metadata={
                        **response_body.get('metadata', {}),
                        'attempt': attempt + 1,
                        'prompt_length': len(prompt)
                    },
                    analysis_type=analysis_type,
                    request_id=request_id,
                    timestamp=datetime.utcnow()
                )
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                
                logger.warning(f"Bedrock ClientError (attempt {attempt + 1}): {error_code} - {error_message}")
                
                # Handle specific error types
                if error_code == 'ThrottlingException':
                    if attempt < self.config.retry_attempts - 1:
                        wait_time = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.info(f"Throttling detected, waiting {wait_time}s before retry")
                        time.sleep(wait_time)
                        continue
                elif error_code == 'ValidationException':
                    logger.error(f"Validation error: {error_message}")
                    raise ValueError(f"Invalid request to Bedrock: {error_message}")
                elif error_code == 'AccessDeniedException':
                    logger.error("Access denied to Bedrock model")
                    raise PermissionError("Access denied to Bedrock model")
                elif error_code == 'ModelNotReadyException':
                    if attempt < self.config.retry_attempts - 1:
                        wait_time = self.config.retry_delay * 2
                        logger.info(f"Model not ready, waiting {wait_time}s before retry")
                        time.sleep(wait_time)
                        continue
                
                if attempt == self.config.retry_attempts - 1:
                    raise
                    
            except BotoCoreError as e:
                logger.warning(f"BotoCore error (attempt {attempt + 1}): {e}")
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay)
                    continue
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error during Bedrock invocation (attempt {attempt + 1}): {e}")
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay)
                    continue
                raise
        
        raise RuntimeError(f"Failed to invoke Bedrock model after {self.config.retry_attempts} attempts")
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM with fallback handling
        
        Args:
            response_text: Raw response text
            
        Returns:
            Parsed JSON data
        """
        try:
            # Try direct JSON parsing
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try to find JSON object in text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # Fallback: return structured error
            logger.warning("Could not parse JSON from LLM response")
            return {
                'error': 'Failed to parse JSON response',
                'raw_response': response_text[:500] + "..." if len(response_text) > 500 else response_text
            }
    
    def _prepare_analysis_context(
        self, 
        cost_data: Dict[str, Any], 
        historical_data: List[Dict],
        client_config: ClientConfig
    ) -> Dict[str, Any]:
        """Prepare context data for analysis prompt"""
        return {
            'client_name': client_config.client_name,
            'period': cost_data.get('period', 'current'),
            'total_cost': cost_data.get('total_cost', 0),
            'primary_provider': cost_data.get('primary_provider', 'AWS'),
            'cost_data': json.dumps(cost_data, indent=2),
            'historical_context': json.dumps(historical_data[-6:], indent=2) if historical_data else '{}'
        }
    
    def _extract_seasonal_patterns(self, historical_data: List[Dict]) -> Dict[str, Any]:
        """Extract seasonal patterns from historical data"""
        # Simple seasonal pattern extraction
        if not historical_data:
            return {}
        
        monthly_costs = {}
        for record in historical_data:
            month = record.get('date', '')[:7]  # YYYY-MM
            cost = record.get('total_cost', 0)
            if month not in monthly_costs:
                monthly_costs[month] = []
            monthly_costs[month].append(cost)
        
        return {
            'monthly_averages': {
                month: sum(costs) / len(costs) 
                for month, costs in monthly_costs.items()
            },
            'pattern_detected': len(monthly_costs) >= 3
        }
    
    def _get_external_factors(self) -> Dict[str, Any]:
        """Get external factors that might affect costs"""
        return {
            'current_month': datetime.utcnow().strftime('%B'),
            'quarter': f"Q{(datetime.utcnow().month - 1) // 3 + 1}",
            'business_factors': ['end_of_quarter', 'holiday_season', 'fiscal_year_end']
        }
    
    def _calculate_confidence_score(self, response_body: Dict) -> float:
        """Calculate confidence score for the response"""
        # Simple confidence calculation based on response completeness
        usage = response_body.get('usage', {})
        output_tokens = usage.get('output_tokens', 0)
        
        if output_tokens > 1000:
            return 0.9
        elif output_tokens > 500:
            return 0.7
        elif output_tokens > 100:
            return 0.5
        else:
            return 0.3
    
    def generate_executive_summary(
        self,
        cost_data: Dict[str, Any],
        insights: Dict[str, Any],
        client_config: ClientConfig
    ) -> str:
        """
        Generate executive summary using AI
        
        Args:
            cost_data: Cost data summary
            insights: Analysis insights
            client_config: Client configuration
            
        Returns:
            Executive summary text
        """
        try:
            context = {
                'client_name': client_config.client_name,
                'total_cost': cost_data.get('total_cost', 0),
                'period': cost_data.get('period', 'current'),
                'key_insights': json.dumps(insights.get('key_insights', []), indent=2),
                'anomalies_count': len(insights.get('anomalies', [])),
                'recommendations_count': len(insights.get('recommendations', []))
            }
            
            prompt = f"""
Generate a concise executive summary for {context['client_name']}'s cloud cost analysis.

Key Information:
- Total Cost: ${context['total_cost']:,.2f}
- Analysis Period: {context['period']}
- Anomalies Detected: {context['anomalies_count']}
- Recommendations Available: {context['recommendations_count']}

Key Insights:
{context['key_insights']}

Provide a 2-3 sentence executive summary that highlights the most important findings and actionable insights for leadership.
Focus on business impact and financial implications.
"""
            
            response = self._invoke_model(prompt, AnalysisType.EXECUTIVE_SUMMARY)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")
            return f"Cost analysis completed for {client_config.client_name} with total spend of ${cost_data.get('total_cost', 0):,.2f}. {len(insights.get('anomalies', []))} anomalies detected with {len(insights.get('recommendations', []))} optimization recommendations available."
    
    def validate_analysis_results(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize analysis results
        
        Args:
            analysis: Raw analysis results
            
        Returns:
            Validated and sanitized results
        """
        validated = {}
        
        # Validate executive summary
        if 'executive_summary' in analysis:
            summary = analysis['executive_summary']
            if isinstance(summary, str) and len(summary.strip()) > 0:
                validated['executive_summary'] = summary.strip()[:1000]  # Limit length
            else:
                validated['executive_summary'] = "Analysis completed successfully."
        
        # Validate key insights
        if 'key_insights' in analysis:
            insights = analysis['key_insights']
            if isinstance(insights, list):
                validated['key_insights'] = [
                    str(insight)[:500] for insight in insights[:10]  # Limit count and length
                    if isinstance(insight, (str, dict))
                ]
            else:
                validated['key_insights'] = []
        
        # Validate anomalies
        if 'anomalies' in analysis:
            anomalies = analysis['anomalies']
            if isinstance(anomalies, list):
                validated_anomalies = []
                for anomaly in anomalies[:20]:  # Limit count
                    if isinstance(anomaly, dict):
                        validated_anomaly = {
                            'service': str(anomaly.get('service', 'Unknown'))[:100],
                            'description': str(anomaly.get('description', ''))[:500],
                            'severity': anomaly.get('severity', 'medium'),
                            'cost_impact': float(anomaly.get('cost_impact', 0)) if isinstance(anomaly.get('cost_impact'), (int, float)) else 0.0
                        }
                        validated_anomalies.append(validated_anomaly)
                validated['anomalies'] = validated_anomalies
            else:
                validated['anomalies'] = []
        
        # Validate recommendations
        if 'recommendations' in analysis:
            recommendations = analysis['recommendations']
            if isinstance(recommendations, list):
                validated_recommendations = []
                for rec in recommendations[:15]:  # Limit count
                    if isinstance(rec, dict):
                        validated_rec = {
                            'title': str(rec.get('title', 'Optimization Opportunity'))[:200],
                            'description': str(rec.get('description', ''))[:1000],
                            'estimated_savings': float(rec.get('estimated_savings', 0)) if isinstance(rec.get('estimated_savings'), (int, float)) else 0.0,
                            'priority': rec.get('priority', 'medium'),
                            'implementation_effort': rec.get('implementation_effort', 'medium')
                        }
                        validated_recommendations.append(validated_rec)
                validated['recommendations'] = validated_recommendations
            else:
                validated['recommendations'] = []
        
        # Validate trends
        if 'trends' in analysis:
            trends = analysis['trends']
            if isinstance(trends, list):
                validated_trends = []
                for trend in trends[:10]:  # Limit count
                    if isinstance(trend, dict):
                        validated_trend = {
                            'metric': str(trend.get('metric', 'cost'))[:100],
                            'direction': trend.get('direction', 'stable'),
                            'rate': float(trend.get('rate', 0)) if isinstance(trend.get('rate'), (int, float)) else 0.0,
                            'significance': trend.get('significance', 'low')
                        }
                        validated_trends.append(validated_trend)
                validated['trends'] = validated_trends
            else:
                validated['trends'] = []
        
        return validated
    
    def get_model_capabilities(self) -> Dict[str, Any]:
        """
        Get information about the current model's capabilities
        
        Returns:
            Model capabilities information
        """
        model_info = {
            'model_id': self.config.model_id,
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature,
            'supports_json': True,
            'supports_analysis': True,
            'supports_forecasting': True,
            'region': self.config.region
        }
        
        # Add model-specific capabilities
        if 'claude-3-opus' in self.config.model_id:
            model_info.update({
                'complexity_level': 'high',
                'reasoning_capability': 'advanced',
                'recommended_for': ['complex_analysis', 'detailed_recommendations']
            })
        elif 'claude-3-sonnet' in self.config.model_id:
            model_info.update({
                'complexity_level': 'medium',
                'reasoning_capability': 'good',
                'recommended_for': ['general_analysis', 'cost_insights']
            })
        elif 'claude-3-haiku' in self.config.model_id:
            model_info.update({
                'complexity_level': 'low',
                'reasoning_capability': 'basic',
                'recommended_for': ['quick_summaries', 'simple_analysis']
            })
        
        return model_info
    
    def _get_fallback_analysis(self, cost_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide fallback analysis when AI fails"""
        return {
            'executive_summary': f"Cost analysis for period with total spend of ${cost_data.get('total_cost', 0):,.2f}",
            'key_insights': [
                "AI analysis temporarily unavailable",
                "Basic cost metrics calculated successfully",
                "Manual review recommended for detailed insights"
            ],
            'anomalies': [],
            'recommendations': [
                {
                    'title': 'Enable AI Analysis',
                    'description': 'Configure AWS Bedrock access to enable advanced AI-powered cost insights',
                    'estimated_savings': 0,
                    'priority': 'medium',
                    'implementation_effort': 'low'
                }
            ],
            'trends': [],
            'metadata': {
                'fallback_used': True,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'ai_available': False
            }
        }