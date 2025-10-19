# Eco-Coder Architecture Specification

## 1. Overview

This document defines the detailed system architecture for Eco-Coder, an AI agent that analyzes code in pull requests for performance, quality, and environmental impact. The architecture is built on **AWS Bedrock AgentCore Runtime** with **Strands Agents SDK** and follows cloud-native, serverless design principles.

The agent is deployed as a containerized application running in AgentCore Runtime, with tools implemented as internal Python functions rather than external Lambda services.

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          GitHub Repository                               │
│                     (Developer creates Pull Request)                     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                │ Webhook Event (JSON payload)
                                │ pull_request: {opened, synchronize, reopened}
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitHub Webhook Configuration                     │
│                    Webhook URL: AgentCore Runtime Endpoint               │
│                    Secret: Stored in GitHub                              │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                │ HTTPS POST (authenticated)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              Amazon Bedrock AgentCore Runtime Service                    │
│              Endpoint: https://bedrock-agentcore.{region}.amazonaws.com  │
│                       /agents/{agent-arn}/invoke                         │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                  Isolated MicroVM Session                         │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │           Eco-Coder Strands Agent (Container)               │ │  │
│  │  │                                                             │ │  │
│  │  │  Foundation Model: Claude 3 Sonnet                         │ │  │
│  │  │  Framework: Strands Agents SDK                             │ │  │
│  │  │  Runtime: Python 3.11                                      │ │  │
│  │  │                                                             │ │  │
│  │  │  ┌──────────────────────────────────────────────────────┐  │ │  │
│  │  │  │  Agent Orchestration (agent.py)                      │  │ │  │
│  │  │  │  - Receive GitHub webhook payload                    │  │ │  │
│  │  │  │  - Parse PR context (repo, branch, commit)           │  │ │  │
│  │  │  │  - Reason and plan analysis workflow                 │  │ │  │
│  │  │  │  - Orchestrate tool invocations                      │  │ │  │
│  │  │  │  - Generate comprehensive report                     │  │ │  │
│  │  │  │  - Return results                                    │  │ │  │
│  │  │  └──────────────────────────────────────────────────────┘  │ │  │
│  │  │                                                             │ │  │
│  │  │  ┌──────────────────────────────────────────────────────┐  │ │  │
│  │  │  │  Internal Tools (Python functions)                   │  │ │  │
│  │  │  │                                                       │  │ │  │
│  │  │  │  @agent.tool                                         │  │ │  │
│  │  │  │  ├─ analyze_code()                                   │  │ │  │
│  │  │  │  │  └─> boto3.client('codeguru-reviewer')           │  │ │  │
│  │  │  │  │                                                   │  │ │  │
│  │  │  │  ├─ profile_code_performance()                      │  │ │  │
│  │  │  │  │  └─> boto3.client('codeguru-profiler')           │  │ │  │
│  │  │  │  │                                                   │  │ │  │
│  │  │  │  ├─ calculate_carbon_footprint()                    │  │ │  │
│  │  │  │  │  └─> codecarbon.EmissionsTracker                 │  │ │  │
│  │  │  │  │                                                   │  │ │  │
│  │  │  │  └─ post_github_comment()                           │  │ │  │
│  │  │  │     └─> requests.post(github_api)                   │  │ │  │
│  │  │  └──────────────────────────────────────────────────────┘  │ │  │
│  │  │                                                             │ │  │
│  │  │  ┌──────────────────────────────────────────────────────┐  │ │  │
│  │  │  │  AgentCore Memory Integration                        │  │ │  │
│  │  │  │  - Session state management                          │  │ │  │
│  │  │  │  - Context persistence                               │  │ │  │
│  │  │  │  - Conversation history                              │  │ │  │
│  │  │  └──────────────────────────────────────────────────────┘  │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  Direct Connections from Agent Container:                            │
│  ├─> Amazon CodeGuru Reviewer API (boto3)                           │
│  ├─> Amazon CodeGuru Profiler API (boto3)                           │
│  ├─> GitHub API (requests)                                           │
│  └─> Amazon Bedrock AgentCore Memory (managed service)              │
└───────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     Supporting Infrastructure                            │
│  - CloudWatch Logs (agent execution logs)                               │
│  - X-Ray (distributed tracing)                                          │
│  - Systems Manager Parameter Store (config/carbon data)                 │
│  - Secrets Manager (GitHub PAT)                                         │
│  - Amazon Bedrock AgentCore Memory (session state)                      │
│  - ECR (container image registry)                                       │
│  - IAM (agent execution role with service permissions)                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Key Architectural Principles

**1. Containerized Agent Deployment**
- Agent runs as a Docker container in AgentCore Runtime
- All tools are internal Python functions, not external services
- Single deployment unit with all dependencies bundled

**2. Direct Service Integration**
- Agent makes direct API calls to AWS services using boto3
- No intermediate Lambda functions or API Gateway layers
- Simplified architecture with fewer moving parts

**3. Strands Framework Integration**
- Tools defined using `@agent.tool` decorator
- Framework-agnostic LLM integration
- Built-in session management with AgentCore Memory

**4. Serverless Execution Model**
- AgentCore Runtime provides isolated microVM per invocation
- Automatic scaling based on demand
- Up to 8-hour execution time per session
- 100MB payload support

## 3. Component Specifications

### 3.1 Amazon Bedrock AgentCore Runtime

**Purpose**: Serverless hosting environment for containerized Strands agent

**Service Features**:
- **Isolation**: Each invocation runs in isolated microVM
- **Scalability**: Automatic scaling based on demand
- **Long-running**: Up to 8 hours execution time
- **Large payloads**: Up to 100MB request/response
- **Framework agnostic**: Works with any agent framework (Strands, LangGraph, etc.)
- **Model flexibility**: Use any LLM (Bedrock, Anthropic, OpenAI, etc.)

**Agent Configuration**:
- **Agent Name**: `eco-coder-agent`
- **Foundation Model**: `anthropic.claude-3-sonnet-20240229-v1:0`
- **Framework**: Strands Agents SDK
- **Runtime**: Python 3.11
- **Container**: Docker image stored in Amazon ECR

**Model Parameters**:
- Temperature: 0.1 (for deterministic code analysis)
- Max Tokens: 4096
- Top P: 0.9
- Stop Sequences: Custom sequences for tool invocation

