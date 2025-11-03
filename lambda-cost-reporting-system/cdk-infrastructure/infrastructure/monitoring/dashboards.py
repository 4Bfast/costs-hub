"""
Comprehensive dashboards for Multi-Cloud AI Cost Analytics
"""

from aws_cdk import (
    Duration,
    aws_cloudwatch as cloudwatch,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
)
from constructs import Construct
from typing import Dict, Any, List


class ComprehensiveDashboards:
    """Comprehensive monitoring dashboards"""
    
    def __init__(self, stack: Construct, namespace: str, resource_prefix: str):
        self.stack = stack
        self.namespace = namespace
        self.resource_prefix = resource_prefix
    
    def create_executive_dashboard(self) -> cloudwatch.Dashboard:
        """Create executive-level dashboard with high-level KPIs"""
        
        return cloudwatch.Dashboard(
            self.stack,
            "ExecutiveDashboard",
            dashboard_name=f"{self.resource_prefix}-executive",
            period_override=cloudwatch.PeriodOverride.AUTO,
            start="-P7D",  # Last 7 days
            widgets=[
                # Row 1: Key Business Metrics
                [
                    cloudwatch.SingleValueWidget(
                        title="Total Active Clients",
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
                        title="Multi-Cloud Providers",
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
                        title="System Uptime (%)",
                        metrics=[
                            cloudwatch.MathExpression(
                                expression="100 - (errors / invocations * 100)",
                                using_metrics={
                                    "errors": cloudwatch.Metric(
                                        namespace=self.namespace,
                                        metric_name="SystemErrors",
                                        statistic="Sum",
                                        period=Duration.hours(24)
                                    ),
                                    "invocations": cloudwatch.Metric(
                                        namespace=self.namespace,
                                        metric_name="SystemInvocations",
                                        statistic="Sum",
                                        period=Duration.hours(24)
                                    )
                                },
                                label="Uptime %"
                            )
                        ],
                        width=6,
                        height=6
                    ),
                    cloudwatch.SingleValueWidget(
                        title="AI Insights Generated (7d)",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AIInsightsGenerated",
                                statistic="Sum",
                                period=Duration.days(7)
                            )
                        ],
                        width=6,
                        height=6
                    )
                ],
                # Row 2: Business Performance Trends
                [
                    cloudwatch.GraphWidget(
                        title="Daily Client Activity",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ActiveClients",
                                statistic="Maximum",
                                period=Duration.hours(24),
                                label="Active Clients"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="NewClients",
                                statistic="Sum",
                                period=Duration.hours(24),
                                label="New Clients"
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="AI Insights Performance",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AIInsightsAccuracy",
                                statistic="Average",
                                period=Duration.hours(6),
                                label="Accuracy %"
                            )
                        ],
                        right=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AIInsightsGenerated",
                                statistic="Sum",
                                period=Duration.hours(6),
                                label="Insights Generated"
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0, max=100),
                        width=12,
                        height=6
                    )
                ],
                # Row 3: Provider Performance
                [
                    cloudwatch.GraphWidget(
                        title="Multi-Provider Success Rates",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ProviderCollectionSuccessRate",
                                dimensions_map={"Provider": "AWS"},
                                statistic="Average",
                                period=Duration.hours(2),
                                label="AWS"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ProviderCollectionSuccessRate",
                                dimensions_map={"Provider": "GCP"},
                                statistic="Average",
                                period=Duration.hours(2),
                                label="GCP"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ProviderCollectionSuccessRate",
                                dimensions_map={"Provider": "Azure"},
                                statistic="Average",
                                period=Duration.hours(2),
                                label="Azure"
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0, max=100),
                        width=24,
                        height=6
                    )
                ],
                # Row 4: Cost and Efficiency
                [
                    cloudwatch.GraphWidget(
                        title="System Operating Costs",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="LambdaCosts",
                                statistic="Sum",
                                period=Duration.hours(24),
                                label="Lambda"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="DynamoDBCosts",
                                statistic="Sum",
                                period=Duration.hours(24),
                                label="DynamoDB"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="BedrockCosts",
                                statistic="Sum",
                                period=Duration.hours(24),
                                label="Bedrock"
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="Cost Per Client",
                        left=[
                            cloudwatch.MathExpression(
                                expression="total_costs / active_clients",
                                using_metrics={
                                    "total_costs": cloudwatch.Metric(
                                        namespace=self.namespace,
                                        metric_name="TotalSystemCosts",
                                        statistic="Sum",
                                        period=Duration.hours(24)
                                    ),
                                    "active_clients": cloudwatch.Metric(
                                        namespace=self.namespace,
                                        metric_name="ActiveClients",
                                        statistic="Average",
                                        period=Duration.hours(24)
                                    )
                                },
                                label="Cost per Client ($)"
                            )
                        ],
                        width=12,
                        height=6
                    )
                ]
            ]
        )
    
    def create_technical_operations_dashboard(self, resources: Dict[str, Any]) -> cloudwatch.Dashboard:
        """Create technical operations dashboard for DevOps teams"""
        
        return cloudwatch.Dashboard(
            self.stack,
            "TechnicalOperationsDashboard",
            dashboard_name=f"{self.resource_prefix}-technical-ops",
            period_override=cloudwatch.PeriodOverride.AUTO,
            start="-PT6H",  # Last 6 hours
            widgets=[
                # Row 1: System Health Overview
                [
                    cloudwatch.SingleValueWidget(
                        title="System Health Score",
                        metrics=[
                            cloudwatch.MathExpression(
                                expression="100 - (errors / invocations * 100)",
                                using_metrics={
                                    "errors": cloudwatch.Metric(
                                        namespace=self.namespace,
                                        metric_name="SystemErrors",
                                        statistic="Sum",
                                        period=Duration.hours(1)
                                    ),
                                    "invocations": cloudwatch.Metric(
                                        namespace=self.namespace,
                                        metric_name="SystemInvocations",
                                        statistic="Sum",
                                        period=Duration.hours(1)
                                    )
                                },
                                label="Health Score %"
                            )
                        ],
                        width=8,
                        height=6
                    ),
                    cloudwatch.SingleValueWidget(
                        title="Active Alarms",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ActiveAlarms",
                                statistic="Maximum",
                                period=Duration.minutes(5)
                            )
                        ],
                        width=8,
                        height=6
                    ),
                    cloudwatch.SingleValueWidget(
                        title="API Response Time (avg)",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="APIResponseTime",
                                statistic="Average",
                                period=Duration.minutes(15)
                            )
                        ],
                        width=8,
                        height=6
                    )
                ],
                # Row 2: Lambda Performance
                [
                    cloudwatch.GraphWidget(
                        title="Lambda Function Performance",
                        left=[
                            cloudwatch.Metric(
                                namespace="AWS/Lambda",
                                metric_name="Duration",
                                dimensions_map={"FunctionName": f"{self.resource_prefix}-cost-orchestrator"},
                                statistic="Average",
                                period=Duration.minutes(5),
                                label="Cost Orchestrator"
                            ),
                            cloudwatch.Metric(
                                namespace="AWS/Lambda",
                                metric_name="Duration",
                                dimensions_map={"FunctionName": f"{self.resource_prefix}-ai-insights"},
                                statistic="Average",
                                period=Duration.minutes(5),
                                label="AI Insights"
                            ),
                            cloudwatch.Metric(
                                namespace="AWS/Lambda",
                                metric_name="Duration",
                                dimensions_map={"FunctionName": f"{self.resource_prefix}-api-handler"},
                                statistic="Average",
                                period=Duration.minutes(5),
                                label="API Handler"
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="Lambda Error Rates",
                        left=[
                            cloudwatch.Metric(
                                namespace="AWS/Lambda",
                                metric_name="Errors",
                                dimensions_map={"FunctionName": f"{self.resource_prefix}-cost-orchestrator"},
                                statistic="Sum",
                                period=Duration.minutes(5),
                                label="Cost Orchestrator"
                            ),
                            cloudwatch.Metric(
                                namespace="AWS/Lambda",
                                metric_name="Errors",
                                dimensions_map={"FunctionName": f"{self.resource_prefix}-ai-insights"},
                                statistic="Sum",
                                period=Duration.minutes(5),
                                label="AI Insights"
                            ),
                            cloudwatch.Metric(
                                namespace="AWS/Lambda",
                                metric_name="Errors",
                                dimensions_map={"FunctionName": f"{self.resource_prefix}-api-handler"},
                                statistic="Sum",
                                period=Duration.minutes(5),
                                label="API Handler"
                            )
                        ],
                        width=12,
                        height=6
                    )
                ],
                # Row 3: Infrastructure Metrics
                [
                    cloudwatch.GraphWidget(
                        title="DynamoDB Performance",
                        left=[
                            cloudwatch.Metric(
                                namespace="AWS/DynamoDB",
                                metric_name="ConsumedReadCapacityUnits",
                                dimensions_map={"TableName": f"{self.resource_prefix}-cost-data"},
                                statistic="Sum",
                                period=Duration.minutes(5),
                                label="Cost Data Reads"
                            ),
                            cloudwatch.Metric(
                                namespace="AWS/DynamoDB",
                                metric_name="ConsumedWriteCapacityUnits",
                                dimensions_map={"TableName": f"{self.resource_prefix}-cost-data"},
                                statistic="Sum",
                                period=Duration.minutes(5),
                                label="Cost Data Writes"
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="SQS Queue Metrics",
                        left=[
                            cloudwatch.Metric(
                                namespace="AWS/SQS",
                                metric_name="ApproximateNumberOfVisibleMessages",
                                dimensions_map={"QueueName": f"{self.resource_prefix}-cost-collection"},
                                statistic="Average",
                                period=Duration.minutes(5),
                                label="Cost Collection Queue"
                            ),
                            cloudwatch.Metric(
                                namespace="AWS/SQS",
                                metric_name="ApproximateNumberOfVisibleMessages",
                                dimensions_map={"QueueName": f"{self.resource_prefix}-ai-processing"},
                                statistic="Average",
                                period=Duration.minutes(5),
                                label="AI Processing Queue"
                            )
                        ],
                        width=12,
                        height=6
                    )
                ],
                # Row 4: External Dependencies
                [
                    cloudwatch.GraphWidget(
                        title="Provider API Performance",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ProviderAPIResponseTime",
                                dimensions_map={"Provider": "AWS"},
                                statistic="Average",
                                period=Duration.minutes(15),
                                label="AWS API"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ProviderAPIResponseTime",
                                dimensions_map={"Provider": "GCP"},
                                statistic="Average",
                                period=Duration.minutes(15),
                                label="GCP API"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ProviderAPIResponseTime",
                                dimensions_map={"Provider": "Azure"},
                                statistic="Average",
                                period=Duration.minutes(15),
                                label="Azure API"
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="Bedrock AI Performance",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="BedrockResponseTime",
                                statistic="Average",
                                period=Duration.minutes(5),
                                label="Response Time (ms)"
                            )
                        ],
                        right=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="BedrockAPICalls",
                                statistic="Sum",
                                period=Duration.minutes(5),
                                label="API Calls"
                            )
                        ],
                        width=12,
                        height=6
                    )
                ]
            ]
        )
    
    def create_ai_performance_dashboard(self) -> cloudwatch.Dashboard:
        """Create AI performance monitoring dashboard"""
        
        return cloudwatch.Dashboard(
            self.stack,
            "AIPerformanceDashboard",
            dashboard_name=f"{self.resource_prefix}-ai-performance",
            period_override=cloudwatch.PeriodOverride.AUTO,
            start="-PT12H",  # Last 12 hours
            widgets=[
                # Row 1: AI Accuracy Metrics
                [
                    cloudwatch.SingleValueWidget(
                        title="Overall AI Accuracy",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AIInsightsAccuracy",
                                statistic="Average",
                                period=Duration.hours(1)
                            )
                        ],
                        width=6,
                        height=6
                    ),
                    cloudwatch.SingleValueWidget(
                        title="Anomaly Detection Accuracy",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AnomalyDetectionAccuracy",
                                statistic="Average",
                                period=Duration.hours(1)
                            )
                        ],
                        width=6,
                        height=6
                    ),
                    cloudwatch.SingleValueWidget(
                        title="Forecast Accuracy",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ForecastAccuracy",
                                statistic="Average",
                                period=Duration.hours(1)
                            )
                        ],
                        width=6,
                        height=6
                    ),
                    cloudwatch.SingleValueWidget(
                        title="Insights Generated (12h)",
                        metrics=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AIInsightsGenerated",
                                statistic="Sum",
                                period=Duration.hours(12)
                            )
                        ],
                        width=6,
                        height=6
                    )
                ],
                # Row 2: AI Processing Performance
                [
                    cloudwatch.GraphWidget(
                        title="AI Processing Duration by Operation",
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
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AIProcessingDuration",
                                dimensions_map={"Operation": "RecommendationGeneration"},
                                statistic="Average",
                                period=Duration.minutes(15),
                                label="Recommendations"
                            )
                        ],
                        width=24,
                        height=6
                    )
                ],
                # Row 3: Anomaly Detection Results
                [
                    cloudwatch.GraphWidget(
                        title="Anomalies Detected by Severity",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AnomaliesDetected",
                                dimensions_map={"Severity": "CRITICAL"},
                                statistic="Sum",
                                period=Duration.hours(1),
                                label="Critical"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AnomaliesDetected",
                                dimensions_map={"Severity": "HIGH"},
                                statistic="Sum",
                                period=Duration.hours(1),
                                label="High"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AnomaliesDetected",
                                dimensions_map={"Severity": "MEDIUM"},
                                statistic="Sum",
                                period=Duration.hours(1),
                                label="Medium"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="AnomaliesDetected",
                                dimensions_map={"Severity": "LOW"},
                                statistic="Sum",
                                period=Duration.hours(1),
                                label="Low"
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="AI Model Performance Trends",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ModelConfidenceScore",
                                statistic="Average",
                                period=Duration.hours(1),
                                label="Confidence Score"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="ModelPredictionAccuracy",
                                statistic="Average",
                                period=Duration.hours(1),
                                label="Prediction Accuracy"
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0, max=100),
                        width=12,
                        height=6
                    )
                ],
                # Row 4: Bedrock Usage and Performance
                [
                    cloudwatch.GraphWidget(
                        title="Bedrock Usage Patterns",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="BedrockAPICalls",
                                statistic="Sum",
                                period=Duration.minutes(30),
                                label="API Calls"
                            )
                        ],
                        right=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="BedrockTokensUsed",
                                statistic="Sum",
                                period=Duration.minutes(30),
                                label="Tokens Used"
                            )
                        ],
                        width=12,
                        height=6
                    ),
                    cloudwatch.GraphWidget(
                        title="Bedrock Response Quality",
                        left=[
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="BedrockResponseQuality",
                                statistic="Average",
                                period=Duration.minutes(30),
                                label="Response Quality Score"
                            ),
                            cloudwatch.Metric(
                                namespace=self.namespace,
                                metric_name="BedrockResponseRelevance",
                                statistic="Average",
                                period=Duration.minutes(30),
                                label="Response Relevance"
                            )
                        ],
                        left_y_axis=cloudwatch.YAxisProps(min=0, max=100),
                        width=12,
                        height=6
                    )
                ]
            ]
        )