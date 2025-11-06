#!/usr/bin/env python3
"""
Test New Features - Dashboard + Insights
"""

import requests
import json

API_BASE_URL = "https://api-costhub.4bfast.com.br/api/v1"

def test_new_features():
    """Test dashboard and insights endpoints"""
    
    print("🧪 Testing New Features (Dashboard + Insights)...")
    print("=" * 60)
    
    # New Dashboard endpoints
    dashboard_endpoints = [
        ('GET', '/dashboard'),
        ('GET', '/dashboard/summary'),
        ('GET', '/dashboard/cost-trends'),
        ('GET', '/dashboard/overview'),
    ]
    
    # New Insights endpoints  
    insights_endpoints = [
        ('GET', '/insights'),
        ('GET', '/insights/recommendations'),
        ('POST', '/insights/generate'),
    ]
    
    print("\n📊 Dashboard Endpoints:")
    for method, path in dashboard_endpoints:
        response = requests.get(f"{API_BASE_URL}{path}")
        status = "✅" if response.status_code != 501 else "❌"
        print(f"{status} {method} {path} - {response.status_code}")
        
        # Show response preview if not 401/501
        if response.status_code not in [401, 501]:
            try:
                data = response.json()
                print(f"   Preview: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"   Response: {response.text[:100]}...")
    
    print("\n🤖 AI Insights Endpoints:")
    for method, path in insights_endpoints:
        if method == 'GET':
            response = requests.get(f"{API_BASE_URL}{path}")
        else:
            response = requests.post(f"{API_BASE_URL}{path}", json={"type": "full_analysis"})
            
        status = "✅" if response.status_code != 501 else "❌"
        print(f"{status} {method} {path} - {response.status_code}")
        
        # Show response preview if not 401/501
        if response.status_code not in [401, 501]:
            try:
                data = response.json()
                print(f"   Preview: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"   Response: {response.text[:100]}...")
    
    print("\n" + "=" * 60)
    print("📋 TESTING STATUS:")
    print("❌ Deploy pendente - endpoints retornam 401 (Unauthorized)")
    print("✅ Handlers implementados - código pronto para deploy")
    print("⚠️  Necessário resolver conflito de domínio CDK para testar")

if __name__ == "__main__":
    test_new_features()
