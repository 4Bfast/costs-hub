"""
Lambda Handler for Cost Collection Orchestration

This module provides Lambda handlers for the cost collection orchestration system,
supporting both EventBridge scheduled events and API Gateway requests.
"""

import json
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ..services.orchestration_integration_service import (
    OrchestrationIntegrationService, OrchestrationConfig, create_orchestration_service
)
from ..services.collection_scheduler import ScheduleFrequency
from ..services.cost_collection_orchestrator import CollectionPriority
from ..models.multi_cloud_models import CloudProvider
from ..models.provider_models import DateRange
from ..utils.logging import create_logger


logger = create_logger(__name__)

# Global orchestration service instance
orchestration_service: Optional[OrchestrationIntegrationService] = None


def get_orchestration_service() -> OrchestrationIntegrationService:
    """Get or create the orchestration service instance."""
    global orchestration_service
    
    if orchestration_service is None:
        config = OrchestrationConfig(
            max_concurrent_tasks=int(os.environ.get('MAX_CONCURRENT_TASKS', '10')),
            max_concurrent_per_provider=int(os.environ.get('MAX_CONCURRENT_PER_PROVIDER', '3')),
            enable_monitoring=os.environ.get('ENABLE_MONITORING', 'true').lower() == 'true',
            enable_xray=os.environ.get('ENABLE_XRAY', 'true').lower() == 'true',
            queue_prefix=os.environ.get('QUEUE_PREFIX', 'cost-collection'),
            metrics_namespace=os.environ.get('METRICS_NAMESPACE', 'CostAnalytics/Collection'),
            region=os.environ.get('AWS_REGION', 'us-east-1')
        )
        
        orchestration_service = create_orchestration_service(config)
    
    return orchestration_service


