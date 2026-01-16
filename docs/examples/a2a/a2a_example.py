"""Example of using the A2A (Agent-to-Agent) backend with Mellea.

This example demonstrates how to connect Mellea to an A2A-compliant agent
and use it for chat-based interactions.

Requirements:
- An A2A-compliant agent running and accessible via HTTP
- The agent should implement the A2A protocol v0.3 specification
"""

from mellea import MelleaSession
from mellea.backends.a2a import A2ABackend


def main():
    """Basic example of using A2A backend."""
    # Create an A2A backend pointing to your agent
    # Replace with your actual agent endpoint
    backend = A2ABackend(
        agent_endpoint="https://your-agent.example.com",
        transport="http",  # or "jsonrpc" for JSON-RPC 2.0 transport
        timeout=150.0,  # 2.5 minutes timeout
        auto_detect_transport=True,  # Automatically detect preferred transport from agent card
    )

    # Create a Mellea session with the A2A backend
    m = MelleaSession(backend=backend)

    # Use the agent like any other Mellea backend
    response = m.chat("Hello! Can you help me with a task?")
    print(f"Agent response: {response.content}")

    # Continue the conversation
    response = m.chat("What can you do?")
    print(f"Agent response: {response.content}")


def example_with_configuration():
    """Example with custom A2A configuration."""
    backend = A2ABackend(
        agent_endpoint="https://your-agent.example.com",
        transport="jsonrpc",  # Use JSON-RPC 2.0 transport
        model_options={
            "configuration": {
                # A2A-specific configuration parameters
                "max_iterations": 5,
                "temperature": 0.7,
            }
        },
    )

    m = MelleaSession(backend=backend)
    response = m.chat("Solve this problem step by step: 2 + 2 * 3")
    print(f"Agent response: {response.content}")


def example_with_instruct():
    """Example using m.instruct with A2A backend."""
    backend = A2ABackend(
        agent_endpoint="https://your-agent.example.com",
    )

    m = MelleaSession(backend=backend)

    # Use instruct for more structured requests
    result = m.instruct(
        "Analyze the sentiment of this text: 'I love using AI agents!'",
    )
    print(f"Analysis result: {result}")


def example_checking_agent_card():
    """Example of fetching and displaying agent card information."""
    import asyncio

    async def check_agent():
        backend = A2ABackend(
            agent_endpoint="https://your-agent.example.com",
        )

        # Fetch agent card
        agent_card = await backend._get_agent_card()

        print(f"Agent Name: {agent_card.name}")
        print(f"Description: {agent_card.description}")
        print(f"Version: {agent_card.version}")

        if agent_card.supported_interfaces:
            print("\nSupported Interfaces:")
            for interface in agent_card.supported_interfaces:
                print(f"  - {interface.protocol_binding} at {interface.url}")

        if agent_card.capabilities:
            print(f"\nCapabilities: {agent_card.capabilities}")

    asyncio.run(check_agent())


if __name__ == "__main__":
    # Run the basic example
    # Note: You'll need to replace the agent_endpoint with your actual A2A agent URL
    print("A2A Backend Example")
    print("=" * 50)
    print("\nTo run this example, you need:")
    print("1. An A2A-compliant agent running")
    print("2. Update the agent_endpoint URL in the code")
    print("\nExample usage:")
    print("  backend = A2ABackend(agent_endpoint='https://your-agent.example.com')")
    print("  m = MelleaSession(backend=backend)")
    print("  response = m.chat('Hello!')")
    print("\n" + "=" * 50)

    # Uncomment to run the examples (after setting up your A2A agent):
    # main()
    # example_with_configuration()
    # example_with_instruct()
    # example_checking_agent_card()

# Made with Bob
