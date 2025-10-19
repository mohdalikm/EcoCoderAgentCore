#!/usr/bin/env python3
"""
Development runner for EcoCoder Agent
Loads environment variables and runs the agent in development mode using Strands SDK and BedrockAgentCore
"""

import os
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = project_root / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment from {env_file}")
    else:
        print(f"⚠️  No .env file found at {env_file}")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment")

# Set development environment
os.environ['ENVIRONMENT'] = 'development'

print("🌱 Starting EcoCoder Agent in Development Mode")
print(f"📁 Project root: {project_root}")
print(f"🌍 AWS region: {os.getenv('AWS_REGION', 'ap-southeast-1')}")

# Check Python version
print(f"🐍 Python: {sys.version}")
if sys.version_info >= (3, 11):
    print("✅ Python 3.11+ detected - Strands SDK supported")
else:
    print("❌ Python < 3.11 required for Strands SDK")
    print("Please upgrade to Python 3.11 or higher")
    sys.exit(1)

def check_agent_server(host="localhost", port=8080, timeout=5):
    """Check if the agent server is running"""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def wait_for_agent_server(host="localhost", port=8080, max_attempts=30):
    """Wait for the agent server to be available"""
    import time
    
    print(f"🔍 Checking if agent server is running at http://{host}:{port}...")
    
    for attempt in range(max_attempts):
        if check_agent_server(host, port):
            print(f"✅ Agent server is available at http://{host}:{port}")
            return True
        
        if attempt == 0:
            print(f"⏳ Waiting for agent server to start...")
        elif attempt % 5 == 0:
            print(f"⏳ Still waiting... (attempt {attempt + 1}/{max_attempts})")
        
        time.sleep(1)
    
    return False


def call_agent_api(payload, host="localhost", port=8080):
    """Call the agent API via HTTP request"""
    import requests
    import json
    
    url = f"http://{host}:{port}/invocations"
    headers = {"Content-Type": "application/json"}
    
    try:
        print(f"🚀 Sending request to {url}")
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "message": f"HTTP {response.status_code}: {response.text}",
                "response_headers": dict(response.headers)
            }
            
    except requests.exceptions.Timeout:
        return {
            "status": "error", 
            "message": "Request timeout - agent may be processing for too long"
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": f"Connection error - is the agent running at {url}?"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }


def main():
    """Main function for local testing and development with proper GitHub webhook payload"""
    import json
    import time
    
    print("🌱 Eco-Coder Agent Development Client")
    print("Built with Strands SDK and AWS Bedrock AgentCore Runtime")
    print("For sustainable software development")
    
    # Check if agent server is running
    if not wait_for_agent_server():
        print("\n❌ Agent server is not running!")
        print("💡 Please start the agent server first by running:")
        print("   python app/agent.py")
        print("   (This should start the server on http://localhost:8080)")
        return
    
    # Example test payload (GitHub PR webhook format) - more realistic structure
    test_payload = {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 1234567890,
            "number": 42,
            "title": "feat: Add new data processing algorithm with performance optimizations",
            "body": "This PR introduces a new algorithm that improves data processing efficiency by 40% and reduces memory usage.",
            "state": "open",
            "created_at": "2025-10-20T03:00:00Z",
            "updated_at": "2025-10-20T03:00:00Z",
            "head": {
                "label": "eco-tech:feature/optimize-performance",
                "ref": "feature/optimize-performance", 
                "sha": "a1b2c3d4e5f67890123456789abcdef012345678",
                "repo": {
                    "id": 987654321,
                    "name": "sample-app",
                    "full_name": "eco-tech/sample-app"
                }
            },
            "base": {
                "label": "eco-tech:main",
                "ref": "main",
                "sha": "def0123456789abcdef0123456789abcdef012345",
                "repo": {
                    "id": 987654321,
                    "name": "sample-app", 
                    "full_name": "eco-tech/sample-app"
                }
            },
            "user": {
                "id": 123456,
                "login": "developer123",
                "type": "User"
            },
            "assignees": [],
            "requested_reviewers": [],
            "labels": [
                {"name": "enhancement"},
                {"name": "performance"}
            ]
        },
        "repository": {
            "id": 987654321,
            "name": "sample-app",
            "full_name": "eco-tech/sample-app",
            "private": False,
            "clone_url": "https://github.com/eco-tech/sample-app.git",
            "ssh_url": "git@github.com:eco-tech/sample-app.git",
            "html_url": "https://github.com/eco-tech/sample-app",
            "description": "A sample application for sustainable software development",
            "language": "Python",
            "default_branch": "main",
            "owner": {
                "id": 123456,
                "login": "eco-tech",
                "type": "Organization"
            }
        },
        "sender": {
            "id": 123456,
            "login": "developer123",
            "type": "User"
        }
    }
    
    print("\n🔍 Testing with realistic GitHub PR webhook payload...")
    print(f"📝 PR #{test_payload['pull_request']['number']}: {test_payload['pull_request']['title']}")
    print(f"🔗 Repository: {test_payload['repository']['full_name']}")
    print(f"🌿 Branch: {test_payload['pull_request']['head']['ref']} → {test_payload['pull_request']['base']['ref']}")
    print(f"💾 Commit SHA: {test_payload['pull_request']['head']['sha'][:8]}...")
    
    # Now test with GitHub webhook payload
    print("\n🚀 Testing with GitHub webhook payload...")
    start_time = time.time()
    
    try:
        result = call_agent_api(test_payload)
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ Analysis Result:")
        print(f"📊 Status: {result.get('status', 'unknown')}")
        print(f"⏱️  Total Time: {elapsed_time:.2f}s")
        print(f"🔑 Session ID: {result.get('session_id', 'unknown')}")
        
        if result.get('status') == 'success':
            print(f"🤖 Agent Response: {result.get('agent_response', 'No response')}")
            if result.get('execution_time_seconds'):
                print(f"⚡ Agent Processing Time: {result.get('execution_time_seconds')}s")
        else:
            print(f"❌ Error: {result.get('message', 'Unknown error')}")
            
        print(f"\n📋 Full Result JSON:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


# Import and run the agent
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error starting agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)