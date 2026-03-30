# NLQE: Testing & Evaluation Strategy

**Version**: v1.0.0  
**Last Updated**: March 17, 2026  
**Status**: POC Testing Framework Design

## Overview

This document defines the comprehensive testing strategy for NLQE, including unit tests, integration tests, and an evaluation framework for measuring accuracy and confidence. See [DESIGN.md](./DESIGN.md) for context on the overall system.

---

## Testing Approach

### Testing Pyramid

```
        ▲
       /│\
      / │ \
     /  │  \          Evaluation Tests (Golden Datasets)
    /   │   \         - Accuracy metrics
   /    │    \        - Answer quality
  ┌─────┼─────┐       - Confidence calibration
  │   E │     │       
  ├─────┼─────┤  Integration Tests (End-to-End Flows)
  │     I     │  - Full query pipeline
  ├─────┼─────┤  - Multi-turn conversations
  │           │  - Error recovery
  └───────────┘
        ▲
       /│\          Unit Tests (Components)
      / │ \         - Context building
     /  │  \        - SQL validation
    /   │   \       - Result parsing
   /    │    \      - Error handling
  └─────┴─────┘
        Base
```

### Test Categories

**Unit Tests** (most numerous):
- Test individual components in isolation
- Mock external dependencies (OpenAI, DuckDB)
- Fast execution (milliseconds per test)
- High coverage target: >80%

**Integration Tests** (medium number):
- Test component interactions
- Use real DuckDB and mock OpenAI
- Test real error paths and recovery
- Coverage: key flows and edge cases

**Evaluation Tests** (ongoing):
- Test against golden datasets
- Measure accuracy, answer quality, confidence
- Requires real OpenAI API
- Run periodically, not on every commit

---

## Unit Testing Strategy

### Context Building Tests

**Responsibility**: Verify context assembly is correct

**Test Cases**:
- ✓ Schema is loaded correctly
- ✓ Examples are selected appropriately
- ✓ Context fits within token limits
- ✓ Multi-turn history is included
- ✓ Conversation context is compressed correctly

**Sample Assertions**:
- Context string contains all table names
- Example SQL patterns are present
- Token count is under limit
- Previous turns are included in order

### OpenAI Client Tests

**Responsibility**: Verify API communication works

**Test Cases** (with mocked responses):
- ✓ Request is formatted correctly
- ✓ SQL is extracted from response
- ✓ Parameters are passed correctly (model, temperature, tokens)
- ✓ Retries on rate limit
- ✓ Parses error responses appropriately

**Mock Strategies**:
- Mock successful SQL generation
- Mock malformed responses (invalid JSON)
- Mock rate limit errors (429)
- Mock API errors (500)

### DuckDB Executor Tests

**Responsibility**: Verify query execution and validation

**Test Cases**:
- ✓ SQL syntax validation (accepts valid, rejects invalid)
- ✓ Schema validation (detects missing tables/columns)
- ✓ Safety validation (blocks DROP, DELETE, etc.)
- ✓ Query execution with valid SQL
- ✓ Timeout protection (long queries fail safely)
- ✓ Result parsing (converts results to dicts)

**Test Data**:
- Small in-memory datasets
- Known schema and results
- Various data types (int, string, decimal, date)

### Conversation Manager Tests

**Responsibility**: Verify conversation state management

**Test Cases**:
- ✓ History is stored correctly
- ✓ Reference expansion works (with mocked OpenAI)
- ✓ Context string is built appropriately
- ✓ Multiple turns maintain coherence
- ✓ Clear() resets state

**Test Scenarios**:
- Single query (no history)
- Multiple independent queries
- Follow-up with ambiguous reference
- Clear and start new conversation

### Answer Synthesis Tests

**Responsibility**: Verify natural language generation

**Test Cases** (with mocked OpenAI):
- ✓ Input (results + question) formatted correctly
- ✓ Response is parsed correctly
- ✓ Confidence score is calculated
- ✓ Multiple output formats supported

**Validation**:
- Answer mentions key values from results
- Answer length is reasonable
- Confidence score is in valid range (0.0-1.0)

