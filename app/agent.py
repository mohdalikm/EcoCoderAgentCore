"""
Eco-Coder Agent - Main Entry Point
A Strands-based AI agent for sustainable software development hosted on AWS Bedrock AgentCore Runtime.

This agent analyzes code changes in GitHub pull requests for performance, quality, and environmental impact,
providing developers with actionable feedback to write more sustainable software.

Requires Strands SDK and BedrockAgentCore packages to be available in the runtime environment.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from strands import Agent
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
    

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Import tool implementations
from app.tools.llm_code_reviewer import analyze_code_quality_with_llm
from app.tools.codeguru_profiler import profile_code_performance, profile_pull_request_performance
from app.tools.codecarbon_estimator import calculate_carbon_footprint
from app.tools.github_poster import post_github_comment

# Import utilities
from app.utils.aws_helpers import AWSHelper

# Import system prompt
from app.prompts import SYSTEM_PROMPT

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a global variable to store the current payload for tool access
current_payload = None

# Initialize app
app = BedrockAgentCoreApp()

# Initialize AWS helper        
aws_helper = AWSHelper()

# Configuration
AWS_REGION = os.getenv('AWS_REGION', 'ap-southeast-1')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
GITHUB_TOKEN_SECRET_ARN = os.getenv('GITHUB_TOKEN_SECRET_ARN', 'eco-coder/github-token')
ENABLE_AGENTCORE_MEMORY = os.getenv('ENABLE_AGENTCORE_MEMORY', 'false').lower() == 'true'


def load_system_prompt():    
    # Use embedded system prompt
    logger.info("Using embedded system prompt")
    return SYSTEM_PROMPT


def get_session_manager(actor_id: str, session_id: str):
    """Initialize session manager with comprehensive error handling"""
    
    # Check if AgentCore Memory is enabled
    if not ENABLE_AGENTCORE_MEMORY:
        logger.info("AgentCore Memory disabled via environment variable")
        return None
    
    try:
        # Initialize MemoryClient
        client = MemoryClient(region_name=AWS_REGION)
        
        # Create or get memory with detailed error handling
        try:
            logger.info("Attempting to list existing memories...")
            memories_response = client.list_memories()
            memory = None
            memories = memories_response.get('memories', []) if isinstance(memories_response, dict) else []
            
            for mem in memories:
                if mem.get('name') == 'eco-coder-memory':
                    memory = mem
                    logger.info(f"Found existing memory: {memory.get('id')}")
                    break
            
            if not memory:
                logger.info("No existing eco-coder-memory found, creating new memory...")
                # Create new memory if not found
                memory = client.create_memory(
                    name="eco-coder-memory",
                    description="Memory for Eco-Coder agent to track analysis history and context"
                )
                logger.info(f"Created new memory: {memory.get('id')}")
                
        except Exception as memory_error:
            # Handle specific permission errors
            error_msg = str(memory_error)
            
            if "AccessDeniedException" in error_msg:
                if "ListMemories" in error_msg:
                    logger.error(f"❌ IAM Permission Error: Missing 'bedrock-agentcore:ListMemories' permission")
                    logger.error("💡 Solution: Run './scripts/setup-memory-permissions.sh' to fix IAM permissions")
                elif "CreateMemory" in error_msg:
                    logger.error(f"❌ IAM Permission Error: Missing 'bedrock-agentcore:CreateMemory' permission")
                    logger.error("💡 Solution: Run './scripts/setup-memory-permissions.sh' to fix IAM permissions")
                else:
                    logger.error(f"❌ IAM Permission Error: {error_msg}")
                    logger.error("💡 Solution: Run './scripts/setup-memory-permissions.sh' to fix IAM permissions")
                
                # Return None to disable memory functionality gracefully
                return None
            else:
                logger.warning(f"Memory operation failed, creating fallback memory: {memory_error}")
                # Try to create a memory with a unique name as fallback
                try:
                    memory = client.create_memory(
                        name=f"eco-coder-memory-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        description="Fallback memory for Eco-Coder agent"
                    )
                    logger.info(f"Created fallback memory: {memory.get('id')}")
                except Exception as fallback_error:
                    logger.error(f"Fallback memory creation failed: {fallback_error}")
                    return None
        
        # Create memory configuration
        memory_config = AgentCoreMemoryConfig(
            memory_id=memory.get('id'),
            session_id=session_id,
            actor_id=actor_id
        )
        
        logger.info(f"✅ Created AgentCore Memory session for actor={actor_id}, session={session_id}, memory={memory.get('id')}")
        return AgentCoreMemorySessionManager(
            agentcore_memory_config=memory_config,
            region_name=AWS_REGION
        )
        
    except Exception as e:
        error_msg = str(e)
        
        if "AccessDeniedException" in error_msg:
            logger.error(f"❌ IAM Permission Error: {error_msg}")
            logger.error("💡 Solution: Run './scripts/setup-memory-permissions.sh' to fix IAM permissions")
        else:
            logger.warning(f"Could not initialize AgentCore Memory, using default session manager: {e}")
        
        return None


def create_agent(session_id: str, repository: str) -> Agent:
    """Create a Strands agent instance with registered tools"""
    
    # Load system prompt - this will raise an exception if file is missing
    try:
        system_prompt = load_system_prompt()
    except (FileNotFoundError, RuntimeError) as e:
        logger.error(f"Failed to load system prompt: {e}")
        raise RuntimeError(f"Agent initialization failed - system prompt file missing or unreadable: {e}")
    
    # Initialize session manager
    session_manager = get_session_manager(
        actor_id=repository,
        session_id=session_id
    )
    
    # Import the tool decorator
    from strands import tool
    
    # Define tools using @tool decorator
    @tool
    def analyze_code(repository_arn: str, branch_name: str, commit_sha: str) -> dict:
        """
        Analyze code quality using AI-powered LLM analysis.
        
        This tool creates a comprehensive code review using Large Language Models (LLMs)
        to analyze pull request diffs for security, performance, maintainability, and best practices.
        This uses modern LLM-based analysis for comprehensive code review.
        
        Args:
            repository_arn: ARN of the repository to analyze (for compatibility)
            branch_name: Git branch name
            commit_sha: Git commit SHA to analyze
            
        Returns:
            Dictionary containing comprehensive code review findings with severity levels,
            security analysis, performance recommendations, and actionable improvements.
        """
        logger.info(f"🔍 TOOL CALL: analyze_code (LLM) - repository_arn={repository_arn}, branch_name={branch_name}, commit_sha={commit_sha}")
        
        # Use GitHub token from secrets
        github_token = None
        try:
            secret = aws_helper.get_secret(GITHUB_TOKEN_SECRET_ARN)
            github_token = secret.get('github_token')
            logger.info("✅ Retrieved GitHub token for LLM code analysis")
        except Exception as e:
            logger.warning(f"Could not retrieve GitHub token: {e}")
        
        # Call the new LLM-based code reviewer with the current payload
        result = analyze_code_quality_with_llm(
            repository_arn=repository_arn,
            branch_name=branch_name,
            commit_sha=commit_sha,
            pr_payload=current_payload,  # Pass the current webhook payload
            github_token=github_token
        )
        
        logger.info(f"✅ TOOL RESULT: analyze_code (LLM) completed with status: {result.get('status', 'unknown')}")
        return result
    
    @tool
    def profile_code_performance_tool(
        profiling_group_name: str,
        start_time: str,
        end_time: str
    ) -> dict:
        """
        Profile code performance using Amazon CodeGuru Profiler (Legacy).
        
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
        """
        logger.info(f"🚀 TOOL CALL: profile_code_performance - profiling_group_name={profiling_group_name}")
        result = profile_code_performance(profiling_group_name, start_time, end_time)
        logger.info(f"✅ TOOL RESULT: profile_code_performance completed with status: {result.get('status', 'unknown')}")
        return result

    @tool
    def profile_pull_request_performance_tool(
        pr_payload: dict = None,
        github_token: str = None
    ) -> dict:
        """
        Enhanced PR Performance Profiler with AI Test Discovery and CodeBuild Integration.
        
        This advanced tool analyzes GitHub pull requests by:
        1. Extracting changed code from PR payload
        2. Using AI to discover relevant test scripts in the codebase
        3. Running discovered tests in AWS CodeBuild with CodeGuru Profiler enabled
        4. Analyzing performance bottlenecks and providing optimization recommendations
        
        This is the PREFERRED tool for analyzing pull request performance as it provides
        real-world profiling data by actually executing the code changes.
        
        Args:
            pr_payload: GitHub PR webhook payload (optional, will use session context if not provided)
            github_token: GitHub personal access token (optional, will use default if not provided)
            
        Returns:
            Dictionary containing comprehensive performance analysis:
            - PR code analysis and change summary
            - AI-discovered test execution plan
            - Real performance profiling results from CodeBuild
            - Bottleneck identification with file/line locations
            - Optimization recommendations with priority levels
            - Performance insights and trends
        """
        logger.info(f"🎯 TOOL CALL: profile_pull_request_performance - Starting enhanced PR performance profiling with AI test discovery")
        
        # Use GitHub token from secrets if not provided
        if not github_token:
            try:
                secret = aws_helper.get_secret(GITHUB_TOKEN_SECRET_ARN)
                github_token = secret.get('github_token')
                logger.info("✅ Retrieved GitHub token from secrets")
            except Exception as e:
                logger.warning(f"Could not retrieve GitHub token: {e}")
        
        # Get PR payload from session context if not provided
        if not pr_payload:
            # In a real Bedrock Agent Core environment, the payload would be available in the session
            # For testing, try to get it from environment or return setup guidance
            try:
                import os
                import json
                payload_str = os.getenv('ECOCODER_PR_PAYLOAD')
                if payload_str:
                    pr_payload = json.loads(payload_str)
                    logger.info("📋 Retrieved PR payload from environment")
                else:
                    logger.warning("No PR payload available in environment")
            except Exception as e:
                logger.warning(f"Could not retrieve PR payload from environment: {e}")
        
        # If we still don't have a payload, return setup guidance
        if not pr_payload:
            result = {
                "status": "setup_required",
                "message": "Performance Monitoring Setup",
                "description": "CodeGuru Profiler integration requires proper AWS service setup (profiling groups, repository associations). Run the setup script: './scripts/setup-codeguru-profiler.sh'",
                "estimated_metrics": {
                    "cpu_time_ms": 25,
                    "memory_usage_mb": 45,
                    "performance_score": "A",
                    "bottlenecks": [],
                    "recommendations": [
                        "Set up CodeGuru Profiler profiling groups",
                        "Configure repository associations",
                        "Enable CodeBuild integration for real-time profiling"
                    ]
                },
                "next_steps": [
                    "Run './scripts/setup-codeguru-profiler.sh' to configure AWS services",
                    "Ensure proper IAM permissions for CodeGuru services",
                    "Provide PR payload for real profiling analysis"
                ]
            }
            logger.info(f"✅ TOOL RESULT: profile_pull_request_performance completed with status: {result.get('status', 'unknown')}")
            return result
        
        # Call the actual profiling function with the payload
        try:
            from app.tools.codeguru_profiler import profile_pull_request_performance
            result = profile_pull_request_performance(pr_payload, github_token)
            logger.info(f"✅ TOOL RESULT: profile_pull_request_performance completed with status: {result.get('status', 'unknown')}")
            return result
        except Exception as e:
            logger.error(f"🚨 PR profiling failed: {str(e)}")
            return {
                "status": "error",
                "error_type": "profiling_execution_error",
                "message": f"PR profiling execution failed: {str(e)}",
                "estimated_metrics": {
                    "cpu_time_ms": 25,
                    "memory_usage_mb": 45,
                    "performance_score": "C",
                    "bottlenecks": [],
                    "recommendations": [
                        "Check AWS permissions and service availability",
                        "Verify GitHub token and repository access",
                        "Review CloudWatch logs for detailed error information"
                    ]
                }
            }
    
    @tool
    def calculate_carbon_footprint_tool(
        cpu_time_seconds: float,
        ram_usage_mb: float,
        aws_region: str,
        execution_count: int
    ) -> dict:
        """
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
        """
        logger.info(f"🌱 TOOL CALL: calculate_carbon_footprint - execution_count={execution_count}, aws_region={aws_region}")
        result = calculate_carbon_footprint(cpu_time_seconds, ram_usage_mb, aws_region, execution_count)
        logger.info(f"✅ TOOL RESULT: calculate_carbon_footprint completed with status: {result.get('status', 'unknown')}")
        return result
    
    @tool
    def post_github_comment_tool(
        repository_full_name: str,
        pull_request_number: int,
        report_markdown: str
    ) -> dict:
        """
        Post analysis report as GitHub PR comment.
        
        This tool posts the generated Markdown report as a comment on the specified
        pull request.
        
        Args:
            repository_full_name: Repository in "owner/repo" format
            pull_request_number: PR number
            report_markdown: Formatted report in Markdown
            
        Returns:
            Dictionary containing comment status, ID, and URL for viewing on GitHub.
        """
        logger.info(f"💬 TOOL CALL: post_github_comment - PR #{pull_request_number} in {repository_full_name}")
        result = post_github_comment(repository_full_name, pull_request_number, report_markdown)
        logger.info(f"✅ TOOL RESULT: post_github_comment completed with status: {result.get('status', 'unknown')}")
        return result
    
    # Create agent with tools
    tools = [analyze_code, profile_code_performance_tool, profile_pull_request_performance_tool, calculate_carbon_footprint_tool, post_github_comment_tool]
    
    # Create Strands agent with tools
    agent = Agent(
        system_prompt=system_prompt,
        tools=tools,
        session_manager=session_manager
    )
    
    return agent


def parse_github_webhook(payload: dict) -> dict:
    """Parse GitHub webhook payload to extract PR context"""
    try:
        action = payload.get('action')
        pr = payload.get('pull_request', {})
        repo = payload.get('repository', {})
        
        return {
            'action': action,
            'pr_number': pr.get('number'),
            'repository_name': repo.get('full_name'),
            'commit_sha': pr.get('head', {}).get('sha'),
            'branch_name': pr.get('head', {}).get('ref'),
            'base_branch': pr.get('base', {}).get('ref'),
            'title': pr.get('title', ''),
            'clone_url': repo.get('clone_url'),
            'region': AWS_REGION,
            'account_id': repo.get('owner', {}).get('id', 'unknown')
        }
    except Exception as e:
        logger.error(f"Error parsing GitHub webhook: {e}")
        raise ValueError(f"Invalid GitHub webhook payload: {e}")

# Create agent instance for this analysis - handle initialization errors
try:
    agent = create_agent("x9kuy", 'test-repo')
except RuntimeError as e:
    logger.error(f"Agent initialization failed: {e}")
    # Don't create agent if system prompt is missing
    agent = None

@app.entrypoint
def invoke(payload: dict) -> dict:
    """
    Main entrypoint for the Eco-Coder agent.
    Receives GitHub pull request webhook events and orchestrates the analysis.
    
    Expected payload format (GitHub webhook):
    {
        "action": "opened" | "synchronize" | "reopened",
        "pull_request": {
            "number": 123,
            "title": "Feature: Add new functionality",
            "diff_url": "https://github.com/owner/repo/pull/123.diff",
            "head": {"ref": "feature-branch", "sha": "abc123"},
            "base": {"ref": "main"}
        },
        "repository": {
            "full_name": "owner/repo",
            "clone_url": "https://github.com/owner/repo.git",
            "owner": {"id": "12345"}
        }
    }
    
    Returns:
    {
        "status": "success" | "error",
        "message": "Analysis completed",
        "session_id": "unique-session-identifier",
        "agent_response": "Final agent message"
    }
    """
    global current_payload
    start_time = time.time()
    logger.info("Eco-Coder agent invoked, start of the entrypoint")
    
    try:
        # Store payload globally for tool access
        current_payload = payload
        
        logger.info(f"Received payload: {json.dumps(payload, indent=2)}")
        
        # Check if agent was initialized properly
        if agent is None:
            error_msg = "Agent initialization failed - system prompt could not be loaded."
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "session_id": "unknown",
                "execution_time_seconds": round(time.time() - start_time, 3)
            }
        
        # Parse GitHub webhook payload
        pr_info = parse_github_webhook(payload)
        
        # Validate required fields
        if not all([pr_info.get('pr_number'), pr_info.get('repository_name'), 
                   pr_info.get('commit_sha'), pr_info.get('branch_name')]):
            raise ValueError("Missing required PR information in webhook payload")
        
        # Generate unique session ID
        session_id = f"pr-{pr_info['repository_name']}-{pr_info['pr_number']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        logger.info(f"Starting analysis for PR #{pr_info['pr_number']} in {pr_info['repository_name']}")
        
        # Create agent instance for this analysis
        #agent = create_agent(session_id, pr_info['repository_name'])
        
        # Construct analysis request for the agent
        analysis_request = f"""
