# Research — Phase 0 (Iteration 2)

Phase 0 captures the decisions that fall out of the Iter-2 handout + Iter-1 constitution + conventions §10 (context engineering). Each decision continues the Iter-1 numbering (D1–D10) so the full product history reads linearly.

## D11. LLM provider: Anthropic Claude (default), swappable via `.env`

**Decision:** Anthropic Claude for all three chains. `claude-haiku-4-5-20251001` for `check_red_flags` and `fact_of_the_day`; `claude-sonnet-4-6` for `doctor_summary`. Model IDs are read from `.env` (`LLM_MODEL_FAST`, `LLM_MODEL_QUALITY`) so switching providers is one file edit.

**Rationale:**
- Conventions §10 Iter-2 targets specifically reference Anthropic prompt caching (≥70% hit on red-flag). Using Anthropic natively keeps that measurement honest.
- Haiku 4.5 is fast (sub-second TTFT) and cheap — the right tool for classification.
- Sonnet 4.6 is the right tool for summarisation under strict "restate only" constraints. Haiku tends to over-summarise and occasionally adds editorial glue.
- `init_chat_model` + the `langchain-anthropic` / `langchain-openai` / `langchain-google-genai` packages make provider swap a single import away. Handout stretch goal is satisfied.

**Alternatives considered:**
- **OpenAI gpt-4o-mini** — fine, slightly cheaper, but we would lose Anthropic prompt caching, which §10 commits to measuring.
- **Groq (Llama)** — fastest, but weakest at strict-instruction summarisation; the "restate only recorded" rule fails more often.
- **Local Ollama** — cheapest but slowest; latency would blow the 5s red-flag budget.
- **Single model (all Haiku)** — rejected after user review: summaries were visibly worse in a spike test.

**Trigger to revisit:** Iter 5 when Langfuse lands and lets us A/B providers with real metrics.

## D12. LangChain primitives only — no agent, no memory, no RAG

**Decision:** Each chain is `PromptTemplate | ChatModel | OutputParser`, composed with `|`. No `AgentExecutor`, no `ConversationBufferMemory`, no `VectorStore` yet.

**Rationale:**
- Handout §07 explicitly says "LangChain, basics only" and "No agents, memory or RAG yet".
- Iter 3 adds RAG; Iter 4 adds the agent. Adding either now would conflict with those iterations' scope.
- Simpler primitives make the chains easier to inspect and test.

**Alternatives considered:** LangGraph — overkill for three independent chains; it is reserved for Iter 4's agent.

## D13. Prompt-cache strategy: stable prefix / volatile suffix per chain

**Decision:** Every chain splits its prompt in two:

| Chain | Cacheable stable prefix | Volatile suffix |
|---|---|---|
| `check_red_flags` | System prompt + 5-category dictionary + positive/negative examples + Pydantic format instructions | `{reason_text}` |
| `fact_of_the_day` | System prompt + content rules (no conditions, no treatments, ≤2 sentences) + example tone | `{previous_fact}` (may be empty) |
| `doctor_summary` | System prompt + "restate only recorded" rules + ≤120-word rule + output shape | `{patient_profile_json, today_reason, past_visits_json}` |

Anthropic cache-control marker is applied at the boundary.

**Rationale:**
- Conventions §10 is explicit about this split. It is the Iter-2 measurable commitment.
- The stable prefix is identical byte-for-byte across calls → cache hits.
- The volatile suffix is the only place PHI can appear — audit focus narrows to one block per chain.

**Targets** (SC-006, SC-007 in spec.md):
- Red-flag: ≥70% cache hit after warm-up (20 calls), ≤2,000 input tokens p95.
- Summary: ≥90% cache hit after warm-up, ≤4,000 input tokens p95.
- Fact of the Day: cache hit less critical (low volume); ≤3,000 input tokens p95.

**Alternatives considered:** Single blended prompt (simplest but burns cache every call); LangChain `CachedPromptTemplate` (doesn't speak Anthropic's cache control header natively).

## D14. Output parsing: Pydantic for red-flag, string for Fact and summary

**Decision:**
- `check_red_flags` → `with_structured_output(RedFlagResult)` where `RedFlagResult(red_flag: bool, category: Literal[...] | None, why: str)`.
- `fact_of_the_day` → `StrOutputParser()`; caveat appended by backend code.
- `doctor_summary` → `StrOutputParser()`; label + raw notes added by backend code.

