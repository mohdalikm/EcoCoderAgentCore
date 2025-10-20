# AgentCore Memory IAM Permissions

## Issue Resolution

The `'dict' object has no attribute 'session_id'` error has been resolved by:

1. **Importing proper modules**: Added `AgentCoreMemoryConfig` from `bedrock_agentcore.memory.integrations.strands.config`
2. **Using correct configuration object**: Replaced plain dictionary with `AgentCoreMemoryConfig` object
3. **Adding proper memory client**: Added `MemoryClient` to manage memory resources
4. **Graceful fallback**: Agent works without memory if permissions are insufficient

## Required IAM Permissions for AgentCore Memory

For the agent to use AgentCore Memory features, the following IAM permissions are required:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:CreateMemory",
                "bedrock-agentcore:GetMemory",
                "bedrock-agentcore:ListMemories",
                "bedrock-agentcore:UpdateMemory",
                "bedrock-agentcore:DeleteMemory",
                "bedrock-agentcore:CreateEvent",
                "bedrock-agentcore:ListEvents",
                "bedrock-agentcore:RetrieveMemories"
            ],
            "Resource": "*"
        }
    ]
}
```

## Alternative: Run without Memory

If AgentCore Memory permissions are not available, the agent will automatically fall back to running without persistent memory. This is acceptable for stateless operations where conversation history is not required.

## Deployment Options

### Option 1: Add IAM Permissions
Add the above permissions to your deployment user/role to enable full memory functionality.

### Option 2: Use Environment Variables
Set environment variables to control memory behavior:

```bash
export ENABLE_AGENTCORE_MEMORY=false  # Disable memory entirely
export AWS_REGION=us-east-1           # Set your preferred region
```

### Option 3: Lambda Execution Role
For AWS Lambda deployment, ensure the Lambda execution role has the required AgentCore permissions.

## Testing the Fix

Run the test script to verify the fix:

```bash
python test_session_manager.py
```

The test should pass regardless of IAM permissions, with warnings logged for permission issues.