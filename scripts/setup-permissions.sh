#!/bin/bash

# Script to setup EcoCoder AgentCore permissions
# This script finds the AgentCore runtime role and attaches necessary permissions policies

set -e

# Configuration
REGION="${AWS_REGION:-ap-southeast-1}"
MEMORY_POLICY_NAME="EcoCoderAgentCoreMemoryPermissions"
CODEGURU_POLICY_NAME="EcoCoderAgentCoreCodeGuruPermissions"
CODEBUILD_POLICY_NAME="EcoCoderCodeBuildServiceRolePermissions"
MEMORY_POLICY_FILE="iam/agentcore-memory-permissions.json"
CODEGURU_POLICY_FILE="iam/codeguru-permissions.json"
CODEBUILD_POLICY_FILE="iam/codebuild-service-role-permissions.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}🚀 EcoCoder AgentCore Permissions Setup${NC}"
echo "========================================="
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ Error: AWS CLI not configured or no valid credentials${NC}"
    exit 1
fi

# Get current AWS account ID and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ACTUAL_REGION=$(aws configure get region || echo $REGION)
echo -e "${GREEN}✅ AWS Account ID: ${ACCOUNT_ID}${NC}"
echo -e "${GREEN}✅ AWS Region: ${ACTUAL_REGION}${NC}"
echo ""

# Check if policy files exist
echo -e "${BLUE}📂 Checking policy files...${NC}"
for policy_file in "$MEMORY_POLICY_FILE" "$CODEGURU_POLICY_FILE" "$CODEBUILD_POLICY_FILE"; do
    if [[ ! -f "$policy_file" ]]; then
        echo -e "${RED}❌ Error: Policy file $policy_file not found${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ Found: $policy_file${NC}"
    fi
done
echo ""

# Function to create or update policy
create_or_update_policy() {
    local policy_name="$1"
    local policy_file="$2"
    local description="$3"
    
    echo -e "${BLUE}📋 Processing IAM policy: $policy_name${NC}" >&2
    
    local policy_arn="arn:aws:iam::${ACCOUNT_ID}:policy/${policy_name}"
    
    # Check if policy already exists
    if aws iam get-policy --policy-arn "$policy_arn" &>/dev/null; then
        echo -e "${YELLOW}⚠️  Policy exists, creating new version...${NC}" >&2
        
        # Create new policy version
        local version_id=$(aws iam create-policy-version \
            --policy-arn "$policy_arn" \
            --policy-document file://"$policy_file" \
            --set-as-default \
            --query 'PolicyVersion.VersionId' \
            --output text 2>/dev/null)
        
        echo -e "${GREEN}✅ Created policy version: $version_id${NC}" >&2
    else
        echo -e "${BLUE}📝 Creating new policy...${NC}" >&2
        
        # Create new policy
        aws iam create-policy \
            --policy-name "$policy_name" \
            --policy-document file://"$policy_file" \
            --description "$description" \
            --output table &>/dev/null
        
        echo -e "${GREEN}✅ Created policy: $policy_arn${NC}" >&2
    fi
    
    # Return just the ARN
    echo "$policy_arn"
}

# Function to attach policy to role
attach_policy_to_role() {
    local role="$1"
    local policy_arn="$2"
    local policy_name="$3"
    
    echo -e "${BLUE}   → Attaching $policy_name to role: $role${NC}"
    
    # Check if policy is already attached
    local attached_policies=$(aws iam list-attached-role-policies --role-name "$role" \
        --query "AttachedPolicies[?PolicyArn=='$policy_arn']" \
        --output text 2>/dev/null)
    
    if [[ -n "$attached_policies" ]]; then
        echo -e "${YELLOW}   ⚠️  Policy already attached to $role${NC}"
        return 0
    else
        # Attach the policy
        if aws iam attach-role-policy \
            --role-name "$role" \
            --policy-arn "$policy_arn" 2>/dev/null; then
            echo -e "${GREEN}   ✅ Successfully attached $policy_name to $role${NC}"
            return 0
        else
            echo -e "${RED}   ❌ Failed to attach $policy_name to $role${NC}"
            return 1
        fi
    fi
}

echo -e "${BLUE}🔍 Finding AgentCore runtime execution role...${NC}"