**Invocation Endpoint**:
```
POST https://bedrock-agentcore.{region}.amazonaws.com/agents/{agent-arn}/invoke
Authorization: AWS Signature v4
Content-Type: application/json

{
  "sessionId": "string",
  "inputText": "string",
  "sessionState": {}
}
```

**Response Format**:
```json
{
  "sessionId": "string",
  "completion": "string",
  "sessionState": {},
  "trace": {},
  "contentType": "text/plain"
}
```

**AgentCore Features Utilized**:
- **MicroVM Isolation**: Each webhook invocation gets isolated execution
- **Memory Integration**: Managed session state via AgentCore Memory
- **Observability**: Built-in logging and tracing to CloudWatch
- **Security**: IAM-based authentication and authorization
- **Container Management**: Automatic container lifecycle management

### 3.2 Strands Agent Container

**Purpose**: Containerized application containing the agent logic and all tools

**Base Image**: `python:3.11-slim`

**Container Contents**:
```
/app/
├── agent.py                 # Main agent entrypoint
├── system_prompt.txt        # System instructions
├── tools/
│   ├── __init__.py
│   ├── codeguru_reviewer.py    # CodeGuru Reviewer integration
│   ├── codeguru_profiler.py    # CodeGuru Profiler integration
│   ├── codecarbon_estimator.py # Carbon footprint calculation
│   └── github_poster.py        # GitHub API integration
├── utils/
│   ├── __init__.py
│   ├── github_parser.py     # Parse webhook payloads
│   └── report_generator.py  # Format analysis reports
├── requirements.txt         # Python dependencies
└── .bedrock_agentcore.yaml  # AgentCore configuration
```

**Key Dependencies**:
```txt
strands==1.2.0
bedrock-agentcore==1.0.0
boto3==1.34.0
codecarbon==2.3.4
requests==2.31.0
```

**Agent Execution Role**: `EcoCoderAgentExecutionRole`

**IAM Permissions Required**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "codeguru-reviewer:CreateCodeReview",
        "codeguru-reviewer:DescribeCodeReview",
        "codeguru-reviewer:ListRecommendations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "codeguru-profiler:ConfigureAgent",
        "codeguru-profiler:GetProfile",
        "codeguru-profiler:GetRecommendations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:eco-coder/github-token-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/eco-coder/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/bedrock/agentcore/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
    }
  ]
}
```

**Environment Variables**:
- `AWS_REGION`: AWS region for service calls
- `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, ERROR)
- `GITHUB_TOKEN_SECRET_ARN`: ARN of GitHub token in Secrets Manager
- `CARBON_DATA_PARAMETER_PATH`: Parameter Store path for carbon intensity data

### 3.3 Internal Tool Implementations

All tools are Python functions within the agent container, decorated with `@agent.tool` from Strands SDK. They are NOT separate Lambda functions.

#### 3.3.1 CodeGuru Reviewer Tool

#### 3.3.1 CodeGuru Reviewer Tool

**File**: `tools/codeguru_reviewer.py`

**Purpose**: Initiate code review and retrieve recommendations using Amazon CodeGuru Reviewer API

**Function Signature**:
```python
@agent.tool
def analyze_code(
    repository_arn: str,
    branch_name: str,
    commit_sha: str
) -> dict:
    """
    Analyze code quality using Amazon CodeGuru Reviewer.
    
    Args:
        repository_arn: ARN of the repository (CodeCommit or S3)
        branch_name: Git branch name
        commit_sha: Git commit SHA to analyze
        
    Returns:
        Dictionary containing review results with recommendations
    """
```

**Implementation**:
- Direct boto3 client call to `codeguru-reviewer`
- Polls CodeGuru API until review completes (with timeout)
- Handles pagination for large result sets
- Formats recommendations into structured output

**Output Structure**:
```python
{
  "review_id": str,
  "status": "Completed" | "Failed",
  "recommendations": [
    {
      "file_path": str,
      "start_line": int,
      "end_line": int,
      "severity": "Critical" | "High" | "Medium" | "Low",
      "category": "CodeQuality" | "Security" | "Performance" | "BestPractices",
      "description": str,
      "recommendation": str
    }
  ],
  "total_recommendations": int
}
```

**Error Handling**:
- Timeout after 5 minutes → Return partial results
- API throttling → Exponential backoff with retries
- Invalid repository → Return error message to agent

#### 3.3.2 CodeGuru Profiler Tool

**File**: `tools/codeguru_profiler.py`

**Purpose**: Profile code performance and identify bottlenecks using Amazon CodeGuru Profiler API

**Function Signature**:
```python
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
        Dictionary containing performance metrics and bottlenecks
    """
```

**Implementation**:
- Direct boto3 client call to `codeguru-profiler`
- Retrieves aggregated profile data for time period
- Identifies top CPU and memory consumers
- Generates flame graph URL if available

**Output Structure**:
```python
{
  "profiling_id": str,
  "total_cpu_time_ms": float,
  "total_memory_mb": float,
  "bottlenecks": [
    {
      "function_name": str,
      "file_path": str,
      "line_number": int,
      "cpu_percentage": float,
      "self_time_ms": float,
      "total_time_ms": float,
      "invocation_count": int
    }
  ],
  "flame_graph_url": str
}
```

#### 3.3.3 CodeCarbon Estimation Tool

**File**: `tools/codecarbon_estimator.py`

**Purpose**: Calculate CO2 emissions from performance metrics using CodeCarbon library

**Function Signature**:
```python
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
        Dictionary containing CO2e estimates and equivalents
    """
```

**Implementation**:
- Uses codecarbon library for calculation
- Fetches regional carbon intensity from Parameter Store (cached 24h)
- Calculates energy consumption based on CPU and memory
- Provides relatable equivalents (phone charges, km driven, etc.)

**Output Structure**:
```python
{
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
```

**Carbon Intensity Data Source**:
- Parameter Store: `/eco-coder/carbon-intensity/{region}`
- TTL: 24 hours
- Fallback: Use regional average if data unavailable

#### 3.3.4 GitHub Poster Tool

**File**: `tools/github_poster.py`

**Purpose**: Post analysis report as comment on GitHub PR

