"""
API Gateway CDK Stack for Multi-Cloud Cost Analytics

This module creates the API Gateway infrastructure with Lambda integration,
authentication, rate limiting, and comprehensive monitoring.
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_apigateway as apigateway,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_wafv2 as waf,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    CfnOutput
)
from constructs import Construct
from typing import Dict, Any, Optional
from config.environments import EnvironmentConfig


class APIGatewayStack(Stack):
    """CDK Stack for API Gateway with Lambda integration"""

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        env_config: EnvironmentConfig,
        lambda_function: _lambda.Function,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_config = env_config
        self.env_name = env_config.name
        self.resource_prefix = f"cost-analytics-api-{env_config.name}"
        self.lambda_function = lambda_function
        
        # Create API Gateway
        self.api_gateway = self._create_api_gateway()
        
        # Create Lambda integration
        self.lambda_integration = self._create_lambda_integration()
        
        # Create API resources and methods
        self._create_api_resources()
        
        # Create deployment
        self.deployment = self._create_deployment()
        
        # Create stages
        self.stage = self._create_stage()
        
        # Create custom domain (if configured)
        if env_config.api_domain_name:
            self.custom_domain = self._create_custom_domain()
        
        # Create WAF (Web Application Firewall)
        if env_config.enable_waf:
            self.waf_acl = self._create_waf()
        
        # Create CloudWatch dashboard for API metrics
        self._create_api_dashboard()
        
        # Output API URL
        self._create_outputs()

    def _create_api_gateway(self) -> apigateway.RestApi:
        """Create API Gateway REST API"""
        
        # Create CloudWatch log group for API Gateway
        log_group = logs.LogGroup(
            self,
            "APIGatewayLogGroup",
            log_group_name=f"/aws/apigateway/{self.resource_prefix}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        return apigateway.RestApi(
            self,
            "MultiCloudCostAnalyticsAPI",
            rest_api_name=f"{self.resource_prefix}",
            description="Multi-Cloud Cost Analytics API with AI insights",
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            ),
            deploy=True,  # Enable automatic deployment
            cloud_watch_role=True,
            cloud_watch_role_removal_policy=RemovalPolicy.DESTROY,
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=self.env_config.cors_allowed_origins,
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=[
                    "Content-Type",
                    "X-Amz-Date",
                    "Authorization",
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                    "X-Amz-User-Agent",
                    "x-request-id"
                ],
                max_age=Duration.hours(1)
            ),
            policy=self._create_api_resource_policy() if self.env_config.restrict_api_access else None
        )

    def _create_api_resource_policy(self) -> iam.PolicyDocument:
        """Create resource policy for API Gateway"""
        return iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.AnyPrincipal()],
                    actions=["execute-api:Invoke"],
                    resources=["*"],
                    conditions={
                        "IpAddress": {
                            "aws:SourceIp": self.env_config.allowed_ip_ranges
                        }
                    }
                )
            ]
        )

    def _create_lambda_integration(self) -> apigateway.LambdaIntegration:
        """Create Lambda integration for API Gateway"""
        return apigateway.LambdaIntegration(
            self.lambda_function,
            proxy=True,
            allow_test_invoke=True,
            timeout=Duration.seconds(29),  # API Gateway max timeout
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                        "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                        "method.response.header.Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,OPTIONS'"
                    }
                ),
                apigateway.IntegrationResponse(
                    status_code="400",
                    selection_pattern="4\\d{2}"
                ),
                apigateway.IntegrationResponse(
                    status_code="500",
                    selection_pattern="5\\d{2}"
                )
            ]
        )

    def _create_api_resources(self) -> None:
        """Create API resources and methods"""
        
        # Health check endpoint (no auth required)
        health_resource = self.api_gateway.root.add_resource("health")
        health_resource.add_method(
            "GET",
            self.lambda_integration,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True
                    }
                )
            ]
        )
        
        # API v1 resource
        api_v1 = self.api_gateway.root.add_resource("api").add_resource("v1")
        
        # Create authorizer for authenticated endpoints
        authorizer = self._create_authorizer()
        
        # Cost data endpoints
        cost_data = api_v1.add_resource("cost-data")
        self._add_authenticated_method(cost_data, "GET", authorizer)
        
        cost_summary = cost_data.add_resource("summary")
        self._add_authenticated_method(cost_summary, "GET", authorizer)
        
        cost_trends = cost_data.add_resource("trends")
        self._add_authenticated_method(cost_trends, "GET", authorizer)
        
        cost_providers = cost_data.add_resource("providers")
        self._add_authenticated_method(cost_providers, "GET", authorizer)
        
        # AI insights endpoints
        insights = api_v1.add_resource("insights")
        self._add_authenticated_method(insights, "GET", authorizer)
        
        anomalies = insights.add_resource("anomalies")
        self._add_authenticated_method(anomalies, "GET", authorizer)
        
        recommendations = insights.add_resource("recommendations")
        self._add_authenticated_method(recommendations, "GET", authorizer)
        
        forecasts = insights.add_resource("forecasts")
        self._add_authenticated_method(forecasts, "GET", authorizer)
        
        # Client management endpoints
        clients = api_v1.add_resource("clients")
        me = clients.add_resource("me")
        self._add_authenticated_method(me, "GET", authorizer)
        self._add_authenticated_method(me, "PUT", authorizer)
        
        accounts = me.add_resource("accounts")
        self._add_authenticated_method(accounts, "GET", authorizer)
        self._add_authenticated_method(accounts, "POST", authorizer)
        
        account_id = accounts.add_resource("{accountId}")
        self._add_authenticated_method(account_id, "DELETE", authorizer)
        
        # Webhook endpoints
        webhooks = api_v1.add_resource("webhooks")
        self._add_authenticated_method(webhooks, "GET", authorizer)
        self._add_authenticated_method(webhooks, "POST", authorizer)
        
        webhook_id = webhooks.add_resource("{webhookId}")
        self._add_authenticated_method(webhook_id, "GET", authorizer)
        self._add_authenticated_method(webhook_id, "PUT", authorizer)
        self._add_authenticated_method(webhook_id, "DELETE", authorizer)
        
        webhook_test = webhook_id.add_resource("test")
        self._add_authenticated_method(webhook_test, "POST", authorizer)
        
        # Notification endpoints
        notifications = api_v1.add_resource("notifications")
        
        send_notification = notifications.add_resource("send")
        self._add_authenticated_method(send_notification, "POST", authorizer)
        
        notification_history = notifications.add_resource("history")
        self._add_authenticated_method(notification_history, "GET", authorizer)
        
        notification_preferences = notifications.add_resource("preferences")
        self._add_authenticated_method(notification_preferences, "GET", authorizer)
        self._add_authenticated_method(notification_preferences, "PUT", authorizer)

    def _create_authorizer(self) -> apigateway.RequestAuthorizer:
        """Create JWT authorizer for API Gateway"""
        
        # Create authorizer Lambda function
        authorizer_function = _lambda.Function(
            self,
            "APIAuthorizer",
            function_name=f"{self.resource_prefix}-authorizer",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="authorizer.lambda_handler",
            code=_lambda.Code.from_asset("../src/handlers"),
            timeout=Duration.seconds(30),
            environment={
                "JWT_SECRET": self.env_config.jwt_secret,
                "ENVIRONMENT": self.env_name
            }
        )
        
        return apigateway.RequestAuthorizer(
            self,
            "JWTAuthorizer",
            handler=authorizer_function,
            identity_sources=[
                apigateway.IdentitySource.header("Authorization"),
                apigateway.IdentitySource.header("X-Api-Key")
            ],
            results_cache_ttl=Duration.minutes(5)
        )

    def _add_authenticated_method(
        self, 
        resource: apigateway.Resource, 
        method: str, 
        authorizer: apigateway.RequestAuthorizer
    ) -> None:
        """Add authenticated method to resource"""
        
        # Create request validator
        request_validator = self.api_gateway.add_request_validator(
            f"{resource.path.replace('/', '-').replace('{', '').replace('}', '')}-{method}-validator",
            validate_request_body=method in ["POST", "PUT"],
            validate_request_parameters=True
        )
        
        resource.add_method(
            method,
            self.lambda_integration,
            authorizer=authorizer,
            request_validator=request_validator,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True
                    }
                ),
                apigateway.MethodResponse(status_code="400"),
                apigateway.MethodResponse(status_code="401"),
                apigateway.MethodResponse(status_code="403"),
                apigateway.MethodResponse(status_code="404"),
                apigateway.MethodResponse(status_code="429"),
                apigateway.MethodResponse(status_code="500")
            ]
        )

    def _create_deployment(self) -> apigateway.Deployment:
        """Create API Gateway deployment"""
        return apigateway.Deployment(
            self,
            "APIDeployment",
            api=self.api_gateway,
            description=f"Deployment for {self.env_name} environment"
        )

    def _create_stage(self) -> apigateway.Stage:
        """Create API Gateway stage"""
        
        # Create CloudWatch log group for stage
        stage_log_group = logs.LogGroup(
            self,
            "APIStageLogGroup",
            log_group_name=f"/aws/apigateway/{self.resource_prefix}/{self.env_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        return apigateway.Stage(
            self,
            "APIStage",
            deployment=self.deployment,
            stage_name=self.env_name,
            description=f"API stage for {self.env_name} environment",
            data_trace_enabled=True,
            logging_level=apigateway.MethodLoggingLevel.INFO,
            access_log_destination=apigateway.LogGroupLogDestination(stage_log_group),
            access_log_format=apigateway.AccessLogFormat.json_with_standard_fields(
                caller=True,
                http_method=True,
                ip=True,
                protocol=True,
                request_time=True,
                resource_path=True,
                response_length=True,
                status=True,
                user=True
            ),
            throttling_rate_limit=self.env_config.api_throttle_rate_limit,
            throttling_burst_limit=self.env_config.api_throttle_burst_limit,
            variables={
                "environment": self.env_name,
                "version": "1.0.0"
            }
        )

    def _create_custom_domain(self) -> apigateway.DomainName:
        """Create custom domain for API Gateway"""
        
        # Get certificate from ACM
        certificate = acm.Certificate.from_certificate_arn(
            self,
            "APICertificate",
            certificate_arn=self.env_config.certificate_arn
        )
        
        # Create custom domain
        domain = apigateway.DomainName(
            self,
            "APICustomDomain",
            domain_name=self.env_config.api_domain_name,
            certificate=certificate,
            endpoint_type=apigateway.EndpointType.REGIONAL,
            security_policy=apigateway.SecurityPolicy.TLS_1_2
        )
        
        # Create base path mapping
        domain.add_base_path_mapping(
            self.api_gateway,
            base_path="v1",
            stage=self.stage
        )
        
        # Create Route 53 record (if hosted zone is provided)
        if self.env_config.hosted_zone_id:
            hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
                self,
                "HostedZone",
                hosted_zone_id=self.env_config.hosted_zone_id,
                zone_name=self.env_config.api_domain_name.split('.', 1)[1]
            )
            
            route53.ARecord(
                self,
                "APIAliasRecord",
                zone=hosted_zone,
                record_name=self.env_config.api_domain_name.split('.')[0],
                target=route53.RecordTarget.from_alias(
                    targets.ApiGatewayDomain(domain)
                )
            )
        
        return domain

    def _create_waf(self) -> waf.CfnWebACL:
        """Create WAF Web ACL for API Gateway"""
        
        return waf.CfnWebACL(
            self,
            "APIWebACL",
            name=f"{self.resource_prefix}-waf",
            scope="REGIONAL",
            default_action=waf.CfnWebACL.DefaultActionProperty(allow={}),
            rules=[
                # Rate limiting rule
                waf.CfnWebACL.RuleProperty(
                    name="RateLimitRule",
                    priority=1,
                    statement=waf.CfnWebACL.StatementProperty(
                        rate_based_statement=waf.CfnWebACL.RateBasedStatementProperty(
                            limit=2000,  # 2000 requests per 5 minutes
                            aggregate_key_type="IP"
                        )
                    ),
                    action=waf.CfnWebACL.RuleActionProperty(block={}),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="RateLimitRule"
                    )
                ),
                # AWS managed rules
                waf.CfnWebACL.RuleProperty(
                    name="AWSManagedRulesCommonRuleSet",
                    priority=2,
                    override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
                    statement=waf.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesCommonRuleSet"
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="CommonRuleSetMetric"
                    )
                ),
                # Known bad inputs rule
                waf.CfnWebACL.RuleProperty(
                    name="AWSManagedRulesKnownBadInputsRuleSet",
                    priority=3,
                    override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
                    statement=waf.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesKnownBadInputsRuleSet"
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="KnownBadInputsRuleSetMetric"
                    )
                )
            ],
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name=f"{self.resource_prefix}-waf"
            )
        )

    def _create_api_dashboard(self) -> None:
        """Create CloudWatch dashboard for API metrics"""
        
        dashboard = cloudwatch.Dashboard(
            self,
            "APIDashboard",
            dashboard_name=f"{self.resource_prefix}-metrics",
            period_override=cloudwatch.PeriodOverride.AUTO,
            start="-PT24H"
        )
        
        # API Gateway metrics
        api_metrics_widget = cloudwatch.GraphWidget(
            title="API Gateway Metrics",
            left=[
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="Count",
                    dimensions_map={"ApiName": self.api_gateway.rest_api_name},
                    statistic="Sum",
                    period=Duration.minutes(5),
                    label="Requests"
                ),
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="4XXError",
                    dimensions_map={"ApiName": self.api_gateway.rest_api_name},
                    statistic="Sum",
                    period=Duration.minutes(5),
                    label="4XX Errors"
                ),
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="5XXError",
                    dimensions_map={"ApiName": self.api_gateway.rest_api_name},
                    statistic="Sum",
                    period=Duration.minutes(5),
                    label="5XX Errors"
                )
            ],
            width=12,
            height=6
        )
        
        # Latency metrics
        latency_widget = cloudwatch.GraphWidget(
            title="API Latency",
            left=[
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="Latency",
                    dimensions_map={"ApiName": self.api_gateway.rest_api_name},
                    statistic="Average",
                    period=Duration.minutes(5),
                    label="Average Latency"
                ),
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="IntegrationLatency",
                    dimensions_map={"ApiName": self.api_gateway.rest_api_name},
                    statistic="Average",
                    period=Duration.minutes(5),
                    label="Integration Latency"
                )
            ],
            left_y_axis=cloudwatch.YAxisProps(
                label="Latency (ms)",
                min=0
            ),
            width=12,
            height=6
        )
        
        dashboard.add_widgets(api_metrics_widget, latency_widget)

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self,
            "APIGatewayURL",
            value=self.api_gateway.url,
            description="API Gateway URL",
            export_name=f"{self.resource_prefix}-url"
        )
        
        CfnOutput(
            self,
            "APIGatewayStageURL",
            value=self.stage.url_for_path(),
            description="API Gateway Stage URL",
            export_name=f"{self.resource_prefix}-stage-url"
        )
        
        if hasattr(self, 'custom_domain'):
            CfnOutput(
                self,
                "CustomDomainURL",
                value=f"https://{self.env_config.api_domain_name}/v1",
                description="Custom Domain URL",
                export_name=f"{self.resource_prefix}-custom-domain-url"
            )
        
        CfnOutput(
            self,
            "APIGatewayId",
            value=self.api_gateway.rest_api_id,
            description="API Gateway ID",
            export_name=f"{self.resource_prefix}-id"
        )