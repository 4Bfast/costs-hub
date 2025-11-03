"""
Monitoring and alerting components for Multi-Cloud Analytics Stack
"""

from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_dynamodb as dynamodb,
)
from constructs import Construct
from typing import Dict, Any
from config.environments import EnvironmentConfig


class MonitoringComponents:
    """Helper class to create monitoring and alerting components"""
    
    def __init__(self, stack: Construct, env_config: EnvironmentConfig, resources: Dict[str, Any]):
        self.stack = stack
        self.env_config = env_config
        self.env_name = env_config.name
        self.resource_prefix = f"multi-cloud-analytics-{env_config.name}"
        self.resources = resources
        self.namespace = f"MultiCloudAnalytics/{self.env_name.title()}"
    
    def create_enhanced_monitoring(self) -> None:
        """Create comprehensive CloudWatch monitoring and dashboards"""
        from .business_metrics import BusinessMetricsMonitoring
        from .system_health import SystemHealthMonitoring
        from .dashboards import ComprehensiveDashboards
        
        # Create business metrics monitoring
        business_metrics = BusinessMetricsMonitoring(
            self.stack, 
            self.namespace, 
            self.resources['alert_topic']
        )
        
        # Create system health monitoring
        system_health = SystemHealthMonitoring(
            self.stack,
            self.namespace,
            self.resources['alert_topic']
        )
        
        # Create comprehensive dashboards
        dashboards = ComprehensiveDashboards(
            self.stack,
            self.namespace,
            self.resource_prefix
        )
        
        # Create alarms for Lambda functions
        self._create_lambda_alarms(self.resources['cost_orchestrator'], "CostOrchestrator")
        self._create_lambda_alarms(self.resources['ai_insights_processor'], "AIInsights")
        self._create_lambda_alarms(self.resources['api_handler'], "APIHandler")
        self._create_lambda_alarms(self.resources['webhook_handler'], "WebhookHandler")
        
        # Create business metric alarms
        business_metrics.create_ai_accuracy_monitoring()
        business_metrics.create_provider_monitoring()
        business_metrics.create_data_quality_monitoring()
        business_metrics.create_client_experience_monitoring()
        business_metrics.create_cost_anomaly_monitoring()
        
        # Create system health alarms
        system_health.create_infrastructure_monitoring(self.resources)
        system_health.create_lambda_health_monitoring({
            'cost_orchestrator': self.resources['cost_orchestrator'],
            'ai_insights_processor': self.resources['ai_insights_processor'],
            'api_handler': self.resources['api_handler'],
            'webhook_handler': self.resources['webhook_handler']
        })
        system_health.create_bedrock_monitoring()
        system_health.create_cost_monitoring()
        system_health.create_security_monitoring()
        
        # Create comprehensive dashboards
        dashboards.create_executive_dashboard()
        dashboards.create_technical_operations_dashboard(self.resources)
        dashboards.create_ai_performance_dashboard()
        
        # Create original dashboards for backward compatibility
        self._create_operational_dashboard()
        self._create_business_dashboard()
        self._create_ai_insights_dashboard()

    def _create_lambda_alarms(self, function: _lambda.Function, function_name: str) -> None:
        """Create standard alarms for a Lambda function"""
        
        # Error rate alarm
        error_alarm = cloudwatch.Alarm(
            self.stack,
            f"{function_name}ErrorAlarm",
            alarm_name=f"{self.resource_prefix}-{function_name.lower()}-errors",
            alarm_description=f"{function_name} function errors",
            metric=function.metric_errors(
                period=Duration.minutes(5),
                statistic="Sum"
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
        )
        
        error_alarm.add_alarm_action(cw_actions.SnsAction(self.resources['alert_topic']))
        
        # Duration alarm
        duration_alarm = cloudwatch.Alarm(
            self.stack,
            f"{function_name}DurationAlarm",
            alarm_name=f"{self.resource_prefix}-{function_name.lower()}-duration",
            alarm_description=f"{function_name} function duration approaching timeout",
            metric=function.metric_duration(
                period=Duration.minutes(5),
                statistic="Average"
            ),
            threshold=function.timeout.to_milliseconds() * 0.8,  # 80% of timeout
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )
        
        duration_alarm.add_alarm_action(cw_actions.SnsAction(self.resources['alert_topic']))
        
        # Throttle alarm
        throttle_alarm = cloudwatch.Alarm(
            self.stack,
            f"{function_name}ThrottleAlarm",
            alarm_name=f"{self.resource_prefix}-{function_name.lower()}-throttles",
            alarm_description=f"{function_name} function throttles",
            metric=function.metric_throttles(
                period=Duration.minutes(5),
                statistic="Sum"
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
        )
        
        throttle_alarm.add_alarm_action(cw_actions.SnsAction(self.resources['alert_topic']))

    def _create_business_metric_alarms(self) -> None:
        """Create alarms for business metrics"""
        
        # AI insights accuracy alarm
        ai_accuracy_alarm = cloudwatch.Alarm(
            self.stack,
            "AIInsightsAccuracyAlarm",
            alarm_name=f"{self.resource_prefix}-ai-accuracy",
            alarm_description="AI insights accuracy below threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="AIInsightsAccuracy",
                statistic="Average",
                period=Duration.hours(1)
            ),
            threshold=85,  # 85% accuracy threshold
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        ai_accuracy_alarm.add_alarm_action(cw_actions.SnsAction(self.resources['alert_topic']))
        
        # Multi-provider collection success rate
        collection_success_alarm = cloudwatch.Alarm(
            self.stack,
            "MultiProviderCollectionSuccessAlarm",
            alarm_name=f"{self.resource_prefix}-collection-success",
            alarm_description="Multi-provider cost collection success rate below threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="ProviderCollectionSuccessRate",
                statistic="Average",
                period=Duration.minutes(30)
            ),
            threshold=90,  # 90% success rate threshold
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD
        )
        
        collection_success_alarm.add_alarm_action(cw_actions.SnsAction(self.resources['alert_topic']))
        
        # Data quality score alarm
        data_quality_alarm = cloudwatch.Alarm(
            self.stack,
            "DataQualityAlarm",
            alarm_name=f"{self.resource_prefix}-data-quality",
            alarm_description="Data quality score below threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="DataQualityScore",
                statistic="Average",
                period=Duration.hours(1)
            ),
            threshold=80,  # 80% data quality threshold
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD
        )
        
        data_quality_alarm.add_alarm_action(cw_actions.SnsAction(self.resources['alert_topic']))

    def _create_operational_dashboard(self) -> None:
        """Create operational monitoring dashboard"""
        
        cloudwatch.Dashboard(
            self.stack,
            "OperationalDashboard",
            dashboard_name=f"{self.resource_prefix}-operational",
            widgets=[
                # Row 1: Lambda Function Health
                [
                    cloudwatch.GraphWidget(
                        title="Lambda Invocations",
                        left=[
                            self.resources['cost_orchestrator'].metric_invocations(period=Duration.minutes(5)),
                            self.resources['ai_insights_processor'].metric_invocations(period=Duration.minutes(5)),
                            self.resources['api_handler'].metric_invocations(period=Duration.minutes(5))
                        ],
                        width=8,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="Lambda Errors",
                        left=[
                            self.resources['cost_orchestrator'].metric_errors(period=Duration.minutes(5)),
                            self.resources['ai_insights_processor'].metric_errors(period=Duration.minutes(5)),
                            self.resources['api_handler'].metric_errors(period=Duration.minutes(5))
                        ],
                        width=8,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="Lambda Duration",
                        left=[
                            self.resources['cost_orchestrator'].metric_duration(period=Duration.minutes(5)),
                            self.resources['ai_insights_processor'].metric_duration(period=Duration.minutes(5)),
                            self.resources['api_handler'].metric_duration(period=Duration.minutes(5))
                        ],
                        width=8,
                        height=6
                    )
                ],
                # Row 2: Queue Metrics
                [
                    cloudwatch.GraphWidget(
                        title="SQS Queue Depth",
                        left=[
                            self.resources['cost_collection_queue'].metric_approximate_number_of_visible_messages(period=Duration.minutes(5)),
                            self.resources['ai_processing_queue'].metric_approximate_number_of_visible_messages(period=Duration.minutes(5))
                        ],
                        width=12,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="SQS Messages Sent/Received",
                        left=[
                            self.resources['cost_collection_queue'].metric_number_of_messages_sent(period=Duration.minutes(5)),
                            self.resources['ai_processing_queue'].metric_number_of_messages_sent(period=Duration.minutes(5))
                        ],
                        right=[
                            self.resources['cost_collection_queue'].metric_number_of_messages_received(period=Duration.minutes(5)),
                            self.resources['ai_processing_queue'].metric_number_of_messages_received(period=Duration.minutes(5))
                        ],
                        width=12,
                        height=6
                    )
                ],
                # Row 3: DynamoDB Metrics
                [
                    cloudwatch.GraphWidget(
                        title="DynamoDB Read/Write Capacity",
                        left=[
                            self.resources['cost_data_table'].metric_consumed_read_capacity_units(period=Duration.minutes(5)),
                            self.resources['timeseries_table'].metric_consumed_read_capacity_units(period=Duration.minutes(5))
                        ],
                        right=[
                            self.resources['cost_data_table'].metric_consumed_write_capacity_units(period=Duration.minutes(5)),
                            self.resources['timeseries_table'].metric_consumed_write_capacity_units(period=Duration.minutes(5))
                        ],
                        width=24,
                        height=6
                    )
                ]
            ]
        )

    def _create_business_dashboard(self) -> None:
        """Create business metrics dashboard"""
        
        cloudwatch.Dashboard(
            self.stack,
            "BusinessDashboard",
            dashboard_name=f"{self.resource_prefix}-business",
            widgets=[
                # Row 1: Key Performance Indicators
                [
                    cloudwatch.SingleValueWidget(
                        title="Active Clients",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ActiveClients",
                                statistic="Maximum",
                                period=Duration.hours(24)
                            )
                        ],
                        width=6,
                        height=6
                    ),
                    cloudwatch.SingleValueWidget(
                        title="Providers Connected",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ProvidersConnected",
                                statistic="Maximum",
                                period=Duration.hours(24)
                            )
                        ],
                        width=6,
                        height=6
                    ),
                    cloudwatch.SingleValueWidget(
                        title="AI Insights Generated (24h)",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AIInsightsGenerated",
                                statistic="Sum",
                                period=Duration.hours(24)
                            )
                        ],
                        width=6,
                        height=6
                    ),
                    cloudwatch.SingleValueWidget(
                        title="Anomalies Detected (24h)",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AnomaliesDetected",
                                statistic="Sum",
                                period=Duration.hours(24)
                            )
                        ],
                        width=6,
                        height=6
                    )
                ],
                # Row 2: Provider Performance
                [
                    cloudwatch.GraphWidget(
                        title="Provider Collection Success Rate",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ProviderCollectionSuccessRate",
                                dimensions_map={"Provider": "AWS"},
                                statistic="Average",
                                period=Duration.hours(1),
                                label="AWS"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ProviderCollectionSuccessRate",
                                dimensions_map={"Provider": "GCP"},
                                statistic="Average",
                                period=Duration.hours(1),
                                label="GCP"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ProviderCollectionSuccessRate",
                                dimensions_map={"Provider": "Azure"},
                                statistic="Average",
                                period=Duration.hours(1),
                                label="Azure"
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0, max=100),
                        width=24,
                        height=6
                    )
                ],
                # Row 3: AI Performance
                [
                    cloudwatch.GraphWidget(
                        title="AI Insights Accuracy",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AIInsightsAccuracy",
                                statistic="Average",
                                period=Duration.hours(1)
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0, max=100),
                        width=12,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="Data Quality Score",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="DataQualityScore",
                                statistic="Average",
                                period=Duration.hours(1)
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0, max=100),
                        width=12,
                        height=6
                    )
                ]
            ]
        )

    def _create_ai_insights_dashboard(self) -> None:
        """Create AI insights specific dashboard"""
        
        cloudwatch.Dashboard(
            self.stack,
            "AIInsightsDashboard",
            dashboard_name=f"{self.resource_prefix}-ai-insights",
            widgets=[
                # Row 1: AI Processing Metrics
                [
                    cloudwatch.GraphWidget(
                        title="AI Processing Duration",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AIProcessingDuration",
                                dimensions_map={"Operation": "AnomalyDetection"},
                                statistic="Average",
                                period=Duration.minutes(15),
                                label="Anomaly Detection"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AIProcessingDuration",
                                dimensions_map={"Operation": "TrendAnalysis"},
                                statistic="Average",
                                period=Duration.minutes(15),
                                label="Trend Analysis"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AIProcessingDuration",
                                dimensions_map={"Operation": "Forecasting"},
                                statistic="Average",
                                period=Duration.minutes(15),
                                label="Forecasting"
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="Bedrock API Calls",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="BedrockAPICalls",
                                statistic="Sum",
                                period=Duration.minutes(15)
                            )
                        ],
                        width=12,
                        height=6
                    )
                ],
                # Row 2: Insights Quality
                [
                    cloudwatch.GraphWidget(
                        title="Anomaly Detection Results",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AnomaliesDetected",
                                dimensions_map={"Severity": "HIGH"},
                                statistic="Sum",
                                period=Duration.hours(1),
                                label="High Severity"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AnomaliesDetected",
                                dimensions_map={"Severity": "MEDIUM"},
                                statistic="Sum",
                                period=Duration.hours(1),
                                label="Medium Severity"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AnomaliesDetected",
                                dimensions_map={"Severity": "LOW"},
                                statistic="Sum",
                                period=Duration.hours(1),
                                label="Low Severity"
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="Forecast Accuracy",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ForecastAccuracy",
                                statistic="Average",
                                period=Duration.hours(1)
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0, max=100),
                        width=12,
                        height=6
                    )
                ]
            ]
        )