**Function Signature**:
```python
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
        repository_full_name: Owner/repo format
        pull_request_number: PR number
        report_markdown: Formatted report in Markdown
        update_existing: Update existing bot comment if found
        
    Returns:
        Dictionary containing comment status and URL
    """
```

**Implementation**:
- Retrieves GitHub PAT from Secrets Manager
- Uses requests library to call GitHub REST API
- If update_existing=True, searches for existing bot comment
- Updates existing or creates new comment

**Output Structure**:
```python
{
  "status": "success" | "failure",
  "comment_id": int,
  "comment_url": str,
  "error_message": str  # Only if status is "failure"
}
```

**Authentication**:
- GitHub Personal Access Token from Secrets Manager
- ARN: `arn:aws:secretsmanager:{region}:{account}:secret:eco-coder/github-token`
- Required scopes: `repo`, `write:discussion`

## 4. Data Flow Sequence

### 4.1 Happy Path Flow

1. **Developer Action**: Creates or updates a pull request in GitHub

2. **GitHub Webhook**: Sends HTTPS POST request to AgentCore Runtime endpoint
   ```
   POST https://bedrock-agentcore.{region}.amazonaws.com/agents/{agent-arn}/invoke
   Headers:
     - X-Hub-Signature-256: {signature}
     - Content-Type: application/json
   Body:
     - action: "opened" | "synchronize" | "reopened"
     - pull_request: {number, head, base, ...}
     - repository: {full_name, clone_url, ...}
   ```

3. **AgentCore Runtime**: Validates request and creates isolated microVM session

4. **Agent Container Bootstrap**:
   - Loads Strands agent from container
   - Initializes session with AgentCore Memory
   - Loads system prompt and tool definitions

5. **Agent Entrypoint** (`@app.entrypoint`):
   - Receives GitHub webhook payload
   - Parses PR context (repo, branch, commit SHA, PR number)
   - Creates analysis request for the agent
   - Initializes agent session

6. **Strands Agent Orchestration**:
   - Agent receives task: "Analyze PR #{number} in {repo}: {title}"
   - LLM reasons about the task and formulates plan
   - Identifies tools needed: analyze_code, profile_code_performance, calculate_carbon_footprint, post_github_comment

7. **Tool Execution - Code Analysis** (Internal function call, not external service):
   - Agent invokes `analyze_code()` tool
   - Tool function makes boto3 call to CodeGuru Reviewer API
   - Polls for results (async with timeout)
   - Returns structured recommendations to agent

8. **Tool Execution - Performance Profiling**:
   - Agent invokes `profile_code_performance()` tool
   - Tool function makes boto3 call to CodeGuru Profiler API
   - Retrieves performance metrics and bottlenecks
   - Returns performance data to agent

9. **Tool Execution - Carbon Calculation**:
   - Agent invokes `calculate_carbon_footprint()` tool
   - Tool function uses codecarbon library
   - Fetches regional carbon intensity from Parameter Store
   - Calculates CO2e emissions
   - Returns carbon footprint data to agent

10. **Report Synthesis**:
    - Agent receives results from all tools
    - LLM synthesizes data into comprehensive analysis
    - Generates Markdown-formatted report with:
      * Code quality findings
      * Performance bottlenecks
      * Carbon footprint estimate
      * Actionable recommendations

11. **Tool Execution - Post to GitHub**:
    - Agent invokes `post_github_comment()` tool
    - Tool retrieves GitHub PAT from Secrets Manager
    - Makes REST API call to GitHub
    - Posts report as PR comment
    - Returns success confirmation

12. **Session Completion**:
    - Agent returns final result to entrypoint
    - Session state persisted to AgentCore Memory
    - AgentCore Runtime returns response to GitHub webhook
    - Returns 200 OK with completion status

13. **Developer**: Sees Eco-Coder analysis report in PR comments

### 4.2 Error Handling Flows

**Scenario 1: CodeGuru Reviewer times out**
```
1. analyze_code() tool hits 5-minute timeout
2. Tool function returns error dict:
   {"status": "timeout", "message": "CodeGuru review timed out", "partial_results": [...]}
3. Agent's LLM receives error response
4. LLM reasons: "CodeGuru unavailable, continue with other tools"
5. Agent proceeds to call profile_code_performance()
6. Agent generates report noting:
   "⚠️ Code quality analysis unavailable (timeout). Performance and carbon analysis below."
7. Report still includes actionable profiler and carbon data
```

**Scenario 2: GitHub API rate limit hit**
```
1. post_github_comment() tool receives 403 Forbidden
2. Tool implements retry with exponential backoff:
   - Attempt 1: Wait 1 second, retry
   - Attempt 2: Wait 2 seconds, retry
   - Attempt 3: Wait 4 seconds, retry
3. If all retries fail:
   - Tool returns error to agent
   - Agent logs: "Failed to post comment, rate limited"
   - Agent returns completion with posting_failed=true
4. CloudWatch alarm triggers for investigation
5. Report can be manually retrieved from CloudWatch logs
```

**Scenario 3: Invalid GitHub webhook signature**
```
1. AgentCore Runtime receives webhook with invalid signature
2. Agent entrypoint validates signature using GitHub webhook secret
3. Returns 401 Unauthorized immediately
4. No agent session created, no cost incurred
5. GitHub webhook dashboard shows failed delivery
```

**Scenario 4: Container startup failure**
```
1. AgentCore Runtime attempts to start container
2. Container fails to start (missing dependency, etc.)
3. Runtime returns 500 Internal Server Error
4. CloudWatch logs capture container error
5. X-Ray shows failed cold start
6. On-call engineer receives alert
```

**Scenario 5: LLM API error (Bedrock throttling)**
```
1. Agent attempts to call Claude via Bedrock
2. Bedrock returns ThrottlingException
3. Strands SDK implements automatic retry with backoff
4. If retries exhausted:
   - Agent returns error response
   - Session state saved to AgentCore Memory
   - Can resume later with same session ID
```

## 5. Security Architecture

### 5.1 Identity and Access Management

**Service Roles**:

