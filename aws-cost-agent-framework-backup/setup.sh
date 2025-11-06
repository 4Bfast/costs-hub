#!/bin/bash
# Setup script for AWS Cost Analysis Framework

echo "🤖 AWS Cost Analysis Framework Setup"
echo "   Powered by Strands Agent Architecture"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI"
    exit 1
fi

echo "✅ AWS CLI found: $(aws --version)"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Create reports directory
mkdir -p reports
echo "📁 Created reports directory"

# Make scripts executable
chmod +x main.py cli.py
echo "🔧 Made scripts executable"

# Test AWS credentials
echo "🔐 Testing AWS credentials..."
if aws sts get-caller-identity --profile billing &> /dev/null; then
    echo "✅ AWS credentials valid"
else
    echo "⚠️  AWS credentials not configured or invalid"
    echo "💡 Run: aws sso login --profile billing"
fi

echo ""
echo "🎉 Setup completed!"
echo ""
echo "📋 Usage examples:"
echo "   python3 cli.py                              # Basic monthly analysis"
echo "   python3 cli.py --weeks 4                    # Weekly analysis (4 weeks)"
echo "   python3 cli.py --days 7                     # Daily analysis (7 days)"
echo "   python3 smart_forecast.py                   # Smart forecast (recommended)"
echo "   python3 quick_forecast.py                   # Monthly forecast analysis"
echo "   python3 weekly_forecast.py                  # Weekly projection analysis"
echo "   python3 generate_charts.py                  # Interactive charts"
echo "   python3 view_charts.py                      # View generated charts"
echo "   python3 forecast_analysis.py                # Detailed forecast report"
echo "   python3 weekly_analysis.py                  # Dedicated weekly script"
echo "   python3 cli.py --profile billing --months 6 # 6 months analysis"
echo "   python3 cli.py --verbose                    # Detailed logging"
echo "   python3 cli.py --help                       # Show all options"
echo ""
echo "📖 Full documentation: README.md"