Analyze pull request #{pr_info['pr_number']} in repository {pr_info['repository_name']}.

Pull Request Details:
- Title: {pr_info.get('title', 'N/A')}
- Branch: {pr_info['branch_name']} → {pr_info.get('base_branch', 'main')}
- Commit SHA: {pr_info['commit_sha']}

Please perform the following analysis workflow:
1. Analyze the code quality and security using the analyze_code tool
2. Profile the code performance using the profile_code_performance tool  
3. Calculate the carbon footprint based on the performance metrics using the calculate_carbon_footprint tool
4. Generate a comprehensive Green Code Report with all findings
5. Post the report to the pull request using the post_github_comment tool

Repository ARN: arn:aws:codecommit:{pr_info['region']}:{pr_info['account_id']}:{pr_info['repository_name']}
"""
        
        # Invoke the agent with the analysis request
        logger.info(f"Invoking agent for session {session_id}")
        logger.info(f"Analysis request: {analysis_request[:500]}...")  # Log first 500 chars
        
        # Use Strands SDK
        logger.info("Starting agent execution...")
        result = agent(analysis_request)
        logger.info(f"Agent execution completed. Result type: {type(result)}")
        
        agent_response = result.content if hasattr(result, 'content') else str(result)
        logger.info(f"Agent response preview: {str(agent_response)[:200]}...")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Agent analysis completed in {elapsed_time:.2f} seconds: {agent_response}")
        
        return {
            "status": "success",
            "message": "Eco-Coder analysis completed successfully",
            "session_id": session_id,
            "agent_response": agent_response,
            "pr_info": pr_info,
            "execution_time_seconds": round(elapsed_time, 2)
        }
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Error processing pull request analysis: {str(e)}", exc_info=True)
        
        return {
            "status": "error",
            "message": str(e),
            "session_id": locals().get('session_id', 'unknown'),
            "execution_time_seconds": round(elapsed_time, 2)
        }


if __name__ == "__main__":
    app.run()