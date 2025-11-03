"""
Example: Report Generation and Email Services Integration

This example demonstrates how to use the LambdaReportGenerator, 
LambdaEmailService, and LambdaAssetManager together to generate 
and send cost analysis reports.
"""

import os
import sys
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.lambda_report_generator import LambdaReportGenerator
from services.lambda_email_service import LambdaEmailService
from services.lambda_asset_manager import LambdaAssetManager
from models.config_models import ClientConfig, ReportConfig, BrandingConfig, AccountConfig


def create_sample_client_config() -> ClientConfig:
    """Create a sample client configuration for testing"""
    
    # Sample AWS account configuration
    aws_account = AccountConfig(
        account_id="123456789012",
        access_key_id="AKIA...",  # Would be real credentials in production
        secret_access_key="encrypted_secret",
        region="us-east-1",
        account_name="Production Account"
    )
    
    # Sample report configuration
    report_config = ReportConfig(
        weekly_enabled=True,
        monthly_enabled=True,
        recipients=["finance@company.com", "devops@company.com"],
        cc_recipients=["cto@company.com"],
        threshold=1000.0,
        top_services=10,
        include_accounts=True,
        alert_thresholds={
            "EC2-Instance": 500.0,
            "RDS": 300.0,
            "S3": 100.0
        }
    )
    
    # Sample branding configuration
    branding_config = BrandingConfig(
        logo_s3_key="assets/client123/logo.png",
        primary_color="#2563eb",
        secondary_color="#f59e0b",
        company_name="Acme Corporation",
        email_footer="This report is generated automatically by Acme's FinOps team."
    )
    
    # Create client configuration
    client_config = ClientConfig(
        client_id="client-123",
        client_name="Acme Corporation",
        aws_accounts=[aws_account],
        report_config=report_config,
        branding=branding_config
    )
    
    return client_config


def create_sample_cost_data() -> dict:
    """Create sample cost analysis data for testing"""
    
    return {
        'periods_data': [
            {
                'name': 'October 2024',
                'total_cost': 15420.50,
                'service_count': 12
            },
            {
                'name': 'September 2024', 
                'total_cost': 14230.25,
                'service_count': 11
            },
            {
                'name': 'August 2024',
                'total_cost': 13890.75,
                'service_count': 10
            }
        ],
        'changes': {
            'current_period': {
                'total_cost': 15420.50
            },
            'previous_period': {
                'total_cost': 14230.25
            },
            'total_change': 1190.25,
            'total_percent_change': 8.4,
            'service_changes': {
                'EC2-Instance': {
                    'previous': 5200.00,
                    'current': 6100.00,
                    'change': 900.00,
                    'percent_change': 17.3
                },
                'RDS': {
                    'previous': 2800.00,
                    'current': 2950.00,
                    'change': 150.00,
                    'percent_change': 5.4
                },
                'S3': {
                    'previous': 450.00,
                    'current': 420.00,
                    'change': -30.00,
                    'percent_change': -6.7
                }
            },
            'new_services': [
                {
                    'service': 'Lambda',
                    'cost': 125.50
                }
            ]
        },
        'top_services': [
            {
                'service': 'EC2-Instance',
                'cost': 6100.00,
                'percentage': 39.6
            },
            {
                'service': 'RDS',
                'cost': 2950.00,
                'percentage': 19.1
            },
            {
                'service': 'ELB',
                'cost': 1800.00,
                'percentage': 11.7
            },
            {
                'service': 'S3',
                'cost': 420.00,
                'percentage': 2.7
            },
            {
                'service': 'Lambda',
                'cost': 125.50,
                'percentage': 0.8
            }
        ],
        'metadata': {
            'analysis_type': 'monthly',
            'generated_at': datetime.now().isoformat()
        },
        'forecast_analysis': {
            'summary': {
                'forecast_increase_percent': 12.5,
                'top_driver': 'EC2-Instance',
                'top_driver_increase': 1200.00
            },
            'current_month': {
                'days_elapsed': 15,
                'days_remaining': 16,
                'total_cost': 7500.00
            },
            'forecast': {
                'total_forecast': 16800.00,
                'vs_previous_change': 2569.75,
                'vs_previous_percent': 18.1
            }
        }
    }


def example_report_generation():
    """Example of generating a client report"""
    
    print("=== Report Generation Example ===")
    
    # Initialize services (would use environment variables in production)
    s3_bucket = "cost-reporting-bucket"
    
    report_generator = LambdaReportGenerator(
        s3_bucket=s3_bucket,
        s3_prefix="reports"
    )
    
    # Create sample data
    client_config = create_sample_client_config()
    cost_data = create_sample_cost_data()
    
    try:
        # Generate report
        print(f"Generating report for client: {client_config.client_name}")
        report_url = report_generator.generate_client_report(cost_data, client_config)
        print(f"Report generated successfully: {report_url}")
        
        return report_url
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return None


