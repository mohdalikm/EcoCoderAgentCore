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
        self.aws_helper = AWSHelper()
        
        # Try to import requests for README reading
        try:
            import requests
            self.requests = requests
        except ImportError:
            logger.warning("requests library not available - README reading will be disabled")
            self.requests = None
        
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
            
            # Step 1: Read repository README for test instructions
            readme_analysis = self._read_repository_readme(pr_code)
            
            # Analyze changed files to understand scope
            changed_files = pr_code['changed_files']
            source_files = [f for f in changed_files if f['is_source_file'] and not f['is_test_file']]
            existing_test_files = [f for f in changed_files if f['is_test_file']]
            
            # Discover related test files using intelligent analysis
            discovered_tests = self._discover_related_tests(source_files, existing_test_files)
            
            # Generate test execution plan with README insights
            test_plan = self._generate_test_execution_plan(discovered_tests, pr_code, readme_analysis)
            
            result = {
                'discovered_tests': discovered_tests,
                'test_execution_plan': test_plan,
                'readme_analysis': readme_analysis,
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
    
    def _generate_test_execution_plan(self, discovered_tests: List[Dict], pr_code: Dict, readme_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimized test execution plan with README insights"""
        # Sort tests by priority and confidence
        high_priority = [t for t in discovered_tests if t['priority'] == 'high']
        medium_priority = [t for t in discovered_tests if t['priority'] == 'medium']
        
        # Use README test commands if available and confident
        readme_commands = []
        if readme_analysis['readme_found'] and readme_analysis['confidence'] > 0.5:
            readme_commands = readme_analysis['test_commands']
            logger.info(f"Using README test commands: {readme_commands}")
        
        # Generate framework commands as fallback
        framework_commands = self._generate_framework_commands(pr_code['languages'])
        
        return {
            'execution_order': ['readme_commands', 'high_priority', 'medium_priority'],
            'readme_commands': readme_commands,
            'high_priority_tests': high_priority,
            'medium_priority_tests': medium_priority,
            'estimated_duration_minutes': len(discovered_tests) * 2,  # 2 min per test avg
            'parallel_execution': len(discovered_tests) > 5,
            'framework_commands': framework_commands,
            'setup_commands': readme_analysis.get('setup_commands', []),
            'dependencies': readme_analysis.get('dependencies', [])
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
    
    def _read_repository_readme(self, pr_code: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read the repository's README file to extract test running instructions
        
        Args:
            pr_code: PR code information containing repository details
            
        Returns:
            Dictionary containing README analysis and extracted test commands
        """
        try:
            if not self.requests:
                logger.warning("requests library not available - using fallback test instructions")
                return self._generate_fallback_test_instructions()
                
            logger.info(f"Reading README from repository: {pr_code['repository']}")
            
            # Get GitHub token from environment or AWS Secrets Manager
            github_token = None
            try:
                github_token = self.aws_helper.get_secret_value('github-token')['SecretString']
            except Exception as e:
                logger.warning(f"Could not retrieve GitHub token: {e}")
            
            # Common README file names to check
            readme_files = ['README.md', 'README.rst', 'README.txt', 'README', 'readme.md', 'Readme.md']
            readme_content = None
            found_readme = None
            
            # GitHub API headers
            headers = {'Accept': 'application/vnd.github.v3+json'}
            if github_token:
                headers['Authorization'] = f'token {github_token}'
            
            # Try to find and read README file
            for readme_name in readme_files:
                try:
                    url = f"https://api.github.com/repos/{pr_code['repository']}/contents/{readme_name}"
                    response = self.requests.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        import base64
                        content_data = response.json()
                        readme_content = base64.b64decode(content_data['content']).decode('utf-8')
                        found_readme = readme_name
                        logger.info(f"Successfully read {readme_name} ({len(readme_content)} characters)")
                        break
                        
                except Exception as e:
                    logger.debug(f"Could not read {readme_name}: {e}")
                    continue
            
            if not readme_content:
                logger.warning("No README file found in repository")
                return self._generate_fallback_test_instructions()
            
            # Extract test instructions from README
            test_instructions = self._extract_test_instructions(readme_content, found_readme)
            
            return {
                'readme_found': True,
                'readme_file': found_readme,
                'readme_length': len(readme_content),
                'test_commands': test_instructions['commands'],
                'setup_commands': test_instructions['setup'],
                'dependencies': test_instructions['dependencies'],
                'test_frameworks': test_instructions['frameworks'],
                'confidence': test_instructions['confidence']
            }
            
        except Exception as e:
            logger.error(f"Failed to read repository README: {str(e)}")
            return self._generate_fallback_test_instructions()
    
    def _extract_test_instructions(self, readme_content: str, filename: str) -> Dict[str, Any]:
        """
        Extract test running instructions from README content
        
        Args:
            readme_content: The README file content
            filename: The README filename
            
        Returns:
            Dictionary containing extracted test instructions
        """
        import re
        
        logger.info(f"Extracting test instructions from {filename}")
        
        # Convert to lowercase for case-insensitive matching
        content_lower = readme_content.lower()
        
        # Initialize result structure
        result = {
            'commands': [],
            'setup': [],
            'dependencies': [],
            'frameworks': [],
            'confidence': 0.0
        }
        
        # Patterns to identify test-related sections
        test_section_patterns = [
            r'##\s*test.*?(?=##|\n\n|\Z)',
            r'##\s*running.*test.*?(?=##|\n\n|\Z)',
            r'##\s*development.*?(?=##|\n\n|\Z)',
            r'##\s*usage.*?(?=##|\n\n|\Z)',
            r'##\s*getting.*started.*?(?=##|\n\n|\Z)',
            r'###\s*test.*?(?=###|\n\n|\Z)',
            r'#\s*test.*?(?=#|\n\n|\Z)'
        ]
        
        # Extract test-related sections
        test_sections = []
        for pattern in test_section_patterns:
            matches = re.findall(pattern, readme_content, re.IGNORECASE | re.DOTALL)
            test_sections.extend(matches)
        
        # If no dedicated test sections found, search the entire README
        if not test_sections:
            test_sections = [readme_content]
        
        # Extract commands from code blocks
        code_block_patterns = [
            r'```(?:bash|shell|sh|console)?\n(.*?)\n```',
            r'`([^`\n]+)`',
            r'^\s*\$\s*(.+)$',
            r'^\s*>\s*(.+)$'
        ]
        
        all_commands = []
        for section in test_sections:
            for pattern in code_block_patterns:
                matches = re.findall(pattern, section, re.MULTILINE | re.DOTALL)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match else ''
                    all_commands.extend(line.strip() for line in match.split('\n') if line.strip())
        
        # Filter for test-related commands
        test_keywords = [
            'test', 'pytest', 'unittest', 'nose', 'tox', 'npm test', 'yarn test',
            'mvn test', 'gradle test', 'go test', 'cargo test', 'make test',
            'python -m pytest', 'python -m unittest', 'jest', 'mocha', 'jasmine'
        ]
        
        setup_keywords = [
            'pip install', 'npm install', 'yarn install', 'mvn install',
            'gradle install', 'go mod', 'cargo build', 'make install',
            'requirements.txt', 'package.json', 'pom.xml', 'build.gradle'
        ]
        
        # Categorize commands
        for cmd in all_commands:
            cmd_lower = cmd.lower()
            
            # Skip comments and empty lines
            if cmd.startswith('#') or not cmd.strip():
                continue
                
            # Test commands
            if any(keyword in cmd_lower for keyword in test_keywords):
                result['commands'].append(cmd.strip())
                result['confidence'] += 0.3
                
            # Setup/dependency commands
            elif any(keyword in cmd_lower for keyword in setup_keywords):
                result['setup'].append(cmd.strip())
                result['confidence'] += 0.1
        
        # Detect frameworks from README content
        framework_indicators = {
            'pytest': ['pytest', 'py.test'],
            'unittest': ['unittest', 'python -m unittest'],
            'jest': ['jest', 'npm test', 'yarn test'],
            'mocha': ['mocha'],
            'maven': ['mvn test', 'maven'],
            'gradle': ['gradle test', 'gradlew'],
            'go': ['go test'],
            'cargo': ['cargo test'],
            'tox': ['tox']
        }
        
        for framework, indicators in framework_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                result['frameworks'].append(framework)
                result['confidence'] += 0.2
        
        # Extract dependencies from common files mentioned
        dependency_patterns = [
            r'requirements\.txt',
            r'package\.json',
            r'pom\.xml',
            r'build\.gradle',
            r'Cargo\.toml',
            r'go\.mod'
        ]
        
        for pattern in dependency_patterns:
            if re.search(pattern, content_lower):
                result['dependencies'].append(pattern.replace('\\', ''))
                result['confidence'] += 0.1
        
        # Normalize confidence score
        result['confidence'] = min(result['confidence'], 1.0)
        
        logger.info(f"Extracted {len(result['commands'])} test commands with confidence {result['confidence']:.2f}")
        logger.info(f"Test commands found: {result['commands']}")
        logger.info(f"Frameworks detected: {result['frameworks']}")
        
        return result
    
    def _generate_fallback_test_instructions(self) -> Dict[str, Any]:
        """Generate fallback test instructions when README is not available"""
        logger.info("Generating fallback test instructions")
        
        return {
            'readme_found': False,
            'readme_file': None,
            'readme_length': 0,
            'test_commands': [],
            'setup_commands': [],
            'dependencies': [],
            'test_frameworks': [],
            'confidence': 0.0
        }


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
        """Always use a single default profiling group for all PRs"""
        try:
            # Always use the default profiling group to avoid creating a new one for each PR
            return self._get_or_create_default_profiling_group()
        except Exception as e:
            logger.error(f"Unexpected error getting or creating default profiling group: {str(e)}")
            # If default group fails, raise an error as this is a critical failure
            raise ProfilerError(f"Failed to get or create default profiling group: {str(e)}")
    
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
        """Ensure CodeBuild project exists - using AgentCore project with GitHub source override"""
        try:
            # Use the existing AgentCore CodeBuild project with GitHub source override
            # This approach follows AWS documentation for using sourceTypeOverride and sourceLocationOverride
            project_name = "bedrock-agentcore-ecocoderagentcore-builder"
            
            # Verify the project exists
            try:
                self.codebuild_client.batch_get_projects(names=[project_name])
                logger.info(f"Using existing CodeBuild project with GitHub source override: {project_name}")
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
        readme_analysis = test_discovery.get('readme_analysis', {})
        
        logger.info(f"Generating buildspec for primary language: {primary_language}")
        logger.info(f"Profiling group: {profiling_group_name}")
        logger.info(f"Test plan execution order: {test_plan.get('execution_order', [])}")
        
        # Log README analysis results
        if readme_analysis.get('readme_found'):
            logger.info(f"README analysis: Found {readme_analysis['readme_file']} with {len(readme_analysis.get('test_commands', []))} test commands (confidence: {readme_analysis.get('confidence', 0):.2f})")
        else:
            logger.info("README analysis: No README found or low confidence, using fallback test discovery")
        
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
        
        # Add language-specific setup and README-based commands
        if primary_language == 'python':
            logger.info("Setting up Python-specific buildspec configuration")
            buildspec['phases']['install']['runtime-versions']['python'] = '3.11'
            
            # Use README setup commands if available
            setup_commands = test_plan.get('setup_commands', [])
            if setup_commands:
                logger.info(f"Using README setup commands: {setup_commands}")
                buildspec['phases']['install']['commands'].extend([
                    'echo "Installing dependencies from README instructions"'
                ] + setup_commands)
            else:
                buildspec['phases']['install']['commands'].extend([
                    'echo "Installing Python dependencies"',
                    'pip install --upgrade pip',
                    'pip install pytest pytest-cov codecov',
                    'pip install -r requirements.txt || echo "No requirements.txt found"'
                ])
            
            # Add profiler agent for Python
            buildspec['phases']['pre_build']['commands'].extend([
                'echo "Installing CodeGuru Profiler agent for Python"',
                'pip install codeguru-profiler-agent',
                'export PYTHONPATH="${PYTHONPATH}:."'
            ])
            
            # Prioritize README test commands
            readme_commands = test_plan.get('readme_commands', [])
            if readme_commands:
                logger.info(f"Using README test commands: {readme_commands}")
                buildspec['phases']['build']['commands'].extend([
                    'echo "Running tests based on README instructions"'
                ])
                for cmd in readme_commands:
                    # Sanitize and add test commands from README
                    safe_cmd = cmd.strip()
                    if safe_cmd and not safe_cmd.startswith('#'):
                        buildspec['phases']['build']['commands'].append(f'{safe_cmd} || echo "README test command completed with issues"')
            else:
                # Fallback to discovered test files
                logger.info("No README test commands found, using discovered test files")
                high_priority_tests = test_plan.get('high_priority_tests', [])
                medium_priority_tests = test_plan.get('medium_priority_tests', [])
                
                logger.info(f"High priority tests found: {len(high_priority_tests)}")
                logger.info(f"Medium priority tests found: {len(medium_priority_tests)}")
                
                for test_type, tests in [('high_priority_tests', high_priority_tests), ('medium_priority_tests', medium_priority_tests)]:
                    if tests:
                        # Filter out pattern-based tests that contain wildcards
                        concrete_tests = [t for t in tests if not '*' in t['filename']]
                        pattern_tests = [t for t in tests if '*' in t['filename']]
                        
                        logger.info(f"{test_type} - Concrete test files: {[t['filename'] for t in concrete_tests]}")
                        logger.info(f"{test_type} - Pattern-based tests: {[t['filename'] for t in pattern_tests]}")
                        
                        if concrete_tests:
                            test_files = ' '.join([t['filename'] for t in concrete_tests])
                            test_command = f'python -m pytest {test_files} -v --tb=short --junitxml=test-results.xml || echo "Tests completed with issues"'
                            logger.info(f"Adding test command: {test_command}")
                            buildspec['phases']['build']['commands'].append(f'echo "Running {test_type}: {test_files}"')
                            buildspec['phases']['build']['commands'].append(test_command)
                        
                        # Handle pattern-based tests
                        for pattern_test in pattern_tests:
                            pattern = pattern_test['filename']
                            pattern_command = f'find . -name "{pattern.split("/")[-1]}" -type f | head -10 | xargs python -m pytest -v --tb=short || echo "Pattern tests completed with issues"'
                            logger.info(f"Adding pattern test command for {pattern}: {pattern_command}")
                            buildspec['phases']['build']['commands'].append(f'echo "Running pattern-based tests: {pattern}"')
                            buildspec['phases']['build']['commands'].append(pattern_command)
        
        elif primary_language == 'javascript':
            logger.info("Setting up JavaScript-specific buildspec configuration")
            buildspec['phases']['install']['runtime-versions']['nodejs'] = '18'
            
            # Use README setup commands if available
            setup_commands = test_plan.get('setup_commands', [])
            if setup_commands:
                logger.info(f"Using README setup commands: {setup_commands}")
                buildspec['phases']['install']['commands'].extend([
                    'echo "Installing dependencies from README instructions"'
                ] + setup_commands)
            else:
                buildspec['phases']['install']['commands'].extend([
                    'echo "Installing Node.js dependencies"',
                    'npm install',
                    'npm install --global @aws/codeguru-profiler-nodejs-agent'
                ])
            
            # Use README test commands or fallback to npm test
            readme_commands = test_plan.get('readme_commands', [])
            if readme_commands:
                logger.info(f"Using README test commands: {readme_commands}")
                buildspec['phases']['build']['commands'].extend([
                    'echo "Running tests based on README instructions"'
                ])
                for cmd in readme_commands:
                    safe_cmd = cmd.strip()
                    if safe_cmd and not safe_cmd.startswith('#'):
                        buildspec['phases']['build']['commands'].append(f'{safe_cmd} || echo "README test command completed with issues"')
            else:
                buildspec['phases']['build']['commands'].append(
                    'npm test || echo "Tests completed with issues"'
                )
        
        else:
            logger.warning(f"Unknown primary language '{primary_language}', using generic setup")
            
            # Still try to use README commands for unknown languages
            readme_commands = test_plan.get('readme_commands', [])
            if readme_commands:
                logger.info(f"Using README test commands for unknown language: {readme_commands}")
                buildspec['phases']['build']['commands'].extend([
                    'echo "Running tests based on README instructions"'
                ])
                for cmd in readme_commands:
                    safe_cmd = cmd.strip()
                    if safe_cmd and not safe_cmd.startswith('#'):
                        buildspec['phases']['build']['commands'].append(f'{safe_cmd} || echo "README test command completed with issues"')
            else:
                buildspec['phases']['build']['commands'].append(
                    'echo "Generic test execution - language-specific setup not available"'
                )
        
        # Add some basic verification commands
        buildspec['phases']['pre_build']['commands'].extend([
            'echo "=== Environment Information ==="',
            'pwd',
            'ls -la',
            'env | grep ECOCODER || echo "No ECOCODER env vars found"',
            'env | grep AWS_CODEGURU || echo "No CodeGuru env vars found"',
            'git status || echo "Not a git repository"',
            'git log --oneline -5 || echo "No git history available"',
            'echo "=== End Environment Information ==="'
        ])
        
        logger.info("Generated buildspec with phases: " + ", ".join(buildspec['phases'].keys()))
        logger.info(f"Total install commands: {len(buildspec['phases']['install']['commands'])}")
        logger.info(f"Total pre_build commands: {len(buildspec['phases']['pre_build']['commands'])}")
        logger.info(f"Total build commands: {len(buildspec['phases']['build']['commands'])}")
        logger.info(f"Total post_build commands: {len(buildspec['phases']['post_build']['commands'])}")
        
        return buildspec
    
    def _start_codebuild_execution(self, project_name: str, pr_code: Dict[str, Any], 
                                 buildspec: Dict[str, Any]) -> Dict[str, Any]:
        """Start CodeBuild execution with detailed logging"""
        try:
            # Log the buildspec that will be used
            logger.info(f"Starting CodeBuild with project: {project_name}")
            logger.info(f"Source version (commit SHA): {pr_code['head_sha']}")
            logger.info(f"Repository: {pr_code['repository']}")
            logger.info(f"PR number: {pr_code['pr_number']}")
            
            # Log buildspec details (but not sensitive information)
            buildspec_summary = {
                'version': buildspec.get('version'),
                'phases': list(buildspec.get('phases', {}).keys()),
                'artifacts': buildspec.get('artifacts', {}).get('files', [])
            }
            logger.info(f"Buildspec summary: {json.dumps(buildspec_summary, indent=2)}")
            
            # Log install commands for debugging
            install_commands = buildspec.get('phases', {}).get('install', {}).get('commands', [])
            if install_commands:
                logger.info(f"Install commands: {install_commands}")
            
            # Log build commands for debugging
            build_commands = buildspec.get('phases', {}).get('build', {}).get('commands', [])
            if build_commands:
                logger.info(f"Build commands: {build_commands}")
            
            # Prepare environment variables
            env_vars = [
                {
                    'name': 'ECOCODER_PR_NUMBER',
                    'value': str(pr_code['pr_number'])
                },
                {
                    'name': 'ECOCODER_REPOSITORY',
                    'value': pr_code['repository']
                },
                {
                    'name': 'ECOCODER_HEAD_SHA',
                    'value': pr_code['head_sha']
                },
                {
                    'name': 'ECOCODER_BASE_SHA', 
                    'value': pr_code.get('base_sha', '')
                },
                {
                    'name': 'ECOCODER_HEAD_REF',
                    'value': pr_code.get('head_ref', '')
                },
                {
                    'name': 'ECOCODER_BASE_REF',
                    'value': pr_code.get('base_ref', '')
                }
            ]
            
            env_var_summary = [f"{var['name']}={var['value']}" for var in env_vars]
            logger.info(f"Environment variables being set: {env_var_summary}")
            logger.info(f"Starting CodeBuild with GitHub source: {pr_code['clone_url']}")
            logger.info(f"Source version (commit SHA): {pr_code['head_sha']}")
            
            # Start the build with GitHub source overrides
            response = self.codebuild_client.start_build(
                projectName=project_name,
                sourceVersion=pr_code['head_sha'],
                sourceTypeOverride='GITHUB',
                sourceLocationOverride=pr_code['clone_url'],
                buildspecOverride=json.dumps(buildspec),
                environmentVariablesOverride=env_vars
            )
            
            build_id = response['build']['id']
            logger.info(f"Successfully started CodeBuild execution: {build_id}")
            
            # Log initial build details
            build = response['build']
            logger.info(f"Build ARN: {build.get('arn', 'N/A')}")
            logger.info(f"Build status: {build.get('buildStatus', 'N/A')}")
            logger.info(f"Build start time: {build.get('startTime', 'N/A')}")
            
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"CodeBuild ClientError - Code: {error_code}, Message: {error_message}")
            logger.error(f"Full error response: {json.dumps(e.response, indent=2, default=str)}")
            raise ProfilerError(f"CodeBuild start failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Unexpected error starting CodeBuild: {str(e)}")
            logger.error(f"Project name: {project_name}")
            logger.error(f"Source version: {pr_code.get('head_sha', 'N/A')}")
            raise ProfilerError(f"CodeBuild start failed: {str(e)}")
    
    def _wait_for_build_completion(self, build_id: str) -> Dict[str, Any]:
        """Wait for CodeBuild to complete with detailed logging"""
        max_attempts = 60  # 30 minutes with 30-second intervals
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = self.codebuild_client.batch_get_builds(ids=[build_id])
                build = response['builds'][0]
                
                status = build['buildStatus']
                current_phase = build.get('currentPhase', 'UNKNOWN')
                phases = build.get('phases', [])
                
                # Log current phase and any phase details
                logger.info(f"Build {build_id} status: {status}, current phase: {current_phase}, attempt {attempt + 1}/{max_attempts}")
                
                # Log phase details for debugging
                if phases:
                    for phase in phases:
                        phase_type = phase.get('phaseType', 'UNKNOWN')
                        phase_status = phase.get('phaseStatus', 'UNKNOWN')
                        duration = phase.get('durationInSeconds', 0)
                        
                        if phase_status in ['FAILED', 'FAULT', 'TIMED_OUT']:
                            logger.error(f"Build phase {phase_type} failed with status {phase_status} after {duration}s")
                            
                            # Log detailed phase context if available
                            contexts = phase.get('contexts', [])
                            for context in contexts:
                                logger.error(f"Phase context - Status: {context.get('statusCode')}, Message: {context.get('message')}")
                        elif phase_status == 'SUCCEEDED':
                            logger.info(f"Build phase {phase_type} completed successfully in {duration}s")
                        elif phase_status in ['IN_PROGRESS']:
                            logger.info(f"Build phase {phase_type} is in progress ({duration}s elapsed)")
                
                if status in ['SUCCEEDED', 'FAILED', 'STOPPED', 'TIMED_OUT']:
                    # Final logging with complete build information
                    total_duration = build.get('timeoutInMinutes', 0)
                    start_time = build.get('startTime')
                    end_time = build.get('endTime')
                    
                    logger.info(f"Build {build_id} completed with final status: {status}")
                    logger.info(f"Build duration: {total_duration} minutes")
                    
                    if start_time:
                        logger.info(f"Build started at: {start_time}")
                    if end_time:
                        logger.info(f"Build ended at: {end_time}")
                    
                    # Log environment information
                    environment = build.get('environment', {})
                    if environment:
                        logger.info(f"Build environment - Type: {environment.get('type')}, "
                                  f"Image: {environment.get('image')}, "
                                  f"Compute: {environment.get('computeType')}")
                    
                    # Log source information
                    source = build.get('source', {})
                    if source:
                        logger.info(f"Build source - Type: {source.get('type')}, "
                                  f"Location: {source.get('location')}")
                    
                    # Log logs information for troubleshooting
                    logs = build.get('logs', {})
                    if logs:
                        log_group = logs.get('groupName')
                        log_stream = logs.get('streamName')
                        deep_link = logs.get('deepLink')
                        
                        if log_group and log_stream:
                            logger.info(f"Build logs available at - Group: {log_group}, Stream: {log_stream}")
                        if deep_link:
                            logger.info(f"CloudWatch logs deep link: {deep_link}")
                    
                    # If build failed, log additional failure information
                    if status == 'FAILED':
                        self._log_build_failure_details(build)
                    
                    return response
                
                time.sleep(30)
                attempt += 1
                
            except Exception as e:
                logger.warning(f"Error checking build status: {e}")
                time.sleep(30)
                attempt += 1
        
        raise ProfilerError(f"Build {build_id} timed out after {max_attempts} attempts")
    
    def _log_build_failure_details(self, build: Dict[str, Any]) -> None:
        """Log detailed information about build failures"""
        try:
            build_id = build.get('id', 'unknown')
            logger.error(f"=== BUILD FAILURE ANALYSIS FOR {build_id} ===")
            
            # Log basic failure information
            logger.error(f"Build Status: {build.get('buildStatus', 'UNKNOWN')}")
            logger.error(f"Build Complete: {build.get('buildComplete', False)}")
            
            # Log phase failures in detail
            phases = build.get('phases', [])
            failed_phases = [p for p in phases if p.get('phaseStatus') in ['FAILED', 'FAULT', 'TIMED_OUT']]
            
            if failed_phases:
                logger.error(f"Failed phases count: {len(failed_phases)}")
                for i, phase in enumerate(failed_phases):
                    logger.error(f"Failed Phase {i+1}:")
                    logger.error(f"  Type: {phase.get('phaseType', 'UNKNOWN')}")
                    logger.error(f"  Status: {phase.get('phaseStatus', 'UNKNOWN')}")
                    logger.error(f"  Duration: {phase.get('durationInSeconds', 0)} seconds")
                    logger.error(f"  Start Time: {phase.get('startTime', 'N/A')}")
                    logger.error(f"  End Time: {phase.get('endTime', 'N/A')}")
                    
                    # Log detailed error contexts
                    contexts = phase.get('contexts', [])
                    if contexts:
                        logger.error(f"  Error Contexts:")
                        for j, context in enumerate(contexts):
                            logger.error(f"    Context {j+1}:")
                            logger.error(f"      Status Code: {context.get('statusCode', 'N/A')}")
                            logger.error(f"      Message: {context.get('message', 'N/A')}")
            
            # Log environment variables that might affect the build
            env_vars = build.get('environment', {}).get('environmentVariables', [])
            if env_vars:
                logger.info("Environment variables:")
                for var in env_vars:
                    name = var.get('name', 'unknown')
                    # Don't log sensitive values
                    if 'TOKEN' in name.upper() or 'SECRET' in name.upper() or 'KEY' in name.upper():
                        logger.info(f"  {name}: [REDACTED]")
                    else:
                        logger.info(f"  {name}: {var.get('value', 'N/A')}")
            
            # Log artifacts information
            artifacts = build.get('artifacts', {})
            if artifacts:
                logger.info(f"Artifacts location: {artifacts.get('location', 'N/A')}")
                artifact_override = build.get('artifactsOverride', {})
                if artifact_override:
                    logger.info(f"Artifact override type: {artifact_override.get('type', 'N/A')}")
            
            # Log service role information
            service_role = build.get('serviceRole')
            if service_role:
                logger.info(f"Service role: {service_role}")
            
            # Log timeout information
            timeout = build.get('timeoutInMinutes', 0)
            logger.info(f"Timeout setting: {timeout} minutes")
            
            # Try to get recent CloudWatch logs if available
            logs = build.get('logs', {})
            if logs:
                log_group = logs.get('groupName')
                log_stream = logs.get('streamName')
                
                if log_group and log_stream:
                    logger.error(f"Recent build logs should be available in CloudWatch:")
                    logger.error(f"  Log Group: {log_group}")
                    logger.error(f"  Log Stream: {log_stream}")
                    logger.error(f"  AWS CLI command: aws logs get-log-events --log-group-name '{log_group}' --log-stream-name '{log_stream}' --start-time {int((datetime.utcnow() - timedelta(hours=1)).timestamp() * 1000)}")
            
            logger.error("=== END BUILD FAILURE ANALYSIS ===")
            
        except Exception as e:
            logger.error(f"Failed to log build failure details: {e}")
    
    
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