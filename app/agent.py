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
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Import Strands SDK and BedrockAgentCore
try:
    from strands import Agent
    from bedrock_agentcore import BedrockAgentCoreApp
    from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
    print("✅ Strands SDK and BedrockAgentCore loaded successfully!")
except ImportError as e:
    print(f"❌ Error importing Strands SDK or BedrockAgentCore: {e}")
    raise ImportError("Required dependencies not available. Please install strands and bedrock_agentcore packages.")



# Import tool implementations
from app.tools.codeguru_reviewer import analyze_code_quality
from app.tools.codeguru_profiler import profile_code_performance
from app.tools.codecarbon_estimator import calculate_carbon_footprint
from app.tools.github_poster import post_github_comment

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize app
app = BedrockAgentCoreApp()

# Configuration
AWS_REGION = os.getenv('AWS_REGION', 'ap-southeast-1')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
GITHUB_TOKEN_SECRET_ARN = os.getenv('GITHUB_TOKEN_SECRET_ARN', 'eco-coder/github-token')


def load_system_prompt() -> str:
    """Load the system prompt from file"""
    try:
        with open('app/prompts/system_prompt.md', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback system prompt
        return """
You are Eco-Coder, an expert AI agent specializing in Green Software Engineering and sustainable software development.
Your mission is to analyze code changes in GitHub pull requests and provide comprehensive, actionable feedback
that helps developers write more efficient, sustainable, and high-quality software.

You have access to tools for code analysis, performance profiling, carbon footprint calculation, and GitHub integration.
Follow the prescribed workflow to gather data from all tools and synthesize it into a comprehensive Green Code Report.
"""


def get_session_manager(actor_id: str, session_id: str):
    """Initialize session manager"""
    try:
        memory_config = {
            'memory_id': f'eco-coder-memory-{actor_id}',
            'session_id': session_id,
            'actor_id': actor_id
        }
        return AgentCoreMemorySessionManager(agentcore_memory_config=memory_config)
    except Exception as e:
        logger.warning(f"Could not initialize AgentCore Memory, using default: {e}")
        return None


def create_agent(session_id: str, repository: str) -> Agent:
    """Create a Strands agent instance with registered tools"""
    
    # Load system prompt
    system_prompt = load_system_prompt()
    
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
        """
        logger.info(f"Analyzing code quality for {repository_arn} @ {commit_sha}")
        return analyze_code_quality(repository_arn, branch_name, commit_sha)
    
    @tool
    def profile_code_performance_tool(
        profiling_group_name: str,
        start_time: str,
        end_time: str
    ) -> dict:
        """
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
        """
        logger.info(f"Profiling performance for group {profiling_group_name}")
        return profile_code_performance(profiling_group_name, start_time, end_time)
    
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
        logger.info(f"Calculating carbon footprint for {execution_count} executions in {aws_region}")
        return calculate_carbon_footprint(cpu_time_seconds, ram_usage_mb, aws_region, execution_count)
    
    @tool
    def post_github_comment_tool(
        repository_full_name: str,
        pull_request_number: int,
        report_markdown: str,
        update_existing: bool = True
    ) -> dict:
        """
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
        """
        logger.info(f"Posting comment to PR #{pull_request_number} in {repository_full_name}")
        return post_github_comment(repository_full_name, pull_request_number, report_markdown, update_existing)
    
    # Create agent with tools
    tools = [analyze_code, profile_code_performance_tool, calculate_carbon_footprint_tool, post_github_comment_tool]
    
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
    start_time = time.time()
    
    try:
        logger.info(f"Received payload: {json.dumps(payload, indent=2)}")
        
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
        agent = create_agent(session_id, pr_info['repository_name'])
        
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
        
        # Use Strands SDK
        result = agent(analysis_request)
        agent_response = result.content if hasattr(result, 'content') else str(result)
        
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


def main():
    """Main function for local testing and development"""
    print("🌱 Eco-Coder Agent Starting...")
    print("Built with Strands SDK and AWS Bedrock AgentCore Runtime")
    print("For sustainable software development")
    
    # In AgentCore Runtime, this would be managed automatically
    # For local testing, we can simulate webhook events
    
    # Example test payload (GitHub PR webhook format)
    test_payload = {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "title": "feat: Add new data processing algorithm",
            "head": {
                "ref": "feature/optimize-performance", 
                "sha": "a1b2c3d4e5f6"
            },
            "base": {"ref": "main"}
        },
        "repository": {
            "full_name": "eco-tech/sample-app",
            "clone_url": "https://github.com/eco-tech/sample-app.git",
            "owner": {"id": "123456"}
        }
    }
    
    print("\n🔍 Testing with sample PR webhook...")
    result = invoke(test_payload)
    print(f"\n✅ Result: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()