# Multi-Cloud Cost Analytics API Implementation

This document describes the implementation of the REST API endpoints for the Multi-Cloud Cost Analytics platform.

## Overview

The API provides comprehensive endpoints for:
- Cost data retrieval and analysis
- AI-powered insights and recommendations
- Client and account management
- Webhook notifications
- Real-time monitoring and alerting

## Architecture

### Components

1. **API Gateway**: AWS API Gateway with Lambda integration
2. **Lambda Functions**: 
   - Main handler for API requests
   - JWT authorizer for authentication
3. **Authentication**: JWT-based authentication with role-based access control
4. **Rate Limiting**: Built-in API Gateway throttling and custom rate limiting
5. **Monitoring**: CloudWatch metrics and dashboards
6. **Security**: WAF protection, CORS configuration, and IP restrictions

### Infrastructure

The API infrastructure is deployed using AWS CDK with the following components:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │────│  Lambda Function │────│   DynamoDB      │
│                 │    │                  │    │                 │
│ - REST API      │    │ - API Handler    │    │ - Cost Data     │
│ - JWT Auth      │    │ - Multi-tenant   │    │ - Client Config │
│ - Rate Limiting │    │ - AI Insights    │    │ - Webhooks      │
│ - CORS          │    │ - Notifications  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌──────────────────┐            │
         │              │   AWS Bedrock    │            │
         │              │                  │            │
         │              │ - LLM Insights   │            │
         │              │ - Recommendations│            │
         │              └──────────────────┘            │
         │                                              │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│      WAF        │    │   CloudWatch     │    │       S3        │
│                 │    │                  │    │                 │
│ - Rate Limiting │    │ - Metrics        │    │ - Reports       │
│ - Security Rules│    │ - Dashboards     │    │ - Assets        │
│ - IP Filtering  │    │ - Alarms         │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## API Endpoints

### Authentication

All endpoints (except `/health`) require authentication via JWT token in the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

### Base URL

- **Development**: `https://{api-id}.execute-api.us-east-1.amazonaws.com/dev`
- **Production**: `https://api.multicloudsanalytics.com/v1`

### Endpoints

#### Health Check
- **GET** `/health` - Health check endpoint (no auth required)

#### Cost Data
- **GET** `/api/v1/cost-data` - Get cost data with filtering
- **GET** `/api/v1/cost-data/summary` - Get cost summary for current month
- **GET** `/api/v1/cost-data/trends` - Get cost trends analysis
- **GET** `/api/v1/cost-data/providers` - Get cost breakdown by provider

#### AI Insights
- **GET** `/api/v1/insights` - Get comprehensive AI insights
- **GET** `/api/v1/insights/anomalies` - Get cost anomalies
- **GET** `/api/v1/insights/recommendations` - Get optimization recommendations
- **GET** `/api/v1/insights/forecasts` - Get cost forecasts

#### Client Management
- **GET** `/api/v1/clients/me` - Get current client information
- **PUT** `/api/v1/clients/me` - Update client configuration
- **GET** `/api/v1/clients/me/accounts` - Get client cloud accounts
- **POST** `/api/v1/clients/me/accounts` - Add cloud account
- **DELETE** `/api/v1/clients/me/accounts/{accountId}` - Remove cloud account

#### Webhooks
- **GET** `/api/v1/webhooks` - List webhooks
- **POST** `/api/v1/webhooks` - Create webhook
- **GET** `/api/v1/webhooks/{webhookId}` - Get webhook details
- **PUT** `/api/v1/webhooks/{webhookId}` - Update webhook
- **DELETE** `/api/v1/webhooks/{webhookId}` - Delete webhook
- **POST** `/api/v1/webhooks/{webhookId}/test` - Test webhook

#### Notifications
- **POST** `/api/v1/notifications/send` - Send notification
- **GET** `/api/v1/notifications/history` - Get notification history
- **GET** `/api/v1/notifications/preferences` - Get notification preferences
- **PUT** `/api/v1/notifications/preferences` - Update notification preferences

## Authentication & Authorization

### JWT Token Structure

```json
{
  "user_id": "user_123",
  "tenant_id": "tenant_456",
  "roles": ["admin", "user"],
  "permissions": [
    "cost_data_read",
    "ai_insights_read",
    "client_config_write",
    "webhook_write"
  ],
  "iat": 1635787200,
  "exp": 1635873600
}
```

### Permissions

- `cost_data_read`: Access to cost data endpoints
- `ai_insights_read`: Access to AI insights endpoints
- `client_config_read`: Read client configuration
- `client_config_write`: Modify client configuration
- `webhook_read`: Read webhook configuration
- `webhook_write`: Manage webhooks
- `notification_send`: Send notifications

### Rate Limiting

