"""Tests for MCP helper functions.

These tests verify the MCP integration functionality including:
- MCPSessionManager initialization and lifecycle
- Tool discovery and wrapper creation
- Context integration
- Global session management
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import the module to test
try:
    from mellea.helpers.mcp_helpers import (
        MCPSessionManager,
        get_current_mcp_session,
        mcp_session_manager,
    )
    from mellea.core import CBlock
    
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    pytest.skip("MCP package not installed", allow_module_level=True)


class TestMCPSessionManager:
    """Test the MCPSessionManager class."""
    
    def test_init(self):
        """Test MCPSessionManager initialization."""
        manager = MCPSessionManager(
            server_url="https://example.com/mcp",
            api_key="test_key"
        )
        
        assert manager.server_url == "https://example.com/mcp"
        assert manager.api_key == "test_key"
        assert manager.session is None
        assert manager.tools == {}
        assert manager.async_tools == {}
        assert manager.mcp_tools_list == []
    
    def test_get_tools_for_mellea_empty(self):
        """Test get_tools_for_mellea with no tools."""
        manager = MCPSessionManager("https://example.com", "key")
        tools = manager.get_tools_for_mellea()
        
        assert tools == []
        assert isinstance(tools, list)
    
    def test_get_tools_for_mellea_with_tools(self):
        """Test get_tools_for_mellea with tools."""
        manager = MCPSessionManager("https://example.com", "key")
        
        # Add mock tools
        def mock_tool1():
            pass
        def mock_tool2():
            pass
        
        manager.tools = {"tool1": mock_tool1, "tool2": mock_tool2}
        tools = manager.get_tools_for_mellea()
        
        assert len(tools) == 2
        assert mock_tool1 in tools
        assert mock_tool2 in tools
    
    @pytest.mark.asyncio
    async def test_call_tool_directly_no_session(self):
        """Test call_tool_directly raises error when session is None."""
        manager = MCPSessionManager("https://example.com", "key")
        
        with pytest.raises(RuntimeError, match="Session not connected"):
            await manager.call_tool_directly("test_tool", {})
    
    @pytest.mark.asyncio
    async def test_call_tool_directly_with_session(self):
        """Test call_tool_directly with active session."""
        manager = MCPSessionManager("https://example.com", "key")
        
        # Mock session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.content = [Mock(text="test result")]
        mock_session.call_tool.return_value = mock_result
        
        manager.session = mock_session
        
        result = await manager.call_tool_directly("test_tool", {"arg": "value"})
        
        mock_session.call_tool.assert_called_once_with(
            "test_tool", 
            arguments={"arg": "value"}
        )
        assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_execute_tool_call_not_found(self):
        """Test execute_tool_call raises error for unknown tool."""
        manager = MCPSessionManager("https://example.com", "key")
        
        with pytest.raises(ValueError, match="Tool unknown_tool not found"):
            await manager.execute_tool_call("unknown_tool")
    
    @pytest.mark.asyncio
    async def test_execute_tool_call_success(self):
        """Test execute_tool_call with existing tool."""
        manager = MCPSessionManager("https://example.com", "key")
        
        # Add mock async tool
        async def mock_async_tool(**kwargs):
            return f"Result: {kwargs}"
        
        manager.async_tools["test_tool"] = mock_async_tool
        
        result = await manager.execute_tool_call("test_tool", arg1="value1")
        
        assert "Result:" in result
        assert "arg1" in result
    
    def test_to_cblock(self):
        """Test to_cblock creates proper CBlock."""
        manager = MCPSessionManager("https://example.com/mcp", "key")
        
        # Add some mock tools
        manager.tools = {"tool1": lambda: None, "tool2": lambda: None}
        
        cblock = manager.to_cblock()
        
        assert isinstance(cblock, CBlock)
        assert "MCP Session" in str(cblock)
        assert "https://example.com/mcp" in str(cblock)
        assert "2 tools available" in str(cblock)


class TestMCPSessionManagerContextManager:
    """Test the mcp_session_manager async context manager."""
    
    @pytest.mark.asyncio
    async def test_mcp_session_manager_invalid_transport(self):
        """Test mcp_session_manager raises error for invalid transport."""
        with pytest.raises(ValueError, match="Unknown transport"):
            async with mcp_session_manager(
                server_url="https://example.com",
                api_key="key",
                transport="invalid"  # type: ignore
            ):
                pass
    
    @pytest.mark.asyncio
    @patch('mellea.helpers.mcp_helpers.streamablehttp_client')
    @patch('mellea.helpers.mcp_helpers.ClientSession')
    async def test_mcp_session_manager_streamable_http(
        self, 
        mock_client_session,
        mock_streamable_client
    ):
        """Test mcp_session_manager with streamable-http transport."""
        # Setup mocks
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_get_session_id = Mock()
        
        mock_streamable_client.return_value.__aenter__.return_value = (
            mock_read, mock_write, mock_get_session_id
        )
        
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock()
        mock_session.list_tools.return_value = Mock(tools=[])
        
        mock_client_session.return_value.__aenter__.return_value = mock_session
        
        # Test the context manager
        async with mcp_session_manager(
            server_url="https://example.com/mcp",
            api_key="test_key",
            transport="streamable-http"
        ) as manager:
            assert isinstance(manager, MCPSessionManager)
            assert manager.server_url == "https://example.com/mcp"
            assert manager.api_key == "test_key"
            assert manager.session == mock_session
        
        # Verify session was initialized
        mock_session.initialize.assert_called_once()
        mock_session.list_tools.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('mellea.helpers.mcp_helpers.sse_client')
    @patch('mellea.helpers.mcp_helpers.ClientSession')
    async def test_mcp_session_manager_sse(
        self,
        mock_client_session,
        mock_sse_client
    ):
        """Test mcp_session_manager with SSE transport."""
        # Setup mocks
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        
        mock_sse_client.return_value.__aenter__.return_value = (
            mock_read, mock_write
        )
        
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock()
        mock_session.list_tools.return_value = Mock(tools=[])
        
        mock_client_session.return_value.__aenter__.return_value = mock_session
        
        # Test the context manager
        async with mcp_session_manager(
            server_url="http://localhost:3000/sse",
            transport="sse",
            headers={"Custom": "Header"}
        ) as manager:
            assert isinstance(manager, MCPSessionManager)
            assert manager.server_url == "http://localhost:3000/sse"
        
        # Verify SSE client was called with correct headers
        mock_sse_client.assert_called_once()
        call_kwargs = mock_sse_client.call_args[1]
        assert call_kwargs["url"] == "http://localhost:3000/sse"
        assert "Custom" in call_kwargs["headers"]
    
    @pytest.mark.asyncio
    @patch('mellea.helpers.mcp_helpers.streamablehttp_client')
    @patch('mellea.helpers.mcp_helpers.ClientSession')
    async def test_mcp_session_manager_with_tools(
        self,
        mock_client_session,
        mock_streamable_client
    ):
        """Test mcp_session_manager creates tool wrappers."""
        # Setup mocks
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_get_session_id = Mock()
        
        mock_streamable_client.return_value.__aenter__.return_value = (
            mock_read, mock_write, mock_get_session_id
        )
        
        # Create mock tools
        mock_tool1 = Mock()
        mock_tool1.name = "get_user"
        mock_tool1.description = "Get user information"
        
        mock_tool2 = Mock()
        mock_tool2.name = "search"
        mock_tool2.description = "Search for content"
        
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock()
        mock_session.list_tools.return_value = Mock(tools=[mock_tool1, mock_tool2])
        mock_session.call_tool = AsyncMock()
        
        mock_client_session.return_value.__aenter__.return_value = mock_session
        
        # Test the context manager
        async with mcp_session_manager(
            server_url="https://example.com/mcp",
            api_key="test_key",
            transport="streamable-http"
        ) as manager:
            # Verify tools were discovered
            assert len(manager.tools) == 2
            assert "get_user" in manager.tools
            assert "search" in manager.tools
            
            # Verify async tools were created
            assert len(manager.async_tools) == 2
            assert "get_user" in manager.async_tools
            assert "search" in manager.async_tools
            
            # Verify tool wrappers have correct names and docs
            assert manager.tools["get_user"].__name__ == "get_user"
            assert manager.tools["get_user"].__doc__ == "Get user information"


class TestGetCurrentMCPSession:
    """Test the get_current_mcp_session function."""
    
    def test_get_current_mcp_session_none(self):
        """Test get_current_mcp_session returns None when no session active."""
        # Ensure no session is active
        import mellea.helpers.mcp_helpers as mcp_helpers
        mcp_helpers._current_mcp_manager = None
        
        result = get_current_mcp_session()
        assert result is None
    
    @pytest.mark.asyncio
    @patch('mellea.helpers.mcp_helpers.streamablehttp_client')
    @patch('mellea.helpers.mcp_helpers.ClientSession')
    @patch('mellea.helpers.mcp_helpers._initialize_session')
    async def test_get_current_mcp_session_active(
        self,
        mock_initialize,
        mock_client_session,
        mock_streamable_client
    ):
        """Test get_current_mcp_session returns active session."""
        # Setup mocks
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_get_session_id = Mock()
        
        mock_streamable_client.return_value.__aenter__.return_value = (
            mock_read, mock_write, mock_get_session_id
        )
        
        mock_session = AsyncMock()
        mock_client_session.return_value.__aenter__.return_value = mock_session
        
        # Mock _initialize_session to set the global variable
        async def mock_init(manager, session, transport):
            import mellea.helpers.mcp_helpers as mcp_helpers
            manager.session = session
            mcp_helpers._current_mcp_manager = manager
        
        mock_initialize.side_effect = mock_init
        
        # Test within context manager
        async with mcp_session_manager(
            server_url="https://example.com/mcp",
            api_key="test_key",
            transport="streamable-http"
        ) as manager:
            current = get_current_mcp_session()
            assert current is manager
            assert current.server_url == "https://example.com/mcp"
        
        # After context manager exits, should be None again
        current = get_current_mcp_session()
        assert current is None


class TestMCPIntegration:
    """Integration tests for MCP functionality."""
    
    @pytest.mark.asyncio
    @patch('mellea.helpers.mcp_helpers.streamablehttp_client')
    @patch('mellea.helpers.mcp_helpers.ClientSession')
    @patch('mellea.helpers.mcp_helpers._initialize_session')
    async def test_full_workflow(
        self,
        mock_initialize,
        mock_client_session,
        mock_streamable_client
    ):
        """Test a complete MCP workflow."""
        # Setup mocks
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_get_session_id = Mock()
        
        mock_streamable_client.return_value.__aenter__.return_value = (
            mock_read, mock_write, mock_get_session_id
        )
        
        # Create mock tool
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        
        # Create mock result
        mock_result = Mock()
        mock_content = Mock()
        mock_content.text = "Tool execution result"
        mock_result.content = [mock_content]
        
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        
        mock_client_session.return_value.__aenter__.return_value = mock_session
        
        # Mock _initialize_session to set up tools and global variable
        async def mock_init(manager, session, transport):
            import mellea.helpers.mcp_helpers as mcp_helpers
            manager.session = session
            manager.mcp_tools_list = [mock_tool]
            # Create a simple sync wrapper
            def sync_wrapper(**kwargs):
                return f"[MCP Tool test_tool called with {kwargs}]"
            sync_wrapper.__name__ = "test_tool"
            sync_wrapper.__doc__ = "A test tool"
            manager.tools = {"test_tool": sync_wrapper}
            mcp_helpers._current_mcp_manager = manager
        
        mock_initialize.side_effect = mock_init
        
        # Execute workflow
        async with mcp_session_manager(
            server_url="https://example.com/mcp",
            api_key="test_key",
            transport="streamable-http"
        ) as manager:
            # 1. Verify session is active
            assert get_current_mcp_session() is manager
            
            # 2. Get tools for Mellea
            tools = manager.get_tools_for_mellea()
            assert len(tools) == 1
            
            # 3. Create CBlock for context
            cblock = manager.to_cblock()
            assert "test_tool" not in str(cblock)  # Tool names not in summary
            assert "1 tools available" in str(cblock)
            
            # 4. Call tool directly
            result = await manager.call_tool_directly("test_tool", {"arg": "value"})
            assert result == mock_result
            
            # 5. Verify call was made correctly
            mock_session.call_tool.assert_called_once_with(
                "test_tool",
                arguments={"arg": "value"}
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
