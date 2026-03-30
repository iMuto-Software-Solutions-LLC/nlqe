# NLQE: Implementation Roadmap

**Version**: v1.0.0  
**Last Updated**: March 17, 2026  
**Status**: POC Planning Phase

## Overview

This document outlines the implementation timeline, phases, and success criteria for NLQE development. Phases are organized sequentially over a 6-week period, with clear deliverables and success metrics.

---

## Executive Summary

| Phase | Duration | Focus | Deliverables |
|-------|----------|-------|--------------|
| **1: Prototype** | Week 1 | POC & validation | Jupyter notebook, mock data, findings |
| **2: Core Package** | Weeks 2-3 | Build package structure & components | Importable library, unit tests, core functionality |
| **3: Multi-turn & Testing** | Weeks 4-5 | Conversation support & evaluation framework | Multi-turn features, golden datasets, evaluation pipeline |
| **4: Polish & Release** | Week 6 | Documentation, optimization, release prep | Complete docs, benchmarks, PyPI ready |

**Total Timeline**: 6 weeks  
**Team Size**: 1-2 engineers  
**Testing**: Continuous throughout all phases

---

## Phase 1: Prototype (Week 1)

### Objectives

- Validate proof-of-concept flow end-to-end
- Confirm OpenAI can generate useful SQL
- Test DuckDB integration
- Identify gaps and issues before full development
- Document learnings for Phase 2

### Scope

Single **Jupyter notebook** (`prototype.ipynb`) demonstrating complete pipeline.

### Tasks

#### Day 1-2: Setup & Data

- [ ] Create `.env.example` with required variables
- [ ] Prepare mock datasource
  - [ ] Create `fixtures/sales.parquet` with sample data (5-10 tables, 1000+ rows)
  - [ ] Document schema and contents
- [ ] Set up Jupyter environment
- [ ] Create sample questions and golden answers (5-10 test cases)

#### Day 2-3: Implementation

- [ ] Section 1: Setup & imports
  - Load libraries (duckdb, openai, pydantic, yaml)
  - Initialize OpenAI client
  - Load environment variables
  
- [ ] Section 2: Introspection
  - Display datasource schema
  - Show example Q&A patterns
  - Explain data contents
  
- [ ] Section 3: Query Flow Implementation
  - Implement context building
  - Implement SQL generation via OpenAI
  - Implement DuckDB execution
  - Implement debug loop (basic, up to 3 attempts)
  - Implement answer synthesis
  
- [ ] Section 4: Experimentation
  - Test 5-10 different queries
  - Log success/failure for each
  - Measure metrics (execution time, API calls, confidence)

#### Day 4: Analysis & Documentation

- [ ] Section 5: Findings & Insights
  - Document what worked well
  - Document issues encountered
  - Identify refinements needed
  - Assess feasibility of Phase 2
  
- [ ] Create `PROTOTYPE_FINDINGS.md` summarizing learnings

### Deliverables

1. **prototype.ipynb** - Complete POC notebook
2. **fixtures/sales.parquet** - Mock datasource
3. **fixtures/sample_queries.yaml** - Test cases with expected answers
4. **.env.example** - Template for environment setup
5. **PROTOTYPE_FINDINGS.md** - Learnings summary for handoff

### Success Criteria

- ✓ Notebook runs without errors
- ✓ Can generate SQL for at least 5 different query patterns
- ✓ DuckDB successfully executes generated SQL
- ✓ Results are accurate
- ✓ Natural language answers are readable
- ✓ Debug loop successfully recovers from at least 1 SQL error
- ✓ All findings documented for Phase 2

### Key Learnings to Document

- Does OpenAI generate good SQL from plain English?
- What types of queries work best? Worst?
- How often does the debug loop help?
- What are the common failure patterns?
- How clear are the synthesized answers?
- Estimated API costs per query?
- Any DuckDB surprises or limitations?
- What examples are most useful?

### Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| OpenAI generates wrong SQL | Document patterns that work, prepare examples |
| Debug loop doesn't help | Try different error messages/context, may need fine-tuning |
| Slow execution times | Profile and optimize critical paths |
| API costs too high | Count tokens, optimize prompts, consider smaller models |
| Data privacy concerns | Use synthetic/mock data only, document data handling |

