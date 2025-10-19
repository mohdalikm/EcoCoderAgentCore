#!/usr/bin/env python3
"""
Pre-traffic deployment hook for EcoCoder Lambda function

This function validates that the new Lambda deployment is ready
to receive traffic before CodeDeploy shifts traffic to it.
"""

import json
import boto3
import os
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
codedeploy = boto3.client('codedeploy')
lambda_client = boto3.client('lambda')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Pre-traffic hook handler
    """
    try:
        logger.info(f"Pre-traffic hook event: {json.dumps(event, default=str)}")
        
        # Extract CodeDeploy lifecycle event details
        deployment_id = event.get('DeploymentId', '')
        lifecycle_event_hook_execution_id = event.get('LifecycleEventHookExecutionId', '')
        
        # Get the new Lambda function version/alias from the event
        lambda_function_name = os.environ.get('NEW_VERSION_LAMBDA_FUNCTION_NAME', '')
        
        if not lambda_function_name:
            # Try to extract from the event context
            lambda_function_name = context.function_name.replace('-pretraffic-hook', '-ecocoder-core-entry')
        
        logger.info(f"Validating Lambda function: {lambda_function_name}")
        
        # Test the new Lambda function version
        try:
            # Create a test event for health check
            test_event = {
                'requestContext': {
                    'http': {'method': 'GET'}
                },
                'headers': {},
                'pathParameters': {'proxy': 'health'},
                'body': ''
            }
            
            # Invoke the Lambda function with the test event
            response = lambda_client.invoke(
                FunctionName=lambda_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_event)
            )
            
            # Check the response
            payload = json.loads(response['Payload'].read())
            status_code = payload.get('statusCode', 500)
            
            if status_code == 200:
                logger.info("Lambda function validation passed")
                validation_status = 'Succeeded'
                validation_message = 'Lambda function is responding correctly'
            else:
                logger.error(f"Lambda function validation failed with status: {status_code}")
                validation_status = 'Failed'
                validation_message = f'Lambda function returned status code: {status_code}'
                
        except Exception as lambda_error:
            logger.error(f"Lambda function validation error: {str(lambda_error)}")
            validation_status = 'Failed'
            validation_message = f'Lambda validation error: {str(lambda_error)}'
        
        # Report the validation result to CodeDeploy
        try:
            codedeploy.put_lifecycle_event_hook_execution_status(
                deploymentId=deployment_id,
                lifecycleEventHookExecutionId=lifecycle_event_hook_execution_id,
                status=validation_status
            )
            
            logger.info(f"Reported validation status to CodeDeploy: {validation_status}")
            
        except Exception as codedeploy_error:
            logger.error(f"Failed to report to CodeDeploy: {str(codedeploy_error)}")
            raise
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': validation_message,
                'status': validation_status
            })
        }
        
    except Exception as e:
        logger.error(f"Pre-traffic hook error: {str(e)}", exc_info=True)
        
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
                'error': 'Pre-traffic validation failed',
                'message': str(e)
            })
        }