---

## Integration Testing Strategy

### End-to-End Query Flow

**Scenario**: User asks a single query

**Setup**:
- Load a real datasource (small parquet file with known data)
- Mock OpenAI to return known-good SQL

**Execute**:
- Call QueryEngine.query(question)
- Verify complete flow: context → SQL → execute → answer

**Assertions**:
- QueryResponse is properly formed
- Generated SQL is the expected query
- Results are correct
- Answer mentions key results
- Execution time is reasonable

### Multi-Turn Conversation

**Scenario**: User asks follow-up questions with context

**Setup**:
- Load datasource with multi-dimensional data (e.g., sales by region and month)
- Mock OpenAI with realistic SQL generation

**Execute**:
- Turn 1: "Show me Q3 revenue"
- Turn 2: "Which region had the highest?"
- Turn 3: "How did Q2 compare?"

**Assertions**:
- Each turn generates appropriate SQL
- Context is preserved and used correctly
- Ambiguous references are resolved
- Results build on previous context

### Error Recovery

**Scenario**: Generated SQL is invalid, debug loop fixes it

**Setup**:
- Mock OpenAI to first return bad SQL, then corrected SQL
- Use real DuckDB with known schema

**Execute**:
- Call QueryEngine.query() with SQL that will fail initially
- Observe debug loop retry and succeed

**Assertions**:
- Debug info shows attempts were made
- Final results are correct
- Total execution time is reasonable
- Confidence score reflects recovery

### Invalid Datasource Handling

**Scenario**: Datasource is missing or malformed

**Execute**:
- Try to load non-existent file
- Try to load corrupted data
- Try to query with wrong schema

**Assertions**:
- Clear error messages are returned
- System handles failures gracefully
- No crashes or undefined behavior

---

## Accuracy Metrics

Your requirement: **Result Correctness + Answer Quality**

### Result Correctness Metric

**Definition**: Does the query result match the expected result?

**Measurement**:

1. **Row Count Matching**
   - Expected rows = N, Actual rows = N ✓
   - Expected rows = 5, Actual rows = 3 ✗

2. **Column Matching**
   - Expected columns: [region, revenue]
   - Actual columns: [region, revenue] ✓
   - Actual columns: [region, revenue, profit] ✗ (extra column)

3. **Data Value Matching**
   - For each row and column: value_actual == value_expected
   - For numeric: allow small variance (e.g., 0.01% tolerance for floating point)
   - For strings: exact match required
   - For dates: exact match required

4. **Data Type Matching**
   - Expected: (integer, string, decimal)
   - Actual: (integer, string, decimal) ✓

**Calculation**:

```
correctness_score = 0.0 to 1.0

Points deducted for:
- Row count mismatch: -0.2
- Column count mismatch: -0.2
- Column name mismatch: -0.1 per column
- Data value mismatch: -0.1 * (pct_rows_with_mismatches)
- Type mismatch: -0.1 per column

Final score = max(0, 1.0 - total_deductions)
```

**Examples**:

- Perfect match: 1.0
- Right data, extra column: 0.8 (column count mismatch)
- 50% of rows wrong: 0.5
- Complete mismatch: 0.0

### Answer Quality Metric

**Definition**: Does the natural language answer accurately describe the results?

**Measurement** (Performed by OpenAI as a judge):

Give OpenAI the following and ask it to rate 0-100:

- Original question
- Query results (reference data)
- System-generated answer

Evaluation criteria:

1. **Factual Accuracy** (Does answer match the data?)
   - Does it cite correct numbers?
   - Are comparisons correct?
   - Are percentages accurate?

2. **Completeness** (Does answer address the full question?)
   - All requested information included?
   - Important details mentioned?
   - Unnecessary information excluded?

3. **Relevance** (Does answer stay on topic?)
   - No hallucination?
   - No irrelevant tangents?
   - Clear connection to original question?

4. **Clarity** (Is answer understandable?)
   - Clear, conversational language?
   - Good sentence structure?
   - Appropriate level of detail?

**Scoring**:

OpenAI evaluator returns a numeric score 0-100, which we normalize to 0.0-1.0.

