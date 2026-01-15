"""
Example of using MCP client to connect to GitHub MCP server
and use its tools with Mellea, with session management using contextlib.
"""
import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Callable

import mellea
from mellea.backends import ModelOption
from mellea.core import CBlock
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# Global variable to store the current MCP session manager
_current_mcp_manager = None


class MCPSessionManager:
    """Manager for MCP client sessions that can be stored and accessed globally."""
    
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url
        self.api_key = api_key
        self.session = None
        self.tools = {}
        self.async_tools = {}
        self.mcp_tools_list = []
        
    def get_tools_for_mellea(self):
        """Get list of tools to pass to Mellea."""
        return list(self.tools.values())
    
    async def call_tool_directly(self, tool_name: str, arguments: dict):
        """Call an MCP tool directly."""
        if self.session:
            return await self.session.call_tool(tool_name, arguments=arguments)
        raise RuntimeError("Session not connected")
    
    async def execute_tool_call(self, tool_name: str, **kwargs):
        """Execute a tool call and return the result."""
        if tool_name in self.async_tools:
            return await self.async_tools[tool_name](**kwargs)
        raise ValueError(f"Tool {tool_name} not found")
    
    def to_cblock(self) -> CBlock:
        """Convert session info to a CBlock for adding to Mellea context."""
        info = f"MCP Session: {self.server_url} ({len(self.tools)} tools available)"
        return CBlock(info)


@asynccontextmanager
async def mcp_session_manager(server_url: str, api_key: str):
    """Async context manager for MCP session."""
    global _current_mcp_manager
    
    manager = MCPSessionManager(server_url, api_key)
    
    print(f"Connecting to GitHub MCP server at {server_url}...")
    
    try:
        # Create MCP client session using streamable-http transport
        async with streamablehttp_client(
            url=server_url,
            headers={"Authorization": f"Bearer {api_key}"}
        ) as (read, write, get_session_id):
            async with ClientSession(read, write) as session:
                manager.session = session
                
                # Initialize the session
                await session.initialize()
                print("✓ Connected to GitHub MCP server")
                
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
                    
                    # Create async wrapper
                    async def async_wrapper(**kwargs):
                        """Async wrapper that calls MCP tool."""
                        # Capture tool_name in closure
                        _tool_name = tool_name
                        try:
                            result = await session.call_tool(_tool_name, arguments=kwargs)
                            # Extract content from result
                            if hasattr(result, 'content') and result.content:
                                if isinstance(result.content, list) and len(result.content) > 0:
                                    content_item = result.content[0]
                                    if hasattr(content_item, 'text'):
                                        return str(content_item.text)
                                    return str(content_item)
                                return str(result.content)
                            return str(result)
                        except Exception as e:
                            return f"Error calling {_tool_name}: {str(e)}"
                    
                    # Store async version
                    manager.async_tools[tool_name] = async_wrapper
                    
                    # Create sync wrapper for Mellea (returns placeholder, actual execution happens later)
                    def create_sync_wrapper(tn, td):
                        def sync_wrapper(**kwargs) -> str:
                            """Sync wrapper - actual execution happens via async context."""
                            # Return a marker that indicates this tool was called
                            return f"[MCP Tool {tn} called with {kwargs}]"
                        sync_wrapper.__name__ = tn
                        sync_wrapper.__doc__ = td
                        return sync_wrapper
                    
                    manager.tools[tool_name] = create_sync_wrapper(tool_name, tool_description)
                
                print(f"\n✓ Created {len(manager.tools)} tool wrappers for Mellea")
                
                # Store in global variable for access
                _current_mcp_manager = manager
                
                try:
                    yield manager
                finally:
                    _current_mcp_manager = None
                    print("\n✓ Disconnecting from MCP server")
                    
    except Exception as e:
        print(f"\n✗ Failed to connect to MCP server: {str(e)}")
        raise


