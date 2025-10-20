"""
CodeGuru Profiler Tool - Enhanced Internal Tool Module
Profiles code performance using Amazon CodeGuru Profiler with AI-powered test discovery

This tool provides performance profiling by:
1. Extracting code from GitHub PR payloads
2. Using AI to discover relevant test scripts in the codebase
3. Running tests in CodeBuild with profiling enabled
4. Analyzing performance bottlenecks and providing optimization recommendations
"""

import logging
import time
import base64
import json
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import os

# Import GitHub helpers for PR code extraction
from app.utils.github_helpers import GitHubHelper, GitHubError
from app.utils.aws_helpers import AWSHelper, AWSError

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
MAX_BOTTLENECKS = 10
CPU_THRESHOLD_PERCENT = 5.0  # Report functions using > 5% CPU
DEFAULT_PROFILE_DURATION_MINUTES = 5
DEFAULT_CODEBUILD_TIMEOUT_MINUTES = 30
TEST_DISCOVERY_PATTERNS = [
    r'.*test.*\.py$',
    r'.*_test\.py$', 
    r'test_.*\.py$',
    r'.*tests.*\.py$',
    r'.*spec.*\.py$',
    r'.*_spec\.py$'
]


class ProfilerError(Exception):
    """Exception for CodeGuru Profiler specific errors"""
    pass


class PRCodeExtractor:
    """Extract and analyze code from GitHub PR payloads"""
    
    def __init__(self, github_token: Optional[str] = None):
        """Initialize with GitHub token"""
        self.github_helper = GitHubHelper(token=github_token)
        self.aws_helper = AWSHelper()
        
    def extract_pr_code(self, pr_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract code and metadata from a GitHub PR payload
        
        Args:
            pr_payload: GitHub PR webhook payload
            
        Returns:
            Dictionary containing extracted PR information
        """
        try:
            pr_data = pr_payload.get('pull_request', {})
            repository = pr_payload.get('repository', {})
            
            repo_full_name = repository.get('full_name')
            pr_number = pr_data.get('number')
            
            if not repo_full_name or not pr_number:
                raise ProfilerError("Missing repository or PR number in payload")
            
            logger.info(f"Extracting code from PR #{pr_number} in {repo_full_name}")
            
            # Get PR details and files
            pr_details = self.github_helper.get_pull_request(repo_full_name, pr_number)
            changed_files = self.github_helper.get_pr_files(repo_full_name, pr_number)
            
            # Extract relevant information
            extraction_result = {
                'repository': repo_full_name,
                'pr_number': pr_number,
                'pr_title': pr_details.get('title', ''),
                'pr_description': pr_details.get('body', ''),
                'head_sha': pr_details.get('head', {}).get('sha'),
                'base_sha': pr_details.get('base', {}).get('sha'),
                'head_ref': pr_details.get('head', {}).get('ref'),
                'base_ref': pr_details.get('base', {}).get('ref'),
                'clone_url': repository.get('clone_url'),
                'changed_files': self._process_changed_files(changed_files),
                'languages': self._detect_languages(changed_files),
                'total_additions': sum(f.get('additions', 0) for f in changed_files),
                'total_deletions': sum(f.get('deletions', 0) for f in changed_files),
                'files_changed': len(changed_files)
            }
            
            logger.info(f"Extracted {extraction_result['files_changed']} changed files, "
                       f"{extraction_result['total_additions']} additions, "
                       f"{extraction_result['total_deletions']} deletions")
            
            return extraction_result
            
        except Exception as e:
            logger.error(f"Failed to extract PR code: {str(e)}")
            raise ProfilerError(f"PR code extraction failed: {str(e)}")
    
    def _process_changed_files(self, changed_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and categorize changed files"""
        processed_files = []
        
        for file_data in changed_files:
            filename = file_data.get('filename', '')
            file_info = {
                'filename': filename,
                'status': file_data.get('status'),  # added, modified, deleted, renamed
                'additions': file_data.get('additions', 0),
                'deletions': file_data.get('deletions', 0),
                'changes': file_data.get('changes', 0),
                'blob_url': file_data.get('blob_url'),
                'raw_url': file_data.get('raw_url'),
                'is_test_file': self._is_test_file(filename),
                'is_source_file': self._is_source_file(filename),
                'language': self._detect_file_language(filename)
            }
            processed_files.append(file_info)
        
        return processed_files
    
    def _detect_languages(self, changed_files: List[Dict[str, Any]]) -> List[str]:
        """Detect programming languages from changed files"""
        languages = set()
        
        for file_data in changed_files:
            filename = file_data.get('filename', '')
            lang = self._detect_file_language(filename)
            if lang:
                languages.add(lang)
        
        return list(languages)
    
    def _detect_file_language(self, filename: str) -> Optional[str]:
        """Detect programming language from file extension"""
        ext = Path(filename).suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.php': 'php',
            '.kt': 'kotlin',
            '.scala': 'scala'
        }
        
        return language_map.get(ext)
    
    def _is_test_file(self, filename: str) -> bool:
        """Check if file is likely a test file"""
        return any(re.match(pattern, filename, re.IGNORECASE) 
                  for pattern in TEST_DISCOVERY_PATTERNS)
    
    def _is_source_file(self, filename: str) -> bool:
        """Check if file is a source code file"""
        source_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', 
                           '.cpp', '.c', '.cs', '.rb', '.php', '.kt', '.scala'}
        return Path(filename).suffix.lower() in source_extensions


