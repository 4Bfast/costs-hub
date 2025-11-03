"""
Real Accounts Handler with DynamoDB persistence
"""

import json
import boto3
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
accounts_table = dynamodb.Table('costhub-accounts')

def lambda_handler(event, context):
    """Handle accounts API requests with real DynamoDB operations"""
    
    try:
        method = event['httpMethod']
        path = event['path']
        
        # CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': 'https://costhub.4bfast.com.br',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Request-ID,X-Requested-With',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        }
        
        if method == 'GET':
            return handle_get_accounts(cors_headers)
        elif method == 'POST':
            return handle_create_account(event, cors_headers)
        elif method == 'PUT':
            return handle_put_account(event, accounts_table, cors_headers)
        elif method == 'DELETE':
            return handle_delete_account(event, accounts_table, cors_headers)
        else:
            return {
                'statusCode': 405,
                'headers': {**cors_headers, 'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'https://costhub.4bfast.com.br'
            },
            'body': json.dumps({'error': str(e)})
        }

def handle_get_accounts(cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Get all accounts from DynamoDB"""
    try:
        response = accounts_table.scan()
        accounts = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Accounts retrieved successfully',
                'accounts': accounts,
                'count': len(accounts)
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Failed to retrieve accounts: {str(e)}'})
        }

def handle_create_account(event: Dict[str, Any], cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Create a new account in DynamoDB"""
    try:
        # Parse request body
        body_data = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        required_fields = ['name', 'provider_type']
        for field in required_fields:
            if not body_data.get(field):
                return {
                    'statusCode': 400,
                    'headers': {**cors_headers, 'Content-Type': 'application/json'},
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # Create account record
        account_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        account = {
            'account_id': account_id,
            'name': body_data['name'],
            'provider_type': body_data['provider_type'],
            'credentials': body_data.get('credentials', {}),
            'status': 'active',
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        # Save to DynamoDB
        accounts_table.put_item(Item=account)
        
        return {
            'statusCode': 201,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Account created successfully',
                'account': account
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Failed to create account: {str(e)}'})
        }

def handle_put_account(event, accounts_table, cors_headers):
    """Handle PUT /accounts/{id} - Update account"""
    try:
        # Extract account ID from path
        path_parts = event['path'].split('/')
        account_id = path_parts[-1] if len(path_parts) > 0 else None
        
        if not account_id:
            return {
                'statusCode': 400,
                'headers': {**cors_headers, 'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Account ID required'})
            }
        
        # Parse request body
        body_data = json.loads(event.get('body', '{}'))
        
        # Get existing account
        response = accounts_table.get_item(Key={'account_id': account_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {**cors_headers, 'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Account not found'})
            }
        
        # Update account
        account = response['Item']
        account['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        
        # Update allowed fields
        updatable_fields = ['name', 'provider_type', 'credentials', 'status']
        for field in updatable_fields:
            if field in body_data:
                account[field] = body_data[field]
        
        # Save updated account
        accounts_table.put_item(Item=account)
        
        return {
            'statusCode': 200,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Account updated successfully',
                'account': account
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

def handle_delete_account(event, accounts_table, cors_headers):
    """Handle DELETE /accounts/{id} - Delete account"""
    try:
        # Extract account ID from path
        path_parts = event['path'].split('/')
        account_id = path_parts[-1] if len(path_parts) > 0 else None
        
        if not account_id:
            return {
                'statusCode': 400,
                'headers': {**cors_headers, 'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Account ID required'})
            }
        
        # Check if account exists
        response = accounts_table.get_item(Key={'account_id': account_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {**cors_headers, 'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Account not found'})
            }
        
        # Delete account
        accounts_table.delete_item(Key={'account_id': account_id})
        
        return {
            'statusCode': 200,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Account deleted successfully'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
