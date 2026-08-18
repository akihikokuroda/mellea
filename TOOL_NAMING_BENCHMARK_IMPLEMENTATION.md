# Tool Naming Reliability Benchmark — Implementation Summary

**Status:** ✅ Complete (Phase 1 & 2)

**Date:** 2026-08-18

**Objective:** Validate that prefix-based tool naming enables LLMs to reliably call the correct tool when multiple components define identical-named tools.

---

## What Was Built

A comprehensive test suite with 15 tests across 4 scenarios that measures LLM reliability with prefixed tool names.

### Files Created

```
test/tool_naming_reliability/
├── __init__.py                              # Package marker
├── conftest.py                              # Fixtures, markers, test utilities
├── test_single_turn.py                      # Scenario 1: Single-turn accuracy (6 tests)
├── test_multi_turn.py                       # Scenario 2: Multi-turn consistency (5 tests)
├── test_scaling.py                          # Scenario 3: Scaling analysis (4 tests)
├── test_prompt_optimization.py              # Scenario 4: System prompt optimization (1 test)
├── fixtures/
│   └── scenarios.json                       # Test data: 6 single-turn + 3 multi-turn + 3 scaling scenarios
├── README.md                                # Detailed guide
└── ../../TOOL_NAMING_BENCHMARK_DESIGN.md   # Full benchmark design doc (updated)
└── ../../TOOL_NAMING_BENCHMARK_QUICKSTART.md   # Quick reference guide (new)
```

### Test Breakdown

| File | Tests | Scenario | Purpose |
|------|-------|----------|---------|
| `test_single_turn.py` | 6 | Single-Turn Selection | LLM chooses correct tool for explicit & ambiguous queries |
| `test_multi_turn.py` | 5 | Multi-Turn Consistency | LLM maintains component affinity; switches on instruction |
| `test_scaling.py` | 4 | Scaling | Accuracy vs. N components (2, 3, 5) |
| `test_prompt_optimization.py` | 1 | System Prompt Optimization | Minimal vs. descriptive prompt comparison |
| **TOTAL** | **15** | — | — |

---

## Design Highlights

### Markers

Tests are tagged for easy targeting:
- `tool_naming_reliability` — Part of this benchmark
- `e2e` — Requires LLM backend (Ollama)
- `qualitative` — Output quality depends on model
- `slow` — Multi-turn/scaling tests

**Run all:**
```bash
uv run pytest test/tool_naming_reliability -m tool_naming_reliability -v
```

### Test Data (`fixtures/scenarios.json`)

Structured test cases for reproducibility:
- **single_turn:** 6 queries (3 easy, 1 ambiguous, 2 medium)
- **multi_turn:** 3 conversations (affinity, explicit switch, files context)
- **scaling:** 3 levels (2, 3, 5 components with targeted queries)

### Fixtures (`conftest.py`)

Reusable utilities:
- `minimal_system_prompt` — Basic tool listing
- `descriptive_system_prompt` — Detailed descriptions + routing guide
- `scenarios_data` — Loads test data from JSON
- `tool_call_extractor` — Regex-based extraction of tool names from LLM responses
- `mock_search_tools` — Mock search components for testing

---

## How It Works

### Single-Turn Test Flow

```
1. Load scenario from JSON (query, expected_component)
2. Build LLM prompt with system prompt + query
3. Call LLM (Ollama/backend)
4. Extract tool name from response (regex)
5. Extract component_id from tool name (prefix)
6. Assert: component_id == expected_component
```

### Multi-Turn Test Flow

```
1. Turn 1: Query → component_1 (init)
2. Turn 2: Contextual query → component_1 (affinity test)
3. Extract components from both turns
4. Assert: Turn 2 maintains Turn 1's component
```

### Scaling Test Flow

```
For level in [1, 2, 3]:
  Create N components
  For each test query:
    Call LLM with all N components available
    Extract chosen component
    Assert: matches expected
  Calculate accuracy
  Compare accuracy across levels
```

---

## Success Criteria (MVP)

All five must be met for production readiness:

1. **Single-Turn Accuracy ≥95%**
   - Tests: `test_prefix_single_turn_accuracy_batch`
   - Measures: % of easy/medium queries routed correctly
   - Why 95%: Industry standard for LLM tool use

2. **Multi-Turn Affinity ≥90%**
   - Tests: `test_multi_turn_affinity`, `test_multi_turn_batch[affinity]`
   - Measures: % of Turn 2s maintaining Turn 1 component
   - Why 90%: Slightly lower due to context complexity