1. **Agent Execution Role** (`EcoCoderAgentExecutionRole`)
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Service": "bedrock.amazonaws.com"
         },
         "Action": "sts:AssumeRole",
         "Condition": {
           "StringEquals": {
             "aws:SourceAccount": "{account-id}"
           },
           "ArnLike": {
             "aws:SourceArn": "arn:aws:bedrock:*:{account-id}:agent/*"
           }
         }
       }
     ]
   }
   ```
   
   **Permissions**:
   - CodeGuru Reviewer: `CreateCodeReview`, `DescribeCodeReview`, `ListRecommendations`
   - CodeGuru Profiler: `ConfigureAgent`, `GetProfile`, `GetRecommendations`
   - Secrets Manager: `GetSecretValue` (GitHub token only)
   - Parameter Store: `GetParameter`, `GetParameters` (carbon data only)
   - CloudWatch Logs: `CreateLogGroup`, `CreateLogStream`, `PutLogEvents`
   - Bedrock: `InvokeModel` (Claude 3 Sonnet only)
   - X-Ray: `PutTraceSegments`, `PutTelemetryRecords`

2. **Container Registry Role** (`EcoCoderECRAccessRole`)
   - Used by AgentCore Runtime to pull container image
   - Assume role policy: Bedrock service
   - Permissions: `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, `ecr:GetAuthorizationToken`

3. **GitHub Webhook Authentication**
   - Not an IAM role - uses HMAC signature validation
   - Shared secret stored in both GitHub webhook config and agent code
   - Validates `X-Hub-Signature-256` header

**Principle of Least Privilege**:
- Agent role has only necessary permissions for tool execution
- Resource-level restrictions where possible (e.g., specific secret ARNs)
- No Lambda execution roles needed (no separate Lambda functions)
- No API Gateway execution role (no API Gateway)

### 5.2 Data Protection

**In Transit**:
- All API calls use HTTPS/TLS 1.3
- GitHub webhook to AgentCore Runtime: TLS with signature validation
- Agent to AWS services: AWS SigV4 authentication over HTTPS
- Agent to GitHub API: HTTPS with bearer token authentication

**At Rest**:
- CloudWatch Logs: Encrypted with AWS KMS (customer-managed key)
- Secrets Manager: Encrypted with AWS KMS (automatic encryption)
- AgentCore Memory: Encrypted at rest by AWS managed service
- Parameter Store: SecureString parameters with KMS encryption
- ECR: Container images encrypted at rest

**Secrets Management**:
- GitHub Personal Access Token stored in AWS Secrets Manager
- Secret ARN: `arn:aws:secretsmanager:{region}:{account}:secret:eco-coder/github-token`
- Automatic rotation every 90 days (via Lambda rotation function)
- Audit logging: All GetSecretValue calls logged to CloudTrail
- Access restricted to agent execution role only

**Data Classification**:
- **Confidential**: Source code content (never persisted, only analyzed in-memory)
- **Internal**: PR metadata, analysis results (retained 90 days in CloudWatch)
- **Public**: Carbon footprint calculations (posted to public GitHub PRs)

### 5.3 Network Security

**AgentCore Runtime Network Isolation**:
- Containers run in isolated microVMs (Firecracker)
- No direct VPC access required
- AgentCore Runtime provides secure network egress to AWS services
- Internet access for GitHub API calls (controlled by runtime)

**No VPC Configuration Required**:
- AgentCore Runtime is fully managed
- Uses AWS PrivateLink for AWS service communication
- No security groups or NACLs to configure
- Simplified network architecture

**GitHub Webhook Security**:
- HMAC-SHA256 signature validation (X-Hub-Signature-256 header)
- Shared secret stored securely
- No IP allowlisting needed (signature validation is sufficient)
- Request logging for audit trail

## 6. Monitoring and Observability

### 6.1 CloudWatch Metrics

**AgentCore Runtime Metrics** (Namespace: `AWS/BedrockAgentCore`):
- `AgentInvocations`: Count of agent invocations
- `AgentDuration`: Time from invocation to completion (milliseconds)
- `AgentErrors`: Count of agent execution errors
- `AgentThrottles`: Count of throttled invocations
- `SessionCount`: Active session count
- `TokensUsed`: Input and output tokens consumed

**Custom Application Metrics** (Namespace: `EcoCoder`):
- `ToolInvocation`: Count by tool name (analyze_code, profile_code_performance, etc.)
- `ToolDuration`: Execution time per tool (milliseconds)
- `ToolErrors`: Error count per tool
- `CodeGuruReviewTime`: Time for CodeGuru review completion
- `CodeGuruRecommendations`: Count of recommendations returned
- `CarbonFootprintCalculated`: CO2e grams calculated per PR
- `GitHubCommentPosted`: Success/failure count

**Dimensions**:
- `AgentName`: eco-coder-agent
- `ToolName`: analyze_code | profile_code_performance | calculate_carbon_footprint | post_github_comment
- `ErrorType`: timeout | throttle | api_error | validation_error
- `Repository`: owner/repo

### 6.2 CloudWatch Logs

**Log Groups**:
- `/aws/bedrock/agentcore/eco-coder-agent`: All agent execution logs
  * Agent invocation events
  * Tool execution logs
  * LLM reasoning traces (if enabled)
  * Error stack traces
  * Session state transitions

**Log Retention**: 
- Development: 7 days
- Production: 90 days

**Structured Logging Format**:
```json
{
  "timestamp": "2025-10-19T10:30:45.123Z",
  "level": "INFO",
  "session_id": "abc123",
  "request_id": "def456",
  "component": "analyze_code_tool",
  "message": "CodeGuru review completed",
  "context": {
    "repository": "owner/repo",
    "pr_number": 123,
    "commit_sha": "a1b2c3d",
    "review_id": "review123",
    "recommendations_count": 15,
    "duration_ms": 45000
  }
}
```

**Log Insights Queries**:

1. **Average tool execution time**:
```
fields @timestamp, component, context.duration_ms
| filter component like /tool/
| stats avg(context.duration_ms) by component
```

2. **Error rate by component**:
```
fields @timestamp, level, component, message
| filter level = "ERROR"
| stats count() by component
```

3. **Carbon footprint trends**:
```
fields @timestamp, context.co2e_grams, context.repository
| filter component = "calculate_carbon_footprint_tool"
| stats avg(context.co2e_grams) by bin(5m)
```

### 6.3 AWS X-Ray Tracing