- 90-100 → 1.0 (excellent)
- 80-89 → 0.8-0.9 (good)
- 70-79 → 0.7-0.8 (acceptable)
- Below 70 → proportionally lower

**Advantages of LLM Evaluation**:
- Evaluates semantic meaning, not string matching
- Catches errors that exact matching misses
- Can score partial correctness
- Aligns with human judgment

**Potential Issues**:
- Evaluator LLM might be inconsistent
- Requires API calls (adds cost)
- Might rate incorrect answers as acceptable

**Mitigation**:
- Sample results for manual human review
- Track evaluator consistency over time
- Use majority voting (evaluate each with 3 different prompts)

---

## Confidence Score Calculation

**Definition**: How confident are we that the answer is correct?

**Inputs** (Multiple signals combined):

1. **Generation Certainty** (from OpenAI API)
   - Use log probabilities from OpenAI response
   - Higher confidence in response = higher certainty
   - Weight: 20%

2. **SQL Complexity**
   - Simple queries (1-2 tables, no complex joins) = more confident
   - Complex queries (3+ tables, subqueries, CTEs) = less confident
   - Weight: 15%

3. **Result Validation**
   - Do results "make sense"? (e.g., no negative quantities where inappropriate)
   - Is row count reasonable? (1000 rows vs. 1M rows)
   - Are any values outliers or suspicious?
   - Weight: 25%

4. **Debug Attempts**
   - 0 attempts needed = full confidence
   - 1 attempt = -0.1
   - 2 attempts = -0.2
   - 3 attempts = -0.3
   - Weight: 20%

5. **Query Execution Success**
   - No warnings or issues = +0.1
   - Had to truncate results = -0.1
   - Weight: 10%

6. **Answer Synthesis Quality**
   - Answer mentions data-backed facts = +0.05
   - Answer has caveats/uncertainties = -0.05
   - Weight: 10%

**Formula**:

```
confidence = weighted_average([
    generation_certainty * 0.20,
    (1.0 - sql_complexity) * 0.15,
    result_validation_score * 0.25,
    execution_success_score * 0.20,
    execution_quality * 0.10,
    answer_quality * 0.10,
])

Clamped to [0.0, 1.0] range
```

**Interpretation**:

- 0.9-1.0: Very confident, results are reliable
- 0.7-0.9: Moderately confident, results likely correct
- 0.5-0.7: Less confident, verify manually
- Below 0.5: Low confidence, likely issues

---

## Golden Dataset Format

### YAML Structure

Golden datasets are defined in YAML for human readability and version control:

