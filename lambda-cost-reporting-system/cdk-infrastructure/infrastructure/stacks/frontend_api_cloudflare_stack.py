"""
Frontend API Stack with Custom Domain (Cloudflare DNS)
"""

from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_certificatemanager as acm,
    Duration,
    CfnOutput
)
from constructs import Construct

class FrontendAPICloudflareStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, certificate_arn: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.certificate_arn = certificate_arn
        
        # Create Lambda functions
        self.authorizer_function = self._create_authorizer_function()
        self.api_handler_function = self._create_api_handler_function()
        
        # Create API Gateway
        self.api = self._create_api_gateway()
        
        # Create custom domain (without Route53)
        self._create_custom_domain()
        
        # Create outputs
        self._create_outputs()
    
    def _create_authorizer_function(self) -> _lambda.Function:
        """Create JWT Authorizer Lambda function"""
        
        return _lambda.Function(
            self, "JWTAuthorizer",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="simple_handlers.api_gateway_authorizer_simple.lambda_handler",
            code=_lambda.Code.from_asset("../src"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                'JWT_SECRET': 'prod-secret-key-4bfast-costhub-2025',
                'LOG_LEVEL': 'INFO'
            },
            description="JWT Authorizer for CostHub Production API"
        )
    
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
                'BACKEND_BASE_URL': 'https://jrltysmyg5.execute-api.us-east-1.amazonaws.com',
                'LOG_LEVEL': 'INFO'
            },
            description="API Gateway Handler for CostHub Production"
        )
    
    def _create_api_gateway(self) -> apigateway.RestApi:
        """Create API Gateway with custom domain support"""
        
        # Create authorizer
        authorizer = apigateway.RequestAuthorizer(
            self, "APIAuthorizer",
            handler=self.authorizer_function,
            identity_sources=[apigateway.IdentitySource.header("Authorization")]
        )
        
        # Create API Gateway
        api = apigateway.RestApi(
            self, "FrontendAPI",
            rest_api_name="costhub-frontend-api-prod",
            description="CostHub Production API with Authentication",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["https://*.costhub.4bfast.com.br"],
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization", "X-Requested-With", "x-request-id"],
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
            apigateway.LambdaIntegration(self.api_handler_function),
            authorizer=authorizer
        )
        
        return api
    
    def _create_custom_domain(self):
        """Create custom domain for API (Cloudflare DNS)"""
        
        # Import certificate
        certificate = acm.Certificate.from_certificate_arn(
            self, "Certificate", self.certificate_arn
        )
        
        # Create custom domain
        self.domain = apigateway.DomainName(
            self, "APIDomain",
            domain_name="api-costhub.4bfast.com.br",
            certificate=certificate,
            endpoint_type=apigateway.EndpointType.REGIONAL
        )
        
        # Map domain to API
        self.domain.add_base_path_mapping(
            self.api,
            stage=self.api.deployment_stage
        )
    
    def _create_outputs(self):
        """Create stack outputs"""
        
        CfnOutput(self, "FrontendAPIUrl", value=self.api.url)
        CfnOutput(self, "CustomDomainUrl", value=f"https://api-costhub.4bfast.com.br")
        CfnOutput(self, "CloudflareCNAME", value=self.domain.domain_name_alias_domain_name)
        CfnOutput(self, "FrontendAPIId", value=self.api.rest_api_id)
