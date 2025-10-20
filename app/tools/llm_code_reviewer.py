"""
LLM Code Reviewer Tool - AI-Powered Code Quality Analysis

This tool provides comprehensive code quality analysis using Large Language Models (LLMs)
focsuing on CO2 emission form the code execution. It analyzes pull request diffs
for code quality, security vulnerabilities, performance issues, and best practices.

Key Features:
1. Fetches PR diff from GitHub using diff_url from webhook payload
2. Uses AWS Bedrock LLMs for comprehensive code analysis
3. Provides detailed recommendations with severity levels
4. Supports multiple programming languages
5. Focuses on security, performance, maintainability, and best practices

This tool is designed to be a drop-in replacement for CodeGuru Reviewer with enhanced
capabilities through modern LLM analysis.

Author: EcoCoder Agent
Version: 1.0.0 (LLM-Powered Code Review)
"""

import logging
import json
import re
import time
from typing import Dict, Any, List, Optional, Tuple
import requests
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

# Import utilities
from app.utils.aws_helpers import AWSHelper
from app.utils.github_helpers import GitHubHelper

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
MAX_DIFF_SIZE = 500000  # 500KB max diff size to analyze
CHUNK_SIZE = 50000  # 50KB chunks for large diffs
DEFAULT_MODEL = "amazon.titan-text-express-v1"  # Amazon Titan Text Express
FALLBACK_MODEL = "amazon.titan-text-lite-v1"  # Amazon Titan Text Lite (faster fallback)

# Code review focus areas
REVIEW_CATEGORIES = {
    "security": {
        "weight": 10,
        "description": "Security vulnerabilities and best practices"
    },
    "performance": {
        "weight": 8,
        "description": "Performance issues and optimization opportunities"
    },
    "maintainability": {
        "weight": 7,
        "description": "Code maintainability and readability"
    },
    "reliability": {
        "weight": 9,
        "description": "Error handling and edge cases"
    },
    "best_practices": {
        "weight": 6,
        "description": "Language-specific best practices and conventions"
    }
}

# Severity levels
SEVERITY_LEVELS = {
    "critical": {"score": 10, "emoji": "🚨", "color": "red"},
    "high": {"score": 8, "emoji": "🔴", "color": "orange"},
    "medium": {"score": 5, "emoji": "🟡", "color": "yellow"},
    "low": {"score": 2, "emoji": "🔵", "color": "blue"},
    "info": {"score": 1, "emoji": "ℹ️", "color": "gray"}
}


class LLMCodeReviewError(Exception):
    """Exception for LLM code review specific errors"""
    pass


