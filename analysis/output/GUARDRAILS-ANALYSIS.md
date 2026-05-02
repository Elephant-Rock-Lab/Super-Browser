# GUARDRAILS-ANALYSIS — SRC-066

**Source**: `C:\Next AI\ref\guardrails-main`
**Version**: 0.10.0 (Apache 2.0)
**Python**: >=3.10, <4.0
**Core deps**: pydantic >=2, openai >=1.30, litellm, langchain-core, opentelemetry-sdk, tiktoken, jsonschema, lxml

---

## PASS 1 — Project Survey

### 1.1 Directory Structure (abbreviated)

```
guardrails-main/
  guardrails/
    guard.py                          # Guard (synchronous orchestrator)
    async_guard.py                    # AsyncGuard
    validator_base.py                 # Validator base class + registry
    validator_service/
      validator_service_base.py       # Execute, correct, merge validators
      async_validator_service.py
      sequential_validator_service.py
    run/
      runner.py                       # Step-based reask loop
      async_runner.py
      stream_runner.py
      async_stream_runner.py
    schema/
      pydantic_schema.py              # Pydantic -> JSON Schema + validator extraction
      rail_schema.py                  # RAIL XML -> schema
      validator.py                    # JSON Schema structural validation
      parser.py                       # Schema path extraction
      generator.py                    # Example generation from schema
      primitive_schema.py
    classes/
      validation/
        validation_result.py
        validation_summary.py
        validator_logs.py
      validation_outcome.py           # ValidationOutcome dataclass
      execution/                      # GuardExecutionOptions
      history/                        # Call, Iteration, Inputs, Outputs
      output_type.py                  # OutputTypes enum (STRING, DICT, LIST)
      schema/                         # ProcessedSchema
    actions/
      reask.py                        # ReAsk, FieldReAsk, introspection, gather_reasks
      filter.py                       # Filter action
      refrain.py                      # Refrain action
    formatters/
      base_formatter.py               # Abstract formatter
      json_formatter.py               # JSON constrained decoding
    telemetry/
      guard_tracing.py                # OTel span wrapping for Guard calls
      runner_tracing.py               # Step/call-level tracing
      validator_tracing.py
      open_inference.py               # OpenInference span attributes
      common.py
    hub/
      install.py                      # Hub validator installation
      registry.py                     # Local hub registry
    hub_telemetry/
    hub_token/
    cli/                              # Typer CLI (configure, start, create)
    integrations/
      langchain/                      # GuardRunnable, ValidatorRunnable
      llama_index/
      databricks/
    utils/
      parsing_utils.py                # JSON extraction, coerce, prune
      structured_data_utils.py        # OpenAI function-calling schema
      prompt_utils.py
      validator_utils.py
      serialization_utils.py
      ...
    settings.py
    llm_providers.py                  # LiteLLM + OpenAI callable wrappers
    merge.py                          # Diff-based merge for reask results
    types/
      on_fail.py                      # OnFailAction enum
      pydantic.py
      validator.py                    # ValidatorMap type alias
  tests/
  docs/
  pyproject.toml
```

### 1.2 Subsystem Catalog

