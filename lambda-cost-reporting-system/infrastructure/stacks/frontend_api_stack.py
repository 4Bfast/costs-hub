"""
Frontend API Stack with Custom Domain - Using Centralized Configuration
"""

from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_cognito as cognito,
    Duration,
    CfnOutput
)
from constructs import Construct
from config.production import config

class FrontendAPIStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create API Handler Lambda function
        self.api_handler_function = self._create_api_handler_function()
        
        # Create API Gateway
        self.api = self._create_api_gateway()
        
        # Create custom domain
        self._create_custom_domain()
        
        # Create outputs
        self._create_outputs()
    
    def _create_api_handler_function(self) -> _lambda.Function:
        """Create API Handler Lambda function"""
        
        return _lambda.Function(
            self, "APIHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="simple_handlers.api_gateway_handler_simple.lambda_handler",
            code=_lambda.Code.from_asset("../src"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                'CORS_ALLOWED_ORIGINS': ','.join(config.cors_allowed_origins),
                'LOG_LEVEL': 'INFO'
            },
            description="API Gateway Handler for Frontend Integration"
        )
    
    def _create_api_gateway(self) -> apigateway.RestApi:
        """Create API Gateway with custom domain support"""
        
        # Create Cognito authorizer
        authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self, "CognitoAuthorizer",
            cognito_user_pools=[
                cognito.UserPool.from_user_pool_id(
                    self, "UserPool", 
                    user_pool_id=config.COGNITO_USER_POOL_ID
                )
            ]
        )
        
        # Create API Gateway
        api = apigateway.RestApi(
            self, "FrontendAPI",
            rest_api_name="costhub-frontend-api",
            description="CostHub Frontend API with Authentication",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=config.cors_allowed_origins,
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization", "X-Requested-With", "x-request-id", "X-Amz-Date", "X-Api-Key", "X-Amz-Security-Token"],
                allow_credentials=True
            ),
            deploy=True,
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=1000,
                throttling_burst_limit=2000
            )
        )
        
        # Create /api/v1 resource
        api_v1 = api.root.add_resource("api").add_resource("v1")
        
        # Add proxy resource
        proxy = api_v1.add_resource("{proxy+}")
        proxy.add_method(
            "ANY",
            apigateway.LambdaIntegration(
                self.api_handler_function,
                proxy=True
            ),
            authorizer=authorizer,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True,
                        "method.response.header.Access-Control-Allow-Credentials": True
                    }
                )
            ]
        )
        
        return api
    
    def _create_custom_domain(self):
        """Create custom domain for API"""
        
        # Import certificate
        certificate = acm.Certificate.from_certificate_arn(
            self, "Certificate", config.CERTIFICATE_ARN
        )
        
        # Create custom domain
        self.domain = apigateway.DomainName(
            self, "APIDomain",
            domain_name=config.api_domain_name,
            certificate=certificate,
            endpoint_type=apigateway.EndpointType.REGIONAL
        )
        
        # Map domain to API
        self.domain.add_base_path_mapping(
            self.api,
            stage=self.api.deployment_stage
        )
        
        # Create Route53 record
        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name=config.DOMAIN_NAME
        )
        
        route53.ARecord(
            self, "APIAliasRecord",
            zone=hosted_zone,
            record_name=config.API_SUBDOMAIN,
            target=route53.RecordTarget.from_alias(
                targets.ApiGatewayDomain(self.domain)
            )
        )
    
    def _create_outputs(self):
        """Create stack outputs"""
        
        CfnOutput(self, "FrontendAPIUrl", value=self.api.url)
        CfnOutput(self, "CustomDomainUrl", value=config.api_base_url)
        CfnOutput(self, "FrontendAPIId", value=self.api.rest_api_id)
