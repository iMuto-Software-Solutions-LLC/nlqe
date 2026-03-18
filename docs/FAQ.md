# Query Engine: FAQ & Design Decisions

**Version**: v1.0.0  
**Last Updated**: March 17, 2026  
**Status**: POC Design Phase

## Overview

This document addresses frequently asked questions about the Query Engine design, documents key decisions and their rationale, and identifies items requiring clarification before final product development.

---

## Design Decisions

### 1. Temperature=0 for SQL Generation

**Decision**: Use `temperature=0` for all SQL generation calls (deterministic).

**Rationale**:
- SQL queries should be reproducible - same question should always generate same SQL
- Easier debugging (consistent failures mean consistent errors)
- Better for testing and evaluation (no random variations)
- Ensures deterministic behavior in production

**Alternative Considered**: 
- `temperature=0.5` for slight variation - rejected because variation can introduce subtle bugs

**Implication**: 
- Answer synthesis can use `temperature=0.5` for variety without affecting correctness
- If we need "creative" SQL generation, would need separate consideration

---

### 2. Max 3 Debug Attempts

**Decision**: Allow up to 3 total attempts to fix a failed query.

**Rationale**:
- 1 attempt: Too strict, legitimate errors won't be fixed
- 3 attempts: Balances success rate vs. cost (law of diminishing returns)
- 5+ attempts: User has waited long enough, likely unrecoverable issue
- Configurable: Advanced users/deployments can adjust via `max_debug_attempts`

**Cost Analysis**:
- Each failed query = 1 generation + up to 3 debug attempts = 4 OpenAI calls max
- At $0.03 per 1K tokens, typical query = $0.10-0.30 worst case
- Acceptable for enterprise use, scalable for high volume

**Alternative Considered**:
- Exponential backoff (retry indefinitely) - rejected as too expensive
- 1 attempt only - rejected as too strict

**Implication**:
- Some fixable errors may not be fixed (still need testing to characterize)
- Error summarization is critical (why did all 3 fail?)

---

### 3. Multi-Turn as Core (Not Optional)

**Decision**: Multi-turn conversation is a core feature, designed in from the start.

**Rationale**:
- Real data analysis is inherently conversational
- Users naturally ask follow-up questions with implicit context
- Built in now prevents major refactoring later
- Simpler than bolting on later
- Key differentiator from simple query tools

**Alternative Considered**:
- Single-query only, add multi-turn later - rejected due to refactoring cost

**Implication**:
- Conversation manager is core component, not optional
- Context management is critical to design
- Testing must include multi-turn scenarios

---

### 4. Separate Synthesis Step

**Decision**: Separate "get results" from "describe results" as distinct components.

**Rationale**:
- Different problems: SQL generation ≠ natural language description
- Cleaner separation of concerns
- Each can be optimized independently
- Different output formats become easy (narrative, bullet points, JSON, etc.)
- Can reuse synthesizer for other query types

**Alternative Considered**:
- Combined query+answer - rejected as conflating concerns

**Implication**:
- Two OpenAI calls per query (generation + synthesis)
- Easier to customize answer format later
- Confidence score involves synthesis quality

---

### 5. DuckDB as Query Engine

**Decision**: Use DuckDB for in-process SQL execution.

**Rationale**:
- In-process (no server setup needed)
- Columnar format = fast analytics
- Good support for multiple data formats (parquet, CSV, JSON)
- Excellent pandas integration
- Active community, well-documented
- No additional operational complexity

**Alternative Considered**:
- SQLite (too limited for analytics)
- Postgres (requires server, more complex)
- Snowflake/BigQuery (cloud, higher cost, external dependency)
- DuckDB chosen as sweet spot

**Implication**:
- Datasources must be local/accessible files or DuckDB can ingest them
- No built-in high availability (by design for POC)
- Good foundation for supporting external DBs later

---

### 6. Pydantic for Configuration

**Decision**: Use Pydantic for all configuration and data models.

**Rationale**:
- Type safety and validation
- Environment variable binding built-in
- Serialization/deserialization
- Good error messages
- Already in dependencies

**Implication**:
- Configuration is strongly typed
- Invalid config caught at startup
- Easy to extend with new fields

---

### 7. Result Correctness + Answer Quality Metrics

**Decision**: Measure both query result correctness AND answer quality (not just one).

**Rationale**:
- Result correctness: Did we get the right data?
- Answer quality: Did we explain it well?
- Both matter for user satisfaction
- Could have correct results but confusing explanation
- Could have explanation fail despite correct results

