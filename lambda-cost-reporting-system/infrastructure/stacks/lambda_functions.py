"""
Lambda function definitions for Multi-Cloud Analytics Stack
"""

from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct
from typing import Dict, Any
from config.environments import EnvironmentConfig


class LambdaFunctions:
    """Helper class to create Lambda functions for Multi-Cloud Analytics"""
    
    def __init__(self, stack: Construct, env_config: EnvironmentConfig, resources: Dict[str, Any]):
        self.stack = stack
        self.env_config = env_config
        self.env_name = env_config.name
        self.resource_prefix = f"multi-cloud-analytics-{env_config.name}"
        self.resources = resources
    
    def create_cost_orchestrator_function(self) -> _lambda.Function:
        """Create Lambda function for cost collection orchestration"""
        
        # Create execution role
        role = iam.Role(
            self.stack,
            "CostOrchestratorRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess")
            ]
        )
        
        # Add permissions for DynamoDB
        self.resources['cost_data_table'].grant_read_write_data(role)
        self.resources['timeseries_table'].grant_read_write_data(role)
        self.resources['client_config_table'].grant_read_data(role)
        
        # Add permissions for S3
        self.resources['data_lake_bucket'].grant_read_write(role)
        
        # Add permissions for SQS
        self.resources['cost_collection_queue'].grant_send_messages(role)
        self.resources['ai_processing_queue'].grant_send_messages(role)
        
        # Add permissions for SNS
        self.resources['alert_topic'].grant_publish(role)
        
        # Add permissions for Secrets Manager
        for secret in self.resources['provider_secrets'].values():
            secret.grant_read(role)
        
        # Add permissions for KMS
        self.resources['kms_key'].grant_encrypt_decrypt(role)
        
        # Add permissions for provider APIs
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    # AWS Cost Explorer
                    "ce:GetCostAndUsage",
                    "ce:GetCostForecast",
                    "ce:GetUsageForecast",
                    "ce:GetDimensionValues",
                    "ce:GetReservationCoverage",
                    "ce:GetReservationPurchaseRecommendation",
                    "ce:GetReservationUtilization",
                    "ce:GetSavingsPlansUtilization",
                    "ce:GetSavingsPlansCoverage",
                    # CloudWatch metrics
                    "cloudwatch:PutMetricData",
                    # Organizations (for AWS account discovery)
                    "organizations:ListAccounts",
                    "organizations:DescribeOrganization"
                ],
                resources=["*"]
            )
        )
        
        return _lambda.Function(
            self.stack,
            "CostOrchestratorFunction",
            function_name=f"{self.resource_prefix}-cost-orchestrator",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handlers.cost_orchestrator.lambda_handler",
            code=_lambda.Code.from_asset("../src"),
            timeout=Duration.minutes(15),
            memory_size=1024,
            role=role,
            environment={
                "COST_DATA_TABLE": self.resources['cost_data_table'].table_name,
                "TIMESERIES_TABLE": self.resources['timeseries_table'].table_name,
                "CLIENT_CONFIG_TABLE": self.resources['client_config_table'].table_name,
                "DATA_LAKE_BUCKET": self.resources['data_lake_bucket'].bucket_name,
                "COST_COLLECTION_QUEUE": self.resources['cost_collection_queue'].queue_url,
                "AI_PROCESSING_QUEUE": self.resources['ai_processing_queue'].queue_url,
                "ALERT_TOPIC_ARN": self.resources['alert_topic'].topic_arn,
                "KMS_KEY_ID": self.resources['kms_key'].key_id,
                "ENVIRONMENT": self.env_name,
                "AWS_XRAY_TRACING_NAME": f"{self.resource_prefix}-cost-orchestrator"
            },
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=self._get_log_retention_days()
        )

    def create_ai_insights_function(self) -> _lambda.Function:
        """Create Lambda function for AI insights processing"""
        
        # Create execution role
        role = iam.Role(
            self.stack,
            "AIInsightsRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess")
            ]
        )
        
        # Add permissions for DynamoDB
        self.resources['cost_data_table'].grant_read_data(role)
        self.resources['timeseries_table'].grant_read_write_data(role)
        self.resources['client_config_table'].grant_read_data(role)
        
        # Add permissions for S3
        self.resources['data_lake_bucket'].grant_read_write(role)
        self.resources['reports_bucket'].grant_read_write(role)
        
        # Add permissions for SQS
        self.resources['ai_processing_queue'].grant_consume_messages(role)
        
        # Add permissions for SNS
        self.resources['alert_topic'].grant_publish(role)
        self.resources['webhook_topic'].grant_publish(role)
        
        # Add permissions for KMS
        self.resources['kms_key'].grant_encrypt_decrypt(role)
        
        # Add permissions for Bedrock
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.stack.region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                    f"arn:aws:bedrock:{self.stack.region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
                ]
            )
        )
        
        # Add permissions for CloudWatch metrics
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["cloudwatch:PutMetricData"],
                resources=["*"]
            )
        )
        
        return _lambda.Function(
            self.stack,
            "AIInsightsFunction",
            function_name=f"{self.resource_prefix}-ai-insights",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handlers.ai_insights.lambda_handler",
            code=_lambda.Code.from_asset("../src"),
            timeout=Duration.minutes(10),
            memory_size=2048,
            role=role,
            environment={
                "COST_DATA_TABLE": self.resources['cost_data_table'].table_name,
                "TIMESERIES_TABLE": self.resources['timeseries_table'].table_name,
                "CLIENT_CONFIG_TABLE": self.resources['client_config_table'].table_name,
                "DATA_LAKE_BUCKET": self.resources['data_lake_bucket'].bucket_name,
                "REPORTS_BUCKET": self.resources['reports_bucket'].bucket_name,
                "ALERT_TOPIC_ARN": self.resources['alert_topic'].topic_arn,
                "WEBHOOK_TOPIC_ARN": self.resources['webhook_topic'].topic_arn,
                "KMS_KEY_ID": self.resources['kms_key'].key_id,
                "ENVIRONMENT": self.env_name,
                "AWS_XRAY_TRACING_NAME": f"{self.resource_prefix}-ai-insights"
            },
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=self._get_log_retention_days()
        )

    def create_api_handler_function(self) -> _lambda.Function:
        """Create Lambda function for API Gateway integration"""
        
        # Create execution role
        role = iam.Role(
            self.stack,
            "APIHandlerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess")
            ]
        )
        
        # Add permissions for DynamoDB
        self.resources['cost_data_table'].grant_read_data(role)
        self.resources['timeseries_table'].grant_read_data(role)
        self.resources['client_config_table'].grant_read_write_data(role)
        
        # Add permissions for S3
        self.resources['reports_bucket'].grant_read(role)
        
        # Add permissions for SQS
        self.resources['cost_collection_queue'].grant_send_messages(role)
        self.resources['ai_processing_queue'].grant_send_messages(role)
        
        # Add permissions for KMS
        self.resources['kms_key'].grant_encrypt_decrypt(role)
        
        return _lambda.Function(
            self.stack,
            "APIHandlerFunction",
            function_name=f"{self.resource_prefix}-api-handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handlers.api_handler.lambda_handler",
            code=_lambda.Code.from_asset("../src"),
            timeout=Duration.seconds(30),
            memory_size=512,
            role=role,
            environment={
                "COST_DATA_TABLE": self.resources['cost_data_table'].table_name,
                "TIMESERIES_TABLE": self.resources['timeseries_table'].table_name,
                "CLIENT_CONFIG_TABLE": self.resources['client_config_table'].table_name,
                "REPORTS_BUCKET": self.resources['reports_bucket'].bucket_name,
                "COST_COLLECTION_QUEUE": self.resources['cost_collection_queue'].queue_url,
                "AI_PROCESSING_QUEUE": self.resources['ai_processing_queue'].queue_url,
                "KMS_KEY_ID": self.resources['kms_key'].key_id,
                "ENVIRONMENT": self.env_name,
                "JWT_SECRET": self.env_config.jwt_secret,
                "AWS_XRAY_TRACING_NAME": f"{self.resource_prefix}-api-handler"
            },
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=self._get_log_retention_days()
        )

    def create_webhook_handler_function(self) -> _lambda.Function:
        """Create Lambda function for webhook processing"""
        
        # Create execution role
        role = iam.Role(
            self.stack,
            "WebhookHandlerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess")
            ]
        )
        
        # Add permissions for SNS
        self.resources['webhook_topic'].grant_consume_messages(role)
        
        # Add permissions for KMS
        self.resources['kms_key'].grant_encrypt_decrypt(role)
        
        return _lambda.Function(
            self.stack,
            "WebhookHandlerFunction",
            function_name=f"{self.resource_prefix}-webhook-handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handlers.webhook_handler.lambda_handler",
            code=_lambda.Code.from_asset("../src"),
            timeout=Duration.seconds(30),
            memory_size=256,
            role=role,
            environment={
                "WEBHOOK_TOPIC_ARN": self.resources['webhook_topic'].topic_arn,
                "KMS_KEY_ID": self.resources['kms_key'].key_id,
                "ENVIRONMENT": self.env_name,
                "AWS_XRAY_TRACING_NAME": f"{self.resource_prefix}-webhook-handler"
            },
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=self._get_log_retention_days()
        )

    def _get_log_retention_days(self) -> logs.RetentionDays:
        """Get log retention days based on environment configuration"""
        retention_mapping = {
            7: logs.RetentionDays.ONE_WEEK,
            30: logs.RetentionDays.ONE_MONTH,
            90: logs.RetentionDays.THREE_MONTHS,
            365: logs.RetentionDays.ONE_YEAR
        }
        return retention_mapping.get(self.env_config.log_retention_days, logs.RetentionDays.ONE_MONTH)