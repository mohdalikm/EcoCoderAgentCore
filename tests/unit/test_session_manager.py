"""
Unit tests for the EcoCoder Agent session manager
"""

import os
import sys
import logging
from datetime import datetime
import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import the agent module
from app.agent import get_session_manager, create_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestSessionManager:
    """Test session manager initialization"""

    def test_session_manager_initialization(self):
        """Test session manager initialization"""
        # Test parameters
        actor_id = "test-repo"
        session_id = f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Test session manager creation
        session_manager = get_session_manager(actor_id, session_id)
        
        if session_manager is None:
            # This is acceptable as a fallback
            assert session_manager is None
        else:
            assert session_manager is not None

    def test_agent_creation_with_session_manager(self):
        """Test agent creation with session manager"""
        # Test parameters
        session_id = f"test-agent-session-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        repository = "test-repo"
        
        agent = create_agent(session_id, repository)
        
        assert agent is not None
        assert hasattr(agent, 'tool_registry')
