"""
CodeGuru Reviewer Tool - Internal Tool Module
Analyzes code quality using Amazon CodeGuru Reviewer

This tool provides code quality analysis by integrating with Amazon CodeGuru Reviewer API
to identify performance issues, security vulnerabilities, and adherence to best practices.
"""

import logging
import time
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import os
import json

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
MAX_POLL_ATTEMPTS = 60  # 5 minutes with 5-second intervals
POLL_INTERVAL_SECONDS = 5
MAX_RECOMMENDATIONS_TO_RETURN = 50
CACHE_TTL_HOURS = 24


class CodeGuruReviewerError(Exception):
    """Exception for CodeGuru Reviewer specific errors"""
    pass


def validate_inputs(repository_arn: str, branch_name: str, commit_sha: str) -> None:
    """
    Validate input parameters for CodeGuru Reviewer analysis
    
    Args:
        repository_arn: ARN of the repository to analyze
        branch_name: Git branch name
        commit_sha: Git commit SHA to analyze
        
    Raises:
        ValueError: If any required parameter is invalid
    """
    if not repository_arn or not repository_arn.startswith('arn:aws:'):
        raise ValueError("repository_arn must be a valid AWS ARN")
    
    if not branch_name or len(branch_name.strip()) == 0:
        raise ValueError("branch_name is required")
    
    if not commit_sha or len(commit_sha) < 7:
        raise ValueError("commit_sha must be at least 7 characters")


def check_cache(commit_sha: str) -> Optional[Dict]:
    """
    Check if analysis results are cached for this commit SHA
    
    Args:
        commit_sha: Git commit SHA
        
    Returns:
        Cached results if found and still valid, None otherwise
    """
    try:
        # In production, this would check Parameter Store or DynamoDB
        # For now, return None (no caching in development)
        return None
    except Exception as e:
        logger.warning(f"Cache check failed: {e}")
        return None


def cache_result(commit_sha: str, result: Dict) -> None:
    """
    Cache analysis results for future use
    
    Args:
        commit_sha: Git commit SHA
        result: Analysis results to cache
    """
    try:
        # In production, this would store in Parameter Store or DynamoDB
        logger.info(f"Would cache result for commit {commit_sha} (development mode)")
    except Exception as e:
        logger.warning(f"Failed to cache result: {e}")


def create_code_review(repository_arn: str, branch_name: str, commit_sha: str) -> str:
    """
    Create a CodeGuru code review
    
    Args:
        repository_arn: ARN of the repository
        branch_name: Git branch name
        commit_sha: Git commit SHA
        
    Returns:
        Code review ARN
        
    Raises:
        CodeGuruReviewerError: If review creation fails
    """
    try:
        # Initialize CodeGuru Reviewer client
        codeguru_client = boto3.client('codeguru-reviewer')
        
        # Create unique review name
        review_name = f"eco-coder-review-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{commit_sha[:8]}"
        
        # Prepare review request
        request = {
            'Name': review_name,
            'RepositoryAssociationArn': repository_arn,
            'Type': {
                'RepositoryAnalysis': {
                    'RepositoryHead': {
                        'BranchName': branch_name,
                        'CommitId': commit_sha
                    }
                }
            },
            'ClientRequestToken': f"eco-coder-{int(time.time())}"
        }
        
        logger.info(f"Creating CodeGuru review for {repository_arn} @ {commit_sha}")
        response = codeguru_client.create_code_review(**request)
        
        review_arn = response['CodeReview']['CodeReviewArn']
        logger.info(f"Created CodeGuru review: {review_arn}")
        
        return review_arn
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'ResourceNotFoundException':
            raise CodeGuruReviewerError(f"Repository association not found: {repository_arn}")
        elif error_code == 'ConflictException':
            raise CodeGuruReviewerError(f"Code review already in progress for this commit")
        elif error_code == 'ThrottlingException':
            raise CodeGuruReviewerError(f"Request throttled by CodeGuru Reviewer")
        else:
            raise CodeGuruReviewerError(f"Failed to create code review: {error_message}")


