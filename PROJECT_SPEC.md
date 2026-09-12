# AI Data Analyst & Chart Generator

## 1. Project Overview

Build an AI-powered data analysis web application that allows users to upload
structured data files such as JSON, CSV, and Excel files and ask questions about
their data using natural language.

The application uses an AI agent to understand the user's request, inspect the
uploaded dataset, determine the appropriate analysis and visualization, and
then use Python-based data analysis and Matplotlib to generate the requested
chart.

The AI should act primarily as an intelligent planner/orchestrator.

Python, Pandas, NumPy, and Matplotlib must perform the actual data processing,
calculations, aggregation, and visualization.

The application should return:

1. Generated chart
2. Short explanation of the analysis
3. Important insights discovered from the data
4. Information about the chart that was selected
5. Any warnings about missing, invalid, or insufficient data


---

# 2. Main Purpose

The purpose of this application is to create a simple AI-powered data analyst
that allows a normal user to analyze datasets without manually writing Python
or SQL code.

Example:

User uploads:

    sales.xlsx

Then enters:

    "Show me the monthly sales trend."

The application should automatically:

1. Read the Excel file
2. Inspect the dataset
3. Understand the user's request
4. Identify the relevant columns
5. Determine the required analysis
6. Select an appropriate chart type
7. Perform the calculation using Pandas
8. Generate the chart using Matplotlib
9. Explain the result
10. Display the result in the web UI


---

# 3. Example User Experience

The UI should contain:

- File upload
- Natural-language prompt input
- Analyze button
- Loading state
- Result section
- Generated chart
- Analysis explanation
- Dataset information
- Error/warning messages


Example:

    --------------------------------------------------
                 AI DATA ANALYST
    --------------------------------------------------

    Upload your dataset

    [ Choose File ]

    Ask something about your data:

    [ Show monthly sales trend              ]

                  [ Analyze ]

    --------------------------------------------------

    Result

    Chart: Line Chart

    [ Generated Matplotlib Chart ]

    Analysis:

    Sales increased consistently from January
    to March.

    --------------------------------------------------


---

# 4. Supported File Types

The first version should support:

- JSON
- CSV
- XLSX
- XLS

Do not execute uploaded files.

Only parse them as data.

Use:

- Pandas for JSON and CSV
- OpenPyXL for XLSX
- xlrd for XLS


---

# 5. Technology Stack

## Frontend

- HTML
- CSS
- HTMX

Do not use React or Next.js for this project.

The frontend should remain lightweight and server-rendered.

## Backend

- Python
- FastAPI
- Uvicorn

## Data Analysis

- Pandas
- NumPy

## File Processing

- OpenPyXL
- xlrd

## Visualization

- Matplotlib

Optional:

- Seaborn

Do not make Seaborn mandatory for the first version.

## AI

- LangChain
- LangGraph
- LLM provider

The LLM provider should be configurable through environment variables.

## Configuration

- python-dotenv


---

# 6. Recommended Architecture

Use this architecture:

    User
      |
      | Prompt + File
      v
    HTMX
      |
      v
    FastAPI
      |
      +----------------------+
      |                      |
      v                      v
    File Reader          Dataset Metadata
      |                      |
      v                      |
    Pandas                   |
      |                      |
      +----------+-----------+
                 |
                 v
            LangGraph Agent
                 |
                 v
            Analysis Plan
                 |
                 v
             Validation
                 |
                 v
             Pandas
                 |
                 v
          Data Analysis
                 |
                 v
            Matplotlib
                 |
                 v
          Generated Chart
                 |
                 v
              FastAPI
                 |
                 v
               HTMX
                 |
                 v
        Chart + Explanation


---

# 7. Important AI Architecture Rule

DO NOT allow the LLM to directly execute arbitrary Python code.

Avoid this architecture:

    User
      |
      v
    LLM
      |
      v
    Generate Python code
      |
      v
    exec(code)

This creates serious security risks.

Instead use:

    User
      |
      v
    LLM
      |
      v
    Structured Analysis Plan
      |
      v
    Validate Plan
      |
      v
    Predefined Python Functions
      |
      v
    Pandas + Matplotlib

The LLM should decide WHAT needs to happen.

Python should decide HOW the operation is safely executed.


---

# 8. AI Agent Responsibilities

The AI agent should:

1. Understand the user's natural-language request
2. Inspect dataset metadata
3. Identify relevant columns
4. Determine the required analysis
5. Determine the appropriate chart
6. Select aggregation methods
7. Produce a structured analysis plan
8. Request additional information when the request is ambiguous
9. Pass the plan to safe Python tools
10. Generate a concise explanation of the result


---

# 9. AI Agent Should NOT

The agent should NOT:

- Execute arbitrary Python
- Modify the original uploaded file
- Delete user data
- Access unrelated files
- Execute shell commands
- Execute SQL directly without controlled tools
- Invent data
- Invent statistics
- Invent column names
- Pretend a calculation succeeded when it failed


---

# 10. Dataset Inspection

When a file is uploaded, use Pandas to inspect it.

Generate dataset metadata such as:

- File name
- File type
- Number of rows
- Number of columns
- Column names
- Data types
- Missing values
- Unique value counts
- Numeric columns
- Categorical columns
- Date/time columns
- Basic statistics


Example metadata:

```json
{
  "rows": 5000,
  "columns": [
    {
      "name": "Date",
      "type": "datetime"
    },
    {
      "name": "Product",
      "type": "string"
    },
    {
      "name": "Sales",
      "type": "float"
    }
  ],
  "missing_values": {
    "Date": 0,
    "Product": 12,
    "Sales": 4
  }
}


### One change I'd strongly recommend

Your original stack:

**HTMX + CSS + Python + Matplotlib + FastAPI + LangChain**

is good, but for the **agent part**, make it:

**HTMX + CSS + FastAPI + Pandas + NumPy + Matplotlib + LangChain + LangGraph**

The most important separation is:

> **LangGraph/LangChain = brain/planner**  
> **Pandas/NumPy = data analyst**  
> **Matplotlib = visualization engine**  
> **FastAPI = backend**  
> **HTMX = UI interaction**

That gives you a much cleaner architecture than asking an LLM to generate and execute Python code.

"Upload your data.
 Ask a question.
 Get the analysis and chart."