**Trace Structure**:
```
AgentCore Runtime Invocation (root span)
└── Eco-Coder Agent Execution
    ├── Parse GitHub Webhook (subsegment)
    ├── Initialize Agent Session (subsegment)
    ├── LLM Reasoning - Task Planning (subsegment)
    ├── Tool: analyze_code (subsegment)
    │   ├── CodeGuru CreateCodeReview API (subsegment)
    │   └── CodeGuru DescribeCodeReview API (subsegment)
    ├── Tool: profile_code_performance (subsegment)
    │   └── CodeGuru Profiler GetProfile API (subsegment)
    ├── LLM Reasoning - Data Synthesis (subsegment)
    ├── Tool: calculate_carbon_footprint (subsegment)
    │   └── Parameter Store GetParameter (subsegment)
    ├── LLM Reasoning - Report Generation (subsegment)
    ├── Tool: post_github_comment (subsegment)
    │   ├── Secrets Manager GetSecretValue (subsegment)
    │   └── GitHub API POST comment (subsegment)
    └── Persist Session State (subsegment)
```

**Custom Annotations** (for filtering):
- `repository`: "owner/repo"
- `pr_number`: 123
- `session_id`: "abc123"
- `agent_version`: "1.0.0"

**Custom Metadata**:
- `commit_sha`: Full commit SHA
- `recommendations_count`: Number of code issues found
- `co2e_grams`: Carbon footprint calculated
- `model_used`: Foundation model identifier

### 6.4 CloudWatch Alarms

**Critical Alarms** (SNS → PagerDuty):

1. **High Error Rate**
   - Metric: `AWS/BedrockAgentCore/AgentErrors`
   - Threshold: > 5 errors in 5 minutes
   - Action: Page on-call engineer

2. **Agent Timeout**
   - Metric: `AWS/BedrockAgentCore/AgentDuration`
   - Threshold: p99 > 10 minutes
   - Action: Page on-call engineer

3. **GitHub Posting Failures**
   - Metric: `EcoCoder/GitHubCommentPosted` (failure count)
   - Threshold: > 3 failures in 5 minutes
   - Action: Page on-call engineer

**Warning Alarms** (SNS → Email):

1. **Elevated Duration**
   - Metric: `AWS/BedrockAgentCore/AgentDuration`
   - Threshold: p95 > 5 minutes
   - Action: Email team

2. **CodeGuru Timeout Rate**
   - Metric: `EcoCoder/ToolErrors` (dimension: ToolName=analyze_code)
   - Threshold: > 2 timeouts in 10 minutes
   - Action: Email team

3. **Token Usage Spike**
   - Metric: `AWS/BedrockAgentCore/TokensUsed`
   - Threshold: > 100K tokens in 5 minutes
   - Action: Email team (cost concern)

4. **Throttling Detected**
   - Metric: `AWS/BedrockAgentCore/AgentThrottles`
   - Threshold: > 0 in 5 minutes
   - Action: Email team (need quota increase)

### 6.5 Operational Dashboards

**Main Operational Dashboard** (`eco-coder-operations`):

Widgets:
1. **Agent Invocations** (line graph, 24h)
   - Metric: AgentInvocations
   - Stat: Sum per 5 minutes

2. **Success Rate** (number, 24h)
   - Formula: (Total Invocations - Errors) / Total Invocations × 100
   - Color: Green > 95%, Yellow 90-95%, Red < 90%

3. **Average Analysis Duration** (line graph, 24h)
   - Metric: AgentDuration
   - Stats: p50, p95, p99

4. **Top Errors** (pie chart, 24h)
   - Metric: AgentErrors
   - Dimension: ErrorType

5. **GitHub Comment Success Rate** (number, 24h)
   - Metric: GitHubCommentPosted (success vs failure)

6. **Active Sessions** (line graph, real-time)
   - Metric: SessionCount

**Performance Dashboard** (`eco-coder-performance`):

Widgets:
1. **Tool Execution Breakdown** (stacked area chart, 24h)
   - Metrics: ToolDuration by ToolName
   - Shows which tool takes longest

2. **CodeGuru Review Time** (line graph, 24h)
   - Metric: CodeGuruReviewTime
   - Stats: p50, p95, p99

3. **LLM Token Usage** (line graph, 24h)
   - Metric: TokensUsed (input and output)
   - Useful for cost tracking

4. **Carbon Footprint Calculated** (line graph, 24h)
   - Metric: CarbonFootprintCalculated
   - Shows average CO2e per PR

5. **Tool Success Rate** (horizontal bar chart, 24h)
   - Success rate per tool

**Cost Dashboard** (`eco-coder-costs`):

Widgets:
1. **Estimated Daily Cost** (number)
   - Formula: Token usage × $0.003/1K + AgentCore runtime costs

2. **Cost Breakdown** (pie chart)
   - AgentCore Runtime
   - Claude 3 Sonnet tokens
   - CodeGuru Reviewer
   - CodeGuru Profiler
   - Other AWS services

3. **PRs Analyzed** (number, 24h)
   - Total count of unique PR analyses

4. **Cost per PR** (number, 24h)
   - Estimated cost / PRs analyzed

## 7. Scalability and Performance

### 7.1 Scaling Characteristics

**AgentCore Runtime**:
- Fully managed, automatic scaling
- No concurrency limits to configure
- Scales to handle webhook traffic spikes
- Isolated microVM per invocation (no cold start contention)
- Concurrent invocations: Limited only by account quotas

**Bedrock Model Invocations**:
- Quota: 10,000 requests/minute for Claude 3 Sonnet (adjustable)
- Token throughput: Monitor and request increase if needed
- Automatic retry with exponential backoff on throttles

**CodeGuru Services**:
- CodeGuru Reviewer: 1,000 reviews/day (default quota)
- CodeGuru Profiler: No hard limits on API calls
- Both services scale automatically

**Container Image Pull**:
- ECR automatically scales
- Image cached by AgentCore Runtime after first pull
- Cold start only on first invocation or after deployment

### 7.2 Performance Targets

