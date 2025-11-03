#!/usr/bin/env python3
"""
Complete Backend Validation Script
Tests all endpoints expected by the frontend

TEST CREDENTIALS (when auth is implemented):
Email: admin@4bfast.com.br
Password: 4BFast2025!
"""

import requests
import json
from typing import Dict, List, Tuple

API_BASE = "https://api-costhub.4bfast.com.br/api/v1"
HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://costhub.4bfast.com.br"
}

def test_endpoint(method: str, endpoint: str, data: Dict = None) -> Tuple[int, str]:
    """Test a single endpoint"""
    try:
        url = f"{API_BASE}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=HEADERS, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=HEADERS, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=HEADERS, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=HEADERS, timeout=10)
        else:
            return 0, "Invalid method"
            
        return response.status_code, response.text[:200]
        
    except requests.exceptions.RequestException as e:
        return 0, str(e)[:200]

def main():
    """Test all endpoints"""
    
    print("🔍 BACKEND VALIDATION - Complete Endpoint Analysis")
    print("=" * 70)
    
    # Define all endpoints from frontend analysis
    endpoints = [
        # Authentication
        ("POST", "/auth/login", {"email": "test@test.com", "password": "test"}),
        ("POST", "/auth/register", {"email": "test@test.com", "password": "test", "name": "Test"}),
        ("POST", "/auth/logout", {}),
        ("GET", "/auth/me", None),
        ("POST", "/auth/refresh", {}),
        
        # Dashboard
        ("GET", "/dashboard/summary", None),
        ("GET", "/dashboard/cost-trends", None),
        ("GET", "/dashboard", None),
        ("GET", "/dashboard/overview", None),
        
        # Costs
        ("GET", "/costs", None),
        ("GET", "/costs/summary", None),
        ("GET", "/costs/trends", None),
        ("GET", "/costs/breakdown", None),
        ("GET", "/costs/by-service", None),
        ("GET", "/costs/by-region", None),
        
        # Accounts - IMPLEMENTED
        ("GET", "/accounts", None),
        ("POST", "/accounts", {"name": "Test Account", "provider_type": "aws", "credentials": {"access_key": "test"}}),
        ("PUT", "/accounts/test-id", {"name": "Updated Account"}),
        ("DELETE", "/accounts/test-id", None),
        
        # Alarms
        ("GET", "/alarms", None),
        ("POST", "/alarms", {"name": "Test Alarm", "threshold": 100, "comparison": "GreaterThanThreshold"}),
        ("PUT", "/alarms/test-id", {"threshold": 200}),
        ("DELETE", "/alarms/test-id", None),
        
        # Insights
        ("GET", "/insights", None),
        ("GET", "/insights/recommendations", None),
        ("POST", "/insights/generate", {}),
        
        # Users
        ("GET", "/users", None),
        ("GET", "/users/profile", None),
        ("PUT", "/users/profile", {"name": "Updated Name"}),
        
        # Organizations
        ("GET", "/organizations", None),
        ("POST", "/organizations", {"name": "Test Org"}),
        
        # Reports
        ("GET", "/reports", None),
        ("POST", "/reports/generate", {"type": "cost", "period": "monthly"}),
        
        # Health & System
        ("GET", "/health", None),
        ("GET", "/status", None),
    ]
    
    # Test results
    results = {
        "✅ WORKING": [],
        "⚠️ NOT_IMPLEMENTED": [],
        "❌ ERROR": [],
        "🔌 NOT_FOUND": []
    }
    
    print(f"Testing {len(endpoints)} endpoints...")
    
    for i, (method, endpoint, data) in enumerate(endpoints, 1):
        print(f"[{i:2d}/{len(endpoints)}] {method} {endpoint}", end=" ... ")
        
        status, response = test_endpoint(method, endpoint, data)
        endpoint_desc = f"{method} {endpoint}"
        
        if status == 200 or status == 201:
            results["✅ WORKING"].append(endpoint_desc)
            print("✅ OK")
        elif status == 501:
            results["⚠️ NOT_IMPLEMENTED"].append(endpoint_desc)
            print("⚠️ 501")
        elif status == 404 or status == 405:
            results["🔌 NOT_FOUND"].append(endpoint_desc)
            print("🔌 404/405")
        else:
            results["❌ ERROR"].append(f"{endpoint_desc} ({status})")
            print(f"❌ {status}")
    
    # Print results
    print("\n" + "=" * 70)
    for category, endpoints in results.items():
        print(f"\n{category} ({len(endpoints)} endpoints):")
        for endpoint in endpoints:
            print(f"  • {endpoint}")
    
    # Summary
    total = sum(len(endpoints) for endpoints in results.values())
    working = len(results["✅ WORKING"])
    not_implemented = len(results["⚠️ NOT_IMPLEMENTED"])
    errors = len(results["❌ ERROR"]) + len(results["🔌 NOT_FOUND"])
    
    print(f"\n📊 IMPLEMENTATION STATUS:")
    print(f"Total Endpoints: {total}")
    print(f"✅ Working: {working} ({working/total*100:.1f}%)")
    print(f"⚠️ Not Implemented: {not_implemented} ({not_implemented/total*100:.1f}%)")
    print(f"❌ Missing/Error: {errors} ({errors/total*100:.1f}%)")
    
    # Save detailed report
    report = {
        "timestamp": "2025-11-03T00:42:57",
        "total_endpoints": total,
        "working": working,
        "not_implemented": not_implemented,
        "errors": errors,
        "results": results
    }
    
    with open("endpoint_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: endpoint_validation_report.json")
    
    # Next steps based on DEVELOPMENT_SPEC.md
    print(f"\n🎯 NEXT PRIORITIES (from DEVELOPMENT_SPEC.md):")
    print(f"1. 🔄 Deploy and test accounts implementation")
    print(f"2. ⏳ Implement cost data collection (Phase 2)")
    print(f"3. ⏳ Add authentication endpoints (Phase 3)")
    print(f"4. ⏳ Create DynamoDB tables: cost_data, alarms, users, insights")

if __name__ == "__main__":
    main()