def poll_review_status(review_arn: str) -> str:
    """
    Poll for code review completion
    
    Args:
        review_arn: ARN of the code review
        
    Returns:
        Final status: 'Completed', 'Failed', or 'timeout'
    """
    codeguru_client = boto3.client('codeguru-reviewer')
    
    for attempt in range(MAX_POLL_ATTEMPTS):
        try:
            response = codeguru_client.describe_code_review(
                CodeReviewArn=review_arn
            )
            
            status = response['CodeReview']['State']
            logger.info(f"Review status (attempt {attempt + 1}/{MAX_POLL_ATTEMPTS}): {status}")
            
            if status in ['Completed', 'Failed', 'Deleting']:
                return status
            
            # Continue polling for pending/in-progress states
            if status in ['Pending', 'InProgress']:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue
            else:
                logger.warning(f"Unknown review state: {status}")
                return status
                
        except ClientError as e:
            logger.error(f"Error polling review status: {e}")
            if attempt == MAX_POLL_ATTEMPTS - 1:
                return 'Failed'
            time.sleep(POLL_INTERVAL_SECONDS)
    
    logger.warning(f"Review polling timeout after {MAX_POLL_ATTEMPTS} attempts")
    return 'timeout'


def fetch_recommendations(review_arn: str) -> List[Dict[str, Any]]:
    """
    Fetch all recommendations from a completed code review
    
    Args:
        review_arn: ARN of the completed code review
        
    Returns:
        List of recommendation dictionaries
    """
    codeguru_client = boto3.client('codeguru-reviewer')
    recommendations = []
    next_token = None
    
    try:
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
        
        # Sort by severity (Critical -> High -> Medium -> Low -> Info)
        severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Info': 4}
        recommendations.sort(
            key=lambda r: (severity_order.get(r['severity'], 5), r['file_path'])
        )
        
        return recommendations[:MAX_RECOMMENDATIONS_TO_RETURN]
        
    except ClientError as e:
        logger.error(f"Error fetching recommendations: {e}")
        return []