| Operation | Target | Measurement | Notes |
|-----------|--------|-------------|-------|
| GitHub webhook to agent start | < 2s | p95 | AgentCore Runtime overhead |
| Container cold start | < 10s | p95 | First invocation or after deploy |
| Container warm start | < 1s | p95 | Subsequent invocations |
| Full agent analysis | < 5 minutes | p95 | End-to-end including all tools |
| CodeGuru Reviewer | < 3 minutes | p95 | Depends on PR size |
| CodeGuru Profiler | < 2 minutes | p95 | Depends on profile size |
| CodeCarbon calculation | < 5s | p95 | Pure computation |
| GitHub comment posting | < 5s | p95 | Depends on GitHub API latency |
| Total PR analysis time | < 6 minutes | p95 | Including cold start |

### 7.3 Performance Optimization Strategies

**1. Container Image Optimization**:
- Multi-stage Docker build to minimize image size
- Use slim base images (python:3.11-slim vs python:3.11)
- Layer caching for faster builds
- Target image size: < 500 MB

**2. Parallel Tool Execution** (future enhancement):
- Run CodeGuru Reviewer and Profiler concurrently
- Use asyncio for parallel boto3 calls
- Reduce total analysis time by ~40%

**3. Prompt Optimization**:
- Minimize system prompt length (reduce input tokens)
- Use structured output for tool responses
- Implement few-shot examples for consistent formatting

**4. CodeGuru Result Caching**:
- Cache results by commit SHA in Parameter Store
- Avoid re-analyzing unchanged commits
- TTL: 7 days
- Reduces CodeGuru API costs

**5. Session State Management**:
- Use AgentCore Memory for multi-turn sessions
- Resume sessions for partial failures
- Avoid re-executing completed tools

### 7.4 Caching Strategy

**Carbon Intensity Data** (Parameter Store):
```
Key: /eco-coder/carbon-intensity/{region}
Value: {"gco2_per_kwh": 475, "updated": "2025-10-19T00:00:00Z"}
TTL: 24 hours
Cache miss: Fetch from AWS Customer Carbon Footprint Tool API
```

**CodeGuru Results** (Parameter Store):
```
Key: /eco-coder/codeguru-cache/{commit_sha}
Value: {Compressed JSON of recommendations}
TTL: 7 days
Cache hit rate: ~30% (developers push same commits multiple times)
```

**GitHub Token** (Secrets Manager):
```
ARN: arn:aws:secretsmanager:*:*:secret:eco-coder/github-token
Cache: Retrieved once per container lifecycle (not per invocation)
Rotation: Every 90 days
```

## 8. Cost Optimization

### 8.1 Cost Breakdown (Estimated per 1000 PRs)

| Service | Usage | Unit Cost | Estimated Cost |
|---------|-------|-----------|----------------|
| **AgentCore Runtime** | 1000 invocations × 5 min avg | $0.01/min | $50.00 |
| **Claude 3 Sonnet (Bedrock)** | ~500K input + ~50K output per PR | $3/MTok in, $15/MTok out | $35.00 |
| **CodeGuru Reviewer** | 1000 reviews | $0.50/review | $500.00 |
| **CodeGuru Profiler** | 1000 profiles × 5 min | $0.005/min | $25.00 |
| **CloudWatch Logs** | 50 GB ingestion + 90-day storage | $0.50/GB + storage | $30.00 |
| **Secrets Manager** | 1 secret | $0.40/month | $0.40 |
| **Parameter Store** | Advanced parameters | $0.05/10K calls | $0.50 |
| **ECR Storage** | Container image (~500 MB) | $0.10/GB/month | $0.05 |
| **X-Ray Tracing** | 1000 traces | $5/1M traces | $0.01 |
| **Data Transfer** | GitHub API + AWS services | Minimal | $2.00 |
| **Total** | | | **~$642.96** |
| **Cost per PR** | | | **~$0.64** |

**Cost Drivers**:
1. **CodeGuru Reviewer** (78% of total cost) - Most expensive component
2. **AgentCore Runtime** (8%) - Serverless execution time
3. **Claude 3 Sonnet** (5%) - LLM token usage
4. **CloudWatch Logs** (5%) - Log storage
5. **CodeGuru Profiler** (4%) - Performance profiling

### 8.2 Cost Optimization Strategies

**1. Selective CodeGuru Analysis** (save ~60%):
```python
# Only use CodeGuru Reviewer for PRs with > 100 lines changed
if lines_changed > 100:
    results = analyze_code(...)
else:
    # Use lightweight static analysis
    results = lightweight_analysis(...)
```
Estimated savings: $380/1000 PRs

**2. Commit SHA Caching** (save ~20%):
- Cache CodeGuru results by commit SHA
- Avoid re-analyzing same code
- Implement in Parameter Store with 7-day TTL
Estimated savings: $130/1000 PRs

**3. Prompt Optimization** (save ~15%):
- Reduce system prompt length (currently ~2K tokens)
- Use structured output to reduce response tokens
- Minimize few-shot examples
Estimated savings: $5/1000 PRs

**4. Log Filtering** (save ~50% on logs):
- Only log ERROR and WARN in production
- Use INFO for debugging in dev/staging
- Reduce CloudWatch ingestion
Estimated savings: $15/1000 PRs

**5. Parallel Tool Execution** (save ~20% runtime):
- Run CodeGuru tools concurrently with asyncio
- Reduce AgentCore Runtime time from 5 min to 4 min
Estimated savings: $10/1000 PRs

**6. Repository Allowlist** (reduce unnecessary invocations):
- Only analyze PRs in configured repositories
- Reject webhooks from non-target repos early
- Saves invocation costs

**7. Business Hours Only** (optional, for non-critical use):
- Only process PRs during business hours
- Queue after-hours PRs for next day
- Reduce weekend costs

### 8.3 Optimized Cost Projection

With optimizations applied:

| Strategy | Savings | New Cost per 1000 PRs |
|----------|---------|------------------------|
| Baseline | - | $642.96 |
| Selective CodeGuru | -$380 | $262.96 |
| Commit caching | -$130 | $132.96 |
| Log filtering | -$15 | $117.96 |
| Parallel execution | -$10 | $107.96 |
| **Optimized Total** | **-$535** | **~$108/1000 PRs** |
| **Cost per PR** | | **~$0.11** |

**Cost Monitoring**:
- Set CloudWatch Budget: $200/month
- Alert at 80% of budget ($160)
- Daily cost tracking dashboard
- Tag resources with `Project:EcoCoder` for cost allocation

