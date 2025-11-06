"""
AI Summary Generator using AWS Bedrock for cost analysis insights
"""

import boto3
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AISummaryGenerator:
    """Generate AI-powered cost analysis summaries using AWS Bedrock"""
    
    def __init__(self, aws_profile: str = "4bfast", region: str = "us-east-1"):
        """Initialize Bedrock client with specific profile"""
        self.aws_profile = aws_profile
        self.region = region
        
        # Initialize Bedrock client with specific profile
        session = boto3.Session(profile_name=aws_profile)
        self.bedrock_client = session.client('bedrock-runtime', region_name=region)
        
        # Model configuration
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        
    def generate_cost_summary(self, analysis_data: Dict[str, Any]) -> Optional[str]:
        """Generate AI summary of cost analysis"""
        try:
            # Extract key data for AI analysis
            periods_data = analysis_data.get('periods_data', [])
            changes = analysis_data.get('changes', {})
            top_services = analysis_data.get('top_services', [])
            forecast_analysis = analysis_data.get('forecast_analysis', {})
            metadata = analysis_data.get('metadata', {})
            
            if not periods_data or len(periods_data) < 2:
                return None
            
            # Prepare data for AI prompt
            current_period = periods_data[0]
            previous_period = periods_data[1] if len(periods_data) > 1 else periods_data[0]
            
            current_cost = current_period.get('total_cost', 0)
            previous_cost = previous_period.get('total_cost', 0)
            change_amount = changes.get('total_change', 0)
            change_percent = changes.get('total_percent_change', 0)
            
            # Top 5 services for context
            top_5_services = [
                f"{s['service']}: ${s['cost']:,.2f}" 
                for s in top_services[:5]
            ]
            
            # Main cost changes
            service_changes = changes.get('service_changes', {})
            main_changes = []
            for service, change_data in list(service_changes.items())[:5]:
                change_val = change_data.get('change', 0)
                change_pct = change_data.get('percent_change', 0)
                main_changes.append(f"{service}: {change_val:+,.2f} ({change_pct:+.1f}%)")
            
            # Forecast insights
            forecast_info = ""
            if forecast_analysis and not forecast_analysis.get('error'):
                forecast_summary = forecast_analysis.get('summary', {})
                forecast_increase = forecast_summary.get('forecast_increase_percent', 0)
                top_driver = forecast_summary.get('top_driver', '')
                if forecast_increase != 0:
                    forecast_info = f"\nPrevisão para fim do mês: {forecast_increase:+.1f}% de mudança"
                    if top_driver:
                        forecast_info += f", principal direcionador: {top_driver}"
            
            # Create AI prompt
            prompt = self._create_cost_analysis_prompt(
                current_cost=current_cost,
                previous_cost=previous_cost,
                change_amount=change_amount,
                change_percent=change_percent,
                top_services=top_5_services,
                main_changes=main_changes,
                forecast_info=forecast_info,
                analysis_type=metadata.get('analysis_type', 'monthly')
            )
            
            # Call Bedrock
            response = self._call_bedrock(prompt)
            
            if response:
                logger.info("✅ AI summary generated successfully")
                return response
            else:
                logger.warning("⚠️ Failed to generate AI summary")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error generating AI summary: {str(e)}")
            return None
    
    def _create_cost_analysis_prompt(self, current_cost: float, previous_cost: float,
                                   change_amount: float, change_percent: float,
                                   top_services: list, main_changes: list,
                                   forecast_info: str, analysis_type: str) -> str:
        """Create detailed prompt for cost analysis"""
        
        period_name = {
            'monthly': 'mensal',
            'weekly': 'semanal', 
            'daily': 'diária'
        }.get(analysis_type, 'mensal')
        
        return f"""Você é um especialista FinOps e consultoria financeira para empresas. 

Analise os seguintes dados de custo AWS de uma empresa cliente e crie um resumo executivo em português brasileiro.


DADOS DE CUSTO ({period_name.upper()}):
- Custo atual: ${current_cost:,.2f}
- Custo anterior: ${previous_cost:,.2f}  
- Mudança: ${change_amount:+,.2f} ({change_percent:+.1f}%)

PRINCIPAIS SERVIÇOS AWS:
{chr(10).join(top_services)}

PRINCIPAIS MUDANÇAS:
{chr(10).join(main_changes) if main_changes else 'Nenhuma mudança significativa'}

{forecast_info}

INSTRUÇÕES:
1. Crie um resumo de 2 parágrafos em português brasileiro
2. Explique o cenário atual dos custos de cloud de forma clara e acessível
3. Destaque os principais direcionadores de custo e seu impacto no negócio
4. Forneça insights sobre tendências e recomendações práticas
5. Use linguagem executiva, não técnica demais
6. Foque no valor e ROI dos serviços AWS
7. Se houver aumento significativo (>10%), explique possíveis causas
8. Se houver redução, destaque as otimizações alcançadas
9. Descreva em poucas palavras apenas o que os 3 custos mais altos significam

FORMATO DE RESPOSTA:
- Apenas o texto do resumo, sem títulos ou formatação markdown
- Máximo 250 palavras
- Tom profissional mas acessível
- Foque em insights acionáveis

Resumo:"""
    
    def _call_bedrock(self, prompt: str) -> Optional[str]:
        """Call AWS Bedrock API"""
        try:
            # Prepare request body for Claude
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.3,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json"
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if 'content' in response_body and response_body['content']:
                return response_body['content'][0]['text'].strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Bedrock API error: {str(e)}")
            return None
    
    def generate_service_explanation(self, service_name: str, cost: float, 
                                   change_percent: float) -> Optional[str]:
        """Generate explanation for a specific service cost change"""
        try:
            prompt = f"""Explique de forma simples e em português brasileiro o que é o serviço AWS "{service_name}" e por que pode ter tido uma mudança de custo de {change_percent:+.1f}% (custo atual: ${cost:,.2f}).

Instruções:
1. Explique o serviço em 1-2 frases simples
2. Mencione possíveis razões para a mudança de custo
3. Use linguagem não-técnica
4. Máximo 100 palavras

Explicação:"""
            
            response = self._call_bedrock(prompt)
            return response
            
        except Exception as e:
            logger.error(f"Error generating service explanation: {str(e)}")
            return None
    
    def generate_optimization_recommendations(self, analysis_data: Dict[str, Any]) -> Optional[str]:
        """Generate cost optimization recommendations"""
        try:
            top_services = analysis_data.get('top_services', [])[:5]
            changes = analysis_data.get('changes', {})
            
            services_info = []
            for service in top_services:
                service_name = service['service']
                cost = service['cost']
                
                # Check if service has significant changes
                if service_name in changes.get('service_changes', {}):
                    change_data = changes['service_changes'][service_name]
                    change_percent = change_data.get('percent_change', 0)
                    services_info.append(f"{service_name}: ${cost:,.2f} ({change_percent:+.1f}%)")
                else:
                    services_info.append(f"{service_name}: ${cost:,.2f} (estável)")
            
            prompt = f"""Como especialista em otimização de custos AWS, analise os seguintes serviços e forneça 3-5 recomendações práticas de otimização em português brasileiro:

PRINCIPAIS SERVIÇOS:
{chr(10).join(services_info)}

Forneça recomendações específicas e acionáveis para:
1. Reduzir custos sem impactar performance
2. Otimizar recursos subutilizados  
3. Implementar melhores práticas de custo
4. Aproveitar descontos e reservas

Formato: Lista numerada, máximo 200 palavras, linguagem executiva.

Recomendações:"""
            
            response = self._call_bedrock(prompt)
            return response
            
        except Exception as e:
            logger.error(f"Error generating optimization recommendations: {str(e)}")
            return None
