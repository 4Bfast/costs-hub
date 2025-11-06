#!/usr/bin/env python3
"""
Interactive Charts Generator
Gera gráficos interativos para análise de custos AWS
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agents.cost_analysis_agent import CostAnalysisAgent
from config.settings import Settings, AWSConfig, AnalysisConfig, ReportConfig
from tools.chart_generator import ChartGenerator

def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description='AWS Cost Analysis Charts Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Generate all charts (monthly)
  %(prog)s --weekly                     # Generate weekly charts
  %(prog)s --forecast-only              # Generate only forecast charts
  %(prog)s --trends-only                # Generate only service trends
  %(prog)s --type weekly --periods 6    # Custom weekly analysis
        """
    )
    
    # AWS Configuration
    parser.add_argument('--profile', default='billing',
                       help='AWS profile name (default: billing)')
    parser.add_argument('--region', default='us-east-2',
                       help='AWS region (default: us-east-2)')
    
    # Analysis Configuration
    parser.add_argument('--type', choices=['monthly', 'weekly'], default='monthly',
                       help='Analysis type (default: monthly)')
    parser.add_argument('--periods', type=int, default=3,
                       help='Number of periods to analyze (default: 3)')
    parser.add_argument('--weekly', action='store_true',
                       help='Generate weekly charts (shortcut)')
    
    # Chart Options
    parser.add_argument('--forecast-only', action='store_true',
                       help='Generate only forecast charts')
    parser.add_argument('--trends-only', action='store_true',
                       help='Generate only service trends charts')
    parser.add_argument('--comparison-only', action='store_true',
                       help='Generate only comparison charts')
    parser.add_argument('--open', action='store_true',
                       help='Automatically open charts in browser')
    
    return parser

async def generate_charts():
    """Generate interactive charts for cost analysis"""
    
    parser = create_parser()
    args = parser.parse_args()
    
    print("📊 AWS Cost Analysis Charts Generator")
    print("=" * 50)
    
    # Determine analysis type
    analysis_type = 'weekly' if args.weekly else args.type
    periods = args.periods
    
    print(f"🔧 Configuration:")
    print(f"   Analysis type: {analysis_type}")
    print(f"   Periods: {periods}")
    print(f"   AWS Profile: {args.profile}")
    print()
    
    # Configure settings
    settings = Settings()
    
    settings.aws = AWSConfig(
        profile_name=args.profile,
        region=args.region
    )
    
    settings.analysis = AnalysisConfig(
        analysis_type=analysis_type,
        periods_to_analyze=periods,
        include_charts=True,
        include_account_analysis=True
    )
    
    settings.report = ReportConfig(
        auto_open=False  # We'll handle opening manually
    )
    
    try:
        # Initialize chart generator
        chart_generator = ChartGenerator(settings.report.output_dir)
        chart_paths = []
        
        # Get data for charts
        print("📊 Collecting data for charts...")
        agent = CostAnalysisAgent(settings)
        
        # We need to run the analysis to get data, but we'll focus on charts
        result = await agent.execute()
        
        if not result.success:
            print(f"❌ Failed to collect data: {result.error}")
            return 1
        
        analysis_data = result.data
        periods_data = analysis_data.get('periods_data', [])
        changes = analysis_data.get('changes', {})
        forecast_analysis = analysis_data.get('forecast_analysis', {})
        
        print("📈 Generating charts...")
        
        # Generate comparison charts
        if not args.forecast_only and not args.trends_only:
            print("   📊 Generating comparison charts...")
            comparison_chart = chart_generator.generate_monthly_comparison_chart(
                periods_data, changes, analysis_type
            )
            if comparison_chart:
                chart_paths.append(comparison_chart)
                print(f"   ✅ Comparison chart: {comparison_chart}")
        
        # Generate forecast charts
        if not args.comparison_only and not args.trends_only:
            if forecast_analysis and not forecast_analysis.get('error'):
                print("   🔮 Generating forecast charts...")
                forecast_chart = chart_generator.generate_forecast_chart(forecast_analysis)
                if forecast_chart:
                    chart_paths.append(forecast_chart)
                    print(f"   ✅ Forecast chart: {forecast_chart}")
            elif analysis_type == 'weekly':
                print("   📅 Generating weekly projection charts...")
                weekly_analysis = await agent.cost_tools.analyze_weekly_projection()
                if not weekly_analysis.get('error'):
                    weekly_chart = chart_generator.generate_weekly_comparison_chart(weekly_analysis)
                    if weekly_chart:
                        chart_paths.append(weekly_chart)
                        print(f"   ✅ Weekly chart: {weekly_chart}")
        
        # Generate service trends charts
        if not args.forecast_only and not args.comparison_only:
            print("   📈 Generating service trends charts...")
            trends_chart = chart_generator.generate_service_trend_chart(periods_data)
            if trends_chart:
                chart_paths.append(trends_chart)
                print(f"   ✅ Service trends chart: {trends_chart}")
        
        # Summary
        print(f"\n✅ Charts generation completed!")
        print(f"📊 Generated {len(chart_paths)} interactive charts:")
        
        for i, chart_path in enumerate(chart_paths, 1):
            chart_name = Path(chart_path).name
            print(f"   {i}. {chart_name}")
        
        # Open charts if requested
        if args.open and chart_paths:
            print(f"\n🌐 Opening charts in browser...")
            import os
            for chart_path in chart_paths:
                os.system(f"open {chart_path}")
        
        print(f"\n💡 Tips:")
        print(f"   • Charts are interactive - hover, zoom, and click!")
        print(f"   • Use browser's full-screen mode for better viewing")
        print(f"   • Charts are saved in: {settings.report.output_dir}")
        
    except Exception as e:
        print(f"💥 Error generating charts: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(generate_charts())
    sys.exit(exit_code)