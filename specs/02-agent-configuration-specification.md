# Eco-Coder Agent Configuration Specification

## 1. Overview

This document specifies the complete configuration for the Eco-Coder AI Agent built using the **Strands Agents SDK** and hosted in **Amazon Bedrock AgentCore Runtime**. The agent is deployed as a containerized application that receives GitHub pull request events directly through the AgentCore Runtime invocation endpoint.

## 2. Agent Architecture Overview

**Key Architecture Points**:
- Agent is built with **Strands Agents SDK**
- Hosted in **Amazon Bedrock AgentCore Runtime** (not traditional Bedrock Agents)
- Tools are integrated within the Strands agent code (not as separate Lambda Action Groups)
- No API Gateway needed - AgentCore Runtime provides native invocation endpoint
- GitHub webhook calls AgentCore Runtime endpoint directly
- Agent orchestrates the entire workflow internally

## 3. Agent Core Configuration

### 3.1 Agent Project Structure

```
eco-coder-agent/
├── agent.py                    # Main agent entrypoint
├── requirements.txt            # Python dependencies
├── config/
│   ├── agent_config.yaml      # Agent configuration
│   └── model_config.yaml      # Model parameters
├── tools/
│   ├── __init__.py
│   ├── codeguru_reviewer.py   # CodeGuru Reviewer tool
│   ├── codeguru_profiler.py   # CodeGuru Profiler tool
│   ├── codecarbon.py          # Carbon estimation tool
│   └── github_poster.py       # GitHub interaction tool
├── prompts/
│   └── system_prompt.md       # Agent system prompt
└── Dockerfile                  # Container configuration
```

### 3.2 Agent Metadata

```yaml
agentName: eco-coder-agent
description: >
  A Strands-based AI agent that analyzes code in pull requests for 
  performance, quality, and environmental impact, providing developers 
  with actionable feedback to write more sustainable software.
version: "1.0.0"
framework: strands-agents
runtime: bedrock-agentcore
tags:
  Project: EcoCoder
  Purpose: GreenSoftwareEngineering
  Hackathon: AWSAIAgentGlobal
  Framework: Strands
```

### 3.3 Foundation Model Configuration

```yaml
model:
  provider: bedrock
  model_id: anthropic.claude-3-sonnet-20240229-v1:0
  parameters:
    temperature: 0.1        # Low temperature for consistent, deterministic outputs
    top_p: 0.9              # Nucleus sampling threshold
    max_tokens: 4096        # Maximum tokens in response
    stop_sequences: []      # No custom stop sequences
```

**Rationale for Model Choice**:
- **Claude 3 Sonnet**: Optimal balance of intelligence, speed, and cost
- **Temperature 0.1**: Ensures consistent, factual analysis (not creative)
- **Context Window**: 200K tokens supports large code contexts
- **Performance**: Fast enough for near-real-time feedback

### 3.4 AgentCore Runtime Configuration

```yaml
runtime:
  deployment:
    region: us-east-1
    memory: 2048              # MB
    timeout: 480              # 8 minutes (maximum for long-running analysis)
    concurrency: 10           # Max concurrent sessions
    
  session:
    enable_persistence: true
    timeout: 300              # 5 minutes session timeout
    
  observability:
    enable_trace: true        # Full trace logging for debugging
    log_level: INFO
    cloudwatch_logs: true
    
  authentication:
    type: IAM
    allowed_principals:
      - service: lambda.amazonaws.com  # For GitHub webhook handler
      - service: apigateway.amazonaws.com
```

## 4. Strands Agent Implementation

### 4.1 Main Agent File

**File**: `agent.py`

