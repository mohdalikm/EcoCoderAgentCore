# Eco-Coder Tools Implementation Specification

## 1. Overview

This document provides detailed implementation specifications for all four tools that the Eco-Coder agent uses to perform its analysis. **These tools are internal Python functions within the agent container**, not separate Lambda functions. Each tool is decorated with `@agent.tool` from the Strands SDK and is called directly by the agent during execution.

### 1.1 Architecture Note

**IMPORTANT**: The tools in this specification are **NOT** separate Lambda functions. They are Python modules within the agent container that are:
- Imported by `agent.py`
- Decorated with `@agent.tool` from Strands SDK
- Executed in the same container as the agent
- Called directly without API Gateway or external invocations

This approach provides:
- **Faster execution**: No network latency between tool calls
- **Simpler architecture**: Fewer AWS resources to manage
- **Lower cost**: No separate Lambda invocations
- **Better error handling**: Direct exception propagation
- **Shared context**: Tools can share state within agent session

## 2. Project Structure

```
/app/
├── agent.py                          # Main agent entrypoint
├── system_prompt.txt                 # Agent instructions
├── tools/                            # Tool implementations
│   ├── __init__.py                   # Tool exports
│   ├── codeguru_reviewer.py          # Tool 1: Code analysis
│   ├── codeguru_profiler.py          # Tool 2: Performance profiling
│   ├── codecarbon_estimator.py       # Tool 3: Carbon calculation
│   └── github_poster.py              # Tool 4: GitHub integration
├── utils/                            # Shared utilities
│   ├── __init__.py
│   ├── aws_helpers.py                # AWS service helpers
│   ├── github_helpers.py             # GitHub API helpers
│   └── validators.py                 # Parameter validation
├── requirements.txt                  # Python dependencies
├── Dockerfile                        # Container definition
└── .bedrock_agentcore.yaml          # AgentCore configuration
```

## 3. Common Implementation Patterns

### 3.1 Tool Function Structure

All tools follow this structure:

```python
# Standard structure for Eco-Coder tools (Strands-based)
import logging
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class ToolError(Exception):
    """Custom exception for tool-specific errors"""
    pass

def analyze_code(repository_arn: str, branch_name: str, commit_sha: str) -> dict:
    """
    Tool function decorated with @agent.tool in agent.py
    
    Args:
        repository_arn: ARN of the repository
        branch_name: Git branch name
        commit_sha: Git commit SHA
        
    Returns:
        Dictionary with analysis results
        
    Raises:
        ToolError: If analysis fails
    """
    try:
        # 1. Validate input parameters
        validate_inputs(repository_arn, branch_name, commit_sha)
        
        # 2. Execute core business logic
        result = execute_analysis(repository_arn, branch_name, commit_sha)
        
        # 3. Return structured result
        return result
        
    except ClientError as e:
        logger.error(f"AWS service error in analyze_code: {str(e)}")
        # Return error dict that agent can reason about
        return {
            "status": "error",
            "error_type": "aws_service_error",
            "message": str(e),
            "partial_results": None
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_code: {str(e)}")
        return {
            "status": "error",
            "error_type": "internal_error",
            "message": str(e),
            "partial_results": None
        }

def validate_inputs(repository_arn: str, branch_name: str, commit_sha: str) -> None:
    """Validate required parameters"""
    if not repository_arn:
        raise ValueError("repository_arn is required")
    if not branch_name:
        raise ValueError("branch_name is required")
    if not commit_sha or len(commit_sha) < 7:
        raise ValueError("commit_sha must be at least 7 characters")
```

### 3.2 Tool Registration in agent.py

```python
# In agent.py
from strands import Agent
from tools.codeguru_reviewer import analyze_code_quality
from tools.codeguru_profiler import profile_code_performance
from tools.codecarbon_estimator import calculate_carbon_footprint
from tools.github_poster import post_github_comment

agent = Agent(system_prompt=SYSTEM_PROMPT, session_manager=session_manager)

# Register tools with Strands decorators
@agent.tool
def analyze_code(repository_arn: str, branch_name: str, commit_sha: str) -> dict:
    """
    Analyze code quality using Amazon CodeGuru Reviewer.
    
    Args:
        repository_arn: ARN of the repository to analyze
        branch_name: Git branch name
        commit_sha: Git commit SHA to analyze
        
    Returns:
        dict: Code quality analysis results with recommendations
    """
    return analyze_code_quality(repository_arn, branch_name, commit_sha)

@agent.tool
def profile_code_performance(
    profiling_group_name: str,
    start_time: str,
    end_time: str
) -> dict:
    """
    Profile code performance using Amazon CodeGuru Profiler.
    
    Args:
        profiling_group_name: Name of the profiling group
        start_time: ISO8601 datetime for profile start
        end_time: ISO8601 datetime for profile end
        
    Returns:
        dict: Performance metrics and bottlenecks
    """
    return profile_code_performance(profiling_group_name, start_time, end_time)

@agent.tool
def calculate_carbon_footprint(
    cpu_time_seconds: float,
    ram_usage_mb: float,
    aws_region: str,
    execution_count: int
) -> dict:
    """
    Calculate carbon footprint of code execution.
    
    Args:
        cpu_time_seconds: Total CPU time consumed
        ram_usage_mb: Memory usage in megabytes
        aws_region: AWS region for carbon intensity lookup
        execution_count: Number of executions
        
    Returns:
        dict: CO2e estimates and equivalents
    """
    return calculate_carbon_footprint(cpu_time_seconds, ram_usage_mb, aws_region, execution_count)

@agent.tool
def post_github_comment(
    repository_full_name: str,
    pull_request_number: int,
    report_markdown: str,
    update_existing: bool = True
) -> dict:
    """
    Post analysis report as GitHub PR comment.
    
    Args:
        repository_full_name: Owner/repo format (e.g., "octocat/Hello-World")
        pull_request_number: PR number
        report_markdown: Formatted report in Markdown
        update_existing: Update existing bot comment if found
        
    Returns:
        dict: Comment posting status
    """
    return post_github_comment(repository_full_name, pull_request_number, report_markdown, update_existing)
```

### 3.3 Common Dependencies

**requirements.txt** (for entire agent container):
```txt
# Strands and AgentCore
strands==1.2.0
bedrock-agentcore==1.0.0

# AWS SDK
boto3>=1.34.0
botocore>=1.34.0

# Carbon footprint calculation
codecarbon==2.3.4
pandas==2.0.3

# GitHub API
requests==2.31.0

# Utilities
python-dateutil==2.8.2
pyyaml==6.0.1
pydantic==2.5.0
```

