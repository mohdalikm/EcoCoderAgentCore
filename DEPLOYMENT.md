# EcoCoder Agent - AWS Deployment Guide

This guide provides comprehensive instructions for deploying the EcoCoder Agent to AWS Bedrock AgentCore Runtime and testing the deployment.

## Overview

The EcoCoder Agent is built with the Strands SDK and deployed on AWS Bedrock AgentCore Runtime. It analyzes GitHub pull requests for sustainable software development, providing feedback on performance, quality, and environmental impact.

## Prerequisites

### 1. Development Environment
- Python 3.11+ (required for Strands SDK)
- AWS CLI configured with appropriate permissions
- Git for version control

### 2. AWS Prerequisites
- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Required IAM roles (auto-created by AgentCore)
- Bedrock AgentCore service enabled in your region

### 3. Required Permissions
Your AWS user/role needs permissions for:
- Bedrock AgentCore (agent management, runtime invocation)
- ECR (container registry)
- CodeBuild (for cloud builds)
- IAM (role creation/management)
- CloudWatch (logs and monitoring)
- SSM Parameter Store (configuration storage)

## Setup Instructions

### 1. Clone and Setup Project

```bash
# Clone the repository
git clone https://github.com/mohdalikm/EcoCoderAgentCore.git
cd EcoCoderAgentCore

# Create and activate virtual environment
python3.11 -m venv .venv-py311
source .venv-py311/bin/activate  # On macOS/Linux
# .venv-py311\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure AWS Environment

```bash
# Configure AWS CLI if not already done
aws configure

# Set your region (modify as needed)
export AWS_REGION=ap-southeast-1
```

### 3. Verify AgentCore CLI

```bash
# Check if AgentCore CLI is available
agentcore --help

# List any existing agents
agentcore configure list
```

## Deployment Process

### 1. Initial Deployment

For first-time deployment:

```bash
# Deploy agent to AWS (creates all resources)
agentcore launch

# This will:
# - Create ECR repository
# - Set up IAM roles
# - Build ARM64 container using CodeBuild
# - Deploy to Bedrock AgentCore Runtime
# - Configure observability (CloudWatch + X-Ray)
```

### 2. Update Existing Deployment

For updating an existing agent with new code:

```bash
# Deploy updates (auto-update existing agent)
agentcore launch --auto-update-on-conflict

# Alternative: Force update
agentcore launch --auto-update-on-conflict
```

### 3. Deployment Options

```bash
# Default: CodeBuild + Cloud Runtime (RECOMMENDED)
agentcore launch

# Local Development: Build and run locally
agentcore launch --local

# Hybrid: Build locally, deploy to cloud
agentcore launch --local-build
```

## Configuration Files

The deployment is configured via `.bedrock_agentcore.yaml`:

```yaml
default_agent: ecocoderagentcore
agents:
  ecocoderagentcore:
    name: ecocoderagentcore
    entrypoint: /path/to/app/agent.py
    platform: linux/arm64
    source_path: /path/to/app
    aws:
      region: ap-southeast-1
      account: 'your-account-id'
      # Other AWS configuration...
