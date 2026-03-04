# Asset Manager - Query & Response Flow Documentation

## Overview

This document explains the complete flow of how user queries are processed, sent to the LLM, and how responses (including PDFs) are generated in the Asset Manager platform.

---

## Table of Contents

1. [Query Flow Architecture](#1-query-flow-architecture)
2. [Query Routing (Vanna vs Rule-Based)](#2-query-routing-vanna-vs-rule-based)
3. [LLM Prompt Construction](#3-llm-prompt-construction)
4. [LLM Response Format](#4-llm-response-format)
5. [Response Parsing](#5-response-parsing)
6. [PDF Generation](#6-pdf-generation)
7. [File References](#7-file-references)

---

## 1. Query Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│                         (React Frontend - Chat.js)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ POST /api/chat/
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CHAT ROUTE                                      │
│                         (/backend/routes/chat.py)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CHAT SERVICE                                       │
│                    (/backend/services/chat_service.py)                      │
│                                                                              │
│  • Manages conversation history                                              │
│  • Stores messages in database                                               │
│  • Calls AnalyticsService for data analysis                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ANALYTICS SERVICE                                    │
│                  (/backend/services/analytics_service.py)                   │
│                                                                              │
│  1. Initialize semantic layer (if enabled)                                   │
│  2. Route query (Vanna semantic OR rule-based)                              │
│  3. Gather data (SQL execution OR pre-computed aggregations)                │
│  4. Build prompt and call LLM Service                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
              ┌─────────────────────┐   ┌─────────────────────┐
              │   SEMANTIC PATH     │   │  RULE-BASED PATH    │
              │   (Vanna + FAISS)   │   │  (Pre-aggregated)   │
              └─────────────────────┘   └─────────────────────┘
                          │                       │
                          └───────────┬───────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            LLM SERVICE                                       │
│                    (/backend/services/llm_service.py)                       │
│                                                                              │
│  1. Build system message                                                     │
│  2. Construct analysis prompt with data context                             │
│  3. Send to OpenAI GPT-4                                                    │
│  4. Receive JSON response                                                    │
│  5. Parse and validate response                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RESPONSE PARSER                                      │
│                   (/backend/utils/response_parser.py)                       │
│                                                                              │
│  • Extracts JSON from LLM response                                          │
│  • Validates structure (response, charts, tables, summary_points)           │
│  • Returns ChatResponse object                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                           │
│                                                                              │
│  • ChatMessage.js renders response                                           │
│  • Charts rendered with Recharts                                             │
│  • Tables rendered with TableRenderer.js                                     │
│  • PDF export via html2canvas + jsPDF (CODE-BASED, not LLM)                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Query Routing (Vanna vs Rule-Based)

### Location: `/backend/services/semantic_layer/query_router.py`

The system uses pattern matching to decide which path to use:

### Semantic Path (Vanna) - Used for:
- Ad-hoc exploratory queries
- "Show me top 10...", "List all...", "Find customers..."
- Queries with filters: "where", "greater than", "between"
- Grouping queries: "by branch", "by product"

### Rule-Based Path - Used for:
- Standard KPI queries: "Gross NPA ratio", "CASA ratio"
- Portfolio summaries: "portfolio overview", "key metrics"
- Pre-computed breakdowns: "asset class breakdown"

### Routing Decision Flow:

```python
# Query classification logic
if query matches SEMANTIC_PATTERNS and not RULE_BASED_PATTERNS:
    → Use Vanna (generate SQL dynamically)
elif query matches RULE_BASED_PATTERNS:
    → Use existing aggregations (pre-computed)
elif query matches HYBRID_PATTERNS:
    → Use both and merge results
else:
    → Default to rule-based (safer)
```

---

## 3. LLM Prompt Construction

### 3.1 Rule-Based Prompt (Standard Analytics)

**Location:** `/backend/services/llm_service.py` → `create_analysis_prompt()`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RULE-BASED PROMPT STRUCTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  You are {agent_role} for Asset Manager - real estate analytics.      │
│                                                                              │
│  QUESTION: "{user_query}"                                                    │
│                                                                              │
│  === DATA MODEL ===                                                          │
│  LOAN_ACCOUNTS: columns and their meanings...                                │
│  DEPOSIT_ACCOUNTS: columns and their meanings...                             │
│                                                                              │
│  === KPIs ===                                                                │
│  Gross NPA: X% | Provision Coverage: Y% | CASA: Z% | PSL: W% | CD Ratio: V% │
│                                                                              │
│  === PORTFOLIO ===                                                           │
│  Loans: X accounts | ₹Y outstanding | ₹Z NPA                                │
│  Deposits: X accounts | ₹Y balance                                          │
│                                                                              │
│  === LOAN BREAKDOWNS ===                                                     │
│  Asset Class: [{name, count, value}, ...]                                   │
│  DPD Buckets: [{name, count, value}, ...]                                   │
│  PSL: [{name, count, value}, ...]                                           │
│  Product Type: [{name, count, value}, ...]                                  │
│  Gender/Religion/Caste/Occupation/Sector: [...]                             │
│                                                                              │
│  === DEPOSIT BREAKDOWNS ===                                                  │
│  Product: [{name, count, balance}, ...]                                     │
│  Branch: [{branch_code, branch_name, count, balance}, ...]                  │
│  Maturity: [{bucket, count, balance}, ...]                                  │
│                                                                              │
│  === TOP CONCENTRATIONS ===                                                  │
│  Top Loan Exposures: [{name, amount, percent}, ...]                         │
│  Top Depositors: [{name, amount, percent}, ...]                             │
│                                                                              │
│  === SAMPLE DATA ===                                                         │
│  Sample Loans: [{account details}, ...]                                     │
│  Sample Deposits: [{account details}, ...]                                  │
│                                                                              │
│  === RESPONSE FORMAT INSTRUCTIONS ===                                        │
│  Return valid JSON with:                                                     │
│  - "response": detailed text explanation                                     │
│  - "charts": array of chart objects                                         │
│  - "tables": array of table objects                                         │
│  - "summary_points": array of key insights                                  │
│                                                                              │
│  CRITICAL RULES:                                                             │
│  - Use exact numbers from data                                               │
│  - Format currency with ₹ symbol                                            │
│  - NEVER create fake data                                                    │
│  - Return only actual records that exist                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Semantic Prompt (Vanna SQL Results)

**Location:** `/backend/services/llm_service.py` → `create_semantic_prompt()`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SEMANTIC PROMPT STRUCTURE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  You are {agent_role} for Asset Manager - real estate analytics.      │
│                                                                              │
│  QUESTION: "{user_query}"                                                    │
│                                                                              │
│  === SQL QUERY EXECUTED ===                                                  │
│  ```sql                                                                      │
│  SELECT i_customer_id, i_customer_name, i_outstanding_principal...          │
│  FROM loan_accounts                                                          │
│  WHERE d_asset_class IN ('DB1', 'DB2', 'DB3')                               │
│  ORDER BY i_outstanding_principal DESC                                       │
│  LIMIT 10                                                                    │
│  ```                                                                         │
│                                                                              │
│  === QUERY RESULTS ===                                                       │
│  Columns: ["i_customer_id", "i_customer_name", "i_outstanding_principal"]   │
│  Total Rows: 10                                                              │
│  Data Summary: Query returned 10 rows with 3 columns...                     │
│                                                                              │
│  === DATA ===                                                                │
│  [                                                                           │
│    {"i_customer_id": 123, "i_customer_name": "ABC", "amount": 50000},       │
│    {"i_customer_id": 456, "i_customer_name": "XYZ", "amount": 45000},       │
│    ...                                                                       │
│  ]                                                                           │
│                                                                              │
│  === CHART SUGGESTION ===                                                    │
│  - Recommended type: bar                                                     │
│  - Category column: i_customer_name                                          │
│  - Value column: i_outstanding_principal                                     │
│                                                                              │
│  === INSTRUCTIONS ===                                                        │
│  1. Analyze the SQL query results and explain clearly                       │
│  2. Highlight key insights                                                   │
│  3. Format numbers with ₹ symbol for currency                               │
│  4. Create visualizations if appropriate                                     │
│  5. Do NOT invent data                                                       │
│                                                                              │
│  === RESPONSE FORMAT ===                                                     │
│  Return valid JSON with: response, charts, tables, summary_points           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. LLM Response Format

### Expected JSON Structure from LLM:

```json
{
  "response": "Based on the analysis, there are 10 NPA accounts with total outstanding of ₹5.2 Cr. The highest exposure is to Customer ABC with ₹50,000 outstanding...",
  
  "charts": [
    {
      "type": "bar",
      "title": "Top 10 NPA Accounts by Outstanding",
      "description": "Customers with highest NPA amounts",
      "data": [
        {"name": "Customer ABC", "value": 50000},
        {"name": "Customer XYZ", "value": 45000},
        {"name": "Customer DEF", "value": 40000}
      ]
    },
    {
      "type": "donut",
      "title": "NPA Distribution by Asset Class",
      "description": "Breakdown of NPA by classification",
      "data": [
        {"name": "DB1 (Substandard)", "value": 2500000},
        {"name": "DB2 (Doubtful)", "value": 1800000},
        {"name": "DB3 (Loss)", "value": 900000}
      ]
    }
  ],
  
  "tables": [
    {
      "title": "Top 10 NPA Accounts",
      "description": "Detailed list of highest NPA exposures",
      "headers": ["Customer ID", "Customer Name", "Outstanding", "Asset Class", "DPD"],
      "rows": [
        ["123", "Customer ABC", "₹50,000", "DB1", "95"],
        ["456", "Customer XYZ", "₹45,000", "DB2", "180"],
        ["789", "Customer DEF", "₹40,000", "DB1", "120"]
      ]
    }
  ],
  
  "summary_points": [
    "Total NPA outstanding is ₹5.2 Cr across 10 accounts",
    "Customer ABC has the highest exposure at ₹50,000",
    "60% of NPA is classified as DB1 (Substandard)",
    "Average DPD for NPA accounts is 145 days",
    "Provision coverage for these accounts is 72%"
  ]
}
```

### Chart Types Supported:
- `bar` - Horizontal/Vertical bar charts
- `donut` / `pie` - Circular charts for proportions
- `line` - Time series or trend data

---

## 5. Response Parsing

### Location: `/backend/utils/response_parser.py`

```python
def parse_llm_response(content: str) -> ChatResponse:
    """
    1. Try to extract JSON from response
    2. Handle markdown code blocks (```json ... ```)
    3. Validate required fields
    4. Convert to ChatResponse object
    5. Fallback to plain text if JSON parsing fails
    """
```

### Parsing Steps:

1. **Extract JSON**: Remove markdown formatting, find JSON object
2. **Validate Structure**: Check for required keys
3. **Build ChatResponse**:
   - `response`: Main text explanation
   - `charts`: List of ChartData objects
   - `tables`: List of TableData objects  
   - `summary_points`: List of strings

---

## 6. PDF Generation

### **PDF Generation is CODE-BASED, NOT LLM-GENERATED**

**Location:** `/frontend/src/components/chat/ChatMessage.js`

### Technology Stack:
- **html2canvas**: Renders DOM elements as images
- **jsPDF**: Creates PDF document
- **jspdf-autotable**: Handles table rendering in PDF

### PDF Generation Flow:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PDF GENERATION FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. User clicks "Export PDF" button                                          │
│                                                                              │
│  2. exportToPDF() function is called                                         │
│                                                                              │
│  3. Create new jsPDF document (A4 size)                                      │
│                                                                              │
│  4. Add Header:                                                              │
│     - "Asset Manager - Chat Export"                                          │
│     - Timestamp                                                              │
│     - User question                                                          │
│                                                                              │
│  5. Add AI Response Text:                                                    │
│     - Split into lines                                                       │
│     - Handle page breaks                                                     │
│     - Format with proper margins                                             │
│                                                                              │
│  6. Render Key Insights (if present):                                        │
│     - Use html2canvas to capture as image                                    │
│     - Add image to PDF                                                       │
│                                                                              │
│  7. Render Charts (if present):                                              │
│     - Use html2canvas to capture each chart                                  │
│     - Scale and position in PDF                                              │
│     - Handle page breaks                                                     │
│                                                                              │
│  8. Render Tables (if present):                                              │
│     - Use html2canvas OR jspdf-autotable                                    │
│     - Preserve formatting                                                    │
│     - Handle multi-page tables                                               │
│                                                                              │
│  9. Add Footer:                                                              │
│     - Page numbers                                                           │
│     - "Generated by Asset Manager AI"                                        │
│                                                                              │
│  10. Save PDF:                                                               │
│      - Filename: "finsight-chat-export-{timestamp}.pdf"                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Points About PDF:

1. **NOT Generated by LLM**: The PDF is created entirely by frontend JavaScript code
2. **html2canvas for Visual Fidelity**: Charts and formatted content are rendered as images to preserve styling
3. **jsPDF for Document Creation**: Creates the actual PDF structure
4. **Code Location**: All PDF logic is in `ChatMessage.js` in the `exportToPDF` function

### Why html2canvas Instead of Direct PDF Rendering?

- Charts (Recharts) use SVG which jsPDF doesn't handle well directly
- Complex CSS styling (gradients, shadows) need visual rendering
- Currency symbols (₹) and special characters render correctly
- Preserves exact visual appearance from browser

---

## 7. File References

### Backend Files:

| File | Purpose |
|------|---------|
| `/backend/routes/chat.py` | API endpoint for chat |
| `/backend/services/chat_service.py` | Conversation management |
| `/backend/services/analytics_service.py` | Query routing & data gathering |
| `/backend/services/llm_service.py` | Prompt building & LLM calls |
| `/backend/services/semantic_layer/vanna_client.py` | Vanna SQL generation |
| `/backend/services/semantic_layer/query_router.py` | Query classification |
| `/backend/services/semantic_layer/sql_validator.py` | SQL safety checks |
| `/backend/services/semantic_layer/result_formatter.py` | Format data for LLM |
| `/backend/services/semantic_layer/flow_logger.py` | Detailed flow logging |
| `/backend/utils/response_parser.py` | Parse LLM JSON response |

### Frontend Files:

| File | Purpose |
|------|---------|
| `/frontend/src/pages/Chat.js` | Main chat page |
| `/frontend/src/components/chat/ChatMessage.js` | Message rendering & PDF export |
| `/frontend/src/components/chat/TableRenderer.js` | Table component |
| `/frontend/src/components/chat/ChartComponents.js` | Chart components |

### Log Files:

| File | Purpose |
|------|---------|
| `/backend/logs/semantic_layer.log` | Detailed query flow logs |
| `/backend/chat_flow.log` | Chat-specific logs |

---

## Summary

| Component | Technology | Location |
|-----------|------------|----------|
| Query Routing | Python (pattern matching) | Backend |
| SQL Generation | Vanna AI + FAISS | Backend |
| Prompt Building | Python string formatting | Backend |
| LLM Processing | OpenAI GPT-4 API | External |
| Response Parsing | Python JSON parsing | Backend |
| Chart Rendering | Recharts (React) | Frontend |
| Table Rendering | React components | Frontend |
| **PDF Generation** | **html2canvas + jsPDF (CODE)** | **Frontend** |

---

*Last Updated: January 2026*