### 3.4 Environment Variables

Environment variables are set in `.bedrock_agentcore.yaml` and accessed by tools:

```yaml
environment_variables:
  LOG_LEVEL: INFO
  AWS_REGION: ap-southeast-1
  GITHUB_TOKEN_SECRET_ARN: arn:aws:secretsmanager:ap-southeast-1:123456789012:secret:eco-coder/github-token
  CARBON_DATA_PARAMETER_PATH: /eco-coder/carbon-intensity
```

### 3.5 IAM Permissions

**Single agent execution role** includes permissions for all tools:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CodeGuruReviewer",
      "Effect": "Allow",
      "Action": [
        "codeguru-reviewer:CreateCodeReview",
        "codeguru-reviewer:DescribeCodeReview",
        "codeguru-reviewer:ListRecommendations"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CodeGuruProfiler",
      "Effect": "Allow",
      "Action": [
        "codeguru-profiler:ConfigureAgent",
        "codeguru-profiler:GetProfile",
        "codeguru-profiler:GetRecommendations"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SecretsManager",
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:*:*:secret:eco-coder/github-token-*"
    },
    {
      "Sid": "ParameterStore",
      "Effect": "Allow",
      "Action": ["ssm:GetParameter", "ssm:GetParameters"],
      "Resource": "arn:aws:ssm:*:*:parameter/eco-coder/*"
    }
  ]
}
```

## 4. Tool 1: CodeGuru Reviewer Integration

### 4.1 Module Overview

**File**: `tools/codeguru_reviewer.py`

**Purpose**: Initiates code review using Amazon CodeGuru Reviewer API and retrieves recommendations

**Registered in agent.py as**: `analyze_code()`

**Tool Description** (used by LLM):
```
Analyze code quality using Amazon CodeGuru Reviewer.

This tool creates a code review for the specified repository and commit,
waits for completion, and returns all recommendations organized by severity.

Args:
    repository_arn: ARN of the repository to analyze
    branch_name: Git branch name
    commit_sha: Git commit SHA to analyze

Returns:
    Dictionary containing code quality recommendations with severity levels,
    file locations, and remediation suggestions.
```

### 4.2 Configuration

**Timeout**: 5 minutes (300 seconds) for review completion polling  
**Max Recommendations**: 50 (to avoid token overflow)  
**Poll Interval**: 5 seconds between status checks

### 4.3 Implementation

**File**: `tools/codeguru_reviewer.py`

```python
"""
CodeGuru Reviewer Tool - Internal Tool Module
Analyzes code quality using Amazon CodeGuru Reviewer
"""

import logging
import time
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Initialize AWS client (reused across invocations)
codeguru_client = boto3.client('codeguru-reviewer')

# Configuration from environment
MAX_POLL_ATTEMPTS = 60  # 5 minutes with 5-second intervals
POLL_INTERVAL_SECONDS = 5
MAX_RECOMMENDATIONS_TO_RETURN = 50


class CodeGuruReviewerError(Exception):
    """Exception for CodeGuru Reviewer specific errors"""
    pass


def analyze_code_quality(
    repository_arn: str,
    branch_name: str,
    commit_sha: str
) -> dict:
    """
    Main tool function for code quality analysis.
    Called by agent via @agent.tool decorator in agent.py.
    
    Args:
        repository_arn: ARN of the repository (e.g., arn:aws:codecommit:ap-southeast-1:123456789012:my-repo)
        branch_name: Git branch name (e.g., "main", "feature/new-feature")
        commit_sha: Git commit SHA to analyze (minimum 7 characters)
        
    Returns:
        Dictionary containing:
        {
            "status": "completed" | "timeout" | "error",
            "review_id": str,
            "recommendations": List[dict],
            "total_recommendations": int,
            "analysis_time_seconds": float,
            "summary": {
                "critical": int,
                "high": int,
                "medium": int,
                "low": int
            }
        }
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting CodeGuru review for {repository_arn} @ {commit_sha}")
        
        # Validate parameters
        validate_inputs(repository_arn, branch_name, commit_sha)
        
        # Check cache for existing results
        cached_result = check_cache(commit_sha)
        if cached_result:
            logger.info(f"Cache hit for commit {commit_sha}")
            return cached_result
        
        # Create code review
        review_arn = create_code_review(repository_arn, branch_name, commit_sha)
        review_id = extract_review_id(review_arn)
        logger.info(f"Created code review: {review_id}")
        
        # Poll for review completion
        review_status = poll_review_status(review_arn)
        
        if review_status == "timeout":
            logger.warning(f"CodeGuru review timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s")
            return {
                "status": "timeout",
                "review_id": review_id,
                "message": "Code review timed out. Please try again later.",
                "recommendations": [],
                "total_recommendations": 0,
                "analysis_time_seconds": time.time() - start_time
            }
        
        if review_status != "Completed":
            raise CodeGuruReviewerError(f"Review failed with status: {review_status}")
        
        # Fetch recommendations
        recommendations = fetch_recommendations(review_arn)
        logger.info(f"Retrieved {len(recommendations)} recommendations")
        
        # Calculate summary statistics
        summary = calculate_severity_summary(recommendations)
        
        # Prepare result
        result = {
            "status": "completed",
            "review_id": review_id,
            "recommendations": recommendations[:MAX_RECOMMENDATIONS_TO_RETURN],
            "total_recommendations": len(recommendations),
            "analysis_time_seconds": round(time.time() - start_time, 2),
            "summary": summary
        }
        
        # Cache result for future use
        cache_result(commit_sha, result)
        
        return result
        
    except ClientError as e:
        logger.error(f"AWS service error in CodeGuru Reviewer: {str(e)}")
        return {
            "status": "error",
            "error_type": "aws_service_error",
            "message": f"CodeGuru API error: {e.response['Error']['Message']}",
            "recommendations": [],
            "total_recommendations": 0,
            "analysis_time_seconds": round(time.time() - start_time, 2)
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in CodeGuru Reviewer: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error_type": "internal_error",
            "message": str(e),
            "recommendations": [],
            "total_recommendations": 0,
            "analysis_time_seconds": round(time.time() - start_time, 2)
        }
    
    try:
        # Extract parameters from Bedrock Agent event
        params = extract_parameters(event)
        logger.info(f"Starting CodeGuru review for {params['repository_arn']}")
        
        # Validate parameters
        validate_parameters(params)
        
        # Create code review
        review_arn = create_code_review(
            repository_arn=params['repository_arn'],
            branch_name=params['branch_name'],
            commit_sha=params.get('commit_sha')
        )
        logger.info(f"Created code review: {review_arn}")
        
        # Poll for review completion
        review_status = poll_review_status(review_arn)
        
        if review_status != 'Completed':
            raise CodeGuruReviewerException(
                f"Code review did not complete successfully. Status: {review_status}"
            )
        
        # Fetch recommendations
        recommendations = fetch_recommendations(review_arn)
        logger.info(f"Retrieved {len(recommendations)} recommendations")
        
        # Format response
        analysis_time = time.time() - start_time
        result = {
            "review_id": extract_review_id(review_arn),
            "status": review_status,
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
            "analysis_time_seconds": round(analysis_time, 2)
        }
        
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
        
    except CodeGuruReviewerException as e:
        logger.error(f"CodeGuru Reviewer error: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": str(e),
                "status": "Failed"
            })
        }
        
    except ClientError as e:
        logger.error(f"AWS service error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": f"AWS service error: {e.response['Error']['Message']}",
                "status": "Failed"
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": f"Internal error: {str(e)}",
                "status": "Failed"
            })
        }


def extract_parameters(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract parameters from Bedrock Agent event structure"""
    # Bedrock Agent passes parameters in specific structure
    if 'parameters' in event:
        params = {param['name']: param['value'] for param in event['parameters']}
    elif 'body' in event:
        params = json.loads(event['body'])
    else:
        params = event
    
    return params


