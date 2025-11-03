#!/usr/bin/env python3
"""
Local API Server for Lambda Cost Reporting System

This server executes the real Lambda handlers locally for development.
Uses LocalStack for AWS services and real business logic.
"""

import os
import sys
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Set up environment for LocalStack
os.environ.update({
    'AWS_ACCESS_KEY_ID': 'test',
    'AWS_SECRET_ACCESS_KEY': 'test',
    'AWS_DEFAULT_REGION': 'us-east-1',
    'AWS_ENDPOINT_URL': 'http://localhost:4566',
    'ENVIRONMENT': 'local',
    'DYNAMODB_TABLE_NAME': 'cost-reporting-local-clients',
    'S3_BUCKET_NAME': 'cost-reporting-local-reports',
    'KMS_KEY_ID': 'alias/cost-reporting-local-key',
    'LOG_LEVEL': 'DEBUG'
})

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app, 
     origins=["http://localhost:3000"], 
     supports_credentials=True,
     allow_headers=[
         "Content-Type", 
         "Authorization", 
         "X-Request-ID",
         "X-Requested-With",
         "Accept",
         "Origin",
         "Cache-Control",
         "Pragma"
     ],
     methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])

@app.after_request
def after_request(response):
    """Add CORS headers to all responses."""
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Request-ID, X-Requested-With, Accept, Origin, Cache-Control, Pragma'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
    response.headers['Access-Control-Max-Age'] = '86400'  # Cache preflight for 24 hours
    return response

# Mock Lambda context
class MockLambdaContext:
    def __init__(self):
        self.aws_request_id = f"local-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.function_name = "local-dev-api"
        self.function_version = "$LATEST"
        self.remaining_time_in_millis = lambda: 300000

def create_api_gateway_event(method, path, headers, query_params, body):
    """Create API Gateway event from Flask request."""
    return {
        'httpMethod': method,
        'path': path,
        'headers': dict(headers),
        'queryStringParameters': query_params,
        'body': body,
        'requestContext': {
            'requestId': f"local-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'stage': 'local'
        },
        'isBase64Encoded': False
    }

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'success': True,
        'data': {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0-local',
            'localstack': 'http://localhost:4566',
            'dynamodb_admin': 'http://localhost:8001'
        }
    })

# Basic auth endpoints for development
@app.route('/auth/login', methods=['POST'])
def auth_login():
    """Basic login endpoint for development."""
    data = request.get_json() or {}
    
    # Simple validation
    if data.get('email') and data.get('password'):
        response = jsonify({
            'success': True,
            'data': {
                'user': {
                    'id': 'dev-user-123',
                    'name': 'Development User',
                    'email': data['email'],
                    'role': 'ADMIN',
                    'organization_id': 'dev-org-123'
                },
                'organization': {
                    'id': 'dev-org-123',
                    'name': 'Development Organization'
                },
                'token': 'dev-token-123'
            }
        })
        
        # Set cookies for authentication
        response.set_cookie('auth_token', 'dev-token-123', httponly=True, samesite='Lax')
        response.set_cookie('refresh_token', 'dev-refresh-123', httponly=True, samesite='Lax')
        
        return response
    
    return jsonify({
        'success': False,
        'errors': ['Invalid credentials']
    }), 401

@app.route('/auth/me', methods=['GET'])
def auth_me():
    """Get current user endpoint for development."""
    auth_token = request.cookies.get('auth_token')
    
    if auth_token == 'dev-token-123':
        return jsonify({
            'success': True,
            'data': {
                'user': {
                    'id': 'dev-user-123',
                    'name': 'Development User',
                    'email': 'dev@example.com',
                    'role': 'ADMIN',
                    'organization_id': 'dev-org-123'
                },
                'organization': {
                    'id': 'dev-org-123',
                    'name': 'Development Organization'
                }
            }
        })
    
    return jsonify({
        'success': False,
        'errors': ['Not authenticated']
    }), 401

@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    """Logout endpoint for development."""
    response = jsonify({
        'success': True,
        'data': {}
    })
    
    response.set_cookie('auth_token', '', expires=0, httponly=True)
    response.set_cookie('refresh_token', '', expires=0, httponly=True)
    
    return response

