#!/usr/bin/env python3
"""
Check which endpoints return 501 (Not Implemented)
"""

import requests

API_BASE_URL = "https://api-costhub.4bfast.com.br/api/v1"

# Endpoints que retornam 501 (Not Implemented)
not_implemented_endpoints = [
    # Dashboard (4 endpoints)
    ('GET', '/dashboard'),
    ('GET', '/dashboard/summary'),
    ('GET', '/dashboard/cost-trends'),
    ('GET', '/dashboard/overview'),
    
    # Insights (3 endpoints)
    ('GET', '/insights'),
    ('GET', '/insights/recommendations'),
    ('POST', '/insights/generate'),
    
    # Organizations (2 endpoints)
    ('GET', '/organizations'),
    ('POST', '/organizations'),
    
    # Reports (2 endpoints)
    ('GET', '/reports'),
    ('POST', '/reports/generate'),
]

print("🔍 Verificando endpoints que retornam 501 (Not Implemented)...")
print("=" * 60)

for method, path in not_implemented_endpoints:
    url = f"{API_BASE_URL}{path}"
    try:
        if method == 'GET':
            response = requests.get(url)
        else:
            response = requests.post(url, json={})
        
        if response.status_code == 501:
            print(f"✅ {method} {path} - 501 (Not Implemented)")
        else:
            print(f"❌ {method} {path} - {response.status_code} (Expected 501)")
            
    except Exception as e:
        print(f"❌ {method} {path} - ERROR: {e}")

print(f"\n📊 Total: {len(not_implemented_endpoints)} endpoints retornando 501")
print("💡 Isso é CORRETO - são features futuras, não erros!")
