#!/usr/bin/env python3
"""
Weekly AWS Cost Analysis Script
Exemplo de uso para análise semanal automatizada
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agents.cost_analysis_agent import CostAnalysisAgent
from config.settings import Settings, AWSConfig, AnalysisConfig, ReportConfig

async def weekly_analysis():
    """Execute weekly cost analysis"""
    
    print("🔄 AWS Weekly Cost Analysis")
    print("=" * 50)
    
    # Configure for weekly analysis
    settings = Settings()
    
    # AWS Configuration
    settings.aws = AWSConfig(
        profile_name="billing",  # Adjust as needed
        region="us-east-2"
    )
    
    # Weekly Analysis Configuration
    settings.analysis = AnalysisConfig(
        analysis_type="weekly",
        periods_to_analyze=4,  # Last 4 weeks
        min_cost_threshold=5.0,  # Higher threshold for weekly changes
        top_services_count=15,
        top_accounts_count=10,
        max_service_changes=20,
        max_account_changes=15,
        include_account_analysis=True
    )
    
    # Report Configuration
    settings.report = ReportConfig(
        auto_open=True
    )
    
    try:
        # Initialize and run agent
        agent = CostAnalysisAgent(settings)
        
        print("🚀 Starting weekly analysis...")
        result = await agent.execute()
        
        if result.success:
            print("✅ Weekly analysis completed successfully!")
            print(f"📄 Report: {result.report_path}")
            print(f"⏱️  Execution time: {result.execution_time:.2f}s")
            
            # Show summary
            if result.data:
                metadata = result.data.get('metadata', {})
                print(f"\n📊 Weekly Summary:")
                print(f"   Weeks analyzed: {metadata.get('periods_analyzed', 'N/A')}")
                print(f"   Total services: {metadata.get('total_services', 'N/A')}")
                print(f"   Total accounts: {metadata.get('total_accounts', 'N/A')}")
                
                # Show cost trend
                periods_data = result.data.get('periods_data', [])
                if len(periods_data) >= 2:
                    current_week = periods_data[0]
                    previous_week = periods_data[1]
                    change = current_week['total_cost'] - previous_week['total_cost']
                    percent_change = (change / previous_week['total_cost'] * 100) if previous_week['total_cost'] > 0 else 0
                    
                    trend = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                    print(f"\n💰 Week-over-Week Change:")
                    print(f"   {trend} ${change:+,.2f} ({percent_change:+.1f}%)")
                    print(f"   Current week: ${current_week['total_cost']:,.2f}")
                    print(f"   Previous week: ${previous_week['total_cost']:,.2f}")
        else:
            print(f"❌ Weekly analysis failed: {result.error}")
            return 1
            
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(weekly_analysis())
    sys.exit(exit_code)