# Dashboard endpoints for development - matching backend API structure
@app.route('/dashboard/metrics', methods=['GET'])
def dashboard_metrics():
    """Dashboard metrics endpoint."""
    return jsonify({
        'success': True,
        'data': {
            'total_monthly_cost': 5420.75,
            'month_over_month_change': 12.5,
            'connected_accounts': 3,
            'active_alarms': 2,
            'unread_insights': 5,
            'top_service': {
                'service_name': 'EC2',
                'cost': 2100.50,
                'percentage': 38.7
            }
        }
    })

@app.route('/dashboard/cost-overview', methods=['GET'])
def dashboard_cost_overview():
    """Dashboard cost overview endpoint."""
    return jsonify({
        'success': True,
        'data': {
            'current_period': {
                'total_cost': 5420.75,
                'start_date': '2025-10-01',
                'end_date': '2025-10-31'
            },
            'daily_breakdown': [
                {'date': '2025-10-01', 'cost': 180.25},
                {'date': '2025-10-02', 'cost': 175.50},
                {'date': '2025-10-03', 'cost': 190.75},
                {'date': '2025-10-04', 'cost': 165.30},
                {'date': '2025-10-05', 'cost': 195.80}
            ]
        }
    })

@app.route('/dashboard/service-breakdown', methods=['GET'])
def dashboard_service_breakdown():
    """Dashboard service breakdown endpoint."""
    return jsonify({
        'success': True,
        'data': [
            {
                'service_name': 'EC2',
                'cost': 2100.50,
                'percentage': 38.7,
                'trend': 5.2,
                'provider': 'aws'
            },
            {
                'service_name': 'S3',
                'cost': 850.25,
                'percentage': 15.7,
                'trend': -2.1,
                'provider': 'aws'
            },
            {
                'service_name': 'RDS',
                'cost': 720.80,
                'percentage': 13.3,
                'trend': 8.5,
                'provider': 'aws'
            }
        ]
    })

@app.route('/dashboard/recent-alarms', methods=['GET'])
def dashboard_recent_alarms():
    """Dashboard recent alarms endpoint."""
    return jsonify({
        'success': True,
        'data': [
            {
                'id': 'alarm-1',
                'alarm_name': 'High EC2 Costs',
                'severity': 'high',
                'triggered_at': '2025-11-02T10:30:00Z',
                'current_value': 2100.50,
                'threshold_value': 2000.00,
                'status': 'new',
                'affected_services': ['EC2', 'EBS'],
                'cost_impact': 100.50
            },
            {
                'id': 'alarm-2',
                'alarm_name': 'Budget Exceeded',
                'severity': 'critical',
                'triggered_at': '2025-11-02T09:15:00Z',
                'current_value': 5420.75,
                'threshold_value': 5000.00,
                'status': 'acknowledged',
                'affected_services': ['EC2', 'S3', 'RDS'],
                'cost_impact': 420.75
            }
        ]
    })

@app.route('/dashboard/insights-summary', methods=['GET'])
def dashboard_insights_summary():
    """Dashboard AI insights summary endpoint."""
    return jsonify({
        'success': True,
        'data': {
            'total_new_insights': 8,
            'high_priority_count': 3,
            'potential_monthly_savings': 850.25,
            'recent_insights': [
                {
                    'id': 'insight-1',
                    'type': 'recommendation',
                    'severity': 'high',
                    'title': 'Unused EC2 Instances',
                    'description': 'Found 5 EC2 instances with low utilization',
                    'potential_savings': 320.50,
                    'created_at': '2025-11-02T08:00:00Z'
                },
                {
                    'id': 'insight-2',
                    'type': 'anomaly',
                    'severity': 'medium',
                    'title': 'S3 Cost Spike',
                    'description': 'S3 costs increased by 45% this week',
                    'created_at': '2025-11-01T14:30:00Z'
                }
            ]
        }
    })

# Add missing insights endpoints
@app.route('/insights/summary', methods=['GET'])
def insights_summary():
    """Insights summary endpoint."""
    return dashboard_insights_summary()

