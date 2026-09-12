# analytic_agent
<div align="center">

# AI Data Analyst

### Ask your data anything — get charts, explanations, and insights in plain words

[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white&style=for-the-badge)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white&style=for-the-badge)](https://fastapi.tiangolo.com)
[![HTMX](https://img.shields.io/badge/HTMX-2.0-3D72D4?logo=htmx&logoColor=white&style=for-the-badge)](https://htmx.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![pandas](https://img.shields.io/badge/pandas-3.0-150458?logo=pandas&logoColor=white&style=for-the-badge)](https://pandas.pydata.org)
[![Matplotlib](https://img.shields.io/badge/Matplotlib-3.11-11557C?logo=python&logoColor=white&style=for-the-badge)](https://matplotlib.org)

**Upload a CSV, JSON or Excel file. Ask a question in natural language.
The AI plans, Pandas computes, Matplotlib draws.**

</div>

---

## Why this exists

Most "AI data tools" ask an LLM to write and execute code against your data —
a black box that can fabricate results or run arbitrary operations. This app
inverts that model:

> **The LLM decides WHAT to analyze. Safe, predefined Pandas and Matplotlib
> functions decide HOW it is executed.**

The result is an open, auditable pipeline where an AI agent produces a small,
schema-validated **analysis plan**, and only a fixed set of functions ever
touches your data.

---

## Features

| | |
|---|---|
| **Natural-language analysis** | Ask "show me the monthly sales trend" — no SQL, no Python, no formulas. |
| **5 chart types + tables** | Line, bar, pie, scatter, and histogram rendered server-side with Matplotlib. |
| **Human-readable answers** | Every answer includes a short explanation, key insight bullets, and warnings. |
| **Safe by design** | The LLM never executes code and never sees full datasets — only metadata. |
| **Pluggable LLMs** | Works with OpenRouter, OpenAI, Groq, Ollama, DeepSeek, or any OpenAI-compatible endpoint. |
| **Offline fallback** | No API key? A built-in rule-based planner keeps the app fully usable. |
| **Chat with history** | Sidebar navigation, JSON-backed chat history, follow-up questions reuse your dataset. |
| **Hardened uploads** | Extension + size checks, random filenames, uploads stored outside executable dirs. |

---

## How it works

```
   User prompt + file
           │
           ▼
┌─────────────────────┐     schema / statistics     ┌──────────────────────┐
│  File reader (Pandas│ ───────────────────────────▶ │   LangGraph agent    │
│  / openpyxl / xlrd) │  (metadata ONLY, no rows)   │  planner + explainer │
└─────────┬───────────┘                              └─────────┬────────────┘
          │                                                   │
          ▼                                                   │
   cleaned DataFrame                                          │
          │                                    structured chart plan (JSON)
          ▼                                                   ▼
┌──────────────────────┐                    ┌──────────────────────────────┐
│  Plan validation     │ ◀──────────────────│  chart_type, x, y, aggregate │
│  (schema-checked)    │                    └──────────────────────────────┘
└─────────┬────────────┘
          ▼
┌───────────────────────────────────────────┐
│  Predefined execution: Pandas analysis +  │
│  Matplotlib rendering → chart PNG         │
└───────────────────────────────────────────┘
          ▼
   Chart + explanation + insights + warnings
```

### The agent pipeline

A small LangGraph state machine orchestrates every answer:

```
inspect ─▶ plan ─▶ execute ─▶ finalize
```

1. **inspect** — parses the uploaded file and builds dataset *metadata only*
   (schema, types, stats, unique values, 5 sample rows). The parsed frame is
   cached per chat, so follow-ups reuse it.
2. **plan** — the LLM reads the metadata + your question and emits a
   structured JSON plan. If the LLM is unavailable, a heuristic planner
   takes over.
3. **execute** — the plan is validated against the real schema, then passed
   to predefined pandas/matplotlib functions. Nothing arbitrary runs.
4. **finalize** — builds your answer: chart, explanation, insights, warnings.

### Supported files

| Format | Engine | Notes |
|---|---|---|
| CSV | pandas | separator auto-detected |
| JSON | pandas | objects & arrays of objects |
| XLSX | openpyxl | modern Excel |
| XLS | xlrd | legacy Excel |

---

## Quick start

### 1. Install

```powershell
cd chart-Agent
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
bun install                 # HTMX assets (pinned htmx.org 2.0.10)
```

### 2. Configure your LLM

```powershell
Copy-Item .env.example .env
```

Then edit `.env`. The fastest path is OpenRouter:

```dotenv
OPEN_ROUTER_API_KEY=sk-or-v1-...
OPEN_ROUTER_MODEL=nex-agi/nex-n2.5-mini:free
```

Any OpenAI-compatible provider works too:

```dotenv
LLM_PROVIDER=openai          # openai | ollama | groq | openrouter | deepseek
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
# LLM_BASE_URL=https://...   # optional override
```

> No key? Skip this step — the app ships a rule-based fallback planner so it
> works offline with zero configuration.

### 3. Run

```powershell
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000**, click **Let's Chat**, attach a dataset, and ask:

```
Show me the monthly sales trend
```

Expected result: a line chart of monthly totals, a one-paragraph explanation,
insight bullets (totals, peaks, direction of change), and any warnings.

---

## The analysis plan

The LLM's plan is a small JSON document — and the only thing it's allowed to
produce:

```json
{
  "chart_type": "line",
  "x_column": "Date",
  "y_column": "Sales",
  "aggregation": "sum",
  "group_by_period": "month",
  "top_n": 10,
  "chart_title": "Monthly Sales Trend",
  "explanation_plan": "Trend of total sales over time, grouped by month."
}
```

This is validated against the dataset metadata before execution: chart type
must be in the allowlist, columns must exist, aggregations must be one of
`sum | mean | median | min | max | count`, and time periods one of
`day | week | month | quarter | year`.

---

## Project structure

```
app/
├── main.py                 # FastAPI app + static mounts
├── config.py               # .env settings, runtime dirs
├── templating.py           # shared Jinja2 instance + filters
├── logger.py               # app.log / error.log + console
├── agent/                  # LangGraph: graph, nodes, state, plan tools
│   ├── graph.py            #   inspect → plan → execute → finalize
│   ├── tools.py            #   plan schema, validation, prompts
├── routes/                 # pages, chat, upload, analysis, chart
├── analysis/               # cleaner, statistics (metadata), analyzer
├── charts/                 # line / bar / pie / scatter / histogram
├── services/               # file reader, LLM client, JSON history, session store
├── templates/              # home, chat page, HTMX partials
└── static/                 # css + js

uploads/                    # runtime: uploaded files   (git-ignored)
generated/                  # runtime: chart PNGs       (git-ignored)
data/chats.json             # runtime: chat history DB  (git-ignored)
logs/                       # runtime: logs             (git-ignored)
```

---

## Security model

Everything follows the rules in `PROJECT_SPEC.md`, `file-info.md`, and
`large-dataset-rule.md`:

- **The LLM never executes code.** It only produces a plan that is validated,
  then run through fixed functions. There is no `exec()` in the pipeline.
- **The LLM never sees raw data.** It receives schema, statistics, unique
  values, and 5 sample rows — not full datasets, no matter the file size.
- **Uploads are data-only.** Files are parsed with pandas/openpyxl/xlrd, stored
  in an unserved directory under random UUID names, extension- and
  size-checked (10 MB default), and replaced files are deleted.
- **Rate limited.** Chat posts are throttled per client to discourage abuse.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | HTML + CSS + HTMX | server-rendered, near-zero JS, no framework |
| Backend | FastAPI + Uvicorn | async, typed, self-documenting |
| Data | pandas 3 + NumPy | native analysis engine |
| Charts | Matplotlib | server-side PNG rendering |
| Agent | LangGraph | explicit, inspectable state machine |
| LLM | configurable | OpenRouter/OpenAI/Groq/Ollama/DeepSeek |
| Storage | JSON file | simple, portable chat history |
| Frontend tooling | bun (`node_modules`) | pinned htmx.org 2.0.10 |

---

## Roadmap ideas

- Share-generated-chart URLs / PNG export endpoint
- CSV download of computed aggregates
- XLSX multi-sheet picking
- Chat title generation from the first question
- Vite-free optional bundling / dark mode toggle

---

<div align="center">

Built with FastAPI, HTMX, LangGraph, pandas & Matplotlib.

<span>Runtime issues land in <code>logs/error.log</code>; build lessons are
documented in <code>logs/DEV_LOG.md</code>.</span>

</div>