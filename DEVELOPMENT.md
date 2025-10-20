# EcoCoder Agent - Local Development Setup

## Quick Start for Local Development

### 1. Prerequisites
- Python 3.9+ (Note: Strands SDK requires Python 3.10+ for production, but development mode works with 3.9+)
- Git

### 2. Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/your-org/EcoCoderAgentCore.git
cd EcoCoderAgentCore

# Set up development environment (creates venv, installs dependencies)
./dev.sh install
```

### 3. Run in Development Mode

The agent includes mock implementations for all external services (AWS CodeGuru, GitHub API) to enable local development without AWS credentials.

**Option 1: Using the development script (recommended)**
```bash
./dev.sh start
```

**Option 2: Direct Python execution**
```bash
# Load environment and run
source .venv/bin/activate
MOCK_MODE=true python run_dev.py
```

**Option 3: Module execution (as shown in README)**
```bash
source .venv/bin/activate
MOCK_MODE=true python -m app.agent
```

### 4. Development Commands

The `dev.sh` script provides several useful commands:

```bash
./dev.sh install     # Set up development environment
./dev.sh start       # Start agent in development mode
./dev.sh test        # Run tests (when available)
./dev.sh format      # Format code with Black and isort
./dev.sh lint        # Lint code with flake8
./dev.sh typecheck   # Run type checking with mypy
./dev.sh all         # Run format, lint, typecheck, and test
```

### 5. Environment Configuration

The `.env` file contains development settings:

```bash
# Development Mode - Uses mock implementations
MOCK_MODE=true

# AWS Configuration (not needed for development)
AWS_REGION=ap-southeast-1

# Logging
LOG_LEVEL=INFO

# Application Environment
ENVIRONMENT=development
```

### 6. Mock Mode Features

When `MOCK_MODE=true`, the agent provides:

- **Mock CodeGuru Reviewer**: Returns sample code quality recommendations
- **Mock CodeGuru Profiler**: Returns sample performance analysis
- **Mock CodeCarbon**: Calculates sample carbon footprint estimates  
- **Mock GitHub API**: Simulates posting comments (logs output instead)
- **No AWS Credentials Required**: All AWS services are mocked

### 7. Sample Output

When you run the agent, you'll see output like:

```
🌱 Starting EcoCoder Agent in Development Mode
📁 Project root: /path/to/EcoCoderAgentCore
🔧 Mock mode: true
🌍 AWS region: ap-southeast-1

🌱 Eco-Coder Agent Starting...
Built with Strands SDK and AWS Bedrock AgentCore Runtime
For sustainable software development

🔍 Testing with sample PR webhook...
INFO - Starting analysis for PR #42 in eco-tech/sample-app
INFO - Agent analysis completed in 0.00 seconds: Analysis completed successfully (mock mode)

✅ Result: {
  "status": "success",
  "message": "Eco-Coder analysis completed successfully",
  "session_id": "pr-eco-tech/sample-app-42-20251019185617",
  "agent_response": "Analysis completed successfully (mock mode)",
  ...
}
```

### 8. Troubleshooting Development Issues

**Import Errors**: Make sure you're using the virtual environment:
```bash
source .venv-py311/bin/activate
```

**Missing Dependencies**: Reinstall dependencies:
```bash
./dev.sh install
```

**Strands SDK Issues**: The development mode includes mock implementations, so the actual Strands SDK is not required for local development.

**Python Version**: If you have Python 3.10+, you can install the actual Strands SDK:
```bash
pip install strands-agents strands-agents-tools
export MOCK_MODE=false  # Use real Strands SDK
```

### 9. Next Steps

- **Production Deployment**: See main README for AWS deployment instructions
- **Real AWS Integration**: Set up AWS credentials and set `MOCK_MODE=false`
- **Custom Tools**: Add new analysis tools in `app/tools/`
- **Testing**: Add unit tests in `tests/` directory

### 10. Development Workflow

1. Make code changes in `app/`
2. Format and lint: `./dev.sh format && ./dev.sh lint`
3. Test locally: `./dev.sh start`
4. Run type checking: `./dev.sh typecheck`
5. Commit and push changes