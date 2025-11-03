#!/usr/bin/env python3
import json
import base64
from datetime import datetime

token = "eyJraWQiOiIyUTNaQitwbDFSZU51d21Wc3R0V1gxQUEzSG5GWW9kY2p4ZDhBQ2pcL1crWT0iLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiI5NDQ4YjRjOC1kMDIxLTcwZWItYTA3ZC0wOTQ4YjVhYTZkNDIiLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAudXMtZWFzdC0xLmFtYXpvbmF3cy5jb21cL3VzLWVhc3QtMV85NE9Za3pjU08iLCJjb2duaXRvOnVzZXJuYW1lIjoiOTQ0OGI0YzgtZDAyMS03MGViLWEwN2QtMDk0OGI1YWE2ZDQyIiwib3JpZ2luX2p0aSI6ImQyY2M1Y2NkLTJjODctNDFiNi04OThkLWYxYmQ1MzI0ODZlOCIsImF1ZCI6IjIzcXJkazRwbDFsaWRyaHNmbHBzaXRsNHUyIiwiZXZlbnRfaWQiOiI3ZTEwYmFiNC03ODBjLTRjYmUtOGY2Yy1iMDU5OTA5…I6IkFkbWluIDRCRmFzdCIsImV4cCI6MTc2MjE0NTUyMiwiaWF0IjoxNzYyMTQxOTIyLCJqdGkiOiI3ZmQ2ZmQ5MS0wYzZhLTRjZDAtYmUxZC1kMTZmM2E2YmJlMWYiLCJlbWFpbCI6ImFkbWluQDRiZmFzdC5jb20uYnIifQ"

# Split token
parts = token.split('.')
if len(parts) != 3:
    print("Invalid JWT token")
    exit(1)

# Decode payload (add padding if needed)
payload = parts[1]
payload += '=' * (4 - len(payload) % 4)

try:
    decoded = base64.b64decode(payload)
    data = json.loads(decoded)
    
    print("JWT Token Info:")
    print(f"Subject: {data.get('sub')}")
    print(f"Email: {data.get('email')}")
    print(f"Audience: {data.get('aud')}")
    print(f"Issuer: {data.get('iss')}")
    
    # Check expiration
    exp = data.get('exp')
    iat = data.get('iat')
    
    if exp:
        exp_date = datetime.fromtimestamp(exp)
        print(f"Expires: {exp_date}")
        print(f"Current: {datetime.now()}")
        print(f"Valid: {'Yes' if datetime.now() < exp_date else 'No - EXPIRED'}")
    
    if iat:
        iat_date = datetime.fromtimestamp(iat)
        print(f"Issued: {iat_date}")
        
except Exception as e:
    print(f"Error decoding token: {e}")
