#!/usr/bin/env python3
"""
CDK App for Alarms DynamoDB Table
"""

from aws_cdk import App, Stack, RemovalPolicy, Environment
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct

class AlarmsTableStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create Alarms DynamoDB Table
        self.alarms_table = dynamodb.Table(
            self, "AlarmsTable",
            table_name="costhub-alarms",
            partition_key=dynamodb.Attribute(
                name="alarm_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )

from aws_cdk import Environment

app = App()
env = Environment(account="008195334540", region="us-east-1")
AlarmsTableStack(app, "costhub-alarms-table", env=env)
app.synth()