```

## Testing the Deployment

### 1. Basic Connectivity Test

```bash
# Test with simple payload
agentcore invoke '{"prompt": "Hello!"}'
```

Expected response (should show validation error):
```json
{
  "status": "error", 
  "message": "Missing required PR information in webhook payload"
}
```

### 2. GitHub Webhook Payload Test

Test with realistic GitHub PR webhook structure:

```bash
# Test with GitHub PR webhook payload
agentcore invoke '{
  "action": "opened",
  "number": 42,
  "pull_request": {
    "id": 1234567890,
    "number": 42,
    "title": "feat: Add new data processing algorithm with performance optimizations",
    "body": "This PR introduces a new algorithm that improves data processing efficiency by 40% and reduces memory usage.",
    "state": "open",
    "created_at": "2025-10-20T03:00:00Z",
    "updated_at": "2025-10-20T03:00:00Z",
    "head": {
      "label": "eco-tech:feature/optimize-performance",
      "ref": "feature/optimize-performance", 
      "sha": "a1b2c3d4e5f67890123456789abcdef012345678",
      "repo": {
        "id": 987654321,
        "name": "sample-app",
        "full_name": "eco-tech/sample-app"
      }
    },
    "base": {
      "label": "eco-tech:main",
      "ref": "main",
      "sha": "def0123456789abcdef0123456789abcdef012345",
      "repo": {
        "id": 987654321,
        "name": "sample-app", 
        "full_name": "eco-tech/sample-app"
      }
    },
    "user": {
      "id": 123456,
      "login": "developer123",
      "type": "User"
    },
    "assignees": [],
    "requested_reviewers": [],
    "labels": [
      {"name": "enhancement"},
      {"name": "performance"}
    ]
  },
  "repository": {
    "id": 987654321,
    "name": "sample-app",
    "full_name": "eco-tech/sample-app",
    "private": false,
    "clone_url": "https://github.com/eco-tech/sample-app.git",
    "ssh_url": "git@github.com:eco-tech/sample-app.git",
    "html_url": "https://github.com/eco-tech/sample-app",
    "description": "A sample application for sustainable software development",
    "language": "Python",
    "default_branch": "main",
    "owner": {
      "id": 123456,
      "login": "eco-tech",
      "type": "Organization"
    }
  },
  "sender": {
    "id": 123456,
    "login": "developer123",
    "type": "User"
  }
}'
```

### 3. Development Testing with run_dev.py

For local development testing against the deployed agent:

```bash
# Run development test client
python run_dev.py
```

This will:
- Check if agent server is running locally
- Test with simple payload first
- Test with realistic GitHub webhook payload
- Display detailed results and timing

## Monitoring and Debugging

### 1. Check Agent Status

```bash
# Get agent status and configuration
agentcore status
```

### 2. View CloudWatch Logs

```bash
# Tail runtime logs
aws logs tail /aws/bedrock-agentcore/runtimes/your-agent-id-DEFAULT \
  --log-stream-name-prefix "2025/10/19/[runtime-logs]" --follow

# View logs from last hour
aws logs tail /aws/bedrock-agentcore/runtimes/your-agent-id-DEFAULT \
  --log-stream-name-prefix "2025/10/19/[runtime-logs]" --since 1h

# View OTEL logs
aws logs tail /aws/bedrock-agentcore/runtimes/your-agent-id-DEFAULT \
  --log-stream-names "otel-rt-logs" --follow
```

### 3. GenAI Observability Dashboard

Access the CloudWatch GenAI Observability Dashboard:
```
https://console.aws.amazon.com/cloudwatch/home?region=ap-southeast-1#gen-ai-observability/agent-core
```

Features:
- Agent invocation metrics
- Error rates and latency
- Token usage tracking
- X-Ray distributed tracing

### 4. Common Debugging Commands

```bash
# Check ECR repository
aws ecr describe-repositories --repository-names bedrock-agentcore-your-agent

# View CodeBuild logs
aws codebuild batch-get-builds --ids your-build-id

