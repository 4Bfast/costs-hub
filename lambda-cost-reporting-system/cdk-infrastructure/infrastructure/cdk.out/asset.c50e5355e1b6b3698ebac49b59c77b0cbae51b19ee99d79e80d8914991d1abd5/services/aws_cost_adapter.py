"""
AWS Cost Adapter

This module implements the AWS-specific cost collection adapter for the multi-cloud
cost analytics platform. It integrates with AWS Cost Explorer API to collect
cost and usage data.
"""

import boto3
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import logging
from botocore.exceptions import ClientError, BotoCoreError

from .cloud_provider_adapter import CloudProviderAdapter
from ..models.provider_models import (
    AWSCredentials, CredentialValidation, DateRange, ProviderCostData,
    CollectionResult, ProviderAccount, ProviderService, ProviderType,
    DataCollectionStatus, ValidationStatus, AuthenticationError,
    AuthorizationError, RateLimitError, ServiceUnavailableError
)
from ..models.multi_cloud_models import ServiceCategory, Currency


logger = logging.getLogger(__name__)


class AWSCostAdapter(CloudProviderAdapter):
    """AWS Cost Explorer adapter for collecting cost data."""
    
    def __init__(self, credentials: AWSCredentials):
        """
        Initialize AWS cost adapter.
        
        Args:
            credentials: AWS credentials
        """
        super().__init__(credentials)
        self.aws_credentials = credentials
        self._cost_explorer_client = None
        self._organizations_client = None
        self._session = None
    
    @property
    def provider_name(self) -> str:
        """Get the human-readable provider name."""
        return "Amazon Web Services"
    
    @property
    def supported_regions(self) -> List[str]:
        """Get list of supported AWS regions."""
        return [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1',
            'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
            'ap-northeast-2', 'ap-south-1', 'sa-east-1',
            'ca-central-1', 'eu-north-1', 'ap-east-1',
            'me-south-1', 'af-south-1', 'eu-south-1'
        ]
    
    @property
    def default_currency(self) -> str:
        """Get the default currency for AWS."""
        return "USD"
    
    async def _initialize_client(self):
        """Initialize AWS clients."""
        try:
            if self.aws_credentials.credential_type.value == 'iam_role':
                # Use STS to assume role
                sts_client = boto3.client('sts', region_name=self.aws_credentials.region)
                
                assume_role_kwargs = {
                    'RoleArn': self.aws_credentials.role_arn,
                    'RoleSessionName': f'cost-analytics-{int(datetime.utcnow().timestamp())}'
                }
                
                if self.aws_credentials.external_id:
                    assume_role_kwargs['ExternalId'] = self.aws_credentials.external_id
                
                response = sts_client.assume_role(**assume_role_kwargs)
                credentials = response['Credentials']
                
                # Create session with assumed role credentials
                self._session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken'],
                    region_name=self.aws_credentials.region
                )
            else:
                # Use access key credentials
                self._session = boto3.Session(
                    aws_access_key_id=self.aws_credentials.access_key_id,
                    aws_secret_access_key=self.aws_credentials.secret_access_key,
                    aws_session_token=self.aws_credentials.session_token,
                    region_name=self.aws_credentials.region
                )
            
            # Initialize service clients
            self._cost_explorer_client = self._session.client('ce', region_name='us-east-1')
            self._organizations_client = self._session.client('organizations', region_name='us-east-1')
            
            self.logger.info("AWS clients initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AWS clients: {e}")
            raise AuthenticationError(
                provider=ProviderType.AWS,
                message=f"Failed to initialize AWS clients: {str(e)}"
            )
    
    async def _cleanup_client(self):
        """Cleanup AWS clients."""
        self._cost_explorer_client = None
        self._organizations_client = None
        self._session = None
    
    async def validate_credentials(self) -> CredentialValidation:
        """
        Validate AWS credentials and permissions.
        
        Returns:
            CredentialValidation with validation results
        """
        start_time = datetime.utcnow()
        
        try:
            await self._initialize_client()
            
            # Test Cost Explorer access
            try:
                # Try to get cost and usage for a small date range
                test_end_date = date.today()
                test_start_date = test_end_date - timedelta(days=1)
                
                response = self._cost_explorer_client.get_cost_and_usage(
                    TimePeriod={
                        'Start': test_start_date.strftime('%Y-%m-%d'),
                        'End': test_end_date.strftime('%Y-%m-%d')
                    },
                    Granularity='DAILY',
                    Metrics=['BlendedCost']
                )
                
                permissions = ['ce:GetCostAndUsage']
                
                # Test additional permissions
                try:
                    self._cost_explorer_client.get_dimension_values(
                        TimePeriod={
                            'Start': test_start_date.strftime('%Y-%m-%d'),
                            'End': test_end_date.strftime('%Y-%m-%d')
                        },
                        Dimension='SERVICE'
                    )
                    permissions.append('ce:GetDimensionValues')
                except ClientError:
                    pass
                
                # Test Organizations access (optional)
                try:
                    self._organizations_client.describe_organization()
                    permissions.extend(['organizations:DescribeOrganization', 'organizations:ListAccounts'])
                except ClientError:
                    pass  # Organizations access is optional
                
                validation_duration = (datetime.utcnow() - start_time).total_seconds()
                
                return CredentialValidation(
                    status=ValidationStatus.VALID,
                    is_valid=True,
                    permissions=permissions,
                    validated_at=datetime.utcnow(),
                    validation_duration_seconds=validation_duration,
                    additional_info={
                        'credential_type': self.aws_credentials.credential_type.value,
                        'region': self.aws_credentials.region
                    }
                )
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                
                if error_code in ['UnauthorizedOperation', 'AccessDenied']:
                    return CredentialValidation(
                        status=ValidationStatus.INSUFFICIENT_PERMISSIONS,
                        is_valid=False,
                        error_message=f"Insufficient permissions: {error_message}",
                        missing_permissions=['ce:GetCostAndUsage'],
                        validated_at=datetime.utcnow(),
                        validation_duration_seconds=(datetime.utcnow() - start_time).total_seconds()
                    )
                elif error_code in ['InvalidUserID.NotFound', 'AuthFailure']:
                    return CredentialValidation(
                        status=ValidationStatus.INVALID,
                        is_valid=False,
                        error_message=f"Invalid credentials: {error_message}",
                        validated_at=datetime.utcnow(),
                        validation_duration_seconds=(datetime.utcnow() - start_time).total_seconds()
                    )
                else:
                    raise
        
        except Exception as e:
            validation_duration = (datetime.utcnow() - start_time).total_seconds()
            return CredentialValidation(
                status=ValidationStatus.UNKNOWN,
                is_valid=False,
                error_message=f"Validation failed: {str(e)}",
                validated_at=datetime.utcnow(),
                validation_duration_seconds=validation_duration
            )
        finally:
            await self._cleanup_client()
    
    async def collect_cost_data(self, date_range: DateRange) -> CollectionResult:
        """
        Collect cost data from AWS Cost Explorer.
        
        Args:
            date_range: Date range for cost collection
            
        Returns:
            CollectionResult with AWS cost data
        """
        start_time = datetime.utcnow()
        api_calls = 0
        
        try:
            await self._initialize_client()
            
            # Get cost and usage data
            cost_response = self._cost_explorer_client.get_cost_and_usage(
                TimePeriod={
                    'Start': date_range.start_date.strftime('%Y-%m-%d'),
                    'End': (date_range.end_date + timedelta(days=1)).strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost', 'UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'}
                ]
            )
            api_calls += 1
            
            # Get service details
            services_response = self._cost_explorer_client.get_dimension_values(
                TimePeriod={
                    'Start': date_range.start_date.strftime('%Y-%m-%d'),
                    'End': (date_range.end_date + timedelta(days=1)).strftime('%Y-%m-%d')
                },
                Dimension='SERVICE'
            )
            api_calls += 1
            
            # Process cost data
            total_cost = Decimal('0')
            services_data = {}
            accounts_data = {}
            regions_data = {}
            
            for result_by_time in cost_response['ResultsByTime']:
                for group in result_by_time['Groups']:
                    keys = group['Keys']
                    service_name = keys[0] if len(keys) > 0 else 'Unknown'
                    account_id = keys[1] if len(keys) > 1 else 'Unknown'
                    
                    # Extract cost
                    cost_amount = Decimal(group['Metrics']['BlendedCost']['Amount'])
                    usage_amount = group['Metrics'].get('UsageQuantity', {}).get('Amount', '0')
                    
                    total_cost += cost_amount
                    
                    # Aggregate by service
                    if service_name not in services_data:
                        services_data[service_name] = {
                            'cost': Decimal('0'),
                            'usage_metrics': {'total_usage': Decimal('0')},
                            'provider_data': {'service_name': service_name}
                        }
                    services_data[service_name]['cost'] += cost_amount
                    services_data[service_name]['usage_metrics']['total_usage'] += Decimal(usage_amount)
                    
                    # Aggregate by account
                    if account_id not in accounts_data:
                        accounts_data[account_id] = {
                            'account_id': account_id,
                            'account_name': None,  # Could be enriched with Organizations API
                            'cost': Decimal('0')
                        }
                    accounts_data[account_id]['cost'] += cost_amount
            
            # Get account names if Organizations access is available
            try:
                accounts_response = self._organizations_client.list_accounts()
                api_calls += 1
                
                account_names = {
                    account['Id']: account['Name'] 
                    for account in accounts_response['Accounts']
                }
                
                for account_id in accounts_data:
                    if account_id in account_names:
                        accounts_data[account_id]['account_name'] = account_names[account_id]
                        
            except ClientError:
                # Organizations access not available, continue without account names
                pass
            
            # Create provider accounts list
            provider_accounts = [
                ProviderAccount(
                    account_id=account_data['account_id'],
                    account_name=account_data['account_name'],
                    provider=ProviderType.AWS,
                    is_active=True
                )
                for account_data in accounts_data.values()
            ]
            
            # Create provider cost data
            provider_cost_data = ProviderCostData(
                client_id="unknown",  # Will be set by caller
                provider=ProviderType.AWS,
                date_range=date_range,
                total_cost=total_cost,
                currency=self.default_currency,
                accounts=provider_accounts,
                services=services_data,
                regions=regions_data,
                collection_metadata={
                    'api_calls': api_calls,
                    'duration': (datetime.utcnow() - start_time).total_seconds(),
                    'freshness_hours': 24,  # AWS Cost Explorer data is typically 24 hours delayed
                    'data_source': 'cost_explorer'
                }
            )
            
            completion_time = datetime.utcnow()
            
            return CollectionResult(
                status=DataCollectionStatus.SUCCESS,
                provider=ProviderType.AWS,
                client_id="unknown",  # Will be set by caller
                date_range=date_range,
                cost_data=provider_cost_data,
                collection_duration_seconds=(completion_time - start_time).total_seconds(),
                api_calls_made=api_calls,
                records_collected=len(cost_response['ResultsByTime']),
                started_at=start_time,
                completed_at=completion_time
            )
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == 'Throttling':
                raise RateLimitError(
                    provider=ProviderType.AWS,
                    message=f"AWS API rate limit exceeded: {error_message}",
                    retry_after=60
                )
            elif error_code in ['UnauthorizedOperation', 'AccessDenied']:
                raise AuthorizationError(
                    provider=ProviderType.AWS,
                    message=f"Insufficient permissions: {error_message}"
                )
            elif error_code in ['InvalidUserID.NotFound', 'AuthFailure']:
                raise AuthenticationError(
                    provider=ProviderType.AWS,
                    message=f"Authentication failed: {error_message}"
                )
            else:
                raise ServiceUnavailableError(
                    provider=ProviderType.AWS,
                    message=f"AWS service error: {error_message}"
                )
        
        except Exception as e:
            self.logger.error(f"Unexpected error collecting AWS cost data: {e}")
            return CollectionResult(
                status=DataCollectionStatus.FAILED,
                provider=ProviderType.AWS,
                client_id="unknown",
                date_range=date_range,
                error_message=str(e),
                collection_duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                api_calls_made=api_calls,
                started_at=start_time,
                completed_at=datetime.utcnow()
            )
        
        finally:
            await self._cleanup_client()
    
    async def get_accounts(self) -> List[ProviderAccount]:
        """
        Get list of AWS accounts accessible with current credentials.
        
        Returns:
            List of AWS accounts
        """
        try:
            await self._initialize_client()
            
            accounts = []
            
            try:
                # Try to get accounts from Organizations
                response = self._organizations_client.list_accounts()
                
                for account in response['Accounts']:
                    accounts.append(ProviderAccount(
                        account_id=account['Id'],
                        account_name=account['Name'],
                        provider=ProviderType.AWS,
                        is_active=account['Status'] == 'ACTIVE',
                        tags={'email': account.get('Email', '')}
                    ))
                    
            except ClientError:
                # If Organizations access is not available, try to get current account
                try:
                    sts_client = self._session.client('sts')
                    identity = sts_client.get_caller_identity()
                    
                    accounts.append(ProviderAccount(
                        account_id=identity['Account'],
                        account_name=None,
                        provider=ProviderType.AWS,
                        is_active=True
                    ))
                except ClientError as e:
                    self.logger.error(f"Failed to get AWS account information: {e}")
            
            return accounts
            
        except Exception as e:
            self.logger.error(f"Error getting AWS accounts: {e}")
            return []
        
        finally:
            await self._cleanup_client()
    
    async def get_services(self) -> List[ProviderService]:
        """
        Get list of AWS services.
        
        Returns:
            List of AWS services
        """
        try:
            await self._initialize_client()
            
            # Get services from Cost Explorer
            end_date = date.today()
            start_date = end_date - timedelta(days=30)  # Last 30 days
            
            response = self._cost_explorer_client.get_dimension_values(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Dimension='SERVICE'
            )
            
            services = []
            service_mapping = self.get_service_mapping()
            
            for dimension_value in response['DimensionValues']:
                service_name = dimension_value['Value']
                category = service_mapping.get(service_name, ServiceCategory.OTHER)
                
                services.append(ProviderService(
                    service_id=service_name.lower().replace(' ', '_'),
                    service_name=service_name,
                    provider=ProviderType.AWS,
                    category=category.value,
                    description=dimension_value.get('Attributes', {}).get('description'),
                    regions_available=self.supported_regions
                ))
            
            return services
            
        except Exception as e:
            self.logger.error(f"Error getting AWS services: {e}")
            return []
        
        finally:
            await self._cleanup_client()
    
    def get_service_mapping(self) -> Dict[str, ServiceCategory]:
        """
        Get mapping of AWS services to unified categories.
        
        Returns:
            Dictionary mapping AWS service names to ServiceCategory enums
        """
        return {
            # Compute services
            'Amazon Elastic Compute Cloud - Compute': ServiceCategory.COMPUTE,
            'AWS Lambda': ServiceCategory.SERVERLESS,
            'Amazon EC2 Container Service': ServiceCategory.CONTAINERS,
            'Amazon Elastic Container Service for Kubernetes': ServiceCategory.CONTAINERS,
            'Amazon Elastic Kubernetes Service': ServiceCategory.CONTAINERS,
            'AWS Fargate': ServiceCategory.CONTAINERS,
            'AWS Batch': ServiceCategory.COMPUTE,
            'Amazon Lightsail': ServiceCategory.COMPUTE,
            
            # Storage services
            'Amazon Simple Storage Service': ServiceCategory.STORAGE,
            'Amazon Elastic Block Store': ServiceCategory.STORAGE,
            'Amazon Elastic File System': ServiceCategory.STORAGE,
            'Amazon FSx': ServiceCategory.STORAGE,
            'Amazon S3 Glacier': ServiceCategory.STORAGE,
            'AWS Storage Gateway': ServiceCategory.STORAGE,
            
            # Database services
            'Amazon Relational Database Service': ServiceCategory.DATABASE,
            'Amazon DynamoDB': ServiceCategory.DATABASE,
            'Amazon Aurora': ServiceCategory.DATABASE,
            'Amazon Redshift': ServiceCategory.ANALYTICS,
            'Amazon ElastiCache': ServiceCategory.DATABASE,
            'Amazon DocumentDB': ServiceCategory.DATABASE,
            'Amazon Neptune': ServiceCategory.DATABASE,
            
            # Networking
            'Amazon Virtual Private Cloud': ServiceCategory.NETWORKING,
            'Amazon CloudFront': ServiceCategory.NETWORKING,
            'Amazon Route 53': ServiceCategory.NETWORKING,
            'Elastic Load Balancing': ServiceCategory.NETWORKING,
            'Amazon API Gateway': ServiceCategory.NETWORKING,
            'AWS Direct Connect': ServiceCategory.NETWORKING,
            'AWS VPN': ServiceCategory.NETWORKING,
            
            # Analytics
            'Amazon EMR': ServiceCategory.ANALYTICS,
            'Amazon Athena': ServiceCategory.ANALYTICS,
            'AWS Glue': ServiceCategory.ANALYTICS,
            'Amazon Kinesis': ServiceCategory.ANALYTICS,
            'Amazon QuickSight': ServiceCategory.ANALYTICS,
            'Amazon Elasticsearch Service': ServiceCategory.ANALYTICS,
            
            # AI/ML
            'Amazon SageMaker': ServiceCategory.AI_ML,
            'Amazon Bedrock': ServiceCategory.AI_ML,
            'Amazon Comprehend': ServiceCategory.AI_ML,
            'Amazon Rekognition': ServiceCategory.AI_ML,
            'Amazon Textract': ServiceCategory.AI_ML,
            'Amazon Translate': ServiceCategory.AI_ML,
            'Amazon Polly': ServiceCategory.AI_ML,
            'Amazon Transcribe': ServiceCategory.AI_ML,
            
            # Security
            'AWS Identity and Access Management': ServiceCategory.SECURITY,
            'AWS Key Management Service': ServiceCategory.SECURITY,
            'AWS Secrets Manager': ServiceCategory.SECURITY,
            'AWS WAF': ServiceCategory.SECURITY,
            'Amazon GuardDuty': ServiceCategory.SECURITY,
            'AWS Security Hub': ServiceCategory.SECURITY,
            'AWS Certificate Manager': ServiceCategory.SECURITY,
            
            # Management
            'Amazon CloudWatch': ServiceCategory.MANAGEMENT,
            'AWS CloudTrail': ServiceCategory.MANAGEMENT,
            'AWS Config': ServiceCategory.MANAGEMENT,
            'AWS Systems Manager': ServiceCategory.MANAGEMENT,
            'AWS CloudFormation': ServiceCategory.MANAGEMENT,
            'AWS Organizations': ServiceCategory.MANAGEMENT,
            'AWS Support': ServiceCategory.MANAGEMENT,
        }
    
    async def test_connection(self) -> bool:
        """
        Test connection to AWS APIs.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            await self._initialize_client()
            
            # Test STS access (basic connectivity)
            sts_client = self._session.client('sts')
            sts_client.get_caller_identity()
            
            # Test Cost Explorer access
            end_date = date.today()
            start_date = end_date - timedelta(days=1)
            
            self._cost_explorer_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost']
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"AWS connection test failed: {e}")
            return False
        
        finally:
            await self._cleanup_client()
    
    async def get_cost_forecast(self, date_range: DateRange, forecast_days: int = 30) -> Optional[Dict[str, Any]]:
        """
        Get cost forecast from AWS Cost Explorer.
        
        Args:
            date_range: Historical date range for forecast basis
            forecast_days: Number of days to forecast
            
        Returns:
            Forecast data from AWS Cost Explorer
        """
        try:
            await self._initialize_client()
            
            forecast_start = date_range.end_date + timedelta(days=1)
            forecast_end = forecast_start + timedelta(days=forecast_days)
            
            response = self._cost_explorer_client.get_cost_forecast(
                TimePeriod={
                    'Start': forecast_start.strftime('%Y-%m-%d'),
                    'End': forecast_end.strftime('%Y-%m-%d')
                },
                Metric='BLENDED_COST',
                Granularity='DAILY'
            )
            
            return {
                'provider': 'AWS',
                'forecast_period': {
                    'start': forecast_start.isoformat(),
                    'end': forecast_end.isoformat()
                },
                'total_forecast': response['Total']['Amount'],
                'currency': response['Total']['Unit'],
                'forecast_results': response['ForecastResultsByTime'],
                'confidence_level': 'MEDIUM'  # AWS doesn't provide confidence levels
            }
            
        except Exception as e:
            self.logger.error(f"Error getting AWS cost forecast: {e}")
            return None
        
        finally:
            await self._cleanup_client()
    
    async def get_cost_anomalies(self, date_range: DateRange) -> List[Dict[str, Any]]:
        """
        Get cost anomalies from AWS Cost Anomaly Detection.
        
        Args:
            date_range: Date range to check for anomalies
            
        Returns:
            List of anomaly data from AWS
        """
        try:
            await self._initialize_client()
            
            response = self._cost_explorer_client.get_anomalies(
                DateInterval={
                    'StartDate': date_range.start_date.strftime('%Y-%m-%d'),
                    'EndDate': date_range.end_date.strftime('%Y-%m-%d')
                }
            )
            
            anomalies = []
            for anomaly in response['Anomalies']:
                anomalies.append({
                    'provider': 'AWS',
                    'anomaly_id': anomaly['AnomalyId'],
                    'anomaly_score': anomaly['AnomalyScore']['CurrentScore'],
                    'max_impact': anomaly['Impact']['MaxImpact'],
                    'total_impact': anomaly['Impact']['TotalImpact'],
                    'start_date': anomaly['AnomalyStartDate'],
                    'end_date': anomaly['AnomalyEndDate'],
                    'dimension_key': anomaly.get('DimensionKey'),
                    'root_causes': anomaly.get('RootCauses', []),
                    'feedback': anomaly.get('Feedback')
                })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error getting AWS cost anomalies: {e}")
            return []
        
        finally:
            await self._cleanup_client()


# Register the AWS adapter with the factory
from .cloud_provider_adapter import ProviderAdapterFactory
ProviderAdapterFactory.register_adapter(ProviderType.AWS, AWSCostAdapter)