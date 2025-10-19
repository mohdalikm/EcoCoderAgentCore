"""
GitHub Poster Tool - Internal Tool Module
Posts analysis reports as comments on GitHub pull requests

This tool integrates with the GitHub REST API to post formatted Markdown reports
as comments on pull requests, providing developers with actionable feedback.
"""

import logging
import time
import json
import os
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
GITHUB_API_BASE = "https://api.github.com"
BOT_COMMENT_SIGNATURE = "\n\n---\n*🌱 Posted by Eco-Coder AI Agent - Sustainable Software Development*"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
REQUEST_TIMEOUT = 30
MAX_COMMENT_LENGTH = 65536  # GitHub's comment length limit


class GitHubPosterError(Exception):
    """Exception for GitHub posting errors"""
    pass


def validate_inputs(
    repository_full_name: str,
    pull_request_number: int,
    report_markdown: str
) -> None:
    """
    Validate input parameters for GitHub comment posting
    
    Args:
        repository_full_name: Repository in "owner/repo" format
        pull_request_number: PR number
        report_markdown: Markdown report content
        
    Raises:
        ValueError: If any required parameter is invalid
    """
    if not repository_full_name or '/' not in repository_full_name:
        raise ValueError("repository_full_name must be in format 'owner/repo-name'")
    
    if not isinstance(pull_request_number, int) or pull_request_number < 1:
        raise ValueError("pull_request_number must be a positive integer")
    
    if not report_markdown or len(report_markdown.strip()) == 0:
        raise ValueError("report_markdown cannot be empty")
    
    if len(report_markdown) > MAX_COMMENT_LENGTH - len(BOT_COMMENT_SIGNATURE):
        raise ValueError(f"report_markdown is too long (max {MAX_COMMENT_LENGTH - len(BOT_COMMENT_SIGNATURE)} characters)")


def get_github_token() -> str:
    """
    Retrieve GitHub token from AWS Secrets Manager
    
    Returns:
        GitHub personal access token
        
    Raises:
        GitHubPosterError: If token retrieval fails
    """
    secret_name = "eco-coder/github-token"
    
    try:
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        
        if 'SecretString' in response:
            secret_data = json.loads(response['SecretString'])
            token = secret_data.get('token')
            if not token:
                raise GitHubPosterError("GitHub token not found in secret")
            return token
        else:
            raise GitHubPosterError("Secret string not found in response")
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            raise GitHubPosterError(f"Secret not found: {secret_name}")
        elif error_code == 'UnauthorizedOperation':
            raise GitHubPosterError("Insufficient permissions to access secret")
        else:
            raise GitHubPosterError(f"Failed to retrieve GitHub token: {e.response['Error']['Message']}")
    except json.JSONDecodeError as e:
        raise GitHubPosterError(f"Invalid JSON in secret: {str(e)}")


