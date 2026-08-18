# Tool Naming Reliability Benchmark

Validates that prefix-based tool naming (`component_abc123.search`) allows LLMs to reliably call the correct tool when multiple components define identical-named tools.

## Overview

When multiple components in a template define tools with identical names (e.g., two `search()` functions), naming collisions must be resolved. This benchmark measures whether **prefix-based naming** is reliable enough for production use.

**Context:** Parameter-based routing was attempted but doesn't work because the tools dict collapses duplicate names—the LLM never sees the first tool once the second overwrites it. Prefix-based is the only viable approach.

## Scenarios

### Scenario 1: Single-Turn Selection (`test_single_turn.py`)

**Measures:** Can the LLM choose the correct prefixed tool in one turn?

- **Easy cases:** Explicit keywords guide selection
  - "Find Q1 budget in email" → `component_email.search`
  - "Search the web for docs" → `component_web.search`
- **Ambiguous cases:** No clear hint; any component acceptable if consistent

**Target:** ≥95% accuracy

### Scenario 2: Multi-Turn Consistency (`test_multi_turn.py`)

**Measures:** Can the LLM maintain component affinity across turns?

- **Affinity:** Model stays with same component when context doesn't change
  - Turn 1: "Find emails about budget" → email
  - Turn 2: "Who sent it?" → email (SAME)
- **Context-Awareness:** Model switches components when explicitly instructed
  - Turn 1: "Find emails..." → email
  - Turn 2: "Now check the WEB..." → web (SWITCH)

**Target:** Affinity ≥90%, Context-Awareness ≥95%

### Scenario 3: Scaling (`test_scaling.py`)

**Measures:** Does accuracy degrade as component count increases?

- Level 1: 2 components
- Level 2: 3 components
- Level 3: 5 components

**Target:** Scaling penalty ≤10 percentage points

### Scenario 4: System Prompt Optimization (`test_prompt_optimization.py`)

**Measures:** What wording helps LLM routing accuracy?

- **Minimal prompt:** Basic tool list
- **Descriptive prompt:** Detailed descriptions + routing guidance

**Target:** Descriptive prompt improves accuracy by ≥5 percentage points

## Running Tests

Run all tool naming reliability tests:

```bash
uv run pytest test/tool_naming_reliability -m tool_naming_reliability -v
```

Run specific scenario:

```bash
# Single-turn only
uv run pytest test/tool_naming_reliability/test_single_turn.py -v

# Multi-turn only
uv run pytest test/tool_naming_reliability/test_multi_turn.py -v

# Scaling (slow)
uv run pytest test/tool_naming_reliability/test_scaling.py -m slow -v

# Prompt optimization
uv run pytest test/tool_naming_reliability/test_prompt_optimization.py -v
```

## Test Data

Test scenarios are defined in `fixtures/scenarios.json`:

- **single_turn:** Array of single-turn queries with expected component
- **multi_turn:** Array of multi-turn conversations with expected components
- **scaling:** Array of scaling levels with increasing component counts

## Markers

- `tool_naming_reliability` — Part of this benchmark
- `e2e` — Requires LLM backend (Ollama)
- `qualitative` — Output quality depends on model behavior
- `slow` — Multi-turn and scaling tests can be slow

## Interpreting Results

### Success Criteria (MVP)

All of these must pass:

1. **Single-turn accuracy ≥95%** — LLM can pick the right tool
2. **Multi-turn affinity ≥90%** — LLM maintains component context
3. **Multi-turn context-awareness ≥95%** — LLM respects explicit switches
4. **Scaling penalty ≤10 percentage points** — Degradation is acceptable
5. **Prompt improvement ≥5 percentage points** — Detailed prompts help

### What to Do If Tests Fail

**Low single-turn accuracy (<95%)**
- Check that component names in prompts are clear
- Try adding more specific descriptions in system prompt
- Verify LLM is extracting tool names correctly from response

**Low multi-turn affinity (<90%)**
- Model may not be tracking context well
- Try simpler component names or more explicit context
- May indicate multi-turn context management needs improvement

**High scaling penalty (>10 percentage points)**
- More components confuse the model
- Consider limiting template complexity
- Document that max N components depends on model quality

**Low prompt improvement (<5 percentage points)**
- Detailed prompts may not matter for this model
- Both prompts may be inherently confusing
- Task may require system prompts to improve further

## Limitations

- Tests assume tool names follow pattern `component_<name>.search`
- Component extraction via regex; fragile for unusual response formats
- Accuracy depends heavily on LLM model and size
- Multi-turn tests assume sequential turns; no branching logic

## References

- Design doc: `docs/TOOL_NAMING_BENCHMARK_DESIGN.md`
- GitHub discussion: https://github.com/generative-computing/mellea/discussions/1455
- PR #1432: Prefix-based approach implementation
- Component tools: `mellea/backends/component_tools.py`
