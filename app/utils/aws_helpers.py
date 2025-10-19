"""
AWS utilities for EcoCoderAgentCore agent.

This module provides common AWS service helpers used across the agent tools.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List, Union, Tuple
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class AWSError(Exception):
    """Custom exception for AWS-related errors."""
    pass


class AWSHelper:
    """Helper class for AWS service operations."""
    
    def __init__(self):
        """Initialize AWS helper with clients."""
        self.session = boto3.Session()
        self._clients = {}
        self._mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        
    def get_client(self, service_name: str, region_name: Optional[str] = None) -> Any:
        """
        Get or create AWS service client.
        
        Args:
            service_name: AWS service name (e.g., 'codeguru-reviewer')
            region_name: AWS region, defaults to session region
            
        Returns:
            boto3 client instance
            
        Raises:
            AWSError: If client creation fails
        """
        if self._mock_mode:
            return MockAWSClient(service_name)
            
        client_key = f"{service_name}:{region_name or 'default'}"
        
        if client_key not in self._clients:
            try:
                client_args = {'service_name': service_name}
                if region_name:
                    client_args['region_name'] = region_name
                    
                self._clients[client_key] = self.session.client(**client_args)
                logger.info(f"Created AWS client for {service_name} in {region_name or 'default region'}")
                
            except Exception as e:
                raise AWSError(f"Failed to create AWS client for {service_name}: {str(e)}")
                
        return self._clients[client_key]
    
    def get_parameter(self, name: str, decrypt: bool = False) -> Optional[str]:
        """
        Get parameter from AWS Systems Manager Parameter Store.
        
        Args:
            name: Parameter name
            decrypt: Whether to decrypt SecureString parameters
            
        Returns:
            Parameter value or None if not found
        """
        if self._mock_mode:
            mock_params = {
                '/ecocoder/carbon-intensity/us-east-1': '0.4',
                '/ecocoder/carbon-intensity/us-west-2': '0.3',
                '/ecocoder/carbon-intensity/eu-west-1': '0.25',
                '/ecocoder/config/profiling-duration': '300',
                '/ecocoder/config/reviewer-timeout': '3600'
            }
            return mock_params.get(name)
            
        try:
            ssm = self.get_client('ssm')
            response = ssm.get_parameter(Name=name, WithDecryption=decrypt)
            return response['Parameter']['Value']
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ParameterNotFound':
                logger.warning(f"Parameter {name} not found")
                return None
            else:
                logger.error(f"Error retrieving parameter {name}: {e}")
                raise AWSError(f"Failed to get parameter {name}: {str(e)}")
                
        except Exception as e:
            logger.error(f"Unexpected error getting parameter {name}: {e}")
            raise AWSError(f"Unexpected error: {str(e)}")
    
    def get_secret(self, secret_id: str, region_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get secret from AWS Secrets Manager.
        
        Args:
            secret_id: Secret identifier
            region_name: AWS region
            
        Returns:
            Secret value as dictionary
        """
        if self._mock_mode:
            return {
                'github_token': 'mock_github_pat_token',
                'webhook_secret': 'mock_webhook_secret'
            }
            
        try:
            secrets_client = self.get_client('secretsmanager', region_name)
            response = secrets_client.get_secret_value(SecretId=secret_id)
            
            if 'SecretString' in response:
                return json.loads(response['SecretString'])
            else:
                # Binary secret
                return {'binary_data': response['SecretBinary']}
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.error(f"Secret {secret_id} not found")
                raise AWSError(f"Secret {secret_id} not found")
            else:
                logger.error(f"Error retrieving secret {secret_id}: {e}")
                raise AWSError(f"Failed to get secret: {str(e)}")
                
        except Exception as e:
            logger.error(f"Unexpected error getting secret {secret_id}: {e}")
            raise AWSError(f"Unexpected error: {str(e)}")
    
    def wait_for_completion(self, 
                          client: Any, 
                          operation: str, 
                          identifier: str, 
                          max_attempts: int = 60, 
                          delay: int = 30) -> Dict[str, Any]:
        """
        Wait for AWS operation to complete with exponential backoff.
        
        Args:
            client: AWS service client
            operation: Operation name (e.g., 'describe_code_review')
            identifier: Resource identifier
            max_attempts: Maximum polling attempts
            delay: Initial delay between attempts
            
        Returns:
            Final operation response
            
        Raises:
            AWSError: If operation fails or times out
        """
        if self._mock_mode:
            # Simulate completion after short delay
            time.sleep(1)
            return {
                'State': 'Completed',
                'Status': 'Success',
                'MockData': True
            }
            
        attempt = 0
        current_delay = delay
        
        while attempt < max_attempts:
            try:
                if operation == 'describe_code_review':
                    response = client.describe_code_review(CodeReviewArn=identifier)
                    state = response['CodeReview']['State']
                    
                    if state == 'Completed':
                        return response
                    elif state in ['Failed', 'Cancelled']:
                        raise AWSError(f"Code review {identifier} {state.lower()}")
                        
                elif operation == 'get_profiling_group':
                    response = client.describe_profiling_group(profilingGroupName=identifier)
                    return response
                    
                else:
                    raise AWSError(f"Unknown operation: {operation}")
                
                attempt += 1
                logger.info(f"Waiting for {operation} completion, attempt {attempt}/{max_attempts}")
                time.sleep(current_delay)
                
                # Exponential backoff with jitter
                current_delay = min(current_delay * 1.5, 300)
                
            except ClientError as e:
                if attempt == max_attempts - 1:
                    raise AWSError(f"Operation {operation} failed: {str(e)}")
                else:
                    logger.warning(f"Transient error on attempt {attempt}: {e}")
                    time.sleep(current_delay)
                    attempt += 1
                    
        raise AWSError(f"Operation {operation} timed out after {max_attempts} attempts")
    
    def tag_resource(self, resource_arn: str, tags: Dict[str, str]) -> None:
        """
        Tag AWS resource for cost tracking and organization.
        
        Args:
            resource_arn: AWS resource ARN
            tags: Dictionary of tag key-value pairs
        """
        if self._mock_mode:
            logger.info(f"Mock: Would tag resource {resource_arn} with {tags}")
            return
            
        try:
            # Extract service from ARN to get appropriate client
            service = resource_arn.split(':')[2]
            client = self.get_client(service)
            
            tag_list = [{'Key': k, 'Value': v} for k, v in tags.items()]
            
            if service == 'codeguru-reviewer':
                client.tag_resource(resourceArn=resource_arn, Tags=tag_list)
            elif service == 'codeguru-profiler':
                client.tag_resource(resourceArn=resource_arn, tags=tags)
            else:
                logger.warning(f"Tagging not implemented for service: {service}")
                
        except Exception as e:
            logger.error(f"Failed to tag resource {resource_arn}: {e}")
            # Don't raise - tagging failure shouldn't break the workflow


