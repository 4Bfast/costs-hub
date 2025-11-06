#!/usr/bin/env python3
"""
Deploy script with dependencies for CostHub Phase 2
Includes PyJWT and other required dependencies in the deployment package
"""

import os
import sys
import json
import boto3
import zipfile
import subprocess
import tempfile
import shutil
from pathlib import Path

# Configuration
LAMBDA_FUNCTION_NAME = "costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV"
AWS_PROFILE = "4bfast"
AWS_REGION = "us-east-1"

def install_dependencies(target_dir):
    """Install Python dependencies to target directory"""
    print("📦 Installing dependencies...")
    
    # Create requirements for Lambda
    lambda_requirements = [
        "PyJWT>=2.8.0",
        "boto3>=1.34.0",
        "botocore>=1.34.0"
    ]
    
    # Write temporary requirements file
    req_file = target_dir / "requirements.txt"
    with open(req_file, 'w') as f:
        f.write('\n'.join(lambda_requirements))
    
    # Install dependencies
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "-r", str(req_file),
            "-t", str(target_dir),
            "--upgrade"
        ], check=True, capture_output=True, text=True)
        
        print("✅ Dependencies installed successfully")
        
        # Remove unnecessary files
        cleanup_patterns = [
            "*.dist-info",
            "__pycache__",
            "*.pyc",
            "tests",
            "test_*"
        ]
        
        for pattern in cleanup_patterns:
            for path in target_dir.glob(f"**/{pattern}"):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        
        # Remove requirements file
        req_file.unlink()
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def create_deployment_package_with_deps():
    """Create deployment package with dependencies"""
    print("📦 Creating deployment package with dependencies...")
    
    # Create temporary directory for packaging
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = Path(temp_dir) / "package"
        package_dir.mkdir()
        
        # Install dependencies first
        if not install_dependencies(package_dir):
            return None
        
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
        zip_path = Path("./costhub_phase2_with_deps.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)
        
        print(f"✅ Deployment package created: {zip_path}")
        print(f"📊 Package size: {zip_path.stat().st_size:,} bytes")
        
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
        
        # Test cost summary endpoint
        cost_test_event = {
            "httpMethod": "GET",
            "path": "/costs/summary",
            "headers": {
                "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjbGllbnRfaWQiOiJ0ZXN0LWNsaWVudC0wMDEiLCJ1c2VybmFtZSI6InRlc3R1c2VyIn0.test",
                "origin": "https://costhub.4bfast.com.br"
            }
        }
        
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Payload=json.dumps(cost_test_event)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            print("✅ Cost summary endpoint test passed")
        elif result.get('statusCode') == 404:
            print("⚠️  Cost summary endpoint: No accounts configured (expected)")
        else:
            print(f"❌ Cost summary endpoint test failed: {result}")
            
        return True
        
    except Exception as e:
        print(f"❌ Testing failed: {e}")
        return False

def main():
    """Main deployment process"""
    print("🚀 CostHub Phase 2 Deployment - With Dependencies")
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
    
    # Create deployment package with dependencies
    zip_path = create_deployment_package_with_deps()
    
    if not zip_path:
        print("❌ Failed to create deployment package")
        return False
    
    # Deploy to Lambda
    deployed = deploy_to_lambda(zip_path)
    
    if deployed:
        # Test deployment
        test_deployment()
        
        print("\n" + "=" * 60)
        print("✅ Phase 2 Deployment Complete!")
        print("\n📋 What's New:")
        print("• Real AWS Cost Explorer integration")
        print("• PyJWT dependency included")
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
    if zip_path and zip_path.exists():
        zip_path.unlink()
        print(f"🧹 Cleaned up: {zip_path}")

if __name__ == "__main__":
    main()
