# Eco-Coder Implementation Strategy

## Executive Summary

This document provides a comprehensive implementation strategy for the Eco-Coder AI Agent, designed to analyze code in pull requests for performance, quality, and environmental impact. The implementation leverages **AWS Bedrock AgentCore Runtime** for serverless agent hosting with **Strands Agents SDK** for building framework-agnostic AI agents.

### Key Architecture Decision

**IMPORTANT**: This project uses **AgentCore Runtime with Strands SDK**, NOT traditional Bedrock Agents. This means:
- Agent is deployed as a **containerized application**
- Tools are **internal Python functions**, not separate Lambda functions
- No API Gateway or Lambda wrappers needed
- Direct webhook invocation to AgentCore Runtime endpoint
- Simpler architecture with fewer components

## Technology Stack Overview

### Core Technologies
- **AWS Bedrock AgentCore Runtime**: Serverless container runtime for AI agents
  - Purpose-built for hosting Strands-based agents
  - Isolated microVM execution (Firecracker)
  - Up to 8-hour execution time, 100MB payloads
  - Native invocation endpoint (no API Gateway needed)
  
- **Strands Agents SDK v1.2.0**: Framework-agnostic agent development
  - `@agent.tool` decorators for tool registration
  - Built-in session management
  - Integration with AgentCore Memory
  - Works with any LLM (Bedrock, Anthropic, OpenAI)
  
- **Claude 3 Sonnet (Bedrock)**: Foundation model for agent intelligence
  - Model ID: `anthropic.claude-3-sonnet-20240229-v1:0`
  - Pricing: $3/MTok input, $15/MTok output
  - Balance of performance and cost

### Integration Services
- **Amazon CodeGuru Reviewer**: Static code analysis via boto3
- **Amazon CodeGuru Profiler**: Runtime performance profiling via boto3
- **CodeCarbon v2.3.4**: Carbon footprint estimation (Python library)
- **GitHub API v3**: Repository interaction via requests library

### Infrastructure & Deployment
- **Docker**: Container packaging
- **Amazon ECR**: Container image registry
- **AgentCore Starter Toolkit**: Deployment CLI (`agentcore` command)
- **AWS Systems Manager Parameter Store**: Configuration management
- **Amazon CloudWatch**: Logging and monitoring
- **AWS X-Ray**: Distributed tracing
- **GitHub Actions**: CI/CD pipeline

## Implementation Phases

### Phase 1: Foundation Setup (Week 1)
**Objective**: Establish container development environment and AWS infrastructure

#### 1.1 Project Initialization
- Set up Git repository structure
  ```
  /app/              # Agent container code
  /tests/            # Unit and integration tests
  /.github/          # CI/CD workflows
  /docs/             # Documentation
  ```
- Install Strands SDK (`pip install strands`)
- Install AgentCore Starter Toolkit (`pip install bedrock-agentcore-cli`)
- Set up local development environment with Docker

#### 1.2 AWS Account Configuration
- Create agent execution IAM role with permissions:
  * CodeGuru Reviewer and Profiler access
  * Secrets Manager read access (GitHub token)
  * Parameter Store read access (carbon data)
  * Bedrock model invocation
- Set up Amazon ECR repository for container images
- Configure AgentCore Runtime in target region
- Store GitHub PAT in AWS Secrets Manager

#### 1.3 Development Tooling
- Configure local Docker build environment
- Set up pytest for unit testing
- Initialize GitHub Actions CI/CD pipeline
- Create CloudWatch log groups

**Deliverables**:
- Working container build pipeline
- IAM roles and policies configured
- ECR repository created
- Development environment ready

### Phase 2: Agent Core Development (Week 2)
**Objective**: Build the Strands-based agent with tool integrations

#### 2.1 Agent Structure Setup
- Create `agent.py` with Strands SDK imports
- Initialize `BedrockAgentCoreApp` for entrypoint
- Configure Claude 3 Sonnet model parameters
- Set up AgentCore Memory session manager
- Write comprehensive system prompt

