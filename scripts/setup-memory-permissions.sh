#!/bin/bash

# Script to update AgentCore runtime execution role with memory permissions
# This script finds the AgentCore runtime role and attaches the memory permissions policy

set -e

# Configuration
REGION="${AWS_REGION:-ap-southeast-1}"
POLICY_NAME="EcoCoderAgentCoreMemoryPermissions"
POLICY_FILE="iam/agentcore-memory-permissions.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 EcoCoder AgentCore Memory Permissions Setup${NC}"
echo "=================================================="

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ Error: AWS CLI not configured or no valid credentials${NC}"
    exit 1
fi

# Get current AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS Account ID: ${ACCOUNT_ID}${NC}"

# Check if policy file exists
if [[ ! -f "$POLICY_FILE" ]]; then
    echo -e "${RED}❌ Error: Policy file $POLICY_FILE not found${NC}"
    exit 1
fi

echo -e "${BLUE}🔍 Finding AgentCore runtime execution role...${NC}"

# Find AgentCore runtime execution roles
AGENTCORE_ROLES=$(aws iam list-roles \
    --query 'Roles[?contains(RoleName, `BedrockAgentCore`) && contains(RoleName, `Runtime`)].RoleName' \
    --output text 2>/dev/null || echo "")

if [[ -z "$AGENTCORE_ROLES" ]]; then
    echo -e "${YELLOW}⚠️  No AgentCore runtime roles found with standard naming convention${NC}"
    echo -e "${YELLOW}    Let's try to find any roles with 'AgentCore' in the name...${NC}"
    
    ALL_AGENTCORE_ROLES=$(aws iam list-roles \
        --query 'Roles[?contains(RoleName, `AgentCore`)].RoleName' \
        --output text 2>/dev/null || echo "")
    
    if [[ -z "$ALL_AGENTCORE_ROLES" ]]; then
        echo -e "${RED}❌ No AgentCore roles found. Please ensure your agent is deployed first.${NC}"
        echo -e "${YELLOW}💡 Run 'agentcore launch' to deploy your agent, then run this script again.${NC}"
        exit 1
    else
        echo -e "${YELLOW}Found AgentCore roles:${NC}"
        for role in $ALL_AGENTCORE_ROLES; do
            echo -e "${YELLOW}  - $role${NC}"
        done
        AGENTCORE_ROLES="$ALL_AGENTCORE_ROLES"
    fi
fi

echo -e "${GREEN}✅ Found AgentCore roles:${NC}"
for role in $AGENTCORE_ROLES; do
    echo -e "${GREEN}  - $role${NC}"
done

# Create or update the policy
echo -e "${BLUE}📋 Creating/updating IAM policy: $POLICY_NAME${NC}"

POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"

# Check if policy already exists
if aws iam get-policy --policy-arn "$POLICY_ARN" &>/dev/null; then
    echo -e "${YELLOW}⚠️  Policy already exists, creating new version...${NC}"
    
    # Create new policy version
    VERSION_ID=$(aws iam create-policy-version \
        --policy-arn "$POLICY_ARN" \
        --policy-document file://"$POLICY_FILE" \
        --set-as-default \
        --query 'PolicyVersion.VersionId' \
        --output text)
    
    echo -e "${GREEN}✅ Created policy version: $VERSION_ID${NC}"
else
    echo -e "${BLUE}📝 Creating new policy...${NC}"
    
    # Create new policy
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file://"$POLICY_FILE" \
        --description "Memory permissions for EcoCoder AgentCore runtime" \
        --output table
    
    echo -e "${GREEN}✅ Created policy: $POLICY_ARN${NC}"
fi

# Attach policy to all AgentCore roles
echo -e "${BLUE}🔗 Attaching policy to AgentCore roles...${NC}"

for role in $AGENTCORE_ROLES; do
    echo -e "${BLUE}   Attaching to role: $role${NC}"
    
    # Check if policy is already attached
    if aws iam list-attached-role-policies --role-name "$role" \
        --query "AttachedPolicies[?PolicyArn=='$POLICY_ARN']" \
        --output text | grep -q "$POLICY_ARN"; then
        echo -e "${YELLOW}   ⚠️  Policy already attached to $role${NC}"
    else
        # Attach the policy
        if aws iam attach-role-policy \
            --role-name "$role" \
            --policy-arn "$POLICY_ARN"; then
            echo -e "${GREEN}   ✅ Successfully attached policy to $role${NC}"
        else
            echo -e "${RED}   ❌ Failed to attach policy to $role${NC}"
        fi
    fi
done

echo ""
echo -e "${GREEN}🎉 Memory permissions setup completed!${NC}"
echo ""
echo -e "${BLUE}📊 Summary:${NC}"
echo -e "${BLUE}  Policy ARN: $POLICY_ARN${NC}"
echo -e "${BLUE}  Applied to roles:${NC}"
for role in $AGENTCORE_ROLES; do
    echo -e "${BLUE}    - $role${NC}"
done

echo ""
echo -e "${YELLOW}🔄 Next Steps:${NC}"
echo -e "${YELLOW}1. Test your agent to ensure memory functionality works${NC}"
echo -e "${YELLOW}2. Check CloudWatch logs for any remaining permission issues${NC}"
echo -e "${YELLOW}3. Use 'agentcore invoke' to test with a sample payload${NC}"

echo ""
echo -e "${GREEN}✅ Setup complete! Your AgentCore agent now has memory permissions.${NC}"