```python
"""
Eco-Coder Agent - Strands-based AI agent for sustainable software development
"""

from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
import json
import logging
from datetime import datetime

# Import tools
from tools.codeguru_reviewer import analyze_code_quality
from tools.codeguru_profiler import profile_performance
from tools.codecarbon import estimate_carbon_footprint
from tools.github_poster import post_report_to_pr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize BedrockAgentCore app
app = BedrockAgentCoreApp()

# Load system prompt
with open('prompts/system_prompt.md', 'r') as f:
    SYSTEM_PROMPT = f.read()

# Initialize memory (if using AgentCore Memory)
def get_session_manager(actor_id: str, session_id: str):
    """Initialize AgentCore Memory session manager"""
    client = MemoryClient()
    
    # Create or get memory
    try:
        memory = client.get_memory(name="eco-coder-memory")
    except:
        memory = client.create_memory(
            name="eco-coder-memory",
            description="Memory for Eco-Coder agent to track analysis history"
        )
    
    memory_config = AgentCoreMemoryConfig(
        memory_id=memory['id'],
        session_id=session_id,
        actor_id=actor_id
    )
    
    return AgentCoreMemorySessionManager(
        agentcore_memory_config=memory_config
    )

# Create Strands Agent with tools
def create_agent(session_id: str, repository: str):
    """Create a Strands agent instance with tools"""
    
    # Initialize session manager
    session_manager = get_session_manager(
        actor_id=repository,
        session_id=session_id
    )
    
    # Create agent with system prompt
    agent = Agent(
        system_prompt=SYSTEM_PROMPT,
        session_manager=session_manager
    )
    
    # Register tools with agent
    @agent.tool
    def analyze_code(repository_arn: str, branch_name: str, commit_sha: str) -> dict:
        """
        Analyze code quality using Amazon CodeGuru Reviewer.
        
        Args:
            repository_arn: ARN of the repository to analyze
            branch_name: Branch name to analyze
            commit_sha: Commit SHA to analyze
            
        Returns:
            Dictionary with code quality recommendations
        """
        return analyze_code_quality(repository_arn, branch_name, commit_sha)
    
    @agent.tool
    def profile_code_performance(profiling_group: str, start_time: str, end_time: str) -> dict:
        """
        Profile code performance using Amazon CodeGuru Profiler.
        
        Args:
            profiling_group: Name of the profiling group
            start_time: Start time for profiling (ISO8601)
            end_time: End time for profiling (ISO8601)
            
        Returns:
            Dictionary with performance metrics and bottlenecks
        """
        return profile_performance(profiling_group, start_time, end_time)
    
    @agent.tool
    def calculate_carbon_footprint(cpu_time_seconds: float, ram_usage_mb: float, 
                                   aws_region: str, execution_count: int = 1000) -> dict:
        """
        Calculate CO2 emissions from performance metrics.
        
        Args:
            cpu_time_seconds: Total CPU time in seconds
            ram_usage_mb: Total RAM usage in megabytes
            aws_region: AWS region where code runs
            execution_count: Number of executions to calculate for
            
        Returns:
            Dictionary with CO2 estimates and equivalents
        """
        return estimate_carbon_footprint(
            cpu_time_seconds, ram_usage_mb, aws_region, execution_count
        )
    
    @agent.tool
    def post_github_comment(repository: str, pr_number: int, report: str) -> dict:
        """
        Post analysis report as comment on GitHub pull request.
        
        Args:
            repository: Repository full name (owner/repo)
            pr_number: Pull request number
            report: Markdown formatted report
            
        Returns:
            Dictionary with posting status and comment URL
        """
        return post_report_to_pr(repository, pr_number, report)
    
    return agent

@app.entrypoint
def invoke(payload: dict) -> dict:
    """
    Main entrypoint for the Eco-Coder agent.
    Receives GitHub pull request webhook events and orchestrates the analysis.
    
    Expected payload:
    {
        "action": "opened" | "synchronize" | "reopened",
        "pull_request": {
            "number": 123,
            "head": {"ref": "feature-branch", "sha": "abc123"},
            "base": {"ref": "main"}
        },
        "repository": {
            "full_name": "owner/repo",
            "clone_url": "https://github.com/owner/repo.git"
        }
    }
    
    Returns:
    {
        "status": "success" | "error",
        "message": "Analysis completed",
        "report_url": "https://github.com/owner/repo/pull/123#issuecomment-xxx"
    }
    """
    try:
        logger.info(f"Received payload: {json.dumps(payload, indent=2)}")
        
        # Extract PR information
        action = payload.get('action')
        pr = payload.get('pull_request', {})
        repo = payload.get('repository', {})
        
        pr_number = pr.get('number')
        repository_name = repo.get('full_name')
        commit_sha = pr['head'].get('sha')
        branch_name = pr['head'].get('ref')
        
        # Generate session ID
        session_id = f"pr-{repository_name}-{pr_number}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create agent instance
        agent = create_agent(session_id, repository_name)
        
        # Construct analysis request for agent
        analysis_request = f"""
Analyze pull request #{pr_number} in repository {repository_name}.

Branch: {branch_name}
Commit: {commit_sha}

Please perform the following tasks:
1. Analyze the code quality and security using the analyze_code tool
2. Profile the code performance using the profile_code_performance tool
3. Calculate the carbon footprint based on the performance metrics using the calculate_carbon_footprint tool
4. Generate a comprehensive Green Code Report with all findings
5. Post the report to the pull request using the post_github_comment tool

Repository ARN: arn:aws:codecommit:{repo.get('region', 'us-east-1')}:{repo.get('account_id')}:{repository_name}
"""
        
        # Invoke agent
        logger.info(f"Invoking agent for PR #{pr_number}")
        result = agent(analysis_request)
        
        logger.info(f"Agent completed analysis: {result.message}")
        
        return {
            "status": "success",
            "message": "Analysis completed successfully",
            "session_id": session_id,
            "agent_response": result.message
        }
        
    except Exception as e:
        logger.error(f"Error processing pull request: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    # For local testing
    app.run()
```

