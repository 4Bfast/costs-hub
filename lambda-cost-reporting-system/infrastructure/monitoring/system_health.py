"""
System health monitoring for Multi-Cloud AI Cost Analytics
"""

from aws_cdk import (
    Duration,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
)
from constructs import Construct
from typing import Dict, Any, List


class SystemHealthMonitoring:
    """System health monitoring and alerting"""
    
    def __init__(self, stack: Construct, namespace: str, alert_topic: sns.Topic):
        self.stack = stack
        self.namespace = namespace
        self.alert_topic = alert_topic
    
    def create_infrastructure_monitoring(self, resources: Dict[str, Any]) -> List[cloudwatch.Alarm]:
        """Create infrastructure health monitoring"""
        alarms = []
        
        # DynamoDB throttling alarms
        for table_name, table in [
            ("cost_data_table", resources.get('cost_data_table')),
            ("timeseries_table", resources.get('timeseries_table')),
            ("client_config_table", resources.get('client_config_table'))
        ]:
            if table:
                # Read throttles
                read_throttle_alarm = cloudwatch.Alarm(
                    self.stack,
                    f"{table_name}ReadThrottleAlarm",
                    alarm_name=f"multi-cloud-{table_name.replace('_', '-')}-read-throttles",
                    alarm_description=f"DynamoDB read throttles on {table_name}",
                    metric=table.metric_throttled_requests_for_read(
                        period=Duration.minutes(5),
                        statistic="Sum"
                    ),
                    threshold=1,
                    evaluation_periods=1,
                    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
                )
                read_throttle_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
                alarms.append(read_throttle_alarm)
                
                # Write throttles
                write_throttle_alarm = cloudwatch.Alarm(
                    self.stack,
                    f"{table_name}WriteThrottleAlarm",
                    alarm_name=f"multi-cloud-{table_name.replace('_', '-')}-write-throttles",
                    alarm_description=f"DynamoDB write throttles on {table_name}",
                    metric=table.metric_throttled_requests_for_write(
                        period=Duration.minutes(5),
                        statistic="Sum"
                    ),
                    threshold=1,
                    evaluation_periods=1,
                    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
                )
                write_throttle_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
                alarms.append(write_throttle_alarm)
        
        # SQS queue depth monitoring
        for queue_name, queue in [
            ("cost_collection_queue", resources.get('cost_collection_queue')),
            ("ai_processing_queue", resources.get('ai_processing_queue'))
        ]:
            if queue:
                queue_depth_alarm = cloudwatch.Alarm(
                    self.stack,
                    f"{queue_name}DepthAlarm",
                    alarm_name=f"multi-cloud-{queue_name.replace('_', '-')}-depth",
                    alarm_description=f"SQS queue depth too high for {queue_name}",
                    metric=queue.metric_approximate_number_of_visible_messages(
                        period=Duration.minutes(5),
                        statistic="Average"
                    ),
                    threshold=100,  # 100 messages
                    evaluation_periods=3,
                    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
                )
                queue_depth_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
                alarms.append(queue_depth_alarm)
                
                # Dead letter queue monitoring
                dlq_alarm = cloudwatch.Alarm(
                    self.stack,
                    f"{queue_name}DLQAlarm",
                    alarm_name=f"multi-cloud-{queue_name.replace('_', '-')}-dlq",
                    alarm_description=f"Messages in dead letter queue for {queue_name}",
                    metric=cloudwatch.Metric(
                        namespace="AWS/SQS",
                        metric_name="ApproximateNumberOfVisibleMessages",
                        dimensions_map={"QueueName": f"{queue.queue_name}-dlq"},
                        statistic="Sum",
                        period=Duration.minutes(5)
                    ),
                    threshold=1,
                    evaluation_periods=1,
                    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
                )
                dlq_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
                alarms.append(dlq_alarm)
        
        return alarms
    
    def create_lambda_health_monitoring(self, functions: Dict[str, _lambda.Function]) -> List[cloudwatch.Alarm]:
        """Create Lambda function health monitoring"""
        alarms = []
        
        for function_name, function in functions.items():
            # Memory utilization alarm
            memory_alarm = cloudwatch.Alarm(
                self.stack,
                f"{function_name}MemoryAlarm",
                alarm_name=f"multi-cloud-{function_name.replace('_', '-')}-memory",
                alarm_description=f"High memory utilization for {function_name}",
                metric=cloudwatch.Metric(
                    namespace=self.namespace,
                    metric_name="MemoryUtilization",
                    dimensions_map={"FunctionName": function.function_name},
                    statistic="Average",
                    period=Duration.minutes(5)
                ),
                threshold=85.0,  # 85% memory utilization
                evaluation_periods=3,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
            )
            memory_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
            alarms.append(memory_alarm)
            
            # Cold start frequency
            cold_start_alarm = cloudwatch.Alarm(
                self.stack,
                f"{function_name}ColdStartAlarm",
                alarm_name=f"multi-cloud-{function_name.replace('_', '-')}-cold-starts",
                alarm_description=f"High cold start frequency for {function_name}",
                metric=cloudwatch.Metric(
                    namespace=self.namespace,
                    metric_name="ColdStarts",
                    dimensions_map={"FunctionName": function.function_name},
                    statistic="Sum",
                    period=Duration.minutes(15)
                ),
                threshold=10,  # 10 cold starts in 15 minutes
                evaluation_periods=2,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
            )
            cold_start_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
            alarms.append(cold_start_alarm)
            
            # Concurrent executions
            concurrency_alarm = cloudwatch.Alarm(
                self.stack,
                f"{function_name}ConcurrencyAlarm",
                alarm_name=f"multi-cloud-{function_name.replace('_', '-')}-concurrency",
                alarm_description=f"High concurrent executions for {function_name}",
                metric=function.metric_concurrent_executions(
                    period=Duration.minutes(5),
                    statistic="Maximum"
                ),
                threshold=50,  # 50 concurrent executions
                evaluation_periods=2,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
            )
            concurrency_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
            alarms.append(concurrency_alarm)
        
        return alarms
    
    def create_bedrock_monitoring(self) -> List[cloudwatch.Alarm]:
        """Create AWS Bedrock monitoring"""
        alarms = []
        
        # Bedrock API throttling
        bedrock_throttle_alarm = cloudwatch.Alarm(
            self.stack,
            "BedrockThrottleAlarm",
            alarm_name="multi-cloud-bedrock-throttles",
            alarm_description="AWS Bedrock API throttling detected",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="BedrockThrottles",
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=5,  # 5 throttles in 5 minutes
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        bedrock_throttle_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(bedrock_throttle_alarm)
        
        # Bedrock API errors
        bedrock_error_alarm = cloudwatch.Alarm(
            self.stack,
            "BedrockErrorAlarm",
            alarm_name="multi-cloud-bedrock-errors",
            alarm_description="AWS Bedrock API errors detected",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="BedrockErrors",
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=3,  # 3 errors in 5 minutes
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        bedrock_error_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(bedrock_error_alarm)
        
        # Bedrock response time
        bedrock_latency_alarm = cloudwatch.Alarm(
            self.stack,
            "BedrockLatencyAlarm",
            alarm_name="multi-cloud-bedrock-latency",
            alarm_description="AWS Bedrock API response time too high",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="BedrockResponseTime",
                statistic="Average",
                period=Duration.minutes(5)
            ),
            threshold=30000,  # 30 seconds
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        bedrock_latency_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(bedrock_latency_alarm)
        
        return alarms
    
    def create_cost_monitoring(self) -> List[cloudwatch.Alarm]:
        """Create cost monitoring for the system itself"""
        alarms = []
        
        # Lambda cost alarm
        lambda_cost_alarm = cloudwatch.Alarm(
            self.stack,
            "LambdaCostAlarm",
            alarm_name="multi-cloud-lambda-costs",
            alarm_description="Lambda costs exceeding budget",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="LambdaCosts",
                statistic="Sum",
                period=Duration.hours(24)
            ),
            threshold=100.0,  # $100 per day
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        lambda_cost_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(lambda_cost_alarm)
        
        # DynamoDB cost alarm
        dynamodb_cost_alarm = cloudwatch.Alarm(
            self.stack,
            "DynamoDBCostAlarm",
            alarm_name="multi-cloud-dynamodb-costs",
            alarm_description="DynamoDB costs exceeding budget",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="DynamoDBCosts",
                statistic="Sum",
                period=Duration.hours(24)
            ),
            threshold=50.0,  # $50 per day
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        dynamodb_cost_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(dynamodb_cost_alarm)
        
        # Bedrock cost alarm
        bedrock_cost_alarm = cloudwatch.Alarm(
            self.stack,
            "BedrockCostAlarm",
            alarm_name="multi-cloud-bedrock-costs",
            alarm_description="Bedrock costs exceeding budget",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="BedrockCosts",
                statistic="Sum",
                period=Duration.hours(24)
            ),
            threshold=200.0,  # $200 per day
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        bedrock_cost_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(bedrock_cost_alarm)
        
        return alarms
    
    def create_security_monitoring(self) -> List[cloudwatch.Alarm]:
        """Create security monitoring"""
        alarms = []
        
        # Unauthorized API access
        unauthorized_access_alarm = cloudwatch.Alarm(
            self.stack,
            "UnauthorizedAccessAlarm",
            alarm_name="multi-cloud-unauthorized-access",
            alarm_description="Unauthorized API access attempts detected",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="UnauthorizedAccess",
                statistic="Sum",
                period=Duration.minutes(15)
            ),
            threshold=10,  # 10 unauthorized attempts in 15 minutes
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        unauthorized_access_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(unauthorized_access_alarm)
        
        # Suspicious activity
        suspicious_activity_alarm = cloudwatch.Alarm(
            self.stack,
            "SuspiciousActivityAlarm",
            alarm_name="multi-cloud-suspicious-activity",
            alarm_description="Suspicious activity detected",
            metric=cloudwatch.Metric(
                namespace=self.namespace,
                metric_name="SuspiciousActivity",
                statistic="Sum",
                period=Duration.minutes(30)
            ),
            threshold=5,  # 5 suspicious activities in 30 minutes
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        suspicious_activity_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        alarms.append(suspicious_activity_alarm)
        
        return alarms