#!/bin/bash

# EcoCoder Agent Core - Local Testing Script
# This script helps test the Lambda function locally using SAM CLI

set -e

echo "🧪 Starting local testing for EcoCoder Agent Core"

# Function to print colored output
print_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# Check if SAM is built
if [ ! -d ".aws-sam" ]; then
    print_info "Building SAM application first..."
    sam build
fi

# Test type selection
echo "Select test type:"
echo "1. Start local API (for webhook testing)"
echo "2. Test health endpoint"
echo "3. Test webhook with sample payload"
echo "4. Invoke function directly"

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        print_info "Starting local API Gateway..."
        print_info "The API will be available at: http://localhost:3000"
        print_info "Webhook endpoint: http://localhost:3000/webhook"
        print_info "Health endpoint: http://localhost:3000/health"
        print_info "Press Ctrl+C to stop"
        sam local start-api --host 0.0.0.0 --port 3000
        ;;
    
    2)
        print_info "Testing health endpoint..."
        if [ -f "test_events/health_check.json" ]; then
            # Use the predefined test event
            sam local invoke EcoCoderCoreEntryFunction --event test_events/health_check.json
        else
            # Create a health check event
            cat > /tmp/health_event.json << EOF
{
    "requestContext": {
        "http": {
            "method": "GET"
        }
    },
    "headers": {},
    "pathParameters": {
        "proxy": "health"
    },
    "body": ""
}
EOF
            sam local invoke EcoCoderCoreEntryFunction --event /tmp/health_event.json
            rm /tmp/health_event.json
        fi
        ;;
    
    3)
        print_info "Testing webhook with sample GitHub payload..."
        if [ -f "test_events/test_pr_payload.json" ]; then
            # Use existing test payload
            print_info "Using existing test_pr_payload.json"
            sam local invoke EcoCoderCoreEntryFunction --event test_events/test_pr_payload.json
        elif [ -f "test_events/webhook_pr_opened.json" ]; then
            # Use the predefined test event
            print_info "Using predefined webhook test event"
            sam local invoke EcoCoderCoreEntryFunction --event test_events/webhook_pr_opened.json
        else
            # Create a sample webhook event
            cat > /tmp/webhook_event.json << EOF
{
    "requestContext": {
        "http": {
            "method": "POST"
        }
    },
    "headers": {
        "X-GitHub-Event": "pull_request",
        "Content-Type": "application/json"
    },
    "pathParameters": {
        "proxy": "webhook"
    },
    "body": "{\"action\":\"opened\",\"pull_request\":{\"number\":123,\"title\":\"Test: Add webhook integration\",\"head\":{\"ref\":\"feature/webhook\",\"sha\":\"abc123def\"},\"base\":{\"ref\":\"main\"}},\"repository\":{\"full_name\":\"test/webhook-repo\",\"clone_url\":\"https://github.com/test/webhook-repo.git\",\"owner\":{\"id\":\"12345\"}}}"
}
EOF
            sam local invoke EcoCoderCoreEntryFunction --event /tmp/webhook_event.json
            rm /tmp/webhook_event.json
        fi
        ;;
    
    4)
        print_info "Invoking function directly with custom event..."
        echo "Please provide the path to your JSON event file:"
        read -p "Event file path: " event_file
        
        if [ -f "$event_file" ]; then
            sam local invoke EcoCoderCoreEntryFunction --event "$event_file"
        else
            print_error "Event file not found: $event_file"
            exit 1
        fi
        ;;
    
    *)
        print_error "Invalid choice: $choice"
        exit 1
        ;;
esac

print_success "Local testing completed!"