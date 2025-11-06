import requests
print("Testing alarms endpoint...")
response = requests.get("https://api-costhub.4bfast.com.br/api/v1/alarms")
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
