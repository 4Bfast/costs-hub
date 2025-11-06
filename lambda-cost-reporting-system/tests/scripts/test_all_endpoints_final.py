#!/usr/bin/env python3
"""
Test All Endpoints - Final Validation
"""

import requests
import json

API_BASE_URL = "https://api-costhub.4bfast.com.br/api/v1"

def test_endpoint(method, path, expected_status=None):
    """Test a single endpoint"""
    url = f"{API_BASE_URL}{path}"
    
    try:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json={})
        elif method == 'PUT':
            response = requests.put(url, json={})
        elif method == 'DELETE':
            response = requests.delete(url)
        
        status = response.status_code
        
        # Determine expected behavior
        if path.startswith('/auth'):
            expected = 400  # Bad request (missing params)
        elif path in ['/health', '/status']:
            expected = 200  # Should work
        elif 'dashboard' in path or 'insights' in path or 'organizations' in path or 'reports' in path:
            expected = 501  # Not implemented (removed mocks)
        else:
            expected = 401  # Unauthorized (needs auth)
        
        if status == expected:
            print(f"✅ {method} {path} - {status}")
            return True
        else:
            print(f"❌ {method} {path} - {status} (expected {expected})")
            return False
            
    except Exception as e:
        print(f"❌ {method} {path} - ERROR: {e}")
        return False

def main():
    """Test all endpoints"""
    print("🧪 Testing All CostHub Endpoints...")
    print("=" * 60)
    
    endpoints = [
        # Auth endpoints (should return 400 - bad request)
        ('POST', '/auth/login'),
        ('POST', '/auth/register'),
        ('POST', '/auth/refresh'),
        ('POST', '/auth/logout'),
        ('GET', '/auth/me'),
        
        # Business endpoints (should return 401 - unauthorized)
        ('GET', '/costs'),
        ('GET', '/costs/summary'),
        ('GET', '/costs/trends'),
        ('GET', '/costs/breakdown'),
        ('GET', '/costs/by-service'),
        ('GET', '/costs/by-region'),
        
        ('GET', '/accounts'),
        ('POST', '/accounts'),
        ('PUT', '/accounts/test-id'),
        ('DELETE', '/accounts/test-id'),
        
        ('GET', '/alarms'),
        ('POST', '/alarms'),
        ('PUT', '/alarms/test-id'),
        ('DELETE', '/alarms/test-id'),
        
        ('GET', '/users'),
        ('GET', '/users/profile'),
        ('PUT', '/users/profile'),
        
        # Mock endpoints (should return 501 - not implemented)
        ('GET', '/dashboard'),
        ('GET', '/dashboard/summary'),
        ('GET', '/dashboard/cost-trends'),
        ('GET', '/dashboard/overview'),
        
        ('GET', '/insights'),
        ('GET', '/insights/recommendations'),
        ('POST', '/insights/generate'),
        
        ('GET', '/organizations'),
        ('POST', '/organizations'),
        
        ('GET', '/reports'),
        ('POST', '/reports/generate'),
        
        # Utility endpoints (should return 200)
        ('GET', '/health'),
        ('GET', '/status'),
    ]
    
    passed = 0
    total = len(endpoints)
    
    for method, path in endpoints:
        if test_endpoint(method, path):
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"🎯 Results: {passed}/{total} endpoints working as expected")
    print(f"📊 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL ENDPOINTS WORKING CORRECTLY!")
    else:
        print(f"⚠️  {total-passed} endpoints need attention")

if __name__ == "__main__":
    main()
