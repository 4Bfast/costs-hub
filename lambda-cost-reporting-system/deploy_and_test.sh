#!/bin/bash

echo "🚀 CostHub Deploy and Test Pipeline"
echo "=================================="

# Step 1: Deploy to production
echo "📦 Step 1: Deploying to production..."
cd infrastructure
./deploy-frontend-api.sh

if [ $? -eq 0 ]; then
    echo "✅ Deploy successful"
else
    echo "❌ Deploy failed - checking status..."
    # Continue anyway to test current version
fi

# Step 2: Wait for deployment to propagate
echo "⏳ Step 2: Waiting for deployment to propagate..."
sleep 30

# Step 3: Run complete test suite
echo "🧪 Step 3: Running complete test suite..."
cd ..
python3 test_production_complete.py

# Step 4: Generate summary
echo ""
echo "📊 Test Summary:"
if [ -f "test_results.json" ]; then
    python3 -c "
import json
with open('test_results.json', 'r') as f:
    results = json.load(f)
    
print(f'✅ Success Rate: {results[\"summary\"][\"success_rate\"]:.1f}%')
print(f'📈 Total Tests: {results[\"summary\"][\"total\"]}')
print(f'⚡ Duration: {results[\"duration_seconds\"]:.1f}s')
"
else
    echo "❌ No test results file found"
fi

echo ""
echo "🎯 Pipeline Complete!"
echo "Check test_results.json for detailed results"
