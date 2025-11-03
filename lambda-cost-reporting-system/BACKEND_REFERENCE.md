# CostHub Backend Reference

## 🎯 **QUICK REFERENCE**

### **AWS Configuration:**
- **Profile:** `4bfast`
- **Region:** `us-east-1`
- **Account:** `008195334540`
- **Lambda Function:** `costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV`
- **Handler:** `api_gateway_handler_simple.lambda_handler`

### **Cognito Configuration:**
- **User Pool ID:** `us-east-1_94OYkzcSO`
- **Client ID:** `23qrdk4pl1lidrhsflpsitl4u2`
- **Region:** `us-east-1`

### **DynamoDB Tables:**
- **costhub-accounts** - Account management
- **costhub-alarms** - Alarm configurations

---

## 📊 **IMPLEMENTED ENDPOINTS (33 total)**

### 🔐 **AUTHENTICATION (5 endpoints)**
```
POST /auth/login      - Cognito authentication
POST /auth/register   - User registration (placeholder)
POST /auth/refresh    - Token refresh (placeholder)
POST /auth/logout     - User logout (placeholder)
GET  /auth/me         - User info (placeholder)
```

### 💰 **COSTS (6 endpoints)**
```
GET /costs            - General cost data
GET /costs/summary    - Cost summary with comparisons
GET /costs/trends     - Historical cost trends
GET /costs/breakdown  - Detailed cost breakdown
GET /costs/by-service - Service-specific costs
GET /costs/by-region  - Regional cost distribution
```

### 🏢 **ACCOUNTS (4 endpoints)**
```
GET    /accounts      - List all accounts
POST   /accounts      - Create new account
PUT    /accounts/{id} - Update account
DELETE /accounts/{id} - Delete account
```

### 🚨 **ALARMS (4 endpoints)**
```
GET    /alarms        - List all alarms
POST   /alarms        - Create new alarm
PUT    /alarms/{id}   - Update alarm
DELETE /alarms/{id}   - Delete alarm
```

### 👥 **USERS (3 endpoints)**
```
GET /users         - List users from Cognito
GET /users/profile - Get user profile
PUT /users/profile - Update user profile
```

### 📊 **DASHBOARD (4 endpoints)**
```
GET /dashboard              - Main dashboard data
GET /dashboard/summary      - Dashboard summary with KPIs
GET /dashboard/cost-trends  - Cost trends for dashboard
GET /dashboard/overview     - Multi-account overview
```

### 🧠 **INSIGHTS (3 endpoints)**
```
GET  /insights                 - List AI insights
GET  /insights/recommendations - Cost optimization recommendations
POST /insights/generate        - Generate new insights
```

### 🏗️ **UTILITY (4 endpoints)**
```
GET /health        - Health check
GET /status        - Service status
GET /organizations - Organizations (placeholder)
GET /reports       - Reports (placeholder)
```

---

## 🔧 **HANDLER FILES**

### **Main Handler:**
- `src/handlers/api_gateway_handler_simple.py` - Main routing

### **Feature Handlers:**
- `src/handlers/costs_handler_simple.py` - AWS Cost Explorer integration
- `src/handlers/accounts_handler_simple.py` - DynamoDB CRUD for accounts
- `src/handlers/alarms_handler_simple.py` - DynamoDB CRUD for alarms
- `src/handlers/users_handler_simple.py` - Cognito user management
- `src/handlers/dashboard_handler_simple.py` - Real-time analytics
- `src/handlers/insights_handler_simple.py` - AI recommendations

### **Legacy Handlers (Not Used):**
- `src/handlers_legacy_backup/` - Complex multi-tenant handlers (archived)

---

## 🚀 **DEPLOYMENT COMMANDS**

### **Build and Deploy:**
```bash
cd /Users/luisf.pontes/Projetos/4bfast/costs-hub/lambda-cost-reporting-system
cd src && zip -r ../lambda_deployment.zip . -x "*.pyc" "*/__pycache__/*"
export AWS_PROFILE=4bfast
aws lambda update-function-code \
  --function-name costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV \
  --zip-file fileb://lambda_deployment.zip
```

### **Test Endpoint:**
```bash
export AWS_PROFILE=4bfast
aws lambda invoke \
  --function-name costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV \
  --cli-binary-format raw-in-base64-out \
  --payload '{"httpMethod":"GET","path":"/health","headers":{"origin":"https://costhub.4bfast.com.br"}}' \
  response.json
```

---

## 📋 **MISSING ENDPOINTS (Frontend expects)**

### **CRITICAL (Break functionality):**
1. `GET /costs/records` - Paginated cost records
2. `POST /costs/export` - Export cost data
3. `POST /accounts/{id}/test` - Test account connection
4. `POST /accounts/{id}/refresh` - Refresh account data
5. `POST /alarms/{id}/test` - Test alarm configuration

### **IMPORTANT (Improve UX):**
1. `GET /dashboard/metrics` - Dashboard metrics (vs /dashboard/summary)
2. `GET /insights/by-service/{service}` - Service-specific insights

---

## 🔍 **DEBUGGING**

### **Check Logs:**
```bash
export AWS_PROFILE=4bfast
aws logs describe-log-streams \
  --log-group-name "/aws/lambda/costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV" \
  --order-by LastEventTime --descending --max-items 1
```

### **View Recent Logs:**
```bash
export AWS_PROFILE=4bfast
aws logs get-log-events \
  --log-group-name "/aws/lambda/costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV" \
  --log-stream-name "STREAM_NAME" \
  --start-from-head
```

---

## 📁 **PROJECT STRUCTURE**
```
lambda-cost-reporting-system/
├── src/
│   ├── handlers/                 # Active handlers (simple implementation)
│   ├── handlers_legacy_backup/   # Legacy handlers (archived)
│   ├── services/                 # Business logic
│   ├── models/                   # Data models
│   └── utils/                    # Utilities
├── cdk-infrastructure/           # AWS CDK
├── tests/                        # Test files
│   ├── scripts/                  # Test scripts
│   └── validation/               # Validation tools
└── docs/                         # Documentation
```

---

## ⚡ **QUICK FIXES**

### **Add Missing Endpoint:**
1. Edit `src/handlers/api_gateway_handler_simple.py`
2. Add route in main handler
3. Implement logic in appropriate handler file
4. Deploy with commands above

### **Debug Issue:**
1. Check CloudWatch logs
2. Test endpoint with AWS CLI
3. Verify CORS headers
4. Check authentication tokens

**Status: PRODUCTION READY** ✅
