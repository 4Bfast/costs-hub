import json
import boto3
from datetime import datetime
import uuid

def handle_accounts(event, context):
    """Handle accounts API requests with proper field mapping"""
    
    method = event['httpMethod']
    path = event['path']
    
    # CORS headers
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': 'https://costhub.4bfast.com.br',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Request-ID,X-Requested-With',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    try:
        if method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }
        
        # Initialize DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('costhub-accounts')
        
        if method == 'GET':
            # List all accounts
            response = table.scan()
            accounts = response.get('Items', [])
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'accounts': accounts,
                    'total': len(accounts)
                })
            }
        
        elif method == 'POST':
            # Create new account
            body = json.loads(event['body'])
            
            # Map frontend fields to backend fields
            account_data = {
                'id': str(uuid.uuid4()),
                'name': body.get('account_name') or body.get('display_name'),  # Map account_name to name
                'provider_type': body.get('provider', 'aws'),  # Map provider to provider_type
                'account_id': body.get('account_id'),
                'display_name': body.get('display_name'),
                'status': body.get('status', 'pending'),
                'configuration': body.get('configuration', {}),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Validate required fields
            if not account_data['name']:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'error': 'Missing required field: name (account_name or display_name)'
                    })
                }
            
            if not account_data['account_id']:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'error': 'Missing required field: account_id'
                    })
                }
            
            # Save to DynamoDB
            table.put_item(Item=account_data)
            
            return {
                'statusCode': 201,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Account created successfully',
                    'account': account_data
                })
            }
        
        elif method == 'PUT':
            # Update account
            account_id = event['pathParameters'].get('id')
            if not account_id:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Missing account ID'})
                }
            
            body = json.loads(event['body'])
            
            # Map frontend fields to backend fields
            update_data = {
                'name': body.get('account_name') or body.get('display_name'),
                'provider_type': body.get('provider', 'aws'),
                'account_id': body.get('account_id'),
                'display_name': body.get('display_name'),
                'status': body.get('status'),
                'configuration': body.get('configuration'),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            # Update in DynamoDB
            table.update_item(
                Key={'id': account_id},
                UpdateExpression='SET ' + ', '.join([f'{k} = :{k}' for k in update_data.keys()]),
                ExpressionAttributeValues={f':{k}': v for k, v in update_data.items()}
            )
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Account updated successfully'
                })
            }
        
        elif method == 'DELETE':
            # Delete account
            account_id = event['pathParameters'].get('id')
            if not account_id:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Missing account ID'})
                }
            
            table.delete_item(Key={'id': account_id})
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Account deleted successfully'
                })
            }
        
        else:
            return {
                'statusCode': 405,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Method not allowed'})
            }
    
    except Exception as e:
        print(f"Error in accounts handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