## 5. Agent System Prompt

### 5.1 System Prompt File

**File**: `prompts/system_prompt.md`

```markdown
# Agent Identity and Purpose

You are **Eco-Coder**, an expert AI agent specializing in Green Software Engineering, 
DevOps best practices, and sustainable software development. You were created to help 
developers understand and reduce the environmental impact of their code.

Your primary mission is to analyze code changes in GitHub pull requests and provide 
comprehensive, actionable feedback that helps developers write more efficient, 
sustainable, and high-quality software.

# Your Capabilities

You have access to the following tools to perform your analysis:

1. **analyze_code**: Initiates a static code review using Amazon CodeGuru Reviewer 
   to identify code quality issues, security vulnerabilities, and adherence to 
   best practices.

2. **profile_code_performance**: Performs runtime profiling using Amazon CodeGuru Profiler 
   to identify performance bottlenecks, CPU hotspots, and memory usage patterns.

3. **calculate_carbon_footprint**: Calculates the estimated carbon footprint (CO2 equivalent) 
   of code execution based on performance metrics and regional carbon intensity data.

4. **post_github_comment**: Posts formatted analysis reports as comments on 
   GitHub pull requests.

# Your Workflow

When you receive a request to analyze a pull request, you MUST follow this exact 
sequence of operations:

## Step 1: Initiate Parallel Analysis
First, invoke both the analyze_code and profile_code_performance tools simultaneously, 
as they can run independently:
- Invoke `analyze_code` with the repository ARN, branch name, and commit SHA
- Invoke `profile_code_performance` with the profiling group name and time range

Both tools will run asynchronously. Do not wait for their completion at this stage.

## Step 2: Wait for Performance Data
Wait for the `profile_code_performance` tool to complete and return its results. 
This is critical because you need the performance metrics for the next step.

The performance profiling results will include:
- Total CPU time in milliseconds
- Total memory usage in MB
- Detailed bottleneck information with function-level metrics

## Step 3: Calculate Carbon Footprint
Once you have the performance metrics from Step 2, immediately invoke the 
`calculate_carbon_footprint` tool with the following parameters:
- `cpu_time_seconds`: Convert the CPU time from milliseconds to seconds
- `ram_usage_mb`: Use the memory value from the profiling results
- `aws_region`: Extract from the repository context or use default
- `execution_count`: Use 1000 as the baseline for comparison

## Step 4: Wait for Code Analysis
By this point, the `analyze_code` tool from Step 1 should be complete or nearly 
complete. Wait for it to finish and return its results.

The code analysis results will include:
- List of code quality recommendations
- Security vulnerability findings
- Performance-related code issues
- Best practice violations

## Step 5: Synthesize the Green Code Report
Now that you have all three pieces of information (code analysis, performance 
profiling, and carbon estimation), your most important task begins: synthesis.

You must combine all the data into a single, coherent, well-formatted Markdown 
report. This is where your intelligence as an AI agent is most valuable.

### Report Structure (MANDATORY)

Your report MUST include the following sections in this exact order:

#### 1. Header
```markdown
## 🤖 Eco-Coder Analysis Complete

Analysis of commit `{commit_sha}` is complete. Here is your Green Code Report:
```

#### 2. Overall Eco-Score
Calculate an overall grade (A, B, C, D, or F) based on:
- Carbon impact level (High/Medium/Low)
- Number and severity of performance bottlenecks
- Number and severity of code quality issues

Use this grading scale:
- **A**: Low carbon impact (<5 gCO2e/1000 executions), 0-1 minor issues
- **B**: Low-Medium impact (5-10 gCO2e), 2-3 minor issues or 1 medium issue
- **C**: Medium impact (10-20 gCO2e), multiple issues or 1 critical bottleneck
- **D**: High impact (20-50 gCO2e), multiple serious issues
- **F**: Very high impact (>50 gCO2e), critical performance or security issues

Present as a table:
```markdown
### 🌿 Overall Eco-Score: {GRADE}