#### 2.2 Tool Module Development
- Create `tools/` directory with modules:
  * `codeguru_reviewer.py` - Code analysis
  * `codeguru_profiler.py` - Performance profiling
  * `codecarbon_estimator.py` - Carbon calculation
  * `github_poster.py` - PR commenting
- Implement each tool as standalone Python function
- Add type hints and docstrings for each tool

#### 2.3 Tool Registration
- Register tools using `@agent.tool` decorator in `agent.py`
- Ensure tool descriptions are clear for LLM
- Test tool parameter extraction
- Implement error handling for each tool

#### 2.4 Local Testing
- Create test harness using `agentcore invoke-local`
- Mock GitHub webhook payloads
- Test tool invocations individually
- Test end-to-end agent reasoning

**Deliverables**:
- Complete `agent.py` with all tools registered
- Four tool modules with implementations
- System prompt finalized
- Local testing passing

### Phase 3: Container & Deployment (Week 3)
**Objective**: Containerize agent and deploy to AgentCore Runtime

#### 3.1 Container Configuration
- Create optimized Dockerfile:
  * Multi-stage build for smaller image
  * Install Python dependencies
  * Copy agent code and tools
  * Set up entrypoint
- Create `.bedrock_agentcore.yaml` config file
- Build and test container locally
- Push initial image to ECR

#### 3.2 AgentCore Runtime Deployment
- Configure agent with AgentCore CLI:
  ```bash
  agentcore configure --agent-name eco-coder-agent \
    --image-uri <ecr-repo>/eco-coder:latest \
    --execution-role-arn <role-arn>
  ```
- Launch agent to AgentCore Runtime:
  ```bash
  agentcore launch --agent-name eco-coder-agent
  ```
- Retrieve agent invocation endpoint
- Test direct invocation with sample payload

#### 3.3 GitHub Webhook Configuration
- Configure webhook in target GitHub repository
- Set webhook URL to AgentCore Runtime endpoint
- Configure webhook secret for signature validation
- Test webhook delivery with PR event

#### 3.4 Integration Testing
- Create test PRs in GitHub
- Verify webhook triggers agent
- Validate report generation
- Test error scenarios (timeout, API failures)

**Deliverables**:
- Docker container built and pushed to ECR
- Agent deployed to AgentCore Runtime
- GitHub webhook configured
- Integration tests passing

### Phase 4: CI/CD & Automation (Week 4)
**Objective**: Implement automated build and deployment pipeline

#### 4.1 GitHub Actions Pipeline
- Create `.github/workflows/deploy.yml`:
  * Build container on commit
  * Run unit tests
  * Security scan (Trivy, Snyk)
  * Push to ECR
  * Deploy to dev/staging/prod
- Implement multi-environment strategy
- Add manual approval for production

#### 4.2 Testing Automation
- Implement unit tests for all tools
- Add integration tests for agent
- Create smoke tests for deployment validation
- Add performance benchmarking

#### 4.3 Monitoring Setup
- Configure CloudWatch Logs for agent
- Set up custom metrics for tools
- Create CloudWatch dashboards
- Configure alarms for critical errors

#### 4.4 Error Handling & Resilience
- Implement retry logic in tools
- Add timeout handling
- Create graceful degradation (partial results)
- Add comprehensive error logging

**Deliverables**:
- Automated CI/CD pipeline operational
- Comprehensive test suite
- Monitoring dashboards created
- Error handling validated

### Phase 5: Enhancement & Documentation (Week 5)
**Objective**: Polish, optimize, and document for production

#### 5.1 Performance Optimization
- Optimize container image size (target < 500MB)
- Implement result caching (Parameter Store)
- Tune prompt for token efficiency
- Add parallel tool execution (asyncio)

#### 5.2 Security Hardening
- Implement GitHub webhook signature validation
- Rotate GitHub PAT (90-day cycle)
- Enable ECR image scanning
- Audit IAM permissions (least privilege)

#### 5.3 Cost Optimization
- Implement selective CodeGuru analysis (> 100 lines changed)
- Add commit SHA caching to avoid duplicate analysis
- Optimize log retention policies
- Monitor and reduce token usage

