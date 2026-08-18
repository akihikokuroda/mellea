# Tool Naming Reliability Benchmark — Quick Start

## What This Is

A test suite that validates **prefix-based tool naming** is reliable for production use. When multiple components define identical tool names (e.g., two `search()` functions), prefixes prevent collisions and allow the LLM to pick the correct one.

**Example:** Instead of two `search` tools, you get:
- `component_email.search` (search email database)
- `component_web.search` (search the web)

## Why It Matters

- **Parameter-based routing doesn't work:** Tools dict collapses duplicates; LLM never sees both
- **Prefix-based is the only viable solution:** But does the LLM understand prefixed names?
- **This benchmark proves it works** (or identifies what needs fixing)

## Quick Run

**Start Ollama:**
```bash
ollama serve
```

**Run all tests:**
```bash
uv run pytest test/tool_naming_reliability -m tool_naming_reliability -v
```

**Run specific scenario:**
```bash
uv run pytest test/tool_naming_reliability/test_single_turn.py -v       # Easy cases
uv run pytest test/tool_naming_reliability/test_multi_turn.py -v        # Consistency
uv run pytest test/tool_naming_reliability/test_scaling.py -v -m slow   # Many components
```

## What Gets Tested

| Scenario | Tests | Goal | Target |
|----------|-------|------|--------|
| **Single-Turn** | Can LLM pick the right tool? | Easy, ambiguous, batch accuracy | ≥95% |
| **Multi-Turn** | Does LLM maintain component context? | Affinity, explicit switching | ≥90% / ≥95% |
| **Scaling** | Does accuracy drop with more components? | 2, 3, 5 component levels | ≤10 pt penalty |
| **Prompts** | Does detailed guidance help? | Minimal vs. descriptive prompt | ≥5 pt improvement |

## Test Structure

```
test/tool_naming_reliability/
├── conftest.py                        # Fixtures, markers
├── test_single_turn.py                # Scenario 1: accuracy
├── test_multi_turn.py                 # Scenario 2: consistency
├── test_scaling.py                    # Scenario 3: complexity
├── test_prompt_optimization.py        # Scenario 4: wording
├── fixtures/
│   └── scenarios.json                 # Test queries + expected outputs
└── README.md
```

## Success Criteria (MVP)

All five conditions must be met:

1. ✅ Single-turn accuracy **≥95%**
2. ✅ Multi-turn affinity **≥90%**
3. ✅ Multi-turn context-awareness **≥95%**
4. ✅ Scaling penalty **≤10 percentage points**
5. ✅ Prompt improvement **≥5 percentage points**

If all pass → **Prefix-based approach is production-ready**

If any fail → Document findings and iterate on system prompts or LLM choice

## Interpreting Results

### "Accuracy: 92/100 = 92.0%"
95% target for single-turn. Close; may need:
- More specific system prompt
- Better component descriptions
- Test with higher-quality LLM

### "Penalty: -8.5 percentage points"
Good! Accuracy actually improved with more components (unusual but acceptable).

### "Improvement: +12.3 percentage points"
Excellent! Detailed system prompt helps a lot. Document this for users.

## Key Files

- **Design doc:** `docs/TOOL_NAMING_BENCHMARK_DESIGN.md` (full motivation, metrics, hypothesis)
- **Test suite:** `test/tool_naming_reliability/` (4 scenarios, 15 tests)
- **Test data:** `test/tool_naming_reliability/fixtures/scenarios.json`
- **GitHub discussion:** https://github.com/generative-computing/mellea/discussions/1455

## Next Steps

1. Run tests with default Ollama model (llama2-7b)
2. Interpret results against success criteria
3. If scores are low, adjust system prompts and re-run
4. Generate report: `TOOL_NAMING_BENCHMARK_REPORT.md`
5. Create issue summarizing findings and recommendation

## Troubleshooting

**Tests skipped with "Ollama not accessible"**
- Start Ollama: `ollama serve`
- Tests default to Ollama; other backends can be configured

**Low accuracy scores**
- Check tool name extraction regex in `conftest.py:tool_call_extractor`
- Verify LLM is producing valid tool calls in responses
- Try more detailed system prompts (see `fixtures/scenarios.json`)

**Multi-turn tests failing**
- LLM may not preserve context across turns
- Try shorter conversations (current tests are 2-3 turns)
- Verify `ChatContext` is being used correctly

## References

- **GitHub Discussion #1455:** Problem statement and three proposed solutions
- **PR #1432:** Prefix-based implementation being validated
- **AGENTS.md:** Mellea project guidelines (markers, test structure)
