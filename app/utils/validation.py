"""
Validation utilities for EcoCoderAgentCore agent.

This module provides parameter validation, data sanitization, and input checking.
"""

import os
import re
import json
import logging
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from datetime import datetime
from urllib.parse import urlparse
import hashlib

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class Validator:
    """Parameter validation and data sanitization utilities."""
    
    @staticmethod
    def validate_github_repo(repo: str) -> str:
        """
        Validate GitHub repository name format.
        
        Args:
            repo: Repository name in owner/repo format
            
        Returns:
            Validated repository name
            
        Raises:
            ValidationError: If format is invalid
        """
        if not repo or not isinstance(repo, str):
            raise ValidationError("Repository name must be a non-empty string")
            
        # GitHub repo format: owner/repo
        pattern = r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$'
        if not re.match(pattern, repo):
            raise ValidationError(
                f"Invalid repository format: {repo}. Expected: owner/repo"
            )
            
        parts = repo.split('/')
        if len(parts) != 2:
            raise ValidationError("Repository must be in owner/repo format")
            
        owner, repo_name = parts
        
        # Validate length constraints
        if len(owner) > 39:
            raise ValidationError(f"Owner name too long: {owner}")
        if len(repo_name) > 100:
            raise ValidationError(f"Repository name too long: {repo_name}")
            
        # Check for reserved names
        reserved = ['api', 'www', 'github', 'help', 'support']
        if owner.lower() in reserved or repo_name.lower() in reserved:
            raise ValidationError(f"Repository name contains reserved word")
            
        return repo
    
    @staticmethod
    def validate_pr_number(pr_number: Union[int, str]) -> int:
        """
        Validate pull request number.
        
        Args:
            pr_number: PR number as int or string
            
        Returns:
            Validated PR number as integer
        """
        try:
            pr_num = int(pr_number)
            if pr_num <= 0:
                raise ValidationError(f"PR number must be positive: {pr_num}")
            if pr_num > 999999:  # GitHub's practical limit
                raise ValidationError(f"PR number too large: {pr_num}")
            return pr_num
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid PR number: {pr_number}")
    
    @staticmethod
    def validate_sha(sha: str) -> str:
        """
        Validate Git SHA hash.
        
        Args:
            sha: Git commit SHA
            
        Returns:
            Validated SHA
        """
        if not sha or not isinstance(sha, str):
            raise ValidationError("SHA must be a non-empty string")
            
        # Git SHA is 40 character hex string
        if not re.match(r'^[a-fA-F0-9]{7,40}$', sha):
            raise ValidationError(f"Invalid SHA format: {sha}")
            
        return sha.lower()
    
    @staticmethod
    def validate_url(url: str, allowed_schemes: List[str] = None) -> str:
        """
        Validate and sanitize URL.
        
        Args:
            url: URL to validate
            allowed_schemes: List of allowed schemes (default: http, https)
            
        Returns:
            Validated URL
        """
        if not url or not isinstance(url, str):
            raise ValidationError("URL must be a non-empty string")
            
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
            
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme:
                raise ValidationError(f"URL missing scheme: {url}")
                
            if parsed.scheme not in allowed_schemes:
                raise ValidationError(
                    f"Invalid URL scheme: {parsed.scheme}. "
                    f"Allowed: {allowed_schemes}"
                )
                
            if not parsed.netloc:
                raise ValidationError(f"URL missing domain: {url}")
                
            return url
            
        except Exception as e:
            raise ValidationError(f"Invalid URL format: {url} - {str(e)}")
    
    @staticmethod
    def validate_file_path(file_path: str, 
                          max_length: int = 4096,
                          allow_relative: bool = True) -> str:
        """
        Validate file path format and security.
        
        Args:
            file_path: File path to validate
            max_length: Maximum path length
            allow_relative: Whether to allow relative paths
            
        Returns:
            Validated file path
        """
        if not file_path or not isinstance(file_path, str):
            raise ValidationError("File path must be a non-empty string")
            
        # Check length
        if len(file_path) > max_length:
            raise ValidationError(f"File path too long: {len(file_path)}")
            
        # Security checks
        dangerous_patterns = ['../', '..\\', '/etc/', '/proc/', '/dev/']
        for pattern in dangerous_patterns:
            if pattern in file_path:
                raise ValidationError(f"Dangerous path pattern: {pattern}")
                
        # Check for absolute paths if not allowed
        if not allow_relative and os.path.isabs(file_path):
            raise ValidationError("Absolute paths not allowed")
            
        # Validate characters (basic check)
        if re.search(r'[<>:"|?*\x00-\x1f]', file_path):
            raise ValidationError("File path contains invalid characters")
            
        return file_path
    
    @staticmethod
    def validate_json(data: Union[str, Dict], max_size: int = 1048576) -> Dict:
        """
        Validate and parse JSON data.
        
        Args:
            data: JSON string or dictionary
            max_size: Maximum JSON size in bytes
            
        Returns:
            Parsed JSON dictionary
        """
        if isinstance(data, dict):
            json_str = json.dumps(data)
        elif isinstance(data, str):
            json_str = data
        else:
            raise ValidationError(f"Invalid JSON type: {type(data)}")
            
        # Check size
        if len(json_str.encode('utf-8')) > max_size:
            raise ValidationError(f"JSON too large: {len(json_str)} bytes")
            
        try:
            if isinstance(data, str):
                return json.loads(data)
            else:
                return data
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {str(e)}")
    
    @staticmethod
    def validate_webhook_signature(payload: str, 
                                 signature: str, 
                                 secret: str) -> bool:
        """
        Validate GitHub webhook signature.
        
        Args:
            payload: Raw payload string
            signature: Signature from GitHub
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        if not all([payload, signature, secret]):
            raise ValidationError("Missing required signature components")
            
        if not signature.startswith('sha256='):
            raise ValidationError("Invalid signature format")
            
        try:
            import hmac
            expected = 'sha256=' + hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected)
            
        except Exception as e:
            raise ValidationError(f"Signature validation failed: {str(e)}")
    
    @staticmethod
    def sanitize_markdown(content: str, max_length: int = 65536) -> str:
        """
        Sanitize markdown content for GitHub comments.
        
        Args:
            content: Markdown content
            max_length: Maximum content length
            
        Returns:
            Sanitized markdown
        """
        if not isinstance(content, str):
            raise ValidationError("Content must be a string")
            
        # Truncate if too long
        if len(content) > max_length:
            content = content[:max_length - 100] + "\n\n... (truncated)"
            
        # Basic sanitization - remove dangerous HTML
        dangerous_tags = ['<script', '<iframe', '<object', '<embed', '<link']
        for tag in dangerous_tags:
            if tag.lower() in content.lower():
                logger.warning(f"Removed dangerous HTML tag: {tag}")
                content = re.sub(
                    rf'{re.escape(tag)}[^>]*>.*?</?\w+>', 
                    '[REMOVED]', 
                    content, 
                    flags=re.IGNORECASE | re.DOTALL
                )
                
        return content
    
    @staticmethod
    def validate_carbon_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate carbon footprint metrics.
        
        Args:
            metrics: Carbon metrics dictionary
            
        Returns:
            Validated metrics
        """
        required_fields = ['energy_kwh', 'carbon_kg', 'region']
        
        for field in required_fields:
            if field not in metrics:
                raise ValidationError(f"Missing required field: {field}")
                
        # Validate numeric fields
        numeric_fields = ['energy_kwh', 'carbon_kg']
        for field in numeric_fields:
            value = metrics[field]
            if not isinstance(value, (int, float)) or value < 0:
                raise ValidationError(f"Invalid {field}: must be non-negative number")
                
        # Validate region
        if not isinstance(metrics['region'], str) or not metrics['region']:
            raise ValidationError("Region must be a non-empty string")
            
        return metrics
    
    @staticmethod
    def validate_performance_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate performance profiling metrics.
        
        Args:
            metrics: Performance metrics dictionary
            
        Returns:
            Validated metrics
        """
        required_fields = ['cpu_utilization', 'memory_usage', 'execution_time']
        
        for field in required_fields:
            if field not in metrics:
                raise ValidationError(f"Missing required field: {field}")
                
        # Validate ranges
        cpu_util = metrics['cpu_utilization']
        if not isinstance(cpu_util, (int, float)) or not 0 <= cpu_util <= 100:
            raise ValidationError("CPU utilization must be 0-100")
            
        memory_usage = metrics['memory_usage']
        if not isinstance(memory_usage, (int, float)) or memory_usage < 0:
            raise ValidationError("Memory usage must be non-negative")
            
        exec_time = metrics['execution_time']
        if not isinstance(exec_time, (int, float)) or exec_time < 0:
            raise ValidationError("Execution time must be non-negative")
            
        return metrics


class ConfigValidator:
    """Configuration validation utilities."""
    
    @staticmethod
    def validate_agent_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate agent configuration.
        
        Args:
            config: Agent configuration dictionary
            
        Returns:
            Validated configuration
        """
        required_sections = ['aws', 'github', 'analysis']
        
        for section in required_sections:
            if section not in config:
                raise ValidationError(f"Missing configuration section: {section}")
                
        # Validate AWS config
        aws_config = config['aws']
        required_aws = ['region', 'codeguru_reviewer_timeout', 'profiler_duration']
        for field in required_aws:
            if field not in aws_config:
                raise ValidationError(f"Missing AWS config: {field}")
                
        # Validate GitHub config
        github_config = config['github']
        required_github = ['token_secret_name', 'webhook_secret_name']
        for field in required_github:
            if field not in github_config:
                raise ValidationError(f"Missing GitHub config: {field}")
                
        return config
    
    @staticmethod
    def validate_runtime_environment() -> Dict[str, str]:
        """
        Validate runtime environment variables.
        
        Returns:
            Dictionary of validated environment variables
        """
        required_env_vars = [
            'AWS_REGION',
            'GITHUB_TOKEN_SECRET_NAME',
            'WEBHOOK_SECRET_NAME'
        ]
        
        env_vars = {}
        missing_vars = []
        
        for var in required_env_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
            else:
                env_vars[var] = value
                
        if missing_vars:
            logger.warning(f"Missing environment variables: {missing_vars}")
            # In production, this might be an error
            # For development, we'll allow it with mock mode
            
        return env_vars


# Decorator for input validation
def validate_inputs(**validators: Callable) -> Callable:
    """
    Decorator for validating function inputs.
    
    Args:
        **validators: Keyword arguments mapping parameter names to validation functions
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Get function parameter names
            import inspect
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            # Create a dictionary of all arguments
            all_args = {}
            for i, arg in enumerate(args):
                if i < len(param_names):
                    all_args[param_names[i]] = arg
            all_args.update(kwargs)
            
            # Validate specified parameters
            for param_name, validator_func in validators.items():
                if param_name in all_args:
                    try:
                        validated_value = validator_func(all_args[param_name])
                        if param_name in kwargs:
                            kwargs[param_name] = validated_value
                        else:
                            # Update args tuple (more complex)
                            args_list = list(args)
                            param_index = param_names.index(param_name)
                            args_list[param_index] = validated_value
                            args = tuple(args_list)
                    except ValidationError as e:
                        raise ValidationError(f"Validation failed for {param_name}: {str(e)}")
                        
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Global validator instance
validator = Validator()
config_validator = ConfigValidator()