3. **Multi-Turn Context-Awareness ≥95%**
   - Tests: `test_multi_turn_context_awareness`, `test_multi_turn_batch[explicit_switch]`
   - Measures: % of explicit switches honored
   - Why 95%: If user says "use component X", model should comply

4. **Scaling Penalty ≤10 percentage points**
   - Tests: `test_scaling_penalty`
   - Measures: Accuracy(2 components) - Accuracy(5 components)
   - Why ≤10: Acceptable degradation under increased complexity

5. **Prompt Improvement ≥5 percentage points**
   - Tests: `test_prompt_comparison`
   - Measures: Accuracy(descriptive) - Accuracy(minimal)
   - Why ≥5: Proves system prompts matter; informs user guidance

---

## Key Implementation Details

### Tool Extraction

Components are extracted from LLM responses using regex patterns:

```python
# From response: "I should use component_email.search"
# Pattern: r"component_(\w+)\.search"
# Result: "email"
```

Patterns handled:
- Direct mentions: `component_email.search`
- JSON schemas: `"name": "component_email.search"`
- Tool descriptions in response

### Component Representation

Each test creates `SearchComponent` with a prefixed MelleaTool:

```python
class SearchComponent(Component[str]):
    def format_for_llm(self, template_repr):
        tool = MelleaTool.from_callable(
            search_func,
            name=f"component_{self.component_name}.search"
        )
```

Prefix format: `component_<name>.search`

### Prompt Variants

**Minimal:**
```
You have access to:
- component_email.search
- component_web.search
- component_files.search
```

**Descriptive:**
```
1. component_email.search: Search corporate email database
2. component_web.search: Search public web
3. component_files.search: Search internal file storage

Routing guide:
- Email mentions → use component_email.search
- Web topics → use component_web.search
- Files/documents → use component_files.search
```

---

## Running Tests

### Prerequisites

```bash
ollama serve                    # Start LLM backend
uv sync                        # Install dependencies
```

### Basic Runs

```bash
# All tool naming tests
uv run pytest test/tool_naming_reliability -m tool_naming_reliability -v

# Specific scenario
uv run pytest test/tool_naming_reliability/test_single_turn.py -v
uv run pytest test/tool_naming_reliability/test_multi_turn.py -v
uv run pytest test/tool_naming_reliability/test_scaling.py -m slow -v
uv run pytest test/tool_naming_reliability/test_prompt_optimization.py -v

# Fast collection (no execution)
uv run pytest test/tool_naming_reliability --collect-only -q
```

### Output

Each test prints results in tabular format:

```
test_prefix_single_turn_accuracy_batch:
✓ Find Q1 budget in email      expected=email got=email
✓ Search web for docs          expected=web   got=web
✓ Look for files               expected=files got=files

Accuracy: 3/3 = 100.0%
Target: ≥95%
```

---

## Next Steps

### Phase 3: Run Benchmark

1. **Execute tests** against target LLM(s)
2. **Collect results** (accuracy, consistency, scaling data)
3. **Verify success criteria** (all 5 conditions met?)
4. **Document findings** in `TOOL_NAMING_BENCHMARK_REPORT.md`

### Phase 4: Iterate (If Needed)

If any criterion fails:
1. Adjust system prompts (test with `descriptive_system_prompt` variant)
2. Improve tool descriptions in JSON schema
3. Test with different LLM (larger model, different vendor)
4. Re-run tests and check improvement

### Phase 5: Publish Results

