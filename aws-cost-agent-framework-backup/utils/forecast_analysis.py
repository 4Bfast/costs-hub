#!/usr/bin/env python3
"""
AWS Cost Forecast Analysis Script
Responde à pergunta: "Qual recurso está elevando meu custo projetado?"
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agents.cost_analysis_agent import CostAnalysisAgent
from config.settings import Settings, AWSConfig, AnalysisConfig, ReportConfig

async def forecast_analysis():
    """Execute forecast analysis to identify cost drivers"""
    
    print("🔮 AWS Cost Forecast Analysis")
    print("=" * 50)
    print("Identificando recursos que estão elevando o custo projetado...")
    print()
    
    # Configure for monthly analysis with forecast
    settings = Settings()
    
    # AWS Configuration
    settings.aws = AWSConfig(
        profile_name="billing",  # Adjust as needed
        region="us-east-2"
    )
    
    # Monthly Analysis Configuration (forecast only works with monthly)
    settings.analysis = AnalysisConfig(
        analysis_type="monthly",
        periods_to_analyze=2,  # Current and previous month
        min_cost_threshold=1.0,
        top_services_count=20,
        top_accounts_count=10,
        include_account_analysis=True
    )
    
    # Report Configuration
    settings.report = ReportConfig(
        auto_open=True
    )
    
    try:
        # Initialize and run agent
        agent = CostAnalysisAgent(settings)
        
        print("🚀 Starting forecast analysis...")
        result = await agent.execute()
        
        if result.success:
            print("✅ Forecast analysis completed successfully!")
            print(f"📄 Report: {result.report_path}")
            print(f"⏱️  Execution time: {result.execution_time:.2f}s")
            
            # Show forecast summary
            if result.data and result.data.get('forecast_analysis'):
                forecast = result.data['forecast_analysis']
                
                if not forecast.get('error'):
                    summary = forecast.get('summary', {})
                    current = forecast.get('current_month', {})
                    forecast_data = forecast.get('forecast', {})
                    service_drivers = forecast.get('service_drivers', {})
                    
                    print(f"\n🔮 Forecast Summary:")
                    print(f"   Current month spent: ${current.get('total_cost', 0):,.2f}")
                    print(f"   Days elapsed: {current.get('days_elapsed', 0)}")
                    print(f"   AWS Forecast: ${forecast_data.get('total_forecast', 0):,.2f}")
                    print(f"   Projected increase: {summary.get('forecast_increase_percent', 0):+.1f}%")
                    
                    if summary.get('is_trending_up'):
                        print(f"\n⚠️  ALERT: Costs trending up!")
                        print(f"   Primary driver: {summary.get('top_driver', 'Unknown')}")
                        print(f"   Driver increase: +${summary.get('top_driver_increase', 0):,.2f}")
                    else:
                        print(f"\n✅ Costs are under control")
                    
                    # Show top 5 cost drivers
                    if service_drivers:
                        print(f"\n🎯 Top Cost Drivers:")
                        count = 0
                        for service, data in service_drivers.items():
                            if count >= 5:
                                break
                            
                            change = data.get('projected_change', 0)
                            if change <= 0:
                                continue
                            
                            current_cost = data.get('current_cost', 0)
                            projected_cost = data.get('projected_cost', 0)
                            percent_change = data.get('projected_percent_change', 0)
                            
                            print(f"   {count + 1}. {service}")
                            print(f"      Current: ${current_cost:,.2f} → Projected: ${projected_cost:,.2f}")
                            print(f"      Increase: +${change:,.2f} ({percent_change:+.1f}%)")
                            print()
                            
                            count += 1
                else:
                    print(f"⚠️  Forecast analysis failed: {forecast.get('error')}")
            else:
                print("ℹ️  No forecast data available")
                
        else:
            print(f"❌ Forecast analysis failed: {result.error}")
            return 1
            
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(forecast_analysis())
    sys.exit(exit_code)