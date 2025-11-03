"""
Authentication Stack with Cognito User Pool - Using Centralized Configuration
"""

from aws_cdk import (
    Stack,
    aws_cognito as cognito,
    CfnOutput,
    Duration
)
from constructs import Construct
from config.production import config

class AuthStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create Cognito User Pool
        self.user_pool = cognito.UserPool(
            self, "CostHubUserPool",
            user_pool_name="costhub-users",
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY
        )
        
        # Create User Pool Client
        self.user_pool_client = cognito.UserPoolClient(
            self, "CostHubUserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name="costhub-web-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=True
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE
                ],
                callback_urls=[
                    f"{config.frontend_base_url}/auth/callback",
                    "http://localhost:3000/auth/callback"
                ],
                logout_urls=[
                    f"{config.frontend_base_url}/auth/logout",
                    "http://localhost:3000/auth/logout"
                ]
            )
        )
        
        # Create Cognito Domain
        self.user_pool_domain = cognito.UserPoolDomain(
            self, "CostHubUserPoolDomain",
            user_pool=self.user_pool,
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"costhub-auth-{config.DOMAIN_NAME.replace('.', '-')}"
            )
        )
        
        # Outputs
        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id)
        CfnOutput(self, "CognitoDomainUrl", 
                 value=f"https://{self.user_pool_domain.domain_name}.auth.{config.AWS_REGION}.amazoncognito.com")