---

## Phase 2: Core Package (Weeks 2-3)

### Objectives

- Build production-grade package structure
- Implement all core components
- Comprehensive error handling
- Unit tests for all components
- Foundation for multi-turn support

### Scope

Transform prototype into importable Python package with proper structure, testing, and documentation.

### Package Structure

```
src/nlqe/
├── __init__.py (public API)
├── config.py (Pydantic models)
├── types.py (type definitions)
├── datasource/ (schema discovery, datasource management)
├── openai/ (OpenAI integration)
├── duckdb/ (DuckDB integration)
├── query/ (query loop logic)
├── conversation/ (multi-turn support - basic)
├── synthesis/ (answer generation)
├── testing/ (evaluation framework - basic)
└── utils/ (logging, errors, etc.)
```

### Tasks

#### Week 2: Foundation

- [ ] Set up package structure
  - [ ] Create `src/nlqe/` directory structure
  - [ ] Implement `__init__.py` with public API exports
  - [ ] Create type definitions in `types.py`
  - [ ] Create Pydantic config models
  - [ ] Create error classes
  
- [ ] Implement datasource management
  - [ ] Schema introspection from parquet/CSV
  - [ ] DataSource model and registration
  - [ ] Multiple datasource format support
  
- [ ] Implement OpenAI integration
  - [ ] Client wrapper around OpenAI API
  - [ ] Request formatting
  - [ ] Response parsing
  - [ ] Retry logic and error handling
  - [ ] Token counting
  
- [ ] Implement DuckDB integration
  - [ ] Connection management
  - [ ] SQL execution with timeout
  - [ ] SQL validation (syntax, schema, safety)
  - [ ] Error handling and classification
  
- [ ] Update `pyproject.toml`
  - [ ] Add new dependencies (openai, pydantic-settings, etc.)
  - [ ] Configure package metadata
  - [ ] Add dev dependencies (pytest, pytest-cov, etc.)

#### Week 2-3: Core Logic & Testing

- [ ] Implement query loop
  - [ ] Context building
  - [ ] SQL generation
  - [ ] Query execution
  - [ ] Debug loop logic
  - [ ] Answer synthesis
  - [ ] Confidence scoring
  
- [ ] Implement QueryEngine class
  - [ ] `__init__`, configuration loading
  - [ ] `load_datasource`
  - [ ] `query` method
  - [ ] Schema access
  - [ ] `start_conversation` (basic)
  
- [ ] Unit tests
  - [ ] Datasource loading (parquet, CSV)
  - [ ] Schema introspection
  - [ ] OpenAI client (mocked)
  - [ ] DuckDB executor
  - [ ] SQL validation
  - [ ] Context building
  - [ ] Error classification
  - [ ] Configuration loading
  
  **Target Coverage**: >80% of core logic
  
- [ ] Integration tests
  - [ ] Full query flow with mock OpenAI
  - [ ] Multi-format datasource loading
  - [ ] Error recovery (debug loop)
  - [ ] End-to-end accuracy on simple queries

### Deliverables

