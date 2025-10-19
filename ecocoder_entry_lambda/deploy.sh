#!/bin/bash

# EcoCoder Agent Core - AWS SAM Deployment Script
# This script builds and deploys the EcoCoder agent infrastructure

set -e  # Exit on any error

# Configuration
STACK_NAME="ecocoder-agent-core"
REGION="ap-southeast-1"
ENVIRONMENT="${1:-dev}"  # Default to dev, can be overridden with first argument

echo "🚀 Deploying EcoCoder Agent Core to environment: $ENVIRONMENT"

# Function to print colored output
print_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# Validate SAM CLI is installed
if ! command -v sam &> /dev/null; then
    print_error "SAM CLI is not installed. Please install it first:"
    print_error "https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
    exit 1
fi

# Validate AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS CLI is not configured or credentials are invalid"
    print_error "Please run 'aws configure' to set up your credentials"
    exit 1
fi

print_info "Using AWS Account: $(aws sts get-caller-identity --query Account --output text)"
print_info "Using AWS Region: $REGION"

# Clean any previous build artifacts
print_info "Cleaning previous build artifacts..."
rm -rf .aws-sam/

# Validate the SAM template
print_info "Validating SAM template..."
if sam validate --template template.yaml; then
    print_success "SAM template validation passed"
else
    print_error "SAM template validation failed"
    exit 1
fi

# Build the application
print_info "Building SAM application..."
if sam build --template template.yaml --use-container --cached; then
    print_success "SAM build completed successfully"
else
    print_error "SAM build failed"
    exit 1
fi

# Deploy based on environment
case $ENVIRONMENT in
    "dev")
        print_info "Deploying to development environment..."
        sam deploy --template template.yaml --config-env default --no-confirm-changeset
        ;;
    "staging")
        print_info "Deploying to staging environment..."
        sam deploy --template template.yaml --config-env staging --no-confirm-changeset
        ;;
    "prod")
        print_info "Deploying to production environment..."
        print_warning "You are about to deploy to PRODUCTION!"
        read -p "Are you sure you want to continue? (yes/no): " confirm
        if [[ $confirm == "yes" ]]; then
            sam deploy --template template.yaml --config-env prod --no-confirm-changeset
        else
            print_info "Deployment cancelled"
            exit 0
        fi
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        print_error "Valid environments: dev, staging, prod"
        exit 1
        ;;
esac

# Get the deployment outputs
print_info "Retrieving deployment outputs..."
STACK_NAME_WITH_ENV="${STACK_NAME}"
if [[ $ENVIRONMENT != "dev" ]]; then
    STACK_NAME_WITH_ENV="${STACK_NAME}-${ENVIRONMENT}"
fi

WEBHOOK_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME_WITH_ENV" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`EcoCoderWebhookUrl`].OutputValue' \
    --output text)

HEALTH_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME_WITH_ENV" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`EcoCoderHealthCheckUrl`].OutputValue' \
    --output text)

API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME_WITH_ENV" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`EcoCoderApiUrl`].OutputValue' \
    --output text)

print_success "Deployment completed successfully!"
echo
echo "📋 Deployment Information:"
echo "┌─────────────────────────────────────────────────────────────────────────────────┐"
echo "│ Environment: $ENVIRONMENT"
echo "│ Stack Name:  $STACK_NAME_WITH_ENV"
echo "│ Region:      $REGION"
echo "└─────────────────────────────────────────────────────────────────────────────────┘"
echo
echo "🔗 Important URLs:"
echo "┌─────────────────────────────────────────────────────────────────────────────────┐"
echo "│ GitHub Webhook URL:  $WEBHOOK_URL"
echo "│ Health Check URL:    $HEALTH_URL"
echo "│ API Base URL:        $API_URL"
echo "└─────────────────────────────────────────────────────────────────────────────────┘"
echo
print_info "To configure GitHub webhook, use the following URL:"
print_info "$WEBHOOK_URL"
echo
print_info "To test the deployment, run:"
print_info "curl $HEALTH_URL"
echo

# Optional: Test the health endpoint
read -p "Do you want to test the health endpoint now? (y/n): " test_health
if [[ $test_health =~ ^[Yy]$ ]]; then
    print_info "Testing health endpoint..."
    if curl -s "$HEALTH_URL" | jq . > /dev/null 2>&1; then
        print_success "Health check passed!"
        curl -s "$HEALTH_URL" | jq .
    else
        print_warning "Health check returned non-JSON response or failed"
        curl -s "$HEALTH_URL"
    fi
fi

print_success "Deployment script completed!"