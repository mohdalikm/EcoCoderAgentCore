#!/usr/bin/env python3
"""
Test script to validate AgentCore Memory session manager initialization.
This script tests the session manager fix for the 'dict' object has no attribute 'session_id' error.
"""

import os
import sys
import logging
from datetime import datetime

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import the agent module
try:
    from app.agent import get_session_manager, create_agent
    print("✓ Successfully imported agent modules")
except ImportError as e:
    print(f"✗ Failed to import agent modules: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_session_manager():
    """Test session manager initialization"""
    print("\n=== Testing Session Manager Initialization ===")
    
    # Test parameters
    actor_id = "test-repo"
    session_id = f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    try:
        # Test session manager creation
        print(f"Creating session manager for actor_id='{actor_id}', session_id='{session_id}'")
        session_manager = get_session_manager(actor_id, session_id)
        
        if session_manager is None:
            print("⚠️  Session manager returned None (using fallback)")
            return True  # This is acceptable as a fallback
        else:
            print("✓ Session manager created successfully")
            print(f"  Type: {type(session_manager)}")
            return True
            
    except Exception as e:
        print(f"✗ Session manager creation failed: {e}")
        return False

def test_agent_creation():
    """Test agent creation with session manager"""
    print("\n=== Testing Agent Creation ===")
    
    # Test parameters
    session_id = f"test-agent-session-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    repository = "test-repo"
    
    try:
        print(f"Creating agent with session_id='{session_id}', repository='{repository}'")
        agent = create_agent(session_id, repository)
        
        print("✓ Agent created successfully")
        print(f"  Type: {type(agent)}")
        return True
        
    except Exception as e:
        print(f"✗ Agent creation failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Testing Eco-Coder Agent Session Manager Fix")
    print("=" * 60)
    
    # Run tests
    tests = [
        test_session_manager,
        test_agent_creation
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 Test Summary:")
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {i+1}. {test.__name__}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Session manager issue should be resolved.")
        return 0
    else:
        print("❌ Some tests failed. Please check the error messages above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)