def create_requests_session() -> requests.Session:
    """
    Create a requests session with retry strategy
    
    Returns:
        Configured requests session
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=MAX_RETRIES,
        status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry
        method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
        backoff_factor=RETRY_BACKOFF_SECONDS
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def find_existing_comment(
    session: requests.Session,
    token: str,
    repo_full_name: str,
    pr_number: int
) -> Optional[int]:
    """
    Find existing Eco-Coder comment on the PR
    
    Args:
        session: Requests session
        token: GitHub API token
        repo_full_name: Repository full name
        pr_number: Pull request number
        
    Returns:
        Comment ID if found, None otherwise
    """
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "EcoCoder-Agent/1.0"
    }
    
    try:
        response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        comments = response.json()
        
        # Look for comment with our signature
        for comment in comments:
            if BOT_COMMENT_SIGNATURE in comment.get('body', ''):
                logger.info(f"Found existing Eco-Coder comment: {comment['id']}")
                return comment['id']
        
        logger.info("No existing Eco-Coder comment found")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error finding existing comment: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON response when finding comments: {str(e)}")
        return None


def create_comment(
    session: requests.Session,
    token: str,
    repo_full_name: str,
    pr_number: int,
    report: str
) -> Dict[str, Any]:
    """
    Create a new comment on the PR
    
    Args:
        session: Requests session
        token: GitHub API token
        repo_full_name: Repository full name
        pr_number: Pull request number
        report: Complete report with signature
        
    Returns:
        Comment data from GitHub API
        
    Raises:
        GitHubPosterError: If comment creation fails
    """
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "EcoCoder-Agent/1.0"
    }
    payload = {
        "body": report
    }
    
    try:
        response = session.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        comment_data = response.json()
        logger.info(f"Created GitHub comment: {comment_data['id']}")
        return comment_data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise GitHubPosterError("Authentication failed - check GitHub token permissions")
        elif e.response.status_code == 403:
            raise GitHubPosterError("Forbidden - insufficient permissions or rate limited")
        elif e.response.status_code == 404:
            raise GitHubPosterError(f"Repository or PR not found: {repo_full_name}#{pr_number}")
        elif e.response.status_code == 422:
            raise GitHubPosterError("Validation failed - check PR number and repository name")
        else:
            raise GitHubPosterError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except requests.exceptions.RequestException as e:
        raise GitHubPosterError(f"Request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise GitHubPosterError(f"Invalid JSON response: {str(e)}")


def update_comment(
    session: requests.Session,
    token: str,
    repo_full_name: str,
    comment_id: int,
    report: str
) -> Dict[str, Any]:
    """
    Update an existing comment
    
    Args:
        session: Requests session
        token: GitHub API token
        repo_full_name: Repository full name
        comment_id: ID of comment to update
        report: Complete report with signature
        
    Returns:
        Updated comment data from GitHub API
        
    Raises:
        GitHubPosterError: If comment update fails
    """
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/comments/{comment_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "EcoCoder-Agent/1.0"
    }
    payload = {
        "body": report
    }
    
    try:
        response = session.patch(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        comment_data = response.json()
        logger.info(f"Updated GitHub comment: {comment_id}")
        return comment_data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise GitHubPosterError("Authentication failed - check GitHub token permissions")
        elif e.response.status_code == 403:
            raise GitHubPosterError("Forbidden - insufficient permissions to update comment")
        elif e.response.status_code == 404:
            raise GitHubPosterError(f"Comment not found: {comment_id}")
        else:
            raise GitHubPosterError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except requests.exceptions.RequestException as e:
        raise GitHubPosterError(f"Request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise GitHubPosterError(f"Invalid JSON response: {str(e)}")


def format_report_with_metadata(report_markdown: str, execution_metadata: Dict[str, Any] = None) -> str:
    """
    Format the report with additional metadata and signature
    
    Args:
        report_markdown: Base report content
        execution_metadata: Optional metadata about the analysis execution
        
    Returns:
        Complete formatted report
    """
    # Add timestamp and metadata if provided
    formatted_report = report_markdown
    
    if execution_metadata:
        metadata_section = f"\n\n### 📊 Analysis Metadata\n"
        if execution_metadata.get('execution_time_seconds'):
            metadata_section += f"- **Analysis Duration**: {execution_metadata['execution_time_seconds']:.1f} seconds\n"
        if execution_metadata.get('session_id'):
            metadata_section += f"- **Session ID**: `{execution_metadata['session_id']}`\n"
        if execution_metadata.get('commit_sha'):
            metadata_section += f"- **Commit**: `{execution_metadata['commit_sha'][:8]}...`\n"
        
        formatted_report += metadata_section
    
    # Add signature
    formatted_report += BOT_COMMENT_SIGNATURE
    
    return formatted_report


def post_github_comment(
    repository_full_name: str,
    pull_request_number: int,
    report_markdown: str,
    update_existing: bool = True,
    execution_metadata: Dict[str, Any] = None
) -> dict:
    """
    Main tool function for posting GitHub comments.
    Called by agent via @agent.tool decorator in agent.py.
    
    This tool posts the generated Markdown report as a comment on the specified
    pull request. It can update an existing bot comment if found, or create a
    new comment if this is the first analysis.
    
    Args:
        repository_full_name: Repository in "owner/repo" format (e.g., "octocat/Hello-World")
        pull_request_number: PR number (integer)
        report_markdown: Formatted report in Markdown
        update_existing: Whether to update existing bot comment (default: True)
        execution_metadata: Optional metadata about the analysis execution
        
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
    start_time = time.time()
    
    try:
        logger.info(f"Posting comment to PR #{pull_request_number} in {repository_full_name}")
        
        # Validate input parameters
        validate_inputs(repository_full_name, pull_request_number, report_markdown)
        
        # Get GitHub token from Secrets Manager
        github_token = get_github_token()
        
        # Create requests session with retry logic
        session = create_requests_session()
        
        # Format report with metadata and signature
        full_report = format_report_with_metadata(report_markdown, execution_metadata)
        
        # Check if we should update existing comment
        existing_comment_id = None
        if update_existing:
            existing_comment_id = find_existing_comment(
                session, github_token, repository_full_name, pull_request_number
            )
        
        # Post or update comment
        if existing_comment_id:
            comment_data = update_comment(
                session, github_token, repository_full_name, existing_comment_id, full_report
            )
            action = "updated"
        else:
            comment_data = create_comment(
                session, github_token, repository_full_name, pull_request_number, full_report
            )
            action = "created"
        
        execution_time = time.time() - start_time
        
        result = {
            "status": "success",
            "comment_id": comment_data['id'],
            "comment_url": comment_data['html_url'],
            "action": action,
            "repository": repository_full_name,
            "pr_number": pull_request_number,
            "execution_time_seconds": round(execution_time, 2)
        }
        
        logger.info(f"Successfully {action} GitHub comment {comment_data['id']} in {execution_time:.2f}s")
        return result
        
    except GitHubPosterError as e:
        execution_time = time.time() - start_time
        logger.error(f"GitHub poster error: {str(e)}")
        return {
            "status": "failure",
            "error_type": "github_error",
            "error_message": str(e),
            "repository": repository_full_name,
            "pr_number": pull_request_number,
            "execution_time_seconds": round(execution_time, 2)
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Unexpected error in GitHub poster: {str(e)}", exc_info=True)
        return {
            "status": "failure",
            "error_type": "internal_error",
            "error_message": str(e),
            "repository": repository_full_name,
            "pr_number": pull_request_number,
            "execution_time_seconds": round(execution_time, 2)
        }


# For development/testing - mock implementation when external services not available
def mock_post_github_comment(
    repository_full_name: str,
    pull_request_number: int,
    report_markdown: str,
    update_existing: bool = True,
    execution_metadata: Dict[str, Any] = None
) -> dict:
    """Mock implementation for development/testing"""
    time.sleep(1)  # Simulate API call time
    
    # Validate inputs even in mock mode
    try:
        validate_inputs(repository_full_name, pull_request_number, report_markdown)
    except ValueError as e:
        return {
            "status": "failure",
            "error_type": "validation_error",
            "error_message": str(e),
            "repository": repository_full_name,
            "pr_number": pull_request_number,
            "execution_time_seconds": 1.0
        }
    
    # Mock successful response
    mock_comment_id = 987654321
    mock_comment_url = f"https://github.com/{repository_full_name}/pull/{pull_request_number}#issuecomment-{mock_comment_id}"
    
    logger.info(f"Mock: Would post comment to {repository_full_name}#{pull_request_number}")
    logger.info(f"Mock comment preview (first 100 chars): {report_markdown[:100]}...")
    
    return {
        "status": "success",
        "comment_id": mock_comment_id,
        "comment_url": mock_comment_url,
        "action": "created",  # Always "created" in mock mode
        "repository": repository_full_name,
        "pr_number": pull_request_number,
        "execution_time_seconds": 1.0,
        "mock_mode": True
    }


# Use mock implementation in development environment
if os.getenv('ENVIRONMENT') == 'development' or not os.getenv('AWS_REGION'):
    post_github_comment = mock_post_github_comment
    logger.info("Using mock GitHub poster implementation for development")