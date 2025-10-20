# AgentCore Memory Permissions Quick Reference

## Problem
```
AccessDeniedException: User: arn:aws:sts::434114167546:assumed-role/AmazonBedrockAgentCoreSDKRuntime-ap-southeast-1-b953f47315/BedrockAgentCore-dc4563bb-8f6a-48f8-8348-6a0f65be53b7 is not authorized to perform: bedrock-agentcore:ListMemories
```

## Quick Solution
```bash
# Run the automated setup script
./scripts/setup-memory-permissions.sh
```

## What This Does
1. **Finds** your AgentCore runtime execution role automatically
2. **Creates** an IAM policy with all necessary memory permissions
3. **Attaches** the policy to your AgentCore role(s)
4. **Verifies** the setup was successful

## Required Permissions
The script adds these permissions to your AgentCore runtime role:

### Memory Management
- `bedrock-agentcore:ListMemories`
- `bedrock-agentcore:CreateMemory`
- `bedrock-agentcore:GetMemory`
- `bedrock-agentcore:UpdateMemory`
- `bedrock-agentcore:DeleteMemory`

### Memory Records
- `bedrock-agentcore:ListMemoryRecords`
- `bedrock-agentcore:BatchCreateMemoryRecords`
- `bedrock-agentcore:BatchUpdateMemoryRecords`
- `bedrock-agentcore:BatchDeleteMemoryRecords`
- `bedrock-agentcore:GetMemoryRecord`
- `bedrock-agentcore:DeleteMemoryRecord`
- `bedrock-agentcore:RetrieveMemoryRecords`

### Memory Events & Sessions
- `bedrock-agentcore:CreateEvent`
- `bedrock-agentcore:GetEvent`
- `bedrock-agentcore:DeleteEvent`
- `bedrock-agentcore:ListEvents`
- `bedrock-agentcore:ListSessions`
- `bedrock-agentcore:ListActors`

## Manual Setup (if script fails)

1. **Find your AgentCore role**:
   ```bash
   aws iam list-roles --query 'Roles[?contains(RoleName, `BedrockAgentCore`)].RoleName'
   ```

2. **Create the policy**:
   ```bash
   aws iam create-policy \
     --policy-name EcoCoderAgentCoreMemoryPermissions \
     --policy-document file://iam/agentcore-memory-permissions.json
   ```

3. **Attach to role**:
   ```bash
   aws iam attach-role-policy \
     --role-name [YOUR_AGENTCORE_ROLE] \
     --policy-arn arn:aws:iam::[ACCOUNT_ID]:policy/EcoCoderAgentCoreMemoryPermissions
   ```

## Verification

Test that the permissions work:
```bash
agentcore invoke '{"action": "opened", "pull_request": {"number": 1}, "repository": {"full_name": "test/repo"}}'
```

Check the logs for memory initialization:
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/your-agent-id-DEFAULT --follow
```

Look for:
- ✅ `Created AgentCore Memory session for actor=...`
- ❌ `IAM Permission Error: Missing 'bedrock-agentcore:ListMemories' permission`

## Files Created
- `iam/agentcore-memory-permissions.json` - IAM policy document
- `scripts/setup-memory-permissions.sh` - Automated setup script (executable)

## Support
If you encounter issues:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify region: `echo $AWS_REGION`
3. Run the script with verbose output for debugging
4. Check CloudWatch logs for detailed error messages