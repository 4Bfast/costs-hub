#!/usr/bin/env python3
"""
Quick Forecast Analysis
Resposta rápida para: "Qual recurso está elevando meu custo projetado?"
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tools.aws_cost_tools import AWSCostTools
from config.settings import AWSConfig

async def quick_forecast():
    """Quick forecast analysis to identify cost drivers"""
    
    print("🔮 Quick AWS Cost Forecast Analysis")
    print("=" * 50)
    
    # Create AWS config
    aws_config = AWSConfig(
        profile_name="billing",
        region="us-east-2"
    )
    
    # Create cost tools
    cost_tools = AWSCostTools(aws_config)
    
    try:
        print("📊 Analyzing current month vs forecast...")
        
        # Get forecast analysis
        analysis = await cost_tools.analyze_forecast_vs_current()
        
        if analysis.get('error'):
            print(f"❌ Error: {analysis['error']}")
            return 1
        
        # Extract key information
        summary = analysis.get('summary', {})
        current = analysis.get('current_month', {})
        forecast_data = analysis.get('forecast', {})
        service_drivers = analysis.get('service_drivers', {})
        
        # Show summary
        forecast_percent = summary.get('forecast_increase_percent', 0)
        
        print(f"\n📈 FORECAST SUMMARY:")
        print(f"   Current month spent: ${current.get('total_cost', 0):,.2f}")
        print(f"   Days elapsed: {current.get('days_elapsed', 0)} of {current.get('days_elapsed', 0) + current.get('days_remaining', 0)}")
        print(f"   Projected month-end: ${forecast_data.get('total_forecast', 0):,.2f}")
        print(f"   Change vs last month: {forecast_percent:+.1f}%")
        
        # Alert level
        if forecast_percent > 10:
            print(f"\n🚨 HIGH ALERT: Custo projetado {forecast_percent:+.1f}% acima do mês anterior!")
        elif forecast_percent > 4:
            print(f"\n⚠️  WARNING: Custo projetado {forecast_percent:+.1f}% acima do mês anterior")
        else:
            print(f"\n✅ OK: Custos sob controle ({forecast_percent:+.1f}%)")
        
        # Show top cost drivers
        if service_drivers:
            print(f"\n🎯 PRINCIPAIS RESPONSÁVEIS PELO AUMENTO:")
            print("-" * 60)
            
            count = 0
            total_increase = 0
            
            for service, data in service_drivers.items():
                change = data.get('projected_change', 0)
                if change <= 5:  # Only show significant increases
                    continue
                
                if count >= 8:  # Show top 8
                    break
                
                current_cost = data.get('current_cost', 0)
                projected_cost = data.get('projected_cost', 0)
                percent_change = data.get('projected_percent_change', 0)
                
                # Determine severity
                if change > 500:
                    icon = "🚨"
                elif change > 100:
                    icon = "⚠️"
                else:
                    icon = "📈"
                
                print(f"{icon} {service}")
                print(f"   Gasto atual: ${current_cost:,.2f}")
                print(f"   Projeção: ${projected_cost:,.2f}")
                print(f"   Aumento: +${change:,.2f} ({percent_change:+.1f}%)")
                print()
                
                total_increase += change
                count += 1
            
            if count == 0:
                print("   Nenhum serviço com aumento significativo detectado")
            else:
                print(f"💰 Total do aumento dos top {count} serviços: +${total_increase:,.2f}")
        
        # Recommendations
        print(f"\n💡 RECOMENDAÇÕES:")
        if forecast_percent > 10:
            print("   • Revisar imediatamente os serviços com maior aumento")
            print("   • Verificar se há recursos não utilizados")
            print("   • Considerar otimizações de instâncias")
        elif forecast_percent > 4:
            print("   • Monitorar de perto os próximos dias")
            print("   • Revisar os principais cost drivers")
        else:
            print("   • Continuar monitoramento regular")
            print("   • Manter práticas atuais de otimização")
        
        print(f"\n📋 Para análise completa, execute: python cli.py --months 3")
        
    except Exception as e:
        print(f"💥 Erro: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(quick_forecast())
    sys.exit(exit_code)