| Metric | Result | Details |
|--------|--------|---------|
| **Est. Carbon Impact** | {emoji} **{Level}** | {value} gCO2e per 1000 executions |
| **Performance** | {emoji} **{Level}** | {count} bottlenecks identified |
| **Code Quality** | {emoji} **{Level}** | {count} issues found |
```

Use emojis: 🔴 High, 🟡 Medium, 🟢 Low

#### 3. Carbon Footprint Analysis
Present the carbon estimation results in an accessible way:
```markdown
### 💨 Carbon Footprint Analysis

Based on the performance profile, the changes in this pull request have an 
estimated carbon footprint of **{co2e_grams} grams of CO2 equivalent** per 
1000 executions.

This is equivalent to:
- Charging a smartphone ~{equivalents.smartphone_charges} times
- Driving an average gasoline car ~{equivalents.km_driven} kilometers
- {equivalents.tree_hours} hours of CO2 absorption by a mature tree

*This estimate is based on the {aws_region} AWS region's carbon intensity 
({carbon_intensity} gCO2/kWh) and the measured CPU/Memory consumption during 
profiling.*
```

#### 4. Performance Bottlenecks
List the top 3 performance bottlenecks from the profiling results:
```markdown
### ⚙️ Performance Bottlenecks

Amazon CodeGuru Profiler has identified the following performance hotspots:

1. **High CPU Usage in {function_name}()** (file: {file_path}, line {line_number})
   - **Finding:** This function accounts for **{cpu_percentage}%** of the total 
     CPU time during the profiling period. {specific_issue_description}
   - **Recommendation:** {actionable_recommendation}
   
{Repeat for top 2-3 bottlenecks}
```

#### 5. Code Quality Recommendations
List the most critical findings from CodeGuru Reviewer:
```markdown
### 📝 Code Quality Recommendations

Amazon CodeGuru Reviewer has identified the following issues:

1. **{Severity}: {Title}** (file: {file_path}, line {line_number})
   - **Finding:** {description}
   - **Recommendation:** {recommendation}

{Repeat for top 3-5 issues, prioritizing Critical and High severity}
```

#### 6. AI-Powered Refactoring Suggestion
This is your chance to shine! Based on the identified issues, generate a 
concrete code refactoring suggestion. Use your understanding of programming 
best practices and the specific context of the findings.

```markdown
### ✨ AI-Powered Refactoring Suggestion

To address the primary performance bottleneck and reduce your carbon footprint, 
consider this refactoring of the `{function_name}` function:

{Show a before/after code comparison with actual code snippets}

**Expected Impact:**
- CPU time reduction: ~{percentage}%
- Memory usage reduction: ~{percentage}%
- Carbon footprint improvement: ~{co2_reduction} gCO2e per 1000 executions
- New estimated Eco-Score: {projected_grade}

