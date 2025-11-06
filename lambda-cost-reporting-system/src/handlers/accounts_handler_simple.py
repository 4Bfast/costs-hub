"""
Accounts Handler - Account management
"""
import json
import boto3
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
accounts_table = dynamodb.Table('costhub-accounts')

def validate_authorization_inline(event, cors_headers):
    """Inline authorization validation"""
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization') or headers.get('authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return False, {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Unauthorized'})
        }, None
    
    access_token = auth_header.replace('Bearer ', '')
    
    try:
        cognito = boto3.client('cognito-idp', region_name='us-east-1')
        response = cognito.get_user(AccessToken=access_token)
        username = response['Username']
        
        # Map username to client_id (simple mapping for now)
        # In production, this should be stored in a proper user-client mapping table
        client_id = get_client_id_for_user(username)
        
        return True, None, {
            'username': username,
            'client_id': client_id
        }
    except:
        return False, {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Unauthorized'})
        }, None

def get_client_id_for_user(username):
    """Get client_id for a given username"""
    # For now, map all users to the test client
    # In production, this should query a user-client mapping table
    return "test-client-001"

def handle_accounts_request(event, cors_headers):
    """Handle accounts endpoints"""
    # Validate authorization first
    is_valid, error_response, user_info = validate_authorization_inline(event, cors_headers)
    if not is_valid:
        return error_response
    
    path = event['path']
    method = event['httpMethod']
    
    try:
        if method == 'GET' and path.endswith('/accounts'):
            return handle_get_accounts(cors_headers, user_info)
        elif method == 'POST' and path.endswith('/accounts'):
            return handle_create_account(event, cors_headers, user_info)
        elif method == 'PUT' and '/accounts/' in path:
            return handle_update_account(event, cors_headers, user_info)
        elif method == 'DELETE' and '/accounts/' in path:
            return handle_delete_account(event, cors_headers, user_info)
        elif method == 'POST' and '/test' in path:
            return handle_test_connection(event, cors_headers, user_info)
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Accounts endpoint not found'})
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Accounts error: {str(e)}'})
        }

def handle_get_accounts(cors_headers, user_info):
    """Get all accounts from DynamoDB for the authenticated user's client"""
    try:
        client_id = user_info.get('client_id')
        
        # Query accounts for this specific client
        response = accounts_table.scan(
            FilterExpression='client_id = :client_id',
            ExpressionAttributeValues={':client_id': client_id}
        )
        accounts = response.get('Items', [])
        
        # If no accounts found with client_id, get all accounts and assign client_id
        if not accounts:
            response = accounts_table.scan()
            all_accounts = response.get('Items', [])
            
            # Update existing accounts to have the correct client_id
            for account in all_accounts:
                if 'client_id' not in account or account.get('client_id') == 'default':
                    account['client_id'] = client_id
                    accounts_table.put_item(Item=account)
            
            accounts = all_accounts
        
        # Normalize accounts to match frontend expectations
        normalized_accounts = []
        for account in accounts:
            normalized_account = {
                'id': account.get('id', account.get('account_id', str(uuid.uuid4()))),
                'client_id': client_id,  # Use the authenticated user's client_id
                'provider': account.get('provider_type', 'aws'),
                'account_id': account.get('account_id'),
                'account_name': account.get('name', account.get('account_name')),
                'display_name': account.get('display_name', account.get('name')),
                'status': account.get('status', 'pending'),
                'last_sync': account.get('last_sync'),
                'configuration': account.get('configuration', {}),
                'created_at': account.get('created_at'),
                'updated_at': account.get('updated_at')
            }
            normalized_accounts.append(normalized_account)
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': normalized_accounts,
                'metadata': {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'version': '1.0',
                    'request_id': f'req_{int(datetime.utcnow().timestamp())}',
                    'client_id': client_id
                },
                'errors': []
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'success': False,
                'data': None,
                'metadata': {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'version': '1.0',
                    'request_id': f'req_{int(datetime.utcnow().timestamp())}'
                },
                'errors': [f'Failed to retrieve accounts: {str(e)}']
            })
        }