class MockAWSClient:
    """Mock AWS client for development and testing."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        
    def __getattr__(self, name: str) -> Any:
        """Return mock response for any AWS API call."""
        def mock_call(*args, **kwargs):
            logger.info(f"Mock AWS call: {self.service_name}.{name}({args}, {kwargs})")
            
            # Return service-specific mock responses
            if self.service_name == 'codeguru-reviewer':
                if name == 'create_code_review':
                    return {'CodeReview': {'CodeReviewArn': 'mock-review-arn-123'}}
                elif name == 'describe_code_review':
                    return {
                        'CodeReview': {
                            'State': 'Completed',
                            'CodeReviewArn': 'mock-review-arn-123'
                        }
                    }
                elif name == 'list_recommendations':
                    return {
                        'RecommendationSummaries': [
                            {
                                'RecommendationId': 'mock-rec-1',
                                'Description': 'Consider using more efficient algorithm',
                                'Severity': 'High',
                                'RuleMetadata': {'RuleName': 'PerformanceOptimization'}
                            }
                        ]
                    }
                    
            elif self.service_name == 'codeguru-profiler':
                if name == 'create_profiling_group':
                    return {'profilingGroup': {'name': 'mock-profiling-group'}}
                elif name == 'describe_profiling_group':
                    return {
                        'profilingGroup': {
                            'name': 'mock-profiling-group',
                            'status': 'Active'
                        }
                    }
                elif name == 'get_profile':
                    return {
                        'profile': b'mock-profile-data',
                        'contentType': 'application/x-amzn-ion'
                    }
                    
            return {'MockResponse': True, 'Service': self.service_name}
            
        return mock_call


# Global instance for easy access
aws_helper = AWSHelper()