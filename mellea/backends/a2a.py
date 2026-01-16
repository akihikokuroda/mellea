"""A2A (Agent-to-Agent) protocol backend for Mellea.

This backend enables Mellea to communicate with A2A-compliant agents
using the A2A protocol v0.3 specification.

Supports two transport bindings:
- HTTP+JSON/REST (default)
- JSON-RPC 2.0
"""

import asyncio
import datetime
import uuid
from collections.abc import Sequence
from typing import Any, Optional

import httpx

from ..core import (
    BaseModelSubclass,
    C,
    CBlock,
    Component,
    Context,
    FancyLogger,
    GenerateLog,
    GenerateType,
    ModelOutputThunk,
)
from ..formatters import ChatFormatter, TemplateFormatter
from ..helpers import ClientCache, get_current_event_loop
from ..stdlib.components import Message
from .model_ids import ModelIdentifier
from .a2a_types import (
    AgentCard,
    Message as A2AMessage,
    Part as A2APart,
    SendMessageResponse,
    Task,
    TaskStatus,
)
from .backend import FormatterBackend
from .model_options import ModelOption

format: None = None  # typing this variable to shadow the global format function


class A2ABackend(FormatterBackend):
    """Backend for communicating with A2A-compliant agents.

    This backend allows Mellea to interact with remote agents that implement
    the A2A (Agent-to-Agent) protocol. It supports both HTTP+JSON/REST and
    JSON-RPC 2.0 transport bindings.

    Example:
        ```python
        from mellea import MelleaSession
        from mellea.backends.a2a import A2ABackend

        # Create a session with an A2A agent
        m = MelleaSession(
            backend=A2ABackend(
                agent_endpoint="https://my-agent.example.com",
                transport="http"  # or "jsonrpc"
            )
        )

        # Use the agent
        response = m.chat("Hello, agent!")
        print(response.content)
        ```
    """

    def __init__(
        self,
        agent_endpoint: str,
        model_id: str | ModelIdentifier = "a2a-agent",
        formatter: ChatFormatter | None = None,
        model_options: dict | None = None,
        *,
        transport: str = "http",
        timeout: float = 150.0,
        a2a_version: str = "0.3",
        auto_detect_transport: bool = True,
        verify_ssl: bool = True,
    ):
        """Initialize an A2A backend.

        Args:
            agent_endpoint: The base URL of the A2A agent (e.g., "https://agent.example.com")
            model_id: Model identifier for logging/tracking purposes
            formatter: Custom formatter for Mellea components. Defaults to TemplateFormatter
            model_options: Global model options. Defaults to None
            transport: Transport protocol - "http" for HTTP+JSON/REST or "jsonrpc" for JSON-RPC 2.0
            timeout: Timeout in seconds for HTTP requests (default: 150.0 = 2.5 minutes)
            a2a_version: A2A protocol version (default: "0.3")
            auto_detect_transport: If True, fetch agent card and use preferred transport
            verify_ssl: If False, disable SSL certificate verification (useful for local testing)
        """
        super().__init__(
            model_id=model_id,
            formatter=(
                formatter if formatter is not None else TemplateFormatter(model_id=model_id)
            ),
            model_options=model_options,
        )

        self.agent_endpoint = agent_endpoint.rstrip("/")
        self.timeout = timeout
        self.a2a_version = a2a_version
        self._transport = transport.lower()
        self._auto_detect_transport = auto_detect_transport
        self._agent_card: Optional[AgentCard] = None
        self._verify_ssl = verify_ssl

        # Client cache for managing httpx clients across event loops
        self._client_cache = ClientCache(2)

        # Model options mapping - A2A doesn't use standard model options
        # We'll handle A2A-specific options directly in the generate method
        self.to_mellea_model_opts_map = {}
        self.from_mellea_model_opts_map = {}

        self._logger = FancyLogger.get_logger()

    async def _get_agent_card(self) -> AgentCard:
        """Fetch and cache the agent card from the A2A agent."""
        if self._agent_card is not None:
            return self._agent_card

        url = f"{self.agent_endpoint}/.well-known/agent-card.json"

        async with httpx.AsyncClient(timeout=self.timeout, verify=self._verify_ssl) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                self._agent_card = AgentCard(**response.json())
                self._logger.info(f"Fetched agent card for: {self._agent_card.name}")
                return self._agent_card
            except Exception as e:
                self._logger.warning(f"Could not fetch agent card from {url}: {e}")
                # Return a minimal agent card
                self._agent_card = AgentCard(
                    name="Unknown Agent",
                    description="Agent card could not be fetched",
                    url=self.agent_endpoint,
                )
                return self._agent_card

    async def _determine_transport(self) -> str:
        """Determine the transport protocol to use."""
        if not self._auto_detect_transport:
            return self._transport

        try:
            agent_card = await self._get_agent_card()

            # Check modern supportedInterfaces first (A2A v0.3+)
            if agent_card.supported_interfaces:
                for interface in agent_card.supported_interfaces:
                    protocol = interface.protocol_binding.upper()
                    if "JSONRPC" in protocol or "JSON-RPC" in protocol:
                        self._logger.info("Auto-detected JSON-RPC transport")
                        return "jsonrpc"
                    elif "HTTP" in protocol or "REST" in protocol:
                        self._logger.info("Auto-detected HTTP+JSON/REST transport")
                        return "http"

            # Fall back to deprecated preferredTransport field
            if agent_card.preferred_transport:
                if agent_card.preferred_transport.upper() == "JSONRPC":
                    self._logger.info("Using preferred transport: JSON-RPC")
                    return "jsonrpc"

        except Exception as e:
            self._logger.warning(f"Could not determine transport, using default: {e}")

        return self._transport

    def _mellea_message_to_a2a(self, message: Message) -> A2AMessage:
        """Convert a Mellea Message to an A2A Message."""
        parts = []
        if message.content:
            parts.append(A2APart(text=message.content))

        return A2AMessage(
            message_id=str(uuid.uuid4()),
            role=message.role if hasattr(message, "role") else "user",
            parts=parts,
            # Don't include timestamp - it causes JSON serialization issues
        )

    def _context_to_a2a_message(self, ctx: Context, action: Component[C] | CBlock) -> A2AMessage:
        """Convert Mellea context and action to an A2A message.

        This extracts the most recent user message or instruction from the context.
        """
        # Get linearized context
        linearized_context = ctx.view_for_generation()
        assert linearized_context is not None, (
            "Cannot generate from a non-linear context in a FormatterBackend."
        )
        
        # Convert to chat messages
        messages: list[Message] = self.formatter.to_chat_messages(linearized_context)
        
        # Add the action as the final message
        messages.extend(self.formatter.to_chat_messages([action]))

        # Find the last user message
        user_content = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_content = msg.content
                break

        parts = [A2APart(text=user_content)] if user_content else []

        return A2AMessage(
            message_id=str(uuid.uuid4()),
            role="user",
            parts=parts,
            # Don't include timestamp - it causes JSON serialization issues
            # and is optional in the A2A spec
        )

    async def _send_message_http(
        self,
        message: A2AMessage,
        configuration: Optional[dict] = None,
    ) -> SendMessageResponse:
        """Send message via HTTP+JSON/REST binding (A2A protocol Section 11)."""
        url = f"{self.agent_endpoint}/v1/message:send"

        # Build request payload
        payload: dict = {"message": message.model_dump(by_alias=True, exclude_none=True)}
        if configuration:
            payload["configuration"] = configuration

        # A2A service parameters via HTTP headers
        headers = {
            "A2A-Version": self.a2a_version,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout, verify=self._verify_ssl) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return SendMessageResponse(**response.json())

    async def _send_message_jsonrpc(
        self,
        message: A2AMessage,
        configuration: Optional[dict] = None,
    ) -> SendMessageResponse:
        """Send message via JSON-RPC 2.0 binding (A2A protocol Section 9)."""
        url = f"{self.agent_endpoint}/"

        # Convert message to JSONRPC format
        jsonrpc_message = {
            "kind": "message",
            "messageId": message.message_id,
            "role": message.role,
            "parts": [
                {"kind": "text", "text": part.text} for part in message.parts if part.text
            ],
        }

        # A2A service parameters via HTTP headers
        headers = {
            "A2A-Version": self.a2a_version,
            "Content-Type": "application/json",
        }

        # Try spec-compliant format first, then fallback to kAgent format
        methods_to_try = ["SendMessage", "message/send"]

        last_error = None
        async with httpx.AsyncClient(timeout=self.timeout, verify=self._verify_ssl) as client:
            for method in methods_to_try:
                # Build JSONRPC request
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": {"message": jsonrpc_message},
                }

                if configuration:
                    payload["params"]["configuration"] = configuration

                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

                # Check if method was found
                if "error" in result:
                    error_code = result["error"].get("code")
                    # -32601 is "Method not found" - try next method
                    if error_code == -32601:
                        last_error = result["error"]
                        continue
                    # Other errors should be raised immediately
                    raise Exception(f"JSONRPC error: {result['error']}")

                # Success! Log which method worked
                if method != methods_to_try[0]:
                    self._logger.info(
                        f"JSONRPC method '{methods_to_try[0]}' not found, using '{method}' instead"
                    )
                break
            else:
                # All methods failed
                raise Exception(f"JSONRPC error: {last_error}")

            # Extract response from JSONRPC format
            jsonrpc_result = result.get("result", {})

            # Get response text from artifacts
            response_text = ""
            artifacts = jsonrpc_result.get("artifacts", [])
            if artifacts and len(artifacts) > 0:
                parts = artifacts[0].get("parts", [])
                if parts and len(parts) > 0:
                    response_text = parts[0].get("text", "")

            # Convert back to standard A2A format
            response_message = A2AMessage(
                message_id=jsonrpc_result.get("id", ""),
                role="assistant",
                parts=[A2APart(text=response_text)],
            )

            task = Task(
                task_id=jsonrpc_result.get("id", ""),
                status=TaskStatus(
                    state=jsonrpc_result.get("status", {}).get("state", "completed"),
                    message=response_message,
                ),
            )

            return SendMessageResponse(task=task)

    async def _send_message(
        self,
        message: A2AMessage,
        configuration: Optional[dict] = None,
        transport: Optional[str] = None,
    ) -> SendMessageResponse:
        """Send a message to the A2A agent using the specified transport."""
        if transport is None:
            transport = await self._determine_transport()

        if transport == "jsonrpc":
            return await self._send_message_jsonrpc(message, configuration)
        else:
            return await self._send_message_http(message, configuration)

    def _extract_response_text(self, response: SendMessageResponse) -> str:
        """Extract text content from an A2A response."""
        # Try direct message response first
        if response.message and response.message.parts:
            for part in response.message.parts:
                if part.text:
                    return part.text

        # Try task-based response
        if response.task and response.task.status.message:
            task_message = response.task.status.message
            if task_message.parts:
                for part in task_message.parts:
                    if part.text:
                        return part.text

        return "No response from agent"

    async def generate_from_context(
        self,
        action: Component[C] | CBlock,
        ctx: Context,
        *,
        format: type[BaseModelSubclass] | None = None,
        model_options: dict | None = None,
        tool_calls: bool = False,
    ) -> tuple[ModelOutputThunk[C], Context]:
        """Generate a response from the A2A agent based on the context.

        Args:
            action: The component or block to generate from
            ctx: The current context
            format: Optional structured output format (not supported by A2A)
            model_options: Optional model options for this generation
            tool_calls: Whether to enable tool calls (not supported by A2A)

        Returns:
            A tuple of (ModelOutputThunk, updated Context)
        """
        # Start by awaiting any necessary computation
        await self.do_generate_walk(action)

        # Merge model options
        merged_options = self.model_options.copy() if self.model_options else {}
        if model_options:
            merged_options.update(model_options)

        # Extract A2A-specific options (using string keys since we don't have ModelOption constants)
        configuration = merged_options.get("configuration")
        transport = merged_options.get("transport")
        
        # Get linearized context
        linearized_context = ctx.view_for_generation()
        assert linearized_context is not None, (
            "Cannot generate from a non-linear context in a FormatterBackend."
        )

        # Convert context to A2A message
        a2a_message = self._context_to_a2a_message(ctx, action)

        # Send message to A2A agent
        try:
            response = await self._send_message(
                a2a_message, configuration=configuration, transport=transport
            )
            response_text = self._extract_response_text(response)
        except Exception as e:
            self._logger.error(f"Failed to communicate with A2A agent: {e}")
            response_text = f"Error communicating with agent: {str(e)}"

        # Create ModelOutputThunk with the response text
        output = ModelOutputThunk(response_text)
        output._context = linearized_context
        output._action = action
        output._model_options = merged_options
        output._computed = True  # A2A responses are synchronous
        
        # Create generate log (required by Mellea)
        output._generate_log = GenerateLog(
            date=datetime.datetime.now(datetime.timezone.utc),
            backend=f"A2A({self.agent_endpoint})",
            model_options=merged_options,
            action=action,
            result=output,
            is_final_result=True,
        )
        
        # Parse the output if the action is a Component
        if isinstance(action, Component):
            output.parsed_repr = action._parse(output)

        # Update context
        new_ctx = ctx.add(action).add(output)

        return output, new_ctx

    async def generate_from_raw(
        self,
        actions: Sequence[Component[C] | CBlock],
        ctx: Context,
        *,
        format: type[BaseModelSubclass] | None = None,
        model_options: dict | None = None,
        tool_calls: bool = False,
    ) -> list[ModelOutputThunk]:
        """Generate responses for multiple actions without using templates.

        A2A agents typically don't support batching, so this will process
        actions sequentially.

        Args:
            actions: List of actions to generate responses for
            ctx: Context (not used in raw generation but required by interface)
            format: Optional structured output format (not supported by A2A)
            model_options: Optional model options for this generation
            tool_calls: Whether to enable tool calls (not supported by A2A)

        Returns:
            List of ModelOutputThunks, one for each action
        """
        if len(actions) > 1:
            self._logger.info(
                "A2A doesn't support batching; will process actions sequentially."
            )

        # Merge model options
        merged_options = self.model_options.copy() if self.model_options else {}
        if model_options:
            merged_options.update(model_options)

        # Extract A2A-specific options
        configuration = merged_options.get("configuration")
        transport = merged_options.get("transport")

        results = []
        for action in actions:
            # Await any necessary computation
            await self.do_generate_walk(action)

            # Format the action as text
            action_text = self.formatter.print(action)

            # Create A2A message
            a2a_message = A2AMessage(
                message_id=str(uuid.uuid4()),
                role="user",
                parts=[A2APart(text=action_text)],
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )

            # Send message to A2A agent
            try:
                response = await self._send_message(
                    a2a_message, configuration=configuration, transport=transport
                )
                response_text = self._extract_response_text(response)
            except Exception as e:
                self._logger.error(f"Failed to communicate with A2A agent: {e}")
                response_text = f"Error communicating with agent: {str(e)}"

            # Create ModelOutputThunk with the response text
            output = ModelOutputThunk(response_text)
            output._action = action
            output._model_options = merged_options
            output._computed = True

            # Parse the output if the action is a Component
            if isinstance(action, Component):
                output.parsed_repr = action._parse(output)

            results.append(output)

        return results

# Made with Bob
