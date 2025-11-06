#!/usr/bin/env python3
"""
Deploy the fixed accounts handler to Lambda
"""

import boto3
import zipfile
import os
import tempfile

def deploy_accounts_fix():
    """Deploy the fixed accounts handler"""
    
    # Read the current Lambda function code
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Function name from the logs
    function_name = 'costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV'
    
    try:
        # Get current function
        response = lambda_client.get_function(FunctionName=function_name)
        print(f"Found function: {function_name}")
        
        # Download current code
        code_url = response['Code']['Location']
        print(f"Downloading current code from: {code_url}")
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download and extract current code
            import urllib.request
            zip_path = os.path.join(temp_dir, 'current_code.zip')
            urllib.request.urlretrieve(code_url, zip_path)
            
            # Extract current code
            extract_dir = os.path.join(temp_dir, 'extracted')
            os.makedirs(extract_dir)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Read the fixed accounts handler
            with open('accounts_handler_fix.py', 'r') as f:
                fixed_handler_code = f.read()
            
            # Find and update the accounts handler in the main file
            main_file = None
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.py') and 'handler' in file.lower():
                        main_file = os.path.join(root, file)
                        break
                if main_file:
                    break
            
            if not main_file:
                # Look for index.py or lambda_function.py
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file in ['index.py', 'lambda_function.py', 'app.py']:
                            main_file = os.path.join(root, file)
                            break
                    if main_file:
                        break
            
            if main_file:
                print(f"Found main file: {main_file}")
                
                # Read current content
                with open(main_file, 'r') as f:
                    current_content = f.read()
                
                # Replace or add the accounts handler
                if 'def handle_accounts(' in current_content:
                    # Replace existing handler
                    import re
                    pattern = r'def handle_accounts\(.*?\n(?:.*?\n)*?(?=def|\Z)'
                    new_content = re.sub(pattern, fixed_handler_code + '\n\n', current_content, flags=re.MULTILINE | re.DOTALL)
                else:
                    # Add new handler
                    new_content = current_content + '\n\n' + fixed_handler_code
                
                # Write updated content
                with open(main_file, 'w') as f:
                    f.write(new_content)
                
                print("Updated accounts handler in main file")
            else:
                # Create new file with the handler
                handler_file = os.path.join(extract_dir, 'accounts_handler.py')
                with open(handler_file, 'w') as f:
                    f.write(fixed_handler_code)
                print("Created new accounts_handler.py file")
            
            # Create new zip file
            new_zip_path = os.path.join(temp_dir, 'updated_code.zip')
            with zipfile.ZipFile(new_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, extract_dir)
                        zip_ref.write(file_path, arc_name)
            
            # Upload updated code
            with open(new_zip_path, 'rb') as f:
                zip_content = f.read()
            
            print("Uploading updated code to Lambda...")
            update_response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            
            print(f"Successfully updated function. New version: {update_response['Version']}")
            print("Accounts handler has been fixed with proper field mapping!")
            
    except Exception as e:
        print(f"Error deploying fix: {str(e)}")
        return False
    
    return True

if __name__ == '__main__':
    deploy_accounts_fix()