1. Update GitHub discussion #1455 with findings
2. Close with recommendation (prefix-based is/isn't viable)
3. Document production best practices:
   - "Use descriptive system prompts for +X% accuracy"
   - "Avoid >N components to maintain >Y% accuracy"
   - etc.

---

## Design Decisions

### Why Regex for Tool Extraction?

**Trade-off:**
- ✅ Simple, works offline, no parsing dependencies
- ❌ Fragile, may miss unusual LLM response formats

**Alternative considered:** Parse LLM structured output (JSON), but less robust for streaming/edge cases.

**Mitigation:** Multiple regex patterns; graceful fallback to `None` if no match.

### Why Mock Tools?

**Trade-off:**
- ✅ Fast, deterministic, no side effects
- ❌ Doesn't test actual tool execution

**Rationale:** Benchmark measures **tool selection accuracy**, not **tool execution**. Mock tools are sufficient.

### Why Separate Test Files?

**Structure:**
- `test_single_turn.py` — One scenario, easy to debug
- `test_multi_turn.py` — Another scenario
- `test_scaling.py` — Another scenario
- `test_prompt_optimization.py` — Another scenario

**Rationale:** Each scenario has different execution profile (speed, complexity); separate files make targeting/debugging easier.

### Why JSON for Test Data?

**Trade-off:**
- ✅ Externalize test cases, easy to add new scenarios
- ❌ External file adds I/O dependency

**Rationale:** Test data will grow; external file reduces code clutter and enables collaboration (non-developers can add queries).

---

## Limitations

### Known Issues

1. **Tool name extraction is regex-based**
   - Fragile: unusual LLM response formats may not match
   - Mitigation: Multiple fallback patterns; log mismatches

2. **Single LLM model assumption**
   - Current tests default to Ollama (llama2-7b)
   - Results vary by model size/quality
   - Mitigation: Test data designed to support multiple models

3. **Mock tools don't test actual execution**
   - We measure tool selection, not tool correctness
   - Actual execution testing is separate concern
   - Mitigation: Qualify this clearly in results

4. **Multi-turn tests are brief (2-3 turns)**
   - Longer conversations may lose context
   - Mitigation: Extensible; can add longer scenarios

### Not in Scope (Phase 1)

- ❌ List-based tool structure (requires major refactoring)
- ❌ Performance benchmarks (token count, latency)
- ❌ Cross-model comparison (Phase 2)
- ❌ System prompt adversarial testing
- ❌ Error recovery patterns (initial design included; deferred)

---

## Documentation

### For Users

- **TOOL_NAMING_BENCHMARK_QUICKSTART.md** — Quick reference
- **test/tool_naming_reliability/README.md** — Detailed test guide
- **TOOL_NAMING_BENCHMARK_DESIGN.md** — Full design rationale

### For Contributors

- **conftest.py** — Inline docstrings explain fixtures
- **test_*.py** — Module docstrings outline each scenario
- **scenarios.json** — Inline comments explain structure

### For Maintainers

- This document — Implementation summary and decisions
- **TOOL_NAMING_BENCHMARK_DESIGN.md** — Original design (reference)
- GitHub #1455 — Discussion context

---

## Files Changed/Created

```
NEW:
  test/tool_naming_reliability/
  test/tool_naming_reliability/__init__.py
  test/tool_naming_reliability/conftest.py
  test/tool_naming_reliability/test_single_turn.py
  test/tool_naming_reliability/test_multi_turn.py
  test/tool_naming_reliability/test_scaling.py
  test/tool_naming_reliability/test_prompt_optimization.py
  test/tool_naming_reliability/fixtures/scenarios.json
  test/tool_naming_reliability/README.md
  docs/TOOL_NAMING_BENCHMARK_DESIGN.md (created in earlier step)
  TOOL_NAMING_BENCHMARK_QUICKSTART.md
  TOOL_NAMING_BENCHMARK_IMPLEMENTATION.md (this file)

UNCHANGED:
  AGENTS.md (contains test structure requirements; confirmed compatible)
  test/conftest.py (root conftest; our markers don't conflict)
```

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Tests implemented | 15 | ✅ Complete |
| Tests discoverable | 100% | ✅ 15/15 collected |
| Code syntax valid | No errors | ✅ All compile |
| Markers working | Proper collection | ✅ `tool_naming_reliability` filters correctly |
| Test data complete | All scenarios | ✅ 6 + 3 + 3 scenarios in JSON |
| Documentation | 3 guides | ✅ Design + Quickstart + This file |

---

## How to Validate This Implementation

```bash
# 1. Check files exist
ls -la test/tool_naming_reliability/

# 2. Check syntax
uv run python -m py_compile test/tool_naming_reliability/*.py

# 3. Collect tests
uv run pytest test/tool_naming_reliability --collect-only -q

# 4. Run without LLM (should skip/defer on Ollama requirement)
uv run pytest test/tool_naming_reliability -m tool_naming_reliability --collect-only

# 5. With Ollama running, try a single test
# ollama serve &
# uv run pytest test/tool_naming_reliability/test_single_turn.py::test_prefix_single_turn_easy[email_explicit] -v
```

---

## Related Issues

- **GitHub #1455:** Initial discussion on tool naming approaches
- **PR #1432:** Prefix-based implementation being validated by this benchmark
- **PR #1431:** Parameter-based attempt (doesn't work; that's why we need prefix validation)

---

## References

- `docs/TOOL_NAMING_BENCHMARK_DESIGN.md` — Original design doc
- `TOOL_NAMING_BENCHMARK_QUICKSTART.md` — Quick start guide
- `test/tool_naming_reliability/README.md` — Detailed test guide
- `AGENTS.md` — Project test structure requirements
- `test/README.md` — Mellea test organization

---

**Ready for Phase 3 (running tests and collecting data).**