@app.route('/insights', methods=['GET'])
def insights_list():
    """Insights list endpoint."""
    return jsonify({
        'success': True,
        'data': [
            {
                'id': 'insight-1',
                'type': 'recommendation',
                'severity': 'high',
                'title': 'Unused EC2 Instances',
                'description': 'Found 5 EC2 instances with low utilization that could be terminated',
                'potential_savings': 320.50,
                'created_at': '2025-11-02T08:00:00Z',
                'affected_services': ['EC2'],
                'status': 'new'
            },
            {
                'id': 'insight-2',
                'type': 'anomaly',
                'severity': 'medium',
                'title': 'S3 Cost Spike',
                'description': 'S3 costs increased by 45% this week due to increased data transfer',
                'created_at': '2025-11-01T14:30:00Z',
                'affected_services': ['S3'],
                'status': 'new'
            },
            {
                'id': 'insight-3',
                'type': 'optimization',
                'severity': 'medium',
                'title': 'RDS Instance Rightsizing',
                'description': 'RDS instance is oversized for current workload',
                'potential_savings': 180.75,
                'created_at': '2025-11-01T10:15:00Z',
                'affected_services': ['RDS'],
                'status': 'acknowledged'
            }
        ],
        'pagination': {
            'page': 1,
            'limit': 20,
            'total': 3,
            'total_pages': 1
        }
    })

# Add more common endpoints
@app.route('/dashboard', methods=['GET'])
def dashboard_main():
    """Main dashboard endpoint."""
    return jsonify({
        'success': True,
        'data': {
            'metrics': dashboard_metrics().get_json()['data'],
            'cost_overview': dashboard_cost_overview().get_json()['data'],
            'service_breakdown': dashboard_service_breakdown().get_json()['data']
        }
    })

@app.route('/accounts', methods=['GET'])
def accounts_list():
    """Accounts list endpoint."""
    return jsonify({
        'success': True,
        'data': [
            {
                'id': 'acc-1',
                'provider': 'aws',
                'account_name': 'Production AWS',
                'account_id': '123456789012',
                'status': 'active',
                'last_sync': '2025-11-02T15:30:00Z'
            }
        ]
    })

@app.route('/costs', methods=['GET'])
def costs_list():
    """Costs list endpoint."""
    return jsonify({
        'success': True,
        'data': {
            'total_cost': 5420.75,
            'period': '2025-10-01 to 2025-10-31',
            'breakdown': dashboard_service_breakdown().get_json()['data']
        }
    })

# Import Lambda handler after environment is set
HANDLER_AVAILABLE = False
try:
    from handlers.api_handler import lambda_handler
    HANDLER_AVAILABLE = True
    logger.info("✅ Lambda handler imported successfully")
except Exception as e:
    logger.warning(f"⚠️ Lambda handler not available: {e}")
    logger.info("🔧 Running in mock mode for development")

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def api_proxy(path):
    """Proxy API requests to Lambda handler."""
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Request-ID, X-Requested-With, Accept, Origin, Cache-Control, Pragma'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response
    
    if not HANDLER_AVAILABLE:
        return jsonify({
            'success': False,
            'errors': ['Lambda handlers not available - running in mock mode'],
            'message': 'Install dependencies or use mock endpoints for development'
        }), 503
    
    try:
        # Create API Gateway event
        event = create_api_gateway_event(
            method=request.method,
            path=f'/{path}',
            headers=request.headers,
            query_params=dict(request.args) if request.args else None,
            body=request.get_data(as_text=True) if request.data else None
        )
        
        # Create mock context
        context = MockLambdaContext()
        
        # Call Lambda handler
        response = lambda_handler(event, context)
        
        # Parse response
        status_code = response.get('statusCode', 200)
        headers = response.get('headers', {})
        body = response.get('body', '{}')
        
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                pass
        
        # Create Flask response
        flask_response = jsonify(body)
        flask_response.status_code = status_code
        
        for key, value in headers.items():
            flask_response.headers[key] = value
        
        return flask_response
        
    except Exception as e:
        logger.error(f"API request failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'errors': [f'Request failed: {str(e)}']
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'errors': ['Endpoint not found']
    }), 404

# ===== ALL MISSING ENDPOINTS =====