**Rationale:**
- Red-flag output drives server-side branching. It MUST be machine-readable. Pydantic parser rejects malformed output → triggers fail-closed path (FR-015).
- Summary and Fact are pure display text. Structuring them would add ceremony with no gain this iteration (the stretch goal in handout §11 upgrades summary to Pydantic — deferred).

**Alternatives considered:** JSON mode (provider-specific, less portable); regex parsing (fragile).

## D15. Fail modes

**Decision:**
- `check_red_flags` fails **closed**: any exception (timeout, HTTP error, parse error, token-budget overrun) → `RuleError("RED_FLAG_CHECK_UNAVAILABLE", ...)` → HTTP 503, no appointment created.
- `fact_of_the_day` fails **open**: any exception → fixed fallback fact + caveat, HTTP 200. The patient home screen never breaks.
- `doctor_summary` fails **open**: any exception → `summary = "Summary unavailable. See the notes below."` + full raw notes rendered, HTTP 200. The doctor never loses access to the notes.

**Rationale:**
- Red-flag is a safety check. Silently booking when the check failed is the exact failure mode the brief §05 forbids.
- Fact of the Day is entertainment-tier UX. A hard failure here would hurt trust for zero safety gain.
- Summary is a convenience view. The full raw notes are the authoritative record; the summary is additive. Failing open is safe because the doctor sees the same notes the summary would have drawn from.

**Alternatives considered:** Retry with backoff on red-flag — rejected because it extends the booking latency beyond the budget and still has to fail somewhere.

## D16. Urgent cases: dedicated table, not a flag on `Appointment`

**Decision:** New `urgent_case` table. The link to `Appointment` is nullable.

**Rationale:**
- A red flag may be raised on a reason whose booking is *refused* by the rules (e.g. surgery session). There is no `Appointment` row to flag. The urgent case must still exist for Staff.
- Staff workflow is "work the urgent list, click Mark seen". That's a filter on `urgent_case.seen_at IS NULL`, cleanly indexed. Doing it on `Appointment` would need a join and a composite condition.
- Audit trail: the case is persisted even after Mark seen. The Appointment may be cancelled later; the urgency record outlives it.

**Alternatives considered:**
- `Appointment.urgent: bool` + `Appointment.urgent_seen_at` — loses the refused-booking case.
- Separate `urgent_case` as a view — same problem; the row has to physically exist when there is no appointment.

## D17. Four new refusal codes added to conventions §2

**Decision:** The contract grows from 17 to 21 codes:

| Code | Meaning | Added by |
|---|---|---|
| `REASON_REQUIRED` | `POST /appointments` missing or empty `reason` | Iter 2 R3 |
| `REASON_TOO_LONG` | `reason` > 300 characters | Iter 2 R3 |
| `NOTE_REQUIRED` | `POST /appointments/{id}/complete` missing `doctor_note` | Iter 2 R2 |
| `RED_FLAG_CHECK_UNAVAILABLE` | Red-flag chain failed (timeout, API, parse) | Iter 2 R4 |

**Rationale:**
- Reason codes are the public contract (D10). Each new failure mode needs its own code so Iter-4's agent and Iter-6's MCP clients can branch on it.
- The four codes are stable from now on. Renaming triggers a constitution amendment (per Principle IV).

**Alternatives considered:**
- Reuse existing codes — rejected because `INVALID_START_TIME` (etc.) describe booking rules; infra and validation failures are a different class.
- Return bare HTTP status without a code — rejected; breaks the §2 contract that *every* refusal has a code.

## D18. Observability: structured logs now, Langfuse in Iter 5

**Decision:** Each LLM call emits a single structured log line:

```
{chain, provider, model, input_tokens, output_tokens, cache_read_tokens, latency_ms, cache_hit, outcome}
```

No PHI. No prompt content. Logged via standard Python logging; shows up in `docker compose logs backend`.

**Rationale:**
- Enables SC-006 (red-flag p95 token count) and SC-007 (cache-hit rate) to be verified from logs alone, no new infra.
- Langfuse is Iter 5's problem. Doing it now means configuring an extra service for one iteration's worth of data.

**Alternatives considered:** Langfuse now — rejected as scope creep; reserved slot in `docker-compose.yml` is enough.

## Open questions

None at Phase 0. Any clarifications surfaced during implementation route to `/speckit-clarify` per CLAUDE.md.
