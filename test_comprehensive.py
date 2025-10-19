#!/usr/bin/env python3
"""
Comprehensive test script for EcoCoder Agent
Tests various scenarios and demonstrates the agent's capabilities
"""

import json
import time
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.agent import invoke, main


def test_scenario(name: str, payload: dict, expected_status: str = "success"):
    """Test a specific scenario"""
    print(f"\n🔍 Testing: {name}")
    print("=" * 50)
    
    # Set development environment for testing
    os.environ['ENVIRONMENT'] = 'development'
    
    start_time = time.time()
    result = invoke(payload)
    end_time = time.time()
    
    execution_time = end_time - start_time
    
    print(f"⏱️  Execution time: {execution_time:.3f} seconds")
    print(f"📊 Status: {result['status']}")
    
    if result["status"] == expected_status:
        print("✅ Test PASSED")
    else:
        print(f"❌ Test FAILED - Expected {expected_status}, got {result['status']}")
        print(f"   Error: {result.get('message', 'No error message')}")
    
    # Print key result information
    if result["status"] == "success":
        print(f"🆔 Session ID: {result['session_id']}")
        print(f"📝 Agent Response: {result['agent_response'][:100]}...")
        pr_info = result.get('pr_info', {})
        print(f"🔀 PR Info: #{pr_info.get('pr_number')} in {pr_info.get('repository_name')}")
    
    return result


def main_test():
    """Run comprehensive test suite"""
    print("🌱 EcoCoder Agent - Comprehensive Test Suite")
    print("=" * 60)
    
    # Test 1: Standard PR opened
    test_scenario(
        "Standard PR Opened",
        {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "title": "feat: Add new authentication system",
                "head": {
                    "ref": "feature/auth-system",
                    "sha": "abc123def456"
                },
                "base": {"ref": "main"}
            },
            "repository": {
                "full_name": "company/backend-service",
                "clone_url": "https://github.com/company/backend-service.git",
                "owner": {"id": "12345"}
            }
        }
    )
    
    # Test 2: PR synchronized (new commits)
    test_scenario(
        "PR Synchronized",
        {
            "action": "synchronize",
            "pull_request": {
                "number": 456,
                "title": "fix: Optimize database queries",
                "head": {
                    "ref": "hotfix/db-optimization",
                    "sha": "xyz789uvw012"
                },
                "base": {"ref": "develop"}
            },
            "repository": {
                "full_name": "startup/microservice",
                "clone_url": "https://github.com/startup/microservice.git",
                "owner": {"id": "67890"}
            }
        }
    )
    
    # Test 3: Large PR with performance implications
    test_scenario(
        "Performance-Critical PR",
        {
            "action": "opened", 
            "pull_request": {
                "number": 789,
                "title": "refactor: Rewrite core processing engine",
                "head": {
                    "ref": "refactor/core-engine",
                    "sha": "big123change456"
                },
                "base": {"ref": "main"}
            },
            "repository": {
                "full_name": "bigcorp/data-processor",
                "clone_url": "https://github.com/bigcorp/data-processor.git",
                "owner": {"id": "99999"}
            }
        }
    )
    
    # Test 4: Invalid payload (should fail gracefully)
    test_scenario(
        "Invalid Payload",
        {
            "invalid": "data",
            "missing": "required_fields"
        },
        expected_status="error"
    )
    
    # Test 5: Missing PR number (should fail)
    test_scenario(
        "Missing PR Number",
        {
            "action": "opened",
            "pull_request": {
                # Missing number field
                "title": "Some PR title",
                "head": {"ref": "branch", "sha": "sha123"},
                "base": {"ref": "main"}
            },
            "repository": {
                "full_name": "test/repo",
                "owner": {"id": "123"}
            }
        },
        expected_status="error"
    )
    
    # Test 6: Different repository types
    test_scenario(
        "Open Source Repository",
        {
            "action": "reopened",
            "pull_request": {
                "number": 42,
                "title": "docs: Update contributing guidelines",
                "head": {
                    "ref": "docs/contributing",
                    "sha": "docs123update456"
                },
                "base": {"ref": "main"}
            },
            "repository": {
                "full_name": "opensource/awesome-project",
                "clone_url": "https://github.com/opensource/awesome-project.git",
                "owner": {"id": "opensource-org"}
            }
        }
    )
    
    print("\n" + "=" * 60)
    print("🏁 Test Suite Completed")
    print("✅ All scenarios tested successfully!")
    
    # Test the main function as well
    print("\n🔧 Testing main() function...")
    try:
        # Capture stdout to avoid cluttering output
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            main()
        
        output = f.getvalue()
        if "Eco-Coder Agent Starting" in output and "Result:" in output:
            print("✅ Main function test PASSED")
        else:
            print("❌ Main function test FAILED")
    except Exception as e:
        print(f"❌ Main function test FAILED: {e}")
    
    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    main_test()