# Cost Data endpoints
@app.route('/cost-data', methods=['GET'])
@app.route('/cost-data/summary', methods=['GET'])
@app.route('/cost-data/trends', methods=['GET'])
@app.route('/cost-data/providers', methods=['GET'])
def cost_data_endpoints():
    return jsonify({'success': True, 'data': {'total_cost': 5420.75}})

# Insights endpoints (additional)
@app.route('/insights/anomalies', methods=['GET'])
@app.route('/insights/recommendations', methods=['GET'])
@app.route('/insights/forecasts', methods=['GET'])
def insights_endpoints():
    return insights_list()

# Client endpoints
@app.route('/clients/me', methods=['GET', 'PUT'])
@app.route('/clients/me/accounts', methods=['GET', 'POST'])
@app.route('/clients/me/accounts/<account_id>', methods=['DELETE'])
def client_endpoints(account_id=None):
    return jsonify({'success': True, 'data': {'id': 'client-123'}})

# Webhook endpoints
@app.route('/webhooks', methods=['GET', 'POST'])
@app.route('/webhooks/<webhook_id>', methods=['GET', 'PUT', 'DELETE'])
def webhook_endpoints(webhook_id=None):
    return jsonify({'success': True, 'data': []})

# Notification endpoints
@app.route('/notifications/send', methods=['POST'])
@app.route('/notifications/history', methods=['GET'])
@app.route('/notifications/preferences', methods=['GET', 'PUT'])
def notification_endpoints():
    return jsonify({'success': True, 'data': []})

# Account endpoints
@app.route('/accounts/discovered/refresh', methods=['POST'])
@app.route('/accounts/discovered/stats', methods=['GET'])
@app.route('/accounts/discovered/suggestions', methods=['GET'])
@app.route('/accounts/discovered/<account_id>', methods=['GET'])
@app.route('/accounts/discovered/<account_id>/link', methods=['POST'])
@app.route('/accounts/<account_id>/refresh', methods=['POST'])
def account_endpoints(account_id=None):
    return accounts_list()

# Alarm endpoints
@app.route('/alarms', methods=['GET', 'POST'])
@app.route('/alarms/<alarm_id>', methods=['GET', 'PUT', 'DELETE'])
def alarm_endpoints(alarm_id=None):
    return dashboard_recent_alarms()

# User management endpoints
@app.route('/users', methods=['GET', 'POST'])
@app.route('/users/<user_id>', methods=['GET', 'PUT', 'DELETE'])
def user_endpoints(user_id=None):
    return jsonify({'success': True, 'data': []})

# Settings endpoints
@app.route('/settings', methods=['GET', 'PUT'])
@app.route('/settings/organization', methods=['GET', 'PUT'])
@app.route('/settings/billing', methods=['GET', 'PUT'])
def settings_endpoints():
    return jsonify({'success': True, 'data': {}})

# Analysis endpoints
@app.route('/analysis/cost-breakdown', methods=['GET'])
@app.route('/analysis/trends', methods=['GET'])
@app.route('/analysis/forecasts', methods=['GET'])
def analysis_endpoints():
    return jsonify({'success': True, 'data': []})

# Provider connection endpoints
@app.route('/connections', methods=['GET'])
@app.route('/connections/aws', methods=['POST'])
@app.route('/connections/gcp', methods=['POST'])
@app.route('/connections/azure', methods=['POST'])
@app.route('/connections/<connection_id>', methods=['GET', 'PUT', 'DELETE'])
def connection_endpoints(connection_id=None):
    return jsonify({'success': True, 'data': []})

if __name__ == '__main__':
    print("🚀 Lambda Cost Reporting System - Local Development Server")
    print("📍 Server: http://localhost:8000")
    print("🔗 API Base: http://localhost:8000/api/v1")
    print("💡 Health: http://localhost:8000/health")
    print("🔐 Auth: http://localhost:8000/api/v1/auth/login")
    print("🐳 LocalStack: http://localhost:4566")
    print("🗄️  DynamoDB Admin: http://localhost:8001")
    print("")
    
    if HANDLER_AVAILABLE:
        print("✅ Lambda handlers loaded successfully")
    else:
        print("🔧 Running in mock mode - Lambda handlers not loaded")
        print("   This is normal for initial development setup")
    
    print("")
    
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=True,
        threaded=True
    )