# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

A lightweight shopping-list web app (add / edit / delete / check items) built with Python + Streamlit, deployed to Streamlit Community Cloud. All 4 stages are done; `REVIEW.md` has the stage-4 results, fixed bugs and open issues. UI notes: rows use `st.container(horizontal=True, wrap=False)` rather than `st.columns` so they never stack on mobile; CSS targets rows via container keys (`st-key-row_{id}` / `st-key-editrow_{id}`); theme is in `.streamlit/config.toml` (server restart needed after editing it). Planning docs:

- `PRD.md` — source of truth for features (F1–F6), data model, UI layout, acceptance criteria (section 10). Check work against it.
- `PROMPTS.md` — the 4-stage build plan (1: skeleton → 2: features → 3: UI → 4: Playwright review). Stay within the scope of the current stage; e.g. stage 1 must not implement features, stage 3 must not change logic.

The user writes in Korean; respond in Korean.

## Commands

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # venv already exists (Python 3.12)
.venv/Scripts/python -m streamlit run app.py                              # dev server, http://localhost:8501
.venv/Scripts/python -m streamlit run app.py --server.headless true       # for Playwright testing (run in background)
```

No unit-test suite or linter. E2E regression is `review/e2e_review.js`, run through the Playwright MCP `browser_run_code_unsafe` tool against a running server with an emptied `data/items.json` (back it up first) — see REVIEW.md §4. It expects an empty list at start.

## Architecture

- `app.py` — Streamlit UI. `st.session_state["items"]` is **re-read from storage on every run**, and every mutating callback is wrapped in `@mutation` (reload under a process-wide `st.cache_resource` lock, then mutate + save). Don't go back to loading once per session — that caused lost updates between tabs/visitors (REVIEW BUG-1); `st.session_state["editing_id"]` tracks the single row in edit mode.
- `storage.py` — only `load_items()` / `save_items(items)`. `app.py` must touch persistence solely through these two functions so the backend (JSON → localStorage → Supabase etc., PRD §7) can be swapped. MVP backend is `data/items.json` (gitignored): missing/corrupt file → empty list; write via temp file + replace; UTF-8 with `ensure_ascii=False`.
- Item shape: `{id: uuid4 str, name: str (1–50 chars, stripped), quantity: int (1–999), checked: bool, created_at: ISO 8601 str}`.

## Streamlit rules that matter here

- Mutate state only in `on_click` / `on_change` callbacks, passing the item `id` via `args`; don't call `st.rerun()` inside callbacks.
- Widget keys must be id-based (`chk_{id}`, `edit_{id}`, `del_{id}`, `name_{id}`, `qty_{id}`), never list indices — the list is re-sorted (unchecked first, then by `created_at`) and items get deleted, so index keys move checkbox/edit state onto the wrong item.
- Call `save_items()` after every mutation.
- User-provided names: `safe_html()` for anything in `unsafe_allow_html` markdown, `md_escape()` for Markdown-rendered text such as `st.toast` and button labels.
- Icon buttons have real labels (`"<name> 수정"` etc.) visually hidden by CSS for screen readers; E2E locators rely on these names. The out-of-range quantity hint is pure CSS (`:has(input:invalid)`), because Streamlit never sends invalid numbers to the server.
- On Streamlit Cloud the JSON file is shared by all visitors and can be wiped on restart/redeploy — a known MVP limitation, not a bug to fix silently.
