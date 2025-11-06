import requests
print("Testing users endpoint...")
response = requests.get("https://api-costhub.4bfast.com.br/api/v1/users")
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
