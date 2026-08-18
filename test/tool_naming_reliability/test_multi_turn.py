# Copyright IBM Corp. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test Scenario 2: Multi-turn consistency and context awareness.

This scenario measures whether the LLM can:
1. Maintain component affinity when context doesn't change (Affinity)
2. Switch components when explicitly instructed (Context-Awareness)

Markers:
- tool_naming_reliability: Part of prefix-based validation benchmark
- e2e: Requires LLM backend
- qualitative: Output quality depends on model behavior
- slow: Multi-turn conversations can be slow
"""

import pytest

from mellea.backends import ModelOption
from mellea.backends.tools import MelleaTool
from mellea.core.base import Component
from mellea.stdlib.components import Message
from mellea.stdlib.context import ChatContext
from mellea.stdlib.session import start_session


pytestmark = [
    pytest.mark.tool_naming_reliability,
    pytest.mark.e2e,
    pytest.mark.qualitative,
    pytest.mark.slow,
    pytest.mark.ollama,
]


@pytest.fixture(scope="module")
def m_session():
    """Start a Mellea session with mistral:latest model."""
    session = start_session(
        model_id="mistral:latest",
        model_options={ModelOption.MAX_NEW_TOKENS: 150}
    )
    yield session
    del session


class SearchComponent(Component[str]):
    """A component that provides a search tool."""

    def __init__(self, component_name: str):
        """Initialize with component name used as tool prefix."""
        self.component_name = component_name

    def format_for_llm(self, template_repr):
        """Format component for LLM as a search tool with prefixed name."""
        component_name = self.component_name

        def search_func(query: str) -> str:
            """Search the {component_name} database."""
            return f"[SEARCH: {component_name} found results for '{query}']"

        tool = MelleaTool.from_callable(
            search_func,
            name=f"component_{component_name}.search",
        )
        return tool


def extract_component_id(response_text: str, tool_extractor) -> str | None:
    """Extract component ID from response."""
    return tool_extractor["extract_component_id"](response_text)


def test_multi_turn_affinity(m_session, descriptive_system_prompt, tool_call_extractor):
    """Test that LLM maintains component affinity across turns.

    Affinity: Model should use the same component in Turn 2 when context
    suggests continuity (no explicit switch).

    Turn 1: "Find emails about Q1 budget" → component_email
    Turn 2: "Who sent the most recent one?" → component_email (SAME)
    """
    ctx = ChatContext()

    # Turn 1: Initialize with email context
    turn1_prompt = f"""{descriptive_system_prompt}

User: Find emails about Q1 budget

Which tool would you use?"""

    response1 = m_session.instruct(turn1_prompt)
    component1 = extract_component_id(response1.value, tool_call_extractor)

    assert component1 == "email", (
        f"Turn 1: Expected email component, got {component1}. "
        f"Response: {response1.value}"
    )

    # Turn 2: Contextual follow-up (should stay with email)
    turn2_prompt = f"""{descriptive_system_prompt}

Context from previous search: Found emails about Q1 budget

User: Who sent the most recent one?

Which tool would you use? (Consider the context - we were just searching emails.)"""

    response2 = m_session.instruct(turn2_prompt)
    component2 = extract_component_id(response2.value, tool_call_extractor)

    assert component2 == "email", (
        f"Turn 2: Expected email component (affinity), got {component2}. "
        f"Should maintain component affinity. Response: {response2.value}"
    )


def test_multi_turn_context_awareness(
    m_session, descriptive_system_prompt, tool_call_extractor
):
    """Test that LLM switches components when explicitly instructed.

    Context-Awareness: Model should respect explicit instruction to use a
    different component.

    Turn 1: "Find emails..." → component_email
    Turn 2: "Now check the WEB for..." → component_web (SWITCH)
    """
    # Turn 1: Email context
    turn1_prompt = f"""{descriptive_system_prompt}

User: Find emails about Q1 budget

Which tool would you use?"""

    response1 = m_session.instruct(turn1_prompt)
    component1 = extract_component_id(response1.value, tool_call_extractor)

    assert component1 == "email", f"Turn 1 setup failed: got {component1}"

    # Turn 2: Explicit instruction to switch to web
    turn2_prompt = f"""{descriptive_system_prompt}

Previous search: Found emails about Q1 budget

User: Now search the WEB for Q1 budget coverage

Which tool would you use? (Note: the user explicitly asked to search the WEB)"""

    response2 = m_session.instruct(turn2_prompt)
    component2 = extract_component_id(response2.value, tool_call_extractor)

    assert component2 == "web", (
        f"Turn 2: Expected web component (explicit switch), got {component2}. "
        f"Should honor explicit instruction to switch. Response: {response2.value}"
    )


@pytest.mark.parametrize(
    "scenario_idx",
    [0, 1, 2],
    ids=["affinity", "explicit_switch", "files_context"],
)
def test_multi_turn_batch(
    m_session, descriptive_system_prompt, tool_call_extractor, scenarios_data, scenario_idx
):
    """Test multiple multi-turn scenarios from test data.

    Measures:
    - Affinity: % of turns maintaining expected component when context unchanged
    - Context-Awareness: % of turns correctly switching when instructed
    """
    scenarios = scenarios_data.get("multi_turn", [])
    if scenario_idx >= len(scenarios):
        pytest.skip(f"Scenario {scenario_idx} not in test data")

    scenario = scenarios[scenario_idx]
    turns = scenario["turns"]
    results = []

    for turn_idx, turn in enumerate(turns):
        query = turn["query"]
        expected_component = turn["expected_component"]
        mode = turn.get("mode", "unknown")

        # Build conversational context
        context_lines = []
        for i in range(turn_idx):
            prev_turn = turns[i]
            context_lines.append(
                f"  - Previous query: {prev_turn['query']} "
                f"(used component_{prev_turn['expected_component']})"
            )

        context_str = (
            "\nPrevious interactions:\n" + "\n".join(context_lines)
            if context_lines
            else ""
        )

        prompt = f"""{descriptive_system_prompt}{context_str}

User: {query}

Which tool would you use?"""

        response = m_session.instruct(prompt)
        chosen_component = extract_component_id(response.value, tool_call_extractor)

        is_correct = chosen_component == expected_component
        results.append(
            {
                "turn": turn_idx + 1,
                "mode": mode,
                "query": query,
                "expected": expected_component,
                "chosen": chosen_component,
                "correct": is_correct,
            }
        )

        # Validate routing
        assert is_correct, (
            f"Turn {turn_idx + 1} ({mode}): Expected {expected_component}, "
            f"got {chosen_component}. Query: {query}"
        )

    # Log results
    print(f"\nScenario: {scenario['description']}")
    for result in results:
        status = "✓" if result["correct"] else "✗"
        print(
            f"  {status} Turn {result['turn']} ({result['mode']:10s}): "
            f"expected={result['expected']:10s} got={result['chosen']:10s}"
        )