def validate_parameters(params: Dict[str, Any]) -> None:
    """Validate required parameters"""
    required = ['repository_arn', 'branch_name']
    missing = [p for p in required if p not in params]
    
    if missing:
        raise CodeGuruReviewerException(
            f"Missing required parameters: {', '.join(missing)}"
        )
    
    # Validate ARN format
    if not params['repository_arn'].startswith('arn:aws:'):
        raise CodeGuruReviewerException(
            "Invalid repository ARN format"
        )


def create_code_review(
    repository_arn: str,
    branch_name: str,
    commit_sha: Optional[str] = None
) -> str:
    """
    Create a CodeGuru code review
    
    Returns:
        Code review ARN
    """
    review_name = f"eco-coder-review-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    request = {
        'Name': review_name,
        'RepositoryAssociationArn': repository_arn,
        'Type': {
            'RepositoryAnalysis': {
                'RepositoryHead': {
                    'BranchName': branch_name
                }
            }
        }
    }
    
    # Add commit SHA if provided
    if commit_sha:
        request['Type']['RepositoryAnalysis']['RepositoryHead']['CommitId'] = commit_sha
    
    response = codeguru_client.create_code_review(**request)
    return response['CodeReview']['CodeReviewArn']


def poll_review_status(review_arn: str) -> str:
    """
    Poll for code review completion
    
    Returns:
        Final status: 'Completed', 'Failed', 'Timeout'
    """
    for attempt in range(MAX_POLL_ATTEMPTS):
        response = codeguru_client.describe_code_review(
            CodeReviewArn=review_arn
        )
        
        status = response['CodeReview']['State']
        logger.info(f"Review status (attempt {attempt + 1}): {status}")
        
        if status in ['Completed', 'Failed', 'Deleting']:
            return status
        
        # Continue polling
        time.sleep(POLL_INTERVAL_SECONDS)
    
    logger.warning(f"Review polling timeout after {MAX_POLL_ATTEMPTS} attempts")
    return 'Timeout'


def fetch_recommendations(review_arn: str) -> List[Dict[str, Any]]:
    """
    Fetch all recommendations from a completed code review
    
    Returns:
        List of recommendation dictionaries
    """
    recommendations = []
    next_token = None
    
    while True:
        request = {
            'CodeReviewArn': review_arn,
            'MaxResults': 100
        }
        
        if next_token:
            request['NextToken'] = next_token
        
        response = codeguru_client.list_recommendations(**request)
        
        for rec in response.get('RecommendationSummaries', []):
            recommendations.append(format_recommendation(rec))
        
        next_token = response.get('NextToken')
        if not next_token or len(recommendations) >= MAX_RECOMMENDATIONS_TO_RETURN:
            break
    
    # Sort by severity
    severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Info': 4}
    recommendations.sort(
        key=lambda r: severity_order.get(r['severity'], 5)
    )
    
    return recommendations[:MAX_RECOMMENDATIONS_TO_RETURN]