async def initialize_service():
    """Initialize the orchestration service."""
    service = get_orchestration_service()
    if not service.is_initialized:
        await service.initialize()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for orchestration requests.
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        Lambda response
    """
    try:
        # Determine event source and route accordingly
        if event.get('source') == 'aws.events':
            # EventBridge scheduled event
            return asyncio.run(handle_scheduled_event(event, context))
        elif event.get('httpMethod'):
            # API Gateway request
            return asyncio.run(handle_api_request(event, context))
        elif event.get('Records'):
            # SQS messages
            return asyncio.run(handle_sqs_messages(event, context))
        else:
            # Direct invocation
            return asyncio.run(handle_direct_invocation(event, context))
    
    except Exception as e:
        logger.error(f"Error in lambda handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }


async def handle_scheduled_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle EventBridge scheduled events.
    
    Args:
        event: EventBridge event
        context: Lambda context
        
    Returns:
        Response dictionary
    """
    try:
        await initialize_service()
        service = get_orchestration_service()
        
        logger.info("Processing scheduled collection event", extra={'event': event})
        
        # Parse schedule information
        detail_type = event.get('detail-type', '')
        scheduled_time = datetime.fromisoformat(event.get('time', '').replace('Z', '+00:00'))
        
        # Determine frequency from event
        frequency = ScheduleFrequency.DAILY  # default
        if 'weekly' in detail_type.lower():
            frequency = ScheduleFrequency.WEEKLY
        elif 'monthly' in detail_type.lower():
            frequency = ScheduleFrequency.MONTHLY
        elif 'hourly' in detail_type.lower():
            frequency = ScheduleFrequency.HOURLY
        
        # Get all active clients
        clients = await service.client_manager.get_active_clients()
        client_ids = [client.client_id for client in clients]
        
        if not client_ids:
            logger.info("No active clients found for scheduled collection")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No active clients found',
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
        
        # Schedule batch collection
        message_ids = await service.schedule_batch_collection(
            client_ids=client_ids,
            frequency=frequency,
            priority=CollectionPriority.NORMAL
        )
        
        logger.info(f"Scheduled collection for {len(client_ids)} clients")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Scheduled collection for {len(client_ids)} clients',
                'frequency': frequency.value,
                'client_count': len(client_ids),
                'message_ids': message_ids,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    
    except Exception as e:
        logger.error(f"Error handling scheduled event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }


async def handle_api_request(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle API Gateway requests.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        await initialize_service()
        service = get_orchestration_service()
        
        method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        
        # Route API requests
        if method == 'POST' and path.endswith('/orchestrate'):
            return await handle_orchestrate_request(event, service)
        elif method == 'POST' and path.endswith('/schedule'):
            return await handle_schedule_request(event, service)
        elif method == 'GET' and '/status/' in path:
            return await handle_status_request(event, service)
        elif method == 'GET' and path.endswith('/health'):
            return await handle_health_request(event, service)
        elif method == 'GET' and path.endswith('/metrics'):
            return await handle_metrics_request(event, service)
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
    
    except Exception as e:
        logger.error(f"Error handling API request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


async def handle_orchestrate_request(
    event: Dict[str, Any], 
    service: OrchestrationIntegrationService
) -> Dict[str, Any]:
    """Handle direct orchestration request."""
    try:
        body = json.loads(event.get('body', '{}'))
        
        client_id = body.get('client_id')
        if not client_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'client_id is required'})
            }
        
        # Parse date range
        date_range_data = body.get('date_range', {})
        if date_range_data:
            start_date = datetime.fromisoformat(date_range_data['start_date']).date()
            end_date = datetime.fromisoformat(date_range_data['end_date']).date()
            date_range = DateRange(start_date=start_date, end_date=end_date)
        else:
            # Default to yesterday
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            date_range = DateRange(start_date=yesterday, end_date=yesterday)
        
        # Parse providers
        providers = None
        if body.get('providers'):
            providers = [CloudProvider(p) for p in body['providers']]
        
        # Parse priority
        priority = CollectionPriority.NORMAL
        if body.get('priority'):
            priority = CollectionPriority(body['priority'])
        
        # Execute orchestration
        result = await service.orchestrate_collection(
            client_id=client_id,
            date_range=date_range,
            providers=providers,
            priority=priority
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(result.to_dict())
        }
    
    except Exception as e:
        logger.error(f"Error in orchestrate request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


async def handle_schedule_request(
    event: Dict[str, Any], 
    service: OrchestrationIntegrationService
) -> Dict[str, Any]:
    """Handle schedule collection request."""
    try:
        body = json.loads(event.get('body', '{}'))
        
        client_id = body.get('client_id')
        frequency = body.get('frequency', 'daily')
        
        if not client_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'client_id is required'})
            }
        
        # Parse parameters
        schedule_frequency = ScheduleFrequency(frequency)
        providers = None
        if body.get('providers'):
            providers = [CloudProvider(p) for p in body['providers']]
        
        priority = None
        if body.get('priority'):
            priority = CollectionPriority(body['priority'])
        
        # Schedule collection
        message_id = await service.schedule_collection(
            client_id=client_id,
            frequency=schedule_frequency,
            providers=providers,
            priority=priority
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message_id': message_id,
                'client_id': client_id,
                'frequency': frequency,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    
    except Exception as e:
        logger.error(f"Error in schedule request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


async def handle_status_request(
    event: Dict[str, Any], 
    service: OrchestrationIntegrationService
) -> Dict[str, Any]:
    """Handle orchestration status request."""
    try:
        path = event.get('path', '')
        orchestration_id = path.split('/')[-1]
        
        status = service.get_orchestration_status(orchestration_id)
        
        if status is None:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Orchestration not found'})
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps(status)
        }
    
    except Exception as e:
        logger.error(f"Error in status request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


async def handle_health_request(
    event: Dict[str, Any], 
    service: OrchestrationIntegrationService
) -> Dict[str, Any]:
    """Handle health check request."""
    try:
        health_status = await service.health_check()
        
        status_code = 200
        if health_status.get('status') in ['unhealthy', 'error']:
            status_code = 503
        elif health_status.get('status') == 'degraded':
            status_code = 200  # Still functional
        
        return {
            'statusCode': status_code,
            'body': json.dumps(health_status)
        }
    
    except Exception as e:
        logger.error(f"Error in health request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


async def handle_metrics_request(
    event: Dict[str, Any], 
    service: OrchestrationIntegrationService
) -> Dict[str, Any]:
    """Handle metrics request."""
    try:
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Get queue metrics
        queue_metrics = service.get_queue_metrics()
        
        # Get service statistics
        service_stats = service.get_service_statistics()
        
        # Get performance analytics if requested
        analytics = None
        if query_params.get('analytics') == 'true':
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)  # Last 24 hours
            client_id = query_params.get('client_id')
            
            analytics = service.get_performance_analytics(
                start_time=start_time,
                end_time=end_time,
                client_id=client_id
            )
        
        response_data = {
            'queue_metrics': queue_metrics,
            'service_statistics': service_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if analytics:
            response_data['performance_analytics'] = analytics
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_data)
        }
    
    except Exception as e:
        logger.error(f"Error in metrics request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


async def handle_sqs_messages(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle SQS messages (queue processing).
    
    Args:
        event: SQS event with messages
        context: Lambda context
        
    Returns:
        Response dictionary
    """
    try:
        await initialize_service()
        service = get_orchestration_service()
        
        records = event.get('Records', [])
        logger.info(f"Processing {len(records)} SQS messages")
        
        results = []
        
        for record in records:
            try:
                # Parse message
                message_body = json.loads(record['body'])
                
                # Extract collection parameters
                client_id = message_body['client_id']
                providers = [CloudProvider(p) for p in message_body['providers']]
                date_range_data = message_body['date_range']
                date_range = DateRange(
                    start_date=datetime.fromisoformat(date_range_data['start_date']).date(),
                    end_date=datetime.fromisoformat(date_range_data['end_date']).date()
                )
                priority = CollectionPriority(message_body['priority'])
                
                # Execute collection
                result = await service.orchestrate_collection(
                    client_id=client_id,
                    date_range=date_range,
                    providers=providers,
                    priority=priority
                )
                
                results.append({
                    'messageId': record['messageId'],
                    'orchestrationId': result.orchestration_id,
                    'status': result.status.value,
                    'success': result.status.value in ['completed', 'partial']
                })
                
            except Exception as e:
                logger.error(f"Error processing SQS message {record.get('messageId')}: {str(e)}")
                results.append({
                    'messageId': record.get('messageId'),
                    'error': str(e),
                    'success': False
                })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed_messages': len(records),
                'results': results,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    
    except Exception as e:
        logger.error(f"Error handling SQS messages: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


async def handle_direct_invocation(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle direct Lambda invocation.
    
    Args:
        event: Direct invocation event
        context: Lambda context
        
    Returns:
        Response dictionary
    """
    try:
        await initialize_service()
        service = get_orchestration_service()
        
        action = event.get('action', 'health_check')
        
        if action == 'health_check':
            health_status = await service.health_check()
            return {
                'statusCode': 200,
                'body': json.dumps(health_status)
            }
        
        elif action == 'orchestrate':
            # Direct orchestration
            client_id = event.get('client_id')
            if not client_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'client_id is required'})
                }
            
            # Use default date range (yesterday)
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            date_range = DateRange(start_date=yesterday, end_date=yesterday)
            
            result = await service.orchestrate_collection(
                client_id=client_id,
                date_range=date_range
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps(result.to_dict())
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
    
    except Exception as e:
        logger.error(f"Error in direct invocation: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# Cleanup handler for graceful shutdown
async def cleanup_handler():
    """Cleanup handler for Lambda container shutdown."""
    global orchestration_service
    
    if orchestration_service:
        await orchestration_service.shutdown()
        orchestration_service = None


# Register cleanup handler
import atexit
atexit.register(lambda: asyncio.run(cleanup_handler()))