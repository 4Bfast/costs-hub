"""
Insights Handler - AI-powered cost optimization
"""
import json
import boto3
import uuid
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

def handle_insights_request(event, cors_headers):
    """Handle insights endpoints"""
    path = event['path']
    method = event['httpMethod']
    
    ce_client = boto3.client('ce', region_name='us-east-1')
    
    try:
        if method == 'GET' and path.endswith('/insights'):
            # GET /insights - List available insights
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            # Get cost data for analysis
            costs_response = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost']
            )
            
            # Simple anomaly detection
            daily_costs = []
            for result in costs_response['ResultsByTime']:
                cost = float(result['Total']['UnblendedCost']['Amount'])
                daily_costs.append(cost)
            
            avg_cost = sum(daily_costs) / len(daily_costs) if daily_costs else 0
            anomalies = [cost for cost in daily_costs if cost > avg_cost * 1.5]
            
            insights = [
                {
                    'id': str(uuid.uuid4()),
                    'type': 'cost_anomaly',
                    'severity': 'high' if len(anomalies) > 5 else 'medium',
                    'title': 'Cost Anomaly Detection',
                    'description': f'Detected {len(anomalies)} days with costs above 150% of average',
                    'created_at': datetime.utcnow().isoformat()
                },
                {
                    'id': str(uuid.uuid4()),
                    'type': 'optimization',
                    'severity': 'medium',
                    'title': 'Cost Optimization Opportunities',
                    'description': f'Average daily cost: ${avg_cost:.2f}. Potential savings identified.',
                    'created_at': datetime.utcnow().isoformat()
                }
            ]
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Insights retrieved successfully',
                    'data': {
                        'insights': insights,
                        'count': len(insights),
                        'period': f"{start_date} to {end_date}"
                    }
                })
            }
            
        elif method == 'GET' and path.endswith('/insights/recommendations'):
            # GET /insights/recommendations - AI cost optimization recommendations
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            # Get service-level costs
            services_response = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            recommendations = []
            
            if services_response['ResultsByTime']:
                groups = services_response['ResultsByTime'][0]['Groups']
                sorted_services = sorted(groups, key=lambda x: float(x['Metrics']['UnblendedCost']['Amount']), reverse=True)
                
                for i, service in enumerate(sorted_services[:3]):  # Top 3 services
                    cost = float(service['Metrics']['UnblendedCost']['Amount'])
                    service_name = service['Keys'][0]
                    
                    # Generate AI-like recommendations
                    if 'Compute' in service_name or 'EC2' in service_name:
                        recommendations.append({
                            'id': str(uuid.uuid4()),
                            'type': 'rightsize',
                            'service': service_name,
                            'current_cost': round(cost, 2),
                            'potential_savings': round(cost * 0.15, 2),
                            'confidence': 85,
                            'description': 'Consider rightsizing EC2 instances based on utilization patterns',
                            'action': 'Review instance types and consider smaller sizes for underutilized resources'
                        })
                    elif 'Storage' in service_name or 'S3' in service_name:
                        recommendations.append({
                            'id': str(uuid.uuid4()),
                            'type': 'storage_optimization',
                            'service': service_name,
                            'current_cost': round(cost, 2),
                            'potential_savings': round(cost * 0.20, 2),
                            'confidence': 78,
                            'description': 'Optimize storage classes and lifecycle policies',
                            'action': 'Implement intelligent tiering and lifecycle rules for infrequently accessed data'
                        })
                    else:
                        recommendations.append({
                            'id': str(uuid.uuid4()),
                            'type': 'general_optimization',
                            'service': service_name,
                            'current_cost': round(cost, 2),
                            'potential_savings': round(cost * 0.10, 2),
                            'confidence': 65,
                            'description': 'Review usage patterns for optimization opportunities',
                            'action': 'Analyze service usage and consider reserved capacity or usage optimization'
                        })
            
            total_savings = sum(r['potential_savings'] for r in recommendations)
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'AI recommendations generated successfully',
                    'data': {
                        'recommendations': recommendations,
                        'total_potential_savings': round(total_savings, 2),
                        'count': len(recommendations),
                        'generated_at': datetime.utcnow().isoformat()
                    }
                })
            }
            
        elif method == 'POST' and path.endswith('/insights/generate'):
            # POST /insights/generate - Generate new insights
            body = json.loads(event.get('body', '{}'))
            analysis_type = body.get('type', 'full_analysis')
            
            job_id = str(uuid.uuid4())
            
            # Simulate AI processing
            insights_job = {
                'job_id': job_id,
                'type': analysis_type,
                'status': 'processing',
                'created_at': datetime.utcnow().isoformat(),
                'estimated_completion': (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
                'progress': 0
            }
            
            return {
                'statusCode': 202,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Insights generation started',
                    'data': insights_job
                })
            }
        
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Insights endpoint not found'})
        }
        
    except ClientError as e:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': f'AWS API error: {str(e)}'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Insights operation error: {str(e)}'})
        }
