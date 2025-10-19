#!/usr/bin/env python3
"""
Root level agent module for Docker container execution.
This imports and runs the main agent from the app module.
"""

# Import the main agent functionality
from app.agent import app

if __name__ == "__main__":
    # Start the AgentCore app
    app.run()