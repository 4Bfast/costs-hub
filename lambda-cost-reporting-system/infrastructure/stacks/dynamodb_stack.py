"""
DynamoDB Stack for Multi-Cloud Cost Analytics

This CDK stack defines the DynamoDB tables and related infrastructure
for the multi-cloud cost analytics platform.
"""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
    CfnOutput
)
from constructs import Construct
from typing import Dict, Any


class DynamoDBStack(Stack):
    """CDK Stack for DynamoDB tables and related infrastructure."""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create the main cost analytics table
        self.cost_analytics_table = self._create_cost_analytics_table()
        
        # Create the time series table
        self.timeseries_table = self._create_timeseries_table()
        
        # Create CloudWatch alarms for monitoring
        self._create_cloudwatch_alarms()
        
        # Create IAM roles and policies
        self._create_iam_resources()
        
        # Create outputs
        self._create_outputs()
    
    def _create_cost_analytics_table(self) -> dynamodb.Table:
        """Create the main cost analytics data table."""
        table = dynamodb.Table(
            self, "CostAnalyticsTable",
            table_name="cost-analytics-data",
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            time_to_live_attribute="ttl",
            table_class=dynamodb.TableClass.STANDARD
        )
        
        # Add Global Secondary Index 1: Provider-Date index
        table.add_global_secondary_index(
            index_name="GSI1-ProviderDate",
            partition_key=dynamodb.Attribute(
                name="GSI1PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI1SK",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # Add Global Secondary Index 2: Client-Provider index
        table.add_global_secondary_index(
            index_name="GSI2-ClientProvider",
            partition_key=dynamodb.Attribute(
                name="GSI2PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI2SK",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # Add tags
        table.node.add_metadata("Environment", "production")
        table.node.add_metadata("Service", "multi-cloud-cost-analytics")
        table.node.add_metadata("Purpose", "cost-data-storage")
        
        return table
    
    def _create_timeseries_table(self) -> dynamodb.Table:
        """Create the time series table optimized for ML analysis."""
        table = dynamodb.Table(
            self, "TimeSeriesTable",
            table_name="cost-analytics-timeseries",
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            time_to_live_attribute="ttl",
            table_class=dynamodb.TableClass.STANDARD
        )
        
        # Add Global Secondary Index: Date-based index for cross-client analysis
        table.add_global_secondary_index(
            index_name="GSI1-DateIndex",
            partition_key=dynamodb.Attribute(
                name="GSI1PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI1SK",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # Add tags
        table.node.add_metadata("Environment", "production")
        table.node.add_metadata("Service", "multi-cloud-cost-analytics")
        table.node.add_metadata("Purpose", "timeseries-ml-data")
        
        return table
    
    def _create_cloudwatch_alarms(self) -> None:
        """Create CloudWatch alarms for monitoring table health."""
        
        # Cost Analytics Table Alarms
        cost_table_throttle_alarm = cloudwatch.Alarm(
            self, "CostTableThrottleAlarm",
            alarm_name="cost-analytics-table-throttles",
            alarm_description="Alarm when cost analytics table experiences throttling",
            metric=self.cost_analytics_table.metric_throttled_requests_for_table(),
            threshold=5,
            evaluation_periods=2,
            datapoints_to_alarm=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        cost_table_error_alarm = cloudwatch.Alarm(
            self, "CostTableErrorAlarm",
            alarm_name="cost-analytics-table-errors",
            alarm_description="Alarm when cost analytics table experiences errors",
            metric=self.cost_analytics_table.metric_system_errors_for_table(),
            threshold=10,
            evaluation_periods=2,
            datapoints_to_alarm=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Time Series Table Alarms
        timeseries_throttle_alarm = cloudwatch.Alarm(
            self, "TimeSeriesThrottleAlarm",
            alarm_name="timeseries-table-throttles",
            alarm_description="Alarm when time series table experiences throttling",
            metric=self.timeseries_table.metric_throttled_requests_for_table(),
            threshold=5,
            evaluation_periods=2,
            datapoints_to_alarm=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        timeseries_error_alarm = cloudwatch.Alarm(
            self, "TimeSeriesErrorAlarm",
            alarm_name="timeseries-table-errors",
            alarm_description="Alarm when time series table experiences errors",
            metric=self.timeseries_table.metric_system_errors_for_table(),
            threshold=10,
            evaluation_periods=2,
            datapoints_to_alarm=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
    
    def _create_iam_resources(self) -> None:
        """Create IAM roles and policies for DynamoDB access."""
        
        # Create a role for Lambda functions to access DynamoDB
        self.lambda_dynamodb_role = iam.Role(
            self, "LambdaDynamoDBRole",
            role_name="multi-cloud-cost-analytics-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Create policy for DynamoDB access
        dynamodb_policy = iam.Policy(
            self, "DynamoDBAccessPolicy",
            policy_name="multi-cloud-cost-analytics-dynamodb-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem"
                    ],
                    resources=[
                        self.cost_analytics_table.table_arn,
                        f"{self.cost_analytics_table.table_arn}/index/*",
                        self.timeseries_table.table_arn,
                        f"{self.timeseries_table.table_arn}/index/*"
                    ]
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "dynamodb:DescribeTable",
                        "dynamodb:DescribeTimeToLive",
                        "dynamodb:ListTables"
                    ],
                    resources=["*"]
                )
            ]
        )
        
        # Attach policy to role
        self.lambda_dynamodb_role.attach_inline_policy(dynamodb_policy)
        
        # Create a role for data processing services
        self.data_processor_role = iam.Role(
            self, "DataProcessorRole",
            role_name="multi-cloud-cost-analytics-processor-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
                iam.ServicePrincipal("ecs-tasks.amazonaws.com")
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Enhanced policy for data processing
        data_processor_policy = iam.Policy(
            self, "DataProcessorPolicy",
            policy_name="multi-cloud-cost-analytics-processor-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "dynamodb:*"
                    ],
                    resources=[
                        self.cost_analytics_table.table_arn,
                        f"{self.cost_analytics_table.table_arn}/index/*",
                        f"{self.cost_analytics_table.table_arn}/stream/*",
                        self.timeseries_table.table_arn,
                        f"{self.timeseries_table.table_arn}/index/*",
                        f"{self.timeseries_table.table_arn}/stream/*"
                    ]
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cloudwatch:PutMetricData",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    resources=["*"]
                )
            ]
        )
        
        self.data_processor_role.attach_inline_policy(data_processor_policy)
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        CfnOutput(
            self, "CostAnalyticsTableName",
            value=self.cost_analytics_table.table_name,
            description="Name of the cost analytics DynamoDB table",
            export_name="CostAnalyticsTableName"
        )
        
        CfnOutput(
            self, "CostAnalyticsTableArn",
            value=self.cost_analytics_table.table_arn,
            description="ARN of the cost analytics DynamoDB table",
            export_name="CostAnalyticsTableArn"
        )
        
        CfnOutput(
            self, "TimeSeriesTableName",
            value=self.timeseries_table.table_name,
            description="Name of the time series DynamoDB table",
            export_name="TimeSeriesTableName"
        )
        
        CfnOutput(
            self, "TimeSeriesTableArn",
            value=self.timeseries_table.table_arn,
            description="ARN of the time series DynamoDB table",
            export_name="TimeSeriesTableArn"
        )
        
        CfnOutput(
            self, "LambdaDynamoDBRoleArn",
            value=self.lambda_dynamodb_role.role_arn,
            description="ARN of the Lambda DynamoDB access role",
            export_name="LambdaDynamoDBRoleArn"
        )
        
        CfnOutput(
            self, "DataProcessorRoleArn",
            value=self.data_processor_role.role_arn,
            description="ARN of the data processor role",
            export_name="DataProcessorRoleArn"
        )


class DynamoDBMonitoringStack(Stack):
    """Additional monitoring stack for DynamoDB tables."""
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        cost_table: dynamodb.Table,
        timeseries_table: dynamodb.Table,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.cost_table = cost_table
        self.timeseries_table = timeseries_table
        
        # Create CloudWatch dashboard
        self._create_dashboard()
        
        # Create log groups for structured logging
        self._create_log_groups()
    
    def _create_dashboard(self) -> None:
        """Create CloudWatch dashboard for DynamoDB monitoring."""
        
        dashboard = cloudwatch.Dashboard(
            self, "DynamoDBDashboard",
            dashboard_name="multi-cloud-cost-analytics-dynamodb"
        )
        
        # Cost Analytics Table Metrics
        cost_table_widget = cloudwatch.GraphWidget(
            title="Cost Analytics Table Metrics",
            left=[
                self.cost_table.metric_consumed_read_capacity_units(),
                self.cost_table.metric_consumed_write_capacity_units()
            ],
            right=[
                self.cost_table.metric_throttled_requests_for_table(),
                self.cost_table.metric_system_errors_for_table()
            ],
            width=12,
            height=6
        )
        
        # Time Series Table Metrics
        timeseries_widget = cloudwatch.GraphWidget(
            title="Time Series Table Metrics",
            left=[
                self.timeseries_table.metric_consumed_read_capacity_units(),
                self.timeseries_table.metric_consumed_write_capacity_units()
            ],
            right=[
                self.timeseries_table.metric_throttled_requests_for_table(),
                self.timeseries_table.metric_system_errors_for_table()
            ],
            width=12,
            height=6
        )
        
        # Table Size Metrics
        size_widget = cloudwatch.GraphWidget(
            title="Table Size Metrics",
            left=[
                cloudwatch.Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="TableSizeBytes",
                    dimensions_map={"TableName": self.cost_table.table_name}
                ),
                cloudwatch.Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="TableSizeBytes",
                    dimensions_map={"TableName": self.timeseries_table.table_name}
                )
            ],
            right=[
                cloudwatch.Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="ItemCount",
                    dimensions_map={"TableName": self.cost_table.table_name}
                ),
                cloudwatch.Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="ItemCount",
                    dimensions_map={"TableName": self.timeseries_table.table_name}
                )
            ],
            width=12,
            height=6
        )
        
        # Add widgets to dashboard
        dashboard.add_widgets(cost_table_widget)
        dashboard.add_widgets(timeseries_widget)
        dashboard.add_widgets(size_widget)
    
    def _create_log_groups(self) -> None:
        """Create CloudWatch log groups for structured logging."""
        
        # Log group for cost data operations
        cost_data_log_group = logs.LogGroup(
            self, "CostDataLogGroup",
            log_group_name="/aws/lambda/multi-cloud-cost-analytics/cost-data",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Log group for time series operations
        timeseries_log_group = logs.LogGroup(
            self, "TimeSeriesLogGroup",
            log_group_name="/aws/lambda/multi-cloud-cost-analytics/timeseries",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Log group for data quality operations
        data_quality_log_group = logs.LogGroup(
            self, "DataQualityLogGroup",
            log_group_name="/aws/lambda/multi-cloud-cost-analytics/data-quality",
            retention=logs.RetentionDays.THREE_MONTHS,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Create outputs for log groups
        CfnOutput(
            self, "CostDataLogGroupName",
            value=cost_data_log_group.log_group_name,
            description="Name of the cost data log group"
        )
        
        CfnOutput(
            self, "TimeSeriesLogGroupName",
            value=timeseries_log_group.log_group_name,
            description="Name of the time series log group"
        )
        
        CfnOutput(
            self, "DataQualityLogGroupName",
            value=data_quality_log_group.log_group_name,
            description="Name of the data quality log group"
        )