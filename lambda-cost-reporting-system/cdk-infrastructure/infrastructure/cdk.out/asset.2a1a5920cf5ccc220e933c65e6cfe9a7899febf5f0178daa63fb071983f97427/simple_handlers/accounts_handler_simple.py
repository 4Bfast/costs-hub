"""
Accounts Handler - DynamoDB CRUD operations
"""
import json
import boto3
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

TABLE_NAME = "costhub-accounts"

def handle_accounts_request(event, cors_headers):
    """Handle accounts endpoints"""
    path = event['path']
    method = event['httpMethod']
    
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        if method == 'GET' and path.endswith('/accounts'):
            # GET /accounts - List all accounts
            response = table.scan()
            accounts = response.get('Items', [])
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Accounts retrieved successfully',
                    'data': {
                        'accounts': accounts,
                        'count': len(accounts)
                    }
                })
            }
            
        elif method == 'POST' and path.endswith('/accounts'):
            # POST /accounts - Create new account
            body = json.loads(event.get('body', '{}'))
            
            required_fields = ['name', 'provider_type']
            for field in required_fields:
                if not body.get(field):
                    return {
                        'statusCode': 400,
                        'headers': cors_headers,
                        'body': json.dumps({'error': f'{field} is required'})
                    }
            
            account_id = str(uuid.uuid4())
            account_data = {
                'account_id': account_id,
                'name': body['name'],
                'provider_type': body['provider_type'],
                'status': body.get('status', 'active'),
                'credentials': body.get('credentials', {}),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            table.put_item(Item=account_data)
            
            return {
                'statusCode': 201,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Account created successfully',
                    'data': account_data
                })
            }
            
        elif method == 'PUT' and '/accounts/' in path:
            # PUT /accounts/{id} - Update account
            account_id = path.split('/accounts/')[-1]
            body = json.loads(event.get('body', '{}'))
            
            # Check if account exists
            try:
                response = table.get_item(Key={'account_id': account_id})
                if 'Item' not in response:
                    return {
                        'statusCode': 404,
                        'headers': cors_headers,
                        'body': json.dumps({'error': 'Account not found'})
                    }
            except ClientError:
                return {
                    'statusCode': 404,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Account not found'})
                }
            
            # Update account
            update_expression = "SET updated_at = :updated_at"
            expression_values = {':updated_at': datetime.utcnow().isoformat()}
            
            if body.get('name'):
                update_expression += ", #name = :name"
                expression_values[':name'] = body['name']
            
            if body.get('status'):
                update_expression += ", #status = :status"
                expression_values[':status'] = body['status']
            
            if body.get('credentials'):
                update_expression += ", credentials = :credentials"
                expression_values[':credentials'] = body['credentials']
            
            expression_names = {}
            if body.get('name'):
                expression_names['#name'] = 'name'
            if body.get('status'):
                expression_names['#status'] = 'status'
            
            update_params = {
                'Key': {'account_id': account_id},
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
                    'message': 'Account updated successfully',
                    'data': response['Attributes']
                })
            }
            
        elif method == 'DELETE' and '/accounts/' in path:
            # DELETE /accounts/{id} - Delete account
            account_id = path.split('/accounts/')[-1]
            
            # Check if account exists
            try:
                response = table.get_item(Key={'account_id': account_id})
                if 'Item' not in response:
                    return {
                        'statusCode': 404,
                        'headers': cors_headers,
                        'body': json.dumps({'error': 'Account not found'})
                    }
            except ClientError:
                return {
                    'statusCode': 404,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Account not found'})
                }
            
            # Delete account
            table.delete_item(Key={'account_id': account_id})
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Account deleted successfully',
                    'data': {'account_id': account_id}
                })
            }
        
        return {
            'statusCode': 404,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Account endpoint not found'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Account operation error: {str(e)}'})
        }
