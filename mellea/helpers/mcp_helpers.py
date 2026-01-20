"""MCP (Model Context Protocol) helper functions for integrating MCP servers with Mellea.

This module provides utilities for connecting to MCP servers and using their tools
within Mellea sessions. It supports both streamable-http and SSE transports.

Example:
    ```python
    import asyncio
    from mellea.helpers import mcp_session_manager
    import mellea

    async def main():
        async with mcp_session_manager(
            server_url="https://api.githubcopilot.com/mcp/",
            api_key="your_api_key",
            transport="streamable-http"
        ) as mcp_manager:
            m = mellea.start_session()
            m.ctx = m.ctx.add(mcp_manager.to_cblock())

            output = m.instruct(
                "Use available tools to get information",
                model_options={
                    ModelOption.TOOLS: mcp_manager.get_tools_for_mellea(),
                },
                tool_calls=True,
            )

            # Execute tool calls
            if output.tool_calls:
                for tool_name, tool_call in output.tool_calls.items():
                    result = await mcp_manager.call_tool_directly(
                        tool_name, dict(tool_call.args)
                    )
                    print(result)

    asyncio.run(main())
    ```
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Literal

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from ..core import CBlock

# Global variable to store the current MCP session manager
_current_mcp_manager = None


class MCPSessionManager:
    """Manager for MCP client sessions that can be stored and accessed globally.

    This class manages the lifecycle of an MCP client session, including:
    - Connection to MCP servers
    - Tool discovery and wrapper creation
    - Synchronous and asynchronous tool execution
    - Integration with Mellea's context system

    Attributes:
        server_url: URL of the MCP server
        api_key: API key for authentication
        session: Active MCP ClientSession (None if not connected)
        tools: Dictionary of synchronous tool wrappers for Mellea
        async_tools: Dictionary of asynchronous tool executors
        mcp_tools_list: List of MCP tool definitions from the server
    """

    def __init__(self, server_url: str, api_key: str):
        """Initialize the MCP session manager.

        Args:
            server_url: URL of the MCP server to connect to
            api_key: API key for authentication (can be empty string if not required)
        """
        self.server_url = server_url
        self.api_key = api_key
        self.session = None
        self.tools = {}
        self.async_tools = {}
        self.mcp_tools_list = []

    def get_tools_for_mellea(self):
        """Get list of tool functions to pass to Mellea's ModelOption.TOOLS.

        Returns:
            List of synchronous tool wrapper functions that can be used with Mellea
        """
        return list(self.tools.values())

    async def call_tool_directly(self, tool_name: str, arguments: dict):
        """Call an MCP tool directly and return the result.

        This method bypasses the wrapper functions and calls the MCP tool directly
        through the session. Useful for executing tool calls after Mellea generates them.

        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            The result from the MCP tool call

        Raises:
            RuntimeError: If the session is not connected
        """
        if self.session:
            return await self.session.call_tool(tool_name, arguments=arguments)
        raise RuntimeError("Session not connected")

    async def execute_tool_call(self, tool_name: str, **kwargs):
        """Execute a tool call using the async wrapper and return the result.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Keyword arguments to pass to the tool

        Returns:
            String result from the tool execution

        Raises:
            ValueError: If the tool is not found
        """
        if tool_name in self.async_tools:
            return await self.async_tools[tool_name](**kwargs)
        raise ValueError(f"Tool {tool_name} not found")

    def to_cblock(self) -> CBlock:
        """Convert session info to a CBlock for adding to Mellea context.

        This allows the Mellea session to be aware of the available MCP tools
        in its context.

        Returns:
            CBlock containing information about the MCP session
        """
        info = f"MCP Session: {self.server_url} ({len(self.tools)} tools available)"
        return CBlock(info)


@asynccontextmanager
async def mcp_session_manager(
    server_url: str,
    api_key: str | None = None,
    transport: Literal["streamable-http", "sse"] = "streamable-http",
    headers: dict[str, str] | None = None,
):
    """Async context manager for MCP session lifecycle management.

    This context manager handles:
    - Connection establishment to the MCP server
    - Session initialization and tool discovery
    - Creation of tool wrappers for Mellea integration
    - Proper cleanup on exit

    The manager supports two transport types:
    - **streamable-http**: Bidirectional HTTP streaming (e.g., GitHub Copilot MCP)
    - **sse**: Server-Sent Events for unidirectional streaming

    Args:
        server_url: URL of the MCP server
        api_key: API key for authentication (optional, can be in headers)
        transport: Transport type - either "streamable-http" or "sse"
        headers: Additional headers to send (optional)

    Yields:
        MCPSessionManager: Configured session manager with active connection

    Raises:
        ValueError: If an unknown transport type is specified
        Exception: If connection to the MCP server fails

    Example:
        ```python
        # Using streamable-http (GitHub Copilot)
        async with mcp_session_manager(
            server_url="https://api.githubcopilot.com/mcp/",
            api_key="your_api_key",
            transport="streamable-http"
        ) as mcp_manager:
            # Use mcp_manager here
            pass

        # Using SSE (other MCP servers)
        async with mcp_session_manager(
            server_url="http://localhost:3000/sse",
            transport="sse",
            headers={"Custom-Header": "value"}
        ) as mcp_manager:
            # Use mcp_manager here
            pass
        ```
    """
    global _current_mcp_manager

    manager = MCPSessionManager(server_url, api_key or "")

    # Prepare headers
    if headers is None:
        headers = {}
    if api_key and "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {api_key}"

    print(f"Connecting to MCP server at {server_url} using {transport} transport...")

    try:
        # Choose transport based on parameter
        if transport == "streamable-http":
            # Create MCP client session using streamable-http transport
            async with streamablehttp_client(url=server_url, headers=headers) as (
                read,
                write,
                get_session_id,
            ):
                async with ClientSession(read, write) as session:
                    await _initialize_session(manager, session, transport)
                    yield manager

        elif transport == "sse":
            # Create MCP client session using SSE transport
            async with sse_client(url=server_url, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await _initialize_session(manager, session, transport)
                    yield manager
        else:
            raise ValueError(
                f"Unknown transport: {transport}. Must be 'streamable-http' or 'sse'"
            )

    except Exception as e:
        print(f"\n✗ Failed to connect to MCP server: {str(e)}")
        raise
    finally:
        _current_mcp_manager = None
        print("\n✓ Disconnecting from MCP server")


async def _initialize_session(
    manager: MCPSessionManager, session: ClientSession, transport: str
):
    """Initialize MCP session and create tool wrappers.

    This internal function:
    1. Initializes the MCP session
    2. Discovers available tools from the server
    3. Creates both sync and async wrappers for each tool
    4. Stores the manager globally for access via get_current_mcp_session()

    Args:
        manager: MCPSessionManager instance to initialize
        session: Active MCP ClientSession
        transport: Transport type used for the connection
    """
    manager.session = session

    # Initialize the session
    await session.initialize()
    print(f"✓ Connected to MCP server via {transport}")

    # List available tools
    tools_result = await session.list_tools()
    manager.mcp_tools_list = tools_result.tools
    print(f"\n✓ Found {len(manager.mcp_tools_list)} available tools:")

    for tool in manager.mcp_tools_list:
        print(f"  - {tool.name}: {tool.description}")

    # Create wrapper functions for each MCP tool
    for tool in manager.mcp_tools_list:
        tool_name = tool.name
        tool_description = tool.description or ""

        # Create async wrapper that actually calls the MCP tool
        async def async_wrapper(**kwargs):
            """Async wrapper that calls MCP tool."""
            # Capture tool_name in closure
            _tool_name = tool_name
            try:
                result = await session.call_tool(_tool_name, arguments=kwargs)
                # Extract content from result
                if hasattr(result, "content") and result.content:
                    if isinstance(result.content, list) and len(result.content) > 0:
                        content_item = result.content[0]
                        if hasattr(content_item, "text"):
                            return str(content_item.text)
                        return str(content_item)
                    return str(result.content)
                return str(result)
            except Exception as e:
                return f"Error calling {_tool_name}: {str(e)}"

        # Store async version
        manager.async_tools[tool_name] = async_wrapper

        # Create sync wrapper for Mellea (returns placeholder, actual execution happens later)
        def create_sync_wrapper(tn, td, tool_schema):
            def sync_wrapper(**kwargs) -> str:
                """Sync wrapper - actual execution happens via async context."""
                # Return a marker that indicates this tool was called
                return f"[MCP Tool {tn} called with {kwargs}]"

            sync_wrapper.__name__ = tn
            
            # Build comprehensive docstring with parameter information
            doc_parts = [td]
            if tool_schema:
                # tool_schema is a dictionary, not an object
                properties = tool_schema.get('properties', {})
                required = tool_schema.get('required', [])
                
                if properties:
                    doc_parts.append("\n\nParameters:")
                    for param_name, param_info in properties.items():
                        param_desc = param_info.get('description', 'No description')
                        param_type = param_info.get('type', 'any')
                        required_marker = " (required)" if param_name in required else " (optional)"
                        doc_parts.append(f"  {param_name} ({param_type}){required_marker}: {param_desc}")
            
            sync_wrapper.__doc__ = "\n".join(doc_parts)
            
            # Add schema as attribute for Mellea to inspect
            if tool_schema:
                sync_wrapper.__mcp_schema__ = tool_schema
            
            return sync_wrapper

        manager.tools[tool_name] = create_sync_wrapper(tool_name, tool_description, tool.inputSchema if hasattr(tool, 'inputSchema') else None)

    print(f"\n✓ Created {len(manager.tools)} tool wrappers for Mellea")

    # Store in global variable for access
    _current_mcp_manager = manager


def get_current_mcp_session():
    """Get the current MCP session manager.

    This function provides global access to the active MCP session manager
    within an async context managed by mcp_session_manager().

    Returns:
        MCPSessionManager or None: The active session manager, or None if no session is active

    Example:
        ```python
        async with mcp_session_manager(...) as mcp_manager:
            # Inside the context, you can access the session globally
            current = get_current_mcp_session()
            assert current is mcp_manager
        ```
    """
    return _current_mcp_manager


__all__ = ["MCPSessionManager", "mcp_session_manager", "get_current_mcp_session"]

# Made with Bob
