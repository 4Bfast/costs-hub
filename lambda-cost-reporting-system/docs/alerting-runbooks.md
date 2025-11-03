# Alerting Runbooks

This document provides step-by-step procedures for responding to alerts from the Lambda Cost Reporting System.

## Alert Categories

### Critical Alerts (Immediate Response Required)

- **Lambda Function Errors**
- **Execution Failures**
- **Component Critical Errors**
- **Client Success Rate Below Threshold**

### Warning Alerts (Response Within 1 Hour)

- **Lambda Duration Approaching Timeout**
- **DynamoDB Throttling**
- **Email Delivery Failures**
- **S3 Access Errors**

### Informational Alerts (Response Within 4 Hours)

- **Performance Degradation**
- **Resource Utilization Changes**
- **Configuration Warnings**

## Runbook Procedures

### 1. Lambda Function Errors

**Alert**: `cost-reporting-{env}-lambda-errors`

**Symptoms**:
- Lambda function returning errors
- Failed executions in CloudWatch logs
- SNS notifications about function failures

**Immediate Actions**:

1. **Check Lambda Function Status**:
   ```bash
   aws lambda get-function --function-name cost-reporting-{env}-handler
   ```

2. **Review Recent Logs**:
   - Navigate to CloudWatch Logs
   - Open log group: `/aws/lambda/cost-reporting-{env}-handler`
   - Filter by ERROR level
   - Look for recent error patterns

3. **Check Function Configuration**:
   - Verify environment variables
   - Check timeout and memory settings
   - Validate IAM role permissions

**Investigation Steps**:

