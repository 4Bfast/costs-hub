import json
import boto3
import uuid
from datetime import datetime
from decimal import Decimal
from utils.jwt_utils_simple import extract_client_id_from_token
from config.settings import config

def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(v) for v in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj

def handle_alarms_request(event, cors_headers):
    """Handle alarms endpoints with real DynamoDB operations"""
    
    try:
        # Extract client_id from JWT token
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Unauthorized - Bearer token required'})
            }
        
        token = auth_header.replace('Bearer ', '')
        client_id = extract_client_id_from_token(token)
        
        path = event['path']
        method = event['httpMethod']
        
        # Route to specific alarm endpoint
        if method == 'GET' and (path.endswith('/alarms') or path.endswith('/alarms/')):
            return handle_list_alarms(client_id, cors_headers)
        elif method == 'POST' and (path.endswith('/alarms') or path.endswith('/alarms/')):
            return handle_create_alarm(event, client_id, cors_headers)
        elif method == 'PUT' and '/alarms/' in path:
            alarm_id = path.split('/alarms/')[-1]
            return handle_update_alarm(event, client_id, alarm_id, cors_headers)
        elif method == 'DELETE' and '/alarms/' in path:
            alarm_id = path.split('/alarms/')[-1]
            return handle_delete_alarm(client_id, alarm_id, cors_headers)
        
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Alarm endpoint not found: {method} {path}'})
        }
        
    except Exception as e:
        print(f"Error in alarms handler: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def handle_list_alarms(client_id, cors_headers):
    """Handle GET /alarms - List alarms for client"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
        table = dynamodb.Table('costhub-alarms')
        
        # Query alarms for this client
        response = table.scan(
            FilterExpression='client_id = :client_id',
            ExpressionAttributeValues={':client_id': client_id}
        )
        
        alarms = response.get('Items', [])
        
        # Sort by created_at desc
        alarms.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Convert Decimal to float for JSON
        alarms = decimal_to_float(alarms)
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': {
                    'alarms': alarms,
                    'count': len(alarms),
                    'client_id': client_id
                }
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to list alarms: {str(e)}'})
        }

def handle_create_alarm(event, client_id, cors_headers):
    """Handle POST /alarms - Create new alarm"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        required_fields = ['name', 'threshold', 'comparison_operator', 'metric_name']
        for field in required_fields:
            if field not in body:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # Generate alarm ID
        alarm_id = str(uuid.uuid4())
        
        # Create alarm record
        alarm = {
            'alarm_id': alarm_id,
            'client_id': client_id,
            'name': body['name'],
            'threshold': Decimal(str(body['threshold'])),
            'comparison_operator': body['comparison_operator'],
            'metric_name': body['metric_name'],
            'enabled': body.get('enabled', True),
            'notification_emails': body.get('notification_emails', []),
            'description': body.get('description', ''),
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Validate comparison operator
        valid_operators = ['>', '<', '>=', '<=', '==']
        if alarm['comparison_operator'] not in valid_operators:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': f'Invalid comparison_operator. Valid: {valid_operators}'})
            }
        
        # Save to DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
        table = dynamodb.Table('costhub-alarms')
        
        table.put_item(Item=alarm)
        
        # Convert Decimal to float for JSON response
        alarm_response = decimal_to_float(alarm)
        
        return {
            'statusCode': 201,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': alarm_response,
                'message': 'Alarm created successfully'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to create alarm: {str(e)}'})
        }

def handle_update_alarm(event, client_id, alarm_id, cors_headers):
    """Handle PUT /alarms/{id} - Update alarm"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
        table = dynamodb.Table('costhub-alarms')
        
        # Check if alarm exists and belongs to client
        response = table.get_item(Key={'alarm_id': alarm_id, 'client_id': client_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Alarm not found'})
            }
        
        # Build update expression
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.utcnow().isoformat() + 'Z'}
        
        # Update allowed fields
        allowed_fields = ['name', 'threshold', 'comparison_operator', 'metric_name', 'enabled', 'notification_emails', 'description']
        
        for field in allowed_fields:
            if field in body:
                update_expression += f", {field} = :{field}"
                if field == 'threshold':
                    expression_values[f':{field}'] = Decimal(str(body[field]))
                else:
                    expression_values[f':{field}'] = body[field]
        
        # Update item
        table.update_item(
            Key={'alarm_id': alarm_id, 'client_id': client_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        # Get updated item
        response = table.get_item(Key={'alarm_id': alarm_id, 'client_id': client_id})
        updated_alarm = decimal_to_float(response['Item'])
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': updated_alarm,
                'message': 'Alarm updated successfully'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to update alarm: {str(e)}'})
        }

def handle_delete_alarm(client_id, alarm_id, cors_headers):
    """Handle DELETE /alarms/{id} - Delete alarm"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
        table = dynamodb.Table('costhub-alarms')
        
        # Check if alarm exists and belongs to client
        response = table.get_item(Key={'alarm_id': alarm_id, 'client_id': client_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Alarm not found'})
            }
        
        # Delete alarm
        table.delete_item(Key={'alarm_id': alarm_id, 'client_id': client_id})
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'message': 'Alarm deleted successfully'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to delete alarm: {str(e)}'})
        }
