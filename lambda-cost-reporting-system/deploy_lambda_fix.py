#!/usr/bin/env python3
"""
Deploy Lambda function with accounts fix
"""

import boto3
import zipfile
import os
import tempfile
import shutil

def create_deployment_package():
    """Create deployment package with fixed accounts handler"""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy source files
        src_dir = os.path.join(temp_dir, 'src')
        shutil.copytree('src', src_dir)
        
        # Create zip file
        zip_path = 'lambda_deployment_accounts_fix.zip'
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, temp_dir)
                        zip_file.write(file_path, arc_name)
        
        return zip_path

def deploy_lambda():
    """Deploy Lambda function"""
    
    function_name = 'costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV'
    
    # Create deployment package
    print("Creating deployment package...")
    zip_path = create_deployment_package()
    
    # Upload to Lambda
    print("Uploading to Lambda...")
    session = boto3.Session(profile_name='4bfast')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    try:
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"✅ Successfully updated Lambda function!")
        print(f"Version: {response['Version']}")
        print(f"Last Modified: {response['LastModified']}")
        print(f"Code Size: {response['CodeSize']} bytes")
        
        # Clean up
        os.remove(zip_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        os.remove(zip_path)
        return False

if __name__ == '__main__':
    print("🚀 Deploying Lambda function with accounts fix...")
    
    # Change to project directory
    os.chdir('/Users/luisf.pontes/Projetos/4bfast/costs-hub/lambda-cost-reporting-system')
    
    success = deploy_lambda()
    
    if success:
        print("\n🎉 Deploy completed successfully!")
        print("The accounts handler now properly maps frontend fields:")
        print("  - account_name → name")
        print("  - provider → provider_type")
        print("\nYou can now test the POST /accounts endpoint.")
    else:
        print("\n💥 Deploy failed. Check the error messages above.")