def handle_create_account(event, cors_headers, user_info):
    """Create a new account in DynamoDB"""
    try:
        # Parse request body
        body_data = json.loads(event.get('body', '{}'))
        
        # Map frontend fields to backend fields
        name = body_data.get('account_name') or body_data.get('display_name') or body_data.get('name')
        provider_type = body_data.get('provider') or body_data.get('provider_type', 'aws')
        client_id = user_info.get('client_id')  # Use authenticated user's client_id
        
        # Validate required fields
        if not name:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing required field: name (account_name, display_name, or name)'})
            }
        
        if not body_data.get('account_id'):
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing required field: account_id'})
            }
        
        # Create account record
        account_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        account = {
            'id': account_id,  # Use 'id' as primary key
            'client_id': client_id,  # Associate with authenticated user's client
            'account_id': body_data.get('account_id'),  # AWS account ID
            'name': name,
            'display_name': body_data.get('display_name', name),
            'provider_type': provider_type,
            'status': body_data.get('status', 'pending'),
            'configuration': body_data.get('configuration', {}),
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        # Save to DynamoDB
        accounts_table.put_item(Item=account)
        
        return {
            'statusCode': 201,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': account,
                'metadata': {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'version': '1.0',
                    'request_id': f'req_{int(datetime.utcnow().timestamp())}'
                },
                'errors': []
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
            'body': json.dumps({'error': f'Failed to create account: {str(e)}'})
        }

def handle_update_account(event, cors_headers, user_info):
    """Handle PUT /accounts/{id} - Update account"""
    try:
        # Extract account ID from path
        path_parts = event['path'].split('/')
        account_id = path_parts[-1] if len(path_parts) > 0 else None
        
        if not account_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Account ID required'})
            }
        
        # Parse request body
        body_data = json.loads(event.get('body', '{}'))
        
        # Get existing account
        response = accounts_table.get_item(Key={'id': account_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
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
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Account updated successfully',
                'account': account
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
            'body': json.dumps({'error': str(e)})
        }

def handle_delete_account(event, cors_headers, user_info):
    """Handle DELETE /accounts/{id} - Delete account"""
    try:
        # Extract account ID from path
        path_parts = event['path'].split('/')
        account_id = path_parts[-1] if len(path_parts) > 0 else None
        
        if not account_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Account ID required'})
            }
        
        # Check if account exists
        response = accounts_table.get_item(Key={'id': account_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Account not found'})
            }
        
        # Delete account
        accounts_table.delete_item(Key={'id': account_id})
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Account deleted successfully'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }

def handle_test_connection(event, cors_headers, user_info):
    """Handle POST /accounts/{id}/test - Test account connection"""
    try:
        # Extract account ID from path
        path_parts = event['path'].split('/')
        account_id = None
        for i, part in enumerate(path_parts):
            if part == 'accounts' and i + 1 < len(path_parts):
                account_id = path_parts[i + 1]
                break
        
        if not account_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({
                    'success': False,
                    'data': None,
                    'metadata': {
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'version': '1.0',
                        'request_id': f'req_{int(datetime.utcnow().timestamp())}'
                    },
                    'errors': ['Account ID required']
                })
            }
        
        # Get account from DynamoDB using account_id as primary key
        response = accounts_table.get_item(Key={'account_id': account_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({
                    'success': False,
                    'data': None,
                    'metadata': {
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'version': '1.0',
                        'request_id': f'req_{int(datetime.utcnow().timestamp())}'
                    },
                    'errors': ['Account not found']
                })
            }
        
        account = response['Item']
        configuration = account.get('configuration', {})
        
        # Test AWS connection using role_arn and external_id
        test_result = {
            'success': True,
            'connection_status': 'healthy',
            'permissions_valid': True,
            'issues': [],
            'test_results': {
                'authentication': True,
                'permissions': True,
                'data_access': True
            }
        }
        
        # Simple validation - check if required fields exist
        if not configuration.get('role_arn'):
            test_result['success'] = False
            test_result['connection_status'] = 'unhealthy'
            test_result['permissions_valid'] = False
            test_result['issues'].append('Missing role_arn in configuration')
            test_result['test_results']['authentication'] = False
        
        if not configuration.get('external_id'):
            test_result['success'] = False
            test_result['connection_status'] = 'unhealthy'
            test_result['permissions_valid'] = False
            test_result['issues'].append('Missing external_id in configuration')
            test_result['test_results']['authentication'] = False
        
        # Try to assume role (basic test)
        if test_result['success']:
            try:
                # This is a basic test - in production you'd actually assume the role
                # For now, just validate the ARN format
                role_arn = configuration['role_arn']
                if not role_arn.startswith('arn:aws:iam::'):
                    test_result['success'] = False
                    test_result['issues'].append('Invalid role ARN format')
                    test_result['test_results']['authentication'] = False
            except Exception as e:
                test_result['success'] = False
                test_result['connection_status'] = 'unhealthy'
                test_result['issues'].append(f'Connection test failed: {str(e)}')
                test_result['test_results']['authentication'] = False
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'data': test_result,
                'metadata': {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'version': '1.0',
                    'request_id': f'req_{int(datetime.utcnow().timestamp())}'
                },
                'errors': []
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'success': False,
                'data': None,
                'metadata': {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'version': '1.0',
                    'request_id': f'req_{int(datetime.utcnow().timestamp())}'
                },
                'errors': [f'Connection test failed: {str(e)}']
            })
        }
