#!/usr/bin/env python3
"""
Deploy script for CostHub Phase 2 - Cost Explorer Integration
Deploys the new cost endpoints with real AWS Cost Explorer data
"""

import os
import sys
import json
import boto3
import zipfile
import subprocess
from pathlib import Path

# Configuration
LAMBDA_FUNCTION_NAME = "costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV"
AWS_PROFILE = "4bfast"
AWS_REGION = "us-east-1"

def create_deployment_package():
    """Create deployment package with new cost endpoints"""
    print("📦 Creating deployment package...")
    
    # Create temporary directory for packaging
    package_dir = Path("./lambda_package")
    package_dir.mkdir(exist_ok=True)
    
    # Files to include in deployment
    files_to_copy = [
        "src/handlers/api_gateway_handler_simple.py",
        "handlers/costs_handler_real.py",
        "services/aws_cost_service.py",
        "utils/jwt_utils.py",
        "config/settings.py"
    ]
    
    # Copy files maintaining directory structure
    for file_path in files_to_copy:
        src_path = Path(file_path)
        if src_path.exists():
            dest_path = package_dir / file_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            import shutil
            shutil.copy2(src_path, dest_path)
            print(f"✅ Copied {file_path}")
        else:
            print(f"⚠️  File not found: {file_path}")
    
    # Create __init__.py files
    init_dirs = [
        package_dir / "src",
        package_dir / "src" / "handlers",
        package_dir / "handlers",
        package_dir / "services",
        package_dir / "utils",
        package_dir / "config"
    ]
    
    for init_dir in init_dirs:
        if init_dir.exists():
            (init_dir / "__init__.py").touch()
    
    # Create zip file
    zip_path = Path("./costhub_phase2_deployment.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
                print(f"📁 Added to zip: {arcname}")
    
    # Cleanup
    import shutil
    shutil.rmtree(package_dir)
    
    print(f"✅ Deployment package created: {zip_path}")
    return zip_path

def deploy_to_lambda(zip_path):
    """Deploy package to Lambda function"""
    print(f"🚀 Deploying to Lambda function: {LAMBDA_FUNCTION_NAME}")
    
    try:
        # Initialize AWS session
        session = boto3.Session(profile_name=AWS_PROFILE)
        lambda_client = session.client('lambda', region_name=AWS_REGION)
        
        # Read zip file
        with open(zip_path, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Update function code
        response = lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=zip_content
        )
        
        print(f"✅ Deployment successful!")
        print(f"📊 Function size: {response.get('CodeSize', 0):,} bytes")
        print(f"🔄 Last modified: {response.get('LastModified')}")
        print(f"📝 Version: {response.get('Version')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return False

def test_deployment():
    """Test the deployed endpoints"""
    print("\n🧪 Testing deployed endpoints...")
    
    try:
        session = boto3.Session(profile_name=AWS_PROFILE)
        lambda_client = session.client('lambda', region_name=AWS_REGION)
        
        # Test health endpoint
        test_event = {
            "httpMethod": "GET",
            "path": "/health",
            "headers": {
                "origin": "https://costhub.4bfast.com.br"
            }
        }
        
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Payload=json.dumps(test_event)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            print("✅ Health endpoint test passed")
            body = json.loads(result.get('body', '{}'))
            print(f"📊 Service: {body.get('service')}")
            print(f"🔢 Version: {body.get('version')}")
        else:
            print(f"❌ Health endpoint test failed: {result}")
            
        return True
        
    except Exception as e:
        print(f"❌ Testing failed: {e}")
        return False

def update_environment_variables():
    """Update Lambda environment variables"""
    print("\n🔧 Updating environment variables...")
    
    try:
        session = boto3.Session(profile_name=AWS_PROFILE)
        lambda_client = session.client('lambda', region_name=AWS_REGION)
        
        # Environment variables for Phase 2
        env_vars = {
            'AWS_REGION': AWS_REGION,
            'AWS_ACCOUNT_ID': '008195334540',
            'COGNITO_USER_POOL_ID': 'us-east-1_94OYkzcSO',
            'COGNITO_CLIENT_ID': '23qrdk4pl1lidrhsflpsitl4u2',
            'DYNAMODB_ACCOUNTS_TABLE': 'costhub-accounts',
            'CORS_ALLOWED_ORIGINS': 'https://costhub.4bfast.com.br,https://www.costhub.4bfast.com.br',
            'ENABLE_AI_INSIGHTS': 'true',
            'ENABLE_COST_ALERTS': 'true',
            'DEFAULT_COST_PERIOD_DAYS': '30'
        }
        
        response = lambda_client.update_function_configuration(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Environment={'Variables': env_vars}
        )
        
        print("✅ Environment variables updated")
        for key, value in env_vars.items():
            print(f"   {key}: {value}")
            
        return True
        
    except Exception as e:
        print(f"❌ Environment update failed: {e}")
        return False

def main():
    """Main deployment process"""
    print("🚀 CostHub Phase 2 Deployment - Cost Explorer Integration")
    print("=" * 60)
    
    # Check AWS credentials
    try:
        session = boto3.Session(profile_name=AWS_PROFILE)
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS Account: {identity['Account']}")
        print(f"✅ AWS Profile: {AWS_PROFILE}")
        print(f"✅ AWS Region: {AWS_REGION}")
    except Exception as e:
        print(f"❌ AWS credentials check failed: {e}")
        return False
    
    # Create deployment package
    zip_path = create_deployment_package()
    
    # Update environment variables
    env_updated = update_environment_variables()
    
    # Deploy to Lambda
    deployed = deploy_to_lambda(zip_path)
    
    if deployed:
        # Test deployment
        test_deployment()
        
        print("\n" + "=" * 60)
        print("✅ Phase 2 Deployment Complete!")
        print("\n📋 What's New:")
        print("• Real AWS Cost Explorer integration")
        print("• 6 cost endpoints with real data")
        print("• JWT token client_id extraction")
        print("• Multi-account cost aggregation ready")
        print("• Fallback handling for API errors")
        
        print("\n🔗 Test Endpoints:")
        print("• GET /health - Health check")
        print("• GET /costs/summary - Cost summary")
        print("• GET /costs/trends - Cost trends")
        print("• GET /costs/breakdown - Cost breakdown")
        print("• GET /costs/by-service - Costs by service")
        print("• GET /costs/by-region - Costs by region")
        
        print(f"\n🌐 API Base URL: https://api-costhub.4bfast.com.br")
        print(f"🔧 Lambda Function: {LAMBDA_FUNCTION_NAME}")
        
        print("\n📝 Next Steps:")
        print("1. Test endpoints with real JWT tokens")
        print("2. Verify frontend integration")
        print("3. Monitor CloudWatch logs")
        print("4. Proceed to Phase 3 (AI Insights)")
        
    else:
        print("\n❌ Deployment failed - check logs above")
    
    # Cleanup
    if zip_path.exists():
        zip_path.unlink()
        print(f"🧹 Cleaned up: {zip_path}")

if __name__ == "__main__":
    main()
