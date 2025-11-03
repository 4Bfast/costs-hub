# Monitoring Setup Guide

This guide explains how to deploy and configure the monitoring dashboards for the Lambda Cost Reporting System.

## Prerequisites

- AWS CDK installed and configured
- Appropriate AWS permissions for CloudWatch, Lambda, DynamoDB, and S3
- Lambda Cost Reporting System deployed

## Dashboard Deployment

### Automatic Deployment via CDK

The dashboards are automatically created when deploying the CDK stack:

```bash
cd lambda-cost-reporting-system/infrastructure
cdk deploy CostReportingStack-{environment}
```

This will create three dashboards:
- `cost-reporting-{environment}-operational`
- `cost-reporting-{environment}-business`
- `cost-reporting-{environment}-health`

### Manual Dashboard Creation

If you need to create dashboards manually or customize them:

1. **Navigate to CloudWatch Console**
2. **Select "Dashboards" from the left menu**
3. **Click "Create dashboard"**
4. **Follow the widget configuration steps below**

## Dashboard Configuration

### Environment-Specific Settings

Each environment (dev, staging, prod) has its own set of dashboards with appropriate configurations:

```typescript
// Environment-specific dashboard names
const dashboardNames = {
  operational: `cost-reporting-${environment}-operational`,
  business: `cost-reporting-${environment}-business`,
  health: `cost-reporting-${environment}-health`
};
```

### Metric Namespace Configuration

Custom metrics are published to environment-specific namespaces:

```typescript
const namespace = `CostReporting/${environment.charAt(0).toUpperCase() + environment.slice(1)}`;
```

Examples:
- Development: `CostReporting/Dev`
- Staging: `CostReporting/Staging`
- Production: `CostReporting/Prod`

## Widget Configuration Details

### Operational Dashboard Widgets

#### Lambda Function Metrics

```json
{
  "metrics": [
    ["AWS/Lambda", "Invocations", "FunctionName", "cost-reporting-{env}-handler"],
    ["AWS/Lambda", "Errors", "FunctionName", "cost-reporting-{env}-handler"],
    ["AWS/Lambda", "Duration", "FunctionName", "cost-reporting-{env}-handler"]
  ],
  "period": 300,
  "stat": "Sum",
  "region": "us-east-1",
  "title": "Lambda Function Health"
}
```

#### Custom Business Metrics

```json
{
  "metrics": [
    ["CostReporting/{Env}", "ExecutionSucceeded"],
    ["CostReporting/{Env}", "ExecutionFailed"],
    ["CostReporting/{Env}", "ClientSuccessRate"]
  ],
  "period": 900,
  "stat": "Sum",
  "region": "us-east-1",
  "title": "Execution Results"
}
```

#### Component Performance Metrics

```json
{
  "metrics": [
    ["CostReporting/{Env}", "OperationDuration", "Operation", "cost_collection"],
    ["CostReporting/{Env}", "OperationDuration", "Operation", "report_generation"],
    ["CostReporting/{Env}", "OperationDuration", "Operation", "email_delivery"]
  ],
  "period": 900,
  "stat": "Average",
  "region": "us-east-1",
  "title": "Operation Duration by Component"
}
```

### Business Dashboard Widgets

#### KPI Single Value Widgets

```json
{
  "metrics": [
    ["CostReporting/{Env}", "ReportsGenerated"]
  ],
  "period": 86400,
  "stat": "Sum",
  "region": "us-east-1",
  "title": "Reports Generated (24h)"
}
```

#### Trend Analysis Widgets

```json
{
  "metrics": [
    ["CostReporting/{Env}", "ClientsSucceeded"],
    ["CostReporting/{Env}", "ClientsFailed"]
  ],
  "period": 86400,
  "stat": "Sum",
  "region": "us-east-1",
  "title": "Client Processing Trend"
}
```

### Health Dashboard Widgets

#### Calculated Metrics

