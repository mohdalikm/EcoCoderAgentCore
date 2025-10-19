#!/usr/bin/env python3
"""
Post-traffic deployment hook for EcoCoder Lambda function

This function performs final validation after traffic has been
shifted to the new Lambda deployment.
"""

import json
import boto3
import os
import logging
import time
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
codedeploy = boto3.client('codedeploy')
cloudwatch = boto3.client('cloudwatch')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Post-traffic hook handler
    """
    try:
        logger.info(f"Post-traffic hook event: {json.dumps(event, default=str)}")
        
        # Extract CodeDeploy lifecycle event details
        deployment_id = event.get('DeploymentId', '')
        lifecycle_event_hook_execution_id = event.get('LifecycleEventHookExecutionId', '')
        
        # Get the Lambda function name
        lambda_function_name = os.environ.get('NEW_VERSION_LAMBDA_FUNCTION_NAME', '')
        
        if not lambda_function_name:
            # Try to extract from the event context
            lambda_function_name = context.function_name.replace('-posttraffic-hook', '-ecocoder-core-entry')
        
        logger.info(f"Performing post-deployment validation for: {lambda_function_name}")
        
        # Wait a bit for metrics to propagate
        time.sleep(30)
        
        # Check CloudWatch metrics for the function
        try:
            # Get error rate metrics for the last 5 minutes
            end_time = time.time()
            start_time = end_time - 300  # 5 minutes ago
            
            # Get invocation count
            invocation_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': lambda_function_name
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            # Get error count
            error_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Errors',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': lambda_function_name
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            # Calculate error rate
            total_invocations = sum(point['Sum'] for point in invocation_response.get('Datapoints', []))
            total_errors = sum(point['Sum'] for point in error_response.get('Datapoints', []))
            
            error_rate = (total_errors / total_invocations * 100) if total_invocations > 0 else 0
            
            logger.info(f"Metrics - Invocations: {total_invocations}, Errors: {total_errors}, Error Rate: {error_rate}%")
            
            # Validate deployment based on error rate
            if error_rate > 20:  # More than 20% error rate is considered a failure
                validation_status = 'Failed'
                validation_message = f'High error rate detected: {error_rate}% (threshold: 20%)'
            elif total_invocations == 0:
                # If no invocations, consider it successful but with a warning
                validation_status = 'Succeeded'
                validation_message = 'No invocations detected during validation period'
            else:
                validation_status = 'Succeeded'
                validation_message = f'Deployment validation passed. Error rate: {error_rate}%'
                
        except Exception as metrics_error:
            logger.warning(f"Unable to retrieve metrics: {str(metrics_error)}")
            # Don't fail the deployment just because we can't get metrics
            validation_status = 'Succeeded'
            validation_message = f'Deployment completed (metrics unavailable: {str(metrics_error)})'
        
        # Additional health checks can be added here
        # For example: making HTTP requests to the API Gateway endpoint
        
        # Report the validation result to CodeDeploy
        try:
            codedeploy.put_lifecycle_event_hook_execution_status(
                deploymentId=deployment_id,
                lifecycleEventHookExecutionId=lifecycle_event_hook_execution_id,
                status=validation_status
            )
            
            logger.info(f"Reported final validation status to CodeDeploy: {validation_status}")
            
        except Exception as codedeploy_error:
            logger.error(f"Failed to report to CodeDeploy: {str(codedeploy_error)}")
            raise
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': validation_message,
                'status': validation_status,
                'metrics': {
                    'invocations': total_invocations if 'total_invocations' in locals() else 0,
                    'errors': total_errors if 'total_errors' in locals() else 0,
                    'error_rate': error_rate if 'error_rate' in locals() else 0
                }
            })
        }
        
    except Exception as e:
        logger.error(f"Post-traffic hook error: {str(e)}", exc_info=True)
        
        # Report failure to CodeDeploy if we have the required info
        if 'DeploymentId' in event and 'LifecycleEventHookExecutionId' in event:
            try:
                codedeploy.put_lifecycle_event_hook_execution_status(
                    deploymentId=event['DeploymentId'],
                    lifecycleEventHookExecutionId=event['LifecycleEventHookExecutionId'],
                    status='Failed'
                )
            except Exception as codedeploy_error:
                logger.error(f"Failed to report failure to CodeDeploy: {str(codedeploy_error)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Post-traffic validation failed',
                'message': str(e)
            })
        }