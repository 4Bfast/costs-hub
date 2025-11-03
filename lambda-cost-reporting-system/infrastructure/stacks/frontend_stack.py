"""
Frontend Stack - S3 + CloudFront - Using Centralized Configuration
"""

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    aws_s3_deployment as s3deploy,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct
from config.production import config

class FrontendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create S3 bucket
        self.bucket = self._create_s3_bucket()
        
        # Create CloudFront distribution
        self.distribution = self._create_cloudfront_distribution()
        
        # Create outputs
        self._create_outputs()
    
    def _create_s3_bucket(self) -> s3.Bucket:
        """Create S3 bucket for static website"""
        
        bucket = s3.Bucket(
            self, "FrontendBucket",
            bucket_name="costhub-frontend-4bfast",
            website_index_document="index.html",
            website_error_document="index.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False
            ),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
        
        return bucket
    
    def _create_cloudfront_distribution(self) -> cloudfront.Distribution:
        """Create CloudFront distribution"""
        
        # Import certificate
        certificate = acm.Certificate.from_certificate_arn(
            self, "Certificate", config.CERTIFICATE_ARN
        )
        
        # Create distribution
        distribution = cloudfront.Distribution(
            self, "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(self.bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                compress=True
            ),
            domain_names=["costhub.4bfast.com.br"],
            certificate=certificate,
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html"
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html"
                )
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100
        )
        
        return distribution
    
    def _create_outputs(self):
        """Create stack outputs"""
        
        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "DistributionId", value=self.distribution.distribution_id)
        CfnOutput(self, "DistributionDomainName", value=self.distribution.distribution_domain_name)
        CfnOutput(self, "WebsiteUrl", value=f"https://costhub.4bfast.com.br")
        CfnOutput(self, "CloudflareCNAME", value=self.distribution.distribution_domain_name)
