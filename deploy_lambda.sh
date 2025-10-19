#!/bin/bash

# EcoCoder Agent Core - Root Level Deployment Wrapper
# This script provides easy access to Lambda deployment from the root directory

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
LAMBDA_DIR="$SCRIPT_DIR/ecocoder_entry_lambda"

echo "🚀 EcoCoder Agent Core Deployment Wrapper"
echo "Delegating to Lambda deployment script..."
echo

# Check if Lambda directory exists
if [ ! -d "$LAMBDA_DIR" ]; then
    echo "❌ Error: Lambda directory not found at $LAMBDA_DIR"
    exit 1
fi

# Navigate to Lambda directory and run deployment
cd "$LAMBDA_DIR"

# Pass all arguments to the actual deployment script
./deploy.sh "$@"