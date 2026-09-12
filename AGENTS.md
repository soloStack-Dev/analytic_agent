# AGENTS.md

## Status: application built, planning docs still authoritative for rules

The root markdown files are the source of truth for **rules and constraints**
(stack, architecture, upload security):

- `PROJECT_SPEC.md` — product spec, stack, architecture, AI rules (read first)
- `architect.md` — architecture flow diagram
- `file-info.md` — file-upload security checklist
- `large-dataset-rule.md` — what the LLM is allowed to see

The actual code lives in `app/`; `file-path.md` described the original planned
layout and was adapted (chat UI added home/chat pages + JSON chat history).
`README.md` documents the current layout and run commands.

## Non-negotiable architecture rules

- **The LLM must never execute arbitrary Python.** It produces a structured
  analysis "chart plan" → validated → executed by predefined Pandas/Matplotlib
  functions. No `exec()` of LLM-generated code (PROJECT_SPEC.md §7). The plan
  schema is validated in `app/agent/tools.py` against the dataset metadata.
- **Never send full dataset rows to the LLM.** It only receives metadata:
  schema, statistics, sample rows, unique values (large-dataset-rule.md).
  `analysis/statistics.py` builds this; `agent/tools.py` sends only that.
- **Never execute or modify uploaded files**; parse as data only (Pandas for
  JSON/CSV, openpyxl for XLSX, xlrd for XLS).
- LLM provider must be configurable via environment variables (`.env`,
  python-dotenv) — see `app/config.py` and `.env.example`.
- If `LLM_API_KEY` is empty, `app/agent/nodes.py` falls back to a rule-based
  planner so the app still works offline. Don't remove this fallback.

## Architecture (how it's wired)

- `app/langgraph graph`: `agent.graph` → pipeline `inspect → plan → execute →
  finalize`. `inspect` caches the parsed DataFrame per chat in
  `services/session_store` (in-memory, keyed by chat_id) — follow-up messages
  reuse it. `plan` (LLM or heuristic) → `execute` (pandas `analysis/analyzer`
  + matplotlib `charts/generator`) → `finalize` (builds the bot message).
- Routes: `pages.py` (home + chat pages, history), `chat.py` (POST /api/chat,
  HTMX, rate-limited), `upload.py` (upload security), `analysis.py`
  (agent orchestration), `chart.py` (serve latest chart PNG).
- Chat history is a JSON file (`data/chats.json`) via `services/history.py`.
  Current chat id is carried in a `chat_id` cookie.
- HTMX responses are fragments returning `partials/messages.html`, sometimes
  with `hx-swap-oob` sidebar refresh. Templates in `app/templating.py` share
  one `Jinja2Templates` instance with the `short_ts` filter — new templates
  must use it, not a fresh instance.

## Quirks (hard-earned)

- **Starlette 1.6.0**: `TemplateResponse` signature is
  `TemplateResponse(request, name, context)` — NOT the old
  `TemplateResponse(name, {"request": ...})`. Use the shared instance.
- **pandas 3.0.5**: string columns use the `str` dtype, NOT `object`. Detect
  with `pd.api.types.is_string_dtype()` (see `statistics.py`). Use `format=
  "mixed"` on `pd.to_datetime` guesses; use freq `ME/QE/YE` not `M/Q/Y`.
- **LangGraph 1.2**: state is a plain `TypedDict` (`agent/state.py`); nodes
  return partial dicts of declared keys only. No checkpointer is used.
- Python is 3.14.3; the venv already has fastapi, uvicorn, pandas, numpy,
  matplotlib, openpyxl, xlrd, langchain, langgraph, python-dotenv,
  python-multipart, **jinja2** (added during build), httpx.
- HTMX is served from `node_modules/htmx.org/dist` mounted at `/htmx`;
  charts at `/generated`; static assets at `/static`. uploads/ is never served.

## Environment

- Activate venv: `.venv\Scripts\Activate.ps1`
- Run server: `uvicorn app.main:app --reload` (from the venv, repo root).
- Frontend dependency (htmx) via bun: `bun add <pkg>`; `package.json` pins
  `htmx.org` 2.0.10.
- Configure LLM in `.env` (copy from `.env.example`); `.env` is git-ignored.
  Either generic `LLM_PROVIDER`/`LLM_API_KEY`/`LLM_MODEL` or the dedicated
  `OPEN_ROUTER_API_KEY`/`OPEN_ROUTER_MODEL` pair (provider inferred as
  `openrouter`, base URL auto-set) — see `app/config.py`, which gives the
  generic `LLM_*` vars priority.
- Runtime dirs `uploads/`, `generated/`, `data/`, `logs/` are git-ignored.
- No tests, lint, formatter, or CI config exists yet.
- `logs/error.log` + `logs/app.log` capture runtime errors; `logs/DEV_LOG.md`
  records build-time issues and their fixes.

## Operative rules to honor

- Uploads: enforce size limit, allowed extensions, random UUID filenames,
  store outside executable dirs, delete replaced temp files, sanitize shown
  names, rate-limit chat posts (file-info.md). `routes/upload.py` owns this.
- The AI is a planner/orchestrator: user request + dataset metadata → plan →
  validated safe Python → chart + explanation + insights + warnings.
- Keep inbox clean: never commit `.env` or runtime data; add secrets only to
  `.env`.