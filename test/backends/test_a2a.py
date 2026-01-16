"""Tests for A2A (Agent-to-Agent) backend."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mellea.backends.a2a import A2ABackend
from mellea.backends.a2a_types import (
    AgentCard,
    AgentInterface,
    Message as A2AMessage,
    Part as A2APart,
    SendMessageResponse,
    Task,
    TaskStatus,
)
from mellea.core import Context
from mellea.stdlib.components import Message


class TestA2ABackend:
    """Test suite for A2A backend."""

    @pytest.fixture
    def mock_agent_card(self):
        """Create a mock agent card."""
        return AgentCard(
            name="Test Agent",
            description="A test A2A agent",
            url="https://test-agent.example.com",
            version="1.0.0",
            supported_interfaces=[
                AgentInterface(
                    url="https://test-agent.example.com",
                    protocol_binding="HTTP+JSON/REST",
                )
            ],
        )

    @pytest.fixture
    def backend(self):
        """Create an A2A backend instance."""
        return A2ABackend(
            agent_endpoint="https://test-agent.example.com",
            transport="http",
            auto_detect_transport=False,
        )

    def test_backend_initialization(self, backend):
        """Test that backend initializes correctly."""
        assert backend.agent_endpoint == "https://test-agent.example.com"
        assert backend.timeout == 150.0
        assert backend.a2a_version == "0.3"
        assert backend._transport == "http"

    def test_backend_initialization_with_options(self):
        """Test backend initialization with custom options."""
        backend = A2ABackend(
            agent_endpoint="https://custom-agent.example.com",
            transport="jsonrpc",
            timeout=300.0,
            a2a_version="0.3",
            model_options={"configuration": {"test": "value"}},
        )
        assert backend.agent_endpoint == "https://custom-agent.example.com"
        assert backend._transport == "jsonrpc"
        assert backend.timeout == 300.0
        assert backend.model_options == {"configuration": {"test": "value"}}

    @pytest.mark.asyncio
    async def test_get_agent_card(self, backend, mock_agent_card):
        """Test fetching agent card."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_agent_card.model_dump(by_alias=True)
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            agent_card = await backend._get_agent_card()

            assert agent_card.name == "Test Agent"
            assert agent_card.description == "A test A2A agent"
            assert agent_card.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_determine_transport_http(self, backend, mock_agent_card):
        """Test transport determination for HTTP."""
        backend._auto_detect_transport = True
        backend._agent_card = mock_agent_card

        transport = await backend._determine_transport()
        assert transport == "http"

    @pytest.mark.asyncio
    async def test_determine_transport_jsonrpc(self, backend):
        """Test transport determination for JSON-RPC."""
        backend._auto_detect_transport = True
        backend._agent_card = AgentCard(
            name="Test Agent",
            description="A test agent",
            url="https://test-agent.example.com",
            supported_interfaces=[
                AgentInterface(
                    url="https://test-agent.example.com",
                    protocol_binding="JSON-RPC 2.0",
                )
            ],
        )

        transport = await backend._determine_transport()
        assert transport == "jsonrpc"

    def test_mellea_message_to_a2a(self, backend):
        """Test converting Mellea Message to A2A Message."""
        mellea_msg = Message(role="user", content="Hello, agent!")

        a2a_msg = backend._mellea_message_to_a2a(mellea_msg)

        assert a2a_msg.role == "user"
        assert len(a2a_msg.parts) == 1
        assert a2a_msg.parts[0].text == "Hello, agent!"
        assert a2a_msg.message_id is not None

    def test_extract_response_text_from_message(self, backend):
        """Test extracting text from A2A message response."""
        response = SendMessageResponse(
            message=A2AMessage(
                message_id="test-123",
                role="assistant",
                parts=[A2APart(text="Hello from agent!")],
            )
        )

        text = backend._extract_response_text(response)
        assert text == "Hello from agent!"

    def test_extract_response_text_from_task(self, backend):
        """Test extracting text from A2A task response."""
        response = SendMessageResponse(
            task=Task(
                task_id="task-123",
                status=TaskStatus(
                    state="completed",
                    message=A2AMessage(
                        message_id="msg-123",
                        role="assistant",
                        parts=[A2APart(text="Task completed!")],
                    ),
                ),
            )
        )

        text = backend._extract_response_text(response)
        assert text == "Task completed!"

    def test_extract_response_text_no_response(self, backend):
        """Test extracting text when no response is available."""
        response = SendMessageResponse()

        text = backend._extract_response_text(response)
        assert text == "No response from agent"

    @pytest.mark.asyncio
    async def test_send_message_http(self, backend):
        """Test sending message via HTTP transport."""
        a2a_message = A2AMessage(
            message_id="test-123",
            role="user",
            parts=[A2APart(text="Test message")],
        )

        mock_response_data = {
            "message": {
                "messageId": "response-123",
                "role": "assistant",
                "parts": [{"text": "Response from agent"}],
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            response = await backend._send_message_http(a2a_message)

            assert response.message is not None
            assert response.message.role == "assistant"
            assert response.message.parts[0].text == "Response from agent"

    @pytest.mark.asyncio
    async def test_generate_from_context(self, backend):
        """Test generating from context."""
        from mellea import MelleaSession
        
        # Create a proper context using MelleaSession
        m = MelleaSession(backend=backend)
        ctx = m.ctx
        action = Message(role="user", content="Test question")

        mock_response = SendMessageResponse(
            message=A2AMessage(
                message_id="response-123",
                role="assistant",
                parts=[A2APart(text="Test answer")],
            )
        )

        with patch.object(backend, "_send_message", return_value=mock_response):
            output, new_ctx = await backend.generate_from_context(action, ctx)

            assert output.value == "Test answer"
            assert output.is_computed()
            # Verify context was updated
            assert new_ctx is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
