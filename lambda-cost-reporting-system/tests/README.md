# Tests Directory

## 📁 **Structure**

### **scripts/** - Test Scripts
- `test_*.py` - Endpoint testing scripts
- `create_test_*.py` - Test data creation scripts
- `decode_*.py` - Token decoding utilities
- `get_*.py` - Token retrieval scripts
- `deploy_and_test.sh` - Deployment and testing script

### **validation/** - Validation Tools
- `validate_*.py` - Endpoint validation scripts
- `check_*.py` - Status checking scripts
- `*.json` - Test results and validation reports

## 🚀 **Usage**

### **Run Endpoint Tests:**
```bash
cd tests/scripts
export AWS_PROFILE=4bfast
python test_auth_endpoints_fixed.py
python test_costs_endpoints.py
```

### **Validate All Endpoints:**
```bash
cd tests/validation
python validate_all_endpoints.py
```

### **Check Endpoint Status:**
```bash
cd tests/validation
python check_endpoints_status.py
```

## 📋 **Test Files**

### **Authentication Tests:**
- `test_auth_endpoints_fixed.py` - Auth endpoint testing
- `test_with_browser_token.py` - Browser token testing

### **Feature Tests:**
- `test_costs_endpoints.py` - Cost endpoints
- `test_accounts_no_auth.py` - Account endpoints
- `test_new_features.py` - New feature testing

### **Validation:**
- `validate_all_endpoints.py` - Complete validation
- `validate_endpoints_no_auth.py` - No-auth validation
- `validate_with_auth.py` - Authenticated validation
- `validate_with_cognito_token.py` - Cognito token validation

### **Utilities:**
- `decode_jwt.py` - JWT token decoder
- `get_fresh_token.py` - Fresh token retrieval
- `get_jwt_token.py` - JWT token getter

## ⚠️ **Important Notes**

- All test scripts require AWS profile `4bfast`
- Some tests require valid Cognito tokens
- Test results are saved as JSON files
- Scripts are for development/debugging only

## 🔧 **Configuration**

Make sure to set:
```bash
export AWS_PROFILE=4bfast
export AWS_REGION=us-east-1
```

Lambda function: `costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV`
