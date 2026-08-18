# Prefix-Based Tool Naming: LLM Reliability Benchmark

**Objective:** Prove that prefix-based tool naming (e.g., `component_abc123.search`) allows LLMs to reliably call the correct tool when multiple components define identical-named tools.

**Status:** Design document (ready to implement)

**Context:** Parameter-based routing doesn't work because the tools dict collapses duplicate names—the LLM never sees the first tool once the second overwrites it. Prefix-based is the only viable approach; this benchmark validates it's reliable enough for production.

---

## 1. Problem Summary

Multiple components defining tools with identical names cause collisions:

```python
# Component A: search(query: str)
# Component B: search(query: str)  ← overwrites Component A

# Result: LLM only sees ONE 'search' tool, not two
# Solution: Rename to preserve both
#   - component_a.search
#   - component_b.search
```

**Key Questions This Benchmark Answers:**
1. Can LLMs reliably call the correct prefixed tool?
2. Does reliability degrade with more components?
3. Can LLMs maintain component affinity across multi-turn conversations?
4. Are there system prompt strategies that improve accuracy?

---

## 2. Test Design

### Scenario 1: Single-Turn Tool Selection
**Measures:** Can the LLM choose the right prefixed tool in one turn?

**Setup:**
- Create 3 components, each defining identical `search()` tool:
  - `component_email.search` → searches corporate email
  - `component_web.search` → searches the web
  - `component_files.search` → searches file storage
- Provide system prompt describing each component's purpose
- Track which tool the LLM calls

**Test Cases:**

| Query | Expected Tool | Rationale |
|-------|---------------|-----------|
| "Find Q1 budget info in our corporate email" | `component_email.search` | Explicit mention of email |
| "Search the web for Python documentation" | `component_web.search` | Explicit mention of web |
| "Look for files modified last week" | `component_files.search` | Explicit mention of files |
| "Find budget-related documents" | Any (ambiguous) | Should pick one consistently |

**Metrics:**
- **Accuracy:** % of queries routed to correct tool (target: ≥95%)
- **Consistency:** For ambiguous queries, does LLM pick the same tool each time?

---

### Scenario 2: Multi-Turn Consistency
**Measures:** Can the LLM maintain component affinity across multiple turns?

**Setup:**
- 3-turn conversation with same components
- Each turn provides context clues about which component to use
- Track whether LLM remembers the component from prior turns

**Conversation Flow:**

```
Turn 1: "Find emails about Q1 budget"
  → Model calls component_email.search
  → Receives results

Turn 2: "Who sent the most recent one?"
  → Model should STILL use component_email.search (same component)
  → Not switch to component_web or component_files

Turn 3: "Also check the web for Q1 budget coverage"
  → Model should SWITCH to component_web.search
  → Explicit instruction to change source
```

**Metrics:**
- **Affinity (Turn 1→2):** % of queries maintaining same component when context unchanged (target: ≥90%)
- **Context-Awareness (Turn 3):** % of queries correctly switching components when instructed (target: ≥95%)

---

### Scenario 3: Scaling (N Components)
**Measures:** Does accuracy degrade as number of components increases?

**Setup:**
- Run Scenario 1 with increasing tool complexity:
  - Level 1: 2 components × 1 tool = 2 prefixed tools total
  - Level 2: 3 components × 1 tool = 3 prefixed tools total
  - Level 3: 5 components × 1 tool = 5 prefixed tools total
  - Level 4: 5 components × 2 tools = 10 prefixed tools total (e.g., `search` + `filter`)

**Metrics:**
- **Accuracy by Complexity:** Plot accuracy vs. tool count
- **Scaling Penalty:** Accuracy(10 tools) - Accuracy(2 tools) (target: ≤10 percentage points)

---

### Scenario 4: System Prompt Optimization
**Measures:** What wording helps LLMs route correctly?

**Setup:**
- Test two system prompt variants for same components:

**Variant A (Minimal):**
```
You have access to: component_email.search, component_web.search, component_files.search
```

**Variant B (Descriptive):**
```
You have access to the following search tools:
- component_email.search: Search the corporate email database
- component_web.search: Search the public web
- component_files.search: Search internal file storage

When a query mentions email, use component_email.search.
When a query asks about web topics, use component_web.search.
When a query mentions files or documents, use component_files.search.
```

**Test:** Run Scenario 1 queries against both prompts.

**Metrics:**
- **Prompt A Accuracy:** % correct routing with minimal prompt
- **Prompt B Accuracy:** % correct routing with detailed prompt
- **Improvement:** Accuracy(B) - Accuracy(A)

---

## 3. Implementation

### Test Structure

```
test/tool_naming_reliability/
├── conftest.py                       # Shared fixtures, marker setup
├── test_single_turn.py               # Scenario 1
├── test_multi_turn.py                # Scenario 2
├── test_scaling.py                   # Scenario 3
├── test_prompt_optimization.py       # Scenario 4
└── fixtures/
    ├── multi_component_template.py   # Factory for N components
    └── scenarios.json                # Test queries + expected outputs
```

### Key Fixtures