def example_email_sending():
    """Example of sending email reports"""
    
    print("\n=== Email Service Example ===")
    
    # Initialize email service
    email_service = LambdaEmailService(
        region="us-east-1",
        sender_email="reports@company.com"
    )
    
    # Create sample data
    client_config = create_sample_client_config()
    cost_data = create_sample_cost_data()
    
    # Prepare report data for email
    report_data = {
        'cost_data': cost_data
    }
    
    try:
        print(f"Sending email report for client: {client_config.client_name}")
        print(f"Recipients: {', '.join(client_config.report_config.recipients)}")
        
        # In a real scenario, this would actually send the email
        # For this example, we'll just generate the email content
        email_content = email_service._create_email_template(report_data, client_config)
        
        print(f"Email subject: {email_content['subject']}")
        print(f"Email recipients: {len(email_content['recipients'])} recipients")
        print("Email content generated successfully")
        
        # Uncomment to actually send (requires SES setup)
        # success = email_service.send_client_report(report_data, client_config)
        # print(f"Email sent: {success}")
        
    except Exception as e:
        print(f"Error with email service: {e}")


def example_asset_management():
    """Example of asset management"""
    
    print("\n=== Asset Management Example ===")
    
    # Initialize asset manager
    s3_bucket = "cost-reporting-bucket"
    asset_manager = LambdaAssetManager(
        s3_bucket=s3_bucket,
        s3_prefix="assets"
    )
    
    client_id = "client-123"
    
    try:
        # Get asset information
        print(f"Getting asset info for client: {client_id}")
        asset_info = asset_manager.get_asset_info(client_id)
        print(f"Total assets: {asset_info.get('total_assets', 0)}")
        print(f"Has logo: {asset_info.get('has_logo', False)}")
        
        # Generate logo HTML
        logo_html = asset_manager.get_logo_html(
            client_id=client_id,
            max_width="200px",
            alt_text="Company Logo"
        )
        print(f"Logo HTML generated: {len(logo_html)} characters")
        
        # Create default logo if none exists
        if not asset_info.get('has_logo'):
            print("Creating default logo...")
            logo_key = asset_manager.create_default_logo(
                client_id=client_id,
                company_name="Acme Corporation"
            )
            print(f"Default logo created: {logo_key}")
        
    except Exception as e:
        print(f"Error with asset management: {e}")


def example_integrated_workflow():
    """Example of integrated workflow using all services"""
    
    print("\n=== Integrated Workflow Example ===")
    
    # Initialize all services
    s3_bucket = "cost-reporting-bucket"
    
    report_generator = LambdaReportGenerator(s3_bucket, "reports")
    email_service = LambdaEmailService("us-east-1", "reports@company.com")
    asset_manager = LambdaAssetManager(s3_bucket, "assets")
    
    # Create sample data
    client_config = create_sample_client_config()
    cost_data = create_sample_cost_data()
    
    try:
        print(f"Processing client: {client_config.client_name}")
        
        # 1. Ensure client has assets
        asset_info = asset_manager.get_asset_info(client_config.client_id)
        if not asset_info.get('has_logo'):
            print("Creating default logo...")
            asset_manager.create_default_logo(
                client_config.client_id,
                client_config.branding.company_name
            )
        
        # 2. Generate HTML report
        print("Generating HTML report...")
        report_url = report_generator.generate_client_report(cost_data, client_config)
        print(f"Report stored at: {report_url}")
        
        # 3. Send email report
        print("Preparing email report...")
        report_data = {'cost_data': cost_data}
        email_content = email_service._create_email_template(report_data, client_config)
        print(f"Email prepared: {email_content['subject']}")
        
        # In production, would actually send:
        # success = email_service.send_client_report(report_data, client_config)
        
        print("Integrated workflow completed successfully!")
        
    except Exception as e:
        print(f"Error in integrated workflow: {e}")


if __name__ == "__main__":
    """Run all examples"""
    
    print("Lambda Cost Reporting System - Service Examples")
    print("=" * 60)
    
    # Note: These examples demonstrate the API but won't actually
    # interact with AWS services without proper configuration
    
    example_report_generation()
    example_email_sending()
    example_asset_management()
    example_integrated_workflow()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("\nNote: To run with real AWS services, ensure:")
    print("- AWS credentials are configured")
    print("- S3 bucket exists and is accessible")
    print("- SES is configured for email sending")
    print("- Required IAM permissions are in place")