```json
{
  "metrics": [
    {
      "expression": "errors / invocations * 100",
      "label": "Error Rate (%)",
      "id": "e1"
    },
    {
      "metric": ["AWS/Lambda", "Errors", "FunctionName", "cost-reporting-{env}-handler"],
      "id": "errors",
      "visible": false
    },
    {
      "metric": ["AWS/Lambda", "Invocations", "FunctionName", "cost-reporting-{env}-handler"],
      "id": "invocations",
      "visible": false
    }
  ],
  "period": 1800,
  "stat": "Sum",
  "region": "us-east-1",
  "title": "Lambda Error Rate"
}
```

## Custom Metric Publishing

### Monitoring Service Integration

The monitoring service automatically publishes custom metrics:

```python
from services.monitoring_service import MonitoringService

# Initialize monitoring service
monitoring = MonitoringService(
    region='us-east-1',
    namespace=f'CostReporting/{environment.title()}'
)

# Publish custom metrics
monitoring.put_metric("ExecutionSucceeded", 1, MetricUnit.COUNT)
monitoring.put_metric("ClientsProcessed", client_count, MetricUnit.COUNT)
monitoring.put_metric("ExecutionDuration", duration, MetricUnit.SECONDS)
```

### Metric Dimensions

Custom metrics support multiple dimensions for filtering:

```python
# Client-specific metrics
monitoring.put_metric("ClientProcessingDuration", duration, MetricUnit.SECONDS, {
    "ClientId": client_id,
    "Success": str(success)
})

# Component-specific metrics
monitoring.put_metric("ComponentError", 1, MetricUnit.COUNT, {
    "Component": "cost_agent",
    "ErrorType": "APIError",
    "Severity": "HIGH"
})
```

## Alarm Integration

### Alarm Configuration

Alarms are automatically created and linked to dashboards:

```python
# Lambda errors alarm
errors_alarm = cloudwatch.Alarm(
    self,
    "LambdaErrorsAlarm",
    alarm_name=f"{self.resource_prefix}-lambda-errors",
    metric=self.lambda_function.metric_errors(period=Duration.minutes(5)),
    threshold=1,
    evaluation_periods=1
)

# Add SNS action
errors_alarm.add_alarm_action(cloudwatch.SnsAction(self.sns_topic))
```

### Alarm States in Dashboards

Dashboard widgets can show alarm states:

```json
{
  "type": "metric",
  "properties": {
    "annotations": {
      "alarms": [
        "arn:aws:cloudwatch:us-east-1:123456789012:alarm:cost-reporting-dev-lambda-errors"
      ]
    },
    "view": "timeSeries",
    "title": "Lambda Errors with Alarm"
  }
}
```

## Dashboard Permissions

### IAM Permissions for Viewing

Users need the following permissions to view dashboards:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "cloudwatch:GetMetricData",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:DescribeAlarmsForMetric"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/cost-reporting-*"
    }
  ]
}
```

### IAM Permissions for Editing

Dashboard editors need additional permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutDashboard",
        "cloudwatch:GetDashboard",
        "cloudwatch:DeleteDashboards",
        "cloudwatch:ListDashboards"
      ],
      "Resource": "*"
    }
  ]
}
```

## Customization Options

### Adding New Widgets

1. **Identify Required Metrics**:
   - Determine what you want to monitor
   - Check if metrics are already available
   - Plan metric dimensions

2. **Create Widget Configuration**:
   ```typescript
   new cloudwatch.GraphWidget({
     title: "Custom Metric",
     left: [
       new cloudwatch.Metric({
         namespace: this.namespace,
         metricName: "CustomMetric",
         statistic: "Average",
         period: Duration.minutes(5)
       })
     ],
     width: 12,
     height: 6
   })
   ```

3. **Add to Dashboard**:
   ```typescript
   dashboard.addWidgets([customWidget]);
   ```

### Modifying Existing Widgets

1. **Update CDK Configuration**:
   - Modify widget properties in the stack
   - Adjust time periods, statistics, or dimensions
   - Update titles and labels

