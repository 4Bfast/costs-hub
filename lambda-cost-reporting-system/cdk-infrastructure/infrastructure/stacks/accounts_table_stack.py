"""
Accounts Table Stack for CostHub
Creates the DynamoDB table for account management
"""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    CfnOutput
)
from constructs import Construct

class AccountsTableStack(Stack):
    """CDK Stack for Accounts DynamoDB table"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create accounts table
        self.accounts_table = dynamodb.Table(
            self, "AccountsTable",
            table_name="costhub-accounts",
            partition_key=dynamodb.Attribute(
                name="account_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True
        )
        
        # Create IAM role for Lambda to access the table
        self.lambda_role = iam.Role(
            self, "AccountsLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Grant Lambda permissions to the table
        self.accounts_table.grant_read_write_data(self.lambda_role)
        
        # Outputs
        CfnOutput(
            self, "AccountsTableName",
            value=self.accounts_table.table_name,
            description="Name of the accounts DynamoDB table"
        )
        
        CfnOutput(
            self, "AccountsTableArn",
            value=self.accounts_table.table_arn,
            description="ARN of the accounts DynamoDB table"
        )
        
        CfnOutput(
            self, "LambdaRoleArn",
            value=self.lambda_role.role_arn,
            description="ARN of the Lambda execution role"
        )