#### 5.4 Documentation
- Write deployment guide
- Create user guide for developers
- Document architecture decisions
- Create troubleshooting guide
- Add inline code documentation

**Deliverables**:
- Optimized performance (< 5 min per PR)
- Security audit completed
- Cost optimizations implemented
- Complete documentation

## Architecture Principles

### 1. Container-First Design
- **Agent as single deployment unit**: All tools within one container
- **Simplified architecture**: No separate Lambda functions or API Gateway
- **Faster execution**: Direct tool invocation without network overhead
- **Easier debugging**: All code runs in same context with shared logging
- **AgentCore Runtime**: Leverages managed serverless container execution

**Benefits**:
- Reduced architectural complexity (fewer AWS resources)
- Lower latency (no Lambda-to-Lambda calls)
- Better error propagation (direct exceptions vs HTTP errors)
- Shared state within container (cached clients, data)

### 2. Framework-Agnostic with Strands SDK
- **Use Strands SDK**: Framework-agnostic agent development
- **Not tied to Bedrock Agents**: Can switch LLMs if needed
- **Standard Python**: Tools are regular Python functions
- **Decorator-based**: `@agent.tool` for clean tool registration
- **Session management**: Built-in with AgentCore Memory

**Benefits**:
- Portability across platforms
- Easier testing (no AWS-specific mocking needed)
- Developer-friendly Python code
- Standard software engineering practices apply

### 3. Direct Integration Pattern
- **No middleware layers**: GitHub webhook → AgentCore Runtime directly
- **Internal tools**: Boto3 calls from within agent container
- **Native endpoint**: AgentCore provides invocation URL
- **Stateless analysis**: Each PR analyzed independently

**Benefits**:
- Simpler data flow (fewer hops)
- Reduced error surface area
- Lower cost (no API Gateway, fewer Lambda invocations)
- Easier to reason about system behavior

### 4. Security by Design
- **Single IAM role**: Agent execution role with all permissions
- **Signature validation**: GitHub webhook HMAC verification
- **Secrets in Secrets Manager**: GitHub PAT encrypted
- **Encryption at rest**: CloudWatch logs, ECR images
- **Least privilege**: Role scoped to specific resources
- **No VPC required**: AgentCore Runtime handles networking

**Benefits**:
- Simplified security model
- Easier to audit (one role vs many)
- AWS-managed encryption
- Reduced attack surface

### 5. Observable & Debuggable
- **Structured logging**: JSON logs to CloudWatch
- **X-Ray tracing**: End-to-end request tracking
- **Custom metrics**: Tool performance and success rates
- **Agent traces**: LLM reasoning and tool calls visible
- **Dashboards**: Real-time operational visibility

**Benefits**:
- Quick troubleshooting
- Performance insights
- Cost tracking
- User behavior understanding

### 6. Cost-Optimized
- **AgentCore consumption pricing**: Pay only for execution time
- **No Lambda invocations**: Tools run in-process
- **Caching strategy**: Avoid duplicate CodeGuru analyses
- **Token efficiency**: Optimized prompts to reduce LLM costs
- **Selective analysis**: Only run CodeGuru for large PRs

**Cost Comparison**:
| Architecture | Cost per 1000 PRs | Components |
|--------------|-------------------|------------|
| Lambda-based (old) | ~$650 | API Gateway + 5 Lambdas + Bedrock Agent |
| Container-based (new) | ~$110 | AgentCore Runtime + Bedrock model |
| **Savings** | **~$540 (83%)** | Simpler architecture |

## Strands SDK Integration Strategy

### Agent Development with Strands SDK

The Strands SDK provides a framework-agnostic approach to building AI agents. Our integration strategy leverages Strands for maximum flexibility and AgentCore Runtime for managed hosting.