# Find AgentCore runtime execution roles (exclude service-linked roles)
AGENTCORE_ROLES=$(aws iam list-roles \
    --query 'Roles[?contains(RoleName, `BedrockAgentCore`) && contains(RoleName, `Runtime`) && !contains(RoleName, `AWSServiceRole`)].RoleName' \
    --output text 2>/dev/null || echo "")

echo -e "${BLUE}🔍 Finding CodeBuild service roles...${NC}"

# Find CodeBuild service roles
CODEBUILD_ROLES=$(aws iam list-roles \
    --query 'Roles[?contains(RoleName, `CodeBuild`) && !contains(RoleName, `AWSServiceRole`)].RoleName' \
    --output text 2>/dev/null || echo "")

# Also look for eco-coder specific CodeBuild roles
ECOCODER_CODEBUILD_ROLES=$(aws iam list-roles \
    --query 'Roles[?contains(RoleName, `eco-coder`) && contains(RoleName, `CodeBuild`)].RoleName' \
    --output text 2>/dev/null || echo "")

if [[ -z "$AGENTCORE_ROLES" ]]; then
    echo -e "${YELLOW}⚠️  No standard AgentCore runtime roles found${NC}"
    echo -e "${YELLOW}    Searching for any roles with 'AgentCore' in the name...${NC}"
    
    ALL_AGENTCORE_ROLES=$(aws iam list-roles \
        --query 'Roles[?contains(RoleName, `AgentCore`) && !contains(RoleName, `AWSServiceRole`)].RoleName' \
        --output text 2>/dev/null || echo "")
    
    if [[ -z "$ALL_AGENTCORE_ROLES" ]]; then
        echo -e "${RED}❌ No modifiable AgentCore roles found${NC}"
        echo -e "${YELLOW}💡 Please ensure your agent is deployed first using 'agentcore launch'${NC}"
        exit 1
    else
        echo -e "${YELLOW}Found these modifiable AgentCore roles:${NC}"
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
echo ""

# Create/update policies
echo -e "${PURPLE}🛠️  Creating/updating IAM policies...${NC}"
echo ""

MEMORY_POLICY_ARN=$(create_or_update_policy \
    "$MEMORY_POLICY_NAME" \
    "$MEMORY_POLICY_FILE" \
    "Bedrock AgentCore memory permissions for EcoCoder")

echo ""

CODEGURU_POLICY_ARN=$(create_or_update_policy \
    "$CODEGURU_POLICY_NAME" \
    "$CODEGURU_POLICY_FILE" \
    "CodeGuru Profiler permissions for EcoCoder")

echo ""

CODEBUILD_POLICY_ARN=$(create_or_update_policy \
    "$CODEBUILD_POLICY_NAME" \
    "$CODEBUILD_POLICY_FILE" \
    "CodeBuild service role permissions for EcoCoder profiling")

echo ""

# Process CodeBuild roles
ALL_CODEBUILD_ROLES="$CODEBUILD_ROLES $ECOCODER_CODEBUILD_ROLES"
ALL_CODEBUILD_ROLES=$(echo "$ALL_CODEBUILD_ROLES" | tr ' ' '\n' | sort -u | tr '\n' ' ' | sed 's/[[:space:]]*$//')

if [[ -n "$ALL_CODEBUILD_ROLES" ]]; then
    echo -e "${GREEN}✅ Found CodeBuild roles:${NC}"
    for role in $ALL_CODEBUILD_ROLES; do
        echo -e "${GREEN}  - $role${NC}"
    done
    echo ""
fi

# Attach policies to all AgentCore roles
echo -e "${PURPLE}🔗 Attaching policies to AgentCore roles...${NC}"

SUCCESS_COUNT=0
AGENTCORE_ROLE_COUNT=$(echo $AGENTCORE_ROLES | wc -w)
CODEBUILD_ROLE_COUNT=$(echo $ALL_CODEBUILD_ROLES | wc -w)
TOTAL_ATTACHMENTS=$((AGENTCORE_ROLE_COUNT * 2 + CODEBUILD_ROLE_COUNT))  # 2 policies per agentcore role + 1 per codebuild role