2. **Redeploy Stack**:
   ```bash
   cdk deploy CostReportingStack-{environment}
   ```

### Creating Environment-Specific Dashboards

```typescript
// Different configurations per environment
const widgetConfig = {
  dev: {
    period: Duration.minutes(1),
    evaluationPeriods: 1
  },
  staging: {
    period: Duration.minutes(5),
    evaluationPeriods: 2
  },
  prod: {
    period: Duration.minutes(5),
    evaluationPeriods: 3
  }
};
```

## Troubleshooting

### Common Issues

#### Dashboard Not Showing Data

1. **Check Metric Publishing**:
   - Verify Lambda function is running
   - Check CloudWatch logs for metric publishing
   - Confirm metric namespace and names

2. **Verify Permissions**:
   - Check IAM roles for CloudWatch permissions
   - Verify cross-account access if applicable
   - Test metric publishing manually

3. **Check Time Ranges**:
   - Ensure sufficient data points exist
   - Adjust time range in dashboard
   - Check metric retention periods

#### Widgets Showing Errors

1. **Metric Configuration**:
   - Verify metric names and dimensions
   - Check namespace spelling
   - Confirm resource names

2. **Permission Issues**:
   - Check CloudWatch permissions
   - Verify resource access
   - Test metric queries manually

3. **Resource Availability**:
   - Confirm resources exist
   - Check resource naming
   - Verify region configuration

### Debugging Steps

1. **Test Metric Queries**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace "CostReporting/Dev" \
     --metric-name "ExecutionSucceeded" \
     --start-time 2023-01-01T00:00:00Z \
     --end-time 2023-01-01T01:00:00Z \
     --period 3600 \
     --statistics Sum
   ```

2. **Check Log Groups**:
   ```bash
   aws logs describe-log-groups \
     --log-group-name-prefix "/aws/lambda/cost-reporting"
   ```

3. **Verify Dashboard Configuration**:
   ```bash
   aws cloudwatch get-dashboard \
     --dashboard-name "cost-reporting-dev-operational"
   ```

## Maintenance

### Regular Tasks

1. **Weekly Review**:
   - Check dashboard performance
   - Review metric accuracy
   - Update time ranges if needed

2. **Monthly Optimization**:
   - Analyze widget usage
   - Remove unused metrics
   - Optimize query performance

3. **Quarterly Updates**:
   - Review business requirements
   - Add new metrics as needed
   - Update documentation

### Version Control

1. **CDK Configuration**:
   - All dashboard configurations in code
   - Version controlled changes
   - Automated deployment

2. **Documentation Updates**:
   - Keep documentation current
   - Update screenshots
   - Maintain troubleshooting guides

3. **Change Management**:
   - Test changes in development
   - Review changes with stakeholders
   - Deploy through proper channels

## Best Practices

### Dashboard Design

1. **Keep It Simple**:
   - Focus on key metrics
   - Avoid information overload
   - Use clear titles and labels

2. **Logical Organization**:
   - Group related metrics
   - Use consistent time ranges
   - Maintain visual hierarchy

3. **Performance Optimization**:
   - Limit widgets per dashboard
   - Use appropriate aggregation periods
   - Optimize query complexity

### Metric Strategy

1. **Meaningful Metrics**:
   - Focus on actionable metrics
   - Align with business objectives
   - Provide clear insights

2. **Consistent Naming**:
   - Use standard naming conventions
   - Include environment in namespace
   - Document metric definitions

3. **Appropriate Granularity**:
   - Balance detail with performance
   - Use suitable time periods
   - Consider data retention costs

### Monitoring Strategy

1. **Proactive Monitoring**:
   - Set up appropriate alarms
   - Monitor trends, not just current values
   - Plan for capacity growth

2. **Regular Review**:
   - Assess dashboard effectiveness
   - Gather user feedback
   - Continuously improve

3. **Documentation**:
   - Keep runbooks updated
   - Document troubleshooting procedures
   - Maintain contact information