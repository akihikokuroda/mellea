# Copyright IBM Corp. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures and utilities for tool naming reliability benchmark."""

import json
from pathlib import Path

import pytest

from mellea.backends.tools import MelleaTool
from mellea.core.base import Component, TemplateRepresentation

# Markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "tool_naming_reliability: mark test as part of tool naming reliability benchmark",
    )
    config.addinivalue_line(
        "markers",
        "tool_naming_reliability_p3: mark test as part of P3 phase (multi-run, confidence intervals)",
    )


# Test data path
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def scenarios_data():
    """Load test scenarios from JSON."""
    scenario_file = FIXTURES_DIR / "scenarios.json"
    if not scenario_file.exists():
        pytest.skip(f"Scenarios file not found: {scenario_file}")
    with open(scenario_file) as f:
        return json.load(f)


@pytest.fixture
def minimal_system_prompt():
    """Minimal system prompt: tool list only, no routing guidance."""
    return """You have access to the following search tools:

1. component_email.search: Search the corporate email database
2. component_web.search: Search the web
3. component_files.search: Search internal file storage
4. component_slack.search: Search Slack messages
5. component_calendar.search: Search calendar

Use the appropriate tool to answer questions."""


@pytest.fixture
def descriptive_system_prompt():
    """Detailed system prompt: tool list + explicit routing guidance."""
    return """You have access to the following search tools to find information:

1. component_email.search: Search the corporate email database for internal communications, memos, and discussions
2. component_web.search: Search the public web for external information, articles, and resources
3. component_files.search: Search internal file storage for documents, reports, and archives
4. component_slack.search: Search Slack messages for team conversations and discussions
5. component_calendar.search: Search calendar for meetings, events, and schedules
6. component_docs.search: Search shared documents and collaborative files
7. component_contacts.search: Search contact directory and team member information
8. component_notes.search: Search meeting notes and action items

Routing guide:
- When a query mentions email, messages, memos, or communications → use component_email.search
- When a query asks about web topics, external information, or public knowledge → use component_web.search
- When a query mentions files, documents, archives, reports, or internal storage → use component_files.search
- When a query asks about Slack, team conversations, or chat messages → use component_slack.search
- When a query mentions calendar, meetings, events, schedules, or appointments → use component_calendar.search
- When a query asks about shared documents or collaborative files → use component_docs.search
- When a query asks about people, contacts, or team members → use component_contacts.search
- When a query asks about notes, action items, or meeting notes → use component_notes.search
- When ambiguous, prioritize based on the most specific keyword in the query"""


class MockSearchTool:
    """Mock tool that simulates a search operation without actual execution."""

    def __init__(self, component_name: str):
        self.component_name = component_name
        self.calls = []

    def search(self, query: str) -> str:
        """Mock search that records calls and returns a fake result."""
        self.calls.append({"query": query, "component": self.component_name})
        return f"Results from {self.component_name} for: {query}"

    def reset(self):
        """Clear call history."""
        self.calls.clear()


@pytest.fixture
def mock_search_tools():
    """Create mock search tools for testing."""
    return {
        "email": MockSearchTool("email"),
        "web": MockSearchTool("web"),
        "files": MockSearchTool("files"),
        "slack": MockSearchTool("slack"),
        "calendar": MockSearchTool("calendar"),
        "docs": MockSearchTool("docs"),
        "contacts": MockSearchTool("contacts"),
        "notes": MockSearchTool("notes"),
    }


def create_search_component(component_name: str, tool_func) -> Component:
    """Create a component with a prefixed search tool.

    Args:
        component_name: Name to use as prefix (e.g., "email" → "component_email")
        tool_func: Callable that implements search(query: str) -> str

    Returns:
        A MelleaTool with the prefixed name
    """
    # Create a MelleaTool from the callable with prefixed name
    return MelleaTool.from_callable(tool_func, name=f"component_{component_name}.search")


@pytest.fixture
def multi_component_template_factory(mock_search_tools):
    """Factory to create templates with N identical-named tools."""

    def _create(component_names: list[str]) -> TemplateRepresentation:
        """Create template with search tools for each component.

        Args:
            component_names: List of component names (e.g., ["email", "web", "files"])

        Returns:
            A TemplateRepresentation with prefixed search tools
        """
        tools = []
        for name in component_names:
            if name not in mock_search_tools:
                raise ValueError(f"Unknown component: {name}")
            tool_func = mock_search_tools[name].search
            tool = MelleaTool.from_callable(
                tool_func, name=f"component_{name}.search"
            )
            tools.append(tool)

        # Create a simple template-like structure with tools
        # This is a minimal representation; actual TemplateRepresentation
        # would need full setup
        return {"tools": tools, "component_names": component_names}

    return _create


@pytest.fixture
def tool_call_extractor():
    """Extract tool name and component ID from LLM response."""

    def extract_tool_name(response: str) -> str | None:
        """Extract the tool name called from the response.

        Looks for patterns like:
        - "tool_name"
        - {"name": "tool_name"}
        - Invoking component_email.search
        """
        import re

        # Pattern 1: JSON with "name" field
        match = re.search(r'"name"\s*:\s*"([^"]+)"', response)
        if match:
            return match.group(1)

        # Pattern 2: Direct tool name mention
        match = re.search(r"component_\w+\.search", response)
        if match:
            return match.group(0)

        return None

    def extract_component_id(response: str) -> str | None:
        """Extract component ID from tool name or response."""
        tool_name = extract_tool_name(response)
        if tool_name and tool_name.startswith("component_"):
            # Extract component name from "component_email.search" → "email"
            import re

            match = re.search(r"component_(\w+)\.search", tool_name)
            if match:
                return match.group(1)
        return None

    return {
        "extract_tool_name": extract_tool_name,
        "extract_component_id": extract_component_id,
    }
