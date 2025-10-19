#!/usr/bin/env python3
"""
GitHub Webhook to Bedrock AgentCore Runtime Bridge
Lambda Function with Function URL for hackathon deployment

This Lambda function receives GitHub webhook events and forwards them
to the deployed EcoCoder agent in Bedrock AgentCore Runtime.
"""

import json
import boto3
import uuid
import hmac
import hashlib
import os
import logging
import time
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration from environment variables
AGENT_ARN = os.environ.get('AGENT_ARN', 'arn:aws:bedrock-agentcore:ap-southeast-1:434114167546:runtime/ecocoderagentcore-H0kpdY5A85')
GITHUB_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', '')  # Optional for hackathon
REGION = os.environ.get('ECOCODER_REGION', os.environ.get('AWS_REGION', 'ap-southeast-1'))

# Initialize AWS clients
bedrock_agentcore = boto3.client('bedrock-agentcore', region_name=REGION)


def verify_github_signature(payload_body: str, signature_header: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature (optional for hackathon)
    """
    if not secret or not signature_header:
        return True  # Skip verification if no secret configured
    
    if not signature_header.startswith('sha256='):
        return False
    
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload_body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    signature = signature_header[7:]  # Remove 'sha256=' prefix
    return hmac.compare_digest(expected_signature, signature)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function handler for GitHub webhook to AgentCore integration
    """
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Extract request details
        http_method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
        headers = event.get('headers', {})
        body = event.get('body', '')
        path = event.get('path', event.get('pathParameters', {}).get('proxy', ''))
        
        # Handle health check requests
        if path == '/health' or path == 'health':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'healthy',
                    'service': 'ecocoder-core-entry',
                    'version': '1.0.0',
                    'timestamp': int(time.time()),
                    'agent_arn': AGENT_ARN,
                    'region': REGION
                })
            }
        
        # Handle preflight OPTIONS requests (CORS)
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, X-GitHub-Event, X-Hub-Signature-256'
                },
                'body': ''
            }
        
        # Only accept POST requests
        if http_method != 'POST':
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed. Use POST.'})
            }
        
        # Check if it's a GitHub webhook
        github_event = headers.get('x-github-event', headers.get('X-GitHub-Event', ''))
        if not github_event:
            logger.warning("No GitHub event header found")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Not a GitHub webhook'})
            }
        
        # Parse the GitHub payload
        try:
            if event.get('isBase64Encoded', False):
                import base64
                body = base64.b64decode(body).decode('utf-8')
            
            github_payload = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON payload: {e}")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid JSON payload'})
            }
        
        # Optional: Verify GitHub signature (recommended for production)
        if GITHUB_SECRET:
            signature = headers.get('x-hub-signature-256', headers.get('X-Hub-Signature-256', ''))
            if not verify_github_signature(body, signature, GITHUB_SECRET):
                logger.error("GitHub signature verification failed")
                return {
                    'statusCode': 401,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Invalid signature'})
                }
        
        logger.info(f"Processing GitHub {github_event} event")
        
        # Filter for relevant events (pull request events)
        if github_event == 'pull_request':
            action = github_payload.get('action', '')
            
            # Only process relevant PR actions
            if action in ['opened', 'synchronize', 'reopened']:
                logger.info(f"Processing pull_request {action} event")
                
                # Extract basic PR info for logging
                pr_number = github_payload.get('pull_request', {}).get('number', 'unknown')
                repo_name = github_payload.get('repository', {}).get('full_name', 'unknown')
                
                try:
                    # Generate unique session ID for this webhook
                    session_id = f"webhook-{repo_name}-{pr_number}-{uuid.uuid4().hex[:8]}"
                    
                    # Prepare payload for AgentCore Runtime
                    agentcore_payload = json.dumps(github_payload).encode('utf-8')
                    
                    logger.info(f"Invoking AgentCore Runtime for PR #{pr_number} in {repo_name}")
                    
                    # Invoke the AgentCore Runtime
                    response = bedrock_agentcore.invoke_agent_runtime(
                        agentRuntimeArn=AGENT_ARN,
                        runtimeSessionId=session_id,
                        payload=agentcore_payload,
                        qualifier='DEFAULT'
                    )
                    
                    # Process the streaming response
                    response_content = []
                    for chunk in response.get('response', []):
                        if isinstance(chunk, bytes):
                            response_content.append(chunk.decode('utf-8'))
                        else:
                            response_content.append(str(chunk))
                    
                    agent_response = ''.join(response_content)
                    logger.info(f"AgentCore Runtime response: {agent_response[:200]}...")
                    
                    # Return success response to GitHub
                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'message': f'EcoCoder analysis initiated for PR #{pr_number}',
                            'session_id': session_id,
                            'repository': repo_name,
                            'status': 'success'
                        })
                    }
                    
                except Exception as agentcore_error:
                    logger.error(f"AgentCore Runtime invocation failed: {str(agentcore_error)}")
                    
                    # Return error but don't fail the webhook
                    return {
                        'statusCode': 200,  # Still return 200 to GitHub
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'message': f'EcoCoder analysis failed for PR #{pr_number}',
                            'error': str(agentcore_error),
                            'status': 'error'
                        })
                    }
            else:
                logger.info(f"Ignoring pull_request {action} event")
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'message': f'Ignored pull_request {action} event'})
                }
        
        else:
            logger.info(f"Ignoring {github_event} event")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'message': f'Ignored {github_event} event'})
            }
    
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


# For local testing
if __name__ == "__main__":
    # Test with a sample GitHub webhook payload
    test_event = {
        'requestContext': {
            'http': {'method': 'POST'}
        },
        'headers': {
            'X-GitHub-Event': 'pull_request',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            "action": "opened",
            "pull_request": {
                "number": 123,
                "title": "Test: Add webhook integration",
                "head": {"ref": "feature/webhook", "sha": "abc123def"},
                "base": {"ref": "main"}
            },
            "repository": {
                "full_name": "test/webhook-repo",
                "clone_url": "https://github.com/test/webhook-repo.git",
                "owner": {"id": "12345"}
            }
        })
    }
    
    print("Testing Lambda function locally...")
    result = lambda_handler(test_event, None)
    print(f"Result: {json.dumps(result, indent=2)}")