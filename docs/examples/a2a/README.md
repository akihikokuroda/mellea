# A2A (Agent-to-Agent) Backend Examples

This directory contains examples of using Mellea with A2A-compliant agents.

## What is A2A?

A2A (Agent-to-Agent) is a protocol for agent communication based on the A2A Protocol v0.3 specification. It enables standardized communication between AI agents using either:
- HTTP+JSON/REST transport (Section 11 of A2A spec)
- JSON-RPC 2.0 transport (Section 9 of A2A spec)

## Prerequisites

To run these examples, you need:

1. **An A2A-compliant agent** running and accessible via HTTP
2. **httpx library** installed (included in Mellea dependencies)
3. **pydantic library** installed (included in Mellea dependencies)

## Quick Start

```python
from mellea import MelleaSession
from mellea.backends.a2a import A2ABackend

# Create an A2A backend
backend = A2ABackend(
    agent_endpoint="https://your-agent.example.com",
    transport="http",  # or "jsonrpc"
)

# Create a Mellea session
m = MelleaSession(backend=backend)

# Use the agent
response = m.chat("Hello, agent!")
print(response.content)
```

## Examples

### `a2a_example.py`

Comprehensive examples demonstrating:
- Basic A2A backend usage
- Custom configuration options
- Using `m.instruct()` with A2A
- Fetching and displaying agent card information

## A2A Backend Features

### Transport Protocols

The A2A backend supports two transport protocols:

1. **HTTP+JSON/REST** (default)
   ```python
   backend = A2ABackend(
       agent_endpoint="https://agent.example.com",
       transport="http"
   )
   ```

2. **JSON-RPC 2.0**
   ```python
   backend = A2ABackend(
       agent_endpoint="https://agent.example.com",
       transport="jsonrpc"
   )
   ```

### Auto-Detection

The backend can automatically detect the preferred transport from the agent's card:

```python
backend = A2ABackend(
    agent_endpoint="https://agent.example.com",
    auto_detect_transport=True  # Default
)
```

### Configuration Options

Pass A2A-specific configuration to the agent:

```python
backend = A2ABackend(
    agent_endpoint="https://agent.example.com",
    model_options={
        "configuration": {
            "max_iterations": 5,
            "temperature": 0.7,
        }
    }
)
```

### Timeout Settings

Adjust the timeout for agent communication:

```python
backend = A2ABackend(
    agent_endpoint="https://agent.example.com",
    timeout=300.0  # 5 minutes
)
```

## Agent Card

A2A agents expose metadata via an agent card at `/.well-known/agent-card.json`. The backend automatically fetches this to:
- Determine supported transport protocols
- Get agent capabilities
- Display agent information

## Limitations

- **No streaming support**: A2A responses are synchronous
- **No tool calling**: A2A protocol doesn't standardize tool calling yet
- **No structured outputs**: Format parameter is not supported
- **No batching**: Multiple requests are processed sequentially

## Troubleshooting

### Connection Errors

If you get connection errors:
1. Verify the agent endpoint URL is correct
2. Check that the agent is running and accessible
3. Ensure firewall rules allow the connection

### Transport Errors

If you get transport-related errors:
1. Try setting `auto_detect_transport=False` and specify transport explicitly
2. Check the agent card at `https://your-agent.example.com/.well-known/agent-card.json`
3. Verify the agent supports your chosen transport protocol

### Timeout Errors

If requests timeout:
1. Increase the timeout: `timeout=300.0` (5 minutes)
2. Check agent performance and response times
3. Consider if the agent is overloaded

## Additional Resources

- [A2A Protocol Specification](https://a2a-protocol.org)
- [Mellea Documentation](https://mellea.ai/)
- [Mellea GitHub Repository](https://github.com/generative-computing/mellea)