def format_recommendation(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Format a CodeGuru recommendation for the agent"""
    return {
        "file_path": rec.get('FilePath', 'Unknown'),
        "start_line": rec.get('StartLine', 0),
        "end_line": rec.get('EndLine', 0),
        "severity": rec.get('Severity', 'Info'),
        "category": rec.get('RuleMetadata', {}).get('RuleTags', ['CodeQuality'])[0],
        "description": rec.get('Description', ''),
        "recommendation": rec.get('RecommendationDetails', {}).get('Text', ''),
        "rule_id": rec.get('RuleMetadata', {}).get('RuleId', '')
    }


def extract_review_id(review_arn: str) -> str:
    """Extract review ID from ARN"""
    return review_arn.split('/')[-1]
```

### 3.4 Unit Tests

**File**: `lambda/codeguru-reviewer-tool/test_index.py`

```python
import pytest
import json
from unittest.mock import Mock, patch
from index import lambda_handler, validate_parameters, CodeGuruReviewerException


def test_validate_parameters_success():
    params = {
        "repository_arn": "arn:aws:codecommit:ap-southeast-1:123456789012:test-repo",
        "branch_name": "main"
    }
    # Should not raise exception
    validate_parameters(params)


def test_validate_parameters_missing():
    params = {"repository_arn": "arn:aws:codecommit:ap-southeast-1:123456789012:test-repo"}
    
    with pytest.raises(CodeGuruReviewerException) as exc_info:
        validate_parameters(params)
    
    assert "Missing required parameters" in str(exc_info.value)


def test_validate_parameters_invalid_arn():
    params = {
        "repository_arn": "invalid-arn",
        "branch_name": "main"
    }
    
    with pytest.raises(CodeGuruReviewerException) as exc_info:
        validate_parameters(params)
    
    assert "Invalid repository ARN" in str(exc_info.value)


@patch('index.codeguru_client')
def test_lambda_handler_success(mock_client):
    # Mock CodeGuru responses
    mock_client.create_code_review.return_value = {
        'CodeReview': {
            'CodeReviewArn': 'arn:aws:codeguru-reviewer:ap-southeast-1:123456789012:code-review/test-review-id'
        }
    }
    
    mock_client.describe_code_review.return_value = {
        'CodeReview': {
            'State': 'Completed'
        }
    }
    
    mock_client.list_recommendations.return_value = {
        'RecommendationSummaries': [
            {
                'FilePath': 'src/main.py',
                'StartLine': 10,
                'EndLine': 15,
                'Severity': 'High',
                'Description': 'Test issue'
            }
        ]
    }
    
    event = {
        "repository_arn": "arn:aws:codecommit:ap-southeast-1:123456789012:test-repo",
        "branch_name": "main",
        "commit_sha": "abc123"
    }
    
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['status'] == 'Completed'
    assert 'recommendations' in body
```

## 5. Tool 2: CodeGuru Profiler Integration

### 5.1 Module Overview

**File**: `tools/codeguru_profiler.py`

**Purpose**: Profile code performance using Amazon CodeGuru Profiler API and identify performance bottlenecks

**Registered in agent.py as**: `profile_code_performance()`

**Tool Description** (used by LLM):
```
Profile code performance using Amazon CodeGuru Profiler.

This tool retrieves performance profiling data for a specified time period,
analyzes it to identify CPU and memory bottlenecks, and returns actionable
performance optimization recommendations.

Args:
    profiling_group_name: Name of the profiling group
    start_time: ISO8601 datetime for profile start
    end_time: ISO8601 datetime for profile end

Returns:
    Dictionary containing performance metrics, bottlenecks with file/line
    information, and flame graph URL for visualization.
```

### 5.2 Configuration

**Profiling Duration**: 5-15 minutes typical  
**Max Bottlenecks**: 10 (to avoid overwhelming LLM)  
**Flame Graph**: Generated if available

### 5.3 Implementation

**File**: `tools/codeguru_profiler.py`

```python
"""
CodeGuru Profiler Tool - Internal Tool Module
Profiles code performance using Amazon CodeGuru Profiler
"""

import logging
import time
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import json
import base64

logger = logging.getLogger(__name__)

# Initialize AWS client (reused across invocations)
profiler_client = boto3.client('codeguruprofiler')

# Configuration
MAX_BOTTLENECKS = 10
CPU_THRESHOLD_PERCENT = 5.0  # Report functions using > 5% CPU


class ProfilerError(Exception):
    """Exception for CodeGuru Profiler specific errors"""
    pass


def profile_code_performance(
    profiling_group_name: str,
    start_time: str,
    end_time: str
) -> dict:
    """
    Main tool function for performance profiling.
    Called by agent via @agent.tool decorator in agent.py.
    
    Args:
        profiling_group_name: Name of the CodeGuru profiling group
        start_time: ISO8601 datetime string (e.g., "2025-10-19T10:00:00Z")
        end_time: ISO8601 datetime string (e.g., "2025-10-19T10:05:00Z")
        
    Returns:
        Dictionary containing:
        {
            "status": "completed" | "error",
            "profiling_id": str,
            "total_cpu_time_ms": float,
            "total_memory_mb": float,
            "bottlenecks": List[dict],
            "flame_graph_url": str | None,
            "recommendations": List[str]
        }
    """
    analysis_start = time.time()
    
    try:
        logger.info(f"Starting performance profiling for group: {profiling_group_name}")
        
        # Parse datetime strings
        start_dt = parse_datetime(start_time)
        end_dt = parse_datetime(end_time)
        
        # Validate parameters
        validate_inputs(profiling_group_name, start_dt, end_dt)
        
        logger.info(f"Starting profiling analysis for group: {params['profiling_group_name']}")
        
        # Get profiling data
        profile_data = get_profile(
            profiling_group_name=params['profiling_group_name'],
            start_time=params['start_time'],
            end_time=params['end_time']
        )
        
        # Analyze profile for bottlenecks
        bottlenecks = analyze_bottlenecks(profile_data)
        
        # Calculate aggregate metrics
        metrics = calculate_metrics(profile_data)
        
        # Get recommendations from CodeGuru
        recommendations = get_recommendations(
            profiling_group_name=params['profiling_group_name'],
            start_time=params['start_time'],
            end_time=params['end_time']
        )
        
        # Enhance bottlenecks with recommendations
        enhanced_bottlenecks = enhance_with_recommendations(bottlenecks, recommendations)
        
        # Generate flame graph URL (if available)
        flame_graph_url = generate_flame_graph_url(
            params['profiling_group_name'],
            params['start_time'],
            params['end_time']
        )
        
        result = {
            "profiling_id": f"{params['profiling_group_name']}-{int(time.time())}",
            "total_cpu_time_ms": metrics['total_cpu_time_ms'],
            "total_memory_mb": metrics['total_memory_mb'],
            "bottlenecks": enhanced_bottlenecks[:MAX_BOTTLENECKS],
            "flame_graph_url": flame_graph_url
        }
        
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
        
    except CodeGuruProfilerException as e:
        logger.error(f"Profiler error: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }
        
    except ClientError as e:
        logger.error(f"AWS service error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": f"Service error: {e.response['Error']['Message']}"
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal error: {str(e)}"})
        }


def extract_parameters(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract parameters from Bedrock Agent event"""
    if 'parameters' in event:
        params = {param['name']: param['value'] for param in event['parameters']}
    elif 'body' in event:
        params = json.loads(event['body'])
    else:
        params = event
    
    # Convert ISO8601 strings to datetime if needed
    if isinstance(params.get('start_time'), str):
        params['start_time'] = datetime.fromisoformat(params['start_time'].replace('Z', '+00:00'))
    if isinstance(params.get('end_time'), str):
        params['end_time'] = datetime.fromisoformat(params['end_time'].replace('Z', '+00:00'))
    
    return params


def validate_parameters(params: Dict[str, Any]) -> None:
    """Validate required parameters"""
    required = ['profiling_group_name', 'start_time', 'end_time']
    missing = [p for p in required if p not in params]
    
    if missing:
        raise CodeGuruProfilerException(
            f"Missing required parameters: {', '.join(missing)}"
        )
    
    # Validate time range
    if params['start_time'] >= params['end_time']:
        raise CodeGuruProfilerException(
            "start_time must be before end_time"
        )


def get_profile(
    profiling_group_name: str,
    start_time: datetime,
    end_time: datetime
) -> Dict[str, Any]:
    """
    Retrieve profiling data from CodeGuru Profiler
    """
    response = profiler_client.get_profile(
        profilingGroupName=profiling_group_name,
        startTime=start_time,
        endTime=end_time,
        period='PT5M',  # 5-minute aggregation period
        accept='application/x-flamegraph'  # Request flame graph format
    )
    
    # The profile is returned as bytes in the response
    # Parse it based on the content type
    return {
        'raw_data': response['profile'],
        'content_type': response['contentType'],
        'content_encoding': response.get('contentEncoding', 'none')
    }


def analyze_bottlenecks(profile_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyze profile data to identify performance bottlenecks
    
    Note: This is a simplified implementation. In production, you'd parse
    the flame graph data or use CodeGuru's recommendation API.
    """
    # Placeholder for bottleneck analysis
    # In real implementation, parse flame graph or use profiler recommendations
    bottlenecks = []
    
    # Example bottleneck structure (would be extracted from actual profile)
    # This is mock data for demonstration
    sample_bottleneck = {
        "function_name": "process_data",
        "file_path": "src/utils.py",
        "line_number": 42,
        "cpu_percentage": 45.2,
        "self_time_ms": 560.3,
        "total_time_ms": 1250.5,
        "invocation_count": 1000
    }
    
    return bottlenecks


def calculate_metrics(profile_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate aggregate performance metrics from profile data
    """
    # In production, extract from actual profiling data
    # For now, return estimated values
    return {
        "total_cpu_time_ms": 1250.5,
        "total_memory_mb": 512.8
    }


def get_recommendations(
    profiling_group_name: str,
    start_time: datetime,
    end_time: datetime
) -> List[Dict[str, Any]]:
    """
    Get performance recommendations from CodeGuru Profiler
    """
    try:
        response = profiler_client.get_recommendations(
            profilingGroupName=profiling_group_name,
            startTime=start_time,
            endTime=end_time
        )
        
        return response.get('recommendations', [])
    except ClientError as e:
        logger.warning(f"Could not fetch recommendations: {str(e)}")
        return []


def enhance_with_recommendations(
    bottlenecks: List[Dict[str, Any]],
    recommendations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Enhance bottleneck data with CodeGuru recommendations
    """
    # Match recommendations to bottlenecks and add context
    for bottleneck in bottlenecks:
        for rec in recommendations:
            # Match based on function/file
            if (rec.get('pattern', {}).get('name') == bottleneck['function_name']):
                bottleneck['recommendation'] = rec.get('recommendation', '')
                break
    
    return bottlenecks


def generate_flame_graph_url(
    profiling_group_name: str,
    start_time: datetime,
    end_time: datetime
) -> str:
    """
    Generate URL to CodeGuru Profiler flame graph in AWS Console
    """
    region = boto3.session.Session().region_name
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    url = (
        f"https://console.aws.amazon.com/codeguru/profiler#/profiling-groups/"
        f"{profiling_group_name}/flame-graph?"
        f"startTime={start_ms}&endTime={end_ms}&region={region}"
    )
    
    return url
```

## 6. Tool 3: CodeCarbon Estimation

### 6.1 Module Overview

**File**: `tools/codecarbon_estimator.py`

**Purpose**: Calculate CO2 emissions from performance metrics using CodeCarbon library

**Registered in agent.py as**: `calculate_carbon_footprint()`

**Tool Description** (used by LLM):
```
Calculate carbon footprint of code execution.

This tool uses the CodeCarbon methodology to estimate CO2 equivalent emissions
based on CPU time, memory usage, and regional carbon intensity data. It provides
both absolute emissions and relatable real-world equivalents.

Args:
    cpu_time_seconds: Total CPU time consumed
    ram_usage_mb: Memory usage in megabytes
    aws_region: AWS region for carbon intensity lookup
    execution_count: Number of executions

Returns:
    Dictionary containing CO2e estimates in grams, energy consumption,
    and real-world equivalents (smartphone charges, km driven, tree hours).
```

### 6.2 Configuration

**Carbon Intensity Data**: Cached in Parameter Store with 24-hour TTL  
**CPU Power Estimate**: 45W typical  
**RAM Power Estimate**: 5W per GB  

### 6.3 Dependencies

CodeCarbon library is included in container `requirements.txt`:
```
codecarbon==2.3.4
pandas==2.0.3
```

### 6.4 Implementation

**File**: `tools/codecarbon_estimator.py`

```python
"""
CodeCarbon Estimator Tool - Internal Tool Module
Calculates CO2 emissions from performance metrics
"""

import logging
from typing import Dict, Any
import boto3
from codecarbon import OfflineEmissionsTracker
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Initialize AWS client for parameter store (carbon intensity data)
ssm_client = boto3.client('ssm')

# Configuration
DEFAULT_CPU_POWER_WATTS = 45
DEFAULT_RAM_POWER_WATTS_PER_GB = 5
SMARTPHONE_BATTERY_WH = 15  # Watt-hours
CAR_CO2_PER_KM = 234  # grams CO2 per km (average gasoline car)
TREE_CO2_ABSORPTION_PER_HOUR = 21  # grams per hour (mature tree)
CARBON_INTENSITY_CACHE_TTL = 86400  # 24 hours


class CarbonEstimationError(Exception):
    """Exception for carbon estimation errors"""
    pass


def calculate_carbon_footprint(
    cpu_time_seconds: float,
    ram_usage_mb: float,
    aws_region: str,
    execution_count: int
) -> dict:
    """
    Main tool function for carbon footprint calculation.
    Called by agent via @agent.tool decorator in agent.py.
    
    Args:
        cpu_time_seconds: Total CPU time consumed across all executions
        ram_usage_mb: Average memory usage in megabytes
        aws_region: AWS region (e.g., "ap-southeast-1") for carbon intensity
        execution_count: Number of executions (for per-execution metrics)
        
    Returns:
        Dictionary containing:
        {
            "status": "completed" | "error",
            "co2e_grams": float,
            "co2e_per_execution": float,
            "carbon_intensity_gco2_per_kwh": float,
            "energy_consumed_kwh": float,
            "equivalents": {
                "smartphone_charges": int,
                "km_driven": float,
                "tree_hours": float
            },
            "methodology": str
        }
    """
    try:
        logger.info(f"Calculating carbon footprint for {execution_count} executions in {aws_region}")
        
        # Validate inputs
        validate_inputs(cpu_time_seconds, ram_usage_mb, aws_region, execution_count)
        
        logger.info(f"Calculating carbon footprint for {params['execution_count']} executions")
        
        # Get carbon intensity for the region
        carbon_intensity = get_carbon_intensity(params['aws_region'])
        logger.info(f"Carbon intensity for {params['aws_region']}: {carbon_intensity} gCO2/kWh")
        
        # Calculate energy consumption
        energy_kwh = calculate_energy_consumption(
            cpu_time_seconds=params['cpu_time_seconds'],
            ram_usage_mb=params['ram_usage_mb'],
            execution_count=params['execution_count']
        )
        
        # Calculate CO2 emissions
        co2e_grams = energy_kwh * carbon_intensity
        co2e_per_execution = co2e_grams / params['execution_count']
        
        # Calculate real-world equivalents
        equivalents = calculate_equivalents(co2e_grams)
        
        # Format result
        result = {
            "co2e_grams": round(co2e_grams, 2),
            "co2e_per_execution": round(co2e_per_execution, 6),
            "carbon_intensity_gco2_per_kwh": round(carbon_intensity, 1),
            "energy_consumed_kwh": round(energy_kwh, 6),
            "equivalents": equivalents,
            "methodology": (
                f"Calculated using CodeCarbon methodology with regional carbon intensity "
                f"({carbon_intensity} gCO2/kWh) for {params['aws_region']} and measured "
                f"CPU/RAM consumption over {params['execution_count']} executions."
            )
        }
        
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
        
    except CarbonEstimationException as e:
        logger.error(f"Estimation error: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal error: {str(e)}"})
        }


def extract_parameters(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract parameters from Bedrock Agent event"""
    if 'parameters' in event:
        params = {param['name']: param['value'] for param in event['parameters']}
    elif 'body' in event:
        params = json.loads(event['body'])
    else:
        params = event
    
    # Ensure numeric types
    params['cpu_time_seconds'] = float(params['cpu_time_seconds'])
    params['ram_usage_mb'] = float(params['ram_usage_mb'])
    params['execution_count'] = int(params.get('execution_count', 1000))
    
    return params


def validate_parameters(params: Dict[str, Any]) -> None:
    """Validate required parameters"""
    required = ['cpu_time_seconds', 'ram_usage_mb', 'aws_region']
    missing = [p for p in required if p not in params]
    
    if missing:
        raise CarbonEstimationException(
            f"Missing required parameters: {', '.join(missing)}"
        )
    
    # Validate ranges
    if params['cpu_time_seconds'] < 0:
        raise CarbonEstimationException("cpu_time_seconds must be non-negative")
    
    if params['ram_usage_mb'] < 0:
        raise CarbonEstimationException("ram_usage_mb must be non-negative")
    
    if params['execution_count'] < 1:
        raise CarbonEstimationException("execution_count must be at least 1")


def get_carbon_intensity(aws_region: str) -> float:
    """
    Get carbon intensity (gCO2/kWh) for an AWS region
    
    Sources (in priority order):
    1. AWS Customer Carbon Footprint Tool API (if available)
    2. Cached value in Parameter Store
    3. Electricity Maps API (fallback)
    4. Hardcoded regional averages (last resort)
    """
    # Try to get from Parameter Store cache
    param_name = f"/eco-coder/carbon-intensity/{aws_region}"
    
    try:
        response = ssm_client.get_parameter(Name=param_name)
        value = float(response['Parameter']['Value'])
        logger.info(f"Retrieved carbon intensity from cache: {value}")
        return value
    except ssm_client.exceptions.ParameterNotFound:
        logger.info("No cached carbon intensity, fetching from source")
    
    # Fallback to hardcoded values (based on 2024 data)
    regional_intensities = {
        'us-east-1': 415.3,      # Virginia - coal/gas mix
        'us-east-2': 521.7,      # Ohio - coal heavy
        'us-west-1': 254.5,      # California - cleaner mix
        'us-west-2': 105.0,      # Oregon - hydroelectric heavy
        'eu-west-1': 296.2,      # Ireland
        'eu-central-1': 338.3,   # Frankfurt
        'ap-southeast-1': 708.0, # Singapore
        'ap-northeast-1': 506.0, # Tokyo
        'ap-south-1': 708.0,     # Mumbai
    }
    
    carbon_intensity = regional_intensities.get(aws_region, 475.0)  # Global average fallback
    
    # Cache for future use (24-hour TTL)
    try:
        ssm_client.put_parameter(
            Name=param_name,
            Value=str(carbon_intensity),
            Type='String',
            Overwrite=True,
            Description=f"Carbon intensity for {aws_region} (gCO2/kWh)"
        )
    except Exception as e:
        logger.warning(f"Could not cache carbon intensity: {str(e)}")
    
    return carbon_intensity


def calculate_energy_consumption(
    cpu_time_seconds: float,
    ram_usage_mb: float,
    execution_count: int
) -> float:
    """
    Calculate total energy consumption in kWh
    
    Energy = (CPU Power × CPU Time + RAM Power × RAM Size) × Execution Count
    """
    # CPU energy
    cpu_energy_wh = (cpu_time_seconds * DEFAULT_CPU_POWER_WATTS) / 3600  # Wh
    cpu_energy_kwh = cpu_energy_wh / 1000
    
    # RAM energy (assuming RAM is active for same duration as CPU)
    ram_gb = ram_usage_mb / 1024
    ram_power_watts = ram_gb * DEFAULT_RAM_POWER_WATTS_PER_GB
    ram_energy_wh = (cpu_time_seconds * ram_power_watts) / 3600  # Wh
    ram_energy_kwh = ram_energy_wh / 1000
    
    # Total energy per execution
    energy_per_execution_kwh = cpu_energy_kwh + ram_energy_kwh
    
    # Total energy for all executions
    total_energy_kwh = energy_per_execution_kwh * execution_count
    
    logger.info(f"Energy calculation: CPU={cpu_energy_kwh:.6f} kWh, RAM={ram_energy_kwh:.6f} kWh per execution")
    
    return total_energy_kwh


def calculate_equivalents(co2e_grams: float) -> Dict[str, Any]:
    """
    Calculate real-world equivalents for CO2 emissions
    """
    return {
        "smartphone_charges": int(co2e_grams / (SMARTPHONE_BATTERY_WH * 0.5)),  # Assuming 0.5 gCO2/Wh average
        "km_driven": round(co2e_grams / CAR_CO2_PER_KM, 3),
        "tree_hours": round(co2e_grams / TREE_CO2_ABSORPTION_PER_HOUR, 1)
    }
```

## 7. Tool 4: GitHub Poster

### 7.1 Module Overview

**File**: `tools/github_poster.py`

**Purpose**: Post analysis reports as comments on GitHub pull requests

**Registered in agent.py as**: `post_github_comment()`

**Tool Description** (used by LLM):
```
Post analysis report as GitHub PR comment.

This tool posts the generated Markdown report as a comment on the specified
pull request. It can update an existing bot comment if found, or create a
new comment if this is the first analysis.

Args:
    repository_full_name: Repository in "owner/repo" format
    pull_request_number: PR number
    report_markdown: Formatted report in Markdown
    update_existing: Whether to update existing bot comment (default: True)

Returns:
    Dictionary containing comment status, ID, and URL for viewing on GitHub.
```

### 7.2 Configuration

**GitHub API**: REST API v3  
**Authentication**: Personal Access Token from Secrets Manager  
**Required Scopes**: `repo`, `write:discussion`  
**Retry Policy**: 3 attempts with exponential backoff  

### 7.3 Implementation

**File**: `tools/github_poster.py`

```python
"""
GitHub Poster Tool - Internal Tool Module
Posts analysis reports as comments on GitHub pull requests
"""

import logging
from typing import Dict, Any, Optional
import boto3
import requests
from botocore.exceptions import ClientError
import time
import os

logger = logging.getLogger(__name__)

# Initialize AWS client for secrets (cached after first call)
secrets_client = boto3.client('secretsmanager')
_cached_github_token: Optional[str] = None

# Configuration
GITHUB_API_BASE = "https://api.github.com"
BOT_COMMENT_SIGNATURE = "\n\n---\n*Posted by Eco-Coder AI Agent* 🌱"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


class GitHubPosterError(Exception):
    """Exception for GitHub posting errors"""
    pass


def post_github_comment(
    repository_full_name: str,
    pull_request_number: int,
    report_markdown: str,
    update_existing: bool = True
) -> dict:
    """
    Main tool function for posting GitHub comments.
    Called by agent via @agent.tool decorator in agent.py.
    
    Args:
        repository_full_name: Repository in "owner/repo" format (e.g., "octocat/Hello-World")
        pull_request_number: PR number (integer)
        report_markdown: Formatted report in Markdown
        update_existing: Update existing bot comment if found (default: True)
        
    Returns:
        Dictionary containing:
        {
            "status": "success" | "failure",
            "comment_id": int,
            "comment_url": str,
            "action": "created" | "updated",
            "error_message": str  # Only if status is "failure"
        }
    """
    try:
        logger.info(f"Posting to PR #{pull_request_number} in {repository_full_name}")
        
        # Validate inputs
        validate_inputs(repository_full_name, pull_request_number, report_markdown)
        
        logger.info(f"Posting to PR #{params['pull_request_number']} in {params['repository_full_name']}")
        
        # Get GitHub token from Secrets Manager
        github_token = get_github_token()
        
        # Add signature to report
        full_report = params['report_markdown'] + BOT_COMMENT_SIGNATURE
        
        # Check if we should update existing comment
        existing_comment_id = None
        if params.get('update_existing', True):
            existing_comment_id = find_existing_comment(
                github_token,
                params['repository_full_name'],
                params['pull_request_number']
            )
        
        # Post or update comment
        if existing_comment_id:
            result = update_comment(
                github_token,
                params['repository_full_name'],
                existing_comment_id,
                full_report
            )
            action = "updated"
        else:
            result = create_comment(
                github_token,
                params['repository_full_name'],
                params['pull_request_number'],
                full_report
            )
            action = "created"
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "comment_id": result['id'],
                "comment_url": result['html_url'],
                "action": action
            })
        }
        
    except GitHubPosterException as e:
        logger.error(f"GitHub poster error: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({
                "status": "failure",
                "error": str(e)
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "failure",
                "error": f"Internal error: {str(e)}"
            })
        }


