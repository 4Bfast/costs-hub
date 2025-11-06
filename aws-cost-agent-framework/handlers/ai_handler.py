import json
import boto3
from services.aws_cost_service import AWSCostService

def handle_ai_request(event, cors_headers):
    """Handle AI insights endpoints"""
    
    try:
        path = event.get('path', '')
        method = event['httpMethod']
        
        if method == 'GET' and '/ai/insights' in path:
            return get_cost_insights(event, cors_headers)
        
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': f'AI endpoint not found: {method} {path}'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'AI service error: {str(e)}'})
        }

def get_cost_insights(event, cors_headers):
    """Generate AI-powered cost insights"""
    try:
        # Get cost data using simple approach
        import boto3
        ce_client = boto3.client('ce', region_name='us-east-1')
        
        # Get basic cost data
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        
        # Process cost data
        total_cost = 0
        top_services = []
        
        if response.get('ResultsByTime'):
            for group in response['ResultsByTime'][0].get('Groups', []):
                service = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                total_cost += amount
                if amount > 1:  # Only services with significant cost
                    top_services.append({'service': service, 'cost': amount})
        
        # Sort by cost
        top_services.sort(key=lambda x: x['cost'], reverse=True)
        top_services = top_services[:5]  # Top 5
        
        cost_data = {
            'total_cost': total_cost,
            'top_services': [s['service'] for s in top_services],
            'trend': 'stable'
        }
        
        # Generate insights with Bedrock
        insights = generate_ai_insights(cost_data)
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': insights
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to generate insights: {str(e)}'})
        }

def generate_ai_insights(cost_data):
    """Generate insights using AWS Bedrock"""
    
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        prompt_text = f"""Analise custos AWS. Seja DIRETO e ESPECÍFICO.

Dados:
- Custo: ${cost_data.get('total_cost', 0):.2f}
- Top serviços: {cost_data.get('top_services', [])}
- Tendência: {cost_data.get('trend', 'N/A')}

Responda APENAS JSON válido:
{{
  "summary": "1 frase direta sobre situação",
  "top_recommendations": [
    "Ação específica 1 - economia $X/mês",
    "Ação específica 2 - economia $Y/mês",
    "Ação específica 3 - economia $Z/mês"
  ],
  "anomalies": ["Evento específico detectado"],
  "forecast": "Projeção direta próximo mês"
}}

REGRAS:
- Máximo 15 palavras por item
- Valores específicos de economia
- Sem explicações longas
- Foque em ações práticas"""
        
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt_text}]
            })
        )
        
        result = json.loads(response['body'].read())
        ai_response = result['content'][0]['text']
        
        # Parse JSON response from AI
        return json.loads(ai_response)
        
    except Exception as e:
        # Fallback to basic insights
        return {
            "summary": f"Custo atual ${cost_data.get('total_cost', 0):.2f} - análise disponível",
            "top_recommendations": [
                "Reserved Instances EC2 - economia 30%",
                "S3 Intelligent Tiering - economia 25%", 
                "Revisar recursos idle - economia variável"
            ],
            "anomalies": ["IA temporariamente indisponível"],
            "forecast": f"Projeção: ${cost_data.get('total_cost', 0) * 1.1:.2f} próximo mês"
        }
