"""
Business metrics monitoring for Multi-Cloud AI Cost Analytics
"""

from aws_cdk import (
    Duration,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_lambda as _lambda,
)
from constructs import Construct
from typing import Dict, Any, List


class BusinessMetricsMonitoring:
    """Business metrics monitoring and alerting"""
    
    def __init__(self, stack: Construct, namespace: str, alert_topic: sns.Topic):
        self.stack = stack
        self.namespace = namespace
        self.alert_topic = alert_topic
    
    def create_ai_accuracy_monitoring(self) -> List[cloudwatch.Alarm]:
        """Create AI insights accuracy monitoring"""
        alarms = []
        
        # AI Insights Accuracy Alarm
        accuracy_alarm = cloudwatch.Alarm(
            self.stack,
            "AIInsightsAccuracyAlarm",
            alarm_name="multi-cloud-ai-insights-accuracy",
            alarm_description="AI insights accuracy below acceptable threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="AIInsightsAccuracy",
                statistic="Average",
                period=Duration.hours(1)
            ),
            threshold=85.0,  # 85% accuracy threshold
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        accuracy_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(accuracy_alarm)
        
        # Anomaly Detection Accuracy
        anomaly_accuracy_alarm = cloudwatch.Alarm(
            self.stack,
            "AnomalyDetectionAccuracyAlarm",
            alarm_name="multi-cloud-anomaly-detection-accuracy",
            alarm_description="Anomaly detection accuracy below threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="AnomalyDetectionAccuracy",
                statistic="Average",
                period=Duration.hours(2)
            ),
            threshold=80.0,  # 80% accuracy threshold
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        anomaly_accuracy_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(anomaly_accuracy_alarm)
        
        # Forecast Accuracy
        forecast_accuracy_alarm = cloudwatch.Alarm(
            self.stack,
            "ForecastAccuracyAlarm",
            alarm_name="multi-cloud-forecast-accuracy",
            alarm_description="Cost forecast accuracy below threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="ForecastAccuracy",
                statistic="Average",
                period=Duration.hours(6)
            ),
            threshold=75.0,  # 75% accuracy threshold
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        forecast_accuracy_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(forecast_accuracy_alarm)
        
        return alarms
    
    def create_provider_monitoring(self) -> List[cloudwatch.Alarm]:
        """Create provider-specific monitoring"""
        alarms = []
        providers = ["AWS", "GCP", "Azure"]
        
        for provider in providers:
            # Provider collection success rate
            success_alarm = cloudwatch.Alarm(
                self.stack,
                f"{provider}CollectionSuccessAlarm",
                alarm_name=f"multi-cloud-{provider.lower()}-collection-success",
                alarm_description=f"{provider} cost collection success rate below threshold",
                metric=cloudwatch.Metric(
                    namespace=self.namespace,
                    metric_name="ProviderCollectionSuccessRate",
                    dimensions_map={"Provider": provider},
                    statistic="Average",
                    period=Duration.minutes(30)
                ),
                threshold=90.0,  # 90% success rate
                evaluation_periods=2,
                comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD
            )
            success_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
            alarms.append(success_alarm)
            
            # Provider API error rate
            api_error_alarm = cloudwatch.Alarm(
                self.stack,
                f"{provider}APIErrorAlarm",
                alarm_name=f"multi-cloud-{provider.lower()}-api-errors",
                alarm_description=f"{provider} API error rate too high",
                metric=cloudwatch.Metric(
                    namespace=self.namespace,
                    metric_name="ProviderAPIErrors",
                    dimensions_map={"Provider": provider},
                    statistic="Sum",
                    period=Duration.minutes(15)
                ),
                threshold=5,  # 5 errors in 15 minutes
                evaluation_periods=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
            )
            api_error_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
            alarms.append(api_error_alarm)
        
        return alarms
    
    def create_data_quality_monitoring(self) -> List[cloudwatch.Alarm]:
        """Create data quality monitoring"""
        alarms = []
        
        # Overall data quality score
        quality_alarm = cloudwatch.Alarm(
            self.stack,
            "DataQualityScoreAlarm",
            alarm_name="multi-cloud-data-quality-score",
            alarm_description="Overall data quality score below threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="DataQualityScore",
                statistic="Average",
                period=Duration.hours(1)
            ),
            threshold=80.0,  # 80% quality threshold
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD
        )
        quality_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(quality_alarm)
        
        # Data completeness
        completeness_alarm = cloudwatch.Alarm(
            self.stack,
            "DataCompletenessAlarm",
            alarm_name="multi-cloud-data-completeness",
            alarm_description="Data completeness below threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="DataCompleteness",
                statistic="Average",
                period=Duration.hours(1)
            ),
            threshold=95.0,  # 95% completeness threshold
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD
        )
        completeness_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(completeness_alarm)
        
        # Data freshness
        freshness_alarm = cloudwatch.Alarm(
            self.stack,
            "DataFreshnessAlarm",
            alarm_name="multi-cloud-data-freshness",
            alarm_description="Data freshness below threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="DataFreshness",
                statistic="Average",
                period=Duration.hours(2)
            ),
            threshold=90.0,  # 90% freshness threshold
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD
        )
        freshness_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(freshness_alarm)
        
        return alarms
    
    def create_client_experience_monitoring(self) -> List[cloudwatch.Alarm]:
        """Create client experience monitoring"""
        alarms = []
        
        # API response time
        api_latency_alarm = cloudwatch.Alarm(
            self.stack,
            "APILatencyAlarm",
            alarm_name="multi-cloud-api-latency",
            alarm_description="API response time too high",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="APIResponseTime",
                statistic="Average",
                period=Duration.minutes(5)
            ),
            threshold=2000,  # 2 seconds
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )
        api_latency_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(api_latency_alarm)
        
        # Client onboarding success rate
        onboarding_alarm = cloudwatch.Alarm(
            self.stack,
            "ClientOnboardingSuccessAlarm",
            alarm_name="multi-cloud-client-onboarding-success",
            alarm_description="Client onboarding success rate below threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="ClientOnboardingSuccessRate",
                statistic="Average",
                period=Duration.hours(1)
            ),
            threshold=95.0,  # 95% success rate
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        onboarding_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(onboarding_alarm)
        
        # Report generation success rate
        report_success_alarm = cloudwatch.Alarm(
            self.stack,
            "ReportGenerationSuccessAlarm",
            alarm_name="multi-cloud-report-generation-success",
            alarm_description="Report generation success rate below threshold",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="ReportGenerationSuccessRate",
                statistic="Average",
                period=Duration.minutes(30)
            ),
            threshold=98.0,  # 98% success rate
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD
        )
        report_success_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(report_success_alarm)
        
        return alarms
    
    def create_cost_anomaly_monitoring(self) -> List[cloudwatch.Alarm]:
        """Create cost anomaly monitoring"""
        alarms = []
        
        # High severity anomalies
        high_severity_alarm = cloudwatch.Alarm(
            self.stack,
            "HighSeverityAnomaliesAlarm",
            alarm_name="multi-cloud-high-severity-anomalies",
            alarm_description="High severity cost anomalies detected",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="AnomaliesDetected",
                dimensions_map={"Severity": "HIGH"},
                statistic="Sum",
                period=Duration.minutes(30)
            ),
            threshold=3,  # 3 high severity anomalies in 30 minutes
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
        )
        high_severity_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(high_severity_alarm)
        
        # Critical anomalies
        critical_alarm = cloudwatch.Alarm(
            self.stack,
            "CriticalAnomaliesAlarm",
            alarm_name="multi-cloud-critical-anomalies",
            alarm_description="Critical cost anomalies detected",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="AnomaliesDetected",
                dimensions_map={"Severity": "CRITICAL"},
                statistic="Sum",
                period=Duration.minutes(15)
            ),
            threshold=1,  # Any critical anomaly
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
        )
        critical_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(critical_alarm)
        
        return alarms