Rate limits are applied at multiple levels:

1. **API Gateway Level**: 
   - Dev: 100 requests/hour per endpoint
   - Prod: 1000 requests/hour per endpoint

2. **User Level**: 1000 requests/hour per user
3. **Tenant Level**: 5000 requests/hour per tenant
4. **WAF Level**: 2000 requests per 5 minutes per IP

## Request/Response Format

### Standard Response Format

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "metadata": {
    "timestamp": "2024-10-30T10:00:00Z",
    "request_id": "req_123"
  }
}
```

### Error Response Format

```json
{
  "success": false,
  "error": {
    "message": "Error description",
    "code": 400,
    "details": {
      // Additional error details
    },
    "field_errors": {
      "field_name": "Field-specific error message"
    }
  },
  "timestamp": "2024-10-30T10:00:00Z"
}
```

## Example Requests

### Get Cost Data

```bash
curl -X GET \
  "https://api.multicloudsanalytics.com/v1/api/v1/cost-data?start_date=2024-10-01&end_date=2024-10-30&provider=AWS" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json"
```

### Get AI Insights

```bash
curl -X GET \
  "https://api.multicloudsanalytics.com/v1/api/v1/insights?days=30" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json"
```

### Create Webhook

```bash
curl -X POST \
  "https://api.multicloudsanalytics.com/v1/api/v1/webhooks" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cost Anomaly Alerts",
    "url": "https://example.com/webhook",
    "events": ["anomaly_detected", "budget_exceeded"],
    "secret": "webhook_secret_123"
  }'
```

## Deployment

### Prerequisites

1. AWS CLI configured
2. AWS CDK installed
3. Python 3.11+
4. Required environment variables set

### Environment Variables

```bash
export CDK_DEFAULT_ACCOUNT=123456789012
export CDK_DEFAULT_REGION=us-east-1
export ENVIRONMENT=dev
export JWT_SECRET=your-jwt-secret
```

### Deploy API Gateway

```bash
cd infrastructure
pip install -r requirements.txt
cdk deploy cost-analytics-api-dev
```

### Environment-Specific Configuration

The API supports multiple environments with different configurations:

- **Development**: Open CORS, no WAF, basic rate limiting
- **Staging**: Restricted CORS, WAF enabled, moderate rate limiting
- **Production**: Custom domain, strict security, high rate limits

## Monitoring & Observability

### CloudWatch Metrics

The API automatically publishes metrics to CloudWatch:

- Request count and error rates
- Latency percentiles
- Authentication failures
- Rate limit violations
- Business metrics (clients processed, insights generated)

### Dashboards

Two CloudWatch dashboards are created:

1. **Operational Dashboard**: Technical metrics and health
2. **Business Dashboard**: Business KPIs and trends

### Alarms

Automated alarms for:

- High error rates
- Increased latency
- Authentication failures
- Rate limit violations
- Lambda function errors

## Security Considerations

### Data Protection

- All data encrypted in transit (TLS 1.2+)
- JWT tokens with expiration
- Sensitive data encrypted at rest
- No sensitive data in logs

### Access Control

- Multi-tenant data isolation
- Role-based permissions
- IP-based restrictions (production)
- WAF protection against common attacks

### Compliance

- GDPR compliance for data handling
- SOC 2 Type II controls
- Audit logging for all operations
- Data retention policies

## Testing

### Unit Tests

```bash
cd src
python -m pytest tests/test_api_handler.py -v
```

### Integration Tests

```bash
cd src
python -m pytest tests/test_api_integration.py -v
```

### Load Testing

Use the provided load testing scripts:

```bash
cd tests/load
python load_test_api.py --endpoint https://api.example.com --concurrent 10 --duration 60
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check JWT token validity and permissions
2. **429 Rate Limited**: Reduce request frequency or contact support
3. **500 Internal Error**: Check CloudWatch logs for detailed error information
4. **CORS Issues**: Verify origin is in allowed list for environment

### Debug Mode

Enable debug logging by setting environment variable:

```bash
export LOG_LEVEL=DEBUG
```

### Support

For API support and questions:
- Documentation: [API Specification](./api-specification.yaml)
- Monitoring: CloudWatch dashboards
- Logs: CloudWatch log groups
- Issues: Create support ticket with request ID

## Future Enhancements

### Planned Features

1. **GraphQL API**: Alternative query interface
2. **Streaming API**: Real-time cost updates via WebSocket
3. **Batch Operations**: Bulk data operations
4. **Advanced Analytics**: Custom query builder
5. **Mobile SDK**: Native mobile app integration

### API Versioning

The API follows semantic versioning:
- Major version changes: Breaking changes
- Minor version changes: New features, backward compatible
- Patch version changes: Bug fixes

Current version: `v1.0.0`