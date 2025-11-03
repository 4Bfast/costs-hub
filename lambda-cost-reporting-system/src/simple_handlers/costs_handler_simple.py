"""
Cost Data Handler - AWS Cost Explorer Integration
"""
import json
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

def get_cost_data(start_date, end_date, granularity='DAILY', group_by=None, metrics=['UnblendedCost']):
    """Get cost data from AWS Cost Explorer"""
    try:
        ce_client = boto3.client('ce', region_name='us-east-1')
        
        params = {
            'TimePeriod': {
                'Start': start_date,
                'End': end_date
            },
            'Granularity': granularity,
            'Metrics': metrics
        }
        
        if group_by:
            params['GroupBy'] = [{'Type': 'DIMENSION', 'Key': group_by}]
        
        response = ce_client.get_cost_and_usage(**params)
        return response
        
    except ClientError as e:
        raise Exception(f"Cost Explorer error: {str(e)}")

def handle_costs_request(event, cors_headers):
    """Handle costs endpoints"""
    path = event['path']
    method = event['httpMethod']
    
    # Default date range (last 30 days)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    try:
        if method == 'GET':
            if path.endswith('/costs'):
                # GET /costs - Overall cost data
                cost_data = get_cost_data(start_date, end_date)
                
                total_cost = 0
                for result in cost_data['ResultsByTime']:
                    total_cost += float(result['Total']['UnblendedCost']['Amount'])
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'message': 'Cost data retrieved successfully',
                        'data': {
                            'period': {'start': start_date, 'end': end_date},
                            'totalCost': round(total_cost, 2),
                            'currency': cost_data['ResultsByTime'][0]['Total']['UnblendedCost']['Unit'] if cost_data['ResultsByTime'] else 'USD',
                            'details': cost_data['ResultsByTime']
                        }
                    })
                }
                
            elif path.endswith('/costs/summary'):
                # GET /costs/summary - Cost summary
                cost_data = get_cost_data(start_date, end_date, group_by='SERVICE')
                
                services = []
                total_cost = 0
                
                for result in cost_data['ResultsByTime']:
                    for group in result['Groups']:
                        service_name = group['Keys'][0]
                        service_cost = float(group['Metrics']['UnblendedCost']['Amount'])
                        total_cost += service_cost
                        
                        # Find or create service entry
                        service_entry = next((s for s in services if s['service'] == service_name), None)
                        if service_entry:
                            service_entry['cost'] += service_cost
                        else:
                            services.append({'service': service_name, 'cost': service_cost})
                
                # Sort by cost descending
                services.sort(key=lambda x: x['cost'], reverse=True)
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'message': 'Cost summary retrieved successfully',
                        'data': {
                            'totalCost': round(total_cost, 2),
                            'topServices': services[:10],
                            'period': {'start': start_date, 'end': end_date}
                        }
                    })
                }
                
            elif path.endswith('/costs/trends'):
                # GET /costs/trends - Cost trends over time
                cost_data = get_cost_data(start_date, end_date, granularity='DAILY')
                
                trends = []
                for result in cost_data['ResultsByTime']:
                    trends.append({
                        'date': result['TimePeriod']['Start'],
                        'cost': float(result['Total']['UnblendedCost']['Amount'])
                    })
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'message': 'Cost trends retrieved successfully',
                        'data': {
                            'trends': trends,
                            'period': {'start': start_date, 'end': end_date}
                        }
                    })
                }
                
            elif path.endswith('/costs/breakdown'):
                # GET /costs/breakdown - Detailed cost breakdown
                cost_data = get_cost_data(start_date, end_date, group_by='SERVICE')
                
                breakdown = []
                for result in cost_data['ResultsByTime']:
                    date = result['TimePeriod']['Start']
                    for group in result['Groups']:
                        breakdown.append({
                            'date': date,
                            'service': group['Keys'][0],
                            'cost': float(group['Metrics']['UnblendedCost']['Amount'])
                        })
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'message': 'Cost breakdown retrieved successfully',
                        'data': {
                            'breakdown': breakdown,
                            'period': {'start': start_date, 'end': end_date}
                        }
                    })
                }
                
            elif path.endswith('/costs/by-service'):
                # GET /costs/by-service - Costs grouped by service
                cost_data = get_cost_data(start_date, end_date, group_by='SERVICE')
                
                services = {}
                for result in cost_data['ResultsByTime']:
                    for group in result['Groups']:
                        service_name = group['Keys'][0]
                        service_cost = float(group['Metrics']['UnblendedCost']['Amount'])
                        
                        if service_name not in services:
                            services[service_name] = 0
                        services[service_name] += service_cost
                
                # Convert to list and sort
                service_list = [{'service': k, 'cost': round(v, 2)} for k, v in services.items()]
                service_list.sort(key=lambda x: x['cost'], reverse=True)
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'message': 'Costs by service retrieved successfully',
                        'data': {
                            'services': service_list,
                            'period': {'start': start_date, 'end': end_date}
                        }
                    })
                }
                
            elif path.endswith('/costs/by-region'):
                # GET /costs/by-region - Costs grouped by region
                cost_data = get_cost_data(start_date, end_date, group_by='REGION')
                
                regions = {}
                for result in cost_data['ResultsByTime']:
                    for group in result['Groups']:
                        region_name = group['Keys'][0] or 'Global'
                        region_cost = float(group['Metrics']['UnblendedCost']['Amount'])
                        
                        if region_name not in regions:
                            regions[region_name] = 0
                        regions[region_name] += region_cost
                
                # Convert to list and sort
                region_list = [{'region': k, 'cost': round(v, 2)} for k, v in regions.items()]
                region_list.sort(key=lambda x: x['cost'], reverse=True)
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'message': 'Costs by region retrieved successfully',
                        'data': {
                            'regions': region_list,
                            'period': {'start': start_date, 'end': end_date}
                        }
                    })
                }
        
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Cost endpoint not found'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Cost data error: {str(e)}'})
        }
