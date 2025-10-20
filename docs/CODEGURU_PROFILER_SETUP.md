# AWS CodeGuru Profiler Setup Guide

This document provides comprehensive instructions for setting up AWS CodeGuru Profiler with EcoCoder.

## Quick Setup

### Automated Setup (Recommended)

Run the automated setup script:

```bash
./scripts/setup-codeguru-profiler.sh
```

This script will:
- ✅ Create CodeGuru Profiler default profiling group
- ✅ Validate IAM permissions
- ✅ Test service functionality

### Manual Setup Options

```bash
# Setup CodeGuru Profiler only
./scripts/setup-codeguru-profiler.sh profiler-only

# Test existing setup
./scripts/setup-codeguru-profiler.sh test

# Clean up (delete profiling groups)
./scripts/setup-codeguru-profiler.sh clean
```

## CodeGuru Profiler Setup

### 1. Required IAM Permissions

The EcoCoder agent requires these CodeGuru Profiler permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CodeGuruProfilerPermissions",
            "Effect": "Allow",
            "Action": [
                "codeguru-profiler:GetProfile",
                "codeguru-profiler:GetRecommendations",
                "codeguru-profiler:DescribeProfilingGroup",
                "codeguru-profiler:ListProfilingGroups",
                "codeguru-profiler:ListProfileTimes",
                "codeguru-profiler:PostAgentProfile",
                "codeguru-profiler:ConfigureAgent"
            ],
            "Resource": [
                "arn:aws:codeguru-profiler:*:*:profilingGroup/*"
            ]
        }
    ]
}
```

### 2. Profiling Group Creation

Create a profiling group for your project:

```bash
aws codeguru-profiler create-profiling-group \
    --profiling-group-name ecocoder-default-profiling-group \
    --compute-platform Default
```

### 3. Profiling Data Collection

Configure your application for profiling:

```bash
# Set environment variables for CodeBuild
AWS_CODEGURU_PROFILER_GROUP_NAME=your-profiling-group
AWS_CODEGURU_PROFILER_ENABLED=true
```

## EcoCoder Integration Status

### ✅ Working Components

1. **Carbon Footprint Calculator**: Fully functional
2. **GitHub Integration**: Working perfectly
3. **CodeGuru Profiler**: Enhanced with automatic setup
4. **AgentCore Deployment**: Successful builds and deployments

### 🔧 Enhanced Error Handling

EcoCoder handles CodeGuru Profiler issues gracefully:

```python
# Example error response for CodeGuru Profiler
{
    "status": "warning",
    "message": "CodeGuru Profiler data unavailable - proceeding with available analyses",
    "recommendation": "Check profiling group configuration and permissions"
}
```

## Testing the Setup

### 1. Test CodeGuru Profiler
```bash
# Run the test script
./scripts/setup-codeguru-profiler.sh test

# Or test manually
aws codeguru-profiler list-profiling-groups
aws codeguru-profiler describe-profiling-group \
    --profiling-group-name ecocoder-default-profiling-group
```

### 2. End-to-End Testing

Test the complete EcoCoder workflow:

```bash
# Make a test pull request to a configured repository
# Check CloudWatch logs for profiling activity
# Verify GitHub comment includes performance analysis
```

## Common Issues and Solutions

### 1. Permission Denied Errors

```bash
# Check your AWS credentials
aws sts get-caller-identity

# Verify CodeGuru Profiler permissions
aws codeguru-profiler list-profiling-groups
```

### 2. Missing Profiling Group

```bash
# Create the default profiling group
./scripts/setup-codeguru-profiler.sh
```

### 3. No Profiling Data

This is normal for new setups. CodeGuru Profiler requires:
- Active application with profiling agent
- Sufficient execution time to collect data
- Proper agent configuration

## Performance Optimization

### Profiling Configuration

```bash
# Optimize profiling for your use case
AWS_CODEGURU_PROFILER_SAMPLING_INTERVAL_MILLIS=1000
AWS_CODEGURU_PROFILER_REPORTING_INTERVAL_MILLIS=60000
AWS_CODEGURU_PROFILER_MAX_STACK_DEPTH=1000
```

### Best Practices

1. **Target Critical Paths**: Profile code sections with performance concerns
2. **Regular Monitoring**: Set up alerts for performance regressions
3. **Integration Testing**: Include performance testing in CI/CD
4. **Cost Management**: Monitor profiling costs and adjust sampling rates

## Support Resources

1. **AWS Documentation**: [CodeGuru Profiler User Guide](https://docs.aws.amazon.com/codeguru/latest/profiler-ug/)
2. **EcoCoder Logs**: Check CloudWatch logs for detailed error messages
3. **AWS Support**: For service-specific issues
4. **Setup Script**: Run `./scripts/setup-codeguru-profiler.sh test` for diagnostics

## Migration Notes

EcoCoder now uses:
- ✅ **CodeGuru Profiler**: For performance analysis (fully supported)
- ✅ **LLM Code Analysis**: Modern replacement for code quality review
- ✅ **Enhanced Integration**: Better error handling and reporting

**Status**: CodeGuru Profiler fully functional with enhanced EcoCoder integration