**Alternative Considered**:
- Result correctness only - misses answer quality issues
- Answer quality only - misses incorrect results

**Implication**:
- Evaluation framework must implement both metrics
- Answer quality requires LLM evaluation (cost/latency tradeoff)
- Success requires both metrics to pass

---

### 8. Confidence Score from Multiple Signals

**Decision**: Confidence score combines 6+ signals (not just one).

**Rationale**:
- Single signal is unreliable
- Multiple signals provide better coverage
- Example signals: generation certainty, SQL complexity, result validation, debug attempts, execution success, answer quality
- Weighted combination allows tuning

**Implication**:
- Confidence score is somewhat opaque (multiple inputs)
- Calibration testing is important
- Can be improved over time as patterns emerge

---

## Frequently Asked Questions

### Datasource & Schema Questions

**Q: How is datasource schema discovered?**

A: Via introspection:
- For parquet: DuckDB reads schema automatically
- For CSV: Can infer schema, or user can provide
- For DuckDB: Introspect existing tables
- Schema is used to validate generated SQL before execution

**Q: What datasource formats are supported?**

A: For POC:
- Parquet (primary)
- CSV (secondary)
- DuckDB native connections (for future)

Future support planned:
- PostgreSQL via ADBC
- Snowflake via DuckDB connector
- Other databases as needed

**Q: Can we join across multiple datasources?**

A: For POC: Limited to single datasource at a time. Future versions will support:
- Multiple parquet files in a directory
- DuckDB connections to external DBs
- Cross-datasource joins

**Q: How does schema caching work?**

A: Schema is loaded once when datasource is loaded, then cached in memory. Strategy:
- Simple for POC
- For production: Could add refresh logic with TTL
- Dynamic schema changes might be missed

---

### Example Patterns & Context

**Q: How many examples are sufficient?**

A: Recommendation: 5-10 examples per datasource.
- Too few (<3): Model doesn't generalize well
- Sufficient (5-10): Covers common patterns
- Too many (>20): Token limit exceeded, diminishing returns

Plan: Start with 5-10 curated examples, monitor effectiveness.

**Q: Should examples be auto-discovered or hand-curated?**

A: For POC: Hand-curated (better quality).

Future: Could implement:
- Semantic similarity matching (select most relevant examples)
- User feedback loop (learn from successes/failures)
- Example pool grows over time

**Q: How should examples be structured in YAML?**

A: Proposed format in [DESIGN.md](./DESIGN.md):
```yaml
examples:
  - question: "What was revenue in Q3?"
    sql: "SELECT SUM(amount) FROM transactions WHERE QUARTER(date) = 3"
    explanation: "Uses QUARTER function for temporal filtering"
    category: "aggregation"
```

Tags help with semantic matching.

**Q: Can we version control example patterns?**

A: Yes. Proposed:
- Store in `config/examples.yaml`
- Version in git
- Tie to specific model versions
- Can roll back if examples degrade performance

---

### Accuracy & Testing

**Q: How is confidence score calculated?**

A: See [TESTING.md](./TESTING.md) for detailed formula.

Summary: Weighted combination of:
1. Generation certainty (20%) - From OpenAI logprobs
2. SQL complexity (15%) - Penalize complex queries
3. Result validation (25%) - Do results make sense?
4. Debug attempts (20%) - Were retries needed?
5. Execution success (10%) - Any warnings?
6. Answer quality (10%) - Is synthesis good?

**Q: How will confidence scores be validated/calibrated?**

A: Plan (Phase 3):
1. Measure empirical accuracy: For queries with score 0.8+, what % are actually correct?
2. If >90% are correct: Score is well-calibrated
3. If <80% are correct: Score is overconfident
4. Adjust weightings based on empirical results
5. Regular recalibration as system evolves

**Q: What is acceptable confidence calibration error?**

A: Target: <5% RMS error

Interpretation:
- If system says confidence 0.85, should achieve ~85% actual correctness
- Allow 5% slop (so 0.80-0.90 actual is acceptable)

**Q: What happens to low-confidence queries?**

A: Options (can be configured):
1. Flag for human review
2. Require additional verification step
3. Return results but mark as uncertain
4. Return error and ask for clarification

For POC: Simply note in response.

---

### Query Debugging & Resilience

**Q: When exactly does the debug loop trigger?**

