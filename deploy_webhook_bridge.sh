#!/bin/bash
"""
Deploy GitHub Webhook Bridge Lambda Function
Quick deployment script for hackathon
"""

set -e

echo "🚀 Deploying GitHub Webhook Bridge Lambda Function..."

# Configuration
FUNCTION_NAME="ecocoder-github-webhook-bridge"
AGENT_ARN="arn:aws:bedrock-agentcore:ap-southeast-1:434114167546:runtime/ecocoderagentcore-H0kpdY5A85"
REGION="ap-southeast-1"
ROLE_NAME="EcoCoderLambdaExecutionRole"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "Function Name: $FUNCTION_NAME"
echo "Agent ARN: $AGENT_ARN"
echo "Region: $REGION"
echo ""

# Create IAM role for Lambda if it doesn't exist
echo -e "${YELLOW}🔐 Creating IAM role...${NC}"
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' \
    --region $REGION \
    2>/dev/null || echo "Role already exists"

# Attach basic Lambda execution policy
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
    --region $REGION

# Create custom policy for Bedrock AgentCore access
echo -e "${YELLOW}📝 Creating AgentCore access policy...${NC}"
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name BedrockAgentCoreInvokePolicy \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:InvokeAgentRuntime"
                ],
                "Resource": "'$AGENT_ARN'"
            }
        ]
    }' \
    --region $REGION

echo -e "${GREEN}✅ IAM role configured${NC}"

# Wait for role propagation
echo -e "${YELLOW}⏳ Waiting for IAM role propagation...${NC}"
sleep 10

# Get the role ARN
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text --region $REGION)
echo "Role ARN: $ROLE_ARN"

# Create deployment package
echo -e "${YELLOW}📦 Creating deployment package...${NC}"
rm -rf lambda_package.zip lambda_temp/
mkdir -p lambda_temp

# Copy Lambda function
cp lambda_webhook_bridge.py lambda_temp/lambda_function.py

# Install dependencies if any (boto3 is included in Lambda runtime)
cd lambda_temp

# Create the deployment package
zip -r ../lambda_package.zip . > /dev/null
cd ..

echo -e "${GREEN}✅ Deployment package created${NC}"

# Deploy Lambda function
echo -e "${YELLOW}🚀 Deploying Lambda function...${NC}"

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo "Function exists, updating..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_package.zip \
        --region $REGION > /dev/null
    
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment "Variables={AGENT_ARN=$AGENT_ARN,ECOCODER_REGION=$REGION}" \
        --timeout 30 \
        --memory-size 256 \
        --region $REGION > /dev/null
else
    echo "Creating new function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.11 \
        --role $ROLE_ARN \
        --handler lambda_function.lambda_handler \
        --zip-file fileb://lambda_package.zip \
        --environment "Variables={AGENT_ARN=$AGENT_ARN,ECOCODER_REGION=$REGION}" \
        --timeout 30 \
        --memory-size 256 \
        --region $REGION > /dev/null
fi

echo -e "${GREEN}✅ Lambda function deployed${NC}"

# Create or update Function URL
echo -e "${YELLOW}🌐 Creating Function URL...${NC}"

# Try to create the function URL first, if it fails, try to get existing one
FUNCTION_URL=$(aws lambda create-function-url-config \
    --function-name $FUNCTION_NAME \
    --auth-type NONE \
    --cors '{
        "AllowCredentials": false,
        "AllowHeaders": ["Content-Type", "X-GitHub-Event", "X-Hub-Signature-256"],
        "AllowMethods": ["POST", "OPTIONS"],
        "AllowOrigins": ["*"],
        "ExposeHeaders": ["Content-Type"],
        "MaxAge": 86400
    }' \
    --region $REGION \
    --query 'FunctionUrl' \
    --output text 2>/dev/null)

# If creation failed, try to get existing URL
if [ -z "$FUNCTION_URL" ]; then
    FUNCTION_URL=$(aws lambda get-function-url-config \
        --function-name $FUNCTION_NAME \
        --region $REGION \
        --query 'FunctionUrl' \
        --output text 2>/dev/null)
fi

echo -e "${GREEN}✅ Function URL configured${NC}"

# Clean up
rm -rf lambda_package.zip lambda_temp/

echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo ""
echo -e "${YELLOW}📋 GitHub Webhook Configuration:${NC}"
echo "Webhook URL: $FUNCTION_URL"
echo "Content Type: application/json"
echo "Events: Pull requests (opened, synchronize, reopened)"
echo "Secret: (optional for hackathon)"
echo ""
echo -e "${YELLOW}🔧 Testing:${NC}"
echo "Test URL: curl -X POST $FUNCTION_URL -H 'X-GitHub-Event: ping' -d '{}'"
echo ""
echo -e "${YELLOW}📊 Monitoring:${NC}"
echo "CloudWatch Logs: /aws/lambda/$FUNCTION_NAME"
echo "AWS Console: https://console.aws.amazon.com/lambda/home?region=$REGION#/functions/$FUNCTION_NAME"
echo ""