for role in $AGENTCORE_ROLES; do
    echo -e "${BLUE}🎯 Processing AgentCore role: $role${NC}"
    
    # Attach memory permissions
    if attach_policy_to_role "$role" "$MEMORY_POLICY_ARN" "$MEMORY_POLICY_NAME"; then
        ((SUCCESS_COUNT++))
    fi
    
    # Attach CodeGuru permissions
    if attach_policy_to_role "$role" "$CODEGURU_POLICY_ARN" "$CODEGURU_POLICY_NAME"; then
        ((SUCCESS_COUNT++))
    fi
    
    echo ""
done

# Attach CodeBuild permissions to CodeBuild roles
if [[ -n "$ALL_CODEBUILD_ROLES" ]]; then
    echo -e "${PURPLE}🔗 Attaching CodeBuild permissions to CodeBuild service roles...${NC}"
    
    for role in $ALL_CODEBUILD_ROLES; do
        echo -e "${BLUE}🎯 Processing CodeBuild role: $role${NC}"
        
        # Attach CodeBuild service role permissions
        if attach_policy_to_role "$role" "$CODEBUILD_POLICY_ARN" "$CODEBUILD_POLICY_NAME"; then
            ((SUCCESS_COUNT++))
        fi
        
        echo ""
    done
else
    echo -e "${YELLOW}⚠️  No CodeBuild service roles found${NC}"
    echo -e "${YELLOW}    CodeBuild projects may need manual role configuration${NC}"
    echo ""
fi

# Summary
echo -e "${PURPLE}📊 Setup Summary${NC}"
echo "=================="
echo -e "${BLUE}Account ID:${NC} $ACCOUNT_ID"
echo -e "${BLUE}Region:${NC} $ACTUAL_REGION"
echo -e "${BLUE}Policies Created/Updated:${NC}"
echo -e "  • $MEMORY_POLICY_NAME"
echo -e "    └─ $MEMORY_POLICY_ARN"
echo -e "  • $CODEGURU_POLICY_NAME"
echo -e "    └─ $CODEGURU_POLICY_ARN"
echo -e "  • $CODEBUILD_POLICY_NAME"
echo -e "    └─ $CODEBUILD_POLICY_ARN"

echo -e "${BLUE}Roles Updated:${NC}"
echo -e "${BLUE}  AgentCore Roles:${NC}"
for role in $AGENTCORE_ROLES; do
    echo -e "    • $role"
done
if [[ -n "$ALL_CODEBUILD_ROLES" ]]; then
    echo -e "${BLUE}  CodeBuild Roles:${NC}"
    for role in $ALL_CODEBUILD_ROLES; do
        echo -e "    • $role"
    done
fi

echo -e "${BLUE}Policy Attachments:${NC} $SUCCESS_COUNT/$TOTAL_ATTACHMENTS successful"
echo ""

if [[ $SUCCESS_COUNT -eq $TOTAL_ATTACHMENTS ]]; then
    echo -e "${GREEN}🎉 All permissions configured successfully!${NC}"
    echo ""
    echo -e "${PURPLE}✨ Your EcoCoder agent now has access to:${NC}"
    echo -e "${GREEN}  ✅ Bedrock AgentCore Memory Management${NC}"
    echo -e "${GREEN}  ✅ CodeGuru Profiler (Performance Analysis)${NC}"
    echo -e "${GREEN}  ✅ LLM Code Analysis (Code Quality)${NC}"
    echo -e "${GREEN}  ✅ Systems Manager Parameters${NC}"
    echo -e "${GREEN}  ✅ Secrets Manager${NC}"
    echo -e "${GREEN}  ✅ CloudWatch Logs (CodeBuild Integration)${NC}"
    echo ""
    echo -e "${YELLOW}🔄 Next Steps:${NC}"
    echo -e "${YELLOW}1. Test profiler: agentcore invoke --test-codeguru${NC}"
    echo -e "${YELLOW}2. Monitor logs: aws logs tail /aws/lambda/ecocoder --follow${NC}"
    echo -e "${YELLOW}3. Create test PR to verify end-to-end functionality${NC}"
else
    echo -e "${YELLOW}⚠️  Some policy attachments failed. Check the output above.${NC}"
    echo -e "${YELLOW}You may need to run this script again or check IAM permissions.${NC}"
fi

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"