"""
Integration tests for the EcoCoder Agent
Tests the full workflow from webhook to response
"""

import json
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.agent import invoke


class TestFullWorkflow:
    """Test complete end-to-end workflow"""
    
    def test_full_webhook_processing(self):
        """Test processing a complete GitHub webhook"""
        # Use the same test payload as in the main function
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "feat: Add new data processing algorithm",
                "head": {
                    "ref": "feature/optimize-performance", 
                    "sha": "a1b2c3d4e5f6"
                },
                "base": {"ref": "main"}
            },
            "repository": {
                "full_name": "eco-tech/sample-app",
                "clone_url": "https://github.com/eco-tech/sample-app.git",
                "owner": {"id": "123456"}
            }
        }
        
        # Set mock mode for testing
        os.environ['ENABLE_AGENTCORE_MEMORY'] = 'false'
        
        result = invoke(payload)
        
        # Verify response structure
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert "session_id" in result
        assert "agent_response" in result
        assert "pr_info" in result
        assert "execution_time_seconds" in result
        
        # Verify PR info extraction
        pr_info = result["pr_info"]
        assert pr_info["action"] == "opened"
        assert pr_info["pr_number"] == 42
        assert pr_info["repository_name"] == "eco-tech/sample-app"
        assert pr_info["commit_sha"] == "a1b2c3d4e5f6"
        assert pr_info["branch_name"] == "feature/optimize-performance"
        
        # Verify session ID format
        session_id = result["session_id"]
        assert session_id.startswith("pr-eco-tech/sample-app-42-")
        
        # Verify execution time is reasonable
        exec_time = result["execution_time_seconds"]
        assert isinstance(exec_time, (int, float))
        assert exec_time >= 0
        assert exec_time < 120  # Should complete within 120 seconds
    
    def test_different_pr_actions(self):
        """Test different GitHub PR actions"""
        actions = ["opened", "synchronize", "reopened"]
        
        for action in actions:
            payload = {
                "action": action,
                "pull_request": {
                    "number": 123,
                    "title": f"Test PR for {action}",
                    "head": {
                        "ref": "test-branch", 
                        "sha": f"sha-{action}"
                    },
                    "base": {"ref": "main"}
                },
                "repository": {
                    "full_name": "test/repo",
                    "clone_url": "https://github.com/test/repo.git",
                    "owner": {"id": "456"}
                }
            }
            
            os.environ['ENABLE_AGENTCORE_MEMORY'] = 'false'
            result = invoke(payload)
            
            assert result["status"] == "success"
            assert result["pr_info"]["action"] == action
    
    def test_error_handling(self):
        """Test error handling for various failure scenarios"""
        
        # Test completely invalid payload
        result = invoke({"invalid": "payload"})
        assert result["status"] == "error"
        assert "execution_time_seconds" in result
        
        # Test missing repository info
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "head": {"ref": "branch", "sha": "sha123"},
                "base": {"ref": "main"}
            }
            # Missing repository
        }
        result = invoke(payload)
        assert result["status"] == "error"
        
        # Test missing PR number
        payload = {
            "action": "opened",
            "pull_request": {
                # Missing number
                "head": {"ref": "branch", "sha": "sha123"},
                "base": {"ref": "main"}
            },
            "repository": {
                "full_name": "test/repo",
                "owner": {"id": "123"}
            }
        }
        result = invoke(payload)
        assert result["status"] == "error"


class TestPerformance:
    """Test performance characteristics"""
    
    def test_response_time(self):
        """Test that responses are generated within reasonable time"""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 999,
                "title": "Performance test PR",
                "head": {"ref": "perf-test", "sha": "perfsha123"},
                "base": {"ref": "main"}
            },
            "repository": {
                "full_name": "perf/test",
                "clone_url": "https://github.com/perf/test.git",
                "owner": {"id": "789"}
            }
        }
        
        os.environ['ENABLE_AGENTCORE_MEMORY'] = 'false'
        
        import time
        start_time = time.time()
        result = invoke(payload)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        assert result["status"] == "success"
        assert execution_time < 180.0  # Should complete within 180 seconds in mock mode
        
        # Verify the reported execution time is close to measured time
        reported_time = result["execution_time_seconds"]
        assert abs(execution_time - reported_time) < 1.0  # Within 1 second tolerance





class TestComprehensiveScenarios:
    """Test comprehensive scenarios"""

    @pytest.mark.parametrize("scenario, payload, expected_status", [
        (
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
            },
            "success"
        ),
        (
            "Invalid Payload",
            {
                "invalid": "data",
                "missing": "required_fields"
            },
            "error"
        ),
        (
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
            "error"
        )
    ])
    def test_scenario(self, scenario, payload, expected_status):
        """Test a specific scenario"""
        os.environ['ENABLE_AGENTCORE_MEMORY'] = 'false'
        result = invoke(payload)
        assert result['status'] == expected_status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])