**Multi-Component Template Factory:**
```python
def create_multi_search_template(
    num_components: int,
    component_names: list[str],
) -> TemplateRepresentation:
    """Create template with N components, each defining search() tool.
    
    Each tool is prefixed with component name:
    - component_email.search
    - component_web.search
    - etc.
    """
```

**Tool Call Validator:**
```python
class PrefixedToolCallValidator:
    """Extract and validate tool calls from LLM responses.
    
    Methods:
    - extract_tool_name(response: str) -> str | None
    - extract_component_id(response: str) -> str | None
    - validate_call(response, expected_component) -> bool
    """
```

### Test Markers

```python
@pytest.mark.tool_naming_reliability  # All tool naming tests
@pytest.mark.e2e                      # Requires LLM
@pytest.mark.qualitative              # Output quality check
@pytest.mark.slow                     # Multi-turn can be slow
```

Run specific tests:
```bash
# All tool naming tests
uv run pytest test/tool_naming_reliability -m tool_naming_reliability -v

# Single-turn only
uv run pytest test/tool_naming_reliability/test_single_turn.py -v

# Scaling study
uv run pytest test/tool_naming_reliability/test_scaling.py -m slow -v
```

---

## 4. Success Criteria

### Minimum Viability

- ✅ **Scenario 1 (Single-Turn):** Accuracy ≥95%
  - Proves prefix approach is usable for basic tool selection
  
- ✅ **Scenario 2 (Multi-Turn):** Affinity ≥90%, Context-Awareness ≥95%
  - Proves LLM can track component across turns
  
- ✅ **Scenario 3 (Scaling):** Scaling penalty ≤10 percentage points
  - Proves degradation is acceptable
  
- ✅ **Scenario 4 (System Prompts):** Detailed prompt improves accuracy by ≥5 percentage points
  - Provides user guidance for reliability

### Recommendation Threshold

If all success criteria are met → **Prefix-based approach is production-ready**

Document limitations:
- Works best with explicit system prompts
- Use specific tool descriptions
- Multi-turn accuracy slightly lower (~90%) than single-turn (~95%)

---

## 5. Example Test Cases

### Scenario 1: Single-Turn (Pseudo-Code)

```python
@pytest.mark.tool_naming_reliability
@pytest.mark.e2e
async def test_prefix_single_turn_accuracy_email_component():
    """Test routing accuracy for email search component."""
    backend = OllamaBackend(model_id="llama2-7b")
    
    template = create_multi_search_template(
        num_components=3,
        component_names=["email", "web", "files"],
    )
    
    query = "Find Q1 budget information in our corporate email"
    expected_tool = "component_email.search"
    
    response = await backend.agenerate(
        system_prompt=DESCRIPTIVE_SYSTEM_PROMPT,
        user_prompt=query,
        tools=template.get_tools(),
    )
    
    called_tool = extract_tool_name(response)
    assert called_tool == expected_tool, f"Expected {expected_tool}, got {called_tool}"
```

### Scenario 2: Multi-Turn (Pseudo-Code)

```python
@pytest.mark.tool_naming_reliability
@pytest.mark.e2e
@pytest.mark.slow
async def test_prefix_multi_turn_affinity():
    """Test component affinity across multiple turns."""
    backend = OllamaBackend(model_id="llama2-7b")
    context = ChatContext()
    template = create_multi_search_template(3, ["email", "web", "files"])
    
    # Turn 1: Email context
    response1 = await backend.agenerate(
        system_prompt=DESCRIPTIVE_SYSTEM_PROMPT,
        messages=context.add(Message("user", "Find Q1 budget in email")),
        tools=template.get_tools(),
    )
    tool1 = extract_tool_name(response1)
    assert tool1 == "component_email.search"
    
    # Turn 2: Contextual follow-up (should stay with email)
    response2 = await backend.agenerate(
        system_prompt=DESCRIPTIVE_SYSTEM_PROMPT,
        messages=context.add(Message("assistant", response1)).add(
            Message("user", "Who sent the most recent one?")
        ),
        tools=template.get_tools(),
    )
    tool2 = extract_tool_name(response2)
    assert tool2 == "component_email.search", "Should maintain component affinity"
    
    # Turn 3: Explicit switch to web
    response3 = await backend.agenerate(
        system_prompt=DESCRIPTIVE_SYSTEM_PROMPT,
        messages=context.add(Message("assistant", response2)).add(
            Message("user", "Also check the web for Q1 budget coverage")
        ),
        tools=template.get_tools(),
    )
    tool3 = extract_tool_name(response3)
    assert tool3 == "component_web.search", "Should switch when instructed"
```

### Scenario 3: Scaling (Pseudo-Code)

```python
@pytest.mark.tool_naming_reliability
@pytest.mark.slow
@pytest.mark.parametrize("num_components,num_tools_per", [
    (2, 1),  # 2 tools total
    (3, 1),  # 3 tools total
    (5, 1),  # 5 tools total
    (5, 2),  # 10 tools total
])
async def test_prefix_scaling(num_components, num_tools_per):
    """Test accuracy degradation with increasing tool count."""
    # Create N×M tools
    # Run Scenario 1 queries
    # Assert accuracy ≥ (baseline - 10 percentage points)
```

