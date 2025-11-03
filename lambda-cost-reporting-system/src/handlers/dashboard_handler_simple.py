"""
Dashboard Handler - Real-time cost analytics
"""
import json
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

def handle_dashboard_request(event, cors_headers):
    """Handle dashboard endpoints"""
    path = event['path']
    method = event['httpMethod']
    
    ce_client = boto3.client('ce', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    try:
        if method == 'GET' and path.endswith('/dashboard'):
            # GET /dashboard - Main dashboard overview
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            # Get current month costs
            current_costs = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost']
            )
            
            total_cost = 0
            if current_costs['ResultsByTime']:
                total_cost = float(current_costs['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
            
            # Get service count
            services_response = ce_client.get_dimension_values(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Dimension='SERVICE'
            )
            
            service_count = len(services_response['DimensionValues'])
            
            # Get accounts count
            accounts_table = dynamodb.Table('costhub-accounts')
            accounts_response = accounts_table.scan()
            accounts_count = len(accounts_response.get('Items', []))
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Dashboard overview retrieved successfully',
                    'data': {
                        'totalCost': round(total_cost, 2),
                        'servicesCount': service_count,
                        'accountsCount': accounts_count,
                        'period': f"{start_date} to {end_date}",
                        'status': 'active'
                    }
                })
            }
            
        elif method == 'GET' and path.endswith('/dashboard/summary'):
            # GET /dashboard/summary - Cost summary with KPIs
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            prev_start = start_date - timedelta(days=30)
            
            # Current month costs
            current_costs = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost']
            )
            
            # Previous month costs
            prev_costs = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': prev_start.strftime('%Y-%m-%d'),
                    'End': start_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost']
            )
            
            current_total = 0
            prev_total = 0
            
            if current_costs['ResultsByTime']:
                current_total = float(current_costs['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
            
            if prev_costs['ResultsByTime']:
                prev_total = float(prev_costs['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
            
            # Calculate MoM growth
            mom_growth = 0
            if prev_total > 0:
                mom_growth = ((current_total - prev_total) / prev_total) * 100
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Dashboard summary retrieved successfully',
                    'data': {
                        'currentMonthCost': round(current_total, 2),
                        'previousMonthCost': round(prev_total, 2),
                        'monthOverMonthGrowth': round(mom_growth, 2),
                        'trend': 'increasing' if mom_growth > 0 else 'decreasing',
                        'period': f"{start_date} to {end_date}"
                    }
                })
            }
            
        elif method == 'GET' and path.endswith('/dashboard/cost-trends'):
            # GET /dashboard/cost-trends - Historical cost trends
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=90)  # Last 3 months
            
            trends_response = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost']
            )
            
            trends_data = []
            for result in trends_response['ResultsByTime']:
                cost = float(result['Total']['UnblendedCost']['Amount'])
                trends_data.append({
                    'date': result['TimePeriod']['Start'],
                    'cost': round(cost, 2)
                })
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Cost trends retrieved successfully',
                    'data': {
                        'trends': trends_data,
                        'period': f"{start_date} to {end_date}",
                        'dataPoints': len(trends_data)
                    }
                })
            }
            
        elif method == 'GET' and path.endswith('/dashboard/overview'):
            # GET /dashboard/overview - Multi-account overview
            accounts_table = dynamodb.Table('costhub-accounts')
            alarms_table = dynamodb.Table('costhub-alarms')
            
            # Get accounts
            accounts_response = accounts_table.scan()
            accounts = accounts_response.get('Items', [])
            
            # Get alarms
            alarms_response = alarms_table.scan()
            alarms = alarms_response.get('Items', [])
            active_alarms = [a for a in alarms if a.get('status') == 'active']
            
            # Get top services by cost
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            services_costs = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            top_services = []
            if services_costs['ResultsByTime']:
                groups = services_costs['ResultsByTime'][0]['Groups']
                sorted_services = sorted(groups, key=lambda x: float(x['Metrics']['UnblendedCost']['Amount']), reverse=True)
                
                for service in sorted_services[:5]:  # Top 5 services
                    top_services.append({
                        'service': service['Keys'][0],
                        'cost': round(float(service['Metrics']['UnblendedCost']['Amount']), 2)
                    })
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Dashboard overview retrieved successfully',
                    'data': {
                        'accountsCount': len(accounts),
                        'activeAlarmsCount': len(active_alarms),
                        'totalAlarmsCount': len(alarms),
                        'topServices': top_services,
                        'period': f"{start_date} to {end_date}"
                    }
                })
            }
        
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Dashboard endpoint not found'})
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
            'body': json.dumps({'error': f'Dashboard operation error: {str(e)}'})
        }
