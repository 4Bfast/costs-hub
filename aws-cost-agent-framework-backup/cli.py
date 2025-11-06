#!/usr/bin/env python3
"""
CLI interface for AWS Cost Analysis Framework
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agents.cost_analysis_agent import CostAnalysisAgent
from config.settings import Settings, AWSConfig, AnalysisConfig, ReportConfig

def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description='AWS Cost Analysis Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Basic monthly analysis (3 months)
  %(prog)s --type weekly --periods 4         # Analyze last 4 weeks
  %(prog)s --weeks 4                         # Same as above (shortcut)
  %(prog)s --type daily --periods 7          # Analyze last 7 days
  %(prog)s --days 7                          # Same as above (shortcut)
  %(prog)s --profile billing --months 6      # Analyze 6 months with billing profile
  %(prog)s --type weekly --weeks 2 --threshold 10.0 --top-services 15
  %(prog)s --region us-west-2 --output custom_report.html
        """
    )
    
    # AWS Configuration
    aws_group = parser.add_argument_group('AWS Configuration')
    aws_group.add_argument('--profile', default='4bfast',
                          help='AWS profile name (default: billing)')
    aws_group.add_argument('--region', default='us-east-2',
                          help='AWS region (default: us-east-2)')
    
    # Analysis Configuration
    analysis_group = parser.add_argument_group('Analysis Configuration')
    analysis_group.add_argument('--type', choices=['monthly', 'weekly', 'daily'], 
                               default='monthly',
                               help='Analysis type: monthly, weekly, or daily (default: monthly)')
    analysis_group.add_argument('--periods', type=int, default=3,
                               help='Number of periods to analyze (default: 3)')
    analysis_group.add_argument('--months', type=int, default=3,
                               help='Number of months to analyze (legacy, use --periods instead)')
    analysis_group.add_argument('--weeks', type=int,
                               help='Number of weeks to analyze (sets --type weekly and --periods)')
    analysis_group.add_argument('--days', type=int,
                               help='Number of days to analyze (sets --type daily and --periods)')
    analysis_group.add_argument('--threshold', type=float, default=1.0,
                               help='Minimum cost change threshold in USD (default: 1.0)')
    analysis_group.add_argument('--top-services', type=int, default=10,
                               help='Number of top services to show (default: 10)')
    analysis_group.add_argument('--top-accounts', type=int, default=10,
                               help='Number of top accounts to show (default: 10)')
    analysis_group.add_argument('--max-changes', type=int, default=15,
                               help='Maximum service changes to show (default: 15)')
    analysis_group.add_argument('--no-accounts', action='store_true',
                               help='Disable account analysis')
    analysis_group.add_argument('--max-account-changes', type=int, default=15,
                               help='Maximum account changes to show (default: 15)')
    analysis_group.add_argument('--forecast', action='store_true',
                               help='Include month-end forecast analysis (monthly only)')
    
    # Report Configuration
    report_group = parser.add_argument_group('Report Configuration')
    report_group.add_argument('--output', 
                             help='Output file name (default: auto-generated)')
    report_group.add_argument('--no-open', action='store_true',
                             help='Do not automatically open report in browser')
    report_group.add_argument('--no-charts', action='store_true',
                             help='Disable interactive chart generation')
    report_group.add_argument('--charts-only', action='store_true',
                             help='Generate only charts (no HTML report)')
    
    # Email Configuration
    email_group = parser.add_argument_group('Email Configuration')
    email_group.add_argument('--email', action='store_true',
                            help='Generate email report template')
    email_group.add_argument('--send-email', action='store_true',
                            help='Send email report via AWS SES')
    email_group.add_argument('--email-recipients', nargs='+',
                            help='Email recipients (space separated)')
    email_group.add_argument('--email-config',
                            help='JSON config file with email settings')
    
    # Other options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress non-error output')
    
    return parser

def configure_logging(verbose: bool, quiet: bool):
    """Configure logging based on verbosity settings"""
    import logging
    
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if verbose else '%(levelname)s: %(message)s'
    )