```yaml
# golden_datasets.yaml
version: 1.0
created_date: 2026-03-17

datasets:
  - id: "q3_revenue_total"
    category: "aggregation"
    description: "Simple sum aggregation over a date range"
    
    datasource:
      name: "sales"
      path: "fixtures/sales.parquet"
    
    # What the user asks
    user_query: "What was the total revenue in Q3?"
    
    # What SQL should be generated
    expected_sql: |
      SELECT SUM(amount) as total_revenue
      FROM transactions
      WHERE QUARTER(date) = 3
    
    # What results should be returned
    expected_results:
      - total_revenue: 1250000.50
    
    # Natural language answer should mention
    expected_answer_summary: |
      The total revenue in Q3 was $1,250,000.50
    
    # Acceptable variance (1% for monetary values)
    acceptable_variance: 0.01
    
    # Difficulty/importance
    priority: "high"
    
    # Tags for grouping tests
    tags: ["aggregation", "financial", "single-table"]
    
    # Any special notes
    notes: "Tests basic SUM aggregation and QUARTER function"

  - id: "top_region_customers"
    category: "sorting"
    description: "Join with sorting and limit"
    
    datasource:
      name: "sales"
      path: "fixtures/sales.parquet"
    
    user_query: "Which region has the most customers?"
    
    expected_sql: |
      SELECT r.name as region, COUNT(DISTINCT c.id) as customer_count
      FROM customers c
      JOIN regions r ON c.region_id = r.id
      GROUP BY r.name
      ORDER BY customer_count DESC
      LIMIT 1
    
    expected_results:
      - region: "North America"
        customer_count: 15234
    
    expected_answer_summary: |
      The North America region has the most customers with 15,234
    
    priority: "high"
    tags: ["join", "group-by", "sorting"]
    
    # Exact match required for categorical data
    acceptable_variance: 0.0

  - id: "revenue_by_region_quarter"
    category: "multi-dimensional"
    description: "Multiple aggregation dimensions"
    
    datasource:
      name: "sales"
      path: "fixtures/sales.parquet"
    
    user_query: "Show me revenue by region and quarter"
    
    expected_sql: |
      SELECT 
        r.name as region,
        QUARTER(t.date) as quarter,
        SUM(t.amount) as revenue
      FROM transactions t
      JOIN regions r ON t.region_id = r.id
      GROUP BY r.name, QUARTER(t.date)
      ORDER BY r.name, QUARTER(t.date)
    
    # Multiple rows
    expected_results:
      - region: "Asia"
        quarter: 1
        revenue: 450000.00
      - region: "Asia"
        quarter: 2
        revenue: 520000.00
      # ... more rows ...
    
    expected_answer_summary: |
      Revenue varies by region and quarter, with [key observations]
    
    priority: "high"
    tags: ["multi-dimensional", "group-by"]
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier for test case |
| `category` | string | Yes | Type of query (aggregation, sorting, filtering, join, etc.) |
| `description` | string | Yes | Human-readable description |
| `datasource` | object | Yes | Reference to test data |
| `user_query` | string | Yes | Exact user question |
| `expected_sql` | string | Yes | SQL that should be generated |
| `expected_results` | list | Yes | Expected query results (list of dicts) |
| `expected_answer_summary` | string | Yes | What answer should convey |
| `acceptable_variance` | float | No | Tolerance for numeric values (default: 0.0) |
| `priority` | string | No | "high", "medium", "low" (default: "medium") |
| `tags` | list | No | Categories for filtering tests |
| `notes` | string | No | Implementation notes |

---

## Evaluation Pipeline

### Running Evaluation

High-level evaluation process:

```
LOAD golden_dataset (YAML file with test cases)
  │
FOR each test_case in dataset.test_cases:
  │
  ├─ GENERATE SQL
  │  ├─ Call QueryEngine.query(test_case.user_query)
  │  └─ Extract generated_sql
  │
  ├─ COMPARE SQL (informational only)
  │  ├─ Is generated_sql == expected_sql? (probably not, but similar)
  │  └─ Log for review
  │
  ├─ MEASURE RESULT CORRECTNESS
  │  ├─ Compare actual_results to expected_results
  │  ├─ Calculate correctness_score (0.0-1.0)
  │  └─ Log any mismatches
  │
  ├─ MEASURE ANSWER QUALITY
  │  ├─ Use OpenAI as judge
  │  ├─ Evaluate: answer_quality_score (0.0-1.0)
  │  └─ Log evaluation notes
  │
  ├─ VERIFY CONFIDENCE SCORE
  │  ├─ Is returned_confidence calibrated?
  │  ├─ Calculate calibration_error
  │  └─ Log if poorly calibrated
  │
  ├─ CAPTURE METRICS
  │  ├─ execution_time_ms
  │  ├─ api_calls_count
  │  ├─ debug_attempts
  │  └─ any_errors
  │
  └─ RECORD TEST RESULT
     ├─ test_id
     ├─ passed (result_correct AND answer_quality > 0.8)
     ├─ result_correctness
     ├─ answer_quality
     ├─ confidence_score
     ├─ confidence_calibration_error
     ├─ metrics
     └─ notes
