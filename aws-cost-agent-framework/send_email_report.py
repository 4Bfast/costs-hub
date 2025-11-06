#!/usr/bin/env python3
"""
Send CostHub Email Report via AWS SES
"""

import asyncio
import sys
import argparse
import json
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agents.cost_analysis_agent import CostAnalysisAgent
from tools.ses_sender import CostHubEmailService
from config.settings import Settings, AWSConfig, AnalysisConfig, ReportConfig

def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description='Send CostHub Email Report via AWS SES',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --recipients exec@company.com finance@company.com
  %(prog)s --config email_config.json --weeks 4
  %(prog)s --template-only --template-name costhub-weekly
        """
    )
    
    # AWS Configuration
    parser.add_argument('--profile', default='billing',
                       help='AWS profile name (default: billing)')
    parser.add_argument('--region', default='us-east-2',
                       help='AWS region (default: us-east-2)')
    parser.add_argument('--ses-region', default='us-east-1',
                       help='SES region (default: us-east-1)')
    
    # Analysis Configuration
    parser.add_argument('--type', choices=['monthly', 'weekly'], default='monthly',
                       help='Analysis type (default: monthly)')
    parser.add_argument('--periods', type=int, default=3,
                       help='Number of periods to analyze (default: 3)')
    parser.add_argument('--weeks', type=int,
                       help='Number of weeks to analyze (sets --type weekly)')
    
    # Email Configuration
    parser.add_argument('--recipients', nargs='+',
                       help='Email recipients (space separated)')
    parser.add_argument('--cc', nargs='+',
                       help='CC recipients (space separated)')
    parser.add_argument('--bcc', nargs='+',
                       help='BCC recipients (space separated)')
    parser.add_argument('--from-email', 
                       help='From email address (must be verified in SES)')
    parser.add_argument('--config', 
                       help='JSON config file with email settings')
    
    # Template Options
    parser.add_argument('--template-only', action='store_true',
                       help='Only create SES template, do not send email')
    parser.add_argument('--template-name',
                       help='SES template name (default: auto-generated)')
    parser.add_argument('--use-template',
                       help='Use existing SES template name')
    
    return parser

def load_email_config(config_path: str) -> dict:
    """Load email configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file {config_path}: {e}")
        return {}

async def main():
    """Main function"""
    parser = create_parser()
    args = parser.parse_args()
    
    print("📧 CostHub Email Report Sender")
    print("=" * 50)
    
    # Load email configuration
    email_config = {}
    if args.config:
        email_config = load_email_config(args.config)
    
    # Determine analysis type
    analysis_type = 'weekly' if args.weeks else args.type
    periods = args.weeks if args.weeks else args.periods
    
    print(f"🔧 Configuration:")
    print(f"   Analysis type: {analysis_type}")
    print(f"   Periods: {periods}")
    print(f"   AWS Profile: {args.profile}")
    print(f"   SES Region: {args.ses_region}")
    
    # Configure settings
    settings = Settings()
    
    settings.aws = AWSConfig(
        profile_name=args.profile,
        region=args.region
    )
    
    settings.analysis = AnalysisConfig(
        analysis_type=analysis_type,
        periods_to_analyze=periods,
        include_charts=False,  # Don't need charts for email
        include_account_analysis=True
    )
    
    settings.report = ReportConfig(
        auto_open=False
    )
    
    try:
        # Step 1: Generate analysis data
        print("📊 Generating cost analysis...")
        agent = CostAnalysisAgent(settings)
        result = await agent.execute()
        
        if not result.success:
            print(f"❌ Analysis failed: {result.error}")
            return 1
        
        print("✅ Analysis completed successfully!")
        
        # Step 2: Generate email report
        print("📧 Generating email report...")
        email_report = agent.email_generator.generate_email_report(result.data)
        
        # Step 3: Setup SES service
        ses_config = {
            'region': args.ses_region,
            'from_email': args.from_email or email_config.get('from_email', 'costhub@yourdomain.com')
        }
        
        email_service = CostHubEmailService(settings.aws, ses_config)
        
        # Step 4: Handle template creation or email sending
        if args.template_only:
            # Only create template
            template_name = args.template_name or f"costhub-{analysis_type}-report"
            
            print(f"📝 Creating SES template: {template_name}")
            template_result = email_service.setup_automated_reporting(template_name, email_report)
            
            if template_result['success']:
                print(f"✅ SES template created: {template_name}")
                print(f"💡 Use --use-template {template_name} to send emails with this template")
            else:
                print(f"❌ Template creation failed: {template_result['error']}")
                return 1
                
        elif args.use_template:
            # Send using existing template
            recipients = args.recipients or email_config.get('recipients', [])
            
            if not recipients:
                print("❌ No recipients specified. Use --recipients or config file.")
                return 1
            
            print(f"📤 Sending email using template: {args.use_template}")
            print(f"📬 Recipients: {', '.join(recipients)}")
            
            send_result = email_service.ses_sender.send_templated_email(
                template_name=args.use_template,
                recipients=recipients,
                cc_recipients=args.cc or email_config.get('cc', []),
                bcc_recipients=args.bcc or email_config.get('bcc', [])
            )
            
            if send_result['success']:
                print(f"✅ Email sent successfully!")
                print(f"📧 Message ID: {send_result['message_id']}")
            else:
                print(f"❌ Email sending failed: {send_result['error']}")
                return 1
                
        else:
            # Generate and send email directly
            recipients = args.recipients or email_config.get('recipients', [])
            
            if not recipients:
                print("❌ No recipients specified. Use --recipients or config file.")
                return 1
            
            print(f"📤 Sending email report...")
            print(f"📬 Recipients: {', '.join(recipients)}")
            
            # Prepare recipient groups
            recipient_groups = {
                'executives': recipients,
                'cc': args.cc or email_config.get('cc', []),
                'bcc': args.bcc or email_config.get('bcc', [])
            }
            
            send_result = email_service.ses_sender.send_cost_report_email(
                email_report=email_report,
                recipients=recipients,
                cc_recipients=args.cc or email_config.get('cc', []),
                bcc_recipients=args.bcc or email_config.get('bcc', [])
            )
            
            if send_result['success']:
                print(f"✅ Email sent successfully!")
                print(f"📧 Message ID: {send_result['message_id']}")
                print(f"📊 Subject: {email_report['subject']}")
            else:
                print(f"❌ Email sending failed: {send_result['error']}")
                return 1
        
        # Step 5: Show summary
        metadata = email_report['metadata']
        print(f"\n📋 Report Summary:")
        print(f"   Analysis type: {metadata['analysis_type']}")
        print(f"   Total cost: ${metadata['total_cost']:,.2f}")
        print(f"   Cost change: ${metadata['cost_change']:+,.2f} ({metadata['cost_change_percent']:+.1f}%)")
        
    except Exception as e:
        print(f"💥 Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)