import requests
print("Testing dashboard endpoints...")

endpoints = [
    '/dashboard',
    '/dashboard/summary', 
    '/dashboard/cost-trends',
    '/dashboard/overview'
]

for endpoint in endpoints:
    response = requests.get(f"https://api-costhub.4bfast.com.br/api/v1{endpoint}")
    print(f"{endpoint}: {response.status_code}")
    if response.status_code != 401:
        print(f"  Response: {response.text[:100]}...")
