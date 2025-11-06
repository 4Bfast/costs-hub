"""
Chart generation tools for AWS Cost Analysis
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class ChartGenerator:
    """Generate interactive charts for cost analysis"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        
    def generate_monthly_comparison_chart(self, periods_data: List[Dict], 
                                        changes: Dict, analysis_type: str = "monthly") -> str:
        """Generate monthly cost comparison chart"""
        
        # Prepare data
        periods = []
        costs = []
        service_counts = []
        
        for period in periods_data:
            periods.append(period['name'])
            costs.append(period['total_cost'])
            service_counts.append(period['service_count'])
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                f'{analysis_type.title()} Cost Trend', 
                'Service Count Trend',
                'Top Services Current Period',
                'Cost Change Analysis'
            ),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"type": "pie"}, {"type": "bar"}]]
        )
        
        # 1. Cost trend line chart
        fig.add_trace(
            go.Scatter(
                x=periods, 
                y=costs,
                mode='lines+markers',
                name='Total Cost',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=8)
            ),
            row=1, col=1
        )
        
        # 2. Service count trend
        fig.add_trace(
            go.Scatter(
                x=periods, 
                y=service_counts,
                mode='lines+markers',
                name='Service Count',
                line=dict(color='#10b981', width=3),
                marker=dict(size=8)
            ),
            row=1, col=2
        )
        
        # 3. Top services pie chart (current period)
        if periods_data:
            current_services = periods_data[0]['services']
            top_services = sorted(current_services.items(), key=lambda x: x[1], reverse=True)[:8]
            
            services_names = [s[0] for s in top_services]
            services_costs = [s[1] for s in top_services]
            
            fig.add_trace(
                go.Pie(
                    labels=services_names,
                    values=services_costs,
                    name="Top Services"
                ),
                row=2, col=1
            )
        
        # 4. Cost changes bar chart
        if changes.get('service_changes'):
            service_changes = list(changes['service_changes'].items())[:10]
            change_services = [s[0] for s in service_changes]
            change_values = [s[1]['change'] for s in service_changes]
            change_colors = ['#dc2626' if v > 0 else '#059669' for v in change_values]
            
            fig.add_trace(
                go.Bar(
                    x=change_services,
                    y=change_values,
                    name="Cost Changes",
                    marker_color=change_colors
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            title=f"AWS Cost Analysis Dashboard - {analysis_type.title()}",
            height=800,
            showlegend=True,
            template="plotly_white"
        )
        
        # Update x-axis labels for better readability
        fig.update_xaxes(tickangle=45, row=2, col=2)
        
        # Save chart
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"cost_analysis_chart_{analysis_type}_{timestamp}.html"
        filepath = self.output_dir / filename
        
        fig.write_html(str(filepath))
        logger.info(f"Chart generated: {filepath}")
        
        return str(filepath)
    
    def generate_forecast_chart(self, forecast_analysis: Dict) -> str:
        """Generate forecast comparison chart"""
        
        if not forecast_analysis or forecast_analysis.get('error'):
            return ""
        
        current = forecast_analysis.get('current_month', {})
        previous = forecast_analysis.get('previous_month', {})
        forecast_data = forecast_analysis.get('forecast', {})
        service_drivers = forecast_analysis.get('service_drivers', {})
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Monthly Cost Comparison', 
                'Current Month Progress',
                'Top Cost Drivers',
                'Service Projections'
            ),
            specs=[[{"type": "bar"}, {"type": "indicator"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # 1. Monthly comparison bar chart
        months = ['Previous Month', 'Current (MTD)', 'Forecasted']
        values = [
            previous.get('total_cost', 0),
            current.get('total_cost', 0),
            forecast_data.get('total_forecast', 0)
        ]
        colors = ['#6b7280', '#3b82f6', '#f59e0b']
        
        fig.add_trace(
            go.Bar(
                x=months,
                y=values,
                name="Monthly Costs",
                marker_color=colors
            ),
            row=1, col=1
        )
        
        # 2. Current month progress indicator
        days_elapsed = current.get('days_elapsed', 0)
        days_total = days_elapsed + current.get('days_remaining', 0)
        progress = (days_elapsed / days_total * 100) if days_total > 0 else 0
        
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=progress,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Month Progress (%)"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#3b82f6"},
                    'steps': [
                        {'range': [0, 50], 'color': "#f3f4f6"},
                        {'range': [50, 80], 'color': "#e5e7eb"},
                        {'range': [80, 100], 'color': "#d1d5db"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ),
            row=1, col=2
        )
        
        # 3. Top cost drivers
        if service_drivers:
            top_drivers = list(service_drivers.items())[:8]
            driver_names = [d[0] for d in top_drivers]
            driver_changes = [d[1]['projected_change'] for d in top_drivers]
            driver_colors = ['#dc2626' if v > 0 else '#059669' for v in driver_changes]
            
            fig.add_trace(
                go.Bar(
                    x=driver_names,
                    y=driver_changes,
                    name="Cost Drivers",
                    marker_color=driver_colors
                ),
                row=2, col=1
            )
        
        # 4. Service projections scatter plot
        if service_drivers:
            current_costs = [d[1]['current_cost'] for d in top_drivers]
            projected_costs = [d[1]['projected_cost'] for d in top_drivers]
            
            fig.add_trace(
                go.Scatter(
                    x=current_costs,
                    y=projected_costs,
                    mode='markers+text',
                    text=driver_names,
                    textposition="top center",
                    name="Current vs Projected",
                    marker=dict(size=10, color='#3b82f6')
                ),
                row=2, col=2
            )
            
            # Add diagonal line (y=x) for reference
            max_cost = max(max(current_costs), max(projected_costs))
            fig.add_trace(
                go.Scatter(
                    x=[0, max_cost],
                    y=[0, max_cost],
                    mode='lines',
                    name="No Change Line",
                    line=dict(dash='dash', color='gray')
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            title="AWS Cost Forecast Analysis Dashboard",
            height=800,
            showlegend=True,
            template="plotly_white"
        )
        
        # Update x-axis labels
        fig.update_xaxes(tickangle=45, row=2, col=1)
        fig.update_xaxes(title="Current Cost ($)", row=2, col=2)
        fig.update_yaxes(title="Projected Cost ($)", row=2, col=2)
        
        # Save chart
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"forecast_analysis_chart_{timestamp}.html"
        filepath = self.output_dir / filename
        
        fig.write_html(str(filepath))
        logger.info(f"Forecast chart generated: {filepath}")
        
        return str(filepath)
    
    def generate_weekly_comparison_chart(self, weekly_analysis: Dict) -> str:
        """Generate weekly comparison chart"""
        
        if not weekly_analysis or weekly_analysis.get('error'):
            return ""
        
        current = weekly_analysis.get('current_week', {})
        projection = weekly_analysis.get('projection', {})
        service_drivers = weekly_analysis.get('service_drivers', {})
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Weekly Progress', 
                'Daily Spending Trend',
                'Weekly Service Changes',
                'Current vs Projected Costs'
            ),
            specs=[[{"type": "indicator"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # 1. Weekly progress indicator
        days_elapsed = current.get('days_elapsed', 0)
        progress = (days_elapsed / 7 * 100)
        
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=progress,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Week Progress (%)"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#10b981"},
                    'steps': [
                        {'range': [0, 30], 'color': "#f3f4f6"},
                        {'range': [30, 70], 'color': "#e5e7eb"},
                        {'range': [70, 100], 'color': "#d1d5db"}
                    ]
                }
            ),
            row=1, col=1
        )
        
        # 2. Daily spending simulation (based on current average)
        daily_avg = projection.get('daily_average', 0)
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        daily_costs = [daily_avg] * 7  # Simplified - could be more sophisticated
        
        # Mark elapsed vs remaining days
        colors = ['#3b82f6' if i < days_elapsed else '#e5e7eb' for i in range(7)]
        
        fig.add_trace(
            go.Bar(
                x=days,
                y=daily_costs,
                name="Daily Average",
                marker_color=colors
            ),
            row=1, col=2
        )
        
        # 3. Weekly service changes
        if service_drivers:
            top_changes = list(service_drivers.items())[:8]
            change_names = [c[0] for c in top_changes]
            change_values = [c[1]['projected_change'] for c in top_changes]
            change_colors = ['#dc2626' if v > 0 else '#059669' for v in change_values]
            
            fig.add_trace(
                go.Bar(
                    x=change_names,
                    y=change_values,
                    name="Weekly Changes",
                    marker_color=change_colors
                ),
                row=2, col=1
            )
        
        # 4. Current vs projected scatter
        if service_drivers:
            current_costs = [c[1]['current_cost'] for c in top_changes]
            projected_costs = [c[1]['projected_cost'] for c in top_changes]
            
            fig.add_trace(
                go.Scatter(
                    x=current_costs,
                    y=projected_costs,
                    mode='markers+text',
                    text=change_names,
                    textposition="top center",
                    name="Current vs Projected",
                    marker=dict(size=10, color='#10b981')
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            title="AWS Weekly Cost Analysis Dashboard",
            height=800,
            showlegend=True,
            template="plotly_white"
        )
        
        # Update axes
        fig.update_xaxes(tickangle=45, row=2, col=1)
        fig.update_xaxes(title="Current Cost ($)", row=2, col=2)
        fig.update_yaxes(title="Projected Cost ($)", row=2, col=2)
        
        # Save chart
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"weekly_analysis_chart_{timestamp}.html"
        filepath = self.output_dir / filename
        
        fig.write_html(str(filepath))
        logger.info(f"Weekly chart generated: {filepath}")
        
        return str(filepath)
    
    def generate_service_trend_chart(self, periods_data: List[Dict], 
                                   top_services: List[str] = None) -> str:
        """Generate service-specific trend chart"""
        
        if not periods_data:
            return ""
        
        # Get top services if not provided
        if not top_services:
            all_services = set()
            for period in periods_data:
                all_services.update(period['services'].keys())
            
            # Calculate total costs per service across all periods
            service_totals = {}
            for service in all_services:
                total = sum(period['services'].get(service, 0) for period in periods_data)
                service_totals[service] = total
            
            # Get top 10 services
            top_services = sorted(service_totals.items(), key=lambda x: x[1], reverse=True)[:10]
            top_services = [s[0] for s in top_services]
        
        # Create line chart for service trends
        fig = go.Figure()
        
        periods = [p['name'] for p in periods_data]
        
        # Add line for each top service
        colors = px.colors.qualitative.Set3
        for i, service in enumerate(top_services):
            costs = [period['services'].get(service, 0) for period in periods_data]
            
            fig.add_trace(
                go.Scatter(
                    x=periods,
                    y=costs,
                    mode='lines+markers',
                    name=service,
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=6)
                )
            )
        
        # Update layout
        fig.update_layout(
            title="Service Cost Trends Over Time",
            xaxis_title="Period",
            yaxis_title="Cost ($)",
            height=600,
            template="plotly_white",
            hovermode='x unified'
        )
        
        # Save chart
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"service_trends_chart_{timestamp}.html"
        filepath = self.output_dir / filename
        
        fig.write_html(str(filepath))
        logger.info(f"Service trends chart generated: {filepath}")
        
        return str(filepath)