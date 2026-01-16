"""Pydantic models for A2A (Agent-to-Agent) protocol types.

Based on A2A Protocol v0.3 specification (a2a-protocol.org).

The A2A protocol defines three official protocol bindings.
This implementation supports two of them:
- HTTP+JSON/REST (Section 11) ✅ SUPPORTED
- JSON-RPC 2.0 (Section 9) ✅ SUPPORTED
- gRPC (Section 10) ❌ NOT SUPPORTED

These types represent the core data structures shared across the supported bindings.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Part(BaseModel):
    """Represents a part of a message (text, data, tool call, etc.)."""

    model_config = ConfigDict(populate_by_name=True)

    text: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    tool_call: Optional[dict[str, Any]] = Field(None, alias="toolCall")
    tool_result: Optional[dict[str, Any]] = Field(None, alias="toolResult")


class Message(BaseModel):
    """Represents a message in the A2A protocol."""

    model_config = ConfigDict(populate_by_name=True)

    message_id: str = Field(..., alias="messageId")
    role: str  # "user" | "agent" | "system"
    parts: list[Part]
    timestamp: Optional[datetime] = None


class TaskStatus(BaseModel):
    """Status of a task including any result message."""

    state: str  # "pending" | "working" | "complete" | "error"
    message: Optional[Message] = None
    error: Optional[str] = None


class Task(BaseModel):
    """Represents an asynchronous task."""

    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(..., alias="taskId")
    status: TaskStatus


class SendMessageResponse(BaseModel):
    """Response from the A2A message:send endpoint.

    Can contain either a direct message response or a task reference.
    """

    message: Optional[Message] = None
    task: Optional[Task] = None


class AgentInterface(BaseModel):
    """Declares a combination of a target URL and a transport protocol."""

    model_config = ConfigDict(populate_by_name=True)

    url: str
    protocol_binding: str = Field(..., alias="protocolBinding")
    tenant: Optional[str] = None


class AgentCard(BaseModel):
    """Agent Card - metadata about an A2A agent from /.well-known/agent-card.json."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    url: str  # Kept for backward compatibility
    version: Optional[str] = None
    capabilities: Optional[dict[str, Any]] = None

    # Modern interface specification (A2A v0.3+)
    supported_interfaces: Optional[list[AgentInterface]] = Field(
        None, alias="supportedInterfaces"
    )

    # Deprecated fields (kept for backward compatibility)
    preferred_transport: Optional[str] = Field(None, alias="preferredTransport")

    protocol_version: Optional[str] = Field(None, alias="protocolVersion")
    default_input_modes: Optional[list[str]] = Field(None, alias="defaultInputModes")
    default_output_modes: Optional[list[str]] = Field(None, alias="defaultOutputModes")
    skills: Optional[list[dict[str, Any]]] = None

# Made with Bob
