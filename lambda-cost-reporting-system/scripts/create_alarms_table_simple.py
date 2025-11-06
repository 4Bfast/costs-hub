import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

try:
    table = dynamodb.create_table(
        TableName='costhub-alarms',
        KeySchema=[{'AttributeName': 'alarm_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'alarm_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    print("✅ Table created: costhub-alarms")
except Exception as e:
    if 'ResourceInUseException' in str(e):
        print("✅ Table already exists")
    else:
        print(f"❌ Error: {e}")
