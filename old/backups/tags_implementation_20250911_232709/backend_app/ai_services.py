# app/ai_services.py

import boto3
import json
import logging
import time
from typing import Dict, Optional
from botocore.exceptions import ClientError

# Configurar logging
logger = logging.getLogger(__name__)

class BedrockService:
    def __init__(self):
        """Inicializa o cliente do AWS Bedrock"""
        try:
            # Em desenvolvimento: usar profile 4bfast
            # Em produção (AWS): usar IAM Role automaticamente
            import os
            
            if os.getenv('AWS_EXECUTION_ENV'):
                # Rodando na AWS (Lambda, ECS, EC2) - usar IAM Role
                self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
            else:
                # Desenvolvimento local - usar profile 4bfast
                session = boto3.Session(profile_name='4bfast')
                self.bedrock_client = session.client('bedrock-runtime', region_name='us-east-1')
            
            self.model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
            logger.info("Cliente Bedrock inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente Bedrock: {e}")
            self.bedrock_client = None

    def generate_dashboard_summary(self, dashboard_data: Dict) -> str:
        """
        Gera resumo executivo dos dados do dashboard usando Claude 3 Sonnet
        
        Args:
            dashboard_data: Dados completos do dashboard em formato dict
            
        Returns:
            str: Resumo executivo gerado pela IA
        """
        # FALLBACK TEMPORÁRIO: Se não conseguir conectar com Bedrock, usar resumo estático
        if not self.bedrock_client:
            return self._generate_fallback_summary(dashboard_data)
        
        try:
            # Construir prompt usando template especificado
            prompt = self._build_prompt(dashboard_data)
            
            # Preparar payload para Claude 3.5
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "top_p": 0.9
            }
            
            # Invocar modelo com retry para throttling
            summary_text = self._invoke_model_with_retry(payload)
            
            logger.info(f"Resumo IA gerado com sucesso. Tamanho: {len(summary_text)} caracteres")
            return summary_text
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ThrottlingException':
                logger.warning(f"Rate limit atingido no Bedrock. Usando fallback.")
                return self._generate_fallback_summary(dashboard_data)
            else:
                logger.error(f"Erro do AWS Bedrock: {e}")
                return self._generate_fallback_summary(dashboard_data)
        except Exception as e:
            logger.error(f"Erro inesperado na geração do resumo: {e}")
            return self._generate_fallback_summary(dashboard_data)

    def _invoke_model_with_retry(self, payload, max_retries=3):
        """
        Invoca o modelo com retry exponencial para lidar com throttling
        """
        for attempt in range(max_retries):
            try:
                response = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(payload),
                    contentType='application/json',
                    accept='application/json'
                )
                
                # Extrair resposta
                response_body = json.loads(response['body'].read())
                return response_body['content'][0]['text'].strip()
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                
                if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                    # Backoff exponencial: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    logger.warning(f"Throttling detectado. Tentativa {attempt + 1}/{max_retries}. Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Re-raise para ser tratado no método principal
                    raise e
        
        # Se chegou aqui, todas as tentativas falharam
        raise Exception("Máximo de tentativas excedido")

    def get_term_explanation(self, term: str, context: str) -> str:
        """
        Gera explicação clara de termos técnicos AWS usando Claude
        
        Args:
            term: Termo técnico (ex: "DataTransfer-Out-Bytes")
            context: Contexto do termo (ex: "UsageType")
            
        Returns:
            str: Explicação em linguagem de negócios
        """
        if not self.bedrock_client:
            return self._generate_fallback_explanation(term, context)
        
        try:
            # Construir prompt para explicação
            prompt = self._build_explanation_prompt(term, context)
            
            # Preparar payload para Claude
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 200,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2,
                "top_p": 0.8
            }
            
            # Invocar modelo com retry
            explanation_text = self._invoke_model_with_retry(payload, max_retries=2)
            
            logger.info(f"Explicação gerada para termo: {term}")
            return explanation_text
            
        except Exception as e:
            logger.error(f"Erro ao gerar explicação para '{term}': {e}")
            return self._generate_fallback_explanation(term, context)

    def _build_explanation_prompt(self, term: str, context: str) -> str:
        """
        Constrói prompt otimizado para explicação de termos
        """
        prompt_template = """Você é o 'Costs-Hub AI', um especialista em FinOps e faturamento da nuvem AWS. Sua missão é traduzir jargões técnicos complexos em explicações claras, concisas e em português do Brasil para gestores de negócios. Use uma analogia se ajudar a clarear o conceito.

Explique o seguinte termo técnico, considerando o contexto fornecido. Responda em no máximo 3 frases.

Termo: "{term}"
Contexto: "{context}"

Responda APENAS com a explicação, sem saudações ou despedidas."""

        return prompt_template.format(term=term, context=context)

    def _generate_fallback_explanation(self, term: str, context: str) -> str:
        """
        Gera explicação básica quando IA não está disponível
        """
        # Dicionário de explicações comuns
        common_explanations = {
            "DataTransfer-Out-Bytes": "Custo de transferência de dados da AWS para a internet. Ocorre quando seus usuários acessam conteúdo ou quando você envia dados para fora da nuvem AWS.",
            "BoxUsage": "Custo básico de execução de instâncias EC2. É como o 'aluguel' que você paga pelo tempo que seus servidores virtuais ficam ligados.",
            "EBS:VolumeUsage": "Custo de armazenamento de discos virtuais (volumes EBS). É como pagar pelo espaço de HD que seus servidores utilizam.",
            "NatGateway-Bytes": "Custo de processamento de dados através do NAT Gateway. Permite que recursos privados acessem a internet de forma segura.",
            "LoadBalancerUsage": "Custo do balanceador de carga que distribui o tráfego entre seus servidores para melhorar performance e disponibilidade."
        }
        
        explanation = common_explanations.get(term)
        if explanation:
            return explanation
        
        # Explicação genérica baseada no padrão do termo
        if "DataTransfer" in term:
            return "Custo relacionado à transferência de dados entre serviços AWS ou para a internet. Varia conforme o volume e destino dos dados."
        elif "Usage" in term:
            return f"Custo de utilização do serviço {term.split(':')[0] if ':' in term else 'AWS'}. Cobrado conforme tempo de uso ou recursos consumidos."
        elif "Storage" in term:
            return "Custo de armazenamento de dados na AWS. Varia conforme o tipo de storage e volume de dados armazenados."
        else:
            return f"Termo técnico AWS relacionado ao contexto {context}. Configure AWS Bedrock para explicações mais detalhadas."

    def generate_trends_analysis(self, trends_data: Dict) -> str:
        """
        Gera análise de tendências com justificativa de variações usando Claude
        
        Args:
            trends_data: Dados de análise de tendências com decomposição
            
        Returns:
            str: Análise executiva de tendências
        """
        if not self.bedrock_client:
            return self._generate_fallback_trends_analysis(trends_data)
        
        try:
            # Construir prompt para análise de tendências
            prompt = self._build_trends_prompt(trends_data)
            
            # Preparar payload para Claude
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 400,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2,
                "top_p": 0.8
            }
            
            # Invocar modelo com retry
            analysis_text = self._invoke_model_with_retry(payload, max_retries=2)
            
            logger.info(f"Análise de tendências gerada com sucesso")
            return analysis_text
            
        except Exception as e:
            logger.error(f"Erro ao gerar análise de tendências: {e}")
            return self._generate_fallback_trends_analysis(trends_data)

    def _build_trends_prompt(self, trends_data: Dict) -> str:
        """
        Constrói prompt otimizado para análise de tendências
        """
        # Converter dados para JSON formatado
        dados_json = json.dumps(trends_data, indent=2, ensure_ascii=False, default=str)
        
        prompt_template = """You are 'Costs-Hub AI', a strategic FinOps forecasting expert. Based on 7-day cost patterns, generate REALISTIC strategic insights proportional to actual spending levels.

### COST DATA (Last 7 days) ###
{dados_json}
### END OF DATA ###

RESPONSE FORMAT (exactly these 2 sections):
Projeção 30 Dias: [Strategic forecast proportional to actual cost levels - if costs are under $50/month, focus on growth opportunities rather than savings]
Ação Estratégica: [Realistic strategic action appropriate for the cost scale - avoid governance overhead for small budgets]

STRATEGIC FOCUS:
- Scale recommendations to actual cost levels (small budgets = growth focus, large budgets = optimization focus)
- For budgets under $50/month: focus on scaling, experimentation, learning
- For budgets $50-500/month: focus on efficiency and smart growth  
- For budgets >$500/month: focus on governance and optimization
- Be realistic about percentages and dollar amounts relative to total spend

GUIDELINES:
- Maximum 1 sentence per section
- Match strategic advice to budget scale
- Use realistic projections based on actual spending levels
- Avoid suggesting governance overhead for small experimental budgets

Respond in Portuguese (Brazil) with ONLY the 2 sections, no introduction or conclusion."""

        return prompt_template.format(dados_json=dados_json)

    def _generate_fallback_trends_analysis(self, trends_data: Dict) -> str:
        """
        Retorna mensagem simples quando IA não está disponível - sem dados fictícios
        """
        return "Projeção 30 Dias: Configure AWS Bedrock para análises preditivas precisas.\nAção Estratégica: Habilite IA para insights estratégicos personalizados."

    def _generate_fallback_summary(self, dashboard_data: Dict) -> str:
        """
        Gera resumo inteligente sem IA quando Bedrock não está disponível
        """
        try:
            service_variation = dashboard_data.get('serviceVariation', [])
            
            if not service_variation:
                return "Dados insuficientes para análise detalhada. Configure mais serviços AWS para insights mais ricos."
            
            # Analisar padrões nos dados
            top_services = service_variation[:3]
            increases = [s for s in top_services if s.get('variationValue', 0) > 0]
            decreases = [s for s in top_services if s.get('variationValue', 0) < 0]
            new_services = [s for s in top_services if s.get('previousCost', 0) == 0 and s.get('currentCost', 0) > 0]
            
            insights = []
            
            # Insight sobre concentração de variação
            if len(top_services) >= 2:
                top_impact = sum(abs(s.get('variationValue', 0)) for s in top_services[:2])
                total_variation = sum(abs(s.get('variationValue', 0)) for s in service_variation)
                if total_variation > 0:
                    concentration = (top_impact / total_variation) * 100
                    if concentration > 70:
                        insights.append(f"Apenas dois serviços ({top_services[0]['service']} e {top_services[1]['service']}) concentram {concentration:.0f}% das mudanças de custo, criando risco de dependência.")
            
            # Insight sobre serviços novos
            if new_services:
                new_cost = sum(s.get('currentCost', 0) for s in new_services)
                insights.append(f"Novos serviços como {new_services[0]['service']} adicionaram ${new_cost:.2f} aos custos, indicando expansão de workloads que requer monitoramento.")
            
            # Insight sobre otimizações
            if decreases:
                biggest_saving = max(decreases, key=lambda x: abs(x.get('variationValue', 0)))
                insights.append(f"A redução em {biggest_saving['service']} (${abs(biggest_saving.get('variationValue', 0)):.2f}) sugere otimização bem-sucedida que pode ser replicada em outros serviços.")
            
            # Insight sobre riscos
            if increases:
                biggest_increase = max(increases, key=lambda x: x.get('variationValue', 0))
                if biggest_increase.get('variationPercentage', 0) > 50:
                    insights.append(f"O crescimento de {biggest_increase.get('variationPercentage', 0):.0f}% em {biggest_increase['service']} pode indicar uso não planejado ou necessidade de rightsizing.")
            
            # Combinar insights ou usar padrão
            if insights:
                summary = " ".join(insights[:2])  # Máximo 2 insights
            else:
                summary = f"O serviço {top_services[0]['service']} lidera as variações de custo, representando uma oportunidade de otimização focada."
            
            return summary + " [Análise local - Configure AWS Bedrock para insights mais avançados]"
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo fallback: {e}")
            return "Sistema de análise temporariamente indisponível. Os dados detalhados estão disponíveis nos gráficos e tabelas abaixo."

    def _build_prompt(self, dashboard_data: Dict) -> str:
        """
        Constrói o prompt usando o template especificado
        
        Args:
            dashboard_data: Dados do dashboard
            
        Returns:
            str: Prompt formatado para o Claude
        """
        # Converter dados para JSON formatado
        dados_json = json.dumps(dashboard_data, indent=2, ensure_ascii=False, default=str)
        
        prompt_template = """You are 'Costs-Hub AI', a FinOps and AWS cloud cost analysis expert. Your audience consists of business managers and CEOs, so use clear, direct language focused on business impact.

Based on the following cost data summary, generate structured executive insights following this format:

### COST DATA ###
{dados_json}
### END OF DATA ###

RESPONSE FORMAT (exactly these 3 sections):
Situação Atual: Main insight about the cost state in the period
Oportunidades: Identification of optimizations or important alerts
Recomendação: Practical and specific action for the next period

GUIDELINES:
- Each section: maximum 2 direct and actionable sentences
- Focus on insights that go BEYOND basic numbers visible on dashboard
- Use dollar values ($X.XX) when relevant
- Avoid repeating KPIs already shown in cards
- Prioritize business impact over technical details
- If there are new services, mention in Oportunidades section

Respond in Portuguese (Brazil) with ONLY the 3 sections using the exact titles above, no introduction or conclusion."""

        return prompt_template.format(dados_json=dados_json)


# Instância global do serviço
bedrock_service = BedrockService()

def generate_dashboard_summary(dashboard_data: Dict) -> str:
    """
    Função de conveniência para gerar resumo do dashboard
    
    Args:
        dashboard_data: Dados completos do dashboard
        
    Returns:
        str: Resumo executivo gerado pela IA
    """
    return bedrock_service.generate_dashboard_summary(dashboard_data)

def get_term_explanation(term: str, context: str) -> str:
    """
    Função de conveniência para obter explicação de termos técnicos
    
    Args:
        term: Termo técnico a ser explicado
        context: Contexto do termo (ex: 'UsageType')
        
    Returns:
        str: Explicação clara do termo
    """
    return bedrock_service.get_term_explanation(term, context)

def generate_trends_analysis(trends_data: Dict) -> str:
    """
    Função de conveniência para gerar análise de tendências
    
    Args:
        trends_data: Dados de análise de tendências
        
    Returns:
        str: Análise de tendências gerada pela IA
    """
    return bedrock_service.generate_trends_analysis(trends_data)
