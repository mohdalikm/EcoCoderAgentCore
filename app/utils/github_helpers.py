"""
GitHub utilities for EcoCoderAgentCore agent.

This module provides GitHub API helpers and webhook processing utilities.
"""

import os
import json
import logging
import hashlib
import hmac
from typing import Dict, Any, Optional, List, Tuple, Union
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class GitHubError(Exception):
    """Custom exception for GitHub-related errors."""
    pass


class GitHubHelper:
    """Helper class for GitHub API operations."""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub helper.
        
        Args:
            token: GitHub personal access token
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.session = self._create_session()
        self._mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PATCH"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Set headers
        session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'EcoCoderAgentCore/1.0'
        })
        
        if self.token:
            session.headers['Authorization'] = f'token {self.token}'
            
        return session
    
    def parse_webhook_payload(self, payload: Union[str, Dict[str, Any]], 
                            signature: Optional[str] = None, 
                            secret: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse and validate GitHub webhook payload.
        
        Args:
            payload: Webhook payload (string or dict)
            signature: GitHub signature header (X-Hub-Signature-256)
            secret: Webhook secret for validation
            
        Returns:
            Parsed payload dictionary
            
        Raises:
            GitHubError: If payload is invalid or signature doesn't match
        """
        if self._mock_mode:
            return {
                'action': 'opened',
                'pull_request': {
                    'number': 123,
                    'title': 'Mock PR for testing',
                    'head': {'sha': 'abc123'},
                    'base': {'sha': 'def456'},
                    'html_url': 'https://github.com/owner/repo/pull/123'
                },
                'repository': {
                    'name': 'mock-repo',
                    'owner': {'login': 'mock-owner'},
                    'full_name': 'mock-owner/mock-repo'
                }
            }
        
        # Convert string payload to dict
        if isinstance(payload, str):
            try:
                payload_dict = json.loads(payload)
                payload_str = payload
            except json.JSONDecodeError as e:
                raise GitHubError(f"Invalid JSON payload: {str(e)}")
        else:
            payload_dict = payload
            payload_str = json.dumps(payload, separators=(',', ':'))
        
        # Validate signature if provided
        if signature and secret:
            if not self._validate_signature(payload_str, signature, secret):
                raise GitHubError("Invalid webhook signature")
        
        # Validate required fields
        if 'action' not in payload_dict:
            raise GitHubError("Missing 'action' field in payload")
            
        if 'pull_request' not in payload_dict and 'repository' not in payload_dict:
            raise GitHubError("Missing required fields in payload")
            
        return payload_dict
    
    def _validate_signature(self, payload: str, signature: str, secret: str) -> bool:
        """
        Validate GitHub webhook signature.
        
        Args:
            payload: Raw payload string
            signature: GitHub signature (sha256=...)
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        if not signature.startswith('sha256='):
            return False
            
        expected_signature = 'sha256=' + hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def get_pull_request(self, repo: str, pr_number: int) -> Dict[str, Any]:
        """
        Get pull request details.
        
        Args:
            repo: Repository name (owner/repo)
            pr_number: Pull request number
            
        Returns:
            Pull request data
        """
        if self._mock_mode:
            return {
                'number': pr_number,
                'title': f'Mock PR #{pr_number}',
                'state': 'open',
                'head': {
                    'sha': 'abc123def456',
                    'ref': 'feature-branch'
                },
                'base': {
                    'sha': 'main456def789',
                    'ref': 'main'
                },
                'html_url': f'https://github.com/{repo}/pull/{pr_number}',
                'diff_url': f'https://github.com/{repo}/pull/{pr_number}.diff',
                'patch_url': f'https://github.com/{repo}/pull/{pr_number}.patch'
            }
            
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise GitHubError(f"Failed to get PR {pr_number}: {str(e)}")
    
    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """
        Get pull request diff content.
        
        Args:
            repo: Repository name (owner/repo)
            pr_number: Pull request number
            
        Returns:
            Diff content as string
        """
        if self._mock_mode:
            return """diff --git a/src/example.py b/src/example.py
index 1234567..abcdefg 100644
--- a/src/example.py
+++ b/src/example.py
@@ -10,7 +10,7 @@ class Example:
         self.data = []
 
     def process_data(self, items):
-        for item in items:
+        for i, item in enumerate(items):
             # Process each item
             result = self.expensive_operation(item)
             self.data.append(result)
"""
            
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"
        headers = {'Accept': 'application/vnd.github.v3.diff'}
        
        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.text
            
        except requests.RequestException as e:
            raise GitHubError(f"Failed to get PR diff: {str(e)}")
    
    def get_pr_files(self, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get list of files changed in pull request.
        
        Args:
            repo: Repository name (owner/repo)
            pr_number: Pull request number
            
        Returns:
            List of changed files with metadata
        """
        if self._mock_mode:
            return [
                {
                    'filename': 'src/example.py',
                    'status': 'modified',
                    'additions': 5,
                    'deletions': 2,
                    'changes': 7,
                    'patch': '@@ -10,7 +10,7 @@ class Example:\n     self.data = []\n \n def process_data(self, items):\n-        for item in items:\n+        for i, item in enumerate(items):\n         # Process each item\n         result = self.expensive_operation(item)\n         self.data.append(result)'
                },
                {
                    'filename': 'tests/test_example.py',
                    'status': 'added',
                    'additions': 15,
                    'deletions': 0,
                    'changes': 15
                }
            ]
            
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}/files"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise GitHubError(f"Failed to get PR files: {str(e)}")
    
    def create_comment(self, repo: str, pr_number: int, body: str) -> Dict[str, Any]:
        """
        Create a comment on pull request.
        
        Args:
            repo: Repository name (owner/repo)
            pr_number: Pull request number
            body: Comment content
            
        Returns:
            Created comment data
        """
        if self._mock_mode:
            return {
                'id': 123456789,
                'html_url': f'https://github.com/{repo}/pull/{pr_number}#issuecomment-123456789',
                'body': body,
                'created_at': '2024-01-15T10:30:00Z'
            }
            
        url = f"{self.base_url}/repos/{repo}/issues/{pr_number}/comments"
        data = {'body': body}
        
        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise GitHubError(f"Failed to create comment: {str(e)}")
    
    def update_comment(self, repo: str, comment_id: int, body: str) -> Dict[str, Any]:
        """
        Update existing comment.
        
        Args:
            repo: Repository name (owner/repo)
            comment_id: Comment ID to update
            body: New comment content
            
        Returns:
            Updated comment data
        """
        if self._mock_mode:
            return {
                'id': comment_id,
                'body': body,
                'updated_at': '2024-01-15T10:35:00Z'
            }
            
        url = f"{self.base_url}/repos/{repo}/issues/comments/{comment_id}"
        data = {'body': body}
        
        try:
            response = self.session.patch(url, json=data)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise GitHubError(f"Failed to update comment: {str(e)}")
    
    def find_bot_comment(self, repo: str, pr_number: int, 
                        marker: str = "<!-- EcoCoder Report -->") -> Optional[Dict[str, Any]]:
        """
        Find existing bot comment by marker.
        
        Args:
            repo: Repository name (owner/repo)
            pr_number: Pull request number
            marker: HTML comment marker to identify bot comments
            
        Returns:
            Existing comment data or None
        """
        if self._mock_mode:
            return None  # Simulate no existing comment
            
        url = f"{self.base_url}/repos/{repo}/issues/{pr_number}/comments"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            comments = response.json()
            
            # Look for comment with our marker
            for comment in comments:
                if marker in comment.get('body', ''):
                    return comment
                    
            return None
            
        except requests.RequestException as e:
            logger.warning(f"Failed to retrieve existing comments: {e}")
            return None
    
    def extract_repo_info(self, github_url: str) -> Tuple[str, str]:
        """
        Extract owner and repo name from GitHub URL.
        
        Args:
            github_url: GitHub repository URL
            
        Returns:
            Tuple of (owner, repo)
        """
        parsed = urlparse(github_url)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) < 2:
            raise GitHubError(f"Invalid GitHub URL: {github_url}")
            
        owner = path_parts[0]
        repo = path_parts[1]
        
        # Remove .git suffix if present
        if repo.endswith('.git'):
            repo = repo[:-4]
            
        return owner, repo
    
    def is_rate_limited(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Check GitHub API rate limit status.
        
        Returns:
            Tuple of (is_limited, rate_limit_info)
        """
        if self._mock_mode:
            return False, {
                'limit': 5000,
                'remaining': 4500,
                'reset': 1705320000
            }
            
        url = f"{self.base_url}/rate_limit"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            rate_limit = response.json()['rate']
            
            is_limited = rate_limit['remaining'] <= 10
            return is_limited, rate_limit
            
        except requests.RequestException as e:
            logger.warning(f"Failed to check rate limit: {e}")
            return False, {}


def format_code_block(content: str, language: str = "") -> str:
    """
    Format content as GitHub markdown code block.
    
    Args:
        content: Content to format
        language: Programming language for syntax highlighting
        
    Returns:
        Formatted markdown code block
    """
    return f"```{language}\n{content}\n```"


def format_pr_link(repo: str, pr_number: int) -> str:
    """
    Format pull request link for markdown.
    
    Args:
        repo: Repository name (owner/repo)
        pr_number: Pull request number
        
    Returns:
        Formatted markdown link
    """
    return f"[#{pr_number}](https://github.com/{repo}/pull/{pr_number})"


def truncate_content(content: str, max_length: int = 60000) -> str:
    """
    Truncate content for GitHub comment limits.
    
    Args:
        content: Content to truncate
        max_length: Maximum allowed length
        
    Returns:
        Truncated content with notice if needed
    """
    if len(content) <= max_length:
        return content
        
    truncated = content[:max_length - 100]  # Leave room for notice
    return f"{truncated}\n\n... (Content truncated due to length limits)"