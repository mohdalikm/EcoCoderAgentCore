# EcoCoder Entry Lambda

This directory contains the AWS Lambda function that serves as the entry point for the EcoCoder agent system.

## Files

- `lambda_webhook_bridge.py` - Main Lambda handler function
- `requirements.txt` - Python dependencies for the Lambda function
- `template.yaml` - AWS SAM CloudFormation template
- `samconfig.toml` - SAM CLI configuration for deployments
- `deploy.sh` - Automated deployment script
- `test_local.sh` - Local testing and development script
- `cleanup.sh` - Resource cleanup script
- `hooks/` - SAM deployment hook functions (pre/post traffic validation)
- `test_events/` - Sample events for local testing
- `__init__.py` - Python package initialization
- `README.md` - This documentation file

## Function Details

**Function Name**: `ecocoder-core-entry`

**Purpose**: 
- Receives GitHub webhook events via API Gateway
- Validates webhook signatures (optional)
- Forwards events to Bedrock AgentCore Runtime
- Returns appropriate HTTP responses

**Supported Endpoints**:
- `POST /webhook` - GitHub webhook processing
- `GET /health` - Health check endpoint
- `OPTIONS /*` - CORS preflight handling

## Quick Start

### Prerequisites

- AWS CLI configured (`aws configure`)
- AWS SAM CLI installed
- Docker installed and running (for local testing and container builds)

### Development
```bash
# Navigate to the Lambda directory
cd /path/to/EcoCoderAgentCore/ecocoder_entry_lambda

# Use the automated testing script
./test_local.sh

# Or manually test specific functions
sam local invoke EcoCoderCoreEntryFunction --event test_events/health_check.json
sam local invoke EcoCoderCoreEntryFunction --event test_events/webhook_pr_opened.json
```

### Deployment
```bash
# Navigate to the Lambda directory
cd /path/to/EcoCoderAgentCore/ecocoder_entry_lambda

# Deploy to development
./deploy.sh

# Deploy to other environments
./deploy.sh staging
./deploy.sh prod
```

### Local API Testing
```bash
# Start local API Gateway
sam local start-api --port 3000

# Test health endpoint
curl http://localhost:3000/health

# Test webhook endpoint
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -d @test_events/webhook_pr_opened.json
```

## Environment Variables

The Lambda function uses the following environment variables:

- `AGENT_ARN` - ARN of the Bedrock AgentCore Runtime instance
- `GITHUB_WEBHOOK_SECRET` - GitHub webhook secret for signature verification (optional)
- `ECOCODER_REGION` - AWS region for EcoCoder services
- `ENVIRONMENT` - Deployment environment (dev/staging/prod)

## Dependencies

See `requirements.txt` for the minimal set of dependencies required by the Lambda function:
- `boto3` - AWS SDK for Python
- `botocore` - Low-level AWS service access

## Deployment

This directory contains a complete SAM application for the EcoCoder entry Lambda function. All necessary files are self-contained within this directory:

- Infrastructure defined in `template.yaml`
- Deployment configuration in `samconfig.toml`
- Automated deployment via `deploy.sh`
- Local testing via `test_local.sh`

The Lambda function can be deployed independently of other EcoCoder components.

## Monitoring

The function logs to CloudWatch Logs under the log group:
`/aws/lambda/{stack-name}-ecocoder-core-entry`

Key metrics monitored:
- Invocation count
- Error rate
- Duration
- Throttles