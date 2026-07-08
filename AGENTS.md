# AGENTS.md

## Overview

Two Textual TUI applications that model game financial runways over 12 months. Each is a standalone single-file Python app using the [Textual](https://textual.textualize.io/) framework for an interactive terminal UI with a sidebar of tunable parameters, scenario management, and data tables showing daily (90 days) + monthly (months 4–12) projections.

- **`runway.py`** — Mobile game simulator. Models F2P (IAP + Ads), Premium, Remove Ads, and Subscription business models with CPI-based UA, ARPPU monetization, ad revenue, and recurring subscriptions.
- **`web_runway.py`** — Web game simulator. Models RPM-based monetization across four portal types (Web Portal, Playable Ads, Social App Mini Game, Custom Web) with session-based ad impressions and CDN costs.

## Running

```bash
./runway.sh        # mobile game simulator (cd's to project dir, runs via venv)
./web_runway.sh    # web game simulator
.venv/bin/python runway.py       # direct
.venv/bin/python web_runway.py   # direct
```

## Documentation Maintenance

**Keep `README.md` in sync with the code.** When you add, rename, or remove a parameter, tab, feature, or key binding in *either* app, update `README.md` in the same change. The parameters tables, tabs, and scenario lists are the most commonly stale sections.

No build step. Dependencies are pre-installed in `.venv` (Python 3.14). Key packages: `textual`, `rich`.

**Key bindings:** `ctrl+r` recalculate, `ctrl+t` switch tab, `ctrl+s` switch panel, `ctrl+1`/`ctrl+2`/`ctrl+3` apply solver values (on Target Solver tab), `ctrl+q` quit, `escape` revert/unfocus. All shortcuts use Ctrl modifiers to avoid conflicts with text input.

## Architecture

Both apps share the same structural pattern. Each is a single file:

**`runway.py`** (~1540 lines):

- **`ScenarioStore`** — JSON-backed (`scenarios.json`) CRUD for named parameter snapshots. Auto-seeds 4 built-in scenarios on first run.
- **`RevenueLagEngine`** — Pure simulation engine. Models UA cohorts, power-law retention, IAP monetization (ARPPU + payer conversion), ad revenue, CPI saturation, recursive virality, platform fees, payout delays, starting capital, auto-scaling UA, scaling OpEx, subscriber cohort tracking with churn, and billing period options. `calculate_timeline()` computes 365 days internally, returns 90 daily rows + 9 monthly summaries.
- **`BusinessModelTUI(App)`** — Textual TUI. Sidebar with scenario selector + collapsible parameter sections (~30 inputs). Four tabs: "12-Month Runway" (timeline table with model-appropriate activity metric), "Compare Scenarios" (side-by-side summary metrics), "Spend Analysis" (sensitivity table), and "Target Solver" (goal-seeking with LTV breakdown). KPI bar includes a health diagnosis line that flags per-install profitability issues.

**`web_runway.py`** (~1400 lines):

- **`ScenarioStore`** — JSON-backed (`web_scenarios.json`) CRUD. Auto-seeds 4 built-in scenarios.
- **`WebGameEngine`** — Simulation engine for RPM-based web game economics. Models organic/paid plays, session-based ad impressions, fill rate, portal rev-shares, IAP, CDN costs, and viral spread. Includes LTV breakdown logic.
- **`WebGameTUI(App)`** — Textual TUI. Sidebar with scenario selector + collapsible parameter sections. Four tabs: "12-Month Runway", "Compare Scenarios", "Portal Comparison" (same params across all four portals), and "Target Solver" (with LTV breakdown). KPI bar includes a health diagnosis line that uses daily cash-flow sustainability for organic-only scenarios and LTV-vs-CPI for paid UA.

`EXPOSED_PARAMS` in each file is the single source of truth linking engine attributes ↔ widget IDs ↔ type cast functions. Both `action_recalculate()` and `_load_scenario()` iterate over it generically — no per-field boilerplate.

**`api.py`** (~850 lines):

- **`MobileGameAPI`** and **`WebGameAPI`** — Agent-friendly programmatic wrappers around the engines. No TUI or Textual dependency required. Provides `evaluate()` (full simulation + structured results), `sensitivity()` (parameter sweeps), `solve()` (goal-seeking), `list_models()`, `parameter_schema()`, and `default_scenario()`. See **`AGENT_API.md`** for agent-facing documentation.

## Key Patterns

- **Auto-recalculation:** Every `Input.Changed` event triggers `action_recalculate()`, which re-reads all inputs, runs the full 365-day simulation, and redraws. `try/except ValueError` swallows partial input (mid-typing a decimal).
- **Scenario loading guard:** `_loading_scenario` flag prevents recursive input-changed events when programmatically setting input values during scenario load.
- **Cohort tracking:** Each day's installs stored as a separate cohort in `cohort_history`. Power-law retention applied to each historical cohort to compute DAU.
- **Accrual vs. cash:** Engine distinguishes accrued (paper) revenue from settled cash inflow, governed by `payout_delay_days`.
- **Monthly aggregation:** Days 91–365 are grouped by calendar month. Summed for revenue/costs, last-day snapshot for DAU and bank balance. Labeled `YYYY-MM (month)`.
- **CPI saturation:** `effective_cpi = base_cpi * (1 + saturation * ln(1 + cumulative_paid / 10000))`. Scales logarithmically — fast rise early, plateau later.
- **Recursive virality:** `viral_installs = first_wave / (1 - k_factor)` (geometric series). Clamped to `first_wave * 10` if k ≥ 1.0.
- **Subscriber cohort tracking (subscription model):** Each day, `new_subscribers = installs × conversion`. Subscribers decay at `daily_churn = 1 − (1 − monthly_churn/100)^(1/30)`. Revenue = `active_subs × daily_rate × (1 − platform_fee)`.
- **Model-appropriate activity metrics:** The timeline table, KPI bar, compare table, and sensitivity table show different activity metrics depending on model type: DAU (F2P, Remove Ads), installs (Premium), or active subscribers (Subscription). Column headers relabel dynamically via `_update_activity_labels()`.
- **Rich markup:** Table cells use inline Rich markup for conditional coloring. The space before `[/]` on negative cash flow is intentional (reverse-video trigger). All closing tags must have their `]` — a missing `]` in `[/` causes a `MarkupError` that only surfaces at runtime when the widget renders.
- **Timeline-sourced CPI cache:** `calculate_timeline()` populates `_cached_blended_cpi`, `_cached_all_user_cpi`, and `_cached_realized_ltv` as float accumulators during the 365-day loop — no extra iterations. `_compute_blended_cpi()` and `_compute_all_user_cpi()` return the cache when available (normal TUI/API path) and fall back to a standalone loop otherwise (solver/sensitivity paths). `_clear_caches()` is called at the start of `calculate_timeline()` and before each `target_fn()` call in `solve_parameter()`.
- **Realized vs. analytical LTV:** `calculate_ltv()` returns the analytical per-install LTV (assumes each install gets its full retention lifetime). `get_realized_ltv()` returns `total_revenue / total_installs` from the actual 365-day timeline — cohorts arriving later in the year have truncated revenue. The health diagnosis uses realized LTV to stay consistent with the bank-balance trajectory. The KPI bar and breakdown still show analytical LTV for reference.
- **Auto-scaling UA (mobile):** Scaler uses `analytical_ltv / effective_cpi` as the ratio signal (computed once per `calculate_timeline()` call). Scales spend up when ratio > `target_roi`, throttles as CPI saturation erodes ratio. The old cash-flow-based heuristic was broken by `payout_delay_days`.

## Gotchas

- `mypy` fails on `textual.*` imports unless `--ignore-missing-imports` is used (no stubs in venv).
- Python 3.14 in venv — some tools may not fully support it yet.
- `scenarios.json` is auto-created from `DEFAULT_SCENARIOS` if missing. Delete it to reset to defaults.
- Monthly rows show aggregated totals (summed revenue/expenses), not daily averages. Values will be ~30x larger than daily rows.
- Removing `scenarios.json` is the only way to reset scenarios — there's no in-app "reset to defaults".
- **Textual CSS ≠ web CSS.** Bare numbers are character cells (not pixels); `Input` height includes its border (so `height: 3` = 1 border + 1 content + 1 border); `Input` does not auto-fill width inside a `Vertical` (hence the base `Input { width: 100% }` rule). Vertical gaps between fields come from `Label { margin-top: 1 }`, not `Input` margins.
- **Collapsible sidebar sections:** Parameters are grouped into `Collapsible` widgets via `section()`. Most start collapsed; only "Launch & Capital" and "Marketing Capital" start expanded.
- **Sidebar fields go through `labeled_input()`**, which yields a `Label` + `Input` pair with a derived label id (`in_foo` → `lbl_foo`). Add new fields by calling it; don't hand-place `Label`/`Input` separately. Group headers (`"SCENARIO"`, `"BUSINESS MODEL"`) are standalone `Label(..., classes="setting-group")`.
- **Remember to update `README.md`** when parameters, tabs, or key bindings change (see Documentation Maintenance above).
