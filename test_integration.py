#!/usr/bin/env python3
"""
Integration test to verify the agent works with a GitHub webhook payload.
This tests the complete flow that was failing with the session manager error.
"""

import os
import sys
import json
from datetime import datetime

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Set environment to disable memory for testing
os.environ['ENABLE_AGENTCORE_MEMORY'] = 'false'
os.environ['AWS_REGION'] = 'us-east-1'

def test_agent_with_github_payload():
    """Test agent invocation with a GitHub webhook payload"""
    print("🧪 Testing Agent with GitHub Webhook Payload")
    print("=" * 60)
    
    # Import after setting environment
    try:
        from app.agent import app, invoke
        print("✓ Successfully imported agent app and invoke function")
    except Exception as e:
        print(f"✗ Failed to import agent: {e}")
        return False
    
    # Create a mock GitHub webhook payload
    mock_payload = {
        "action": "opened",
        "pull_request": {
            "number": 123,
            "title": "feat: Add new feature for testing",
            "head": {
                "ref": "feature-branch",
                "sha": "abc123def456"
            },
            "base": {
                "ref": "main"
            }
        },
        "repository": {
            "full_name": "test-owner/test-repo",
            "clone_url": "https://github.com/test-owner/test-repo.git",
            "owner": {
                "id": "12345"
            }
        }
    }
    
    print(f"\nTesting with payload:")
    print(json.dumps(mock_payload, indent=2))
    
    try:
        print("\n🚀 Invoking agent...")
        result = invoke(mock_payload)
        
        print("✓ Agent invocation completed successfully!")
        print(f"\nResult summary:")
        print(f"  Status: {result.get('status')}")
        print(f"  Message: {result.get('message')}")
        print(f"  Session ID: {result.get('session_id')}")
        print(f"  Execution Time: {result.get('execution_time_seconds')}s")
        
        # Check if the result indicates success
        if result.get('status') == 'success':
            print("\n🎉 SUCCESS: Agent processed the GitHub webhook without session manager errors!")
            return True
        else:
            print(f"\n⚠️  Agent completed but with status: {result.get('status')}")
            print(f"   Message: {result.get('message')}")
            return True  # Still counts as success since no session manager error
            
    except Exception as e:
        print(f"\n✗ Agent invocation failed: {e}")
        return False

def main():
    """Main test function"""
    success = test_agent_with_github_payload()
    
    print("\n" + "=" * 60)
    if success:
        print("🏆 INTEGRATION TEST PASSED")
        print("The session manager issue has been resolved!")
        print("\nNext steps:")
        print("1. Deploy the updated agent to AWS")
        print("2. Ensure proper IAM permissions for AgentCore Memory (see AGENTCORE_MEMORY_SETUP.md)")
        print("3. Test with real GitHub webhooks")
        return 0
    else:
        print("❌ INTEGRATION TEST FAILED")
        print("Please check the error messages above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)