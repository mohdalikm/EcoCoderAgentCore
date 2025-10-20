"""
Unit tests for the EcoCoder Agent main functionality
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.agent import (
    parse_github_webhook,
    create_agent,
    invoke,
    load_system_prompt
)


class TestGitHubWebhookParsing:
    """Test GitHub webhook payload parsing"""
    
    def test_parse_valid_github_webhook(self):
        """Test parsing a valid GitHub webhook payload"""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "feat: Add new feature",
                "head": {
                    "ref": "feature/new-feature",
                    "sha": "abc123def456"
                },
                "base": {
                    "ref": "main"
                }
            },
            "repository": {
                "full_name": "owner/repo",
                "clone_url": "https://github.com/owner/repo.git",
                "owner": {
                    "id": "12345"
                }
            }
        }
        
        result = parse_github_webhook(payload)
        
        assert result["action"] == "opened"
        assert result["pr_number"] == 42
        assert result["repository_name"] == "owner/repo"
        assert result["commit_sha"] == "abc123def456"
        assert result["branch_name"] == "feature/new-feature"
        assert result["base_branch"] == "main"
        assert result["title"] == "feat: Add new feature"
    
    def test_parse_invalid_github_webhook(self):
        """Test parsing an invalid GitHub webhook payload"""
        payload = {"invalid": "data"}
        
        # The function doesn't raise ValueError for invalid data, it returns None values
        result = parse_github_webhook(payload)
        assert result["action"] is None
        assert result["pr_number"] is None
        assert result["repository_name"] is None
    
    def test_parse_missing_fields(self):
        """Test parsing webhook with missing required fields"""
        payload = {
            "action": "opened",
            "pull_request": {},
            "repository": {}
        }
        
        result = parse_github_webhook(payload)
        assert result["pr_number"] is None
        assert result["repository_name"] is None


class TestAgentCreation:
    """Test agent creation and configuration"""
    
    @patch.dict(os.environ, {'ENVIRONMENT': 'development'})
    def test_create_agent_development_mode(self):
        """Test creating agent in development mode"""
        session_id = "test-session-123"
        repository = "test-owner/test-repo"
        
        agent = create_agent(session_id, repository)
        
        assert agent is not None
        assert hasattr(agent, 'tool_registry')
        assert hasattr(agent, 'tool_names')
        assert len(agent.tool_names) > 0
        
        # Check that required tools are registered
        expected_tools = [
            'analyze_code',
            'profile_code_performance_tool',
            'calculate_carbon_footprint_tool',
            'post_github_comment_tool'
        ]
        
        for tool_name in expected_tools:
            assert tool_name in agent.tool_names

    def test_load_system_prompt(self):
        """Test loading system prompt"""
        prompt = load_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "Eco-Coder" in prompt


class TestMainInvoke:
    """Test the main invoke function"""
    
    @patch.dict(os.environ, {'ENVIRONMENT': 'development'})
    def test_invoke_success(self):
        """Test successful invocation with valid payload"""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "feat: Add new feature",
                "head": {
                    "ref": "feature/new-feature",
                    "sha": "abc123def456"
                },
                "base": {
                    "ref": "main"
                }
            },
            "repository": {
                "full_name": "owner/repo",
                "clone_url": "https://github.com/owner/repo.git",
                "owner": {
                    "id": "12345"
                }
            }
        }
        
        result = invoke(payload)
        
        assert result["status"] == "success"
        assert "session_id" in result
        assert "agent_response" in result
        assert "execution_time_seconds" in result
        assert "pr_info" in result
    
    @patch.dict(os.environ, {'ENVIRONMENT': 'development'})
    def test_invoke_invalid_payload(self):
        """Test invocation with invalid payload"""
        payload = {"invalid": "data"}
        
        result = invoke(payload)
        
        assert result["status"] == "error"
        assert "message" in result
        assert "execution_time_seconds" in result
    
    @patch.dict(os.environ, {'ENVIRONMENT': 'development'})  
    def test_invoke_missing_pr_info(self):
        """Test invocation with missing PR information"""
        payload = {
            "action": "opened",
            "pull_request": {
                # Missing number, head, etc.
            },
            "repository": {
                "full_name": "owner/repo"
            }
        }
        
        result = invoke(payload)
        
        assert result["status"] == "error"
        assert "Missing required PR information" in result["message"]


class TestToolIntegration:
    """Test tool integration functionality"""
    
    @patch.dict(os.environ, {'ENVIRONMENT': 'development'})
    def test_tools_are_callable(self):
        """Test that all tools can be called without errors"""
        session_id = "test-session-123"
        repository = "test-owner/test-repo"
        
        agent = create_agent(session_id, repository)
        
        # Get tools from the registry
        tools = agent.tool_registry.registry
        
        # Test analyze_code tool
        analyze_code = tools['analyze_code']
        result = analyze_code(
            repository_arn="arn:aws:codecommit:us-east-1:123456:test-repo",
            branch_name="main",
            commit_sha="abc123"
        )
        assert isinstance(result, dict)
        
        # Test profile_code_performance_tool
        profile_tool = tools['profile_code_performance_tool']
        result = profile_tool(
            profiling_group_name="test-group",
            start_time="2023-01-01T00:00:00Z",
            end_time="2023-01-01T01:00:00Z"
        )
        assert isinstance(result, dict)
        
        # Test calculate_carbon_footprint_tool
        carbon_tool = tools['calculate_carbon_footprint_tool']
        result = carbon_tool(
            cpu_time_seconds=10.5,
            ram_usage_mb=512.0,
            aws_region="us-east-1",
            execution_count=100
        )
        assert isinstance(result, dict)
        
        # Test post_github_comment_tool
        github_tool = tools['post_github_comment_tool']
        result = github_tool(
            repository_full_name="owner/repo",
            pull_request_number=42,
            report_markdown="# Test Report\nThis is a test."
        )
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])