│
AGGREGATE RESULTS
│
CALCULATE METRICS
├─ Overall accuracy: % passed
├─ Result correctness: avg score
├─ Answer quality: avg score
├─ Confidence calibration: RMS error
├─ Performance: avg execution time
├─ API efficiency: avg calls per query
├─ Reliability: % required debugging
└─ By category: accuracy by query type
│
GENERATE REPORT
├─ Summary (pass rate, key metrics)
├─ Detailed results per test case
├─ Failure analysis (patterns in errors)
├─ Performance breakdown
├─ Recommendations for improvement
└─ Timestamp and version info
```

### Evaluation Output

Results are written to JSON for programmatic access:

```json
{
  "evaluation_run": {
    "timestamp": "2026-03-17T14:30:00Z",
    "version": "v1.0.0",
    "dataset": "golden_datasets.yaml",
    "test_count": 25,
    "passed_count": 22,
    "accuracy": 0.88
  },
  "metrics": {
    "result_correctness": {
      "mean": 0.92,
      "min": 0.6,
      "max": 1.0,
      "std_dev": 0.08
    },
    "answer_quality": {
      "mean": 0.85,
      "min": 0.65,
      "max": 0.99,
      "std_dev": 0.09
    },
    "confidence_calibration_error": 0.04,
    "execution_time_ms": {
      "mean": 2500,
      "min": 400,
      "max": 8200,
      "p95": 6500
    },
    "api_calls_per_query": {
      "mean": 1.8,
      "min": 1,
      "max": 4
    }
  },
  "by_category": {
    "aggregation": {
      "passed": 8,
      "total": 8,
      "accuracy": 1.0
    },
    "join": {
      "passed": 6,
      "total": 8,
      "accuracy": 0.75
    },
    "sorting": {
      "passed": 5,
      "total": 5,
      "accuracy": 1.0
    }
  },
  "failures": [
    {
      "test_id": "multi_join_with_filtering",
      "category": "complex",
      "reason": "Missing WHERE clause in generated SQL",
      "user_query": "Show me Q3 revenue for customers in USA",
      "expected_sql": "SELECT ... WHERE country = 'USA' AND QUARTER(date) = 3",
      "generated_sql": "SELECT ... WHERE QUARTER(date) = 3",
      "result_correctness": 0.5,
      "answer_quality": 0.6,
      "notes": "Generated SQL missing geographic filter"
    }
  ],
  "recommendations": [
    "Improve example selection for filtering queries",
    "Add more examples of WHERE clause patterns",
    "Consider multi-step generation for complex queries"
  ]
}
```

---

## Success Criteria

### Prototype Phase Success

- ✓ Notebook runs end-to-end without errors
- ✓ Can answer at least 5 simple queries correctly
- ✓ Debug loop successfully recovers from at least 1 error
- ✓ Natural language answers are readable
- ✓ System identifies areas for improvement

### Phase 2 Success (Core Package)

- ✓ Unit test coverage: >80%
- ✓ All integration tests pass
- ✓ Zero crashes or undefined behavior
- ✓ Clear error messages for all failure modes
- ✓ Handles datasource loading correctly

### Phase 3 Success (Multi-turn & Testing)

- ✓ Multi-turn conversations work smoothly
- ✓ Confidence scores calculated
- ✓ Golden datasets created and loading
- ✓ Evaluation pipeline runs successfully

### Final Success Metrics

These are the targets for production readiness:

**Accuracy**:
- ✓ Result Correctness: >85% on golden datasets
- ✓ Answer Quality: >80% scored as good/excellent
- ✓ Overall Pass Rate: >85% (both metrics pass)

**Reliability**:
- ✓ Debug Recovery Rate: >90% of fixable errors
- ✓ Unrecoverable Errors: <5% of queries
- ✓ Crashes/Undefined Behavior: 0%

**Performance**:
- ✓ Average Execution Time: <5 seconds
- ✓ P95 Execution Time: <15 seconds
- ✓ Average API Calls: <2 per query
- ✓ SQL Generation Time: <100ms

**Confidence Calibration**:
- ✓ Calibration Error: <5% (RMS)
- ✓ High confidence (0.8+) queries: >90% actually correct
- ✓ Low confidence (<0.5) queries: escalate for review

---

## Related Documentation

- [DESIGN.md](./DESIGN.md) - Design and goals
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [API.md](./API.md) - Public API reference
- [ROADMAP.md](./ROADMAP.md) - Implementation timeline
- [FAQ.md](./FAQ.md) - Design questions and decisions