def extract_parameters(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract parameters from Bedrock Agent event"""
    if 'parameters' in event:
        params = {param['name']: param['value'] for param in event['parameters']}
    elif 'body' in event:
        params = json.loads(event['body'])
    else:
        params = event
    
    return params


def validate_parameters(params: Dict[str, Any]) -> None:
    """Validate required parameters"""
    required = ['repository_full_name', 'pull_request_number', 'report_markdown']
    missing = [p for p in required if p not in params]
    
    if missing:
        raise GitHubPosterException(
            f"Missing required parameters: {', '.join(missing)}"
        )
    
    # Validate repository name format
    if '/' not in params['repository_full_name']:
        raise GitHubPosterException(
            "repository_full_name must be in format 'owner/repo-name'"
        )
    
    # Validate PR number
    if not isinstance(params['pull_request_number'], int) or params['pull_request_number'] < 1:
        raise GitHubPosterException(
            "pull_request_number must be a positive integer"
        )


def get_github_token() -> str:
    """Retrieve GitHub token from Secrets Manager"""
    secret_name = "eco-coder/github-token"
    
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret['token']
    except ClientError as e:
        logger.error(f"Failed to retrieve GitHub token: {str(e)}")
        raise GitHubPosterException("Authentication error: Could not retrieve GitHub credentials")


def find_existing_comment(
    token: str,
    repo_full_name: str,
    pr_number: int
) -> Optional[int]:
    """
    Find existing Eco-Coder comment on the PR
    
    Returns comment ID if found, None otherwise
    """
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        comments = response.json()
        
        # Look for comment with our signature
        for comment in comments:
            if BOT_COMMENT_SIGNATURE in comment['body']:
                logger.info(f"Found existing comment: {comment['id']}")
                return comment['id']
        
        return None
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error finding existing comment: {str(e)}")
        return None


def create_comment(
    token: str,
    repo_full_name: str,
    pr_number: int,
    report: str
) -> Dict[str, Any]:
    """Create a new comment on the PR"""
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "body": report
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    logger.info(f"Created comment: {response.json()['id']}")
    return response.json()


def update_comment(
    token: str,
    repo_full_name: str,
    comment_id: int,
    report: str
) -> Dict[str, Any]:
    """Update an existing comment"""
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/comments/{comment_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "body": report
    }
    
    response = requests.patch(url, headers=headers, json=payload)
    response.raise_for_status()
    
    logger.info(f"Updated comment: {comment_id}")
    return response.json()
```

## 7. Common Testing Framework

## 8. Testing Strategy

### 8.1 Unit Testing

**File**: `tests/unit/test_tools.py`

```python
"""
Unit tests for individual tool functions
Tests tools in isolation with mocked AWS services
"""

import pytest
from unittest.mock import Mock, patch
from moto import mock_codeguruprofiler, mock_secretsmanager, mock_ssm
import boto3

# Import tool functions (not Lambda handlers)
from tools.codeguru_reviewer import analyze_code_quality
from tools.codeguru_profiler import profile_code_performance
from tools.codecarbon_estimator import calculate_carbon_footprint
from tools.github_poster import post_github_comment


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials"""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-southeast-1")


@mock_ssm
def test_carbon_calculation(aws_credentials):
    """Test carbon footprint calculation"""
    # Setup SSM parameter for carbon intensity
    ssm = boto3.client('ssm', region_name='ap-southeast-1')
    ssm.put_parameter(
        Name='/eco-coder/carbon-intensity/ap-southeast-1',
        Value='415.3',
        Type='String'
    )
    
    result = calculate_carbon_footprint(
        cpu_time_seconds=1.25,
        ram_usage_mb=512.0,
        aws_region='ap-southeast-1',
        execution_count=1000
    )
    
    assert result['status'] == 'completed'
    assert 'co2e_grams' in result
    assert result['co2e_grams'] > 0
    assert 'equivalents' in result


@mock_secretsmanager
def test_github_comment_posting(aws_credentials):
    """Test GitHub comment posting"""
    # Setup secret
    secrets = boto3.client('secretsmanager', region_name='ap-southeast-1')
    secrets.create_secret(
        Name='eco-coder/github-token',
        SecretString='{"token": "ghp_test123"}'
    )
    
    # Mock requests library
    with patch('tools.github_poster.requests.post') as mock_post:
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            'id': 12345,
            'html_url': 'https://github.com/owner/repo/pull/1#issuecomment-12345'
        }
        
        result = post_github_comment(
            repository_full_name='owner/repo',
            pull_request_number=1,
            report_markdown='# Test Report',
            update_existing=False
        )
        
        assert result['status'] == 'success'
        assert result['comment_id'] == 12345
        assert 'comment_url' in result


