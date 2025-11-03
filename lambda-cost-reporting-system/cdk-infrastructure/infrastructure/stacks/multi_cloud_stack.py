"""
Multi-Cloud AI Cost Analytics CDK Stack
Enhanced infrastructure for multi-cloud cost analytics with AI capabilities
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_kms as kms,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_logs as logs,
    aws_apigateway as apigateway,
    aws_secretsmanager as secretsmanager,
    aws_xray as xray,
)
from constructs import Construct
from typing import Dict, Any, List
from config.environments import EnvironmentConfig


class MultiCloudAnalyticsStack(Stack):
    """CDK Stack for Multi-Cloud AI Cost Analytics System"""

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        env_config: EnvironmentConfig,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_config = env_config
        self.env_name = env_config.name
        self.resource_prefix = f"multi-cloud-analytics-{env_config.name}"
        
        # Create KMS key for encryption
        self.kms_key = self._create_kms_key()
        
        # Create enhanced DynamoDB tables
        self.cost_data_table = self._create_cost_data_table()
        self.timeseries_table = self._create_timeseries_table()
        self.client_config_table = self._create_client_config_table()
        
        # Create S3 buckets
        self.data_lake_bucket = self._create_data_lake_bucket()
        self.reports_bucket = self._create_reports_bucket()
        
        # Create SQS queues for async processing
        self.cost_collection_queue = self._create_cost_collection_queue()
        self.ai_processing_queue = self._create_ai_processing_queue()
        
        # Create SNS topics for notifications
        self.alert_topic = self._create_alert_topic()
        self.webhook_topic = self._create_webhook_topic()
        
        # Create Secrets Manager for provider credentials
        self.provider_secrets = self._create_provider_secrets()
        
        # Create Lambda functions
        self.cost_orchestrator = self._create_cost_orchestrator_function()
        self.ai_insights_processor = self._create_ai_insights_function()
        self.api_handler = self._create_api_handler_function()
        self.webhook_handler = self._create_webhook_handler_function()
        
        # Create EventBridge rules
        self._create_event_rules()
        
        # Create API Gateway
        self.api_gateway = self._create_api_gateway()
        
        # Create comprehensive monitoring
        self._create_enhanced_monitoring()
        
        # Create X-Ray tracing
        self._enable_xray_tracing()

    def _create_kms_key(self) -> kms.Key:
        """Create KMS key for encrypting sensitive data"""
        return kms.Key(
            self,
            "MultiCloudAnalyticsKey",
            description=f"KMS key for Multi-Cloud Analytics System - {self.env_name}",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY if self.env_config.removal_policy == "DESTROY" else RemovalPolicy.RETAIN
        )    def _cr
eate_cost_data_table(self) -> dynamodb.Table:
        """Create main cost data table with GSI indexes"""
        table = dynamodb.Table(
            self,
            "CostAnalyticsDataTable",
            table_name=f"{self.resource_prefix}-cost-data",
            partition_key=dynamodb.Attribute(
                name="PK",  # CLIENT#{client_id}
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",  # COST#{provider}#{date}
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.kms_key,
            removal_policy=RemovalPolicy.DESTROY if self.env_config.removal_policy == "DESTROY" else RemovalPolicy.RETAIN,
            point_in_time_recovery=self.env_config.enable_point_in_time_recovery,
            time_to_live_attribute="ttl"
        )
        
        # GSI1: Provider-Date index for cross-client queries
        table.add_global_secondary_index(
            index_name="GSI1",
            partition_key=dynamodb.Attribute(
                name="GSI1PK",  # PROVIDER#{provider}
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI1SK",  # DATE#{date}
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # GSI2: Client-Provider index for client-specific provider queries
        table.add_global_secondary_index(
            index_name="GSI2",
            partition_key=dynamodb.Attribute(
                name="GSI2PK",  # CLIENT#{client_id}
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI2SK",  # PROVIDER#{provider}
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        return table

    def _create_timeseries_table(self) -> dynamodb.Table:
        """Create time series table optimized for ML and trend analysis"""
        return dynamodb.Table(
            self,
            "CostTimeseriesTable",
            table_name=f"{self.resource_prefix}-timeseries",
            partition_key=dynamodb.Attribute(
                name="PK",  # TIMESERIES#{client_id}
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",  # DAILY#{date} or HOURLY#{datetime}
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.kms_key,
            removal_policy=RemovalPolicy.DESTROY if self.env_config.removal_policy == "DESTROY" else RemovalPolicy.RETAIN,
            point_in_time_recovery=self.env_config.enable_point_in_time_recovery,
            time_to_live_attribute="ttl"
        )

    def _create_client_config_table(self) -> dynamodb.Table:
        """Create client configuration table"""
        table = dynamodb.Table(
            self,
            "ClientConfigTable",
            table_name=f"{self.resource_prefix}-clients",
            partition_key=dynamodb.Attribute(
                name="client_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.kms_key,
            removal_policy=RemovalPolicy.DESTROY if self.env_config.removal_policy == "DESTROY" else RemovalPolicy.RETAIN,
            point_in_time_recovery=self.env_config.enable_point_in_time_recovery
        )
        
        # GSI for status queries
        table.add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        return table   
 def _create_data_lake_bucket(self) -> s3.Bucket:
        """Create S3 bucket for data lake storage"""
        return s3.Bucket(
            self,
            "DataLakeBucket",
            bucket_name=f"{self.resource_prefix}-data-lake-{self.account}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.kms_key,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="TransitionToIA",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=Duration.days(365)
                        )
                    ]
                )
            ],
            removal_policy=RemovalPolicy.DESTROY if self.env_config.removal_policy == "DESTROY" else RemovalPolicy.RETAIN,
            auto_delete_objects=self.env_config.removal_policy == "DESTROY"
        )

    def _create_reports_bucket(self) -> s3.Bucket:
        """Create S3 bucket for reports and assets"""
        return s3.Bucket(
            self,
            "ReportsBucket",
            bucket_name=f"{self.resource_prefix}-reports-{self.account}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.kms_key,
            versioned=False,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldReports",
                    enabled=True,
                    expiration=Duration.days(90)
                )
            ],
            removal_policy=RemovalPolicy.DESTROY if self.env_config.removal_policy == "DESTROY" else RemovalPolicy.RETAIN,
            auto_delete_objects=self.env_config.removal_policy == "DESTROY"
        )

    def _create_cost_collection_queue(self) -> sqs.Queue:
        """Create SQS queue for cost collection tasks"""
        dlq = sqs.Queue(
            self,
            "CostCollectionDLQ",
            queue_name=f"{self.resource_prefix}-cost-collection-dlq",
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.kms_key,
            retention_period=Duration.days(14)
        )
        
        return sqs.Queue(
            self,
            "CostCollectionQueue",
            queue_name=f"{self.resource_prefix}-cost-collection",
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.kms_key,
            visibility_timeout=Duration.minutes(15),
            message_retention_period=Duration.days(7),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dlq
            )
        )

    def _create_ai_processing_queue(self) -> sqs.Queue:
        """Create SQS queue for AI processing tasks"""
        dlq = sqs.Queue(
            self,
            "AIProcessingDLQ",
            queue_name=f"{self.resource_prefix}-ai-processing-dlq",
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.kms_key,
            retention_period=Duration.days(14)
        )
        
        return sqs.Queue(
            self,
            "AIProcessingQueue",
            queue_name=f"{self.resource_prefix}-ai-processing",
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.kms_key,
            visibility_timeout=Duration.minutes(10),
            message_retention_period=Duration.days(7),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dlq
            )
        )   
 def _create_alert_topic(self) -> sns.Topic:
        """Create SNS topic for alerts and notifications"""
        return sns.Topic(
            self,
            "AlertTopic",
            topic_name=f"{self.resource_prefix}-alerts",
            display_name="Multi-Cloud Analytics Alerts",
            master_key=self.kms_key
        )

    def _create_webhook_topic(self) -> sns.Topic:
        """Create SNS topic for webhook notifications"""
        return sns.Topic(
            self,
            "WebhookTopic",
            topic_name=f"{self.resource_prefix}-webhooks",
            display_name="Multi-Cloud Analytics Webhooks",
            master_key=self.kms_key
        )

    def _create_provider_secrets(self) -> Dict[str, secretsmanager.Secret]:
        """Create Secrets Manager secrets for provider credentials"""
        secrets = {}
        
        providers = ["aws", "gcp", "azure"]
        for provider in providers:
            secret = secretsmanager.Secret(
                self,
                f"{provider.upper()}ProviderSecret",
                secret_name=f"{self.resource_prefix}-{provider}-credentials",
                description=f"{provider.upper()} provider credentials for multi-cloud analytics",
                encryption_key=self.kms_key,
                generate_secret_string=secretsmanager.SecretStringGenerator(
                    secret_string_template='{"provider": "' + provider + '"}',
                    generate_string_key="credentials",
                    exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\",
                    include_space=False,
                    password_length=32
                )
            )
            secrets[provider] = secret
            
        return secrets    def 
_create_cost_orchestrator_function(self) -> _lambda.Function:
        """Create Lambda function for cost collection orchestration"""
        from .lambda_functions import LambdaFunctions
        
        resources = {
            'cost_data_table': self.cost_data_table,
            'timeseries_table': self.timeseries_table,
            'client_config_table': self.client_config_table,
            'data_lake_bucket': self.data_lake_bucket,
            'cost_collection_queue': self.cost_collection_queue,
            'ai_processing_queue': self.ai_processing_queue,
            'alert_topic': self.alert_topic,
            'provider_secrets': self.provider_secrets,
            'kms_key': self.kms_key
        }
        
        lambda_functions = LambdaFunctions(self, self.env_config, resources)
        return lambda_functions.create_cost_orchestrator_function()

    def _create_ai_insights_function(self) -> _lambda.Function:
        """Create Lambda function for AI insights processing"""
        from .lambda_functions import LambdaFunctions
        
        resources = {
            'cost_data_table': self.cost_data_table,
            'timeseries_table': self.timeseries_table,
            'client_config_table': self.client_config_table,
            'data_lake_bucket': self.data_lake_bucket,
            'reports_bucket': self.reports_bucket,
            'ai_processing_queue': self.ai_processing_queue,
            'alert_topic': self.alert_topic,
            'webhook_topic': self.webhook_topic,
            'kms_key': self.kms_key
        }
        
        lambda_functions = LambdaFunctions(self, self.env_config, resources)
        return lambda_functions.create_ai_insights_function()

    def _create_api_handler_function(self) -> _lambda.Function:
        """Create Lambda function for API Gateway integration"""
        from .lambda_functions import LambdaFunctions
        
        resources = {
            'cost_data_table': self.cost_data_table,
            'timeseries_table': self.timeseries_table,
            'client_config_table': self.client_config_table,
            'reports_bucket': self.reports_bucket,
            'cost_collection_queue': self.cost_collection_queue,
            'ai_processing_queue': self.ai_processing_queue,
            'kms_key': self.kms_key
        }
        
        lambda_functions = LambdaFunctions(self, self.env_config, resources)
        return lambda_functions.create_api_handler_function()

    def _create_webhook_handler_function(self) -> _lambda.Function:
        """Create Lambda function for webhook processing"""
        from .lambda_functions import LambdaFunctions
        
        resources = {
            'webhook_topic': self.webhook_topic,
            'kms_key': self.kms_key
        }
        
        lambda_functions = LambdaFunctions(self, self.env_config, resources)
        return lambda_functions.create_webhook_handler_function() 
   def _create_event_rules(self) -> None:
        """Create EventBridge rules for scheduling"""
        
        # Daily cost collection - Every day at 6 AM UTC
        daily_rule = events.Rule(
            self,
            "DailyCostCollectionRule",
            rule_name=f"{self.resource_prefix}-daily-collection",
            description="Trigger daily cost collection for all providers",
            schedule=events.Schedule.cron(
                minute="0",
                hour="6"
            )
        )
        
        daily_rule.add_target(
            targets.LambdaFunction(
                self.cost_orchestrator,
                event=events.RuleTargetInput.from_object({
                    "collection_type": "daily",
                    "providers": ["aws", "gcp", "azure"],
                    "source": "eventbridge"
                })
            )
        )
        
        # Weekly AI insights - Every Monday at 8 AM UTC
        weekly_ai_rule = events.Rule(
            self,
            "WeeklyAIInsightsRule",
            rule_name=f"{self.resource_prefix}-weekly-ai",
            description="Trigger weekly AI insights generation",
            schedule=events.Schedule.cron(
                minute="0",
                hour="8",
                week_day="MON"
            )
        )
        
        weekly_ai_rule.add_target(
            targets.LambdaFunction(
                self.ai_insights_processor,
                event=events.RuleTargetInput.from_object({
                    "analysis_type": "weekly",
                    "include_forecasting": True,
                    "source": "eventbridge"
                })
            )
        )
        
        # Monthly comprehensive analysis - First day of month at 9 AM UTC
        monthly_rule = events.Rule(
            self,
            "MonthlyAnalysisRule",
            rule_name=f"{self.resource_prefix}-monthly-analysis",
            description="Trigger monthly comprehensive analysis",
            schedule=events.Schedule.cron(
                minute="0",
                hour="9",
                day="1"
            )
        )
        
        monthly_rule.add_target(
            targets.LambdaFunction(
                self.ai_insights_processor,
                event=events.RuleTargetInput.from_object({
                    "analysis_type": "monthly",
                    "include_forecasting": True,
                    "include_recommendations": True,
                    "source": "eventbridge"
                })
            )
        )
        
        # SQS event sources for Lambda functions
        self.ai_insights_processor.add_event_source(
            _lambda.SqsEventSource(
                self.ai_processing_queue,
                batch_size=5,
                max_batching_window=Duration.seconds(30)
            )
        )    def _c
reate_api_gateway(self) -> apigateway.RestApi:
        """Create API Gateway for REST API"""
        
        api = apigateway.RestApi(
            self,
            "MultiCloudAnalyticsAPI",
            rest_api_name=f"{self.resource_prefix}-api",
            description="Multi-Cloud AI Cost Analytics API",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=self.env_config.cors_allowed_origins,
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key", "X-Amz-Security-Token", "x-request-id"]
            ),
            deploy_options=apigateway.StageOptions(
                stage_name=self.env_name,
                throttling_rate_limit=self.env_config.api_throttle_rate_limit,
                throttling_burst_limit=self.env_config.api_throttle_burst_limit,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
                tracing_enabled=True
            )
        )
        
        # Create Lambda integration
        lambda_integration = apigateway.LambdaIntegration(
            self.api_handler,
            proxy=True,
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'"
                    }
                )
            ]
        )
        
        # Add API resources
        v1 = api.root.add_resource("v1")
        
        # Cost data endpoints
        costs = v1.add_resource("costs")
        costs.add_method("GET", lambda_integration)
        
        cost_by_id = costs.add_resource("{client_id}")
        cost_by_id.add_method("GET", lambda_integration)
        
        # AI insights endpoints
        insights = v1.add_resource("insights")
        insights.add_method("GET", lambda_integration)
        insights.add_method("POST", lambda_integration)
        
        # Client management endpoints
        clients = v1.add_resource("clients")
        clients.add_method("GET", lambda_integration)
        clients.add_method("POST", lambda_integration)
        
        client_by_id = clients.add_resource("{client_id}")
        client_by_id.add_method("GET", lambda_integration)
        client_by_id.add_method("PUT", lambda_integration)
        client_by_id.add_method("DELETE", lambda_integration)
        
        # Webhook endpoints
        webhooks = v1.add_resource("webhooks")
        webhooks.add_method("POST", apigateway.LambdaIntegration(self.webhook_handler))
        
        return api  
  def _create_enhanced_monitoring(self) -> None:
        """Create comprehensive CloudWatch monitoring and dashboards"""
        from .monitoring import MonitoringComponents
        
        resources = {
            'cost_orchestrator': self.cost_orchestrator,
            'ai_insights_processor': self.ai_insights_processor,
            'api_handler': self.api_handler,
            'webhook_handler': self.webhook_handler,
            'alert_topic': self.alert_topic,
            'cost_collection_queue': self.cost_collection_queue,
            'ai_processing_queue': self.ai_processing_queue,
            'cost_data_table': self.cost_data_table,
            'timeseries_table': self.timeseries_table
        }
        
        monitoring = MonitoringComponents(self, self.env_config, resources)
        monitoring.create_enhanced_monitoring()

    def _enable_xray_tracing(self) -> None:
        """Enable X-Ray tracing for distributed tracing"""
        # X-Ray is already enabled on Lambda functions via tracing=_lambda.Tracing.ACTIVE
        # This method can be extended to add additional X-Ray configuration if needed
        pass

    def _get_log_retention_days(self) -> logs.RetentionDays:
        """Get log retention days based on environment configuration"""
        retention_mapping = {
            7: logs.RetentionDays.ONE_WEEK,
            30: logs.RetentionDays.ONE_MONTH,
            90: logs.RetentionDays.THREE_MONTHS,
            365: logs.RetentionDays.ONE_YEAR
        }
        return retention_mapping.get(self.env_config.log_retention_days, logs.RetentionDays.ONE_MONTH)

    @property
    def namespace(self) -> str:
        """CloudWatch namespace for custom metrics"""
        return f"MultiCloudAnalytics/{self.env_name.title()}"