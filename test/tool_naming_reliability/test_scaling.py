# Copyright IBM Corp. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test Scenario 3: Scaling (N components, M tools).

This scenario measures whether accuracy degrades as the number of components
and tools increases.

Metrics:
- Accuracy by complexity level
- Scaling penalty: Accuracy(N=5) - Accuracy(N=2)
- Target: Scaling penalty ≤10 percentage points

Markers:
- tool_naming_reliability: Part of prefix-based validation benchmark
- e2e: Requires LLM backend
- qualitative: Output quality depends on model behavior
- slow: Scaling tests require multiple queries
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
    pytest.mark.slow,
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
        self.component_name = component_name

    def format_for_llm(self, template_repr):
        component_name = self.component_name

        def search_func(query: str) -> str:
            """Search the {component_name} database."""
            return f"[SEARCH: {component_name} found results]"

        tool = MelleaTool.from_callable(
            search_func,
            name=f"component_{component_name}.search",
        )
        return tool


@pytest.mark.parametrize(
    "level,num_components,components",
    [
        (1, 2, ["email", "web"]),
        (2, 3, ["email", "web", "files"]),
        (3, 5, ["email", "web", "files", "slack", "drive"]),
    ],
    ids=["level1_2comp", "level2_3comp", "level3_5comp"],
)
def test_scaling_accuracy(
    m_session, descriptive_system_prompt, tool_call_extractor, scenarios_data,
    level, num_components, components
):
    """Test accuracy at different scaling levels.

    Measures accuracy for N components.
    """
    scaling_scenarios = scenarios_data.get("scaling", [])

    # Find the scenario matching this level
    scenario = None
    for s in scaling_scenarios:
        if s["level"] == level:
            scenario = s
            break

    if scenario is None:
        pytest.skip(f"No scaling scenario for level {level}")

    test_queries = scenario["test_queries"]
    correct = 0
    total = 0
    results = []

    # Build component list string for the prompt
    component_list = ", ".join([f"component_{c}" for c in components])

    for query_scenario in test_queries:
        query = query_scenario["query"]
        expected_component = query_scenario["expected_component"]

        prompt = f"""{descriptive_system_prompt}

Available components: {component_list}

Query: {query}

Which component should I use?"""

        response = m_session.instruct(prompt)
        chosen_component = tool_call_extractor["extract_component_id"](response.value)

        is_correct = chosen_component == expected_component
        correct += int(is_correct)
        total += 1

        results.append(
            {
                "query": query[:40],
                "expected": expected_component,
                "chosen": chosen_component,
                "correct": is_correct,
            }
        )

    accuracy = (correct / total * 100) if total > 0 else 0

    print(f"\n=== Level {level} ({num_components} components) ===")
    print(f"Testing with components: {component_list}\n")

    for result in results:
        status = "✓" if result["correct"] else "✗"
        chosen = result['chosen'] or "None"
        print(
            f"{status} {result['query']:40s} "
            f"expected={result['expected']:10s} "
            f"got={chosen:10s}"
        )

    print(f"\nAccuracy: {correct}/{total} = {accuracy:.1f}%")

    # Assert minimum accuracy (lower threshold for scaling tests)
    assert accuracy >= 40, (
        f"Level {level}: Accuracy {accuracy:.1f}% is too low. Results: {results}"
    )


def test_scaling_penalty(
    m_session, descriptive_system_prompt, tool_call_extractor, scenarios_data
):
    """Test scaling penalty: measure accuracy degradation as components increase.

    Scaling penalty = Accuracy(N=5) - Accuracy(N=2)
    Target: ≤10 percentage points

    This test runs scaling tests across levels and compares the results.
    """
    scaling_scenarios = scenarios_data.get("scaling", [])
    if len(scaling_scenarios) < 2:
        pytest.skip("Need at least 2 scaling scenarios to compute penalty")

    accuracies = {}

    for scenario in scaling_scenarios:
        level = scenario["level"]
        components = scenario["components"]
        test_queries = scenario["test_queries"]

        correct = 0
        for query_scenario in test_queries:
            query = query_scenario["query"]
            expected = query_scenario["expected_component"]

            prompt = f"""{descriptive_system_prompt}

Query: {query}

Available: {', '.join([f'component_{c}' for c in components])}

Which component?"""

            response = m_session.instruct(prompt)
            chosen = tool_call_extractor["extract_component_id"](response.value)

            if chosen == expected:
                correct += 1

        accuracy = (correct / len(test_queries)) * 100
        accuracies[level] = accuracy

    # Calculate penalties
    if 1 in accuracies and 3 in accuracies:
        penalty = accuracies[1] - accuracies[3]
        print(f"\n=== Scaling Penalty ===")
        print(f"Level 1 (2 components):  {accuracies[1]:.1f}%")
        print(f"Level 3 (5 components):  {accuracies[3]:.1f}%")
        print(f"Penalty:                 {penalty:.1f} percentage points")
        print(f"Target:                  ≤10 percentage points")

        # For initial benchmark, just log the penalty
        # (Allows baseline establishment before requiring threshold)
        pytest.skip(
            f"Scaling penalty: {penalty:.1f}% (baseline measurement, not enforced)"
        )