def get_current_mcp_session():
    """Get the current MCP session manager."""
    return _current_mcp_manager


async def main_async():
    """Main async entry point."""
    # GitHub MCP server configuration
    server_url = "https://api.githubcopilot.com/mcp/"
    api_key = "dummy"  # Replace with real API key
    
    try:
        # Use async context manager to handle MCP session
        async with mcp_session_manager(server_url, api_key) as mcp_manager:
            
            # Create Mellea session with Claude Haiku via OpenAI-compatible endpoint
            from mellea.backends.openai import OpenAIBackend
            from mellea.stdlib.session import MelleaSession
            from mellea.stdlib.context import ChatContext
            
            backend = OpenAIBackend(
                model_id="aws/claude-haiku-4-5",
                base_url="https://ete-litellm.ai-models.vpc-int.res.ibm.com",
                api_key="dummy"  # Replace with actual API key if needed
            )
            m = MelleaSession(backend=backend, ctx=ChatContext())
            
            # Store MCP session info in Mellea context as a CBlock
            m.ctx = m.ctx.add(mcp_manager.to_cblock())
            
            print("\n" + "="*60)
            print("Using Mellea with GitHub MCP tools")
            print("MCP session accessible via get_current_mcp_session()")
            print("MCP session info stored in Mellea context")
            print("="*60)
            
            # Query about GitHub user
            print("\nQuerying Mellea about GitHub user 'akihikokuroda'...")
            output = m.instruct(
                "Get information about the GitHub user 'akihikokuroda'. Use available guthub tool 'get_me' to fetch their profile information.",
                model_options={
                    ModelOption.TOOLS: mcp_manager.get_tools_for_mellea(),
                    ModelOption.MAX_NEW_TOKENS: 500,
                },
                tool_calls=True,
            )
            
            print("\n" + "-"*60)
            print("Mellea Response:")
            print("-"*60)
            if output.value:
                print(output.value)
            else:
                print("(Empty response - model may have only made tool calls)")
            
            if output.tool_calls:
                print("\n" + "-"*60)
                print("Tool Calls Made by Mellea:")
                print("-"*60)
                for tool_name, tool_call in output.tool_calls.items():
                    print(f"\nTool: {tool_name}")
                    print(f"Arguments: {json.dumps(tool_call.args, indent=2)}")
                    
                    # Execute the tool call directly via MCP session
                    print(f"\nExecuting {tool_name} via MCP session...")
                    try:
                        result = await mcp_manager.call_tool_directly(tool_name, dict(tool_call.args))
                        print(f"\nMCP Tool Result:")
                        if hasattr(result, 'content') and result.content:
                            if isinstance(result.content, list):
                                for item in result.content:
                                    if hasattr(item, 'text'):
                                        print(item.text)
                                    else:
                                        print(item)
                            else:
                                print(result.content)
                        else:
                            print(result)
                    except Exception as e:
                        print(f"Error: {str(e)}")
                        import traceback
                        traceback.print_exc()
            else:
                print("\nNo tool calls were made by the model.")
            
            # Demonstrate that MCP session is accessible globally
            print("\n" + "-"*60)
            print("Accessing MCP session globally:")
            print("-"*60)
            
            current_session = get_current_mcp_session()
            if current_session:
                print(f"✓ MCP session retrieved via get_current_mcp_session()")
                print(f"  Server URL: {current_session.server_url}")
                print(f"  Available tools: {len(current_session.tools)}")
                print(f"  Session active: {current_session.session is not None}")
            
            # Show context contains MCP info
            print("\n" + "-"*60)
            print("MCP info in Mellea context:")
            print("-"*60)
            context_list = m.ctx.as_list()
            for item in context_list:
                if isinstance(item, CBlock) and "MCP Session" in str(item):
                    print(f"✓ Found in context: {item}")
            
            print("\n" + "="*60)
            print("Done!")
            print("="*60)
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

# Made with Bob