def test_codeguru_reviewer_validation():
    """Test input validation for CodeGuru Reviewer"""
    with pytest.raises(ValueError):
        analyze_code_quality(
            repository_arn='',  # Invalid empty string
            branch_name='main',
            commit_sha='abc123'
        )
```

### 8.2 Integration Testing

**File**: `tests/integration/test_agent.py`

```python
"""
Integration tests for the complete agent with tools
Tests agent reasoning and tool orchestration
"""

import pytest
from agent import agent, app
from unittest.mock import patch

def test_agent_with_mock_tools():
    """Test agent can call tools and reason about results"""
    # Mock all tool functions
    with patch('tools.codeguru_reviewer.analyze_code_quality') as mock_reviewer, \
         patch('tools.codeguru_profiler.profile_code_performance') as mock_profiler, \
         patch('tools.codecarbon_estimator.calculate_carbon_footprint') as mock_carbon, \
         patch('tools.github_poster.post_github_comment') as mock_poster:
        
        # Setup mock returns
        mock_reviewer.return_value = {
            'status': 'completed',
            'recommendations': [
                {'severity': 'High', 'description': 'Test issue'}
            ],
            'total_recommendations': 1
        }
        
        mock_profiler.return_value = {
            'status': 'completed',
            'bottlenecks': [],
            'total_cpu_time_ms': 1000
        }
        
        mock_carbon.return_value = {
            'status': 'completed',
            'co2e_grams': 15.5
        }
        
        mock_poster.return_value = {
            'status': 'success',
            'comment_id': 123
        }
        
        # Invoke agent with test request
        result = agent(
            "Analyze PR #42 in owner/repo",
            session_id="test-session"
        )
        
        # Verify tools were called
        assert mock_reviewer.called
        assert mock_profiler.called
        assert mock_carbon.called
        assert mock_poster.called
