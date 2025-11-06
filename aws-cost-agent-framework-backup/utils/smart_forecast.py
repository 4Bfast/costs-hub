#!/usr/bin/env python3
"""
Smart Forecast Analysis
Escolhe automaticamente entre forecast mensal e projeção semanal
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tools.aws_cost_tools import AWSCostTools
from config.settings import AWSConfig

def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description='Smart AWS Cost Forecast Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Auto-detect best analysis
  %(prog)s --monthly          # Force monthly forecast
  %(prog)s --weekly           # Force weekly projection
  %(prog)s --both             # Show both analyses
        """
    )
    
    parser.add_argument('--monthly', action='store_true',
                       help='Force monthly forecast analysis')
    parser.add_argument('--weekly', action='store_true',
                       help='Force weekly projection analysis')
    parser.add_argument('--both', action='store_true',
                       help='Show both monthly and weekly analyses')
    parser.add_argument('--profile', default='billing',
                       help='AWS profile name (default: billing)')
    parser.add_argument('--region', default='us-east-2',
                       help='AWS region (default: us-east-2)')
    
    return parser

async def run_monthly_analysis(cost_tools):
    """Run monthly forecast analysis"""
    print("🔮 MONTHLY FORECAST ANALYSIS")
    print("=" * 50)
    
    analysis = await cost_tools.analyze_forecast_vs_current()
    
    if analysis.get('error'):
        print(f"❌ Monthly analysis error: {analysis['error']}")
        return False
    
    # Extract key information
    summary = analysis.get('summary', {})
    current = analysis.get('current_month', {})
    forecast_data = analysis.get('forecast', {})
    service_drivers = analysis.get('service_drivers', {})
    
    # Show summary
    forecast_percent = summary.get('forecast_increase_percent', 0)
    
    print(f"📈 Month-to-Date: ${current.get('total_cost', 0):,.2f}")
    print(f"📅 Days elapsed: {current.get('days_elapsed', 0)}")
    print(f"🎯 Projected month-end: ${forecast_data.get('total_forecast', 0):,.2f}")
    print(f"📊 Change vs last month: {forecast_percent:+.1f}%")
    
    # Alert level
    if forecast_percent > 10:
        print(f"🚨 HIGH ALERT: Custo mensal projetado {forecast_percent:+.1f}% acima!")
    elif forecast_percent > 4:
        print(f"⚠️  WARNING: Custo mensal projetado {forecast_percent:+.1f}% acima")
    else:
        print(f"✅ OK: Custos mensais sob controle ({forecast_percent:+.1f}%)")
    
    # Show top 3 drivers
    if service_drivers:
        print(f"\n🎯 Top 3 Cost Drivers:")
        count = 0
        for service, data in service_drivers.items():
            if count >= 3:
                break
            change = data.get('projected_change', 0)
            if change <= 0:
                continue
            print(f"   {count + 1}. {service}: +${change:,.2f}")
            count += 1
    
    return True

async def run_weekly_analysis(cost_tools):
    """Run weekly projection analysis"""
    print("📅 WEEKLY PROJECTION ANALYSIS")
    print("=" * 50)
    
    analysis = await cost_tools.analyze_weekly_projection()
    
    if analysis.get('error'):
        print(f"❌ Weekly analysis error: {analysis['error']}")
        return False
    
    # Extract key information
    summary = analysis.get('summary', {})
    current = analysis.get('current_week', {})
    projection = analysis.get('projection', {})
    service_drivers = analysis.get('service_drivers', {})
    
    # Show summary
    week_percent = summary.get('week_increase_percent', 0)
    
    print(f"📈 Week-to-Date: ${current.get('total_cost', 0):,.2f}")
    print(f"📅 Days elapsed: {current.get('days_elapsed', 0)} of 7")
    print(f"🎯 Projected week-end: ${projection.get('projected_total', 0):,.2f}")
    print(f"📊 Change vs last week: {week_percent:+.1f}%")
    
    # Alert level (higher thresholds for weekly)
    if week_percent > 25:
        print(f"🚨 HIGH ALERT: Custo semanal projetado {week_percent:+.1f}% acima!")
    elif week_percent > 10:
        print(f"⚠️  WARNING: Custo semanal projetado {week_percent:+.1f}% acima")
    else:
        print(f"✅ OK: Custos semanais estáveis ({week_percent:+.1f}%)")
    
    # Show top 3 drivers
    if service_drivers:
        print(f"\n🎯 Top 3 Weekly Variations:")
        count = 0
        for service, data in service_drivers.items():
            if count >= 3:
                break
            change = data.get('projected_change', 0)
            if abs(change) < 2:
                continue
            direction = "+" if change > 0 else ""
            print(f"   {count + 1}. {service}: {direction}${change:,.2f}")
            count += 1
    
    return True

async def smart_forecast():
    """Smart forecast analysis with auto-detection"""
    
    parser = create_parser()
    args = parser.parse_args()
    
    print("🧠 Smart AWS Cost Forecast Analysis")
    print("=" * 50)
    
    # Create AWS config
    aws_config = AWSConfig(
        profile_name=args.profile,
        region=args.region
    )
    
    # Create cost tools
    cost_tools = AWSCostTools(aws_config)
    
    try:
        # Determine what to run
        if args.both:
            # Run both analyses
            monthly_success = await run_monthly_analysis(cost_tools)
            print("\n" + "=" * 50 + "\n")
            weekly_success = await run_weekly_analysis(cost_tools)
            
            if monthly_success or weekly_success:
                print(f"\n💡 RECOMMENDATION:")
                print(f"   • Use monthly for budget planning")
                print(f"   • Use weekly for operational monitoring")
            
        elif args.monthly:
            # Force monthly
            await run_monthly_analysis(cost_tools)
            
        elif args.weekly:
            # Force weekly
            await run_weekly_analysis(cost_tools)
            
        else:
            # Auto-detect best analysis
            from datetime import datetime
            today = datetime.now()
            day_of_month = today.day
            
            print("🤖 Auto-detecting best analysis type...")
            
            if day_of_month <= 7:
                print("📅 Early in month - Weekly projection more relevant\n")
                success = await run_weekly_analysis(cost_tools)
                if success:
                    print(f"\n💡 TIP: Run monthly analysis after day 10 for better forecast")
            elif day_of_month >= 25:
                print("📅 Late in month - Monthly forecast more relevant\n")
                success = await run_monthly_analysis(cost_tools)
                if success:
                    print(f"\n💡 TIP: Weekly analysis available for next week planning")
            else:
                print("📅 Mid-month - Both analyses available\n")
                monthly_success = await run_monthly_analysis(cost_tools)
                print("\n" + "-" * 30 + "\n")
                weekly_success = await run_weekly_analysis(cost_tools)
                
                if monthly_success and weekly_success:
                    print(f"\n💡 SMART RECOMMENDATION:")
                    print(f"   • Focus on monthly for budget impact")
                    print(f"   • Monitor weekly for operational trends")
        
        print(f"\n📋 Available commands:")
        print(f"   python smart_forecast.py --monthly    # Monthly forecast")
        print(f"   python smart_forecast.py --weekly     # Weekly projection")
        print(f"   python smart_forecast.py --both       # Both analyses")
        
    except Exception as e:
        print(f"💥 Erro: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(smart_forecast())
    sys.exit(exit_code)