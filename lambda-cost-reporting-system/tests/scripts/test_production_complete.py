#!/usr/bin/env python3
"""
Complete Production Test Suite - All CostHub Endpoints
Tests real API after deployment with authentication
"""

import requests
import json
import time
from datetime import datetime

API_BASE_URL = "https://api-costhub.4bfast.com.br/api/v1"

class CostHubTester:
    def __init__(self):
        self.token = None
        self.test_results = []
        
    def get_auth_token(self):
        """Get authentication token for testing"""
        print("🔐 Getting authentication token...")
        
        # Try to login (using real account data)
        login_data = {
            "username": "test@4bfast.com.br",
            "password": "TestPassword123!"
        }
        
        try:
            response = requests.post(f"{API_BASE_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                tokens = response.json()['tokens']
                self.token = tokens['IdToken']
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def test_endpoint(self, method, path, data=None, auth_required=True):
        """Test a single endpoint"""
        url = f"{API_BASE_URL}{path}"
        headers = {'Content-Type': 'application/json'}
        
        if auth_required and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data or {}, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data or {}, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            
            # Determine expected status
            expected_status = self.get_expected_status(path, method, auth_required)
            success = response.status_code == expected_status
            
            result = {
                'method': method,
                'path': path,
                'status_code': response.status_code,
                'expected': expected_status,
                'success': success,
                'response_time': response.elapsed.total_seconds(),
                'has_data': len(response.text) > 0
            }
            
            # Try to parse JSON response
            try:
                result['response_data'] = response.json()
            except:
                result['response_data'] = response.text[:200]
            
            self.test_results.append(result)
            
            status_icon = "✅" if success else "❌"
            print(f"{status_icon} {method} {path} - {response.status_code} ({response.elapsed.total_seconds():.2f}s)")
            
            return result
            
        except Exception as e:
            result = {
                'method': method,
                'path': path,
                'status_code': 'ERROR',
                'expected': expected_status,
                'success': False,
                'error': str(e)
            }
            self.test_results.append(result)
            print(f"❌ {method} {path} - ERROR: {e}")
            return result
    
    def get_expected_status(self, path, method, auth_required):
        """Get expected status code for endpoint"""
        if not auth_required:
            if path.startswith('/auth'):
                return 400 if method == 'GET' and path.endswith('/me') else 400
            elif path in ['/health', '/status']:
                return 200
        else:
            # Authenticated endpoints should return 200/201 for success
            if method == 'POST' and any(x in path for x in ['/accounts', '/alarms', '/organizations', '/insights/generate']):
                return 201
            elif method == 'DELETE':
                return 200
            elif method in ['GET', 'PUT']:
                return 200
        
        return 401 if auth_required and not self.token else 200
    
    def run_complete_test_suite(self):
        """Run complete test suite for all endpoints"""
        print("🚀 Starting Complete CostHub Production Test Suite")
        print("=" * 80)
        
        start_time = datetime.now()
        
        # Get authentication token
        if not self.get_auth_token():
            print("❌ Cannot proceed without authentication")
            return
        
        print(f"\n🧪 Testing All Endpoints at {datetime.now()}")
        print("-" * 80)
        
        # Test all endpoints systematically
        
        # 1. Authentication Endpoints (no auth required)
        print("\n🔐 Authentication Endpoints:")
        self.test_endpoint('POST', '/auth/login', {'username': 'test', 'password': 'test'}, False)
        self.test_endpoint('POST', '/auth/register', {'username': 'test', 'password': 'test'}, False)
        self.test_endpoint('POST', '/auth/refresh', {'refresh_token': 'invalid'}, False)
        self.test_endpoint('POST', '/auth/logout', {'access_token': 'invalid'}, False)
        self.test_endpoint('GET', '/auth/me', auth_required=True)
        
        # 2. Cost Endpoints (auth required)
        print("\n💰 Cost Analysis Endpoints:")
        self.test_endpoint('GET', '/costs')
        self.test_endpoint('GET', '/costs/summary')
        self.test_endpoint('GET', '/costs/trends')
        self.test_endpoint('GET', '/costs/breakdown')
        self.test_endpoint('GET', '/costs/by-service')
        self.test_endpoint('GET', '/costs/by-region')
        
        # 3. Accounts CRUD (auth required)
        print("\n👥 Accounts Management:")
        self.test_endpoint('GET', '/accounts')
        account_data = {
            'name': 'Test Account',
            'provider_type': 'aws',
            'status': 'active'
        }
        create_result = self.test_endpoint('POST', '/accounts', account_data)
        
        # If account created, test update and delete
        if create_result.get('success') and create_result.get('response_data'):
            try:
                account_id = create_result['response_data']['data']['account_id']
                self.test_endpoint('PUT', f'/accounts/{account_id}', {'name': 'Updated Test Account'})
                self.test_endpoint('DELETE', f'/accounts/{account_id}')
            except:
                # Fallback to test with dummy ID
                self.test_endpoint('PUT', '/accounts/test-id', {'name': 'Updated Test Account'})
                self.test_endpoint('DELETE', '/accounts/test-id')
        
        # 4. Alarms CRUD (auth required)
        print("\n🚨 Alarms Management:")
        self.test_endpoint('GET', '/alarms')
        alarm_data = {
            'name': 'Test Alarm',
            'threshold': 100.0,
            'comparison': 'GreaterThanThreshold'
        }
        alarm_result = self.test_endpoint('POST', '/alarms', alarm_data)
        
        # If alarm created, test update and delete
        if alarm_result.get('success') and alarm_result.get('response_data'):
            try:
                alarm_id = alarm_result['response_data']['data']['alarm_id']
                self.test_endpoint('PUT', f'/alarms/{alarm_id}', {'threshold': 150.0})
                self.test_endpoint('DELETE', f'/alarms/{alarm_id}')
            except:
                self.test_endpoint('PUT', '/alarms/test-id', {'threshold': 150.0})
                self.test_endpoint('DELETE', '/alarms/test-id')
        
        # 5. Users Management (auth required)
        print("\n👤 Users Management:")
        self.test_endpoint('GET', '/users')
        self.test_endpoint('GET', '/users/profile')
        self.test_endpoint('PUT', '/users/profile', {'name': 'Updated Name'})
        
        # 6. Dashboard Analytics (auth required)
        print("\n📊 Dashboard Analytics:")
        self.test_endpoint('GET', '/dashboard')
        self.test_endpoint('GET', '/dashboard/summary')
        self.test_endpoint('GET', '/dashboard/cost-trends')
        self.test_endpoint('GET', '/dashboard/overview')
        
        # 7. AI Insights (auth required)
        print("\n🤖 AI Insights:")
        self.test_endpoint('GET', '/insights')
        self.test_endpoint('GET', '/insights/recommendations')
        self.test_endpoint('POST', '/insights/generate', {'type': 'full_analysis'})
        
        # 8. Organizations (auth required)
        print("\n🏢 Organizations:")
        self.test_endpoint('GET', '/organizations')
        self.test_endpoint('POST', '/organizations', {'name': 'Test Org'})
        
        # 9. Reports (auth required)
        print("\n📋 Reports:")
        self.test_endpoint('GET', '/reports')
        self.test_endpoint('POST', '/reports/generate', {'type': 'monthly'})
        
        # 10. Utility Endpoints (no auth required)
        print("\n🔧 Utility Endpoints:")
        self.test_endpoint('GET', '/health', auth_required=False)
        self.test_endpoint('GET', '/status', auth_required=False)
        
        # Generate test report
        self.generate_test_report(start_time)
    
    def generate_test_report(self, start_time):
        """Generate comprehensive test report"""
        end_time = datetime.now()
        duration = end_time - start_time
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - successful_tests
        
        print("\n" + "=" * 80)
        print("📊 COMPLETE TEST REPORT")
        print("=" * 80)
        print(f"🕐 Test Duration: {duration.total_seconds():.2f} seconds")
        print(f"📈 Total Tests: {total_tests}")
        print(f"✅ Successful: {successful_tests} ({(successful_tests/total_tests)*100:.1f}%)")
        print(f"❌ Failed: {failed_tests} ({(failed_tests/total_tests)*100:.1f}%)")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   {result['method']} {result['path']} - {result['status_code']} (expected {result['expected']})")
        
        # Performance metrics
        response_times = [r.get('response_time', 0) for r in self.test_results if 'response_time' in r]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            print(f"\n⚡ Performance:")
            print(f"   Average Response Time: {avg_response_time:.3f}s")
            print(f"   Max Response Time: {max_response_time:.3f}s")
        
        # Feature status
        print(f"\n🎯 Feature Status:")
        feature_groups = {
            'Authentication': [r for r in self.test_results if '/auth' in r['path']],
            'Cost Analysis': [r for r in self.test_results if '/costs' in r['path']],
            'Accounts': [r for r in self.test_results if '/accounts' in r['path']],
            'Alarms': [r for r in self.test_results if '/alarms' in r['path']],
            'Users': [r for r in self.test_results if '/users' in r['path']],
            'Dashboard': [r for r in self.test_results if '/dashboard' in r['path']],
            'AI Insights': [r for r in self.test_results if '/insights' in r['path']],
            'Organizations': [r for r in self.test_results if '/organizations' in r['path']],
            'Reports': [r for r in self.test_results if '/reports' in r['path']],
        }
        
        for feature, tests in feature_groups.items():
            if tests:
                success_rate = len([t for t in tests if t['success']]) / len(tests) * 100
                status = "✅" if success_rate == 100 else "⚠️" if success_rate >= 50 else "❌"
                print(f"   {status} {feature}: {success_rate:.0f}% ({len([t for t in tests if t['success']])}/{len(tests)})")
        
        print("\n🎉 Test Suite Complete!")
        
        # Save detailed results to file
        with open('test_results.json', 'w') as f:
            json.dump({
                'timestamp': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'summary': {
                    'total': total_tests,
                    'successful': successful_tests,
                    'failed': failed_tests,
                    'success_rate': (successful_tests/total_tests)*100
                },
                'results': self.test_results
            }, f, indent=2)
        
        print("📄 Detailed results saved to test_results.json")

if __name__ == "__main__":
    tester = CostHubTester()
    tester.run_complete_test_suite()