## 9. Disaster Recovery and Business Continuity

### 9.1 Backup Strategy

**Infrastructure as Code**:
- All configuration in Git repository
- Version controlled with tags for releases
- Automated deployments via CI/CD
- Recovery: Redeploy from Git

**Container Images**:
- Stored in Amazon ECR with image scanning
- Immutable tags for production deployments
- Lifecycle policy: Keep last 10 images
- Recovery: Redeploy specific image version

**Configuration Data**:
- System prompts and agent code in Git
- Secrets in AWS Secrets Manager (replicated across AZs)
- Carbon intensity data in Parameter Store (can be refetched)
- No critical user data stored (stateless analysis)

**Session State**:
- AgentCore Memory handles persistence
- Managed by AWS, automatically backed up
- Sessions expire after completion (no long-term storage)

### 9.2 Recovery Procedures

**RTO (Recovery Time Objective)**: 30 minutes  
**RPO (Recovery Point Objective)**: 0 (stateless system)

**Failure Scenarios**:

1. **Container Image Corruption**:
   - Impact: New invocations fail to start
   - Detection: CloudWatch alarm on high error rate
   - Recovery: Redeploy previous image tag from ECR
   - RTO: 10 minutes
   ```bash
   agentcore launch --agent-name eco-coder-agent --image-tag v1.2.3
   ```

2. **AgentCore Runtime Service Degradation**:
   - Impact: Increased latency or throttling
   - Detection: CloudWatch metrics show elevated duration/errors
   - Recovery: AWS manages service recovery, monitor status page
   - RTO: Dependent on AWS (typically < 1 hour)
   - Mitigation: Queue webhooks for retry

3. **GitHub Token Expiration**:
   - Impact: Cannot post comments to GitHub
   - Detection: post_github_comment tool returns 401 errors
   - Recovery: Rotate secret in Secrets Manager, redeploy agent
   - RTO: 15 minutes

4. **CodeGuru Service Outage**:
   - Impact: Code analysis unavailable
   - Detection: analyze_code tool times out repeatedly
   - Recovery: Agent gracefully handles timeout, posts partial report
   - RTO: N/A (degraded operation, not total failure)

5. **Regional Outage** (us-east-1):
   - Impact: Complete service unavailable
   - Detection: All invocations failing
   - Recovery: Deploy to secondary region (us-west-2)
   - RTO: 1 hour (requires multi-region setup)
   - Mitigation: Pre-deploy standby agent in secondary region

### 9.3 High Availability Considerations

**Current Architecture** (Single Region):
- AgentCore Runtime: Multi-AZ by AWS
- Secrets Manager: Replicated across AZs automatically
- ECR: Replicated across AZs automatically
- CloudWatch: Multi-AZ by AWS

**Future Multi-Region Setup**:
1. Deploy agent to us-east-1 (primary) and us-west-2 (secondary)
2. Use Route 53 health checks to monitor primary
3. Update GitHub webhook URL on failure
4. Replicate secrets and parameters to secondary region
5. Synchronize container images via ECR replication

## 10. Compliance and Governance

### 10.1 Data Governance

**Data Classification**:
- **Confidential**: Source code content (only processed in-memory, never persisted)
- **Internal**: PR metadata, analysis results (retained 90 days)
- **Public**: Carbon footprint estimates, GitHub comments (public repos)
- **Restricted**: GitHub PAT (stored encrypted in Secrets Manager)

**Data Retention Policy**:
- CloudWatch Logs: 90 days (production), 7 days (dev)
- Agent traces: 30 days
- Session state (AgentCore Memory): Deleted after session completion
- Container logs: 90 days
- Parameter Store cache: 7 days TTL

**Data Location**:
- All data stored in US region (us-east-1)
- No cross-border data transfer
- GitHub API calls to github.com (US-based)

**Personal Data Handling**:
- GitHub usernames in PR metadata (logged, retained 90 days)
- No PII collected or processed
- GDPR not applicable (no EU data subjects)

### 10.2 Audit Trail

**CloudTrail Logging** (enabled):
- All IAM actions by agent execution role
- Secrets Manager access (GetSecretValue)
- Parameter Store access (GetParameter)
- ECR image pulls
- Retention: 90 days in CloudTrail, indefinite in S3

**Application Logging** (CloudWatch):
- Every webhook invocation (session ID, repo, PR number)
- Every tool invocation (tool name, parameters, results)
- Every error with stack trace
- Every GitHub comment posted

**Audit Events**:
```json
{
  "event_type": "tool_invocation",
  "timestamp": "2025-10-19T10:30:45Z",
  "session_id": "abc123",
  "tool_name": "analyze_code",
  "parameters": {
    "repository_arn": "...",
    "commit_sha": "a1b2c3d"
  },
  "result": "success",
  "duration_ms": 45000
}
```

### 10.3 Security Compliance

**CIS AWS Foundations Benchmark**:
- ✅ IAM roles follow least privilege
- ✅ CloudTrail enabled for all API calls
- ✅ CloudWatch Logs encrypted with KMS
- ✅ Secrets Manager for credential storage
- ✅ No root account usage
- ✅ MFA required for AWS console access

**Container Security**:
- Base image scanning with ECR (enabled)
- No high/critical vulnerabilities in production
- Trivy scan in CI/CD pipeline
- Snyk monitoring for dependency vulnerabilities

**Secret Rotation**:
- GitHub PAT: Every 90 days (automated via Lambda)
- AWS credentials: Managed by STS (temporary)
- No hardcoded secrets in code or containers

### 10.4 Governance Policies

**Change Management**:
- All infrastructure changes via Git pull requests
- Peer review required for production changes
- Automated testing in dev/staging before production
- Rollback plan documented for each deployment

**Access Control**:
- AWS account access via SSO
- MFA required for all human users
- Service accounts use IAM roles (no long-term credentials)
- Principle of least privilege enforced

**Incident Response**:
- On-call rotation for critical alerts
- Incident response playbook documented
- Post-mortem required for all incidents
- Blameless culture for learning

## 11. Development and Deployment

### 11.1 Environment Strategy

**Environments**:

