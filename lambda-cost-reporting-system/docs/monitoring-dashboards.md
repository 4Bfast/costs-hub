# CloudWatch Dashboards Guide

This document describes the CloudWatch dashboards created for the Lambda Cost Reporting System and how to use them for monitoring and troubleshooting.

## Dashboard Overview

The system creates three main dashboards to provide comprehensive monitoring coverage:

1. **Operational Dashboard** - Real-time system health and performance
2. **Business Dashboard** - Business metrics and KPIs
3. **System Health Dashboard** - Component health and alarm status

## Dashboard Details

### 1. Operational Dashboard (`{environment}-operational`)

**Purpose**: Monitor real-time system performance and identify operational issues.

**Key Widgets**:

- **Lambda Invocations**: Shows function execution frequency
- **Lambda Errors**: Tracks function errors over time
- **Lambda Duration**: Monitors execution time and timeout risks
- **Execution Results**: Success vs failure rates for report executions
- **Client Success Rate**: Percentage of clients processed successfully
- **Operation Duration by Component**: Performance breakdown by system component
- **Component Errors**: Error distribution across components
- **DynamoDB Operations**: Database read/write capacity consumption
- **S3 Operations**: Storage utilization and object count

**Time Range**: Last 24 hours (auto-refreshing)

**Use Cases**:
- Daily operational monitoring
- Performance troubleshooting
- Capacity planning
- Real-time issue detection

### 2. Business Dashboard (`{environment}-business`)

**Purpose**: Track business metrics and long-term trends.

**Key Widgets**:

- **Reports Generated (24h)**: Total reports created in last 24 hours
- **Emails Sent (24h)**: Total emails delivered in last 24 hours
- **Clients Processed (24h)**: Number of clients processed in last 24 hours
- **Success Rate (24h)**: Overall system success rate
- **Daily Reports Trend**: Historical report generation trends
- **Client Processing Trend**: Success/failure trends over time
- **Average Execution Duration**: Performance trends
- **Email Recipients**: Distribution of email recipients
- **Errors by Severity**: Error categorization and trends

**Time Range**: Last 7 days

**Use Cases**:
- Business reporting
- Trend analysis
- Capacity planning
- SLA monitoring

### 3. System Health Dashboard (`{environment}-health`)

**Purpose**: Monitor system health and alarm status.

**Key Widgets**:

- **Lambda Error Rate**: Calculated error percentage
- **DynamoDB Throttles**: Database throttling events
- **S3 4xx Errors**: Storage access errors
- **Recent Alarm State Changes**: Log of alarm state transitions

**Time Range**: Last 6 hours

**Use Cases**:
- Health checks
- Incident response
- Alarm investigation
- System status verification

## Accessing Dashboards

### AWS Console

1. Navigate to CloudWatch in the AWS Console
2. Select "Dashboards" from the left menu
3. Look for dashboards with the naming pattern:
   - `cost-reporting-{environment}-operational`
   - `cost-reporting-{environment}-business`
   - `cost-reporting-{environment}-health`

### Direct URLs

Dashboards can be accessed directly using URLs in the format:
```
https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name={dashboard-name}
```

## Key Metrics to Monitor

### Critical Metrics (Immediate Attention Required)

1. **Lambda Error Rate > 5%**
   - Indicates system instability
   - Check Lambda logs for error details
   - Verify AWS service availability

2. **Client Success Rate < 80%**
   - Multiple client processing failures
   - Check client configurations
   - Verify AWS account access

3. **Execution Duration > 10 minutes**
   - Risk of Lambda timeout
   - Investigate performance bottlenecks
   - Consider optimization

4. **Component Errors (CRITICAL severity)**
   - System component failures
   - Immediate investigation required
   - Check component-specific logs

### Warning Metrics (Monitor Closely)

1. **DynamoDB Throttles > 0**
   - Database capacity issues
   - Consider increasing capacity
   - Review query patterns

2. **S3 4xx Errors > 0**
   - Storage access issues
   - Check IAM permissions
   - Verify bucket configuration

3. **Email Delivery Failures > 5%**
   - SES delivery issues
   - Check recipient addresses
   - Verify SES configuration

## Dashboard Customization

### Adding Custom Widgets

1. Open the dashboard in edit mode
2. Click "Add widget"
3. Select widget type (Graph, Number, Log, etc.)
4. Configure metrics and dimensions
5. Save the dashboard

### Modifying Time Ranges

1. Use the time picker in the top-right corner
2. Select predefined ranges or custom periods
3. Enable auto-refresh for real-time monitoring

### Creating Alerts from Widgets

1. Click on any metric in a widget
2. Select "Create alarm"
3. Configure threshold and notification settings
4. Link to SNS topic for notifications

## Best Practices

### Daily Monitoring Routine

1. **Morning Check** (Operational Dashboard):
   - Review overnight execution results
   - Check for any error spikes
   - Verify client success rates

2. **Weekly Review** (Business Dashboard):
   - Analyze report generation trends
   - Review client processing patterns
   - Identify performance improvements

3. **Health Monitoring** (System Health Dashboard):
   - Check alarm status
   - Review error distributions
   - Verify system component health

### Troubleshooting Workflow

1. **Start with System Health Dashboard**
   - Check overall system status
   - Review active alarms
   - Identify affected components

2. **Drill Down with Operational Dashboard**
   - Analyze specific metrics
   - Identify time ranges of issues
   - Correlate multiple metrics

3. **Use Business Dashboard for Impact Assessment**
   - Determine business impact
   - Identify affected clients
   - Assess SLA compliance

### Performance Optimization

1. **Monitor Trends**:
   - Track execution duration over time
   - Identify performance degradation
   - Plan capacity adjustments

2. **Resource Utilization**:
   - Monitor DynamoDB capacity usage
   - Track S3 storage growth
   - Optimize Lambda memory allocation

3. **Error Analysis**:
   - Categorize errors by component
   - Identify recurring issues
   - Implement preventive measures

## Integration with Alerting

The dashboards integrate with the CloudWatch alarm system:

- **Metric-based Alarms**: Automatically trigger based on threshold breaches
- **Composite Alarms**: Combine multiple metrics for complex conditions
- **SNS Integration**: Send notifications to administrators
- **Dashboard Links**: Include dashboard URLs in alert notifications

## Maintenance

### Regular Tasks

1. **Monthly Dashboard Review**:
   - Verify widget relevance
   - Update time ranges if needed
   - Add new metrics as system evolves

2. **Quarterly Optimization**:
   - Review dashboard performance
   - Consolidate similar widgets
   - Update documentation

3. **Annual Assessment**:
   - Evaluate dashboard effectiveness
   - Gather user feedback
   - Plan dashboard improvements

### Version Control

- Dashboard configurations are managed through CDK
- Changes should be made in code and deployed
- Manual changes in console should be documented
- Regular backups of dashboard configurations

## Troubleshooting Common Issues

### Dashboard Not Loading

1. Check IAM permissions for CloudWatch access
2. Verify dashboard exists in correct region
3. Check for resource naming conflicts

### Missing Metrics

1. Verify Lambda function is publishing custom metrics
2. Check metric namespace and dimensions
3. Ensure sufficient data points exist

### Performance Issues

1. Reduce time range for large datasets
2. Limit number of metrics per widget
3. Use appropriate aggregation periods

## Support and Escalation

For dashboard-related issues:

1. **Level 1**: Check dashboard documentation and troubleshooting guide
2. **Level 2**: Review CloudWatch logs and metrics
3. **Level 3**: Contact AWS support for CloudWatch issues
4. **Level 4**: Escalate to development team for custom metric issues