---

## 6. Test Data: `scenarios.json`

```json
{
  "single_turn": [
    {
      "components": ["email", "web", "files"],
      "query": "Find Q1 budget information in our corporate email",
      "expected_component": "email",
      "difficulty": "easy"
    },
    {
      "components": ["email", "web", "files"],
      "query": "Search the web for Python documentation",
      "expected_component": "web",
      "difficulty": "easy"
    },
    {
      "components": ["email", "web", "files"],
      "query": "Look for files modified last week",
      "expected_component": "files",
      "difficulty": "easy"
    },
    {
      "components": ["email", "web", "files"],
      "query": "Find budget-related documents",
      "expected_component": "any",
      "difficulty": "ambiguous"
    }
  ],
  "multi_turn": [
    {
      "turns": [
        {
          "query": "Find emails about Q1 budget",
          "expected_component": "email"
        },
        {
          "query": "Who sent the most recent one?",
          "expected_component": "email",
          "mode": "affinity"
        },
        {
          "query": "Now check the web for Q1 budget coverage",
          "expected_component": "web",
          "mode": "switch"
        }
      ]
    }
  ]
}
```

---

## 7. System Prompts

**Variant A (Minimal):**
```
You have access to search tools from multiple sources:
- component_email.search
- component_web.search
- component_files.search

Use them to answer questions.
```

**Variant B (Descriptive):**
```
You have access to the following search tools to find information:

1. component_email.search: Search the corporate email database for internal communications, memos, and discussions
2. component_web.search: Search the public web for external information, articles, and resources
3. component_files.search: Search internal file storage for documents, reports, and archives

Routing guide:
- When a query mentions email, internal communications, or asks about company messages → use component_email.search
- When a query asks about web topics, external information, or public knowledge → use component_web.search
- When a query mentions files, documents, archives, or internal storage → use component_files.search
- When ambiguous, prioritize based on the most specific keyword in the query
```

---

## 8. Metrics Definition

### Accuracy

```
Accuracy = (number of correctly routed queries) / (total queries) × 100%
```

**Target:** ≥95%
**Rationale:** LLM tool use is probabilistic; 95% is industry-standard acceptable threshold.

---

### Multi-Turn Affinity

```
Affinity = (turns maintaining expected component) / (total affinity-testing turns) × 100%
```

**Target:** ≥90%
**Rationale:** Slightly lower than single-turn due to context complexity.

---

### Context-Awareness (Explicit Switching)

```
Context_Awareness = (turns successfully switching on instruction) / (total switch-testing turns) × 100%
```

**Target:** ≥95%
**Rationale:** If model is told to switch, it should comply.

---

### Scaling Penalty

```
Scaling_Penalty = Accuracy(10 tools) - Accuracy(2 tools)
```

**Target:** ≤10 percentage points
**Rationale:** Degradation should be gradual, not cliff-like.

---

## 9. Deliverables

### Code
- Test suite in `test/tool_naming_reliability/`
- Fixtures and helpers in `test/fixtures/`
- Updated `test/conftest.py` with markers

### Report: `TOOL_NAMING_BENCHMARK_REPORT.md`
- Raw results per scenario
- Accuracy table by model
- Scaling degradation graph
- System prompt analysis
- Recommendation and caveats

### Data Export
- CSV: `tool_naming_results.csv` (all runs, model, accuracy, consistency)
- PNG: `scaling_curve.png` (accuracy vs. tool count)

---

## 10. Success Definition

**Benchmark passes if:**

1. ✅ Single-turn accuracy ≥95% (Scenario 1)
2. ✅ Multi-turn affinity ≥90% (Scenario 2, part 1)
3. ✅ Context-awareness ≥95% (Scenario 2, part 2)
4. ✅ Scaling penalty ≤10 percentage points (Scenario 3)
5. ✅ Detailed system prompt improves accuracy ≥5 percentage points (Scenario 4)

**Outcome:** Prefix-based approach is **production-ready** with documented best practices.

---

## 11. Timeline

- **Phase 1 (Week 1):** Implement test infrastructure + Scenario 1–2
- **Phase 2 (Week 2):** Run tests on 2–3 models, collect data
- **Phase 3 (Week 3):** Run scaling study (Scenario 3)
- **Phase 4 (Week 4):** System prompt optimization (Scenario 4)
- **Phase 5 (Week 5):** Write report, document recommendations

---

## 12. References

- GitHub Discussion: https://github.com/generative-computing/mellea/discussions/1455
- PR #1432 (prefix-based approach): https://github.com/generative-computing/mellea/pull/1432#issuecomment-5105743324
- Component Tool Routing: `mellea/backends/component_tools.py`
- React Components: `mellea/stdlib/components/react.py`

---

## 13. Next Steps

1. ✅ Approve this design
2. 🔄 Implement Phase 1 (test infrastructure)
3. 🔄 Run initial benchmark
4. 📊 Generate results and recommendation
