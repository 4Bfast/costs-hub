#!/usr/bin/env python3
"""
Weekly Cost Projection Analysis
Projeção de custos para fim da semana baseada na tendência atual
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tools.aws_cost_tools import AWSCostTools
from config.settings import AWSConfig

async def weekly_forecast():
    """Weekly cost projection analysis"""
    
    print("📅 Weekly AWS Cost Projection")
    print("=" * 50)
    
    # Create AWS config
    aws_config = AWSConfig(
        profile_name="billing",
        region="us-east-2"
    )
    
    # Create cost tools
    cost_tools = AWSCostTools(aws_config)
    
    try:
        print("📊 Analyzing current week vs previous week...")
        
        # Get weekly projection analysis
        analysis = await cost_tools.analyze_weekly_projection()
        
        if analysis.get('error'):
            print(f"❌ Error: {analysis['error']}")
            return 1
        
        # Extract key information
        summary = analysis.get('summary', {})
        current = analysis.get('current_week', {})
        projection = analysis.get('projection', {})
        service_drivers = analysis.get('service_drivers', {})
        
        # Show summary
        week_percent = summary.get('week_increase_percent', 0)
        
        print(f"\n📈 WEEKLY PROJECTION SUMMARY:")
        print(f"   Week period: {current.get('week_start')} to {current.get('week_end')}")
        print(f"   Current week spent: ${current.get('total_cost', 0):,.2f}")
        print(f"   Days elapsed: {current.get('days_elapsed', 0)} of 7")
        print(f"   Daily average: ${projection.get('daily_average', 0):,.2f}")
        print(f"   Projected week-end: ${projection.get('projected_total', 0):,.2f}")
        print(f"   Change vs last week: {week_percent:+.1f}%")
        
        # Alert level (higher thresholds for weekly)
        if week_percent > 25:
            print(f"\n🚨 HIGH ALERT: Custo semanal projetado {week_percent:+.1f}% acima da semana anterior!")
        elif week_percent > 10:
            print(f"\n⚠️  WARNING: Custo semanal projetado {week_percent:+.1f}% acima da semana anterior")
        elif week_percent < -10:
            print(f"\n📉 GOOD: Custo semanal {week_percent:+.1f}% abaixo da semana anterior")
        else:
            print(f"\n✅ OK: Custos semanais estáveis ({week_percent:+.1f}%)")
        
        # Show top cost drivers
        if service_drivers:
            print(f"\n🎯 PRINCIPAIS VARIAÇÕES DESTA SEMANA:")
            print("-" * 60)
            
            count = 0
            total_increase = 0
            
            for service, data in service_drivers.items():
                change = data.get('projected_change', 0)
                if abs(change) < 2:  # Only show changes > $2 for weekly
                    continue
                
                if count >= 8:  # Show top 8
                    break
                
                current_cost = data.get('current_cost', 0)
                projected_cost = data.get('projected_cost', 0)
                percent_change = data.get('projected_percent_change', 0)
                
                # Determine direction and severity
                if change > 50:
                    icon = "🚨" if change > 0 else "📉"
                elif abs(change) > 20:
                    icon = "⚠️" if change > 0 else "📉"
                else:
                    icon = "📈" if change > 0 else "📉"
                
                direction = "Aumento" if change > 0 else "Redução"
                
                print(f"{icon} {service}")
                print(f"   Gasto atual (parcial): ${current_cost:,.2f}")
                print(f"   Projeção semana: ${projected_cost:,.2f}")
                print(f"   {direction}: {change:+.2f} ({percent_change:+.1f}%)")
                print()
                
                if change > 0:
                    total_increase += change
                count += 1
            
            if count == 0:
                print("   Nenhuma variação significativa detectada")
            elif total_increase > 0:
                print(f"💰 Total do aumento dos serviços: +${total_increase:,.2f}")
        
        # Weekly recommendations
        print(f"\n💡 RECOMENDAÇÕES SEMANAIS:")
        if week_percent > 25:
            print("   • Investigar imediatamente os serviços com maior variação")
            print("   • Verificar se há recursos novos ou mudanças de configuração")
            print("   • Considerar ajustes antes do fim da semana")
        elif week_percent > 10:
            print("   • Monitorar diariamente até o fim da semana")
            print("   • Revisar os principais cost drivers")
            print("   • Preparar ações para próxima semana se necessário")
        else:
            print("   • Continuar monitoramento semanal regular")
            print("   • Manter práticas atuais")
        
        # Context about weekly vs monthly
        print(f"\n📋 Contexto:")
        print(f"   • Projeção baseada na tendência dos últimos {current.get('days_elapsed', 0)} dias")
        print(f"   • Variações semanais são normais (threshold: ±10%)")
        print(f"   • Para análise mensal completa: python quick_forecast.py")
        
    except Exception as e:
        print(f"💥 Erro: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(weekly_forecast())
    sys.exit(exit_code)