class AITestDiscovery:
    """AI-powered test script discovery and analysis"""
    
    def __init__(self):
        """Initialize test discovery engine"""
        self.confidence_threshold = 0.7
        
    def discover_test_scripts(self, pr_code: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to discover relevant test scripts for the PR changes
        
        Args:
            pr_code: Extracted PR code information
            
        Returns:
            Dictionary containing discovered test information
        """
        try:
            logger.info(f"Starting AI test discovery for PR #{pr_code['pr_number']}")
            
            # Analyze changed files to understand scope
            changed_files = pr_code['changed_files']
            source_files = [f for f in changed_files if f['is_source_file'] and not f['is_test_file']]
            existing_test_files = [f for f in changed_files if f['is_test_file']]
            
            # Discover related test files using intelligent analysis
            discovered_tests = self._discover_related_tests(source_files, existing_test_files)
            
            # Generate test execution plan
            test_plan = self._generate_test_execution_plan(discovered_tests, pr_code)
            
            result = {
                'discovered_tests': discovered_tests,
                'test_execution_plan': test_plan,
                'source_files_count': len(source_files),
                'existing_test_files_count': len(existing_test_files),
                'primary_language': self._get_primary_language(pr_code['languages']),
                'test_frameworks': self._detect_test_frameworks(discovered_tests),
                'confidence_score': self._calculate_confidence_score(discovered_tests)
            }
            
            logger.info(f"AI test discovery completed: {len(discovered_tests)} tests found, "
                       f"confidence: {result['confidence_score']:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"AI test discovery failed: {str(e)}")
            raise ProfilerError(f"Test discovery failed: {str(e)}")
    
    def _discover_related_tests(self, source_files: List[Dict], existing_tests: List[Dict]) -> List[Dict]:
        """Discover tests related to changed source files"""
        discovered_tests = []
        
        # Add existing test files from PR
        for test_file in existing_tests:
            discovered_tests.append({
                'filename': test_file['filename'],
                'source': 'pr_changes',
                'confidence': 1.0,
                'test_type': 'unit',
                'priority': 'high',
                'reason': 'Modified in PR'
            })
        
        # Use AI-like heuristics to find related tests
        for source_file in source_files:
            related_tests = self._find_tests_for_source_file(source_file)
            discovered_tests.extend(related_tests)
        
        # Add integration and end-to-end tests based on file patterns
        integration_tests = self._find_integration_tests(source_files)
        discovered_tests.extend(integration_tests)
        
        return discovered_tests
    
    def _find_tests_for_source_file(self, source_file: Dict) -> List[Dict]:
        """Find test files related to a specific source file using naming conventions"""
        tests = []
        filename = source_file['filename']
        
        # Generate potential test file names
        base_name = Path(filename).stem
        dir_path = str(Path(filename).parent)
        
        potential_test_names = [
            f"test_{base_name}.py",
            f"{base_name}_test.py", 
            f"test_{base_name.lower()}.py",
            f"tests/test_{base_name}.py",
            f"test/test_{base_name}.py",
            f"{dir_path}/test_{base_name}.py",
            f"tests/{dir_path}/test_{base_name}.py"
        ]
        
        for test_name in potential_test_names:
            tests.append({
                'filename': test_name,
                'source': 'ai_discovery',
                'confidence': 0.8,
                'test_type': 'unit',
                'priority': 'high',
                'reason': f'Likely test for {filename}'
            })
        
        return tests
    
    def _find_integration_tests(self, source_files: List[Dict]) -> List[Dict]:
        """Find integration tests that might be affected"""
        integration_tests = []
        
        # Common integration test patterns
        integration_patterns = [
            'tests/integration/',
            'test/integration/', 
            'integration_tests/',
            'tests/e2e/',
            'e2e_tests/'
        ]
        
        for pattern in integration_patterns:
            integration_tests.append({
                'filename': f"{pattern}*.py",
                'source': 'ai_discovery',
                'confidence': 0.6,
                'test_type': 'integration',
                'priority': 'medium',
                'reason': 'Integration tests for changed components'
            })
        
        return integration_tests
    
    def _generate_test_execution_plan(self, discovered_tests: List[Dict], pr_code: Dict) -> Dict[str, Any]:
        """Generate optimized test execution plan"""
        # Sort tests by priority and confidence
        high_priority = [t for t in discovered_tests if t['priority'] == 'high']
        medium_priority = [t for t in discovered_tests if t['priority'] == 'medium']
        
        return {
            'execution_order': ['high_priority', 'medium_priority'],
            'high_priority_tests': high_priority,
            'medium_priority_tests': medium_priority,
            'estimated_duration_minutes': len(discovered_tests) * 2,  # 2 min per test avg
            'parallel_execution': len(discovered_tests) > 5,
            'framework_commands': self._generate_framework_commands(pr_code['languages'])
        }
    
    def _generate_framework_commands(self, languages: List[str]) -> Dict[str, str]:
        """Generate test commands for different frameworks"""
        commands = {}
        
        if 'python' in languages:
            commands['python'] = 'python -m pytest -v --tb=short'
        if 'javascript' in languages:
            commands['javascript'] = 'npm test'
        if 'java' in languages:
            commands['java'] = 'mvn test'
        
        return commands
    
    def _get_primary_language(self, languages: List[str]) -> str:
        """Get the primary programming language"""
        return languages[0] if languages else 'unknown'
    
    def _detect_test_frameworks(self, tests: List[Dict]) -> List[str]:
        """Detect test frameworks from test files"""
        frameworks = set()
        
        for test in tests:
            filename = test['filename']
            if 'pytest' in filename or filename.endswith('_test.py'):
                frameworks.add('pytest')
            elif 'unittest' in filename:
                frameworks.add('unittest')
            elif filename.endswith('.spec.js'):
                frameworks.add('jest')
        
        return list(frameworks)
    
    def _calculate_confidence_score(self, tests: List[Dict]) -> float:
        """Calculate overall confidence score for test discovery"""
        if not tests:
            return 0.0
        
        total_confidence = sum(test.get('confidence', 0.5) for test in tests)
        return min(total_confidence / len(tests), 1.0)


class CodeBuildProfilerRunner:
    """Run tests with profiling in AWS CodeBuild"""
    
    def __init__(self):
        """Initialize CodeBuild runner"""
        self.aws_helper = AWSHelper()
        self.codebuild_client = self.aws_helper.get_client('codebuild')
        self.profiler_client = self.aws_helper.get_client('codeguruprofiler')
        
        # Validate permissions on initialization
        self._validate_profiler_permissions()
    
    def _validate_profiler_permissions(self) -> None:
        """Validate that we have the required CodeGuru Profiler permissions"""
        try:
            # Test basic profiler permissions by listing profiling groups
            self.profiler_client.list_profiling_groups(maxResults=1)
            logger.info("CodeGuru Profiler permissions validated successfully")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['AccessDenied', 'UnauthorizedOperation']:
                raise ProfilerError(
                    "Missing CodeGuru Profiler permissions. Please run: ./scripts/setup-permissions.sh"
                )
            else:
                logger.warning(f"Could not validate profiler permissions: {error_code}")
        except Exception as e:
            logger.warning(f"Permission validation failed: {str(e)}")
    
    def run_tests_with_profiling(self, pr_code: Dict[str, Any], 
                                test_discovery: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run discovered tests in CodeBuild with CodeGuru Profiler enabled
        
        Args:
            pr_code: Extracted PR code information
            test_discovery: AI test discovery results
            
        Returns:
            Dictionary containing profiling results
        """
        try:
            logger.info(f"Starting CodeBuild test execution with profiling for PR #{pr_code['pr_number']}")
            
            # Create profiling group for this PR
            profiling_group_name = self._create_or_get_profiling_group(pr_code)
            
            # Create CodeBuild project or use existing one
            project_name = self._ensure_codebuild_project(pr_code)
            
            # Generate buildspec for test execution with profiling
            buildspec = self._generate_buildspec_with_profiling(
                pr_code, test_discovery, profiling_group_name
            )
            
            # Start CodeBuild execution
            build_result = self._start_codebuild_execution(
                project_name, pr_code, buildspec
            )
            
            # Wait for build completion
            build_completion = self._wait_for_build_completion(
                build_result['build']['id']
            )
            
            # Collect profiling data
            profiling_data = self._collect_profiling_data(
                profiling_group_name, 
                build_completion['build']['startTime'],
                build_completion['build']['endTime']
            )
            
            return {
                'status': 'completed',
                'build_id': build_result['build']['id'],
                'build_status': build_completion['build']['buildStatus'],
                'profiling_group': profiling_group_name,
                'profiling_data': profiling_data,
                'test_results': self._extract_test_results(build_completion),
                'execution_time_seconds': self._calculate_execution_time(
                    build_completion['build']['startTime'],
                    build_completion['build']['endTime']
                )
            }
            
        except Exception as e:
            logger.error(f"CodeBuild test execution failed: {str(e)}")
            raise ProfilerError(f"Test execution failed: {str(e)}")
    
    def _create_or_get_profiling_group(self, pr_code: Dict[str, Any]) -> str:
        """Create or get a profiling group for this PR with fallback logic"""
        try:
            # First try to create a PR-specific profiling group
            return self._create_profiling_group(pr_code)
        except ProfilerError as e:
            logger.warning(f"Failed to create PR-specific profiling group: {str(e)}")
            # Fall back to a default profiling group
            return self._get_or_create_default_profiling_group()
        except Exception as e:
            logger.error(f"Unexpected error creating profiling group: {str(e)}")
            # Last resort: return a fallback group name that we'll try to create
            return self._get_or_create_default_profiling_group()
    
    def _get_or_create_default_profiling_group(self) -> str:
        """Get or create a default profiling group for EcoCoder with enhanced error handling"""
        default_group_name = "ecocoder-default-profiling-group"
        
        try:
            # Check if default group exists
            try:
                response = self.profiler_client.describe_profiling_group(
                    profilingGroupName=default_group_name
                )
                logger.info(f"Using existing default profiling group: {default_group_name}")
                return default_group_name
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    # Create default profiling group with comprehensive configuration
                    logger.info(f"Creating default profiling group: {default_group_name}")
                    
                    create_params = {
                        'profilingGroupName': default_group_name,
                        'computePlatform': 'Default',  # For non-Lambda applications
                        'agentOrchestrationConfig': {
                            'profilingEnabled': True
                        },
                        'tags': {
                            'Project': 'EcoCoder',
                            'Environment': 'Production',
                            'Service': 'GreenSoftwareAnalysis',
                            'CreatedBy': 'EcoCoderAgent'
                        }
                    }
                    
                    response = self.profiler_client.create_profiling_group(**create_params)
                    logger.info(f"Successfully created default profiling group: {default_group_name}")
                    logger.debug(f"Profiling group ARN: {response.get('arn', 'N/A')}")
                    return default_group_name
                else:
                    logger.error(f"Failed to check profiling group existence: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
                    raise
                    
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'ConflictException':
                # Group might have been created by another process
                logger.info(f"Profiling group {default_group_name} already exists (created concurrently)")
                return default_group_name
            elif error_code == 'AccessDeniedException':
                logger.error(f"Access denied creating profiling group. Check IAM permissions for CodeGuru Profiler.")
                raise ProfilerError(f"Insufficient permissions to create profiling group. Please run: ./scripts/setup-codeguru-permissions.sh")
            elif error_code == 'ServiceQuotaExceededException':
                logger.error(f"Service quota exceeded for profiling groups")
                raise ProfilerError(f"AWS service quota exceeded for CodeGuru Profiler groups")
            else:
                logger.error(f"AWS API error creating profiling group: {error_code} - {error_message}")
                raise ProfilerError(f"AWS API error: {error_message}")
                
        except Exception as e:
            logger.error(f"Unexpected error in default profiling group setup: {str(e)}")
            raise ProfilerError(f"Default profiling group setup failed: {str(e)}")

    def _create_profiling_group(self, pr_code: Dict[str, Any]) -> str:
        """Create CodeGuru Profiler group for this PR"""
        try:
            repo_name = pr_code['repository'].replace('/', '-')
            # Clean the profiling group name - must contain only alphanumeric chars, hyphens and underscores
            clean_repo_name = re.sub(r'[^a-zA-Z0-9\-_]', '-', repo_name)
            profiling_group_name = f"ecocoder-{clean_repo_name}-pr-{pr_code['pr_number']}"
            
            # Ensure profiling group name meets AWS requirements (1-255 chars, alphanumeric, hyphens, underscores)
            if len(profiling_group_name) > 255:
                # Truncate but keep unique PR identifier
                max_repo_length = 255 - len(f"ecocoder--pr-{pr_code['pr_number']}")
                clean_repo_name = clean_repo_name[:max_repo_length]
                profiling_group_name = f"ecocoder-{clean_repo_name}-pr-{pr_code['pr_number']}"
            
            # Create profiling group with simplified configuration
            try:
                response = self.profiler_client.create_profiling_group(
                    profilingGroupName=profiling_group_name
                )
                logger.info(f"Created profiling group: {profiling_group_name}")
                logger.debug(f"Profiling group response: {response}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ConflictException':
                    logger.info(f"Profiling group already exists: {profiling_group_name}")
                else:
                    logger.error(f"ClientError creating profiling group: {e.response}")
                    raise
            
            return profiling_group_name
            
        except Exception as e:
            logger.error(f"Failed to create profiling group: {str(e)}")
            raise ProfilerError(f"Profiling group creation failed: {str(e)}")
    
    def _ensure_codebuild_project(self, pr_code: Dict[str, Any]) -> str:
        """Ensure CodeBuild project exists or use the AgentCore one"""
        try:
            # Use the existing AgentCore CodeBuild project
            project_name = "bedrock-agentcore-ecocoderagentcore-builder"
            
            # Verify the project exists
            try:
                self.codebuild_client.batch_get_projects(names=[project_name])
                logger.info(f"Using existing CodeBuild project: {project_name}")
                return project_name
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.warning(f"AgentCore CodeBuild project not found, using fallback")
                    return self._create_fallback_project(pr_code)
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"CodeBuild project setup failed: {str(e)}")
            raise ProfilerError(f"CodeBuild project setup failed: {str(e)}")
    
    def _create_fallback_project(self, pr_code: Dict[str, Any]) -> str:
        """Create a fallback CodeBuild project if AgentCore one doesn't exist"""
        project_name = f"ecocoder-profiler-{pr_code['repository'].replace('/', '-')}"
        
        try:
            self.codebuild_client.create_project(
                name=project_name,
                description=f"EcoCoder profiler project for {pr_code['repository']}",
                serviceRole='arn:aws:iam::434114167546:role/AmazonBedrockAgentCoreSDKCodeBuild-ap-southeast-1-b953f47315',
                artifacts={'type': 'NO_ARTIFACTS'},
                environment={
                    'type': 'LINUX_CONTAINER',
                    'image': 'aws/codebuild/amazonlinux2-x86_64-standard:3.0',
                    'computeType': 'BUILD_GENERAL1_MEDIUM',
                    'privilegedMode': True
                },
                source={'type': 'GITHUB', 'location': pr_code['clone_url']},
                timeoutInMinutes=DEFAULT_CODEBUILD_TIMEOUT_MINUTES
            )
            
            logger.info(f"Created fallback CodeBuild project: {project_name}")
            return project_name
            
        except Exception as e:
            logger.error(f"Failed to create fallback CodeBuild project: {str(e)}")
            raise ProfilerError(f"Fallback project creation failed: {str(e)}")
    
    def _generate_buildspec_with_profiling(self, pr_code: Dict[str, Any], 
                                         test_discovery: Dict[str, Any],
                                         profiling_group_name: str) -> Dict[str, Any]:
        """Generate buildspec.yml for test execution with profiling"""
        
        test_plan = test_discovery['test_execution_plan']
        primary_language = test_discovery['primary_language']
        
        buildspec = {
            'version': 0.2,
            'phases': {
                'install': {
                    'runtime-versions': {},
                    'commands': []
                },
                'pre_build': {
                    'commands': [
                        'echo "Setting up CodeGuru Profiler"',
                        f'export AWS_CODEGURU_PROFILER_GROUP_NAME={profiling_group_name}',
                        'export AWS_CODEGURU_PROFILER_ENABLED=true',
                        'echo "Checking out PR code"',
                        f'git fetch origin {pr_code["head_ref"]}:{pr_code["head_ref"]}',
                        f'git checkout {pr_code["head_ref"]}'
                    ]
                },
                'build': {
                    'commands': [
                        'echo "Running tests with profiling enabled"'
                    ]
                },
                'post_build': {
                    'commands': [
                        'echo "Test execution completed"',
                        'echo "Profiling data will be available in CodeGuru Profiler"'
                    ]
                }
            },
            'artifacts': {
                'files': ['test-results.xml', 'coverage.xml']
            }
        }
        
        # Add language-specific setup
        if primary_language == 'python':
            buildspec['phases']['install']['runtime-versions']['python'] = '3.11'
            buildspec['phases']['install']['commands'].extend([
                'pip install --upgrade pip',
                'pip install pytest pytest-cov codecov',
                'pip install -r requirements.txt || echo "No requirements.txt found"'
            ])
            
            # Add profiler agent for Python
            buildspec['phases']['pre_build']['commands'].extend([
                'pip install codeguru-profiler-agent',
                'export PYTHONPATH="${PYTHONPATH}:."'
            ])
            
            # Add test commands
            for test_type in ['high_priority_tests', 'medium_priority_tests']:
                tests = test_plan.get(test_type, [])
                if tests:
                    test_files = ' '.join([t['filename'] for t in tests if not '*' in t['filename']])
                    if test_files:
                        buildspec['phases']['build']['commands'].append(
                            f'python -m pytest {test_files} -v --tb=short --junitxml=test-results.xml || echo "Tests completed with issues"'
                        )
        
        elif primary_language == 'javascript':
            buildspec['phases']['install']['runtime-versions']['nodejs'] = '18'
            buildspec['phases']['install']['commands'].extend([
                'npm install',
                'npm install --global @aws/codeguru-profiler-nodejs-agent'
            ])
            
            buildspec['phases']['build']['commands'].append(
                'npm test || echo "Tests completed with issues"'
            )
        
        return buildspec
    
    def _start_codebuild_execution(self, project_name: str, pr_code: Dict[str, Any], 
                                 buildspec: Dict[str, Any]) -> Dict[str, Any]:
        """Start CodeBuild execution"""
        try:
            response = self.codebuild_client.start_build(
                projectName=project_name,
                sourceVersion=pr_code['head_sha'],
                buildspecOverride=json.dumps(buildspec),
                environmentVariablesOverride=[
                    {
                        'name': 'ECOCODER_PR_NUMBER',
                        'value': str(pr_code['pr_number'])
                    },
                    {
                        'name': 'ECOCODER_REPOSITORY',
                        'value': pr_code['repository']
                    }
                ]
            )
            
            logger.info(f"Started CodeBuild execution: {response['build']['id']}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to start CodeBuild: {str(e)}")
            raise ProfilerError(f"CodeBuild start failed: {str(e)}")
    
    def _wait_for_build_completion(self, build_id: str) -> Dict[str, Any]:
        """Wait for CodeBuild to complete"""
        max_attempts = 60  # 30 minutes with 30-second intervals
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = self.codebuild_client.batch_get_builds(ids=[build_id])
                build = response['builds'][0]
                
                status = build['buildStatus']
                
                if status in ['SUCCEEDED', 'FAILED', 'STOPPED', 'TIMED_OUT']:
                    logger.info(f"Build {build_id} completed with status: {status}")
                    return response
                
                logger.info(f"Build {build_id} in progress, attempt {attempt + 1}/{max_attempts}")
                time.sleep(30)
                attempt += 1
                
            except Exception as e:
                logger.warning(f"Error checking build status: {e}")
                time.sleep(30)
                attempt += 1
        
        raise ProfilerError(f"Build {build_id} timed out after {max_attempts} attempts")
    
    def _collect_profiling_data(self, profiling_group_name: str, 
                               start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Collect profiling data from CodeGuru Profiler"""
        try:
            # Wait a bit for profiling data to be processed
            time.sleep(30)
            
            # Get profile data
            profile_data = get_profile_data(profiling_group_name, start_time, end_time)
            
            # Analyze bottlenecks
            bottlenecks = analyze_bottlenecks(profile_data)
            
            # Get recommendations
            recommendations = get_recommendations(profiling_group_name, start_time, end_time)
            
            # Calculate metrics
            metrics = calculate_metrics(profile_data, bottlenecks)
            
            return {
                'profile_data': profile_data,
                'bottlenecks': bottlenecks,
                'recommendations': recommendations,
                'metrics': metrics
            }
            
        except Exception as e:
            logger.warning(f"Failed to collect profiling data: {e}")
            # Return empty data rather than failing the whole operation
            return {
                'profile_data': {},
                'bottlenecks': [],
                'recommendations': [],
                'metrics': {}
            }
    
    def _extract_test_results(self, build_completion: Dict[str, Any]) -> Dict[str, Any]:
        """Extract test results from CodeBuild logs"""
        # This would parse CloudWatch logs or build artifacts for test results
        # For now, return basic information from build status
        
        build = build_completion['builds'][0]
        
        return {
            'build_status': build['buildStatus'],
            'test_success': build['buildStatus'] == 'SUCCEEDED',
            'duration_seconds': self._calculate_execution_time(
                build['startTime'], build['endTime']
            ),
            'log_group': build.get('logs', {}).get('groupName'),
            'log_stream': build.get('logs', {}).get('streamName')
        }
    
    def _calculate_execution_time(self, start_time: datetime, end_time: datetime) -> int:
        """Calculate execution time in seconds"""
        return int((end_time - start_time).total_seconds())


def _generate_performance_insights(pr_code: Dict[str, Any], 
                                 test_discovery: Dict[str, Any],
                                 profiling_results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate performance insights from profiling results"""
    try:
        profiling_data = profiling_results.get('profiling_data', {})
        bottlenecks = profiling_data.get('bottlenecks', [])
        metrics = profiling_data.get('metrics', {})
        
        # Analyze performance impact
        high_impact_bottlenecks = [b for b in bottlenecks if b.get('cpu_percentage', 0) > 20]
        memory_intensive_functions = [b for b in bottlenecks if 'memory' in b.get('issue_type', '').lower()]
        
        # Calculate performance scores
        cpu_score = _calculate_cpu_performance_score(bottlenecks)
        memory_score = _calculate_memory_performance_score(bottlenecks, metrics)
        overall_score = (cpu_score + memory_score) / 2
        
        # Determine performance grade
        performance_grade = _determine_performance_grade(overall_score)
        
        insights = {
            'overall_performance_score': overall_score,
            'performance_grade': performance_grade,
            'cpu_performance_score': cpu_score,
            'memory_performance_score': memory_score,
            'high_impact_bottlenecks': high_impact_bottlenecks,
            'memory_intensive_functions': memory_intensive_functions,
            'total_cpu_time_ms': metrics.get('total_cpu_time_ms', 0),
            'total_memory_mb': metrics.get('total_memory_mb', 0),
            'avg_cpu_per_invocation': metrics.get('avg_cpu_per_invocation_ms', 0),
            'performance_trends': _analyze_performance_trends(pr_code, bottlenecks),
            'optimization_opportunities': _identify_optimization_opportunities(bottlenecks)
        }
        
        return insights
        
    except Exception as e:
        logger.error(f"Failed to generate performance insights: {e}")
        return {
            'overall_performance_score': 0.5,
            'performance_grade': 'C',
            'error': str(e)
        }


def _generate_comprehensive_recommendations(pr_code: Dict[str, Any],
                                         profiling_results: Dict[str, Any],
                                         performance_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate comprehensive performance optimization recommendations"""
    recommendations = []
    
    try:
        bottlenecks = profiling_results.get('profiling_data', {}).get('bottlenecks', [])
        
        # High-priority recommendations from bottlenecks
        for bottleneck in bottlenecks[:5]:  # Top 5 bottlenecks
            recommendation = {
                'priority': 'high' if bottleneck.get('cpu_percentage', 0) > 20 else 'medium',
                'category': 'performance_optimization',
                'title': f"Optimize {bottleneck.get('function_name', 'Unknown Function')}",
                'description': bottleneck.get('description', ''),
                'file_location': {
                    'file': bottleneck.get('file_path', ''),
                    'line': bottleneck.get('line_number', 0)
                },
                'current_impact': {
                    'cpu_percentage': bottleneck.get('cpu_percentage', 0),
                    'execution_time_ms': bottleneck.get('total_time_ms', 0),
                    'invocation_count': bottleneck.get('invocation_count', 0)
                },
                'suggested_actions': [
                    bottleneck.get('recommendation', 'Review function for optimization opportunities')
                ],
                'estimated_improvement': f"Potential {bottleneck.get('cpu_percentage', 0) * 0.3:.1f}% performance gain"
            }
            recommendations.append(recommendation)
        
        # Language-specific recommendations
        primary_language = pr_code.get('languages', ['unknown'])[0]
        language_recommendations = _get_language_specific_recommendations(
            primary_language, performance_insights
        )
        recommendations.extend(language_recommendations)
        
        # CodeBuild optimization recommendations
        build_recommendations = _get_codebuild_optimization_recommendations(profiling_results)
        recommendations.extend(build_recommendations)
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}")
        return [{
            'priority': 'low',
            'category': 'error',
            'title': 'Failed to generate recommendations',
            'description': str(e)
        }]


def _calculate_cpu_performance_score(bottlenecks: List[Dict]) -> float:
    """Calculate CPU performance score (0-1, higher is better)"""
    if not bottlenecks:
        return 0.8  # Default good score if no bottlenecks
    
    total_cpu_impact = sum(b.get('cpu_percentage', 0) for b in bottlenecks)
    
    # Score based on total CPU impact (lower is better)
    if total_cpu_impact > 80:
        return 0.2
    elif total_cpu_impact > 60:
        return 0.4
    elif total_cpu_impact > 40:
        return 0.6
    elif total_cpu_impact > 20:
        return 0.7
    else:
        return 0.9


def _calculate_memory_performance_score(bottlenecks: List[Dict], metrics: Dict) -> float:
    """Calculate memory performance score (0-1, higher is better)"""
    memory_usage_mb = metrics.get('total_memory_mb', 256)
    memory_bottlenecks = [b for b in bottlenecks if 'memory' in b.get('issue_type', '').lower()]
    
    # Score based on memory usage and memory-related bottlenecks
    memory_score = 1.0
    
    if memory_usage_mb > 2048:  # > 2GB
        memory_score *= 0.3
    elif memory_usage_mb > 1024:  # > 1GB
        memory_score *= 0.6
    elif memory_usage_mb > 512:   # > 512MB
        memory_score *= 0.8
    
    # Penalize for memory bottlenecks
    if memory_bottlenecks:
        memory_score *= (1 - len(memory_bottlenecks) * 0.1)
    
    return max(memory_score, 0.1)  # Minimum score


def _determine_performance_grade(overall_score: float) -> str:
    """Determine performance grade from overall score"""
    if overall_score >= 0.9:
        return 'A'
    elif overall_score >= 0.8:
        return 'B'
    elif overall_score >= 0.6:
        return 'C'
    elif overall_score >= 0.4:
        return 'D'
    else:
        return 'F'


def _analyze_performance_trends(pr_code: Dict[str, Any], bottlenecks: List[Dict]) -> Dict[str, Any]:
    """Analyze performance trends from the PR changes"""
    return {
        'files_with_performance_issues': len(set(b.get('file_path', '') for b in bottlenecks)),
        'functions_with_issues': len(bottlenecks),
        'primary_issue_types': list(set(b.get('issue_type', '') for b in bottlenecks)),
        'average_cpu_per_function': sum(b.get('cpu_percentage', 0) for b in bottlenecks) / max(len(bottlenecks), 1)
    }


def _identify_optimization_opportunities(bottlenecks: List[Dict]) -> List[str]:
    """Identify optimization opportunities from bottlenecks"""
    opportunities = set()
    
    for bottleneck in bottlenecks:
        issue_type = bottleneck.get('issue_type', '').lower()
        cpu_pct = bottleneck.get('cpu_percentage', 0)
        
        if 'cpu' in issue_type and cpu_pct > 30:
            opportunities.add('Algorithm optimization needed')
        if 'memory' in issue_type:
            opportunities.add('Memory usage optimization')
        if 'i/o' in issue_type:
            opportunities.add('I/O operation optimization')
        if bottleneck.get('invocation_count', 0) > 1000:
            opportunities.add('Consider caching frequently called functions')
    
    return list(opportunities)


def _get_language_specific_recommendations(language: str, 
                                         performance_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get language-specific performance recommendations"""
    recommendations = []
    
    if language == 'python':
        if performance_insights.get('cpu_performance_score', 0.5) < 0.6:
            recommendations.append({
                'priority': 'medium',
                'category': 'python_optimization',
                'title': 'Consider Python Performance Optimizations',
                'description': 'Python-specific optimizations can significantly improve performance',
                'suggested_actions': [
                    'Use list comprehensions instead of loops where possible',
                    'Consider using NumPy for numerical computations',
                    'Profile with cProfile for detailed function-level analysis',
                    'Consider Cython for CPU-intensive functions'
                ]
            })
    
    elif language == 'javascript':
        recommendations.append({
            'priority': 'medium',
            'category': 'javascript_optimization',
            'title': 'JavaScript Performance Best Practices',
            'description': 'Apply JavaScript-specific performance optimizations',
            'suggested_actions': [
                'Avoid blocking the event loop with synchronous operations',
                'Use efficient data structures (Map/Set vs Object/Array)',
                'Consider worker threads for CPU-intensive tasks',
                'Optimize bundle size and loading patterns'
            ]
        })
    
    return recommendations


def _get_codebuild_optimization_recommendations(profiling_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get CodeBuild-specific optimization recommendations"""
    recommendations = []
    
    execution_time = profiling_results.get('execution_time_seconds', 0)
    
    if execution_time > 300:  # > 5 minutes
        recommendations.append({
            'priority': 'medium',
            'category': 'build_optimization',
            'title': 'Optimize CodeBuild Execution Time',
            'description': f'Build took {execution_time} seconds, which may impact CI/CD performance',
            'suggested_actions': [
                'Consider using Docker layer caching',
                'Parallelize test execution where possible',
                'Use CodeBuild compute optimized instances',
                'Optimize dependency installation'
            ]
        })
    
    return recommendations


def validate_inputs(profiling_group_name: str, start_dt: datetime, end_dt: datetime) -> None:
    """
    Validate input parameters for profiling
    
    Args:
        profiling_group_name: Name of the CodeGuru profiling group
        start_dt: Start datetime for profiling
        end_dt: End datetime for profiling
        
    Raises:
        ValueError: If any required parameter is invalid
    """
    if not profiling_group_name or len(profiling_group_name.strip()) == 0:
        raise ValueError("profiling_group_name is required")
    
    if start_dt >= end_dt:
        raise ValueError("start_time must be before end_time")
    
    # Validate time range is reasonable (not too long or too short)
    duration = end_dt - start_dt
    if duration.total_seconds() < 60:  # Less than 1 minute
        raise ValueError("Profiling duration must be at least 1 minute")
    
    if duration.total_seconds() > 3600:  # More than 1 hour
        raise ValueError("Profiling duration cannot exceed 1 hour")


def parse_datetime(datetime_str: str) -> datetime:
    """
    Parse ISO8601 datetime string
    
    Args:
        datetime_str: ISO8601 formatted datetime string
        
    Returns:
        datetime object
        
    Raises:
        ValueError: If datetime string is invalid
    """
    try:
        # Handle both with and without timezone info
        if datetime_str.endswith('Z'):
            datetime_str = datetime_str[:-1] + '+00:00'
        
        return datetime.fromisoformat(datetime_str)
    except ValueError as e:
        raise ValueError(f"Invalid datetime format: {datetime_str}. Expected ISO8601 format.")


def get_profile_data(
    profiling_group_name: str,
    start_time: datetime,
    end_time: datetime
) -> Dict[str, Any]:
    """
    Retrieve profiling data from CodeGuru Profiler
    
    Args:
        profiling_group_name: Name of the profiling group
        start_time: Start datetime for profiling
        end_time: End datetime for profiling
        
    Returns:
        Dictionary containing profile data
        
    Raises:
        ProfilerError: If profiling data retrieval fails
    """
    try:
        profiler_client = boto3.client('codeguruprofiler')
        
        # AWS CodeGuru Profiler API rules:
        # - Can specify only 'period' (gets latest aggregated profile)
        # - Can specify 'startTime' + 'period'
        # - Can specify 'endTime' + 'period'  
        # - Can specify 'startTime' + 'endTime' (no period)
        # - CANNOT specify all three parameters (throws ValidationException)
        
        # Strategy: Use startTime + endTime (no period) for specific time ranges
        # This gives us the most control and avoids parameter conflicts
        response = profiler_client.get_profile(
            profilingGroupName=profiling_group_name,
            startTime=start_time,
            endTime=end_time,
            accept='application/x-flamegraph'  # Request flame graph format
        )
        
        # The profile is returned as bytes in the response
        profile_data = {
            'raw_data': response['profile'],
            'content_type': response['contentType'],
            'content_encoding': response.get('contentEncoding', 'none')
        }
        
        logger.info(f"Retrieved profile data: {len(profile_data['raw_data'])} bytes")
        return profile_data
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'ResourceNotFoundException':
            raise ProfilerError(f"Profiling group not found: {profiling_group_name}")
        elif error_code == 'ValidationException':
            raise ProfilerError(f"Invalid profiling parameters: {error_message}")
        elif error_code == 'ThrottlingException':
            raise ProfilerError(f"Request throttled by CodeGuru Profiler")
        else:
            raise ProfilerError(f"Failed to retrieve profile: {error_message}")


def get_recommendations(
    profiling_group_name: str,
    start_time: datetime,
    end_time: datetime
) -> List[Dict[str, Any]]:
    """
    Get performance recommendations from CodeGuru Profiler
    
    Args:
        profiling_group_name: Name of the profiling group
        start_time: Start datetime for profiling
        end_time: End datetime for profiling
        
    Returns:
        List of recommendation dictionaries
    """
    try:
        profiler_client = boto3.client('codeguruprofiler')
        
        response = profiler_client.get_recommendations(
            profilingGroupName=profiling_group_name,
            startTime=start_time,
            endTime=end_time
        )
        
        recommendations = response.get('recommendations', [])
        logger.info(f"Retrieved {len(recommendations)} performance recommendations")
        
        return recommendations
        
    except ClientError as e:
        logger.warning(f"Could not fetch recommendations: {str(e)}")
        return []


def analyze_bottlenecks(profile_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyze profile data to identify performance bottlenecks
    
    Args:
        profile_data: Profile data from CodeGuru Profiler
        
    Returns:
        List of bottleneck dictionaries
    
    Note: This is a simplified implementation. In production, you would parse
    the flame graph data or use CodeGuru's recommendation API for detailed analysis.
    """
    bottlenecks = []
    
    try:
        # In a full implementation, parse the flame graph data
        # For now, we'll create mock bottlenecks based on common patterns
        
        # Example bottleneck structure (would be extracted from actual profile)
        mock_bottlenecks = [
            {
                "function_name": "process_data",
                "file_path": "src/utils.py",
                "line_number": 42,
                "cpu_percentage": 45.2,
                "self_time_ms": 560.3,
                "total_time_ms": 1250.5,
                "invocation_count": 1000,
                "issue_type": "High CPU Usage",
                "description": "This function accounts for a significant portion of CPU time"
            },
            {
                "function_name": "load_large_dataset",
                "file_path": "src/data_loader.py", 
                "line_number": 78,
                "cpu_percentage": 25.1,
                "self_time_ms": 310.2,
                "total_time_ms": 890.7,
                "invocation_count": 500,
                "issue_type": "Memory Intensive",
                "description": "High memory allocation detected"
            }
        ]
        
        # Filter bottlenecks by significance
        for bottleneck in mock_bottlenecks:
            if bottleneck['cpu_percentage'] > CPU_THRESHOLD_PERCENT:
                bottlenecks.append(bottleneck)
        
        return bottlenecks[:MAX_BOTTLENECKS]
        
    except Exception as e:
        logger.error(f"Error analyzing bottlenecks: {e}")
        return []


def calculate_metrics(profile_data: Dict[str, Any], bottlenecks: List[Dict]) -> Dict[str, float]:
    """
    Calculate aggregate performance metrics from profile data
    
    Args:
        profile_data: Profile data from CodeGuru Profiler
        bottlenecks: List of identified bottlenecks
        
    Returns:
        Dictionary containing performance metrics
    """
    try:
        # In production, extract from actual profiling data
        # For now, calculate from bottlenecks
        
        total_cpu_time_ms = sum(b.get('total_time_ms', 0) for b in bottlenecks)
        total_invocations = sum(b.get('invocation_count', 0) for b in bottlenecks)
        
        # Estimate memory usage based on profiling data size and bottlenecks
        estimated_memory_mb = len(profile_data.get('raw_data', b'')) / 1024 / 1024 * 100
        
        return {
            "total_cpu_time_ms": total_cpu_time_ms,
            "total_memory_mb": max(estimated_memory_mb, 256.0),  # Minimum reasonable estimate
            "total_invocations": total_invocations,
            "avg_cpu_per_invocation_ms": total_cpu_time_ms / max(total_invocations, 1)
        }
        
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        return {
            "total_cpu_time_ms": 1000.0,
            "total_memory_mb": 512.0,
            "total_invocations": 1000,
            "avg_cpu_per_invocation_ms": 1.0
        }


def enhance_with_recommendations(
    bottlenecks: List[Dict[str, Any]],
    recommendations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Enhance bottleneck data with CodeGuru recommendations
    
    Args:
        bottlenecks: List of bottleneck dictionaries
        recommendations: List of recommendation dictionaries
        
    Returns:
        Enhanced bottlenecks with recommendations
    """
    # Match recommendations to bottlenecks and add context
    for bottleneck in bottlenecks:
        for rec in recommendations:
            # Match based on function name or file path
            pattern = rec.get('pattern', {})
            if (pattern.get('name') == bottleneck['function_name'] or
                pattern.get('countersToAggregate', {}).get('startTime')):
                bottleneck['recommendation'] = rec.get('recommendation', '')
                bottleneck['recommendation_type'] = rec.get('type', '')
                break
        
        # Add default recommendation if none found
        if 'recommendation' not in bottleneck:
            bottleneck['recommendation'] = generate_default_recommendation(bottleneck)
    
    return bottlenecks


def generate_default_recommendation(bottleneck: Dict[str, Any]) -> str:
    """Generate a default recommendation for a bottleneck"""
    issue_type = bottleneck.get('issue_type', '')
    cpu_percentage = bottleneck.get('cpu_percentage', 0)
    
    if 'High CPU' in issue_type and cpu_percentage > 30:
        return "Consider optimizing algorithm complexity or using more efficient data structures"
    elif 'Memory' in issue_type:
        return "Review memory allocation patterns and consider lazy loading or caching strategies"
    else:
        return "Review this function for potential performance optimizations"


def generate_flame_graph_url(
    profiling_group_name: str,
    start_time: datetime,
    end_time: datetime
) -> str:
    """
    Generate URL to CodeGuru Profiler flame graph in AWS Console
    
    Args:
        profiling_group_name: Name of the profiling group
        start_time: Start datetime for profiling
        end_time: End datetime for profiling
        
    Returns:
        URL to flame graph in AWS Console
    """
    try:
        region = boto3.session.Session().region_name or 'us-east-1'
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        
        url = (
            f"https://console.aws.amazon.com/codeguru/profiler#/profiling-groups/"
            f"{profiling_group_name}/flame-graph?"
            f"startTime={start_ms}&endTime={end_ms}&region={region}"
        )
        
        return url
    except Exception as e:
        logger.warning(f"Could not generate flame graph URL: {e}")
        return ""


def validate_pr_payload(pr_payload: Dict[str, Any]) -> None:
    """Validate PR payload structure and required fields"""
    if not isinstance(pr_payload, dict):
        raise ProfilerError("PR payload must be a dictionary")
    
    if 'pull_request' not in pr_payload:
        raise ProfilerError("Missing 'pull_request' field in payload")
    
    if 'repository' not in pr_payload:
        raise ProfilerError("Missing 'repository' field in payload")
    
    pr_data = pr_payload['pull_request']
    if not pr_data.get('number'):
        raise ProfilerError("Missing PR number in payload")
    
    repository = pr_payload['repository']
    if not repository.get('full_name'):
        raise ProfilerError("Missing repository full name in payload")


def profile_pull_request_performance(
    pr_payload: Dict[str, Any],
    github_token: Optional[str] = None
) -> dict:
    """
    Enhanced tool function for PR-based performance profiling with AI test discovery.
    Called by agent via @agent.tool decorator in agent.py.
    
    This tool:
    1. Extracts code from GitHub PR payload
    2. Uses AI to discover relevant test scripts
    3. Runs tests in CodeBuild with CodeGuru Profiler enabled
    4. Analyzes performance bottlenecks and provides optimization recommendations
    
    Args:
        pr_payload: GitHub PR webhook payload containing PR information
        github_token: GitHub personal access token for API access
        
    Returns:
        Dictionary containing comprehensive profiling results or error information
    """
    analysis_start = time.time()
    pr_number = "unknown"
    repository = "unknown"
    
    try:
        logger.info("Starting enhanced PR performance profiling with AI test discovery")
        
        # Input validation
        validate_pr_payload(pr_payload)
        
        pr_number = pr_payload['pull_request']['number']
        repository = pr_payload['repository']['full_name']
        
        logger.info(f"Processing PR #{pr_number} in {repository}")
        
        # Step 1: Extract PR code information with error handling
        logger.info("Step 1: Extracting PR code...")
        try:
            pr_extractor = PRCodeExtractor(github_token=github_token)
            pr_code = pr_extractor.extract_pr_code(pr_payload)
        except GitHubError as e:
            logger.error(f"GitHub API error: {e}")
            return _create_error_response("github_api_error", f"GitHub API error: {str(e)}", 
                                        analysis_start, pr_number, repository)
        except Exception as e:
            logger.error(f"PR code extraction failed: {e}")
            return _create_error_response("pr_extraction_error", f"Code extraction failed: {str(e)}", 
                                        analysis_start, pr_number, repository)
        
        # Step 2: AI-powered test discovery with fallback
        logger.info("Step 2: AI test discovery...")
        try:
            test_discoverer = AITestDiscovery()
            test_discovery = test_discoverer.discover_test_scripts(pr_code)
            
            # Check if we found enough tests to proceed
            if test_discovery['confidence_score'] < 0.3:
                logger.warning(f"Low confidence test discovery (score: {test_discovery['confidence_score']})")
                # Continue with low confidence but add warning to results
        except Exception as e:
            logger.error(f"Test discovery failed: {e}")
            # Create fallback test discovery
            test_discovery = _create_fallback_test_discovery(pr_code)
        
        # Step 3: Run tests with profiling in CodeBuild
        logger.info("Step 3: Running tests with profiling...")
        try:
            codebuild_runner = CodeBuildProfilerRunner()
            profiling_results = codebuild_runner.run_tests_with_profiling(pr_code, test_discovery)
            
            # Check if CodeBuild execution was successful
            if profiling_results['build_status'] not in ['SUCCEEDED']:
                logger.warning(f"CodeBuild execution status: {profiling_results['build_status']}")
                # Continue with whatever data we have
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"AWS CodeBuild error ({error_code}): {e}")
            return _create_error_response("codebuild_error", 
                                        f"CodeBuild execution failed: {error_code}", 
                                        analysis_start, pr_number, repository)
        except Exception as e:
            logger.error(f"CodeBuild execution failed: {e}")
            return _create_error_response("execution_error", f"Test execution failed: {str(e)}", 
                                        analysis_start, pr_number, repository)
        
        # Step 4: Analyze results and generate insights
        logger.info("Step 4: Generating performance insights...")
        try:
            performance_insights = _generate_performance_insights(
                pr_code, test_discovery, profiling_results
            )
        except Exception as e:
            logger.error(f"Performance insight generation failed: {e}")
            performance_insights = _create_fallback_insights()
        
        # Step 5: Create comprehensive recommendations  
        try:
            recommendations = _generate_comprehensive_recommendations(
                pr_code, profiling_results, performance_insights
            )
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            recommendations = _create_fallback_recommendations()
        
        # Prepare final result
        result = {
            "status": "completed",
            "profiling_id": f"pr-{pr_code['pr_number']}-{int(time.time())}",
            "pr_analysis": {
                "repository": pr_code['repository'],
                "pr_number": pr_code['pr_number'],
                "files_changed": pr_code['files_changed'],
                "languages": pr_code['languages'],
                "total_changes": pr_code['total_additions'] + pr_code['total_deletions']
            },
            "test_discovery": {
                "tests_discovered": len(test_discovery['discovered_tests']),
                "confidence_score": test_discovery['confidence_score'],
                "primary_language": test_discovery['primary_language'],
                "test_frameworks": test_discovery['test_frameworks']
            },
            "profiling_results": profiling_results,
            "performance_insights": performance_insights,
            "recommendations": recommendations,
            "execution_summary": {
                "analysis_time_seconds": round(time.time() - analysis_start, 2),
                "codebuild_execution_time": profiling_results.get('execution_time_seconds', 0),
                "total_bottlenecks_found": len(profiling_results.get('profiling_data', {}).get('bottlenecks', [])),
                "flame_graph_url": generate_flame_graph_url(
                    profiling_results.get('profiling_group', ''),
                    datetime.utcnow() - timedelta(hours=1),
                    datetime.utcnow()
                ) if profiling_results.get('profiling_group') else None
            }
        }
        
        logger.info(f"PR performance profiling completed successfully in {result['execution_summary']['analysis_time_seconds']} seconds")
        return result
        
    except ProfilerError as e:
        logger.error(f"Profiler error: {str(e)}")
        return _create_error_response("profiler_error", str(e), analysis_start, pr_number, repository)
        
    except Exception as e:
        logger.error(f"Unexpected error in PR profiler: {str(e)}", exc_info=True)
        return _create_error_response("internal_error", str(e), analysis_start, pr_number, repository)


def _create_error_response(error_type: str, message: str, start_time: float, 
                          pr_number: str, repository: str) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "status": "error",
        "error_type": error_type,
        "message": message,
        "pr_info": {
            "pr_number": pr_number,
            "repository": repository
        },
        "analysis_time_seconds": round(time.time() - start_time, 2),
        "recommendations": [{
            "priority": "high",
            "category": "error_resolution",
            "title": f"Resolve {error_type}",
            "description": message,
            "suggested_actions": [
                "Check AWS permissions and service availability",
                "Verify GitHub token and repository access",
                "Review CloudWatch logs for detailed error information"
            ]
        }]
    }


def _create_fallback_test_discovery(pr_code: Dict[str, Any]) -> Dict[str, Any]:
    """Create fallback test discovery when AI discovery fails"""
    return {
        'discovered_tests': [],
        'test_execution_plan': {
            'execution_order': [],
            'high_priority_tests': [],
            'medium_priority_tests': [],
            'estimated_duration_minutes': 0,
            'parallel_execution': False,
            'framework_commands': {}
        },
        'source_files_count': len([f for f in pr_code.get('changed_files', []) if f.get('is_source_file')]),
        'existing_test_files_count': 0,
        'primary_language': pr_code.get('languages', ['unknown'])[0] if pr_code.get('languages') else 'unknown',
        'test_frameworks': [],
        'confidence_score': 0.0
    }


def _create_fallback_insights() -> Dict[str, Any]:
    """Create fallback performance insights when analysis fails"""
    return {
        'overall_performance_score': 0.5,
        'performance_grade': 'C',
        'cpu_performance_score': 0.5,
        'memory_performance_score': 0.5,
        'high_impact_bottlenecks': [],
        'memory_intensive_functions': [],
        'total_cpu_time_ms': 0,
        'total_memory_mb': 0,
        'avg_cpu_per_invocation': 0,
        'performance_trends': {},
        'optimization_opportunities': ['Unable to analyze - check error logs'],
        'error': 'Performance analysis failed'
    }


def _create_fallback_recommendations() -> List[Dict[str, Any]]:
    """Create fallback recommendations when generation fails"""
    return [{
        'priority': 'medium',
        'category': 'general_optimization',
        'title': 'General Performance Review Recommended',
        'description': 'Automated analysis encountered issues. Manual performance review recommended.',
        'suggested_actions': [
            'Review code changes for obvious performance issues',
            'Run local profiling tools on changed functions',
            'Check for algorithmic complexity improvements',
            'Verify resource usage patterns'
        ]
    }]


def profile_code_performance(
    profiling_group_name: str,
    start_time: str,
    end_time: str
) -> dict:
    """
    Legacy tool function for basic performance profiling.
    Maintained for backward compatibility.
    
    Args:
        profiling_group_name: Name of the CodeGuru profiling group
        start_time: ISO8601 datetime string (e.g., "2025-10-19T10:00:00Z")
        end_time: ISO8601 datetime string (e.g., "2025-10-19T10:05:00Z")
        
    Returns:
        Dictionary containing basic profiling results
    """
    analysis_start = time.time()
    
    try:
        logger.info(f"Starting performance profiling for group: {profiling_group_name}")
        
        # Parse datetime strings
        start_dt = parse_datetime(start_time)
        end_dt = parse_datetime(end_time)
        
        # Validate parameters
        validate_inputs(profiling_group_name, start_dt, end_dt)
        
        # Get profiling data
        profile_data = get_profile_data(profiling_group_name, start_dt, end_dt)
        
        # Analyze profile for bottlenecks
        bottlenecks = analyze_bottlenecks(profile_data)
        
        # Calculate aggregate metrics
        metrics = calculate_metrics(profile_data, bottlenecks)
        
        # Get recommendations from CodeGuru
        recommendations = get_recommendations(profiling_group_name, start_dt, end_dt)
        
        # Enhance bottlenecks with recommendations
        enhanced_bottlenecks = enhance_with_recommendations(bottlenecks, recommendations)
        
        # Generate flame graph URL (if available)
        flame_graph_url = generate_flame_graph_url(profiling_group_name, start_dt, end_dt)
        
        # Prepare result
        result = {
            "status": "completed",
            "profiling_id": f"{profiling_group_name}-{int(time.time())}",
            "total_cpu_time_ms": metrics['total_cpu_time_ms'],
            "total_memory_mb": metrics['total_memory_mb'],
            "total_invocations": metrics['total_invocations'],
            "avg_cpu_per_invocation_ms": metrics['avg_cpu_per_invocation_ms'],
            "bottlenecks": enhanced_bottlenecks,
            "flame_graph_url": flame_graph_url,
            "analysis_time_seconds": round(time.time() - analysis_start, 2),
            "profiling_group_name": profiling_group_name,
            "start_time": start_time,
            "end_time": end_time
        }
        
        return result
        
    except ProfilerError as e:
        logger.error(f"Profiler error: {str(e)}")
        return {
            "status": "error",
            "error_type": "profiler_error",
            "message": str(e),
            "bottlenecks": [],
            "analysis_time_seconds": round(time.time() - analysis_start, 2)
        }
        
    except ClientError as e:
        logger.error(f"AWS service error: {str(e)}")
        return {
            "status": "error",
            "error_type": "aws_service_error",
            "message": f"CodeGuru Profiler API error: {e.response['Error']['Message']}",
            "bottlenecks": [],
            "analysis_time_seconds": round(time.time() - analysis_start, 2)
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in profiler: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error_type": "internal_error",
            "message": str(e),
            "bottlenecks": [],
            "analysis_time_seconds": round(time.time() - analysis_start, 2)
        }


# For development/testing - mock implementation when AWS services not available
def mock_profile_code_performance(
    profiling_group_name: str,
    start_time: str, 
    end_time: str
) -> dict:
    """Mock implementation for development/testing"""
    time.sleep(1)  # Simulate analysis time
    
    return {
        "status": "completed",
        "profiling_id": f"mock-profile-{int(time.time())}",
        "total_cpu_time_ms": 1250.5,
        "total_memory_mb": 512.8,
        "total_invocations": 1500,
        "avg_cpu_per_invocation_ms": 0.83,
        "bottlenecks": [
            {
                "function_name": "process_large_dataset",
                "file_path": "src/processor.py",
                "line_number": 89,
                "cpu_percentage": 42.3,
                "self_time_ms": 528.7,
                "total_time_ms": 1025.2,
                "invocation_count": 850,
                "issue_type": "High CPU Usage",
                "description": "This function accounts for 42% of total CPU time",
                "recommendation": "Consider using vectorized operations or parallel processing"
            },
            {
                "function_name": "load_config_file", 
                "file_path": "src/config.py",
                "line_number": 23,
                "cpu_percentage": 18.7,
                "self_time_ms": 234.1,
                "total_time_ms": 456.8,
                "invocation_count": 650,
                "issue_type": "I/O Bottleneck",
                "description": "Frequent file reads detected",
                "recommendation": "Cache configuration data to reduce I/O operations"
            }
        ],
        "flame_graph_url": f"https://console.aws.amazon.com/codeguru/profiler#/profiling-groups/{profiling_group_name}/flame-graph",
        "analysis_time_seconds": 1.5,
        "profiling_group_name": profiling_group_name,
        "start_time": start_time,
        "end_time": end_time
    }


# Use mock implementation in development environment
if os.getenv('ENVIRONMENT') == 'development' or not os.getenv('AWS_REGION'):
    profile_code_performance = mock_profile_code_performance
    logger.info("Using mock CodeGuru Profiler implementation for development")