| Environment | Purpose | AWS Account | Agent Name | GitHub Webhook |
|-------------|---------|-------------|------------|----------------|
| **Development** | Active development, testing | dev-account | eco-coder-agent-dev | Test repo only |
| **Staging** | Pre-production validation | staging-account | eco-coder-agent-staging | Internal repos |
| **Production** | Live system | prod-account | eco-coder-agent | All target repos |

**Environment Isolation**:
- Separate AWS accounts (strongly recommended)
- Distinct AgentCore Runtime deployments
- Separate ECR repositories per environment
- Different Secrets Manager secrets
- Isolated CloudWatch log groups

**Environment Configuration**:
```yaml
# .bedrock_agentcore.yaml (per environment)
agent_name: eco-coder-agent-{env}
model_id: anthropic.claude-3-sonnet-20240229-v1:0
image_uri: {account}.dkr.ecr.{region}.amazonaws.com/eco-coder:{env}-{version}
execution_role_arn: arn:aws:iam::{account}:role/EcoCoderAgentRole-{env}
memory: 2048
timeout: 600
environment_variables:
  LOG_LEVEL: INFO
  ENV_NAME: production
```

### 11.2 CI/CD Pipeline

**Pipeline Implementation**: GitHub Actions

**Workflow File**: `.github/workflows/deploy.yml`

**Stages**:

1. **Build & Test** (on every commit):
   ```yaml
   - name: Build container
     run: docker build -t eco-coder:${{ github.sha }} .
   
   - name: Run unit tests
     run: pytest tests/unit --cov=.
   
   - name: Run integration tests
     run: pytest tests/integration
   ```

2. **Security Scan** (on every commit):
   ```yaml
   - name: Trivy container scan
     run: trivy image --severity HIGH,CRITICAL eco-coder:${{ github.sha }}
   
   - name: Snyk dependency scan
     run: snyk test --severity-threshold=high
   ```

3. **Deploy to Dev** (on push to `develop` branch):
   ```yaml
   - name: Push to ECR
     run: |
       aws ecr get-login-password --region us-east-1 | \
         docker login --username AWS --password-stdin ${ECR_DEV}
       docker tag eco-coder:${{ github.sha }} ${ECR_DEV}/eco-coder:dev-latest
       docker push ${ECR_DEV}/eco-coder:dev-latest
   
   - name: Deploy to AgentCore Runtime
     run: |
       agentcore launch \
         --agent-name eco-coder-agent-dev \
         --image-tag dev-latest \
         --profile dev
   ```

4. **Deploy to Staging** (on push to `main` branch):
   ```yaml
   - name: Deploy to staging
     run: |
       docker tag eco-coder:${{ github.sha }} ${ECR_STAGING}/eco-coder:staging-${{ github.sha }}
       docker push ${ECR_STAGING}/eco-coder:staging-${{ github.sha }}
       agentcore launch \
         --agent-name eco-coder-agent-staging \
         --image-tag staging-${{ github.sha }} \
         --profile staging
   ```

5. **Manual Approval** (required for production):
   - GitHub Actions environment protection rule
   - Requires approval from designated reviewers
   - Includes deployment checklist

6. **Deploy to Production** (on approval):
   ```yaml
   - name: Deploy to production
     run: |
       docker tag eco-coder:${{ github.sha }} ${ECR_PROD}/eco-coder:v${{ github.ref_name }}
       docker push ${ECR_PROD}/eco-coder:v${{ github.ref_name }}
       agentcore launch \
         --agent-name eco-coder-agent \
         --image-tag v${{ github.ref_name }} \
         --profile prod
   ```

7. **Smoke Tests** (post-deployment):
   ```yaml
   - name: Run smoke tests
     run: |
       python tests/smoke/test_agent_health.py --env production
       python tests/smoke/test_webhook_endpoint.py --env production
   ```

8. **Rollback** (on failure):
   ```yaml
   - name: Rollback on failure
     if: failure()
     run: |
       agentcore launch \
         --agent-name eco-coder-agent \
         --image-tag ${{ env.PREVIOUS_VERSION }} \
         --profile prod
   ```

**Deployment Tools**:
- **Container Build**: Docker
- **Container Registry**: Amazon ECR
- **Deployment**: AgentCore Starter Toolkit (`agentcore` CLI)
- **Testing**: pytest
- **Security**: Trivy, Snyk
- **CI/CD**: GitHub Actions

---

## Appendices

### Appendix A: AWS Service Quotas

| Service | Quota | Current Usage | Action Required |
|---------|-------|---------------|-----------------|
| AgentCore Runtime invocations | No published limit | ~10/hour | Monitor via metrics |
| Bedrock model invocations (Claude) | 10,000/min | ~100/hour | Request increase if > 5K |
| CodeGuru Reviewer | 1000 reviews/day | ~100/day | Request increase if needed |
| CodeGuru Profiler API calls | No hard limit | ~100/day | None |
| ECR storage | 500 GB | ~0.5 GB | None |
| CloudWatch Logs ingestion | 5 GB/s | ~1 MB/s | None |
| Secrets Manager secrets | 500,000 | 1 | None |

### Appendix B: External Dependencies

| Dependency | Version | Purpose | Fallback | Impact if Unavailable |
|------------|---------|---------|----------|----------------------|
| GitHub API | v3 REST | PR commenting | Queue for retry | Comments not posted |
| Strands SDK | 1.2.0 | Agent framework | None | Cannot deploy |
| CodeCarbon | 2.3.4 | CO2 calculation | Manual formula | Less accurate estimates |
| boto3 | 1.34+ | AWS SDK | None | Cannot call AWS services |
| AWS Customer Carbon API | Latest | Carbon intensity | Regional averages | Less accurate by region |

### Appendix C: Container Dependencies

**Base Image**: `python:3.11-slim`

**Python Packages** (`requirements.txt`):
```txt
strands==1.2.0
bedrock-agentcore==1.0.0
boto3>=1.34.0
codecarbon==2.3.4
requests==2.31.0
python-dateutil==2.8.2
pyyaml==6.0.1
```

**System Packages**:
- `git` (for cloning repositories if needed)
- `curl` (for health checks)

---

**Document Version**: 2.0  
**Last Updated**: 2025-10-19  
**Status**: Corrected Architecture (No API Gateway, No Lambda Tools, Strands-based Agent in AgentCore Runtime)
