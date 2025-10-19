#!/bin/bash

# EcoCoder Agent Core - Cleanup Script
# This script removes the deployed AWS resources

set -e

ENVIRONMENT="${1:-dev}"
STACK_NAME="ecocoder-agent-core"

if [[ $ENVIRONMENT != "dev" ]]; then
    STACK_NAME="${STACK_NAME}-${ENVIRONMENT}"
fi

echo "🗑️  Cleaning up EcoCoder Agent Core resources for environment: $ENVIRONMENT"
echo "Stack name: $STACK_NAME"

read -p "Are you sure you want to delete the stack? This cannot be undone. (yes/no): " confirm

if [[ $confirm == "yes" ]]; then
    echo "Deleting CloudFormation stack..."
    aws cloudformation delete-stack --stack-name "$STACK_NAME" --region ap-southeast-1
    
    echo "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region ap-southeast-1
    
    echo "✅ Stack deleted successfully!"
else
    echo "Cleanup cancelled."
fi