# Check IAM roles
aws iam list-roles --query 'Roles[?contains(RoleName, `AgentCore`)]'
```

## Environment Configuration

### Development Environment

The agent detects development environment and uses mock implementations:

```bash
export ENVIRONMENT=development
# This enables:
# - Mock AWS services (CodeGuru, GitHub API)
# - Simplified carbon footprint calculations
# - Enhanced logging for debugging
```

### Production Environment

For production deployment:

```bash
export ENVIRONMENT=production
export AWS_REGION=ap-southeast-1
# This enables:
# - Real AWS service integration
# - Production-grade error handling
# - CloudWatch monitoring
```

## GitHub Webhook Integration

### 1. Deploy Webhook Bridge Lambda

```bash
# Deploy the GitHub webhook bridge
./deploy_webhook_bridge.sh
```

This creates:
- Lambda function for webhook processing
- Function URL for GitHub webhook endpoint
- IAM roles with AgentCore invocation permissions

### 2. Configure GitHub Repository

In your GitHub repository settings:

1. Go to Settings → Webhooks
2. Add webhook with:
   - **Payload URL**: Lambda Function URL (from deployment output)
   - **Content Type**: `application/json`
   - **Events**: Pull requests (opened, synchronize, reopened)
   - **Active**: ✅ Enabled

### 3. Test Webhook Integration

Create a test PR in your repository to verify:
- Webhook triggers Lambda function
- Lambda invokes AgentCore agent
- Agent analyzes PR and posts comment

## Cost Management

### Estimated Costs (ap-southeast-1)

- **Bedrock AgentCore Runtime**: ~$0.10 per 1K invocations
- **CodeBuild**: ~$0.005 per build minute (ARM64)
- **ECR Storage**: ~$0.10 per GB-month
- **CloudWatch Logs**: ~$0.50 per GB ingested
- **Lambda (webhook bridge)**: ~$0.20 per 1M requests

### Cost Optimization Tips

1. **Use development environment** for testing (mocked services)
2. **Monitor CloudWatch logs** retention (set appropriate retention periods)
3. **Use CodeBuild** for builds (more cost-effective than local builds + push)
4. **Configure appropriate timeouts** to avoid long-running costs

## Troubleshooting

### Common Issues

1. **Permission Errors**
   ```bash
   # Check AWS credentials
   aws sts get-caller-identity
   
   # Verify region configuration
   echo $AWS_REGION
   ```

2. **Build Failures**
   ```bash
   # Check CodeBuild logs
   agentcore status
   
   # View build history
   aws codebuild list-builds-for-project --project-name your-project
   ```

3. **Runtime Errors**
   ```bash
   # Check agent logs
   aws logs tail /aws/bedrock-agentcore/runtimes/your-agent-id-DEFAULT --follow
   
   # Test with simple payload
   agentcore invoke '{"prompt": "test"}'
   ```

4. **Webhook Issues**
   ```bash
   # Check Lambda function logs
   aws logs tail /aws/lambda/ecocoder-github-webhook-bridge --follow
   
   # Test webhook endpoint
   curl -X POST https://your-lambda-url.lambda-url.region.on.aws/ \
     -H "X-GitHub-Event: ping" -d '{}'
   ```

### Getting Help

- **AWS Documentation**: [Bedrock AgentCore Runtime Guide](https://docs.aws.amazon.com/bedrock/)
- **Strands SDK**: [Documentation](https://docs.strands.com/sdk/)
- **GitHub Issues**: Report bugs and request features
- **AWS Support**: For AWS-specific issues

## Security Best Practices

1. **IAM Permissions**: Use least-privilege principle
2. **Secrets Management**: Store sensitive data in AWS Secrets Manager
3. **Network Security**: Use VPC configuration for enhanced security
4. **Monitoring**: Enable CloudTrail for API call auditing
5. **Encryption**: Enable encryption in transit and at rest

## Maintenance

### Regular Tasks

1. **Update Dependencies**: Regularly update Python packages
2. **Monitor Costs**: Review AWS billing dashboard monthly
3. **Log Retention**: Set appropriate CloudWatch log retention
4. **Security Updates**: Keep AWS CLI and tools updated
5. **Performance Monitoring**: Review GenAI dashboard metrics

### Scaling Considerations

- **Concurrent Invocations**: Monitor and adjust limits as needed
- **Memory Configuration**: Optimize based on usage patterns
- **Regional Deployment**: Consider multi-region for global usage
- **Caching**: Implement caching for repeated analyses

---

## Quick Reference

### Essential Commands

```bash
# Deploy/Update
agentcore launch --auto-update-on-conflict

# Test
agentcore invoke '{"prompt": "Hello!"}'

# Monitor
agentcore status
aws logs tail /aws/bedrock-agentcore/runtimes/your-agent-id-DEFAULT --follow

# Local Development
python run_dev.py
```

### Key URLs
- **GenAI Dashboard**: CloudWatch → GenAI Observability → Agent Core
- **Lambda Console**: AWS Console → Lambda → Functions
- **ECR Repository**: AWS Console → ECR → Repositories
- **CodeBuild Projects**: AWS Console → CodeBuild → Projects

---

**🌱 Happy deploying with sustainable software development!**