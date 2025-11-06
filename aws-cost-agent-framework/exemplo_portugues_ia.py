#!/usr/bin/env python3
"""
Exemplo de uso do CostHub com relatórios em português e IA
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from agents.cost_analysis_agent import CostAnalysisAgent
from config.settings import Settings

async def exemplo_relatorio_portugues():
    """Exemplo de geração de relatório em português com IA"""
    
    print("🇧🇷 CostHub - Relatório em Português com IA")
    print("=" * 50)
    
    # Configurar settings
    settings = Settings()
    
    # Configurações de idioma e IA
    settings.report.language = "pt-BR"
    settings.ai.enabled = True
    settings.ai.aws_profile = "4bfast"  # Profile com acesso ao Bedrock
    settings.ai.include_summary = True
    settings.ai.include_recommendations = True
    
    # Configurações de análise (sem redundância de contas)
    settings.analysis.analysis_type = "monthly"
    settings.analysis.periods_to_analyze = 3
    settings.analysis.include_account_analysis = False  # Remove redundância
    settings.analysis.top_services_count = 10
    settings.analysis.min_cost_threshold = 5.0
    
    # Configurações AWS
    settings.aws.profile_name = "4bfast"  # Profile para dados de custo
    settings.aws.region = "us-east-2"
    
    print("✅ Configurações aplicadas:")
    print(f"   • Idioma: {settings.report.language}")
    print(f"   • IA habilitada: {settings.ai.enabled}")
    print(f"   • Profile AWS (custos): {settings.aws.profile_name}")
    print(f"   • Profile AWS (IA): {settings.ai.aws_profile}")
    print(f"   • Análise de contas: {settings.analysis.include_account_analysis}")
    print(f"   • Períodos: {settings.analysis.periods_to_analyze} meses")
    print()
    
    try:
        # Executar análise
        print("🚀 Iniciando análise de custos...")
        agent = CostAnalysisAgent(settings)
        result = await agent.execute()
        
        if result.success:
            print("✅ Análise concluída com sucesso!")
            print(f"📄 Relatório: {result.report_path}")
            print(f"⏱️  Tempo: {result.execution_time:.2f}s")
            
            # Mostrar estatísticas
            metadata = result.metadata or {}
            print(f"📊 Estatísticas:")
            print(f"   • Períodos analisados: {metadata.get('periods_analyzed', 0)}")
            print(f"   • Total de serviços: {metadata.get('total_services', 0)}")
            print(f"   • IA incluída: {'Sim' if metadata.get('has_ai_summary') else 'Não'}")
            
            # Abrir relatório
            if settings.report.auto_open:
                import webbrowser
                webbrowser.open(f"file://{result.report_path}")
                print("🌐 Relatório aberto no navegador")
            
        else:
            print(f"❌ Erro: {result.error}")
            
    except Exception as e:
        print(f"❌ Erro durante execução: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Função principal"""
    asyncio.run(exemplo_relatorio_portugues())

if __name__ == "__main__":
    main()