class DiffFetcher:
    """Handles fetching and parsing PR diffs from GitHub"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.session = requests.Session()
        if github_token:
            self.session.headers.update({
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3.diff'
            })
    
    def fetch_pr_diff(self, diff_url: str) -> str:
        """
        Fetch PR diff from GitHub
        
        Args:
            diff_url: GitHub PR diff URL (e.g., https://github.com/owner/repo/pull/1.diff)
            
        Returns:
            Raw diff content as string
        """
        try:
            logger.info(f"Fetching PR diff from: {diff_url}")
            
            response = self.session.get(diff_url, timeout=30)
            response.raise_for_status()
            
            diff_content = response.text
            logger.info(f"Successfully fetched diff: {len(diff_content)} characters")
            
            if len(diff_content) > MAX_DIFF_SIZE:
                logger.warning(f"Diff size ({len(diff_content)}) exceeds maximum ({MAX_DIFF_SIZE}), truncating")
                diff_content = diff_content[:MAX_DIFF_SIZE] + "\n... [TRUNCATED]"
            
            return diff_content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch PR diff: {e}")
            raise LLMCodeReviewError(f"Could not fetch PR diff: {str(e)}")
    
    def parse_diff(self, diff_content: str) -> Dict[str, Any]:
        """
        Parse diff content to extract file changes and metadata
        
        Args:
            diff_content: Raw diff content
            
        Returns:
            Dictionary with parsed diff information
        """
        try:
            files_changed = []
            current_file = None
            
            lines = diff_content.split('\n')
            for line in lines:
                # File header
                if line.startswith('diff --git'):
                    if current_file:
                        files_changed.append(current_file)
                    
                    # Extract file paths
                    parts = line.split()
                    if len(parts) >= 4:
                        old_file = parts[2][2:]  # Remove 'a/' prefix
                        new_file = parts[3][2:]  # Remove 'b/' prefix
                        current_file = {
                            'old_path': old_file,
                            'new_path': new_file,
                            'changes': [],
                            'additions': 0,
                            'deletions': 0,
                            'language': self._detect_language(new_file)
                        }
                
                # File mode/index info
                elif line.startswith('index ') and current_file:
                    current_file['index'] = line
                
                # Line changes
                elif current_file and (line.startswith('+') or line.startswith('-')):
                    if not line.startswith('+++') and not line.startswith('---'):
                        current_file['changes'].append(line)
                        if line.startswith('+'):
                            current_file['additions'] += 1
                        elif line.startswith('-'):
                            current_file['deletions'] += 1
            
            # Add the last file
            if current_file:
                files_changed.append(current_file)
            
            # Calculate summary statistics
            total_additions = sum(f['additions'] for f in files_changed)
            total_deletions = sum(f['deletions'] for f in files_changed)
            languages = list(set(f['language'] for f in files_changed if f['language']))
            
            return {
                'files_changed': files_changed,
                'total_files': len(files_changed),
                'total_additions': total_additions,
                'total_deletions': total_deletions,
                'languages': languages,
                'raw_diff': diff_content
            }
            
        except Exception as e:
            logger.error(f"Error parsing diff: {e}")
            raise LLMCodeReviewError(f"Could not parse diff: {str(e)}")
    
    def _detect_language(self, filename: str) -> Optional[str]:
        """Detect programming language from file extension"""
        ext_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.sh': 'Shell',
            '.sql': 'SQL',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.xml': 'XML',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.md': 'Markdown',
            '.dockerfile': 'Docker',
            '.tf': 'Terraform'
        }
        
        for ext, lang in ext_map.items():
            if filename.lower().endswith(ext):
                return lang
        
        return None


class LLMCodeAnalyzer:
    """Handles LLM-based code analysis using AWS Bedrock"""
    
    def __init__(self, region_name: str = 'us-east-1'):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)
        self.aws_helper = AWSHelper()
    
    def analyze_code_changes(self, parsed_diff: Dict[str, Any], pr_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze code changes using LLM
        
        Args:
            parsed_diff: Parsed diff information
            pr_context: PR context (title, description, etc.)
            
        Returns:
            Comprehensive code review results
        """
        try:
            logger.info(f"Starting LLM code analysis for {parsed_diff['total_files']} files")
            
            # Prepare analysis context
            analysis_context = self._prepare_analysis_context(parsed_diff, pr_context)
            
            # Analyze in chunks if diff is large
            if len(parsed_diff['raw_diff']) > CHUNK_SIZE:
                return self._analyze_large_diff(parsed_diff, pr_context)
            else:
                return self._analyze_single_chunk(analysis_context)
                
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            raise LLMCodeReviewError(f"Code analysis failed: {str(e)}")
    
    def _prepare_analysis_context(self, parsed_diff: Dict[str, Any], pr_context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context for LLM analysis"""
        return {
            'pr_title': pr_context.get('title', 'N/A'),
            'pr_description': pr_context.get('body', 'N/A'),
            'files_changed': parsed_diff['total_files'],
            'additions': parsed_diff['total_additions'],
            'deletions': parsed_diff['total_deletions'],
            'languages': parsed_diff['languages'],
            'diff_content': parsed_diff['raw_diff'][:CHUNK_SIZE]  # Limit for single chunk
        }
    
    def _analyze_single_chunk(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single chunk of code changes"""
        prompt = self._build_analysis_prompt(context)
        
        try:
            # Use Claude 3.5 Sonnet for comprehensive analysis
            response = self._call_bedrock_llm(prompt, DEFAULT_MODEL)
            return self._parse_llm_response(response)
            
        except Exception as e:
            logger.warning(f"Primary model failed, trying fallback: {e}")
            try:
                # Fallback to Claude 3 Haiku for faster analysis
                response = self._call_bedrock_llm(prompt, FALLBACK_MODEL)
                return self._parse_llm_response(response)
            except Exception as fallback_e:
                logger.error(f"Fallback model also failed: {fallback_e}")
                return self._create_fallback_analysis(context)
    
    def _analyze_large_diff(self, parsed_diff: Dict[str, Any], pr_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze large diffs by breaking into chunks"""
        logger.info("Analyzing large diff in chunks")
        
        # For large diffs, analyze file by file for the most critical files
        critical_files = self._identify_critical_files(parsed_diff['files_changed'])
        
        all_findings = []
        summary_stats = {
            'total_issues': 0,
            'critical_issues': 0,
            'security_issues': 0,
            'performance_issues': 0
        }
        
        for file_info in critical_files[:5]:  # Limit to 5 most critical files
            file_context = {
                'pr_title': pr_context.get('title', 'N/A'),
                'file_path': file_info['new_path'],
                'language': file_info['language'],
                'changes': '\n'.join(file_info['changes'][:100]),  # Limit changes
                'additions': file_info['additions'],
                'deletions': file_info['deletions']
            }
            
            try:
                file_analysis = self._analyze_single_file(file_context)
                all_findings.extend(file_analysis.get('findings', []))
                
                # Update summary stats
                for finding in file_analysis.get('findings', []):
                    summary_stats['total_issues'] += 1
                    if finding.get('severity') == 'critical':
                        summary_stats['critical_issues'] += 1
                    if finding.get('category') == 'security':
                        summary_stats['security_issues'] += 1
                    if finding.get('category') == 'performance':
                        summary_stats['performance_issues'] += 1
                        
            except Exception as e:
                logger.warning(f"Failed to analyze file {file_info['new_path']}: {e}")
        
        return {
            'status': 'completed',
            'analysis_type': 'chunked_analysis',
            'files_analyzed': len(critical_files),
            'total_findings': len(all_findings),
            'findings': all_findings,
            'summary': summary_stats,
            'recommendations': self._generate_summary_recommendations(all_findings)
        }
    
    def _analyze_single_file(self, file_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single file's changes"""
        prompt = self._build_file_analysis_prompt(file_context)
        
        try:
            response = self._call_bedrock_llm(prompt, FALLBACK_MODEL)  # Use faster model for files
            return self._parse_llm_response(response)
        except Exception as e:
            logger.warning(f"File analysis failed: {e}")
            return {'findings': [], 'summary': 'Analysis failed'}
    
    def _identify_critical_files(self, files_changed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify most critical files to analyze first"""
        def file_priority(file_info):
            score = 0
            
            # Language priority
            lang = file_info.get('language', '')
            if lang in ['Python', 'JavaScript', 'TypeScript', 'Java']:
                score += 10
            elif lang in ['C++', 'C', 'Go', 'Rust']:
                score += 8
            
            # File type priority
            path = file_info.get('new_path', '').lower()
            if any(keyword in path for keyword in ['auth', 'security', 'password', 'token']):
                score += 15
            if any(keyword in path for keyword in ['api', 'service', 'controller']):
                score += 10
            if any(keyword in path for keyword in ['test', 'spec']):
                score -= 5
            
            # Change size
            changes = file_info.get('additions', 0) + file_info.get('deletions', 0)
            score += min(changes / 10, 20)  # Cap at 20 points
            
            return score
        
        return sorted(files_changed, key=file_priority, reverse=True)
    
    def _build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt for LLM"""
        return f"""You are an expert code reviewer analyzing a pull request focusing on code performance to reduce the Co2 footprint of the application. Please provide a comprehensive review focusing on performance, maintainability and best practices.

Pull Request Context:
- Title: {context['pr_title']}
- Description: {context['pr_description']}
- Files Changed: {context['files_changed']}
- Languages: {', '.join(context['languages']) if context['languages'] else 'Unknown'}
- Additions: +{context['additions']}, Deletions: -{context['deletions']}

Code Diff to Review:
```diff
{context['diff_content']}
```

Please analyze this code and provide your response in the following JSON format:

{{
    "overall_assessment": {{
        "quality_score": <1-10>,
        "performance_score": <1-10>,
        "maintainability_score": <1-10>,
        "summary": "<brief overall assessment>"
    }},
    "findings": [
        {{
            "category": "<security|performance|maintainability|reliability|best_practices>",
            "severity": "<critical|high|medium|low|info>",
            "title": "<brief title>",
            "description": "<detailed description>",
            "file_path": "<file path if applicable>",
            "line_range": "<line numbers if applicable>",
            "code_snippet": "<relevant code snippet>",
            "recommendation": "<specific fix recommendation>",
            "impact": "<potential impact if not fixed>"
        }}
    ],
    "positive_aspects": [
        "<list of good practices found>"
    ],
    "recommendations": [
        "<prioritized list of recommendations>"
    ]
}}

Focus on:
1. Performance problems (inefficient algorithms, memory leaks, etc.) with the aim to reduce Co2 emissions from code execution.
2. Code maintainability (complex functions, poor naming, lack of documentation)
3. Language-specific best practices

Be specific about file paths and line numbers when possible. Provide actionable recommendations. If no recommendations, state 'No issues found'."""
    
    def _build_file_analysis_prompt(self, file_context: Dict[str, Any]) -> str:
        """Build file-specific analysis prompt"""
        return f"""Analyze this specific file change for code quality issues:

File: {file_context['file_path']}
Language: {file_context['language']}
Changes: +{file_context['additions']} -{file_context['deletions']}

Code Changes:
```diff
{file_context['changes']}
```

Provide analysis in JSON format focusing on the most critical issues in this file:

{{
    "findings": [
        {{
            "category": "<security|performance|maintainability|reliability|best_practices>",
            "severity": "<critical|high|medium|low|info>",
            "title": "<issue title>",
            "description": "<detailed description>",
            "recommendation": "<specific fix>"
        }}
    ]
}}"""
    
    def _call_bedrock_llm(self, prompt: str, model_id: str) -> str:
        """Call AWS Bedrock LLM with the analysis prompt"""
        try:
            # Prepare request for different model types
            if "claude" in model_id:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "temperature": 0.1,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            elif "titan" in model_id:
                # Amazon Titan models
                body = {
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 4000,
                        "temperature": 0.1,
                        "topP": 0.9,
                        "stopSequences": []
                    }
                }
            else:
                # Fallback for other models
                body = {
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 4000,
                        "temperature": 0.1
                    }
                }
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            
            if "claude" in model_id:
                return response_body['content'][0]['text']
            elif "titan" in model_id:
                return response_body['results'][0]['outputText']
            else:
                return response_body['results'][0]['outputText']
                
        except Exception as e:
            logger.error(f"Bedrock LLM call failed: {e}")
            raise
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                parsed = json.loads(json_text)
                
                # Validate structure
                if 'findings' in parsed:
                    return {
                        'status': 'completed',
                        'analysis_type': 'llm_analysis',
                        'findings': parsed.get('findings', []),
                        'overall_assessment': parsed.get('overall_assessment', {}),
                        'positive_aspects': parsed.get('positive_aspects', []),
                        'recommendations': parsed.get('recommendations', []),
                        'total_findings': len(parsed.get('findings', []))
                    }
            
            # Fallback: parse as plain text
            return self._parse_text_response(response_text)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse JSON response: {e}")
            return self._parse_text_response(response_text)
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return self._create_error_response(str(e))
    
    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse plain text response as fallback"""
        # Simple text parsing for basic findings
        findings = []
        
        # Look for common issue patterns
        lines = text.split('\n')
        current_finding = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect severity indicators
            severity = 'info'
            if any(word in line.lower() for word in ['critical', 'severe', 'dangerous']):
                severity = 'critical'
            elif any(word in line.lower() for word in ['high', 'important', 'major']):
                severity = 'high'
            elif any(word in line.lower() for word in ['medium', 'moderate']):
                severity = 'medium'
            elif any(word in line.lower() for word in ['low', 'minor']):
                severity = 'low'
            
            # Detect categories
            category = 'best_practices'
            if any(word in line.lower() for word in ['security', 'vulnerability', 'exploit']):
                category = 'security'
            elif any(word in line.lower() for word in ['performance', 'slow', 'inefficient']):
                category = 'performance'
            elif any(word in line.lower() for word in ['maintainability', 'readable', 'complex']):
                category = 'maintainability'
            elif any(word in line.lower() for word in ['error', 'exception', 'reliability']):
                category = 'reliability'
            
            if line.startswith('-') or line.startswith('*') or line.startswith('•'):
                findings.append({
                    'category': category,
                    'severity': severity,
                    'title': line[1:].strip()[:100],
                    'description': line[1:].strip(),
                    'recommendation': 'See description for details'
                })
        
        return {
            'status': 'completed',
            'analysis_type': 'text_fallback',
            'findings': findings,
            'total_findings': len(findings),
            'raw_response': text
        }
    
    def _create_fallback_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create basic analysis when LLM fails"""
        return {
            'status': 'completed',
            'analysis_type': 'fallback_analysis',
            'findings': [
                {
                    'category': 'best_practices',
                    'severity': 'info',
                    'title': 'LLM Analysis Unavailable',
                    'description': f'Could not perform detailed LLM analysis. Please review the {context.get("files_changed", "N/A")} changed files manually.',
                    'recommendation': 'Consider running local static analysis tools or manual code review.'
                }
            ],
            'total_findings': 1,
            'message': 'LLM code analysis was not available, basic analysis provided'
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response structure"""
        return {
            'status': 'error',
            'error_type': 'analysis_error',
            'message': error_message,
            'findings': [],
            'total_findings': 0
        }
    
    def _generate_summary_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """Generate high-level recommendations from findings"""
        recommendations = []
        
        # Count issues by category and severity
        security_count = len([f for f in findings if f.get('category') == 'security'])
        critical_count = len([f for f in findings if f.get('severity') == 'critical'])
        high_count = len([f for f in findings if f.get('severity') == 'high'])
        
        if critical_count > 0:
            recommendations.append(f"Address {critical_count} critical issue(s) immediately before merging")
        
        if security_count > 0:
            recommendations.append(f"Review {security_count} security-related finding(s) carefully")
        
        if high_count > 0:
            recommendations.append(f"Consider fixing {high_count} high-priority issue(s)")
        
        if not findings:
            recommendations.append("No significant issues found - code looks good!")
        
        recommendations.append("Consider adding automated testing for changed code")
        recommendations.append("Update documentation if necessary")
        
        return recommendations


def analyze_code_quality_with_llm(
    repository_arn: str,
    branch_name: str,
    commit_sha: str,
    pr_payload: Optional[Dict[str, Any]] = None,
    github_token: Optional[str] = None
) -> dict:
    """
    Main tool function for LLM-based code quality analysis.
    Called by agent via @agent.tool decorator in agent.py.
    
    This tool replaces the deprecated CodeGuru Reviewer with modern LLM-based analysis.
    It fetches PR diffs and uses AWS Bedrock LLMs for comprehensive code review.
    
    Args:
        repository_arn: Repository ARN (for compatibility, not used)
        branch_name: Git branch name
        commit_sha: Git commit SHA
        pr_payload: GitHub PR webhook payload (optional, for diff_url extraction)
        github_token: GitHub personal access token
        
    Returns:
        Dictionary containing:
        {
            "status": "completed" | "error",
            "analysis_type": "llm_analysis",
            "total_findings": int,
            "findings": [
                {
                    "category": str,
                    "severity": str,
                    "title": str,
                    "description": str,
                    "file_path": str,
                    "recommendation": str
                }
            ],
            "overall_assessment": {
                "quality_score": int,
                "security_score": int,
                "performance_score": int
            },
            "recommendations": [str],
            "analysis_time_seconds": float
        }
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting LLM code analysis for {commit_sha} on {branch_name}")
        
        # Initialize GitHub token if not provided
        if not github_token:
            try:
                aws_helper = AWSHelper()
                secret = aws_helper.get_secret('eco-coder/github-token')
                github_token = secret.get('github_token')
                logger.info("Retrieved GitHub token from AWS Secrets Manager")
            except Exception as e:
                logger.warning(f"Could not retrieve GitHub token: {e}")
        
        # Extract diff URL from PR payload
        diff_url = None
        pr_context = {}
        
        if pr_payload and 'pull_request' in pr_payload:
            pr_data = pr_payload['pull_request']
            diff_url = pr_data.get('diff_url')
            pr_context = {
                'title': pr_data.get('title', ''),
                'body': pr_data.get('body', ''),
                'number': pr_data.get('number'),
                'additions': pr_data.get('additions', 0),
                'deletions': pr_data.get('deletions', 0),
                'changed_files': pr_data.get('changed_files', 0)
            }
            logger.info(f"Found PR diff URL: {diff_url}")
        
        if not diff_url:
            # Construct diff URL from repository info if not provided
            if pr_payload and 'repository' in pr_payload:
                repo_full_name = pr_payload['repository']['full_name']
                pr_number = pr_payload.get('number') or pr_context.get('number')
                if pr_number:
                    diff_url = f"https://github.com/{repo_full_name}/pull/{pr_number}.diff"
                    logger.info(f"Constructed diff URL: {diff_url}")
        
        if not diff_url:
            return {
                'status': 'error',
                'error_type': 'missing_diff_url',
                'message': 'Could not determine PR diff URL from payload',
                'analysis_time_seconds': round(time.time() - start_time, 3)
            }
        
        # Fetch and parse PR diff
        diff_fetcher = DiffFetcher(github_token)
        diff_content = diff_fetcher.fetch_pr_diff(diff_url)
        parsed_diff = diff_fetcher.parse_diff(diff_content)
        
        logger.info(f"Parsed diff: {parsed_diff['total_files']} files, "
                   f"+{parsed_diff['total_additions']} -{parsed_diff['total_deletions']}")
        
        # Analyze code with LLM
        analyzer = LLMCodeAnalyzer()
        analysis_result = analyzer.analyze_code_changes(parsed_diff, pr_context)
        
        # Add metadata
        analysis_result.update({
            'commit_sha': commit_sha,
            'branch_name': branch_name,
            'diff_url': diff_url,
            'files_analyzed': parsed_diff['total_files'],
            'lines_changed': parsed_diff['total_additions'] + parsed_diff['total_deletions'],
            'languages': parsed_diff['languages'],
            'analysis_time_seconds': round(time.time() - start_time, 3)
        })
        
        logger.info(f"LLM code analysis completed: {analysis_result.get('total_findings', 0)} findings")
        return analysis_result
        
    except LLMCodeReviewError as e:
        logger.error(f"LLM code review error: {e}")
        return {
            'status': 'error',
            'error_type': 'code_review_error',
            'message': str(e),
            'analysis_time_seconds': round(time.time() - start_time, 3)
        }
    except Exception as e:
        logger.error(f"Unexpected error in LLM code analysis: {e}", exc_info=True)
        return {
            'status': 'error',
            'error_type': 'internal_error',
            'message': f"Code analysis failed: {str(e)}",
            'analysis_time_seconds': round(time.time() - start_time, 3)
        }


# Utility functions for testing and validation
def test_diff_fetcher():
    """Test the diff fetcher with a sample PR"""
    test_diff_url = "https://github.com/mohdalikm/test-repo/pull/1.diff"
    
    fetcher = DiffFetcher()
    try:
        diff_content = fetcher.fetch_pr_diff(test_diff_url)
        parsed = fetcher.parse_diff(diff_content)
        
        print(f"Fetched diff with {len(diff_content)} characters")
        print(f"Parsed {parsed['total_files']} files")
        print(f"Languages: {parsed['languages']}")
        print(f"Changes: +{parsed['total_additions']} -{parsed['total_deletions']}")
        
        return parsed
    except Exception as e:
        print(f"Test failed: {e}")
        return None


def test_llm_analysis():
    """Test LLM analysis with sample code"""
    sample_diff = """diff --git a/app.py b/app.py
index 1234567..abcdefg 100644
--- a/app.py
+++ b/app.py
@@ -10,6 +10,10 @@ def process_user_input(user_input):
     # Process user input
     query = request.args.get('query')
     
+    # Execute SQL query directly
+    cursor.execute(f"SELECT * FROM users WHERE name = '{query}'")
+    results = cursor.fetchall()
+    
     return render_template('results.html', data=results)
"""
    
    parsed_diff = {
        'files_changed': [
            {
                'old_path': 'app.py',
                'new_path': 'app.py',
                'changes': ['+    cursor.execute(f"SELECT * FROM users WHERE name = \'{query}\'")'],
                'additions': 3,
                'deletions': 0,
                'language': 'Python'
            }
        ],
        'total_files': 1,
        'total_additions': 3,
        'total_deletions': 0,
        'languages': ['Python'],
        'raw_diff': sample_diff
    }
    
    pr_context = {
        'title': 'Add user search functionality',
        'body': 'Implements basic user search'
    }
    
    analyzer = LLMCodeAnalyzer()
    try:
        result = analyzer.analyze_code_changes(parsed_diff, pr_context)
        print(f"Analysis completed: {result.get('total_findings', 0)} findings")
        
        for finding in result.get('findings', []):
            print(f"- {finding.get('severity', 'unknown').upper()}: {finding.get('title', 'N/A')}")
        
        return result
    except Exception as e:
        print(f"Analysis test failed: {e}")
        return None


if __name__ == "__main__":
    # Run tests when executed directly
    print("Testing LLM Code Reviewer...")
    print("=" * 50)
    
    print("\n1. Testing diff fetcher...")
    test_diff_fetcher()
    
    print("\n2. Testing LLM analysis...")
    test_llm_analysis()
    
    print("\nLLM Code Reviewer tests completed!")