| # | Subsystem | Key Files | Purpose |
|---|-----------|-----------|---------|
| S1 | **Guard Orchestrator** | `guard.py`, `async_guard.py` | Central facade. Factory methods (`for_pydantic`, `for_string`, `for_rail`, `use`), execution dispatch, server delegation, history management. |
| S2 | **Validator Runtime** | `validator_base.py`, `validator_service/` | Abstract `Validator` class, validator registry, `ValidatorServiceBase` with execute/correct/merge. Async and sequential variants. |
| S3 | **Runner / Reask Loop** | `run/runner.py`, `run/async_runner.py`, `run/stream_runner.py` | Step-based execution: prepare -> call LLM -> parse -> validate -> introspect. Reask loop with budget (`num_reasks`). Stream and async variants. |
| S4 | **Schema Engine** | `schema/pydantic_schema.py`, `schema/rail_schema.py`, `schema/validator.py` | Pydantic model and RAIL XML to JSON Schema conversion. Structural validation against JSON Schema Draft 2020-12. Validator extraction from `Field(json_schema_extra={"validators": [...]})`. |
| S5 | **Output Parsing** | `utils/parsing_utils.py`, `utils/structured_data_utils.py` | JSON extraction from LLM output (code-block aware, regex fallback). Type coercion. Key pruning. OpenAI function-calling tool schema generation. |
| S6 | **Actions (Reask/Filter/Refrain)** | `actions/reask.py`, `actions/filter.py`, `actions/refrain.py` | `FieldReAsk`, `SkeletonReAsk`, `NonParseableReAsk`. Introspection (gather_reasks), merge logic, reask prompt construction. `Filter` and `Refrain` sentinel actions. |
| S7 | **OnFailAction Policy** | `types/on_fail.py`, `validator_service_base.py` | 8 failure policies: REASK, FIX, FIX_REASK, FILTER, REFRAIN, NOOP, EXCEPTION, CUSTOM. Dispatch logic in `perform_correction`. |
| S8 | **Telemetry / Tracing** | `telemetry/` | OpenTelemetry span wrapping for guard execution, steps, calls, validators. OpenInference semconv attributes. OTLP exporter support. |
| S9 | **Hub / Plugin System** | `hub/`, `hub_telemetry/`, `hub_token/` | CLI-based validator installation from Guardrails Hub. Local JSON registry. Remote inference option. JWT authentication. |
| S10 | **History / Observability** | `classes/history/`, `classes/validation_outcome.py` | `Call` -> `Iteration` -> `Inputs`/`Outputs` stack. `ValidationOutcome` with raw output, validated output, reask, validation summaries, error spans. |
| S11 | **Formatters** | `formatters/` | Abstract `BaseFormatter` for constrained decoding. `PassthroughFormatter`, JSON formatter. Wraps LLM callable. |
| S12 | **Integrations** | `integrations/langchain/`, `integrations/llama_index/`, `integrations/databricks/` | LangChain `GuardRunnable`/`ValidatorRunnable`. LlamaIndex guard wrapper. Databricks/MLflow integration. |
| S13 | **CLI / Server** | `cli/`, `guardrails start` | Typer CLI for configure, hub install, server management. Flask-based REST server mode. |
| S14 | **LLM Providers** | `llm_providers.py` | LiteLLM-backed callable wrappers. OpenAI SDK integration. Server-side model detection. |

### 1.3 D-Scores (Depth, Difficulty, Dependencies, Documentation)

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **D1 — Codebase Depth** | 3.5/5 | ~12k lines of core library. Well-structured, modular subsystems. Not a monolith, but some legacy coupling (RC loading in Validator init, `_kwargs` passthrough). |
| **D2 — API Complexity** | 3/5 | The public API is clean (`Guard().use()`, `Guard.for_pydantic()`). Internals are moderately complex (reask loop, streaming chunk accumulation, merge logic). The 8 OnFailAction policies create a matrix of behavior. |
| **D3 — External Dependencies** | 2.5/5 | Heavy dependency surface: OpenAI, LiteLLM, LangChain, OpenTelemetry, lxml, tiktoken, Pydantic, jsonschema, JWT. Hub validators bring their own ML models. |
| **D4 — Documentation Quality** | 3/5 | Good README with examples. Docstrings on public methods. No API reference docs in-repo (hosted externally). Some TODOs and FIXMEs in code indicating unfinished documentation. |

### 1.4 Tier Classification

| Tier | Subsystems | Rationale |
|------|-----------|-----------|
| **Tier 1 — Directly Applicable** | S2 (Validator Runtime), S4 (Schema Engine), S5 (Output Parsing), S7 (OnFailAction Policy), S6 (Actions/Reask) | These map directly to output validation, structured output parsing, and content filtering needs. |
| **Tier 2 — Adaptable** | S1 (Guard Orchestrator), S3 (Runner/Reask Loop), S8 (Telemetry), S10 (History), S11 (Formatters) | The orchestration pattern, reask loop, tracing, and history concepts are transferable but would need adaptation for browser automation context. |
| **Tier 3 — Reference Only** | S9 (Hub/Plugin), S12 (Integrations), S13 (CLI/Server), S14 (LLM Providers) | These are Guardrails-specific infrastructure (Hub marketplace, Flask server, LangChain integration) and provide patterns but not direct reuse. |

---

## PASS 2 — Gap Mapping

### 2.1 Gap #12: Structured Action Results (Output Validation)

**Requirement**: Validate and enforce structured output from browser automation actions. Ensure action results conform to expected schemas.

