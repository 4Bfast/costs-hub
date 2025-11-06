"""
AI Analysis Service for Cost Intelligence

Provides AI-powered cost analysis using Amazon Bedrock or OpenAI
for intelligent insights, recommendations, and narrative reporting.
"""

import boto3
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

try:
    from ..models.config_models import ClientConfig
    from ..utils.logging import create_logger as get_logger
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.config_models import ClientConfig
    from utils.logging import create_logger
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class AIAnalysisService:
    """AI-powered cost analysis service using Amazon Bedrock"""
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize AI Analysis Service
        
        Args:
            region: AWS region for Bedrock service
        """
        self.region = region
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"  # Claude 3 Sonnet
        
    def analyze_cost_patterns(self, cost_data: Dict, historical_data: List[Dict]) -> Dict:
        """
        Analyze cost patterns using AI to identify anomalies and trends
        
        Args:
            cost_data: Current period cost data
            historical_data: Historical cost data for pattern analysis
            
        Returns:
            Dict containing AI analysis results
        """
        try:
            # Prepare data for AI analysis
            analysis_prompt = self._build_pattern_analysis_prompt(cost_data, historical_data)
            
            # Call Bedrock API
            response = self._call_bedrock_api(analysis_prompt)
            
            # Parse and structure response
            analysis_result = self._parse_pattern_analysis(response)
            
            logger.info("AI pattern analysis completed successfully")
            return analysis_result
            
        except Exception as e:
            logger.error(f"AI pattern analysis failed: {e}")
            return {
                'error': str(e),
                'anomalies': [],
                'patterns': [],
                'confidence': 0
            }
    
    def generate_cost_insights(self, cost_data: Dict, client_config: ClientConfig) -> Dict:
        """
        Generate intelligent cost insights and recommendations
        
        Args:
            cost_data: Current cost data
            client_config: Client configuration for context
            
        Returns:
            Dict containing insights and recommendations
        """
        try:
            # Build insights prompt
            insights_prompt = self._build_insights_prompt(cost_data, client_config)
            
            # Get AI insights
            response = self._call_bedrock_api(insights_prompt)
            
            # Structure insights
            insights = self._parse_insights_response(response)
            
            logger.info(f"Generated {len(insights.get('recommendations', []))} AI recommendations")
            return insights
            
        except Exception as e:
            logger.error(f"AI insights generation failed: {e}")
            return {
                'error': str(e),
                'insights': [],
                'recommendations': [],
                'executive_summary': 'AI analysis unavailable'
            }
    
    def generate_narrative_summary(self, cost_data: Dict, changes: Dict, client_config: ClientConfig) -> str:
        """
        Generate narrative summary of cost changes using AI
        
        Args:
            cost_data: Current cost data
            changes: Cost changes analysis
            client_config: Client configuration
            
        Returns:
            AI-generated narrative summary
        """
        try:
            # Build narrative prompt
            narrative_prompt = self._build_narrative_prompt(cost_data, changes, client_config)
            
            # Generate narrative
            response = self._call_bedrock_api(narrative_prompt)
            
            # Extract narrative text
            narrative = self._extract_narrative_text(response)
            
            logger.info("AI narrative summary generated successfully")
            return narrative
            
        except Exception as e:
            logger.error(f"AI narrative generation failed: {e}")
            return f"Your {changes.get('period_type', 'monthly')} AWS costs were ${cost_data.get('total_cost', 0):,.2f}, representing a {changes.get('total_percent_change', 0):+.1f}% change from the previous period."
    
    def _build_pattern_analysis_prompt(self, cost_data: Dict, historical_data: List[Dict]) -> str:
        """Build prompt for pattern analysis"""
        prompt = f"""
        You are an expert AWS cost analyst. Analyze the following cost data to identify patterns, anomalies, and trends.
        
        Current Period Data:
        {json.dumps(cost_data, indent=2)}
        
        Historical Data (last 6 months):
        {json.dumps(historical_data[-6:], indent=2)}
        
        Please provide analysis in JSON format with:
        1. "anomalies": List of unusual cost patterns or spikes
        2. "patterns": Identified trends or recurring patterns
        3. "confidence": Confidence level (0-100) in the analysis
        4. "key_findings": Top 3 most important findings
        
        Focus on actionable insights that can help optimize costs.
        """
        return prompt
    
    def _build_insights_prompt(self, cost_data: Dict, client_config: ClientConfig) -> str:
        """Build prompt for generating insights and recommendations"""
        prompt = f"""
        You are an AWS cost optimization expert. Analyze the cost data and provide actionable insights.
        
        Client: {client_config.client_name}
        Industry Context: {getattr(client_config, 'industry', 'General')}
        
        Cost Data:
        {json.dumps(cost_data, indent=2)}
        
        Provide analysis in JSON format with:
        1. "insights": Key cost insights (3-5 items)
        2. "recommendations": Specific optimization recommendations with estimated savings
        3. "risk_factors": Potential cost risks to monitor
        4. "executive_summary": 2-3 sentence summary for executives
        
        Focus on practical, implementable recommendations.
        """
        return prompt
    
    def _build_narrative_prompt(self, cost_data: Dict, changes: Dict, client_config: ClientConfig) -> str:
        """Build prompt for narrative summary generation"""
        prompt = f"""
        You are a financial analyst writing a cost report summary. Create a clear, professional narrative.
        
        Client: {client_config.client_name}
        
        Current Costs: ${cost_data.get('total_cost', 0):,.2f}
        Change: {changes.get('total_percent_change', 0):+.1f}%
        Top Services: {cost_data.get('top_services', [])[:3]}
        
        Write a 2-3 paragraph executive summary that:
        1. Summarizes the overall cost situation
        2. Highlights key changes and drivers
        3. Provides context and next steps
        
        Use professional, business-appropriate language. Be concise but informative.
        """
        return prompt
    
    def _call_bedrock_api(self, prompt: str) -> str:
        """Call Amazon Bedrock API with the given prompt"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Bedrock API call failed: {e}")
            raise
    
    def _parse_pattern_analysis(self, response: str) -> Dict:
        """Parse pattern analysis response from AI"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback parsing
                return {
                    'anomalies': [],
                    'patterns': [response[:200] + "..."],
                    'confidence': 50,
                    'key_findings': ["Analysis completed"]
                }
        except Exception as e:
            logger.error(f"Failed to parse pattern analysis: {e}")
            return {
                'anomalies': [],
                'patterns': [],
                'confidence': 0,
                'key_findings': []
            }
    
    def _parse_insights_response(self, response: str) -> Dict:
        """Parse insights response from AI"""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    'insights': [response[:300] + "..."],
                    'recommendations': [],
                    'risk_factors': [],
                    'executive_summary': response[:200] + "..."
                }
        except Exception as e:
            logger.error(f"Failed to parse insights: {e}")
            return {
                'insights': [],
                'recommendations': [],
                'risk_factors': [],
                'executive_summary': 'AI analysis unavailable'
            }
    
    def _extract_narrative_text(self, response: str) -> str:
        """Extract narrative text from AI response"""
        try:
            # Clean up the response
            narrative = response.strip()
            
            # Remove any JSON formatting if present
            if narrative.startswith('{'):
                import re
                text_match = re.search(r'"text":\s*"([^"]*)"', narrative)
                if text_match:
                    narrative = text_match.group(1)
            
            return narrative
            
        except Exception as e:
            logger.error(f"Failed to extract narrative: {e}")
            return response[:500] + "..." if len(response) > 500 else response