1. **Analyze Error Patterns**:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/cost-reporting-{env}-handler \
     --start-time $(date -d '1 hour ago' +%s)000 \
     --filter-pattern "ERROR"
   ```

2. **Check Dependencies**:
   - DynamoDB table accessibility
   - S3 bucket permissions
   - SES service status
   - KMS key availability

3. **Verify Client Configurations**:
   - Check for invalid client data
   - Validate AWS credentials
   - Test cross-account access

**Resolution Actions**:

1. **For Permission Issues**:
   - Update IAM role policies
   - Verify resource ARNs
   - Check cross-account trust relationships

2. **For Configuration Issues**:
   - Update environment variables
   - Adjust timeout/memory settings
   - Redeploy function if needed

3. **For Data Issues**:
   - Validate client configurations
   - Fix corrupted data in DynamoDB
   - Update client credentials

**Escalation**: If errors persist after 30 minutes, escalate to development team.

### 2. Execution Failures

**Alert**: `cost-reporting-{env}-execution-failures`

**Symptoms**:
- Multiple execution failures in short time
- High failure rate in business dashboard
- Client reports not being generated

**Immediate Actions**:

1. **Check Execution Metrics**:
   - Open Operational Dashboard
   - Review "Execution Results" widget
   - Identify failure patterns

2. **Review Execution Logs**:
   - Filter logs by execution_id
   - Look for correlation between failures
   - Check for timeout issues

3. **Verify System Dependencies**:
   - AWS service status dashboard
   - DynamoDB table status
   - S3 bucket accessibility

**Investigation Steps**:

1. **Analyze Failure Distribution**:
   - Check if failures are client-specific
   - Identify common error messages
   - Review timing patterns

2. **Check Resource Limits**:
   - Lambda concurrent executions
   - DynamoDB capacity utilization
   - S3 request rates

3. **Validate Data Integrity**:
   - Check client configuration completeness
   - Verify AWS account accessibility
   - Test Cost Explorer API access

**Resolution Actions**:

1. **For Resource Limits**:
   - Increase Lambda reserved concurrency
   - Scale DynamoDB capacity
   - Implement request throttling

2. **For Data Issues**:
   - Fix invalid client configurations
   - Update expired credentials
   - Validate account permissions

3. **For System Issues**:
   - Restart Lambda function (redeploy)
   - Clear DynamoDB connection pools
   - Check AWS service limits

**Escalation**: If failure rate doesn't improve within 1 hour, escalate to development team.

### 3. Component Critical Errors

**Alert**: `cost-reporting-{env}-component-errors`

**Symptoms**:
- Critical severity errors in specific components
- Component-specific failure patterns
- Degraded functionality in specific areas

**Immediate Actions**:

1. **Identify Affected Component**:
   - Check alert details for component name
   - Review Component Errors widget in dashboard
   - Filter logs by component

2. **Assess Impact**:
   - Determine affected clients
   - Check if other components are working
   - Evaluate business impact

3. **Check Component Health**:
   - Review component-specific metrics
   - Check dependencies
   - Validate configuration

**Component-Specific Procedures**:

#### Cost Agent Errors

**Investigation**:
- Check AWS Cost Explorer API limits
- Verify cross-account role assumptions
- Review cost data query parameters

**Resolution**:
- Implement exponential backoff
- Update IAM policies
- Adjust query time ranges

#### Report Generator Errors

**Investigation**:
- Check S3 bucket permissions
- Verify template files
- Review asset availability

**Resolution**:
- Fix S3 permissions
- Update report templates
- Regenerate missing assets

#### Email Service Errors

**Investigation**:
- Check SES service limits
- Verify email addresses
- Review bounce/complaint rates

**Resolution**:
- Request SES limit increases
- Clean up email lists
- Update email templates

#### Configuration Manager Errors

**Investigation**:
- Check DynamoDB table status
- Verify encryption keys
- Review data consistency

**Resolution**:
- Fix DynamoDB issues
- Rotate encryption keys
- Repair data inconsistencies

**Escalation**: Component-specific issues should be escalated to the component owner within 30 minutes.

### 4. Client Success Rate Below Threshold

**Alert**: `cost-reporting-{env}-client-success-rate`

**Symptoms**:
- Success rate below 80%
- Multiple client processing failures
- Inconsistent report delivery

**Immediate Actions**:

1. **Check Success Rate Trend**:
   - Review Business Dashboard
   - Identify when rate started declining
   - Check for correlation with deployments

2. **Identify Failing Clients**:
   - Filter logs by client_id
   - Look for common failure patterns
   - Check client configuration validity

3. **Assess System Load**:
   - Check Lambda concurrency
   - Review DynamoDB throttling
   - Monitor S3 request rates

**Investigation Steps**:

1. **Client-Specific Analysis**:
   ```bash
   # Get failing clients from logs
   aws logs filter-log-events \
     --log-group-name /aws/lambda/cost-reporting-{env}-handler \
     --filter-pattern "client_id ERROR" \
     --start-time $(date -d '2 hours ago' +%s)000
   ```

2. **Configuration Validation**:
   - Check client AWS credentials
   - Verify account permissions
   - Test cross-account access

3. **Performance Analysis**:
   - Review execution duration trends
   - Check for timeout issues
   - Analyze resource utilization

**Resolution Actions**:

1. **For Configuration Issues**:
   - Update invalid client configurations
   - Refresh expired credentials
   - Fix permission issues

2. **For Performance Issues**:
   - Increase Lambda timeout/memory
   - Optimize query parameters
   - Implement parallel processing

3. **For System Issues**:
   - Scale infrastructure resources
   - Implement circuit breakers
   - Add retry mechanisms

**Escalation**: If success rate doesn't improve within 2 hours, escalate to development team.

### 5. Lambda Duration Approaching Timeout

**Alert**: `cost-reporting-{env}-lambda-duration`

**Symptoms**:
- Execution duration consistently above 10 minutes
- Risk of Lambda timeout (15 minutes)
- Performance degradation

**Immediate Actions**:

1. **Check Current Executions**:
   - Monitor active Lambda executions
   - Check for long-running processes
   - Identify bottlenecks

2. **Review Performance Metrics**:
   - Check Operation Duration by Component
   - Identify slowest operations
   - Look for performance trends

3. **Assess Data Volume**:
   - Check number of clients being processed
   - Review cost data volume
   - Identify large accounts

**Investigation Steps**:

1. **Performance Profiling**:
   - Analyze execution logs for timing
   - Identify slow components
   - Check for inefficient queries

2. **Resource Analysis**:
   - Review Lambda memory utilization
   - Check CPU usage patterns
   - Analyze network latency

3. **Data Analysis**:
   - Identify clients with large datasets
   - Check for inefficient data processing
   - Review query optimization

**Resolution Actions**:

1. **Immediate Optimizations**:
   - Increase Lambda memory allocation
   - Implement parallel processing
   - Add execution checkpoints

2. **Code Optimizations**:
   - Optimize database queries
   - Implement data caching
   - Reduce API calls

3. **Architecture Changes**:
   - Split processing into smaller functions
   - Implement Step Functions workflow
   - Use SQS for async processing

**Escalation**: If duration doesn't improve within 1 hour, escalate to development team.

### 6. Email Delivery Failures

**Alert**: `cost-reporting-{env}-email-failures`

**Symptoms**:
- High email delivery failure rate
- SES bounce/complaint notifications
- Client reports not being delivered

**Immediate Actions**:

1. **Check SES Status**:
   - Review SES sending statistics
   - Check for account suspension
   - Verify sending limits

2. **Analyze Failure Patterns**:
   - Check bounce/complaint rates
   - Identify problematic email addresses
   - Review email content issues

3. **Verify Configuration**:
   - Check SES configuration
   - Verify email templates
   - Test email sending

**Investigation Steps**:

1. **SES Metrics Analysis**:
   ```bash
   aws ses get-send-statistics
   aws ses get-send-quota
   ```

2. **Email List Validation**:
   - Check for invalid email addresses
   - Review bounce/complaint history
   - Validate email format

3. **Content Analysis**:
   - Check for spam-like content
   - Verify email size limits
   - Review attachment policies

**Resolution Actions**:

1. **For SES Issues**:
   - Request limit increases
   - Resolve account suspension
   - Update SES configuration

2. **For Email Issues**:
   - Clean up email lists
   - Fix invalid addresses
   - Update email templates

3. **For Content Issues**:
   - Optimize email content
   - Reduce email size
   - Fix formatting issues

**Escalation**: Email delivery issues should be escalated to the communications team within 2 hours.

## Alert Response Checklist

### Initial Response (First 5 Minutes)

- [ ] Acknowledge alert receipt
- [ ] Check alert severity and priority
- [ ] Review alert details and context
- [ ] Access relevant dashboards
- [ ] Identify immediate impact

### Investigation Phase (Next 15 Minutes)

- [ ] Follow component-specific runbook
- [ ] Gather relevant logs and metrics
- [ ] Identify root cause
- [ ] Assess business impact
- [ ] Document findings

### Resolution Phase (Next 30 Minutes)

- [ ] Implement immediate fixes
- [ ] Monitor system response
- [ ] Verify resolution effectiveness
- [ ] Update stakeholders
- [ ] Document resolution steps

### Follow-up Phase (Next 24 Hours)

- [ ] Monitor for recurrence
- [ ] Implement preventive measures
- [ ] Update documentation
- [ ] Conduct post-incident review
- [ ] Update runbooks if needed

## Escalation Matrix

| Alert Type | Initial Response | Escalation Time | Escalation Target |
|------------|------------------|-----------------|-------------------|
| Critical | Immediate | 30 minutes | Development Team |
| Warning | 1 hour | 2 hours | Team Lead |
| Informational | 4 hours | 8 hours | Product Owner |

## Contact Information

### Primary Contacts

- **Development Team**: dev-team@company.com
- **Operations Team**: ops-team@company.com
- **Product Owner**: product@company.com

### Emergency Contacts

- **On-Call Engineer**: +1-XXX-XXX-XXXX
- **Team Lead**: +1-XXX-XXX-XXXX
- **Engineering Manager**: +1-XXX-XXX-XXXX

## Tools and Resources

### Monitoring Tools

- **CloudWatch Dashboards**: [Dashboard URLs]
- **CloudWatch Logs**: [Log Group Links]
- **AWS Console**: [Console Links]

### Documentation

- **System Architecture**: [Link to architecture docs]
- **API Documentation**: [Link to API docs]
- **Deployment Guide**: [Link to deployment docs]

### Communication Channels

- **Slack Channel**: #cost-reporting-alerts
- **Email List**: cost-reporting-team@company.com
- **Incident Management**: [Link to incident management system]

## Post-Incident Procedures

### Immediate Post-Resolution

1. **Verify System Stability**:
   - Monitor for 30 minutes after resolution
   - Check all related metrics
   - Confirm normal operation

2. **Update Stakeholders**:
   - Send resolution notification
   - Update incident status
   - Provide impact summary

3. **Document Resolution**:
   - Record resolution steps
   - Update runbook if needed
   - Create knowledge base entry

### Post-Incident Review

1. **Schedule Review Meeting**:
   - Within 24 hours for critical incidents
   - Within 1 week for warning incidents
   - Include all relevant stakeholders

2. **Review Process**:
   - Timeline analysis
   - Root cause identification
   - Response effectiveness evaluation
   - Improvement opportunities

3. **Action Items**:
   - Preventive measures
   - Process improvements
   - Documentation updates
   - Training needs

### Continuous Improvement

1. **Monthly Review**:
   - Alert frequency analysis
   - Response time metrics
   - Runbook effectiveness
   - Team feedback

2. **Quarterly Assessment**:
   - Alert threshold optimization
   - Runbook updates
   - Training program review
   - Tool evaluation

3. **Annual Planning**:
   - Monitoring strategy review
   - Resource allocation
   - Technology upgrades
   - Process standardization