A: Triggers on:
- SQL syntax errors (invalid DuckDB SQL)
- Schema errors (table/column not found)
- Runtime errors (DuckDB execution failed)

Doesn't trigger on:
- Incorrect results (too hard to detect automatically)
- Ambiguous questions (need clarification)
- Timeout/memory errors (usually unrecoverable)

**Q: What makes a good debug suggestion?**

A: Error message + previous context should help AI understand:
- Original question (what was intended?)
- Original SQL (what was attempted?)
- Error message (what went wrong?)
- Previous attempts (what's already been tried?)

**Q: Can we learn from debug failures?**

A: Yes. Future features:
- Log failure patterns
- Improve examples based on failures
- Fine-tune model on failure cases
- Track which error types are recoverable

**Q: Is there a hard limit on debug attempts?**

A: Yes: max 3 attempts (configurable).

Rationale:
- After 3 attempts, likely unrecoverable
- User should be informed to rephrase
- Cost/time limits for patience

Could add adaptive limits:
- Quick retries for schema errors
- Give up fast on syntax errors
- More aggressive on simple patterns

---

### Caching & Performance

**Q: Should we cache query results?**

A: For POC: No caching (dangerous if data changes).

Future: Could implement with caveats:
- Require TTL (expire cache after N minutes)
- User control (opt-in caching)
- Manual refresh option
- Clear cache warnings

Risk: Returning stale data without user knowledge.

**Q: Should we cache generated SQL?**

A: Yes, possibly good idea.

Benefit: If same question asked twice, reuse SQL without API call.

Implementation:
- Hash on: question + datasource_schema
- Store in: file or redis (configurable)
- Invalidate when: schema changes
- Risk: SQL might be suboptimal or outdated

**Q: Should we cache OpenAI responses?**

A: Possible, but limited benefit.

Benefit: Avoid recomputation if same prompt sent.

Risk:
- OpenAI changes models frequently
- Caching responses breaks determinism assumption
- More valuable to cache SQL, not API responses

Recommendation: Skip for POC, revisit if API costs are problematic.

**Q: What about query result caching?**

A: Risky for live data. Better alternatives:
- User application caches (out of scope)
- Materialized views in DuckDB (not currently used)
- Document that users are responsible for freshness

---

### Conversation & Context

**Q: How long should conversation context be?**

A: Strategy (adaptive):
- Include all turns up to token limit
- For long conversations, summarize old turns
- Compress: "Earlier you asked about Q3, which had $1.5M revenue"
- Keep recent turns verbatim

Limit: Fit in OpenAI context window (8K tokens = ~3-5 turns typical).

**Q: How are ambiguous references resolved?**

A: Current plan:
1. Detect ambiguity in user input (pronouns, "that", "which one")
2. Call OpenAI with previous results to disambiguate
3. Example: "Which one?" + previous results → "Which region had the highest sales?"
4. Generate SQL with expanded question

Limitations:
- Only works with unambiguous previous results
- If previous turn had multiple entities, may need clarification

**Q: What if reference can't be resolved?**

A: System should ask for clarification:
```
User: "How did that change?"
System: "I'm not sure what you're comparing. Could you clarify which two time periods?"
```

Better than guessing and getting it wrong.

**Q: Can we maintain context across conversations?**

A: For POC: No (each conversation is independent).

Future: Could implement:
- User-level context (remember patterns across conversations)
- Document-level context (relate to previous documents)
- But requires careful design to avoid hallucination

---

### Deployment & Operations

**Q: Self-hosted vs cloud service?**

A: For POC: Python library (self-hosted by user).

Rationale:
- Simpler initial release
- User controls data (privacy)
- No ops burden on us
- Can evolve to cloud service later

Future: Could offer:
- Cloud API
- Managed deployment
- SaaS version

**Q: How are API keys managed?**

A: Environment variables via `.env` file.

For production, recommend:
- Use secrets management (AWS Secrets Manager, HashiCorp Vault, etc.)
- Never commit keys to git
- Rotate keys regularly

**Q: Rate limiting strategy?**

A: For POC: None (assuming single-user).

For production:
- Token-level rate limits (OpenAI enforces)
- Query-level rate limits (throttle queries to avoid overload)
- Cost controls (alert if usage spikes)

**Q: What about monitoring & observability?**

A: For POC: Logging to stdout.

For production:
- Structured logging (JSON)
- Error tracking (Sentry)
- Metrics (Prometheus)
- Traces (OpenTelemetry)

Recommended: Instrument from the start.

---

### Design Tradeoffs

**Q: Why not use GPT-3.5 instead of GPT-4?**

A: For POC: Using GPT-4 (better accuracy for SQL).

Tradeoff:
- GPT-4: More expensive, better accuracy (target)
- GPT-3.5: Cheaper, lower accuracy (fallback for cost-conscious users)

Future: Could offer both, let users choose.

**Q: Why is multi-turn context so important?**

A: Real-world usage patterns:
- Users start with high-level question
- Dig deeper with follow-ups
- "What was revenue?" → "Which region?" → "How did it change?"

Single-query mode ignores this natural flow. Multi-turn is table stakes.

**Q: Why not just prompt-engineer our way to success?**

A: Some truths:
- Prompt engineering helps but has limits
- Model capability is the bottleneck (not prompts)
- Few-shot examples help, but not magic
- Need solid error handling to recover from mistakes

Strategy: 
- Good prompts (important but not sufficient)
- Examples (improve generation, don't fix fundamental issues)
- Debug loop (recover from common errors)
- Evaluation (measure actual performance)

**Q: What if results are contradictory?**

A: Possible issues:
1. Question was ambiguous (could mean multiple things)
2. Data has quality issues
3. SQL is correct but user expectation was wrong

Handling:
- Return results with confidence score
- Explain what query was executed (show the SQL)
- Let user verify against data directly
- Document any data quality issues found

---

## Open Questions Requiring Clarification

### Before Phase 2 Start

These should be clarified with stakeholders:

1. **Example Pattern Format**
   - Q: Should examples be curated manually or auto-discovered?
   - Current assumption: Hand-curated in YAML
   - Need: Confirm approach, define curation process

2. **Datasource Introspection**
   - Q: Will datasource introspection be a separate tool or integrated?
   - Current assumption: Integrated in Phase 2
   - Need: Confirm if separate tool exists, integration plan

3. **Data Privacy**
   - Q: What are data handling requirements?
   - Current assumption: User is responsible (library doesn't transmit data)
   - Need: Confirm if any data can be sent to OpenAI, audit requirements

4. **Cost Controls**
   - Q: Budget limit for API costs?
   - Current assumption: Optimized but not minimized
   - Need: Confirm if cost is hard constraint

5. **Production Readiness**
   - Q: What are production SLAs?
   - Current assumption: POC/research tool, not mission-critical
   - Need: Clarify if this changes after initial release

### Before Phase 3 Start

6. **Golden Datasets**
   - Q: Should golden datasets be part of repo or external?
   - Current assumption: Part of repo in `fixtures/`
   - Need: Confirm storage, versioning strategy

7. **Accuracy Targets**
   - Q: Are >85% accuracy targets realistic?
   - Current assumption: Depends on query complexity
   - Need: Actual targets per query category

8. **Evaluation Frequency**
   - Q: How often should evaluation run?
   - Current assumption: On-demand, nightly in CI
   - Need: Confirm if needed for every commit

### Before Phase 4 Start

9. **PyPI Release**
   - Q: Public release immediately or private/beta first?
   - Current assumption: Public 0.1.0
   - Need: Confirm release strategy

10. **Support Model**
    - Q: Who supports users? What SLA?
    - Current assumption: GitHub issues, async support
    - Need: Confirm support plan

---

## Decision Log

| Decision | Date | Status | Rationale |
|----------|------|--------|-----------|
| Temperature=0 for SQL generation | 2026-03-17 | Approved | Determinism, testability |
| Max 3 debug attempts | 2026-03-17 | Approved | Cost/success balance |
| Multi-turn as core feature | 2026-03-17 | Approved | Reflects real usage |
| Separate synthesis step | 2026-03-17 | Approved | Clean separation |
| DuckDB as executor | 2026-03-17 | Approved | In-process, flexible |
| Pydantic for config | 2026-03-17 | Approved | Type safety, validation |
| Result+Quality metrics | 2026-03-17 | Approved | Comprehensive measurement |
| Multiple signals for confidence | 2026-03-17 | Approved | Robust estimation |

---

## Related Documentation

- [DESIGN.md](./DESIGN.md) - Design philosophy and goals
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical implementation
- [TESTING.md](./TESTING.md) - Testing and evaluation
- [API.md](./API.md) - Public API reference
- [ROADMAP.md](./ROADMAP.md) - Implementation timeline
