"""
Main CDK stack for Lambda Cost Reporting System
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    BundlingOptions,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_kms as kms,
    aws_sns as sns,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_logs as logs,
)
from constructs import Construct
from typing import Dict, Any
from config.environments import EnvironmentConfig


class CostReportingStack(Stack):
    """CDK Stack for Lambda Cost Reporting System"""

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
        self.resource_prefix = f"cost-reporting-{env_config.name}"
        
        # Create KMS key for encryption
        self.kms_key = self._create_kms_key()
        
        # Create DynamoDB table for client configurations
        self.dynamodb_table = self._create_dynamodb_table()
        
        # Create DynamoDB table for alarms
        self.alarms_table = self._create_alarms_table()
        
        # Create S3 bucket for reports and assets
        self.s3_bucket = self._create_s3_bucket()
        
        # Create SNS topic for alerts
        self.sns_topic = self._create_sns_topic()
        
        # Create Lambda function
        self.lambda_function = self._create_lambda_function()
        
        # Create EventBridge rules for scheduling
        self.create_event_rules()
        
        # Create CloudWatch alarms
        self._create_cloudwatch_alarms()
        
        # Create CloudWatch dashboards
        self._create_cloudwatch_dashboards()

    def _create_kms_key(self) -> kms.Key:
        """Create KMS key for encrypting sensitive data"""
        return kms.Key(
            self,
            "CostReportingKey",
            description=f"KMS key for Lambda Cost Reporting System - {self.env_name}",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY if self.env_config.removal_policy == "DESTROY" else RemovalPolicy.RETAIN
        )

    def _create_dynamodb_table(self) -> dynamodb.Table:
        """Create DynamoDB table for client configurations"""
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
        
        # Add GSI for status queries
        table.add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        return table

    def _create_s3_bucket(self) -> s3.Bucket:
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
                    expiration=Duration.days(30)  # Delete reports after 30 days
                )
            ],
            removal_policy=RemovalPolicy.DESTROY if self.env_config.removal_policy == "DESTROY" else RemovalPolicy.RETAIN,
            auto_delete_objects=self.env_config.removal_policy == "DESTROY"
        )

    def _create_alarms_table(self) -> dynamodb.Table:
        """Create DynamoDB table for alarms"""
        return dynamodb.Table(
            self,
            "AlarmsTable",
            table_name="costhub-alarms",
            partition_key=dynamodb.Attribute(
                name="alarm_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.DESTROY if self.env_config.removal_policy == "DESTROY" else RemovalPolicy.RETAIN
        )

    def _create_lambda_function(self) -> _lambda.Function:
        """Create Lambda function for cost reporting"""
        
        # Create Lambda execution role
        lambda_role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Add permissions for DynamoDB
        self.dynamodb_table.grant_read_write_data(lambda_role)
        self.alarms_table.grant_read_write_data(lambda_role)
        
        # Add permissions for S3
        self.s3_bucket.grant_read_write(lambda_role)
        
        # Add permissions for KMS
        self.kms_key.grant_encrypt_decrypt(lambda_role)
        
        # Add permissions for SES
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                resources=["*"]
            )
        )
        
        # Add permissions for Cost Explorer
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ce:GetCostAndUsage",
                    "ce:GetCostForecast",
                    "ce:GetUsageForecast"
                ],
                resources=["*"]
            )
        )
        
        # Add permissions for CloudWatch metrics
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudwatch:PutMetricData"
                ],
                resources=["*"]
            )
        )
        
        # Add permissions for SNS alerts
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sns:Publish"
                ],
                resources=[self.sns_topic.topic_arn]
            )
        )
        
        # Use AWS Lambda Powertools Layer (public layer)
        powertools_layer = _lambda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            layer_version_arn=f"arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:59"
        )
        
        # Create Lambda function
        lambda_function = _lambda.Function(
            self,
            "CostReportingFunction",
            function_name=f"{self.resource_prefix}-handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="simple_handler.lambda_handler",
            code=_lambda.Code.from_asset("../src"),
            layers=[powertools_layer],
            timeout=Duration.minutes(self.env_config.lambda_timeout_minutes),
            memory_size=self.env_config.lambda_memory,
            role=lambda_role,
            environment={
                "DYNAMODB_TABLE_NAME": self.dynamodb_table.table_name,
                "S3_BUCKET_NAME": self.s3_bucket.bucket_name,
                "KMS_KEY_ID": self.kms_key.key_id,
                "ENVIRONMENT": self.env_name,
                "SNS_ALERT_TOPIC_ARN": self.sns_topic.topic_arn
            },
            log_retention=self._get_log_retention_days()
        )
        
        return lambda_function

    def create_event_rules(self) -> None:
        """Create EventBridge rules for scheduling"""
        
        # Weekly reports - Every Monday at 9 AM UTC
        weekly_rule = events.Rule(
            self,
            "WeeklyReportRule",
            rule_name=f"{self.resource_prefix}-weekly",
            description="Trigger weekly cost reports",
            schedule=events.Schedule.cron(
                minute="0",
                hour="9",
                week_day="MON"
            )
        )
        
        weekly_rule.add_target(
            targets.LambdaFunction(
                self.lambda_function,
                event=events.RuleTargetInput.from_object({
                    "report_type": "weekly",
                    "source": "eventbridge"
                })
            )
        )
        
        # Monthly reports - First day of month at 8 AM UTC
        monthly_rule = events.Rule(
            self,
            "MonthlyReportRule",
            rule_name=f"{self.resource_prefix}-monthly",
            description="Trigger monthly cost reports",
            schedule=events.Schedule.cron(
                minute="0",
                hour="8",
                day="1"
            )
        )
        
        monthly_rule.add_target(
            targets.LambdaFunction(
                self.lambda_function,
                event=events.RuleTargetInput.from_object({
                    "report_type": "monthly",
                    "source": "eventbridge"
                })
            )
        )

    def _create_sns_topic(self) -> sns.Topic:
        """Create SNS topic for admin alerts"""
        return sns.Topic(
            self,
            "AdminAlertsTopic",
            topic_name=f"{self.resource_prefix}-admin-alerts",
            display_name="Cost Reporting Admin Alerts",
            master_key=self.kms_key
        )

    def _create_cloudwatch_alarms(self) -> None:
        """Create comprehensive CloudWatch alarms for monitoring"""
        
        # Lambda errors alarm
        errors_alarm = cloudwatch.Alarm(
            self,
            "LambdaErrorsAlarm",
            alarm_name=f"{self.resource_prefix}-lambda-errors",
            alarm_description="Lambda function errors",
            metric=self.lambda_function.metric_errors(
                period=Duration.minutes(5),
                statistic="Sum"
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
        )
        
        errors_alarm.add_alarm_action(
            cw_actions.SnsAction(self.sns_topic)
        )
        
        # Lambda duration alarm
        duration_alarm = cloudwatch.Alarm(
            self,
            "LambdaDurationAlarm",
            alarm_name=f"{self.resource_prefix}-lambda-duration",
            alarm_description="Lambda function duration approaching timeout",
            metric=self.lambda_function.metric_duration(
                period=Duration.minutes(5),
                statistic="Average"
            ),
            threshold=Duration.minutes(10).to_milliseconds(),
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )
        
        duration_alarm.add_alarm_action(
            cw_actions.SnsAction(self.sns_topic)
        )
        
        # Lambda throttles alarm
        throttles_alarm = cloudwatch.Alarm(
            self,
            "LambdaThrottlesAlarm",
            alarm_name=f"{self.resource_prefix}-lambda-throttles",
            alarm_description="Lambda function throttles",
            metric=self.lambda_function.metric_throttles(
                period=Duration.minutes(5),
                statistic="Sum"
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
        )
        
        throttles_alarm.add_alarm_action(
            cw_actions.SnsAction(self.sns_topic)
        )
        
        # Custom metric alarms for business logic
        
        # Client success rate alarm
        client_success_rate_alarm = cloudwatch.Alarm(
            self,
            "ClientSuccessRateAlarm",
            alarm_name=f"{self.resource_prefix}-client-success-rate",
            alarm_description="Client processing success rate below threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="ClientSuccessRate",
                statistic="Average",
                period=Duration.minutes(15)
            ),
            threshold=80,  # 80% success rate threshold
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        client_success_rate_alarm.add_alarm_action(
            cw_actions.SnsAction(self.sns_topic)
        )
        
        # Execution failures alarm
        execution_failures_alarm = cloudwatch.Alarm(
            self,
            "ExecutionFailuresAlarm",
            alarm_name=f"{self.resource_prefix}-execution-failures",
            alarm_description="Multiple execution failures detected",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="ExecutionFailed",
                statistic="Sum",
                period=Duration.minutes(30)
            ),
            threshold=2,  # 2 failures in 30 minutes
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
        )
        
        execution_failures_alarm.add_alarm_action(
            cw_actions.SnsAction(self.sns_topic)
        )
        
        # Email delivery failure alarm
        email_failure_alarm = cloudwatch.Alarm(
            self,
            "EmailDeliveryFailureAlarm",
            alarm_name=f"{self.resource_prefix}-email-failures",
            alarm_description="High email delivery failure rate",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="OperationFailure",
                dimensions_map={"Operation": "email_delivery"},
                statistic="Sum",
                period=Duration.minutes(15)
            ),
            threshold=3,  # 3 email failures in 15 minutes
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
        )
        
        email_failure_alarm.add_alarm_action(
            cw_actions.SnsAction(self.sns_topic)
        )
        
        # Component error alarm for critical components
        component_error_alarm = cloudwatch.Alarm(
            self,
            "ComponentErrorAlarm",
            alarm_name=f"{self.resource_prefix}-component-errors",
            alarm_description="Critical component errors detected",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="ComponentError",
                dimensions_map={"Severity": "CRITICAL"},
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
        )
        
        component_error_alarm.add_alarm_action(
            cw_actions.SnsAction(self.sns_topic)
        )
    
    def _create_cloudwatch_dashboards(self) -> None:
        """Create comprehensive CloudWatch dashboards for monitoring"""
        
        # Operational Dashboard
        operational_dashboard = cloudwatch.Dashboard(
            self,
            "OperationalDashboard",
            dashboard_name=f"{self.resource_prefix}-operational",
            period_override=cloudwatch.PeriodOverride.AUTO,
            start="-PT24H",  # Last 24 hours
            widgets=[
                # Row 1: Lambda Function Health
                [
                    # Lambda Invocations
                    cloudwatch.GraphWidget(
                        title="Lambda Invocations",
                        left=[
                            self.lambda_function.metric_invocations(
                                period=Duration.minutes(5),
                                statistic="Sum"
                            )
                        ],
                        width=8,
                        height=6
                    ),
                    # Lambda Errors
                    cloudwatch.GraphWidget(
                        title="Lambda Errors",
                        left=[
                            self.lambda_function.metric_errors(
                                period=Duration.minutes(5),
                                statistic="Sum"
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0),
                        width=8,
                        height=6
                    ),
                    # Lambda Duration
                    cloudwatch.GraphWidget(
                        title="Lambda Duration",
                        left=[
                            self.lambda_function.metric_duration(
                                period=Duration.minutes(5),
                                statistic="Average"
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(
                            label="Duration (ms)",
                            min=0
                        ),
                        width=8,
                        height=6
                    )
                ],
                # Row 2: Execution Metrics
                [
                    # Execution Success/Failure
                    cloudwatch.GraphWidget(
                        title="Execution Results",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ExecutionSucceeded",
                                statistic="Sum",
                                period=Duration.minutes(15),
                                label="Successful"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ExecutionFailed",
                                statistic="Sum",
                                period=Duration.minutes(15),
                                label="Failed"
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    # Client Success Rate
                    cloudwatch.GraphWidget(
                        title="Client Success Rate",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ClientSuccessRate",
                                statistic="Average",
                                period=Duration.minutes(15)
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(
                            label="Success Rate (%)",
                            min=0,
                            max=100
                        ),
                        width=12,
                        height=6
                    )
                ],
                # Row 3: Component Performance
                [
                    # Operation Duration by Component
                    cloudwatch.GraphWidget(
                        title="Operation Duration by Component",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="OperationDuration",
                                dimensions_map={"Operation": "cost_collection"},
                                statistic="Average",
                                period=Duration.minutes(15),
                                label="Cost Collection"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="OperationDuration",
                                dimensions_map={"Operation": "report_generation"},
                                statistic="Average",
                                period=Duration.minutes(15),
                                label="Report Generation"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="OperationDuration",
                                dimensions_map={"Operation": "email_delivery"},
                                statistic="Average",
                                period=Duration.minutes(15),
                                label="Email Delivery"
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(
                            label="Duration (seconds)",
                            min=0
                        ),
                        width=12,
                        height=6
                    ),
                    # Component Errors
                    cloudwatch.GraphWidget(
                        title="Component Errors",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ComponentError",
                                dimensions_map={"Component": "cost_agent"},
                                statistic="Sum",
                                period=Duration.minutes(15),
                                label="Cost Agent"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ComponentError",
                                dimensions_map={"Component": "report_generator"},
                                statistic="Sum",
                                period=Duration.minutes(15),
                                label="Report Generator"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ComponentError",
                                dimensions_map={"Component": "email_service"},
                                statistic="Sum",
                                period=Duration.minutes(15),
                                label="Email Service"
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0),
                        width=12,
                        height=6
                    )
                ],
                # Row 4: Resource Utilization
                [
                    # DynamoDB Metrics
                    cloudwatch.GraphWidget(
                        title="DynamoDB Operations",
                        left=[
                            cloudwatch.Metric(
                                namespace="AWS/DynamoDB",
                                metric_name="ConsumedReadCapacityUnits",
                                dimensions_map={"TableName": self.dynamodb_table.table_name},
                                statistic="Sum",
                                period=Duration.minutes(5),
                                label="Read Capacity"
                            ),
                            cloudwatch.Metric(
                                namespace="AWS/DynamoDB",
                                metric_name="ConsumedWriteCapacityUnits",
                                dimensions_map={"TableName": self.dynamodb_table.table_name},
                                statistic="Sum",
                                period=Duration.minutes(5),
                                label="Write Capacity"
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    # S3 Metrics
                    cloudwatch.GraphWidget(
                        title="S3 Operations",
                        left=[
                            cloudwatch.Metric(
                                namespace="AWS/S3",
                                metric_name="NumberOfObjects",
                                dimensions_map={"BucketName": self.s3_bucket.bucket_name, "StorageType": "AllStorageTypes"},
                                statistic="Average",
                                period=Duration.hours(1),
                                label="Object Count"
                            )
                        ],
                        width=12,
                        height=6
                    )
                ]
            ]
        )
        
        # Business Dashboard
        business_dashboard = cloudwatch.Dashboard(
            self,
            "BusinessDashboard",
            dashboard_name=f"{self.resource_prefix}-business",
            period_override=cloudwatch.PeriodOverride.AUTO,
            start="-P7D",  # Last 7 days
            widgets=[
                # Row 1: Business KPIs
                [
                    # Reports Generated
                    cloudwatch.SingleValueWidget(
                        title="Reports Generated (24h)",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ReportsGenerated",
                                statistic="Sum",
                                period=Duration.hours(24)
                            )
                        ],
                        width=6,
                        height=6
                    ),
                    # Emails Sent
                    cloudwatch.SingleValueWidget(
                        title="Emails Sent (24h)",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="EmailsSent",
                                statistic="Sum",
                                period=Duration.hours(24)
                            )
                        ],
                        width=6,
                        height=6
                    ),
                    # Active Clients
                    cloudwatch.SingleValueWidget(
                        title="Clients Processed (24h)",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ClientsProcessed",
                                statistic="Sum",
                                period=Duration.hours(24)
                            )
                        ],
                        width=6,
                        height=6
                    ),
                    # Success Rate
                    cloudwatch.SingleValueWidget(
                        title="Success Rate (24h)",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ClientSuccessRate",
                                statistic="Average",
                                period=Duration.hours(24)
                            )
                        ],
                        width=6,
                        height=6
                    )
                ],
                # Row 2: Trends
                [
                    # Daily Reports Trend
                    cloudwatch.GraphWidget(
                        title="Daily Reports Generated",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ReportsGenerated",
                                statistic="Sum",
                                period=Duration.hours(24)
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    # Client Processing Trend
                    cloudwatch.GraphWidget(
                        title="Client Processing Trend",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ClientsSucceeded",
                                statistic="Sum",
                                period=Duration.hours(24),
                                label="Successful"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ClientsFailed",
                                statistic="Sum",
                                period=Duration.hours(24),
                                label="Failed"
                            )
                        ],
                        width=12,
                        height=6
                    )
                ],
                # Row 3: Performance Metrics
                [
                    # Average Execution Duration
                    cloudwatch.GraphWidget(
                        title="Average Execution Duration",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ExecutionDuration",
                                statistic="Average",
                                period=Duration.hours(1)
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(
                            label="Duration (seconds)",
                            min=0
                        ),
                        width=12,
                        height=6
                    ),
                    # Email Recipients
                    cloudwatch.GraphWidget(
                        title="Email Recipients per Execution",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="EmailRecipients",
                                statistic="Sum",
                                period=Duration.hours(1)
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0),
                        width=12,
                        height=6
                    )
                ],
                # Row 4: Error Analysis
                [
                    # Error Distribution by Severity
                    cloudwatch.GraphWidget(
                        title="Errors by Severity",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ComponentError",
                                dimensions_map={"Severity": "LOW"},
                                statistic="Sum",
                                period=Duration.hours(1),
                                label="Low"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ComponentError",
                                dimensions_map={"Severity": "MEDIUM"},
                                statistic="Sum",
                                period=Duration.hours(1),
                                label="Medium"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ComponentError",
                                dimensions_map={"Severity": "HIGH"},
                                statistic="Sum",
                                period=Duration.hours(1),
                                label="High"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ComponentError",
                                dimensions_map={"Severity": "CRITICAL"},
                                statistic="Sum",
                                period=Duration.hours(1),
                                label="Critical"
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0),
                        width=24,
                        height=6
                    )
                ]
            ]
        )
        
        # System Health Dashboard
        health_dashboard = cloudwatch.Dashboard(
            self,
            "SystemHealthDashboard",
            dashboard_name=f"{self.resource_prefix}-health",
            period_override=cloudwatch.PeriodOverride.AUTO,
            start="-PT6H",  # Last 6 hours
            widgets=[
                # Row 1: System Status
                [
                    # Lambda Health
                    cloudwatch.SingleValueWidget(
                        title="Lambda Error Rate",
                        metrics=[
                            cloudwatch.MathExpression(
                                expression="errors / invocations * 100",
                                using_metrics={
                                    "errors": self.lambda_function.metric_errors(
                                        period=Duration.minutes(30),
                                        statistic="Sum"
                                    ),
                                    "invocations": self.lambda_function.metric_invocations(
                                        period=Duration.minutes(30),
                                        statistic="Sum"
                                    )
                                },
                                label="Error Rate (%)"
                            )
                        ],
                        width=8,
                        height=6
                    ),
                    # DynamoDB Throttles
                    cloudwatch.SingleValueWidget(
                        title="DynamoDB Throttles",
                        metrics=[
                            cloudwatch.Metric(
                                namespace="AWS/DynamoDB",
                                metric_name="ReadThrottles",
                                dimensions_map={"TableName": self.dynamodb_table.table_name},
                                statistic="Sum",
                                period=Duration.minutes(30)
                            )
                        ],
                        width=8,
                        height=6
                    ),
                    # S3 Errors
                    cloudwatch.SingleValueWidget(
                        title="S3 4xx Errors",
                        metrics=[
                            cloudwatch.Metric(
                                namespace="AWS/S3",
                                metric_name="4xxErrors",
                                dimensions_map={"BucketName": self.s3_bucket.bucket_name},
                                statistic="Sum",
                                period=Duration.minutes(30)
                            )
                        ],
                        width=8,
                        height=6
                    )
                ],
                # Row 2: System Health Summary
                [
                    # System Health Status
                    cloudwatch.SingleValueWidget(
                        title="System Health Score",
                        metrics=[
                            cloudwatch.MathExpression(
                                expression="100 - (errors / invocations * 100)",
                                using_metrics={
                                    "errors": self.lambda_function.metric_errors(
                                        period=Duration.hours(1),
                                        statistic="Sum"
                                    ),
                                    "invocations": self.lambda_function.metric_invocations(
                                        period=Duration.hours(1),
                                        statistic="Sum"
                                    )
                                },
                                label="Health Score (%)"
                            )
                        ],
                        width=24,
                        height=6
                    )
                ]
            ]
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

    @property
    def namespace(self) -> str:
        """CloudWatch namespace for custom metrics"""
        return f"CostReporting/{self.env_name.title()}"