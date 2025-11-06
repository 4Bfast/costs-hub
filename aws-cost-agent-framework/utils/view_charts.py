#!/usr/bin/env python3
"""
Chart Viewer - Visualiza os gráficos gerados
"""

import os
import sys
from pathlib import Path
import argparse
from datetime import datetime

def main():
    """Main function"""
    
    print("📊 AWS Cost Analysis Chart Viewer")
    print("=" * 50)
    
    # Get reports directory
    reports_dir = Path("reports")
    
    if not reports_dir.exists():
        print(f"❌ Reports directory not found: {reports_dir}")
        print(f"💡 Generate charts first: python generate_charts.py")
        return 1
    
    # Get chart files
    chart_files = []
    for file_path in reports_dir.glob("*.html"):
        if any(keyword in file_path.name for keyword in [
            'chart', 'forecast_analysis', 'service_trends', 'weekly_analysis'
        ]):
            stat = file_path.stat()
            chart_files.append({
                'path': file_path,
                'name': file_path.name,
                'created': datetime.fromtimestamp(stat.st_mtime)
            })
    
    if not chart_files:
        print(f"📁 No charts found in: {reports_dir}")
        print(f"💡 Generate charts first: python generate_charts.py")
        return 1
    
    # Sort by creation time (newest first)
    chart_files.sort(key=lambda x: x['created'], reverse=True)
    
    print(f"📋 Found {len(chart_files)} charts:")
    for i, chart in enumerate(chart_files, 1):
        age = datetime.now() - chart['created']
        age_str = f"{age.seconds//3600}h {(age.seconds%3600)//60}m ago"
        print(f"   {i}. {chart['name']} ({age_str})")
    
    # Open latest charts
    latest_charts = chart_files[:3]  # Open up to 3 most recent
    
    print(f"\n🌐 Opening {len(latest_charts)} most recent charts...")
    
    for chart in latest_charts:
        try:
            print(f"   📊 Opening: {chart['name']}")
            os.system(f"open '{chart['path']}'")
        except Exception as e:
            print(f"   ❌ Failed to open {chart['name']}: {e}")
    
    print(f"\n✅ Charts opened in your browser!")
    print(f"\n💡 Chart Tips:")
    print(f"   • Charts are interactive - hover over data points")
    print(f"   • Use zoom controls to focus on specific periods")
    print(f"   • Click legend items to show/hide data series")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())