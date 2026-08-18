# Copyright IBM Corp. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test Scenario 4: System prompt optimization.

This scenario tests whether detailed system prompts with routing guidance
improve accuracy compared to minimal prompts.

Markers:
- tool_naming_reliability: Part of prefix-based validation benchmark
- e2e: Requires LLM backend
- qualitative: Output quality depends on model behavior
"""

import pytest

from mellea.backends import ModelOption
from mellea.backends.tools import MelleaTool
from mellea.core.base import Component
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
        model_id="mistral:latest", model_options={ModelOption.MAX_NEW_TOKENS: 100}
    )
    yield session
    del session


class SearchComponent(Component[str]):
    """A component that provides a search tool."""

    def __init__(self, component_name: str):
        self.component_name = component_name

    def format_for_llm(self, template_repr):
        component_name = self.component_name

        def search_func(query: str) -> str:
            """Search the {component_name} database."""
            return f"[SEARCH: {component_name}]"

        tool = MelleaTool.from_callable(
            search_func, name=f"component_{component_name}.search"
        )
        return tool


def test_prompt_comparison(
    m_session,
    minimal_system_prompt,
    descriptive_system_prompt,
    tool_call_extractor,
    scenarios_data,
):
    """Compare accuracy with minimal vs. descriptive system prompts.

    Measures:
    - Accuracy with minimal prompt
    - Accuracy with descriptive prompt
    - Improvement from detailed guidance
    """
    single_turn = scenarios_data.get("single_turn", [])
    # Test on all non-ambiguous queries (easy + medium)
    # Ambiguous queries excluded since any answer is acceptable
    test_queries = [
        s for s in single_turn if s["difficulty"] != "ambiguous"
    ]

    if not test_queries:
        pytest.skip("No non-ambiguous queries in test data")

    results_minimal = {"correct": 0, "total": 0, "queries": []}
    results_descriptive = {"correct": 0, "total": 0, "queries": []}

    for query_scenario in test_queries:
        query = query_scenario["query"]
        expected = query_scenario["expected_component"]
        components = query_scenario["components"]

        # Test with minimal prompt
        minimal_full = f"""{minimal_system_prompt}

Query: {query}

Which tool?"""

        response_minimal = m_session.instruct(minimal_full)
        chosen_minimal = tool_call_extractor["extract_component_id"](
            response_minimal.value
        )

        is_correct_minimal = chosen_minimal == expected
        results_minimal["correct"] += int(is_correct_minimal)
        results_minimal["total"] += 1
        results_minimal["queries"].append(
            {
                "query": query[:50],
                "expected": expected,
                "chosen": chosen_minimal,
                "correct": is_correct_minimal,
            }
        )

        # Test with descriptive prompt
        descriptive_full = f"""{descriptive_system_prompt}

Query: {query}

Which tool?"""

        response_descriptive = m_session.instruct(descriptive_full)
        chosen_descriptive = tool_call_extractor["extract_component_id"](
            response_descriptive.value
        )

        is_correct_descriptive = chosen_descriptive == expected
        results_descriptive["correct"] += int(is_correct_descriptive)
        results_descriptive["total"] += 1
        results_descriptive["queries"].append(
            {
                "query": query[:50],
                "expected": expected,
                "chosen": chosen_descriptive,
                "correct": is_correct_descriptive,
            }
        )

    # Calculate metrics
    acc_minimal = (
        results_minimal["correct"] / results_minimal["total"] * 100
        if results_minimal["total"] > 0
        else 0
    )
    acc_descriptive = (
        results_descriptive["correct"] / results_descriptive["total"] * 100
        if results_descriptive["total"] > 0
        else 0
    )
    improvement = acc_descriptive - acc_minimal

    # Print results
    print("\n=== Prompt Comparison ===")
    print(f"Test queries: {results_minimal['total']}")
    print(f"\nMinimal Prompt Accuracy: {acc_minimal:.1f}%")
    print("Results:")
    for q in results_minimal["queries"]:
        status = "✓" if q["correct"] else "✗"
        print(
            f"  {status} {q['query']:50s} "
            f"expected={q['expected']:10s} got={q['chosen']:10s}"
        )

    print(f"\nDescriptive Prompt Accuracy: {acc_descriptive:.1f}%")
    print("Results:")
    for q in results_descriptive["queries"]:
        status = "✓" if q["correct"] else "✗"
        print(
            f"  {status} {q['query']:50s} "
            f"expected={q['expected']:10s} got={q['chosen']:10s}"
        )

    print(f"\nImprovement: {improvement:+.1f} percentage points")
    print(f"Target: ≥0 percentage points (no degradation)")

    # Fair comparison: both prompts have same tools, differ only in routing guidance
    # For well-crafted queries, model may not need explicit guidance (saturated at high accuracy)
    # Validate that guidance doesn't degrade performance
    assert improvement >= 0, (
        f"Improvement {improvement:.1f} percentage points is negative. "
        f"Routing guidance should not degrade tool selection accuracy."
    )
