#!/usr/bin/env python3
"""
Test script for Portuguese reports with AI summary
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from agents.cost_analysis_agent import CostAnalysisAgent
from config.settings import Settings

async def test_portuguese_ai_report():
    """Test Portuguese report generation with AI summary"""
    
    print("🧪 Testando relatório em português com IA...")
    
    # Configure settings for Portuguese and AI
    settings = Settings()
    
    # Set Portuguese language
    settings.report.language = "pt-BR"
    
    # Enable AI features
    settings.ai.enabled = True
    settings.ai.aws_profile = "4bfast"  # Profile for Bedrock access
    settings.ai.include_summary = True
    settings.ai.include_recommendations = True
    
    # Configure analysis for testing
    settings.analysis.analysis_type = "monthly"
    settings.analysis.periods_to_analyze = 3
    settings.analysis.include_account_analysis = False  # Disable redundant account analysis
    settings.analysis.top_services_count = 10
    
    print(f"✅ Configurações:")
    print(f"   - Idioma: {settings.report.language}")
    print(f"   - IA habilitada: {settings.ai.enabled}")
    print(f"   - Profile Bedrock: {settings.ai.aws_profile}")
    print(f"   - Análise de contas: {settings.analysis.include_account_analysis}")
    
    try:
        # Create and execute agent
        agent = CostAnalysisAgent(settings)
        result = await agent.execute()
        
        if result.success:
            print(f"✅ Relatório gerado com sucesso!")
            print(f"   - Arquivo: {result.report_path}")
            print(f"   - Tempo de execução: {result.execution_time:.2f}s")
            print(f"   - Períodos analisados: {result.metadata.get('periods_analyzed', 0)}")
            print(f"   - IA incluída: {result.metadata.get('has_ai_summary', False)}")
            
            # Open report if successful
            if settings.report.auto_open:
                import webbrowser
                webbrowser.open(f"file://{result.report_path}")
                print("🌐 Relatório aberto no navegador")
            
        else:
            print(f"❌ Erro na geração do relatório: {result.error}")
            
    except Exception as e:
        print(f"❌ Erro durante execução: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    print("🚀 Iniciando teste do CostHub em Português com IA")
    print("=" * 60)
    
    # Run async test
    asyncio.run(test_portuguese_ai_report())
    
    print("=" * 60)
    print("✅ Teste concluído!")

if __name__ == "__main__":
    main()
