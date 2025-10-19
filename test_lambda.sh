#!/bin/bash

# EcoCoder Agent Core - Root Level Testing Wrapper
# This script provides easy access to Lambda testing from the root directory

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
LAMBDA_DIR="$SCRIPT_DIR/ecocoder_entry_lambda"

echo "🧪 EcoCoder Agent Core Testing Wrapper"
echo "Delegating to Lambda testing script..."
echo

# Check if Lambda directory exists
if [ ! -d "$LAMBDA_DIR" ]; then
    echo "❌ Error: Lambda directory not found at $LAMBDA_DIR"
    exit 1
fi

# Navigate to Lambda directory and run testing
cd "$LAMBDA_DIR"

# Run the testing script
./test_local.sh