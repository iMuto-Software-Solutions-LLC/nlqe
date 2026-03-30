# Example Queries for NLQE Testing

This document lists all 25+ example query patterns organized by complexity and SQL feature.

## Simple Queries (Easy - Good for Testing Basics)

### 1. Count Transactions
**Question**: "How many transactions are in the dataset?"  
**Difficulty**: Easy  
**SQL Feature**: COUNT(*)  
**Expected Approach**: Basic aggregation without WHERE clause

### 2. Total Revenue
**Question**: "What is the total revenue from all transactions?"  
**Difficulty**: Easy  
**SQL Feature**: SUM()  
**Expected Approach**: Basic SUM aggregation

### 3. Average Amount
**Question**: "What is the average transaction amount?"  
**Difficulty**: Easy  
**SQL Feature**: AVG()  
**Expected Approach**: Simple average calculation

### 4. Filter by Category
**Question**: "Show me all Electronics transactions"  
**Difficulty**: Easy  
**SQL Feature**: WHERE with string comparison  
**Expected Approach**: Filter single table by category

### 5. Filter by Date Range
**Question**: "Show transactions from February 2024"  
**Difficulty**: Easy  
**SQL Feature**: WHERE with date range (>=, <)  
**Expected Approach**: Date range filtering

### 6. Filter by Amount
**Question**: "Show me transactions over 1000 dollars"  
**Difficulty**: Easy  
**SQL Feature**: WHERE with numeric comparison  
**Expected Approach**: Simple numeric filter

---

## Grouping Queries (Medium - Test GROUP BY)

### 7. Revenue by Category
**Question**: "What is the total revenue by product category?"  
**Difficulty**: Medium  
**SQL Features**: GROUP BY, SUM(), ORDER BY  
**Expected Approach**: GROUP BY with aggregation and sorting

### 8. Transaction Count by Category
**Question**: "How many transactions are there for each category?"  
**Difficulty**: Medium  
**SQL Features**: GROUP BY, COUNT(), ORDER BY  
**Expected Approach**: Count transactions per category

### 9. Revenue by Region and Category
**Question**: "Show total revenue by region and category"  
**Difficulty**: Medium  
**SQL Features**: GROUP BY (multiple columns), SUM(), JOIN  
**Expected Approach**: Multi-column GROUP BY with join

---

## Sorting and Limiting (Medium - Test ORDER BY and LIMIT)

### 10. Top 10 Transactions
**Question**: "Show the 10 largest transactions"  
**Difficulty**: Easy  
**SQL Features**: ORDER BY DESC, LIMIT  
**Expected Approach**: Sort descending and limit results

### 11. Smallest Transactions
**Question**: "Show the 5 smallest transactions"  
**Difficulty**: Easy  
**SQL Features**: ORDER BY ASC, LIMIT  
**Expected Approach**: Sort ascending for minimum values

---

## Join Queries (Medium - Test INNER and LEFT JOINs)

### 12. Revenue by Region Name
**Question**: "Show revenue by region name"  
**Difficulty**: Medium  
**SQL Features**: INNER JOIN, GROUP BY, SUM()  
**Expected Approach**: Join transactions with regions table

### 13. Transactions with Details
**Question**: "Show transactions with customer name and region name"  
**Difficulty**: Medium  
**SQL Features**: Multiple JOINs, SELECT specific columns  
**Expected Approach**: Denormalize data with two joins

### 14. All Customers and Spending
**Question**: "Show all customers and their total spending (including inactive)"  
**Difficulty**: Medium  
**SQL Features**: LEFT JOIN, GROUP BY, NULLS  
**Expected Approach**: Preserve unmatched customers with LEFT JOIN

---

## Complex Queries (Hard - Advanced SQL Features)

### 15. Multi-Dimensional Revenue Analysis
**Question**: "Show revenue, transaction count, and average amount by region and category"  
**Difficulty**: Hard  
**SQL Features**: GROUP BY (multi-column), multiple aggregations  
**Expected Approach**: Multiple aggregate functions with 2-level grouping

### 16. Customer Segmentation
**Question**: "Show spending analysis for Gold tier customers who are active"  
**Difficulty**: Hard  
**SQL Features**: WHERE multiple conditions, LEFT JOIN, multiple aggregations  
**Expected Approach**: Filter on customer attributes, join with transactions

### 17. High-Value Customers
**Question**: "List customers with lifetime value over 10000 dollars and at least 5 transactions"  
**Difficulty**: Hard  
**SQL Features**: GROUP BY, HAVING clause, aggregate filtering  
**Expected Approach**: HAVING clause to filter aggregated results

### 18. Return Rate by Category
**Question**: "Show return rate by category"  
**Difficulty**: Hard  
**SQL Features**: CASE WHEN, conditional aggregation, percentage calculation  
**Expected Approach**: Use CASE WHEN for conditional counting

### 19. Quarterly Revenue Comparison
**Question**: "Show quarterly revenue and growth comparison"  
**Difficulty**: Hard  
**SQL Features**: QUARTER(), EXTRACT(), GROUP BY date components  
**Expected Approach**: Date functions for temporal grouping

### 20. Profit Margin Analysis
**Question**: "Which category has the highest profit margin and is it growing?"  
**Difficulty**: Hard  
**SQL Features**: SUM(), AVG(), percentage calculations  
**Expected Approach**: Calculate margins and percentages

