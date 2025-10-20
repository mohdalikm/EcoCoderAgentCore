# AWS CodeGuru Services Setup Guide

This document provides comprehensive instructions for setting up AWS CodeGuru services with EcoCoder, including important information about service deprecation.

## 🚨 Important Notice: CodeGuru Reviewer Deprecation

**Amazon CodeGuru Reviewer will be discontinued on November 7, 2025.** After this date:
- No new repository associations can be created
- Existing associations will continue to work until the service is fully retired
- AWS recommends migrating to alternative code quality tools

## Quick Setup

### Automated Setup (Recommended)

Run the automated setup script:

```bash
./scripts/setup-codeguru-services.sh
```

This script will:
- ✅ Create CodeGuru Profiler default profiling group
- ✅ Validate IAM permissions
- ✅ Test service functionality
- ⚠️ Provide CodeGuru Reviewer migration guidance

### Manual Setup Options

```bash
# Setup CodeGuru Profiler only
./scripts/setup-codeguru-services.sh profiler-only

# Test existing setup
./scripts/setup-codeguru-services.sh test

# Clean up (delete profiling groups)
./scripts/setup-codeguru-services.sh clean
```

## CodeGuru Profiler Setup

### 1. Required IAM Permissions

The EcoCoder agent requires these CodeGuru Profiler permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "codeguru-profiler:CreateProfilingGroup",
                "codeguru-profiler:DescribeProfilingGroup",
                "codeguru-profiler:GetProfile",
                "codeguru-profiler:GetRecommendations",
                "codeguru-profiler:ListProfilingGroups",
                "codeguru-profiler:PostAgentProfile",
                "codeguru-profiler:ConfigureAgent"
            ],
            "Resource": [
                "arn:aws:codeguru-profiler:*:*:profilingGroup/ecocoder-*"
            ]
        }
    ]
}
```

### 2. Profiling Group Creation

EcoCoder automatically creates profiling groups with this naming pattern:

- **Default Group**: `ecocoder-default-profiling-group`
- **PR-Specific Groups**: `ecocoder-{repo-name}-pr-{number}`

The agent includes intelligent fallback logic:
1. Try to create PR-specific profiling group
2. Fall back to default profiling group if PR-specific fails
3. Create default group if it doesn't exist

### 3. Profiling Data Collection

CodeGuru Profiler collects runtime data when:
- Applications use the CodeGuru Profiler agent
- Tests run in CodeBuild with profiling enabled
- Environment variables are properly configured:
  ```bash
  AWS_CODEGURU_PROFILER_GROUP_NAME=your-profiling-group
  AWS_CODEGURU_PROFILER_ENABLED=true
  ```

## CodeGuru Reviewer Setup & Migration

### ⚠️ Deprecation Timeline

| Date | Status | Action Required |
|------|--------|----------------|
| **October 2024** | Current | Can still create new associations |
| **November 7, 2025** | Cutoff | No new associations allowed |
| **TBD 2026** | End of Life | Service fully retired |

### Current Functionality (Until Nov 7, 2025)

If you have existing CodeGuru Reviewer associations, they will continue to work:

```bash
# List existing associations
aws codeguru-reviewer list-repository-associations

# Check association status
aws codeguru-reviewer describe-repository-association \
    --association-arn arn:aws:codeguru-reviewer:region:account:association/id
```

### Migration Alternatives

Since CodeGuru Reviewer is being deprecated, consider these alternatives:

#### 1. **SonarQube** (Recommended)
```bash
# Self-hosted or SonarCloud
# Supports: Java, Python, JavaScript, TypeScript, C#, Go, etc.
# Features: Security vulnerabilities, code smells, coverage
```

#### 2. **GitHub-Native Tools**
```yaml
# .github/workflows/code-quality.yml
name: Code Quality
on: [push, pull_request]
jobs:
  codeql:
    uses: github/codeql-action/analyze@v2
    with:
      languages: python, javascript
```

#### 3. **Language-Specific Linters**
```bash
# Python
pip install pylint bandit safety
pylint src/
bandit -r src/
safety check

# JavaScript/TypeScript  
npm install --save-dev eslint @typescript-eslint/parser
npx eslint src/