#### 1. Project Structure
```
/app/
├── agent.py                          # Main agent with Strands integration
│   ├── BedrockAgentCoreApp setup
│   ├── Strands Agent initialization
│   ├── Tool registration with @agent.tool
│   └── Entrypoint decorator
├── system_prompt.txt                 # Agent instructions
├── tools/                            # Internal tool modules
│   ├── __init__.py
│   ├── codeguru_reviewer.py          # analyze_code_quality()
│   ├── codeguru_profiler.py          # profile_code_performance()
│   ├── codecarbon_estimator.py       # calculate_carbon_footprint()
│   └── github_poster.py              # post_github_comment()
├── utils/                            # Shared utilities
│   ├── aws_helpers.py                # Boto3 client helpers
│   ├── github_helpers.py             # GitHub API wrappers
│   └── validators.py                 # Input validation
├── requirements.txt                  # Python dependencies
├── Dockerfile                        # Container definition
└── .bedrock_agentcore.yaml          # AgentCore configuration
```

#### 2. Tool Registration Pattern

**In agent.py**:
```python
from strands import Agent
from bedrock_agentcore import BedrockAgentCoreApp
from tools.codeguru_reviewer import analyze_code_quality

app = BedrockAgentCoreApp()
agent = Agent(
    system_prompt=load_system_prompt(),
    session_manager=AgentCoreMemorySessionManager()
)

@agent.tool
def analyze_code(repository_arn: str, branch_name: str, commit_sha: str) -> dict:
    """
    Analyze code quality using Amazon CodeGuru Reviewer.
    
    This tool creates a code review, waits for completion, and returns
    recommendations organized by severity level.
    """
    return analyze_code_quality(repository_arn, branch_name, commit_sha)

@app.entrypoint
def invoke(payload: dict) -> dict:
    """AgentCore Runtime invocation entrypoint"""
    # Parse GitHub webhook
    pr_info = parse_github_webhook(payload)
    
    # Create agent session
    session_id = f"{pr_info['repo']}-{pr_info['pr_number']}"
    
    # Invoke agent with analysis request
    result = agent(
        f"Analyze pull request #{pr_info['pr_number']} in {pr_info['repo']}",
        session_id=session_id
    )
    
    return {"status": "success", "message": result.message}
```

#### 3. Tool Implementation Pattern

**Each tool module** (e.g., `tools/codeguru_reviewer.py`):
```python
import boto3
from typing import Dict

def analyze_code_quality(
    repository_arn: str,
    branch_name: str, 
    commit_sha: str
) -> Dict:
    """
    Internal tool function - NOT a Lambda.
    Called directly by agent within same container.
    """
    client = boto3.client('codeguru-reviewer')
    
    # Create review
    response = client.create_code_review(...)
    
    # Poll for completion (with timeout)
    status = poll_review_status(response['CodeReview']['CodeReviewArn'])
    
    # Fetch and format recommendations
    recommendations = fetch_recommendations(...)
    
    return {
        "status": "completed",
        "recommendations": recommendations,
        "total": len(recommendations)
    }
```

#### 4. Memory and Session Management

**AgentCore Memory Integration**:
```python
from strands.session_managers import AgentCoreMemorySessionManager

# Initialize with AgentCore Memory
session_manager = AgentCoreMemorySessionManager(
    memory_id="eco-coder-memory",
    region="us-east-1"
)

agent = Agent(
    system_prompt=SYSTEM_PROMPT,
    session_manager=session_manager  # Persistent across invocations
)
```

**Benefits**:
- Session state persisted automatically
- Multi-turn conversations supported
- Context maintained across PR updates
- Managed by AWS (no DynamoDB setup needed)

#### 5. Error Handling Strategy

**Tool-level errors**:
```python
def analyze_code_quality(...) -> Dict:
    try:
        # Tool logic
        return {"status": "completed", "results": ...}
    except ClientError as e:
        # AWS service error - return error dict
        return {
            "status": "error",
            "error_type": "aws_service_error",
            "message": str(e)
        }
```

**Agent-level handling**:
- LLM reasons about error responses
- Can retry with different parameters
- Can proceed with partial results
- Generates report noting missing data

#### 6. Strands SDK Best Practices

1. **Clear tool descriptions**: LLM uses these to decide when to call tools
2. **Type hints**: Strands uses these for parameter validation
3. **Structured returns**: Use dictionaries with consistent keys
4. **Error dictionaries**: Return errors as data, not exceptions
5. **Idempotent tools**: Same inputs should yield same outputs (when possible)

## Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| **Container startup time** | High | Optimize Dockerfile with multi-stage builds, pre-warm containers | Monitored |
| **CodeGuru API rate limits** | High | Implement caching by commit SHA, selective analysis (> 100 lines) | Implemented |
| **Agent reasoning errors** | High | Comprehensive prompt engineering, extensive testing, fallback logic | In Progress |
| **GitHub API rate limits** | Medium | Exponential backoff with retries, respect rate limit headers | Implemented |
| **AgentCore Runtime throttling** | Medium | Monitor CloudWatch metrics, request quota increase proactively | Monitored |
| **Carbon intensity data unavailable** | Low | Fallback to regional averages in Parameter Store | Implemented |
| **ECR image pull failures** | Low | Image verification in CI/CD, rollback to previous version | Automated |

### Operational Risks

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| **Cost overruns** | High | CloudWatch Budget alarms, CodeGuru selective analysis, token optimization | Implemented |
| **AgentCore Runtime outages** | High | Multi-region deployment (future), graceful error messages to users | Planned |
| **Container image vulnerabilities** | High | Trivy/Snyk scanning in CI/CD, base image updates, dependency audits | Automated |
| **GitHub webhook delivery failures** | Medium | Webhook retry mechanism, CloudWatch alarms on failures | Monitored |
| **Poor agent performance** | Medium | Continuous prompt refinement, A/B testing, user feedback loop | In Progress |
| **Memory leaks in container** | Low | Container restart on timeout, memory profiling in staging | Monitored |

### Architecture-Specific Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Strands SDK compatibility** | Medium | Pin exact version (1.2.0), test upgrades in staging before production |
| **AgentCore Runtime API changes** | Medium | Monitor AWS announcements, version pinning, gradual migration |
| **Single point of failure (container)** | Medium | Comprehensive error handling, partial result generation, retry logic |
| **Tool execution timeouts** | Medium | Per-tool timeouts (5 min max), graceful degradation, partial reports |

## Success Criteria

### Technical Success Metrics

| Metric | Target | Measurement | Priority |
|--------|--------|-------------|----------|
| **End-to-end analysis time** | < 5 minutes (p95) | CloudWatch custom metric | High |
| **Container cold start** | < 10 seconds | AgentCore Runtime metrics | High |
| **Container warm start** | < 1 second | AgentCore Runtime metrics | Medium |
| **Agent success rate** | > 95% | Successful report generation / total PRs | High |
| **Tool error rate** | < 5% per tool | Failed tool calls / total calls | High |
| **Report quality** | 90% actionable | Manual review + user feedback | High |
| **GitHub comment posting** | > 98% success | Successful posts / attempts | Medium |
| **Token efficiency** | < 600K tokens/PR | CloudWatch metrics | Medium |
| **Cost per PR** | < $0.15 | Cost tracking dashboard | High |

### Architecture Success Metrics

| Metric | Target | Validates |
|--------|--------|-----------|
| **Zero Lambda functions** | 0 | Correct architecture |
| **Zero API Gateway** | 0 | Correct architecture |
| **Single container deployment** | 1 | Simplified architecture |
| **Single IAM role** | 1 | Simplified security |
| **Direct tool calls** | 100% | No external invocations |
| **Image size** | < 500 MB | Optimized container |

### Business Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **CO2e calculation accuracy** | ±10% vs manual | Compare with manual calculations |
| **Developer adoption** | > 80% of teams | Internal survey |
| **Positive feedback** | > 4.0/5.0 stars | User ratings |
| **Actionable recommendations** | 90% implementation rate | PR updates after analysis |
| **Green coding awareness** | +50% knowledge increase | Pre/post surveys |

### Hackathon Success Metrics

| Requirement | Status | Evidence |
|-------------|--------|----------|
| ✅ Uses Bedrock AgentCore Runtime | Complete | Deployed to AgentCore |
| ✅ Strands SDK integration | Complete | agent.py with @agent.tool |
| ✅ Working end-to-end demo | Complete | Video + live demo |
| ✅ Environmental impact focus | Complete | CO2e calculations |
| ✅ Reproducible deployment | Complete | GitHub repo + docs |
| ✅ Innovative architecture | Complete | Container-based, no Lambda |
| ✅ Production-ready | Complete | CI/CD, monitoring, security |