### 21. Top Customers by Region
**Question**: "Show the top 3 spenders in each region"  
**Difficulty**: Hard  
**SQL Features**: Multiple JOINs, GROUP BY, LIMIT with grouping  
**Expected Approach**: Top N per group pattern

---

## Multi-Turn Conversation Examples

### 22. Regional Analysis (3-turn conversation)
**Turn 1**: "Which product category has the highest total revenue?"  
**Turn 2**: "How many returns did we have in that category?"  
**Turn 3**: "How does the return rate compare to other categories?"  
**Purpose**: Test context preservation and follow-up understanding

### 23. Customer Analysis (3-turn conversation)
**Turn 1**: "Show me our Gold tier customers"  
**Turn 2**: "What is their average lifetime value?"  
**Turn 3**: "How does that compare to other tiers?"  
**Purpose**: Test multi-level context and comparison

---

## SQL Features Coverage Matrix

| Feature | Query | Difficulty |
|---------|-------|------------|
| COUNT(*) | #1 | Easy |
| SUM() | #2 | Easy |
| AVG() | #3 | Easy |
| WHERE (string) | #4 | Easy |
| WHERE (date range) | #5 | Easy |
| WHERE (numeric) | #6 | Easy |
| GROUP BY | #7-9 | Medium |
| ORDER BY | #10-11 | Easy |
| LIMIT | #10-11 | Easy |
| INNER JOIN | #12-13 | Medium |
| LEFT JOIN | #14 | Medium |
| Multiple JOINs | #13 | Medium |
| Multi-column GROUP BY | #9, #15 | Medium-Hard |
| Multiple Aggregations | #15, #20 | Hard |
| HAVING clause | #17 | Hard |
| CASE WHEN | #18 | Hard |
| Date Functions | #19 | Hard |
| Percentage Calc | #18, #20 | Hard |
| WHERE (multi-condition) | #16 | Hard |
| Top N per group | #21 | Hard |

---

## Query Difficulty Distribution

**Easy (6)**: Basic operations
- Simple aggregations (COUNT, SUM, AVG)
- Single table filtering
- Basic sorting and limiting

**Medium (10)**: Combine multiple concepts
- GROUP BY with aggregation
- Joining multiple tables
- Sorting with limiting
- Basic multi-column operations

**Hard (9+)**: Advanced patterns
- Multi-dimensional analysis
- Complex filtering with aggregation
- HAVING clauses
- Conditional aggregation (CASE WHEN)
- Date/time functions
- Top N per group
- Multi-turn conversation

---

## Running the Examples

### Option 1: Interactive Notebooks
```bash
# Basic examples
jupyter notebook prototype.ipynb

# Advanced examples with complex queries
jupyter notebook prototype_advanced.ipynb
```

### Option 2: Python API
```python
from nlqe import QueryEngine, QueryEngineConfig

config = QueryEngineConfig.from_env()
engine = QueryEngine(config)
engine.load_datasource("fixtures/transactions.parquet")

# Try any query
response = engine.query("Show revenue by region and category")
print(response.answer)
```

### Option 3: From YAML
See `fixtures/example_queries.yaml` for all 25+ examples in structured format with:
- Natural language question
- Expected SQL
- Explanation
- Difficulty level
- SQL features used
- Tags for filtering

---

## Expected Accuracy by Category

Based on the design goals (>85% accuracy):

| Category | Expected Accuracy |
|----------|------------------|
| Simple Aggregations | >95% |
| Filtering | >90% |
| Single GROUP BY | >90% |
| Joins | 80-85% |
| Multi-column GROUP BY | 75-85% |
| Complex (HAVING, CASE) | 70-80% |
| Multi-turn Context | 75-85% |

**Note**: Accuracy improves with better examples and prompt engineering in Phase 2.

---

## Extending the Examples

To add more example queries to the system:

1. **Add to `fixtures/example_queries.yaml`:**
   ```yaml
   - id: "unique_id"
     category: "category_name"
     difficulty: "easy|medium|hard"
     description: "What this tests"
     question: "Natural language question"
     sql: "Expected SQL"
     explanation: "Why this SQL works"
     tags: ["tag1", "tag2"]
   ```

2. **Add test case to notebook:**
   - Create cell with question
   - Call `engine.query(question)`
   - Verify results

3. **Track metrics:**
   - Did it generate correct SQL?
   - Did it execute successfully?
   - Was the answer helpful?
   - Confidence score appropriate?

---

## Next Phase Goals

**Phase 2 (Weeks 2-3):**
- ✓ Add 50+ more example patterns
- ✓ Create golden dataset with expected results
- ✓ Implement evaluation metrics
- ✓ Measure accuracy by category
- ✓ Optimize prompts based on failures

**Phase 3 (Weeks 4-5):**
- ✓ Add domain-specific examples
- ✓ Fine-tune confidence scoring
- ✓ Improve multi-turn handling
- ✓ Reach 85%+ accuracy target

---

## Resources

- See `fixtures/README.md` for sample data documentation
- See `docs/TESTING.md` for accuracy evaluation methodology
- See `docs/API.md` for QueryEngine usage
- See `IMPLEMENTATION_SUMMARY.md` for architecture overview
