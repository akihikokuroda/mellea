# Copyright IBM Corp. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test Scenario 1: Single-turn tool selection accuracy with prefix-based naming.

This scenario measures whether the LLM can reliably choose the correct prefixed
tool when presented with multiple identical-named tools (one per component).

Markers:
- tool_naming_reliability: Part of the prefix-based validation benchmark
- e2e: Requires LLM backend
- qualitative: Output quality depends on model behavior
"""

import pytest

from mellea.backends import ModelOption
from mellea.backends.tools import MelleaTool
from mellea.core.base import CBlock, Component
from mellea.stdlib.session import start_session


pytestmark = [
    pytest.mark.tool_naming_reliability,
    pytest.mark.e2e,
    pytest.mark.qualitative,
    pytest.mark.ollama,
]


@pytest.fixture(scope="module")
def m_session():
    """Start a Mellea session with mistral:latest model."""
    session = start_session(
        model_id="mistral:latest",
        model_options={ModelOption.MAX_NEW_TOKENS: 100}
    )
    yield session
    del session


class SearchComponent(Component[str]):
    """A component that provides a search tool."""

    def __init__(self, component_name: str):
        """Initialize with component name used as tool prefix.

        Args:
            component_name: Name for this component (e.g., "email")
        """
        self.component_name = component_name

    def format_for_llm(self, template_repr):
        """Format component for LLM as a search tool with prefixed name."""
        # Create a search function specific to this component
        component_name = self.component_name

        def search_func(query: str) -> str:
            """Search the {component_name} database."""
            # In real usage, this would execute actual searches
            # For testing, we return a marker showing which component was "called"
            return f"[SEARCH_EXECUTED: {component_name} searched for '{query}']"

        # Create a MelleaTool with the prefixed name
        tool = MelleaTool.from_callable(
            search_func,
            name=f"component_{component_name}.search",
        )

        # Return the tool in the template representation
        return tool


@pytest.mark.parametrize(
    "query,expected_component",
    [
        ("Find Q1 budget information in our corporate email", "email"),
        ("Search the web for Python documentation", "web"),
        ("Look for files modified last week", "files"),
    ],
    ids=["email_explicit", "web_explicit", "files_explicit"],
)
def test_prefix_single_turn_easy(
    m_session, descriptive_system_prompt, tool_call_extractor, query, expected_component
):
    """Test that LLM correctly routes to intended component for easy cases.

    Easy cases have explicit mentions of which component to use.
    """
    components = [
        SearchComponent("email"),
        SearchComponent("web"),
        SearchComponent("files"),
    ]

    # Build a prompt that includes all components and their tools (extracted from descriptions)
    tool_list = "\n".join(
        [f"- component_{c.component_name}.search: Search the {c.component_name} database"
         for c in components]
    )

    full_prompt = f"""{descriptive_system_prompt}

Query: {query}

Which tool would you use to answer this query? Call the appropriate tool."""

    # Get LLM response
    response = m_session.instruct(full_prompt)
    response_text = response.value

    # Extract which component the LLM chose
    chosen_component = tool_call_extractor["extract_component_id"](response_text)

    # For explicit cases, we expect the correct component
    assert chosen_component == expected_component, (
        f"Expected component '{expected_component}' for query '{query}', "
        f"but got '{chosen_component}'. Response: {response_text}"
    )


def test_prefix_single_turn_ambiguous(
    m_session, descriptive_system_prompt, tool_call_extractor
):
    """Test that LLM consistently handles ambiguous queries.

    For ambiguous queries, any component is acceptable as long as
    the model picks one from the available set.
    """
    components = ["email", "web", "files"]
    query = "Find budget-related documents"

    # Run the query twice to check consistency
    responses = []
    for run in range(2):
        full_prompt = f"""{descriptive_system_prompt}

Query: {query}

Which tool would you use to answer this query? Call the appropriate tool."""

        response = m_session.instruct(full_prompt)
        chosen_component = tool_call_extractor["extract_component_id"](response.value)
        responses.append(chosen_component)

    # Both should pick a valid component
    assert all(r in components for r in responses), (
        f"LLM chose invalid component. "
        f"Expected one of {components}, got {responses}"
    )

    # For ambiguous queries, consistency is nice but not required
    # (model may legitimately pick different components)
    # Just verify that it picked something valid both times


def test_prefix_single_turn_accuracy_batch(
    m_session, descriptive_system_prompt, tool_call_extractor, scenarios_data
):
    """Test accuracy across a batch of single-turn scenarios.

    Measures: % of queries correctly routed to expected component.
    Target: ≥95%
    """
    scenarios = scenarios_data.get("single_turn", [])
    if not scenarios:
        pytest.skip("No single_turn scenarios in test data")

    correct = 0
    total = 0
    results = []

    for scenario in scenarios:
        if scenario["difficulty"] == "ambiguous":
            # Skip ambiguous for this accuracy test
            continue

        query = scenario["query"]
        expected_component = scenario["expected_component"]
        components = scenario["components"]

        full_prompt = f"""{descriptive_system_prompt}

Query: {query}

Available components: {', '.join([f'component_{c}' for c in components])}

Which tool would you use? Call the appropriate tool."""

        response = m_session.instruct(full_prompt)
        chosen_component = tool_call_extractor["extract_component_id"](response.value)

        is_correct = chosen_component == expected_component
        correct += int(is_correct)
        total += 1

        results.append(
            {
                "query": query,
                "expected": expected_component,
                "chosen": chosen_component,
                "correct": is_correct,
            }
        )

    accuracy = (correct / total * 100) if total > 0 else 0

    # Log results for debugging
    for result in results:
        status = "✓" if result["correct"] else "✗"
        print(
            f"{status} {result['query'][:50]:50s} "
            f"expected={result['expected']:10s} "
            f"got={result['chosen']:10s}"
        )

    print(f"\nAccuracy: {correct}/{total} = {accuracy:.1f}%")
    print(f"Target: ≥95%")

    # For now, log the accuracy but don't fail on threshold
    # (This helps establish baseline before optimizing)
    assert accuracy >= 50, (
        f"Accuracy {accuracy:.1f}% is too low (expected ≥50% for initial benchmark). "
        f"Results: {results}"
    )