def create_settings_from_args(args) -> Settings:
    """Create Settings object from command line arguments"""
    
    # Determine analysis type and periods
    analysis_type = args.type
    periods = args.periods
    
    # Handle shortcut arguments
    if args.weeks:
        analysis_type = 'weekly'
        periods = args.weeks
    elif args.days:
        analysis_type = 'daily'
        periods = args.days
    elif analysis_type == 'monthly':
        periods = args.months  # Use months for backward compatibility
    
    # Create custom configurations
    aws_config = AWSConfig(
        profile_name=args.profile,
        region=args.region
    )
    
    analysis_config = AnalysisConfig(
        analysis_type=analysis_type,
        periods_to_analyze=periods,
        months_to_analyze=args.months,  # Keep for backward compatibility
        min_cost_threshold=args.threshold,
        top_services_count=args.top_services,
        top_accounts_count=args.top_accounts,
        max_service_changes=args.max_changes,
        max_account_changes=args.max_account_changes,
        include_account_analysis=not args.no_accounts,
        include_charts=not args.no_charts
    )
    
    report_config = ReportConfig(
        auto_open=not args.no_open
    )
    
    # Create main settings
    settings = Settings()
    settings.aws = aws_config
    settings.analysis = analysis_config
    settings.report = report_config
    
    return settings

async def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging
    configure_logging(args.verbose, args.quiet)
    
    try:
        if not args.quiet:
            print("AWS Cost Analysis Framework")
            print()

        # Create settings from arguments
        settings = create_settings_from_args(args)
        
        if not args.quiet:
            print(f"📋 Configuration:")
            print(f"   AWS Profile: {settings.aws.profile_name}")
            print(f"   Region: {settings.aws.region}")
            print(f"   Analysis Type: {settings.analysis.analysis_type}")
            print(f"   Periods to analyze: {settings.analysis.periods_to_analyze}")
            print(f"   Cost threshold: ${settings.analysis.min_cost_threshold}")
            print(f"   Account analysis: {'Enabled' if settings.analysis.include_account_analysis else 'Disabled'}")
            print(f"   Forecast analysis: {'Enabled' if args.forecast and settings.analysis.analysis_type == 'monthly' else 'Disabled'}")
            print()
        
        # Initialize and run agent
        agent = CostAnalysisAgent(settings)
        
        if not args.quiet:
            print("🚀 Starting analysis...")
        
        result = await agent.execute()
        
        if result.success:
            if not args.quiet:
                print(f"✅ Analysis completed successfully!")
                print(f"📄 Report: {result.report_path}")
                print(f"⏱️  Execution time: {result.execution_time:.2f}s")
                
                # Show summary
                if result.data:
                    metadata = result.data.get('metadata', {})
                    analysis_type = metadata.get('analysis_type', 'monthly')
                    periods_analyzed = metadata.get('periods_analyzed', metadata.get('months_analyzed', 'N/A'))
                    
                    print(f"📊 Summary:")
                    print(f"   Analysis type: {analysis_type}")
                    print(f"   Periods analyzed: {periods_analyzed}")
                    print(f"   Total services: {metadata.get('total_services', 'N/A')}")
                    if metadata.get('accounts_analyzed', 0) > 0:
                        print(f"   Total accounts: {metadata.get('total_accounts', 'N/A')}")
                    
                    # Show chart paths if generated
                    if hasattr(result, 'chart_paths') and result.chart_paths:
                        print(f"📈 Charts generated: {len(result.chart_paths)}")
                        for chart_path in result.chart_paths:
                            print(f"   📊 {chart_path}")
                    
                    # Show email template if generated
                    if hasattr(result, 'email_template_path') and result.email_template_path:
                        print(f"📧 Email template: {result.email_template_path}")
            
            # Open report if requested
            if settings.report.auto_open and result.report_path:
                import os
                os.system(f"open {result.report_path}")
                
        else:
            print(f"❌ Analysis failed: {result.error}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Analysis cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
