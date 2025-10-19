#!/usr/bin/env python3
"""
Development runner for EcoCoder Agent
Loads environment variables and runs the agent in development mode
"""

import os
import sys
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

# Set development mode - use real Strands SDK but still mock AWS services
os.environ['MOCK_MODE'] = 'false'  # Use real Strands SDK
os.environ['ENVIRONMENT'] = 'development'

print("🌱 Starting EcoCoder Agent in Development Mode")
print(f"📁 Project root: {project_root}")
print(f"🔧 Mock mode: {os.getenv('MOCK_MODE')}")
print(f"🌍 AWS region: {os.getenv('AWS_REGION')}")

# Check Python version
print(f"🐍 Python: {sys.version}")
if sys.version_info >= (3, 11):
    print("✅ Python 3.11+ detected - Strands SDK supported")
else:
    print("⚠️  Python < 3.11 detected - falling back to mock mode")
    os.environ['MOCK_MODE'] = 'true'

# Import and run the agent
if __name__ == "__main__":
    try:
        from app.agent import main
        main()
    except Exception as e:
        print(f"❌ Error starting agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)