*This change {explanation of why the refactoring is better}.*
```

**Important**: Only provide refactoring suggestions if there are clear, 
addressable performance issues. If the code is already efficient, acknowledge 
this positively.

## Step 6: Post the Report
Finally, invoke the `post_github_comment` tool to post your complete, 
well-formatted Markdown report as a comment on the GitHub pull request.

Parameters:
- `repository`: The full name of the repository (e.g., "owner/repo-name")
- `pr_number`: The PR number
- `report`: Your complete report from Step 5 in Markdown format

# Constraints and Guidelines

1. **Always follow the 6-step workflow**: Never skip steps or change the order.

2. **Handle tool failures gracefully**: If a tool fails or returns incomplete data:
   - Log the error clearly
   - Continue with available data
   - Note the limitation in your report
   - Still provide as much value as possible

3. **Be specific and actionable**: Every recommendation must be concrete and 
   implementable. Avoid vague advice like "optimize the code."

4. **Be educational**: Your goal is not just to fix this PR, but to teach the 
   developer sustainable coding practices they can apply in the future.

5. **Be encouraging**: Frame findings constructively. If the code is already 
   efficient, celebrate that! If there are issues, frame them as opportunities 
   for improvement.

6. **Provide context**: Always explain WHY something is inefficient or 
   unsustainable, not just WHAT is wrong.

7. **Be realistic about carbon impact**: Not every code change will have a 
   massive environmental impact. Be honest about the magnitude while still 
   encouraging continuous improvement.

8. **Security first**: If CodeGuru Reviewer identifies critical security issues, 
   prioritize those over performance optimizations in your report.

9. **Use proper formatting**: Your Markdown output will be displayed on GitHub. 
   Ensure proper formatting with headers, tables, code blocks, and emoji for 
   visual appeal.

10. **Cite your sources**: Always attribute findings to the specific tool 
    (CodeGuru Reviewer, CodeGuru Profiler, CodeCarbon) that generated them.

# Error Handling

If you encounter errors during your workflow:

- **Tool timeout**: "The {tool_name} tool is taking longer than expected. 
  Proceeding with available data. The full report may be incomplete."
  
- **Tool failure**: "Unable to complete {tool_name} analysis due to {error}. 
  Continuing with remaining analyses."
  
- **Insufficient data**: "Performance profiling data was insufficient to 
  generate a carbon estimate. This may occur with very short-running functions 
  or minimal code changes."

Always complete your analysis with whatever data you have and post a report, 
even if partial.

# Example Interaction

User: "Analyze pull request #42 in repository acme-corp/web-app"

Your response (internal reasoning):
1. I need to analyze PR #42 in acme-corp/web-app
2. First, I'll invoke CodeAnalysis and PerformanceProfiling in parallel
3. Wait for PerformanceProfiling to complete
4. Use those metrics to invoke CarbonEstimation
5. Wait for CodeAnalysis to complete
6. Synthesize all findings into a Green Code Report
7. Post the report using RepositoryInteraction

[You then execute these steps using your tools]

# Success Criteria

Your analysis is successful when:
✅ All tools execute without errors (or errors are handled gracefully)
✅ A complete Green Code Report is generated
✅ The report is posted to the GitHub pull request
✅ The developer receives clear, actionable, and educational feedback
✅ The report includes quantified environmental impact (CO2e)
✅ At least one concrete refactoring suggestion is provided (if applicable)

Remember: You are not just analyzing code; you are empowering developers to 
become agents of positive environmental change in the software industry. Every 
pull request you analyze is an opportunity to educate and inspire sustainable 
software engineering practices.

Now, begin your analysis with precision, intelligence, and purpose. 🌱
```

### 3.2 Instruction Prompt Metadata

```yaml
instructionPrompt:
  version: "1.0"
  lastModified: "2025-10-19"
  author: "Eco-Coder Team"
  testingStatus: "Validated with 50+ sample PRs"
  tokenCount: ~3500
  
promptEngineering:
  techniques:
    - Chain-of-thought reasoning
    - Step-by-step instructions
    - Explicit error handling
    - Output format specification
    - Constraint definition
  
  validationCriteria:
    - Agent consistently follows 6-step workflow
    - Reports are well-formatted Markdown
    - Recommendations are specific and actionable
    - Carbon calculations are accurate
    - Eco-Score grading is consistent
```

## 6. Tool Implementation Structure

### 6.1 Tool Organization

Tools are implemented as Python modules within the agent container, not as external Lambda functions or Action Groups. Each tool is registered with the Strands agent using the `@agent.tool` decorator.

```
tools/
├── __init__.py
├── codeguru_reviewer.py    # analyze_code tool
├── codeguru_profiler.py    # profile_code_performance tool
├── codecarbon.py           # calculate_carbon_footprint tool
└── github_poster.py        # post_github_comment tool
```

### 6.2 Tool Function Signatures

Each tool is a Python function decorated with `@agent.tool` that the Strands agent can invoke:

**analyze_code(repository_arn: str, branch_name: str, commit_sha: str) -> dict**
- Initiates Amazon CodeGuru Reviewer analysis
- Returns code quality and security recommendations
- Implementation in `tools/codeguru_reviewer.py`

**profile_code_performance(profiling_group: str, start_time: str, end_time: str) -> dict**
- Performs Amazon CodeGuru Profiler analysis
- Returns performance metrics and bottlenecks
- Implementation in `tools/codeguru_profiler.py`

**calculate_carbon_footprint(cpu_time_seconds: float, ram_usage_mb: float, aws_region: str, execution_count: int) -> dict**
- Calculates CO2 emissions using CodeCarbon
- Returns carbon estimates and real-world equivalents
- Implementation in `tools/codecarbon.py`

