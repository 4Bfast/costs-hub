"""
Internationalization support for AWS Cost Analysis Framework
"""

from typing import Dict, Any

class I18n:
    """Internationalization class for multi-language support"""
    
    def __init__(self, language: str = "pt-BR"):
        self.language = language
        self.translations = self._load_translations()
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """Load translation dictionaries"""
        return {
            "pt-BR": {
                # Headers and titles
                "monthly_cost_analysis": "Análise de Custos Mensal",
                "weekly_cost_analysis": "Análise de Custos Semanal", 
                "daily_cost_analysis": "Análise de Custos Diária",
                "executive_summary": "Resumo Executivo",
                "monthly_overview": "Visão Geral Mensal",
                "weekly_overview": "Visão Geral Semanal",
                "daily_overview": "Visão Geral Diária",
                "top_services_by_cost": "Principais Serviços por Custo",
                "main_cost_changes": "Principais Mudanças de Custo",
                "new_services": "Novos Serviços",
                "cost_summary": "Resumo de Custos",
                "forecast_analysis": "Análise de Previsão",
                "ai_insights": "Insights de IA",
                
                # Table headers
                "service": "Serviço",
                "current_cost": "Custo Atual",
                "previous_cost": "Custo Anterior",
                "change": "Mudança",
                "percentage": "Porcentagem",
                "percent_of_total": "% do Total",
                "status": "Status",
                
                # Status labels
                "new": "NOVO",
                "stable": "ESTÁVEL",
                "increase": "AUMENTO",
                "decrease": "REDUÇÃO",
                
                # Time periods
                "previous_month": "Mês Anterior",
                "current_month": "Mês Atual",
                "previous_week": "Semana Anterior", 
                "current_week": "Semana Atual",
                "previous_day": "Dia Anterior",
                "current_day": "Dia Atual",
                "month": "Mês",
                "week": "Semana",
                "day": "Dia",
                
                # Forecast
                "high_cost_increase_alert": "ALERTA DE ALTO AUMENTO DE CUSTO",
                "cost_increase_warning": "AVISO DE AUMENTO DE CUSTO",
                "costs_under_control": "CUSTOS SOB CONTROLE",
                "forecasted_increase": "Aumento previsto para fim do mês",
                "primary_cost_driver": "Principal direcionador de custo",
                "current_month_progress": "Progresso do Mês Atual",
                "days_elapsed": "Dias decorridos",
                "spent_so_far": "Gasto até agora",
                "daily_average": "Média diária",
                "aws_forecast": "Previsão AWS",
                "forecasted_total": "Total previsto",
                "projected_change": "Mudança projetada",
                "current_trend": "Tendência Atual",
                "projected_total": "Total projetado",
                "trend_change": "Mudança de tendência",
                "vs_aws_forecast": "vs Previsão AWS",
                "top_cost_drivers": "Principais Direcionadores de Custo",
                "current_mtd": "Atual (MTD)",
                "projected": "Projetado",
                
                # Footer
                "generated_on": "Gerado em",
                "data_source": "Dados obtidos da API AWS Cost Explorer",
                "cost_optimization_platform": "Plataforma de Análise e Otimização de Custos AWS",
                
                # Units
                "services": "serviços",
                "accounts": "contas",
                "difference": "diferença",
                
                # AI Summary prompts
                "ai_summary_prompt": """Analise os dados de custo AWS fornecidos e crie um resumo executivo em português brasileiro para empresas clientes. 

Dados de custo:
- Custo atual: ${current_cost}
- Custo anterior: ${previous_cost}
- Mudança: ${change} ({change_percent}%)
- Principais serviços: {top_services}
- Principais mudanças: {main_changes}

Crie um resumo de 2-3 parágrafos que:
1. Explique o cenário atual dos custos de cloud de forma clara
2. Destaque os principais direcionadores de custo
3. Forneça insights sobre tendências e recomendações
4. Use linguagem acessível para executivos não-técnicos

Foque em explicar o valor e impacto dos serviços AWS de forma que o cliente entenda o retorno do investimento."""
            },
            
            "en-US": {
                # Keep original English translations as fallback
                "monthly_cost_analysis": "Monthly Cost Analysis",
                "weekly_cost_analysis": "Weekly Cost Analysis",
                "daily_cost_analysis": "Daily Cost Analysis",
                "executive_summary": "Executive Summary",
                "monthly_overview": "Monthly Overview",
                "weekly_overview": "Weekly Overview", 
                "daily_overview": "Daily Overview",
                "top_services_by_cost": "Top Services by Cost",
                "main_cost_changes": "Main Cost Changes",
                "new_services": "New Services",
                "cost_summary": "Cost Summary",
                "forecast_analysis": "Forecast Analysis",
                "ai_insights": "AI Insights",
                
                "service": "Service",
                "current_cost": "Current Cost",
                "previous_cost": "Previous Cost", 
                "change": "Change",
                "percentage": "Percentage",
                "percent_of_total": "% of Total",
                "status": "Status",
                
                "new": "NEW",
                "stable": "STABLE",
                "increase": "INCREASE",
                "decrease": "DECREASE",
                
                "previous_month": "Previous Month",
                "current_month": "Current Month",
                "previous_week": "Previous Week",
                "current_week": "Current Week", 
                "previous_day": "Previous Day",
                "current_day": "Current Day",
                "month": "Month",
                "week": "Week",
                "day": "Day",
                
                "generated_on": "Generated on",
                "data_source": "Data sourced from AWS Cost Explorer API",
                "cost_optimization_platform": "AWS Cost Analysis & Optimization Platform",
                
                "services": "services",
                "accounts": "accounts",
                "difference": "difference"
            }
        }
    
    def t(self, key: str, **kwargs) -> str:
        """Translate a key to the current language"""
        translations = self.translations.get(self.language, self.translations["en-US"])
        text = translations.get(key, key)
        
        # Simple string formatting
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
                
        return text
    
    def get_period_label(self, analysis_type: str, is_previous: bool = False) -> str:
        """Get localized period label"""
        if is_previous:
            return {
                "monthly": self.t("previous_month"),
                "weekly": self.t("previous_week"),
                "daily": self.t("previous_day")
            }.get(analysis_type, self.t("previous_month"))
        else:
            return {
                "monthly": self.t("current_month"), 
                "weekly": self.t("current_week"),
                "daily": self.t("current_day")
            }.get(analysis_type, self.t("current_month"))
    
    def get_analysis_title(self, analysis_type: str) -> str:
        """Get localized analysis title"""
        return {
            "monthly": self.t("monthly_cost_analysis"),
            "weekly": self.t("weekly_cost_analysis"),
            "daily": self.t("daily_cost_analysis")
        }.get(analysis_type, self.t("monthly_cost_analysis"))
    
    def get_overview_title(self, analysis_type: str) -> str:
        """Get localized overview title"""
        return {
            "monthly": f"📅 {self.t('monthly_overview')}",
            "weekly": f"📅 {self.t('weekly_overview')}", 
            "daily": f"📅 {self.t('daily_overview')}"
        }.get(analysis_type, f"📅 {self.t('monthly_overview')}")
    
    def get_changes_title(self, analysis_type: str) -> str:
        """Get localized changes title"""
        period_type = {
            "monthly": "Mensais",
            "weekly": "Semanais", 
            "daily": "Diárias"
        }.get(analysis_type, "Mensais")
        
        return f"📈 Principais Mudanças de Custo {period_type}"