## Implementation Checklist

### Week 1: Foundation
- [ ] Set up Git repository and project structure
- [ ] Install Strands SDK and AgentCore CLI
- [ ] Create Dockerfile for agent container
- [ ] Configure IAM roles and permissions
- [ ] Set up ECR repository
- [ ] Store GitHub PAT in Secrets Manager
- [ ] Initialize GitHub Actions CI/CD

### Week 2: Agent Development
- [ ] Implement `agent.py` with Strands integration
- [ ] Write comprehensive system prompt
- [ ] Implement 4 tool modules in `tools/` directory
- [ ] Register tools with `@agent.tool` decorators
- [ ] Set up AgentCore Memory session manager
- [ ] Test tools individually with mocks
- [ ] Test agent reasoning locally

### Week 3: Deployment
- [ ] Build Docker container and push to ECR
- [ ] Deploy to AgentCore Runtime with `agentcore launch`
- [ ] Configure GitHub webhook with AgentCore endpoint
- [ ] Test end-to-end with real PR
- [ ] Validate report generation
- [ ] Fix any deployment issues

### Week 4: CI/CD & Monitoring
- [ ] Complete GitHub Actions pipeline
- [ ] Add automated tests (unit + integration)
- [ ] Configure CloudWatch dashboards
- [ ] Set up CloudWatch alarms
- [ ] Implement cost tracking
- [ ] Add X-Ray tracing
- [ ] Test multi-environment deployment

### Week 5: Polish & Documentation
- [ ] Optimize container image size
- [ ] Implement caching strategy
- [ ] Add security scanning (Trivy, Snyk)
- [ ] Write deployment guide
- [ ] Create architecture diagrams
- [ ] Record demo video
- [ ] Prepare hackathon submission

## Next Steps

### Immediate Actions (This Week)
1. ✅ Review and approve corrected architecture
2. ✅ Update all specification documents
3. 🔄 Begin Phase 1: Foundation setup
4. 📅 Schedule daily standups for development

### Short-term Actions (Next 2 Weeks)
1. Complete agent development (Phase 2)
2. Deploy to AgentCore Runtime (Phase 3)
3. Configure GitHub webhook integration
4. Begin integration testing

### Long-term Actions (Weeks 4-5)
1. Implement full CI/CD pipeline
2. Add comprehensive monitoring
3. Optimize performance and costs
4. Complete documentation
5. Prepare hackathon submission

## References

### AWS Documentation
- [AWS Bedrock AgentCore Runtime Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-tools-runtime.html)
- [AgentCore Runtime Getting Started](https://docs.aws.amazon.com/bedrock/latest/userguide/runtime-getting-started.html)
- [AgentCore Starter Toolkit](https://github.com/aws/bedrock-agentcore-starter-toolkit)
- [Amazon CodeGuru Reviewer API Reference](https://docs.aws.amazon.com/codeguru/latest/reviewer-api/)
- [Amazon CodeGuru Profiler API Reference](https://docs.aws.amazon.com/codeguru/latest/profiler-api/)

### Strands SDK
- [Strands Agents SDK Documentation](https://strandsagents.com/latest/)
- [Strands + AgentCore Integration Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/strands-sdk-memory.html)
- [Strands GitHub Repository](https://github.com/strands/strands-sdk)

### Best Practices
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Container Security Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/security.html)
- [Green Software Foundation - SCI Specification](https://sci.greensoftware.foundation/)
- [Sustainable Software Engineering Principles](https://principles.green/)

### Tools & Libraries
- [CodeCarbon Documentation](https://codecarbon.io/)
- [GitHub REST API v3](https://docs.github.com/en/rest)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

**Document Version**: 2.0  
**Last Updated**: 2025-10-19  
**Status**: Corrected Strategy (Container-based AgentCore Runtime with Strands SDK)
