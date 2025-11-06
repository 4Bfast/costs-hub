import requests
print("Testing accounts endpoint...")
response = requests.get("https://api-costhub.4bfast.com.br/api/v1/accounts")
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