| Guardrails Capability | Mapping | Reuse Potential |
|-----------------------|---------|-----------------|
| `Guard.for_pydantic(output_class=...)` | Define action result schemas as Pydantic models | **HIGH** — Direct reuse pattern |
| `schema/pydantic_schema.py` | Pydantic model to JSON Schema extraction with validator annotations | **HIGH** — Schema generation |
| `schema/validator.py` | Structural validation of output against JSON Schema Draft 2020-12 | **HIGH** — Schema enforcement |
| `Runner.step()` -> `parse()` -> `validate()` | Parse-then-validate pipeline | **HIGH** — Pipeline pattern |
| `utils/parsing_utils.py` | `extract_json_from_output()`, `parse_fragment()`, `coerce_types()` | **HIGH** — JSON extraction and type coercion |
| `ValidationOutcome` | Container for raw output, validated output, pass/fail, error spans | **HIGH** — Result envelope pattern |
| `OnFailAction` (8 policies) | REASK, FIX, FIX_REASK, FILTER, REFRAIN, NOOP, EXCEPTION, CUSTOM | **HIGH** — Failure policy framework |
| `Validator.validate()` + `_validate()` | Pluggable validation with local/remote inference | **MEDIUM** — Validator contract |

**Recommended Extraction Pattern for SUPER-BROWSER**:

```
Action Result Validation Pipeline (from Guardrails):
1. Define Action result as Pydantic BaseModel
2. Extract JSON Schema + attach validators via Field(json_schema_extra={"validators": [...]})
3. After browser action completes, parse raw output:
   - extract_json_from_output() -> handle code blocks, markdown wrapping
   - coerce_types() -> ensure correct types
   - prune_extra_keys() -> strip schema-foreign fields
4. Schema validation: validate_payload() against JSON Schema
5. Run registered validators (custom or hub)
6. On failure: dispatch via OnFailAction policy
7. Return ValidationOutcome(raw, validated, passed, summaries, error_spans)
```

**Key Files to Study**:
- `guardrails/guard.py` lines 440-484 (`for_string`, `for_pydantic`)
- `guardrails/schema/pydantic_schema.py` (full file)
- `guardrails/schema/validator.py` (full file)
- `guardrails/utils/parsing_utils.py` lines 75-224 (JSON extraction and parsing)
- `guardrails/classes/validation_outcome.py` (full file)

### 2.2 Gap #10: Security Envelope — Output Validation, Content Filtering

**Requirement**: Content filtering and security validation on browser automation outputs. Prevent leakage of sensitive data, validate that scraped content meets safety criteria.

| Guardrails Capability | Mapping | Reuse Potential |
|-----------------------|---------|----------------|
| `Guard.use(validator, on="output")` | Attach validators to output pipeline | **HIGH** — Validator attachment |
| `Guard.use(validator, on="messages")` | Validate input messages (prompt injection defense) | **MEDIUM** — Input validation |
| Hub validators (toxic_language, competitor_check, regex_match, PII) | Pre-built content filters | **MEDIUM** — Conceptual reference (not directly importable without Hub) |
| `ValidatorServiceBase.perform_correction()` | FIX, FILTER, REFRAIN, CUSTOM correction actions | **HIGH** — Post-validation action dispatch |
| `actions/filter.py` / `actions/refrain.py` | Filter removes fields, Refrain returns empty | **HIGH** — Sanitization actions |
| `validator_base.py` -> `_validate()` / `_inference()` | Local or remote ML-based validation | **MEDIUM** — ML validator pattern |
| `validator_base.py` -> streaming validation | `validate_stream()` with chunk accumulation | **MEDIUM** — Stream filtering |
| `Validator.run_in_separate_process` | Sandboxed validator execution | **LOW** — Concept only |
| `validator_base.py` -> `required_metadata_keys` | Metadata requirements for validators | **MEDIUM** — Context-aware validation |

**Recommended Extraction Pattern for SUPER-BROWSER**:

```
Content Filtering Pipeline (from Guardrails):
1. Define security validators extending Validator base:
   - PIIDetector: scan output for PII patterns
   - SensitiveURLFilter: check scraped URLs
   - ContentSafetyValidator: toxic/harmful content detection
   - SchemaConformanceValidator: structural validation
2. Compose into a Guard:
   security_guard = Guard().use(PIIDetector, on_fail=OnFailAction.FILTER)
                           .use(ContentSafetyValidator, on_fail=OnFailAction.REFRAIN)
                           .use(SchemaConformanceValidator, on_fail=OnFailAction.EXCEPTION)
3. After browser action, run: security_guard.validate(llm_output=raw_result)
4. ValidationOutcome tells you what passed, what was filtered
5. Error spans pinpoint exactly where violations occurred
```

**Key Files to Study**:
- `guardrails/validator_base.py` lines 92-340 (Validator class, validate_stream)
- `guardrails/validator_service/validator_service_base.py` lines 73-120 (perform_correction)
- `guardrails/actions/filter.py` and `guardrails/actions/refrain.py`
- `guardrails/types/on_fail.py` (OnFailAction enum)
- `guardrails/guard.py` lines 800-856 (use(), __add_validators)

### 2.3 Gap #7: Agent Orchestration & Facade (Structured Output Parsing)

**Requirement**: Orchestrate browser automation agents with structured output parsing. Provide a facade that coordinates actions and returns well-typed results.

| Guardrails Capability | Mapping | Reuse Potential |
|-----------------------|---------|----------------|
| `Guard` class as facade | Single entry point wrapping LLM + validation | **HIGH** — Facade pattern |
| `Guard.__call__()` / `Guard.parse()` / `Guard.validate()` | Call-flow variants | **HIGH** — API design |
| `Runner` step loop (prepare -> call -> parse -> validate -> introspect) | Orchestrated execution pipeline | **HIGH** — Pipeline pattern |
| `GuardExecutionOptions` | Configurable execution parameters (num_reasks, messages, reask_messages) | **MEDIUM** — Options pattern |
| `Call` / `Iteration` / `Inputs` / `Outputs` history | Execution history tracking | **MEDIUM** — Observability model |
| `Guard.for_pydantic()` + `json_function_calling_tool()` | Structured output via function calling | **MEDIUM** — Schema-driven generation |
| `formatters/base_formatter.py` | Pluggable output formatting | **LOW** — Concept only |
| `Guard.to_runnable()` | LangChain Runnable integration | **LOW** — Integration pattern |
| Reask loop with `introspect()` -> `gather_reasks()` -> `prepare_to_loop()` | Self-correction cycle | **HIGH** — Retry-with-context pattern |

**Recommended Extraction Pattern for SUPER-BROWSER**:

```
Agent Orchestration (from Guardrails):
1. BrowserAgent facade (mirrors Guard):
   - .for_action(action_schema) -> configure for specific browser action
   - .use(validator) -> attach output validators
   - .execute(instruction) -> run action pipeline
   - .validate(raw_output) -> validate without re-execution
2. Step-based execution (mirrors Runner):
   - prepare: resolve selectors, validate inputs
   - call: execute browser action via CDP
   - parse: extract structured data from page
   - validate: run security + schema validators
   - introspect: check for reaskable failures
3. Reask/retry loop:
   - If validation fails with REASK policy
   - Generate corrective instruction (what went wrong)
   - Re-execute with adjusted parameters
   - Budget: num_reasks limit
4. Return ValidationOutcome equivalent:
   - raw_browser_output
   - validated_output (typed)
   - validation_passed
   - error_spans (for UI highlighting)
   - validation_summaries
```

**Key Files to Study**:
- `guardrails/guard.py` (full file — facade pattern)
- `guardrails/run/runner.py` (full file — step loop)
- `guardrails/actions/reask.py` (full file — reask mechanics)
- `guardrails/classes/history/call.py` (execution history model)
- `guardrails/classes/execution/guard_execution_options.py`

---

## 3. Cross-Cutting Patterns Worth Adopting

### 3.1 Validator Registration & Plugin Architecture

The `register_validator(name, data_type)` decorator pattern (in `validator_base.py`) creates a clean plugin system:
- Validators self-register by type (string, list, object, etc.)
- `validators_registry` dict provides lookup by name
- Hub validators auto-import on first use
- **Adopt for SUPER-BROWSER**: Register browser-specific validators (selector validator, URL validator, screenshot validator) by element type.

### 3.2 OnFailAction Policy Matrix

The 8-policy failure handling system is more nuanced than simple pass/fail:

| Policy | Behavior | Browser Automation Analogy |
|--------|----------|---------------------------|
| REASK | Re-prompt LLM for failed field | Retry action with corrective feedback |
| FIX | Apply static fix from validator | Auto-correct selector/value |
| FIX_REASK | Fix, then re-validate and reask if still invalid | Auto-correct, then retry if still broken |
| FILTER | Remove the invalid value | Filter out unsafe content from result |
| REFRAIN | Return empty | Abort action, return nothing |
| NOOP | Pass through unchanged | Log warning but continue |
| EXCEPTION | Raise error | Throw exception to caller |
| CUSTOM | User-defined callback | Custom browser-specific handling |

### 3.3 ValidationOutcome as Universal Result Envelope

The tuple-like `ValidationOutcome` that unpacks as `(raw_output, validated_output, reask, validation_passed, error)` is a clean pattern for separating "what the system produced" from "what passed validation." SUPER-BROWSER should adopt this for every action result.

### 3.4 Streaming Validation with Chunk Accumulation

`Validator.validate_stream()` with `_chunking_function()` accumulates text chunks until a sentence boundary is reached, then validates. This is directly relevant for streaming browser action results or progressive page scraping.

---

## 4. Limitations & Gaps in Guardrails for SUPER-BROWSER

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Guardrails validates *text* (LLM output), not *structured browser state* | Need to extend validation to DOM elements, screenshots, network responses | Create browser-specific Validator subclasses that accept page state |
| No async-native validation for real-time streams | `AsyncGuard` exists but delegates to executor | Build on `async_validate` pattern from `validator_service/` |
| Hub validators require network access and Hub account | Cannot use pre-built content filters offline | Implement custom validators using same base class |
| No schema evolution or versioning | Browser page structures change frequently | Add schema versioning layer on top of Pydantic models |
| Error spans are character-offset based | Need element-level or XPath-based error location for browser context | Extend `ErrorSpan` with DOM-specific location metadata |
| No built-in retry with exponential backoff | `num_reasks` is a flat count | Add backoff strategy to Runner step loop |

---

## 5. Recommended Integration Priority

| Priority | Action | Estimated Effort |
|----------|--------|-----------------|
| P0 | Adopt `ValidationOutcome` as the standard result type for all browser actions | 1-2 days |
| P0 | Implement `OnFailAction` policy enum for browser action failure handling | 0.5 days |
| P1 | Port `parse_llm_output()` + `extract_json_from_ouput()` for browser result parsing | 2-3 days |
| P1 | Port `schema/validator.py` structural validation for action result schemas | 1-2 days |
| P1 | Build Validator base class for browser-specific validators (mirrors `validator_base.py`) | 2-3 days |
| P2 | Port `Runner` step loop as browser action orchestration pipeline | 3-5 days |
| P2 | Implement reask/retry loop with `introspect()` -> `gather_reasks()` pattern | 2-3 days |
| P3 | Adopt OTel tracing pattern from `telemetry/` for action observability | 2-3 days |
| P3 | Build content-filtering validator set (PII, URL safety, content safety) | 3-5 days |

---

## 6. Summary Assessment

Guardrails provides a **mature, well-architected validation framework** that maps strongly to three SUPER-BROWSER gaps:

- **Gap #12 (Structured Action Results)**: Directly applicable. The Pydantic-to-JSON-Schema pipeline, structural validation, type coercion, and `ValidationOutcome` envelope can be ported nearly as-is. The 8-policy `OnFailAction` system provides a rich vocabulary for handling validation failures in browser automation contexts.

- **Gap #10 (Security Envelope / Content Filtering)**: Highly applicable. The `Validator` base class with local/remote inference, the `Guard.use()` compositional API, and the `perform_correction()` dispatch mechanism provide the exact architecture needed for a pluggable content filtering pipeline. Hub validators serve as design references for PII detection, toxicity filtering, and competitor checking.

- **Gap #7 (Agent Orchestration / Structured Output)**: Applicable as architectural reference. The `Guard` facade pattern, `Runner` step-based loop (prepare -> call -> parse -> validate -> introspect), and reask/retry cycle provide a proven orchestration model. The history/iteration tracking provides an observability model.

The library's main limitation for SUPER-BROWSER is its text-centric design — it validates string outputs from LLMs, not structured browser state. All validator logic would need adaptation to accept DOM elements, screenshots, and network responses rather than raw text.