# Java
# Use SpotBugs, PMD, Checkstyle in Maven/Gradle
```

#### 4. **Multi-Language Solutions**
- **Semgrep**: Static analysis for multiple languages
- **CodeClimate**: Code quality and maintainability
- **DeepCode (Snyk)**: AI-powered code review

## EcoCoder Integration Status

### ✅ Working Components

1. **Carbon Footprint Calculator**: Fully functional
2. **GitHub Integration**: Working perfectly
3. **CodeGuru Profiler**: Enhanced with automatic setup
4. **AgentCore Deployment**: Successful builds and deployments

### ⚠️ Components Requiring Attention

1. **CodeGuru Reviewer**: 
   - Parameter validation fixed
   - Service deprecation handled gracefully
   - Returns helpful error messages with migration guidance

### 🔧 Enhanced Error Handling

The EcoCoder agent now provides intelligent error handling:

```python
# Example error response for CodeGuru Reviewer
{
    "status": "error",
    "error_type": "repository_association_required", 
    "message": "CodeGuru Reviewer setup required. Service will be deprecated Nov 7, 2025.",
    "setup_instructions": [
        "Consider using alternative code quality tools like SonarQube, ESLint, or Pylint",
        "For existing associations, use the full ARN format"
    ]
}
```

## Testing the Setup

### 1. Test CodeGuru Profiler
```bash
# Run the test script
./scripts/setup-codeguru-services.sh test

# Or test manually
aws codeguru-profiler list-profiling-groups
aws codeguru-profiler describe-profiling-group \
    --profiling-group-name ecocoder-default-profiling-group
```

### 2. Deploy and Test Agent
```bash
# Deploy updated agent
agentcore launch

# Test with sample PR payload
agentcore invoke --payload '{
    "pull_request": {"number": 1},
    "repository": {"full_name": "mohdalikm/test-repo"}
}'
```

### 3. Verify Functionality

The agent should now:
- ✅ Create profiling groups automatically
- ✅ Handle CodeGuru Reviewer gracefully with helpful messages
- ✅ Provide comprehensive Green Software Engineering analysis
- ✅ Post detailed reports to GitHub PRs

## Monitoring and Maintenance

### CodeGuru Profiler Console
- Monitor profiling groups: [AWS Console](https://console.aws.amazon.com/codeguru/profiler)
- View flame graphs and performance recommendations
- Track profiling data usage and costs

### CloudWatch Logs
- Agent execution logs: `/aws/bedrock-agentcore/runtimes/ecocoderagentcore-*`
- CodeBuild logs: `/aws/codebuild/*`
- Look for profiling setup success/failure messages

### Cost Optimization
- CodeGuru Profiler charges per hour of application profiled
- Monitor usage in AWS Cost Explorer
- Delete unused profiling groups to reduce costs

## Troubleshooting

### Common Issues

1. **"Access Denied" creating profiling groups**
   ```bash
   # Check IAM permissions
   aws iam simulate-principal-policy \
       --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
       --action-names codeguru-profiler:CreateProfilingGroup \
       --resource-arns "arn:aws:codeguru-profiler:*:*:profilingGroup/ecocoder-*"
   ```

2. **"Repository association not found" for CodeGuru Reviewer**
   - This is expected for new repositories after Nov 7, 2025
   - Use alternative code quality tools
   - For existing associations, ensure you're using the full ARN

3. **No profiling data appearing**
   - Ensure applications are instrumented with CodeGuru Profiler agent
   - Check environment variables are set correctly
   - Verify profiling group is active and configured properly

### Getting Help

1. **AWS Documentation**: [CodeGuru Profiler User Guide](https://docs.aws.amazon.com/codeguru/latest/profiler-ug/)
2. **EcoCoder Logs**: Check CloudWatch logs for detailed error messages
3. **AWS Support**: For service-specific issues
4. **Setup Script**: Run `./scripts/setup-codeguru-services.sh test` for diagnostics

## Migration Roadmap

### Immediate (Now - Nov 2025)
- ✅ Use enhanced CodeGuru Profiler integration  
- ✅ Handle CodeGuru Reviewer deprecation gracefully
- 🔄 Evaluate alternative code quality tools

### Short Term (Nov 2025 - Mar 2026)
- 🔄 Implement SonarQube or similar integration
- 🔄 Update EcoCoder agent with new code quality providers
- 🔄 Test alternative tools with existing workflows

### Long Term (2026+)
- 🔄 Full migration to alternative code quality solution
- 🔄 Remove CodeGuru Reviewer dependencies
- 🔄 Enhanced static analysis with multiple tools

---

**Last Updated**: October 20, 2025  
**Version**: 2.1  
**Status**: CodeGuru Profiler fully functional, CodeGuru Reviewer deprecated