def format_recommendation(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a CodeGuru recommendation for agent consumption
    
    Args:
        rec: Raw recommendation from CodeGuru API
        
    Returns:
        Formatted recommendation dictionary
    """
    return {
        "file_path": rec.get('FilePath', 'Unknown'),
        "start_line": rec.get('StartLine', 0),
        "end_line": rec.get('EndLine', 0),
        "severity": rec.get('Severity', 'Info'),
        "category": extract_category(rec),
        "description": rec.get('Description', ''),
        "recommendation": extract_recommendation_text(rec),
        "rule_id": rec.get('RuleMetadata', {}).get('RuleId', ''),
        "rule_name": rec.get('RuleMetadata', {}).get('RuleName', ''),
        "tags": rec.get('RuleMetadata', {}).get('RuleTags', [])
    }


def extract_category(rec: Dict[str, Any]) -> str:
    """Extract category from recommendation metadata"""
    rule_tags = rec.get('RuleMetadata', {}).get('RuleTags', [])
    
    # Map common rule tags to categories
    if any(tag in ['Security', 'security'] for tag in rule_tags):
        return 'Security'
    elif any(tag in ['Performance', 'performance'] for tag in rule_tags):
        return 'Performance'
    elif any(tag in ['BestPractices', 'best-practices'] for tag in rule_tags):
        return 'BestPractices'
    elif any(tag in ['CodeQuality', 'code-quality'] for tag in rule_tags):
        return 'CodeQuality'
    else:
        return 'CodeQuality'  # Default category


def extract_recommendation_text(rec: Dict[str, Any]) -> str:
    """Extract recommendation text from various possible fields"""
    recommendation_details = rec.get('RecommendationDetails', {})
    
    # Try different fields for recommendation text
    return (
        recommendation_details.get('Text') or
        recommendation_details.get('Description') or
        rec.get('Description', '') or
        "Please review this code section for potential improvements"
    )


def calculate_severity_summary(recommendations: List[Dict]) -> Dict[str, int]:
    """
    Calculate summary statistics by severity level
    
    Args:
        recommendations: List of recommendation dictionaries
        
    Returns:
        Dictionary with counts per severity level
    """
    summary = {
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0,
        'info': 0
    }
    
    for rec in recommendations:
        severity = rec.get('severity', 'info').lower()
        if severity in summary:
            summary[severity] += 1
        else:
            summary['info'] += 1  # Default to info for unknown severities
    
    return summary


def extract_review_id(review_arn: str) -> str:
    """Extract review ID from ARN"""
    return review_arn.split('/')[-1] if review_arn else 'unknown'


def analyze_code_quality(
    repository_arn: str,
    branch_name: str,
    commit_sha: str
) -> dict:
    """
    Main tool function for code quality analysis.
    Called by agent via @agent.tool decorator in agent.py.
    
    This function initiates a comprehensive code review using Amazon CodeGuru Reviewer,
    waits for completion, and returns structured recommendations organized by severity.
    
    Args:
        repository_arn: ARN of the repository (e.g., arn:aws:codecommit:us-east-1:123456789012:my-repo)
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
                "low": int,
                "info": int
            }
        }
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting CodeGuru review for {repository_arn} @ {commit_sha}")
        
        # Validate input parameters
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
                "message": f"Code review timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds. Please try again later.",
                "recommendations": [],
                "total_recommendations": 0,
                "analysis_time_seconds": time.time() - start_time,
                "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
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
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
            "analysis_time_seconds": round(time.time() - start_time, 2),
            "summary": summary,
            "repository_arn": repository_arn,
            "commit_sha": commit_sha,
            "branch_name": branch_name
        }
        
        # Cache result for future use
        cache_result(commit_sha, result)
        
        return result
        
    except CodeGuruReviewerError as e:
        logger.error(f"CodeGuru Reviewer error: {str(e)}")
        return {
            "status": "error",
            "error_type": "codeguru_error",
            "message": str(e),
            "recommendations": [],
            "total_recommendations": 0,
            "analysis_time_seconds": round(time.time() - start_time, 2),
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        }
        
    except ClientError as e:
        logger.error(f"AWS service error in CodeGuru Reviewer: {str(e)}")
        return {
            "status": "error",
            "error_type": "aws_service_error",
            "message": f"CodeGuru API error: {e.response['Error']['Message']}",
            "recommendations": [],
            "total_recommendations": 0,
            "analysis_time_seconds": round(time.time() - start_time, 2),
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in CodeGuru Reviewer: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error_type": "internal_error", 
            "message": str(e),
            "recommendations": [],
            "total_recommendations": 0,
            "analysis_time_seconds": round(time.time() - start_time, 2),
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        }


# For development/testing - mock implementation when AWS services not available
def mock_analyze_code_quality(repository_arn: str, branch_name: str, commit_sha: str) -> dict:
    """Mock implementation for development/testing"""
    time.sleep(2)  # Simulate analysis time
    
    return {
        "status": "completed",
        "review_id": f"mock-review-{commit_sha[:8]}",
        "recommendations": [
            {
                "file_path": "src/main.py",
                "start_line": 42,
                "end_line": 45,
                "severity": "High",
                "category": "Performance",
                "description": "Inefficient nested loop detected",
                "recommendation": "Consider using a more efficient algorithm or data structure to reduce time complexity",
                "rule_id": "inefficient-loop",
                "rule_name": "Inefficient Loop Detection",
                "tags": ["performance", "algorithm"]
            },
            {
                "file_path": "src/utils.py",
                "start_line": 18,
                "end_line": 18,
                "severity": "Medium",
                "category": "Security",
                "description": "Potential resource leak detected",
                "recommendation": "Use a context manager to ensure proper resource cleanup",
                "rule_id": "resource-leak",
                "rule_name": "Resource Leak Detection",
                "tags": ["security", "resources"]
            }
        ],
        "total_recommendations": 2,
        "analysis_time_seconds": 2.0,
        "summary": {"critical": 0, "high": 1, "medium": 1, "low": 0, "info": 0},
        "repository_arn": repository_arn,
        "commit_sha": commit_sha,
        "branch_name": branch_name
    }


# Use mock implementation in development environment
if os.getenv('ENVIRONMENT') == 'development' or not os.getenv('AWS_REGION'):
    analyze_code_quality = mock_analyze_code_quality
    logger.info("Using mock CodeGuru Reviewer implementation for development")