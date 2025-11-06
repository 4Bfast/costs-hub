#!/usr/bin/env python3
"""
Test Backend with Browser Token
Use this after logging in at https://costhub.4bfast.com.br
"""

import requests
import sys

def test_endpoints(token: str):
    """Test endpoints with valid JWT token"""
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": "https://costhub.4bfast.com.br"
    }
    
    # Core endpoints to test
    endpoints = [
        ("GET", "/accounts", "List accounts"),
        ("POST", "/accounts", "Create account", {"name": "Test", "provider_type": "aws"}),
        ("GET", "/dashboard/summary", "Dashboard summary"),
        ("GET", "/costs", "Cost data"),
        ("GET", "/alarms", "Alarms"),
        ("GET", "/insights", "Insights"),
    ]
    
    print("🔍 TESTING WITH VALID TOKEN")
    print("=" * 50)
    
    results = {"✅ WORKING": [], "⚠️ NOT_IMPLEMENTED": [], "❌ ERROR": []}
    
    for method, endpoint, description, *data in endpoints:
        print(f"{method} {endpoint} ({description})", end=" ... ")
        
        try:
            url = f"https://api-costhub.4bfast.com.br/api/v1{endpoint}"
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                payload = data[0] if data else {}
                response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            status = response.status_code
            
            if status == 200 or status == 201:
                results["✅ WORKING"].append(f"{method} {endpoint}")
                print("✅ WORKING")
                # Show response preview
                try:
                    resp_data = response.json()
                    print(f"    Response: {str(resp_data)[:100]}...")
                except:
                    print(f"    Response: {response.text[:100]}...")
                    
            elif status == 501:
                results["⚠️ NOT_IMPLEMENTED"].append(f"{method} {endpoint}")
                print("⚠️ NOT IMPLEMENTED")
                
            else:
                results["❌ ERROR"].append(f"{method} {endpoint} ({status})")
                print(f"❌ ERROR ({status})")
                
        except Exception as e:
            results["❌ ERROR"].append(f"{method} {endpoint} (exception)")
            print(f"❌ EXCEPTION: {str(e)[:50]}")
    
    # Summary
    print("\n" + "=" * 50)
    for category, endpoints in results.items():
        print(f"\n{category} ({len(endpoints)}):")
        for endpoint in endpoints:
            print(f"  • {endpoint}")
    
    total = sum(len(endpoints) for endpoints in results.values())
    working = len(results["✅ WORKING"])
    
    print(f"\n📊 RESULT: {working}/{total} endpoints working ({working/total*100:.1f}%)")

def main():
    print("🔑 BROWSER TOKEN TESTER")
    print("=" * 30)
    print("STEPS:")
    print("1. Go to https://costhub.4bfast.com.br")
    print("2. Login with admin@4bfast.com.br / 4BFast2025!")
    print("3. Open DevTools > Network tab")
    print("4. Make any request and copy Authorization header")
    print("5. Paste token below (without 'Bearer ' prefix)")
    print()
    
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        token = input("Enter JWT token: ").strip()
    
    if not token:
        print("❌ No token provided")
        return
    
    # Remove Bearer prefix if present
    if token.startswith('Bearer '):
        token = token[7:]
    
    test_endpoints(token)

if __name__ == "__main__":
    main()