1. **Importable package** - `from nlqe import QueryEngine`
2. **Unit tests** - 50+ tests covering all components
3. **Integration tests** - End-to-end flows
4. **.github/workflows/** - CI/CD pipeline (optional for POC)
5. **Updated pyproject.toml** - All dependencies configured
6. **docs/API.md** - Public API specification

### Success Criteria

- ✓ Package imports without errors
- ✓ Unit test coverage >80%
- ✓ All integration tests pass
- ✓ Can load parquet and CSV datasources
- ✓ Can execute queries end-to-end
- ✓ Error handling works for main scenarios
- ✓ Configuration loads from environment
- ✓ Query execution time <5 seconds for simple queries

### Key Components

1. **QueryEngine** - Main user-facing class
2. **QueryContext** - Context assembly
3. **OpenAIClient** - API integration
4. **DuckDBExecutor** - Query execution
5. **DebugLoop** - Error recovery
6. **AnswerSynthesizer** - Natural language generation

### Testing Strategy

- Mock OpenAI API calls (don't use real API in tests)
- Use real DuckDB with small test datasets
- Test error paths explicitly
- Measure code coverage with pytest-cov

---

## Phase 3: Multi-turn & Testing (Weeks 4-5)

### Objectives

- Implement multi-turn conversation support
- Build golden dataset evaluation framework
- Create evaluation pipeline
- Measure accuracy and confidence
- Comprehensive testing infrastructure

### Scope

Add conversation management, build testing infrastructure, create golden datasets for evaluation.

### Tasks

#### Week 4: Conversation & Evaluation Framework

- [ ] Implement ConversationManager
  - [ ] Conversation state management
  - [ ] Turn history tracking
  - [ ] Context window management
  - [ ] Reference expansion (pronouns, "that region", etc.)
  - [ ] Conversation context synthesis
  
- [ ] Build evaluation framework
  - [ ] Golden dataset YAML format
  - [ ] GoldenDataset model
  - [ ] Evaluator class
  - [ ] Metric calculations
  - [ ] Report generation
  
- [ ] Create golden datasets
  - [ ] 5-10 test cases per query category
  - [ ] Categories: aggregation, filtering, sorting, join, multi-dimensional
  - [ ] Include simple and complex queries
  - [ ] Document expected results precisely
  
- [ ] Implement metrics
  - [ ] Result correctness scoring
  - [ ] Answer quality evaluation (using OpenAI as judge)
  - [ ] Confidence score calculation
  - [ ] Calibration measurement

#### Week 4-5: Testing & Metrics

- [ ] Build evaluation pipeline
  - [ ] Load golden datasets
  - [ ] Run queries through engine
  - [ ] Compare results
  - [ ] Score accuracy
  - [ ] Generate reports (JSON)
  
- [ ] Unit tests for evaluation
  - [ ] Metric calculation correctness
  - [ ] Golden dataset loading
  - [ ] Result comparison logic
  - [ ] Confidence score calculation
  
- [ ] Integration tests for conversation
  - [ ] Single turn queries
  - [ ] Multi-turn with context preservation
  - [ ] Reference expansion
  - [ ] Conversation state management
  
- [ ] Performance benchmarks
  - [ ] Query execution time
  - [ ] API calls per query
  - [ ] Token usage
  - [ ] Confidence score accuracy

#### Week 5: Documentation & Polish

- [ ] Create sample datasets
  - [ ] Sales data (transactions, customers, regions)
  - [ ] With known schema and relationships
  
- [ ] Documentation updates
  - [ ] Update API.md with conversation examples
  - [ ] Update ARCHITECTURE.md with detailed flows
  - [ ] Create TESTING.md
  - [ ] Example notebooks
  
- [ ] Evaluation campaign
  - [ ] Run against golden datasets
  - [ ] Measure accuracy
  - [ ] Identify failure patterns
  - [ ] Document results

### Deliverables

1. **ConversationManager** - Multi-turn conversation support
2. **Evaluator** - Golden dataset evaluation framework
3. **golden_datasets.yaml** - Test cases (25-50 test cases)
4. **evaluation_results.json** - Metrics and results
5. **docs/TESTING.md** - Testing strategy document
6. **Example notebooks** - Usage demonstrations
7. **Updated docs/** - Complete documentation

### Success Criteria

- ✓ Multi-turn conversations work smoothly
- ✓ Reference expansion handles common pronouns
- ✓ Confidence scores are calculated
- ✓ Golden datasets load correctly
- ✓ Evaluation pipeline runs successfully
- ✓ >80% of simple queries correct
- ✓ Detailed metrics available
- ✓ Failure patterns identified and documented

### Golden Dataset Examples

- Simple aggregation: "What was Q3 revenue?" (1-2 tables)
- Filtering: "Show me customers in USA" (schema filtering)
- Grouping: "Revenue by region" (GROUP BY)
- Sorting: "Top 5 regions by sales" (ORDER BY, LIMIT)
- Joining: "Revenue per customer by region" (multiple tables)
- Complex: "Q3 revenue by region for customers in USA" (multiple conditions)
- Multi-dimensional: "Revenue by region and quarter" (multiple GROUP BY)

### Metrics to Track

| Metric | Target | Importance |
|--------|--------|-----------|
| Result Correctness | >85% | Critical |
| Answer Quality | >80% | Critical |
| Overall Accuracy | >85% | Critical |
| Confidence Calibration Error | <5% | High |
| Execution Time | <5s | Medium |
| API Calls Per Query | <2 | High |
| Debug Recovery Rate | >90% | Medium |

---

## Phase 4: Polish & Release (Week 6)

### Objectives

- Complete documentation
- Security review
- Performance optimization
- Prepare for public release
- Ensure production readiness

### Scope

Final polish, comprehensive documentation, security/performance review, PyPI release preparation.

### Tasks

#### Day 1-2: Documentation

- [ ] Complete all documentation
  - [ ] docs/DESIGN.md - finalize
  - [ ] docs/ARCHITECTURE.md - finalize
  - [ ] docs/TESTING.md - finalize
  - [ ] docs/API.md - finalize
  - [ ] docs/ROADMAP.md - finalize
  - [ ] docs/FAQ.md - finalize
  
- [ ] Create comprehensive README
  - [ ] Project description
  - [ ] Quick start guide
  - [ ] Feature overview
  - [ ] Documentation links
  - [ ] Contributing guidelines
  
- [ ] Create usage examples
  - [ ] Basic single query notebook
  - [ ] Multi-turn conversation notebook
  - [ ] Evaluation against golden data notebook
  - [ ] Deployment guide

#### Day 2-3: Security & Performance

- [ ] Security review
  - [ ] SQL injection prevention verified
  - [ ] API key handling secure
  - [ ] No secrets in code/docs
  - [ ] Dependency audit
  
- [ ] Performance optimization
  - [ ] Profile bottlenecks
  - [ ] Optimize context building
  - [ ] Optimize result parsing
  - [ ] Optimize network calls
  
- [ ] Stress testing
  - [ ] Large datasets
  - [ ] Complex queries
  - [ ] Multiple concurrent queries
  - [ ] API rate limits

#### Day 3-4: Release Preparation

- [x] Version bump
  - [x] Update version to 0.1.0
  - [x] Update all docs with version
  - [x] Create CHANGELOG.md

- [x] Package configuration
  - [x] Finalize pyproject.toml
  - [x] Test package building
  - [x] Verify imports work
  - [x] Create wheel and sdist

- [x] PyPI preparation
  - [x] Create PyPI account
  - [x] Configure authentication
  - [x] Test TestPyPI upload
  - [x] Create PyPI project page

- [x] Final testing
  - [x] Full test suite passes
  - [x] All examples work
  - [x] Documentation is correct
  - [x] No warnings or errors

#### Day 4-5: Release & Monitoring

- [x] Release to PyPI
  - [x] Upload to PyPI
  - [x] Verify installation via pip
  - [x] Test in fresh environment

- [x] Create release announcement
  - [x] Summary of features
  - [x] Known limitations
  - [x] Future roadmap

- [x] Set up monitoring
  - [x] Error tracking
  - [x] Usage metrics
  - [x] Feedback collection
### Deliverables

1. **Complete Documentation** - All docs finalized
2. **README.md** - Comprehensive project overview
3. **Example Notebooks** - Usage demonstrations
4. **CHANGELOG.md** - Version history
5. **PyPI Package** - Published to PyPI
6. **Release Announcement** - Public announcement

### Success Criteria

- ✓ All documentation complete and reviewed
- ✓ Code passes security review
- ✓ Performance benchmarks meet targets
- ✓ Package installs via pip
- ✓ All tests pass in CI/CD
- ✓ Example notebooks run without errors
- ✓ Released to PyPI successfully

### Quality Checklist

- [ ] Type hints on all public APIs
- [ ] Docstrings for all public methods
- [ ] No pylint/flake8 warnings
- [ ] No mypy type errors
- [ ] >80% test coverage
- [ ] All tests pass
- [ ] No security vulnerabilities
- [ ] Performance within targets
- [ ] Documentation is accurate
- [ ] Examples are runnable

---

## Cross-Phase Dependencies

```
Phase 1 (Prototype)
  ├─ Must complete before Phase 2
  └─ Outputs: Design learnings, data samples
  
Phase 2 (Core Package)
  ├─ Depends on Phase 1 learnings
  ├─ Must complete before Phase 3
  └─ Outputs: Importable package, test framework
  
Phase 3 (Multi-turn & Testing)
  ├─ Depends on Phase 2 package
  ├─ Can run in parallel with Phase 2 (after day 3)
  ├─ Must complete before Phase 4
  └─ Outputs: Evaluation framework, accuracy metrics
  
Phase 4 (Polish & Release)
  ├─ Depends on Phase 3 completion
  └─ Outputs: Released package, documentation
```

---

## Parallelizable Work

Some tasks can run in parallel to compress timeline:

**Phase 2-3 Overlap (saves 1 week)**:
- While Phase 2 completes component tests (day 3+)
- Can start Phase 3 golden dataset creation
- Can start Phase 3 evaluation framework design

**Documentation Parallel**:
- API docs (API.md) can be written during Phase 2
- ARCHITECTURE.md can be written during Phase 2
- TESTING.md requires Phase 3 to be meaningful

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| OpenAI model underperforms | Medium | High | Prototype validates; prepare fallback models |
| DuckDB lacks features | Low | Medium | Early spike; document limitations |
| Confidence calibration fails | Medium | Medium | Use multiple signals; validate with humans |
| Performance issues | Medium | Medium | Profile early; optimize critical paths |
| API costs exceed budget | Low | Medium | Token counting; optimize prompts |

### Schedule Risks

| Risk | Mitigation |
|------|-----------|
| Phase 1 takes longer than expected | Document findings thoroughly; don't let perfect be enemy of good |
| Package structure needs rework | Build incrementally; refactor early |
| Tests are difficult to write | Start test-first; use fixtures and mocking |
| Golden datasets are hard to create | Start with simple cases; build up gradually |

### Dependency Risks

| Risk | Mitigation |
|------|-----------|
| OpenAI API changes | Watch for announcements; pin version; add abstraction layer |
| DuckDB version incompatibilities | Pin version; test with multiple versions |
| Security vulnerabilities in deps | Regular audits; update promptly |

---

## Resource Requirements

### Team Composition

Recommended: 1-2 engineers

- 1 engineer can do it (6 weeks)
- 2 engineers can parallelize (4 weeks)
- 3+ engineers not recommended (coordination overhead)

### Tools & Infrastructure

- Python 3.14+
- OpenAI API (paid tier for volume)
- PyPI account
- Git/GitHub
- Jupyter for prototype
- pytest for testing

### Estimated Costs

- **Phase 1-3**: ~$500-2000 OpenAI API costs (depends on volume)
- **Phase 4**: Minimal
- **Total**: <$3000 for POC to release

---

## Success Metrics

### Phase 1 Success
- Prototype notebook runs end-to-end
- At least 5 queries work correctly
- Findings documented

### Phase 2 Success
- Package installs via pip
- Unit test coverage >80%
- Simple queries work end-to-end

### Phase 3 Success
- Multi-turn conversations work
- 25+ golden datasets created
- Evaluation pipeline functional
- Accuracy >80% on golden data

### Phase 4 Success
- Released to PyPI
- Complete documentation
- Example notebooks work
- All tests pass

### Final Product Success
- Accuracy >85% on golden data
- Confidence scores well-calibrated
- Multi-turn works reliably
- Performance <5 seconds average

---

## Post-Release Roadmap

After v0.1.0 release:

### v0.2.0 (Weeks 7-9)
- Support for more datasource types (PostgreSQL, Snowflake, etc.)
- Caching layer for query results
- Custom synthesizer plugins
- Streaming responses

### v0.3.0 (Weeks 10-12)
- Fine-tuning support for custom SQL patterns
- Multi-datasource joins
- Advanced confidence scoring
- Batch query mode

### v1.0.0 (Weeks 13-16)
- Cloud deployment option
- Authentication & authorization
- API server
- Advanced monitoring & observability

---

## Related Documentation

- [DESIGN.md](./DESIGN.md) - Design and architecture
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical implementation details
- [TESTING.md](./TESTING.md) - Testing strategy and metrics
- [API.md](./API.md) - Public API reference
- [FAQ.md](./FAQ.md) - Design decisions and questions