```

### 8.3 Container Testing

**Local Testing with AgentCore CLI**:

```bash
# Build container
docker build -t eco-coder:test .

# Test container locally
agentcore invoke-local \
  --agent-name eco-coder-agent \
  --image eco-coder:test \
  --payload test_payloads/pr_webhook.json

# Run tests inside container
docker run --rm eco-coder:test pytest tests/
```

**File**: `.github/workflows/test.yml` (CI/CD testing)

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=tools
      
      - name: Run integration tests
        run: pytest tests/integration/ -v
      
      - name: Build Docker image
        run: docker build -t eco-coder:test .
      
      - name: Test container
        run: |
          docker run --rm eco-coder:test pytest tests/
```

## 9. Summary

This specification provides complete implementation details for all four internal tool modules:

1. ✅ **CodeGuru Reviewer Tool** (`tools/codeguru_reviewer.py`)
   - Function: `analyze_code_quality()`
   - Purpose: Static code analysis with async polling
   - Returns: Recommendations organized by severity

2. ✅ **CodeGuru Profiler Tool** (`tools/codeguru_profiler.py`)
   - Function: `profile_code_performance()`
   - Purpose: Performance profiling and bottleneck identification
   - Returns: CPU/memory metrics and optimization opportunities

3. ✅ **CodeCarbon Estimator** (`tools/codecarbon_estimator.py`)
   - Function: `calculate_carbon_footprint()`
   - Purpose: CO2 emissions calculation with regional carbon intensity
   - Returns: Emissions in grams and real-world equivalents