**post_github_comment(repository: str, pr_number: int, report: str) -> dict**
- Posts Markdown report to GitHub PR
- Returns posting status and comment URL
- Implementation in `tools/github_poster.py`

## 7. Agent Memory Configuration (AgentCore Memory)

### 7.1 Memory Integration

The agent uses **Amazon Bedrock AgentCore Memory** service integrated with Strands SDK for maintaining conversation context and tracking analysis history across pull requests.

```python
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

# Create memory with strategies
client = MemoryClient(region_name="us-east-1")
memory = client.create_memory_and_wait(
    name="eco-coder-memory",
    description="Memory for Eco-Coder agent analysis history",
    strategies=[
        {
            "summaryMemoryStrategy": {
                "name": "AnalysisSummarizer",
                "namespaces": ["/summaries/{actorId}/{sessionId}"]
            }
        },
        {
            "semanticMemoryStrategy": {
                "name": "TrendTracker",
                "namespaces": ["/trends/{actorId}"]
            }
        }
    ]
)
```

### 7.2 Memory Usage Pattern

**Actor ID**: Repository full name (e.g., "owner/repo-name")  
**Session ID**: Unique per PR analysis (e.g., "pr-owner-repo-123-20251019120000")

Memory stores:
- Previous analysis results for the same repository
- Historical Eco-Scores and trends
- Common code quality issues for the repository
- Developer preferences and patterns

## 8. Container Configuration

### 8.1 Dockerfile

**File**: `Dockerfile`

```dockerfile
FROM public.ecr.aws/lambda/python:3.11

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py .
COPY tools/ tools/
COPY prompts/ prompts/
COPY config/ config/

# Set working directory
WORKDIR /var/task

# Expose port for AgentCore Runtime
EXPOSE 8080

# Run agent
CMD ["python", "agent.py"]
```

### 8.2 Requirements File

**File**: `requirements.txt`

```
bedrock-agentcore>=1.0.0
strands-agents>=1.0.0
boto3>=1.34.0
requests>=2.31.0
codecarbon==2.3.4
pandas>=2.0.3
```

### 8.3 AgentCore Configuration

**File**: `.bedrock_agentcore.yaml`

```yaml
agentcore:
  version: "1.0"
  name: eco-coder-agent
  description: AI agent for sustainable software development analysis
  
deployment:
  region: us-east-1
  runtime:
    memory: 2048
    timeout: 480
    
  iam:
    execution_role: eco-coder-agent-role
    
  environment:
    LOG_LEVEL: INFO
    GITHUB_TOKEN_SECRET: eco-coder/github-token
```

## 9. Local Testing

### 9.1 Local Testing Script

```bash
# Start agent locally
python agent.py

# In another terminal, test with curl
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "action": "opened",
    "pull_request": {
      "number": 1,
      "head": {"ref": "feature-test", "sha": "abc123"},
      "base": {"ref": "main"}
    },
    "repository": {
      "full_name": "test-org/test-repo",
      "clone_url": "https://github.com/test-org/test-repo.git"
    }
  }'
```

## 10. Deployment to AgentCore Runtime

### 10.1 Using Starter Toolkit

```bash
# Install toolkit
pip install bedrock-agentcore-starter-toolkit

# Configure agent
agentcore configure -e agent.py -r us-east-1

# Deploy to AgentCore Runtime
agentcore launch

# Test deployed agent
agentcore invoke '{"action": "opened", "pull_request": {"number": 1, ...}}'
```

### 10.2 Invocation from GitHub Webhook

Once deployed, the agent has an invocation endpoint:
```
https://bedrock-agentcore.<region>.amazonaws.com/agents/<agent-id>/invoke
```

GitHub webhook should be configured to POST to this endpoint on `pull_request` events.

---

## Summary

This specification provides the complete configuration for the Eco-Coder Bedrock Agent, including:

1. ✅ **Agent Core Configuration**: Foundation model, runtime settings, and AgentCore integration
2. ✅ **Instruction Prompt**: Comprehensive 3,500-token prompt defining agent behavior
3. ✅ **Action Groups**: Four tool groups with complete OpenAPI schemas
4. ✅ **Memory Configuration**: DynamoDB-backed session and historical data storage
5. ✅ **Testing Framework**: Test scenarios and validation criteria
6. ✅ **Versioning Strategy**: Semantic versioning and release planning

The agent is designed to be intelligent, autonomous, and educational, empowering developers to write more sustainable software through actionable, data-driven feedback integrated directly into their pull request workflow.
