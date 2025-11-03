"""
Alarms Handler - DynamoDB CRUD operations
"""
import json
import boto3
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

TABLE_NAME = "costhub-alarms"

def handle_alarms_request(event, cors_headers):
    """Handle alarms endpoints"""
    path = event['path']
    method = event['httpMethod']
    
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        if method == 'GET' and path.endswith('/alarms'):
            # GET /alarms - List all alarms
            response = table.scan()
            alarms = response.get('Items', [])
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Alarms retrieved successfully',
                    'data': {
                        'alarms': alarms,
                        'count': len(alarms)
                    }
                })
            }
            
        elif method == 'POST' and path.endswith('/alarms'):
            # POST /alarms - Create new alarm
            body = json.loads(event.get('body', '{}'))
            
            required_fields = ['name', 'threshold', 'comparison']
            for field in required_fields:
                if not body.get(field):
                    return {
                        'statusCode': 400,
                        'headers': cors_headers,
                        'body': json.dumps({'error': f'{field} is required'})
                    }
            
            alarm_id = str(uuid.uuid4())
            alarm_data = {
                'alarm_id': alarm_id,
                'name': body['name'],
                'threshold': body['threshold'],
                'comparison': body['comparison'],
                'status': body.get('status', 'active'),
                'account_ids': body.get('account_ids', []),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            table.put_item(Item=alarm_data)
            
            return {
                'statusCode': 201,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Alarm created successfully',
                    'data': alarm_data
                })
            }
            
        elif method == 'PUT' and '/alarms/' in path:
            # PUT /alarms/{id} - Update alarm
            alarm_id = path.split('/alarms/')[-1]
            body = json.loads(event.get('body', '{}'))
            
            # Check if alarm exists
            try:
                response = table.get_item(Key={'alarm_id': alarm_id})
                if 'Item' not in response:
                    return {
                        'statusCode': 404,
                        'headers': cors_headers,
                        'body': json.dumps({'error': 'Alarm not found'})
                    }
            except ClientError:
                return {
                    'statusCode': 404,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Alarm not found'})
                }
            
            # Update alarm
            update_expression = "SET updated_at = :updated_at"
            expression_values = {':updated_at': datetime.utcnow().isoformat()}
            
            if body.get('name'):
                update_expression += ", #name = :name"
                expression_values[':name'] = body['name']
            
            if body.get('threshold'):
                update_expression += ", threshold = :threshold"
                expression_values[':threshold'] = body['threshold']
            
            if body.get('status'):
                update_expression += ", #status = :status"
                expression_values[':status'] = body['status']
            
            expression_names = {}
            if body.get('name'):
                expression_names['#name'] = 'name'
            if body.get('status'):
                expression_names['#status'] = 'status'
            
            update_params = {
                'Key': {'alarm_id': alarm_id},
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': expression_values,
                'ReturnValues': 'ALL_NEW'
            }
            
            if expression_names:
                update_params['ExpressionAttributeNames'] = expression_names
            
            response = table.update_item(**update_params)
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Alarm updated successfully',
                    'data': response['Attributes']
                })
            }
            
        elif method == 'DELETE' and '/alarms/' in path:
            # DELETE /alarms/{id} - Delete alarm
            alarm_id = path.split('/alarms/')[-1]
            
            # Check if alarm exists
            try:
                response = table.get_item(Key={'alarm_id': alarm_id})
                if 'Item' not in response:
                    return {
                        'statusCode': 404,
                        'headers': cors_headers,
                        'body': json.dumps({'error': 'Alarm not found'})
                    }
            except ClientError:
                return {
                    'statusCode': 404,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Alarm not found'})
                }
            
            # Delete alarm
            table.delete_item(Key={'alarm_id': alarm_id})
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Alarm deleted successfully',
                    'data': {'alarm_id': alarm_id}
                })
            }
        
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Alarm endpoint not found'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Alarm operation error: {str(e)}'})
        }