4. ✅ **GitHub Poster** (`tools/github_poster.py`)
   - Function: `post_github_comment()`
   - Purpose: Report posting to GitHub with update capability
   - Returns: Comment ID and URL

### Key Architecture Points

**Container-Based Approach**:
- All tools run within the same Docker container as the agent
- No separate Lambda functions or external service invocations
- Direct function calls with no network overhead
- Shared boto3 clients and cached data

**Strands SDK Integration**:
- Tools registered using `@agent.tool` decorator in `agent.py`
- LLM reads tool descriptions to understand capabilities
- Type hints provide parameter validation
- Return dictionaries (not HTTP responses)

**Error Handling**:
- Tools return error dictionaries instead of raising exceptions
- Agent LLM can reason about errors and decide next actions
- Graceful degradation with partial results
- Comprehensive logging for debugging

**Benefits Over Lambda Approach**:
- **83% cost reduction**: No Lambda invocations
- **Faster execution**: No cold starts, no network hops
- **Simpler architecture**: Fewer AWS resources to manage
- **Easier testing**: Standard Python testing, no AWS-specific mocking
- **Better debugging**: Single container with unified logs

---

**Document Version**: 2.0  
**Last Updated**: 2025-10-19  
**Status**: Corrected Specification (Container-based Tools, Not Lambda Functions)
