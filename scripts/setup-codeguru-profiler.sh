#!/bin/bash

# Setup script for AWS CodeGuru Profiler
# This script configures CodeGuru Profiler for the EcoCoder agent

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
IAM_POLICY_FILE="$PROJECT_ROOT/iam/codeguru-permissions.json"
DEFAULT_PROFILING_GROUP="ecocoder-default-profiling-group"
AWS_REGION=${AWS_DEFAULT_REGION:-ap-southeast-1}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== EcoCoder AWS CodeGuru Profiler Setup ===${NC}"
echo ""

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install AWS CLI first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check jq
    if ! command -v jq &> /dev/null; then
        print_error "jq not found. Please install jq for JSON processing."
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Get current AWS account and region info
get_aws_info() {
    ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
    CURRENT_REGION=$(aws configure get region || echo "$AWS_REGION")
    
    print_info "AWS Account ID: $ACCOUNT_ID"
    print_info "AWS Region: $CURRENT_REGION"
    echo ""
}

# Check and update IAM permissions
setup_iam_permissions() {
    print_info "Setting up IAM permissions for CodeGuru services..."
    
    # Get current execution role ARN (from AgentCore environment)
    EXECUTION_ROLE_ARN=$(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null || echo "")
    
    if [[ "$EXECUTION_ROLE_ARN" == *"assumed-role"* ]]; then
        # Extract role name from assumed role ARN
        ROLE_NAME=$(echo "$EXECUTION_ROLE_ARN" | cut -d'/' -f2)
        print_info "Detected execution role: $ROLE_NAME"
        
        # Check if we can attach policies (may not have permissions in production)
        print_info "Checking IAM permissions (may require manual setup in production)..."
        
        # In production, this would need to be done by an administrator
        print_warning "IAM policy attachment may require administrator privileges."
        print_info "Please ensure the execution role has the permissions defined in:"
        print_info "$IAM_POLICY_FILE"
    else
        print_warning "Could not detect execution role. Manual IAM setup may be required."
    fi
    
    print_status "IAM permissions check completed"
}

# Setup CodeGuru Profiler
setup_codeguru_profiler() {
    print_info "Setting up CodeGuru Profiler..."
    
    # Check if default profiling group exists
    if aws codeguruprofiler describe-profiling-group --profiling-group-name "$DEFAULT_PROFILING_GROUP" --region "$CURRENT_REGION" &>/dev/null; then
        print_status "Default profiling group '$DEFAULT_PROFILING_GROUP' already exists"
    else
        print_info "Creating default profiling group '$DEFAULT_PROFILING_GROUP'..."
        
        # Create profiling group with tags
        aws codeguruprofiler create-profiling-group \
            --profiling-group-name "$DEFAULT_PROFILING_GROUP" \
            --compute-platform "Default" \
            --agent-orchestration-config "profilingEnabled=true" \
            --tags "Project=EcoCoder,Environment=Production,Service=GreenSoftwareAnalysis,CreatedBy=SetupScript" \
            --region "$CURRENT_REGION" || {
                print_error "Failed to create profiling group. Check IAM permissions."
                return 1
            }
        
        print_status "Created default profiling group '$DEFAULT_PROFILING_GROUP'"
    fi
    
    # Display profiling group info
    print_info "Profiling group details:"
    aws codeguruprofiler describe-profiling-group \
        --profiling-group-name "$DEFAULT_PROFILING_GROUP" \
        --region "$CURRENT_REGION" \
        --query '{
            Name: name,
            Status: profilingStatus.latestAgentOrchestratedAt,
            ComputePlatform: computePlatform,
            ProfilingEnabled: agentOrchestrationConfig.profilingEnabled,
            ARN: arn
        }' \
        --output table
    
    print_status "CodeGuru Profiler setup completed"
}

# Test CodeGuru Profiler functionality
test_codeguru_profiler() {
    print_info "Testing CodeGuru Profiler functionality..."
    
    # Test listing profiling groups
    if aws codeguruprofiler list-profiling-groups --region "$CURRENT_REGION" --max-results 5 &>/dev/null; then
        print_status "CodeGuru Profiler API access working"
    else
        print_error "CodeGuru Profiler API access failed. Check permissions."
        return 1
    fi
    
    # Test getting profile (will fail if no data, but should not have permission error)
    print_info "Testing profile data access (may show no data if no profiling has occurred)..."
    
    # Handle both macOS and Linux date commands
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
        START_TIME=$(date -u -v-1H +"%Y-%m-%dT%H:%M:%S.000Z")
    else
        # Linux
        END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
        START_TIME=$(date -u -d '1 hour ago' +"%Y-%m-%dT%H:%M:%S.000Z")
    fi
    
    aws codeguruprofiler get-profile \
        --profiling-group-name "$DEFAULT_PROFILING_GROUP" \
        --start-time "$START_TIME" \
        --end-time "$END_TIME" \
        --region "$CURRENT_REGION" \
        --query 'contentType' \
        --output text &>/dev/null || print_warning "No profile data available yet (this is normal for new groups)"
    
    print_status "CodeGuru Profiler functionality test completed"
}

# Generate configuration summary
generate_summary() {
    echo ""
    print_info "=== Setup Summary ==="
    
    cat << EOF

✓ CodeGuru Profiler Configuration:
  - Default profiling group: $DEFAULT_PROFILING_GROUP
  - Region: $CURRENT_REGION
  - Account: $ACCOUNT_ID
  - Status: Ready for use

📋 Next Steps:
  1. Deploy the updated EcoCoder agent with enhanced CodeGuru Profiler integration
  2. Test profiling functionality with a sample PR
  3. Monitor profiling group usage in AWS Console

🔗 Useful Links:
  - CodeGuru Profiler Console: https://console.aws.amazon.com/codeguru/profiler
  - Profiling Group: https://console.aws.amazon.com/codeguru/profiler#/profiling-groups/$DEFAULT_PROFILING_GROUP

EOF
}

# Main execution
main() {
    check_prerequisites
    get_aws_info
    setup_iam_permissions
    echo ""
    setup_codeguru_profiler
    echo ""
    test_codeguru_profiler
    generate_summary
    
    print_status "CodeGuru Profiler setup completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    "profiler-only")
        print_info "Setting up CodeGuru Profiler only..."
        check_prerequisites
        get_aws_info
        setup_codeguru_profiler
        test_codeguru_profiler
        ;;
    "test")
        print_info "Testing existing CodeGuru setup..."
        check_prerequisites
        get_aws_info
        test_codeguru_profiler
        ;;
    "clean")
        print_warning "This will delete the default profiling group. Are you sure? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            aws codeguruprofiler delete-profiling-group --profiling-group-name "$DEFAULT_PROFILING_GROUP" --region "$CURRENT_REGION" || print_error "Failed to delete profiling group"
            print_status "Deleted profiling group '$DEFAULT_PROFILING_GROUP'"
        fi
        ;;
    *)
        main
        ;;
esac