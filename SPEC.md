# Runway Calculator — Specification

## Purpose

A single-file Python TUI application that simulates a free-to-play (or premium) mobile game's 12-month financial runway. The user tunes marketing, retention, and monetization parameters via a sidebar and sees projected daily cash flow, bank balance, and key metrics in real time.

**Primary question the tool answers:** "Given these acquisition costs, retention curve, and monetization assumptions, how long until we run out of money — and what levers can we pull to reach breakeven?"

---

## Revenue Models

Three mutually exclusive models selected via a dropdown. The model type controls which sidebar sections are visible and how revenue is computed each day.

| Model | Constant | Revenue Sources | Monetization Sections Shown |
|-------|----------|----------------|----------------------------|
| F2P (IAP + Ads) | `f2p` | In-app purchases (payer conversion × ARPPU) + video ads (eCPM × impressions) | IAP Monetization, Ad Revenue |
| Premium (Buy Once) | `premium` | One-time game purchase at install | Premium Pricing |
| F2P + Remove Ads IAP | `remove_ads` | Ad removal IAP (one-time) for a fraction of users + video ads for the rest | Ad Revenue, Ad Removal IAP |

---

## Simulation Engine (`RevenueLagEngine`)

Simulates 365 days internally. The UI shows 90 daily rows (days 1–90) then monthly aggregated rows for months 4–12.

### Cohort-Based DAU Model

Each day's total installs are stored as a **cohort** with an initial size. On subsequent days, every historical cohort is decayed through the retention curve and summed to compute surviving DAU.

```
DAU(day) = Σ cohort_size[c] × retention_rate(day - c)   for all c ≤ day
         + total_new_installs(day)
```

Note: Today's new installs are added to DAU on their install day (they're retained at 100% for day 0).

### Retention Curve

Power-law decay with a floor:

```
retention_rate(0) = 1.0
retention_rate(1) = d1_rate                    (day_1_retention / 100)
retention_rate(d) = d1_rate × d^(-decay_exponent)   for d ≥ 2
retention_rate(d) = max(retained, d1_rate × 0.12)   floor at 12% of D1
```

The floor prevents retention from reaching zero and ensures long-tail users always exist.

### Install Pipeline

```
effective_cpi = base_cpi × (1 + cpi_saturation × ln(1 + cumulative_paid / 10000))
paid_installs = daily_ua_spend / effective_cpi
base_installs = influencer_installs + paid_installs
organic_installs = base_installs × organic_ratio
first_wave = (base_installs + organic_installs) × k_factor
viral_installs = first_wave / (1 - k_factor)        if k < 1.0
               = first_wave × 10                    if k ≥ 1.0  (geometric series clamp)
total_new_installs = base_installs + organic_installs + viral_installs
```

- **CPI saturation** models diminishing returns on UA spend as the paid audience saturates. The logarithmic curve rises fast early, then plateaus.
- **Viral installs** use a geometric series formula (each wave of viral users recruits another wave). Clamped at 10× the first wave when k ≥ 1.0 to prevent runaway.

### Revenue Per Day (Accrual Basis)

**F2P:**
```
gross_iap = DAU × payer_pct × daily_payer_arppu
gross_ads = DAU × (video_ecpm × video_impressions / 1000)
net_revenue = gross_iap × (1 - platform_fee) + gross_ads × (1 - ad_mediation_tax)
```

**Premium:**
```
net_revenue = total_new_installs × game_price × (1 - platform_fee)
```
Every new install is assumed to purchase (no conversion rate — see Known Issues).

**Remove Ads:**
```
ad_removers = total_new_installs × ad_removal_pct
iap_revenue = ad_removers × ad_removal_price
ad_viewing_dau = DAU × (1 - ad_removal_pct)
ad_revenue = ad_viewing_dau × ad_arpu_per_dau
net_revenue = iap_revenue × (1 - platform_fee) + ad_revenue × (1 - ad_mediation_tax)
```

### Payer ARPPU (IAP Monetization Tier Mix)

A weighted average across four payer tiers. The split percentages and spend amounts are hardcoded:

| Tier | % of Payers | Daily Spend |
|------|-------------|-------------|
| Minnow | 55% | $0.10 |
| Tuna | 27% | $0.50 |
| Dolphin | 15.5% | $2.00 |
| Whale | 2.5% | $10.00 |

`daily_payer_arppu = Σ (tier_pct × tier_spend)` ≈ $0.42 at defaults.

Only `whale_spend` and `payer_pct` are user-tunable. The tier mix is fixed.

### Cash Flow Model

```
cash_inflow(day) = net_revenue(day - payout_delay_days)    # settled cash
ops_outflow(day) = fixed_overhead
                 + (DAU / 1000) × server_cost_per_k_dau
                 + (DAU / 1000) × support_cost_per_k_dau   # hardcoded: $0.04
                 + daily_ua_spend
net_cash_flow = cash_inflow - ops_outflow
bank_balance += net_cash_flow
```

- **Payout delay:** App store / ad network revenue is settled with a configurable delay (default 30 days). During the delay, revenue is accrued but not cash.
- **Ad mediation tax:** A 2% fee deducted from gross ad revenue (hardcoded).
- **Support cost:** $0.04 per 1k DAU (hardcoded, not exposed to UI).

### LTV Calculation

```
lifetime = Σ retention_rate(d) for d in 0..364

F2P:          LTV = (payer_pct × arppu × (1 - platform_fee) + ad_arpu × (1 - mediation_tax)) × lifetime
Premium:      LTV = game_price × (1 - platform_fee)
Remove Ads:   LTV = ad_removal_pct × ad_removal_price × (1 - platform_fee)
               + (1 - ad_removal_pct) × ad_arpu × lifetime × (1 - mediation_tax)
```

LTV:CPI ratio = LTV / CPI. Healthy threshold: ≥ 3.0.

### Solver (Target Solver Tab)

A binary search solver that finds the parameter value needed to hit a target metric. Used for two goals:

1. **Year-end breakeven:** bank_balance at day 365 ≥ $0
2. **LTV:CPI ≥ 3.0**

The solver adjusts one parameter at a time using bisection (15 iterations) over a defined range. Results can be applied to the sidebar with keyboard shortcuts.

| Goal | Parameter | Range |
|------|-----------|-------|
| Breakeven | CPI | $0.01 – $20.00 |
| Breakeven | D1 Retention | 1% – 99% |
| Breakeven | Monetization* | varies by model |
| LTV:CPI ≥ 3.0 | CPI | $0.01 – $20.00 |
| LTV:CPI ≥ 3.0 | D1 Retention | 1% – 99% |
| LTV:CPI ≥ 3.0 | Monetization* | varies by model |

*Monetization parameter depends on model: `payer_pct` (F2P), `game_price` (Premium), `ad_removal_pct` (Remove Ads).

---

## Parameters

### Exposed Parameters (UI Sidebar)

These are the user-tunable inputs. The `EXPOSED_PARAMS` list is the single source of truth linking engine attribute names, widget IDs, and type cast functions.

| Engine Attribute | Widget ID | Type | Description | Default |
|-----------------|-----------|------|-------------|---------|
| `daily_ua_spend` | `in_ua_spend` | float | Daily user acquisition budget ($) | 10.00 |
| `cpi` | `in_cpi` | float | Cost per install ($) | 0.26 |
| `cpi_saturation` | `in_cpi_sat` | float | CPI saturation coefficient | 0.30 |
| `influencer_installs` | `in_influencer` | float | Burst/influencer installs per day | 0.0 |
| `organic_ratio` | `in_organic` | float | Organic installs as fraction of paid | 0.10 |
| `virality_k_factor` | `in_kfactor` | float | Viral coefficient (installs per user) | 0.05 |
| `payer_pct` | `in_payer_pct` | float | Fraction of DAU that makes IAP | 0.03 |
| `whale_spend` | `in_whale_spend` | float | Whale daily spend ($) | 10.00 |
| `video_ecpm` | `in_video_ecpm` | float | Video ad eCPM ($) | 80.00 |
| `video_impressions` | `in_video_impressions` | float | Ad impressions per DAU per day | 0.33 |
| `platform_fee` | `in_platform_fee` | float | App store fee fraction | 0.30 |
| `payout_delay_days` | `in_delay` | int | Revenue settlement delay (days) | 30 |
| `fixed_overhead_daily` | `in_fixed_ops` | float | Fixed daily operating cost ($) | 10.00 |
| `server_cost_per_k_dau` | `in_server_k` | float | Server cost per 1k DAU ($) | 0.12 |
| `day_1_retention` | `in_d1_retention` | float | Day-1 retention (%) | 40.0 |
| `decay_exponent` | `in_decay` | float | Power-law retention decay exponent | 0.55 |
| `game_price` | `in_game_price` | float | Premium game price ($) | 4.99 |
| `ad_removal_price` | `in_ad_removal_price` | float | Ad removal IAP price ($) | 2.99 |
| `ad_removal_pct` | `in_ad_removal_pct` | float | Fraction of users who remove ads | 0.05 |
| `start_date` | `in_start_date` | str | Simulation start date (YYYY-MM-DD) | today |

### Hidden Parameters (Hardcoded)

These are NOT exposed in the UI and are not part of scenarios:

| Attribute | Value | Description |
|-----------|-------|-------------|
| `minnow_pct` | 0.55 | Fraction of payers who are minnows |
| `minnow_spend` | 0.10 | Minnow daily spend ($) |
| `tuna_pct` | 0.27 | Fraction of payers who are tuna |
| `tuna_spend` | 0.50 | Tuna daily spend ($) |
| `dolphin_pct` | 0.155 | Fraction of payers who are dolphins |
| `dolphin_spend` | 2.00 | Dolphin daily spend ($) |
| `whale_pct` | 0.025 | Fraction of payers who are whales |
| `support_cost_per_k_dau` | 0.04 | Support cost per 1k DAU ($) |
| `ad_mediation_tax` | 0.02 | Ad mediation platform fee |

---

## UI Layout

```
┌─────────────────────────────────────────────────────────┐
│ Header: "Runway — 12-Month Financial Runway Simulator"  │
├──────────────┬──────────────────────────────────────────┤
│   Sidebar    │  Focus Indicator                        │
│  (42 cols)   │  ┌────────────────────────────────────┐ │
│              │  │ KPI Summary Bar                     │ │
│ SCENARIO     │  │ LTV · CPI · LTV:CPI · PeakDAU · $  │ │
│ [dropdown]   │  ├────────────────────────────────────┤ │
│ [name input] │  │                                    │ │
│ [Save][Del]  │  │  Tab: 12-Month Runway              │ │
│ [Solve]      │  │  Tab: Compare Scenarios            │ │
│              │  │  Tab: Target Solver                 │ │
│ MODEL TYPE   │  │                                    │ │
│ [dropdown]   │  │  DataTable (timeline / compare /   │ │
│              │  │  solver output)                    │ │
│ Collapsible  │  │                                    │ │
│  sections:   │  │                                    │ │
│  Launch Date │  │                                    │ │
│  Marketing   │  │                                    │ │
│  Growth      │  │                                    │ │
│  IAP *       │  │                                    │ │
│  Ads *       │  │                                    │ │
│  Premium *   │  │                                    │ │
│  RemAds *    │  │                                    │ │
│  Platform    │  │                                    │ │
│  Live-Ops    │  │                                    │ │
├──────────────┴──────────────────────────────────────────┤
│ Footer: keyboard shortcut hints                         │
└─────────────────────────────────────────────────────────┘
```

*Sections marked with `*` are conditionally visible based on the selected revenue model.

### Sidebar Structure

- **Fixed top area** (`#sidebar-fixed`): Scenario selector, model type dropdown. Always visible.
- **Scrollable parameter area** (`#params-scroll`): Collapsible sections for each parameter group. Scrolls independently.

### Model-Based Section Visibility

| Section | F2P | Premium | Remove Ads |
|---------|-----|---------|------------|
| IAP Monetization | visible | hidden | hidden |
| Ad Revenue | visible | hidden | visible |
| Premium Pricing | hidden | visible | hidden |
| Ad Removal IAP | hidden | hidden | visible |

Hidden sections are collapsed and their inputs are disabled.

---

## Behavior Notes

- **Per-keystroke recalc:** Every `Input.Changed` event triggers a full 365-day simulation and redraws the timeline table.
- **Enter/Blur:** Commits the value, clears the `.pending` highlight, recalculates, and refreshes the Solver tab if it's active.
- **Solver tab:** Also refreshes when activated via `ctrl+t` or clicking the tab.
- **Delete confirmation:** First click shows "Delete this scenario? Press Delete again to confirm." Second click executes deletion. Escape cancels.
- **Monthly rows:** Styled with bold cyan date to distinguish from daily rows.

---

## Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `ctrl+q` | quit | Exit the application |
| `ctrl+r` | refresh_solver | Re-run the solver computation |
| `ctrl+t` | next_tab | Cycle through tabs (Timeline → Compare → Solver) |
| `ctrl+s` | toggle_panel | Move focus between sidebar and right panel |
| `ctrl+1` | apply_1 | Apply solver's CPI value to sidebar |
| `ctrl+2` | apply_2 | Apply solver's D1 Retention value to sidebar |
| `ctrl+3` | apply_3 | Apply solver's monetization value to sidebar |
| `escape` | unfocus | Revert input to last-committed value and unfocus |

### Focus Management

- `_focus_original_values`: Per-widget dict storing the last committed value. Pressing Escape reverts to this.
- `_last_sidebar_focus` / `_last_right_focus`: Memory of last-focused widget in each panel. `ctrl+s` restores focus to the remembered widget.
- `_panel_on_sidebar`: Boolean tracking which panel "owns" focus.

---

## Scenario Management

- **Storage:** `scenarios.json` — flat JSON dict keyed by scenario name.
- **Auto-seed:** On first run (or if file is empty/corrupt), seeds three built-in scenarios: "F2P Base Case", "Premium $4.99", "F2P Remove Ads $2.99".
- **Save:** Writes current engine state (all `EXPOSED_PARAMS` + `model_type`) to `scenarios.json`.
- **Delete:** Removes a scenario by name.
- **Loading guard:** `_loading_scenario` flag prevents recursive `Input.Changed` events when programmatically setting widget values.

### Saved Scenario Schema

```json
{
  "model_type": "f2p",
  "daily_ua_spend": 10.0,
  "cpi": 0.26,
  "...": "all EXPOSED_PARAMS attributes"
}
```

---

## Timeline Output Format

`calculate_timeline()` returns a list of dicts, one per row in the table:

```python
{
    "date": "2025-01-15" or "2025-03 (month)",
    "dau": 1234,              # int, last-day snapshot for monthly rows
    "accrued_rev": 45.67,     # net revenue earned this day (accrual basis)
    "cash_inflow": 12.34,     # settled cash received (delayed by payout_delay_days)
    "ops_cost": 28.90,        # total operating expenses (fixed + scaling + UA)
    "cash_flow": -16.56,      # cash_inflow - ops_cost
    "bank_balance": -500.12   # cumulative running balance
}
```

- **Daily rows (1–90):** One row per calendar day.
- **Monthly rows (months 4–12):** Aggregated by calendar month. Revenue/expenses are **summed**. DAU and bank balance are **last-day snapshots** (not sums).

---

## Key Design Decisions & Known Issues

### Deliberate Choices

1. **No premium conversion rate:** The Premium model assumes every install purchases. This is unrealistic but keeps the model simple. A `premium_conversion` parameter could be added.
2. **Retention floor at 12% of D1:** Prevents retention from reaching zero, ensuring long-tail DAU. This inflates late-period revenue somewhat.
3. **Hardcoded payer tier mix:** Only `payer_pct` and `whale_spend` are tunable. The 4-tier structure with fixed splits is baked in.
4. **CPI saturation uses magic constant 10000:** The denominator in the logarithmic CPI curve is not parameterized.
5. **Escape reverts input:** Unlike most TUIs where Escape just unfocuses, here it reverts to the last committed value. This is intentional for "safe exploration."

### Known Issues

1. **O(n²) cohort iteration:** Each day iterates all historical cohorts. At 365 days this is ~66k iterations — fine at current scale but would need optimization for longer simulations.
2. **Solver performance:** Each solver call runs up to 10 full 365-day simulations. With 6 solver calls, that's ~60 simulations when the Solver tab opens. Noticeable but acceptable.
3. **No input validation for date beyond format:** Invalid date strings (e.g., "2025-13-01") are rejected, but dates like "2025-02-30" pass format validation.
4. **Compare tab shows "(Current)" row:** Always shows current parameters even if they match a saved scenario (deduplication only applies to saved scenarios).

---

## File Structure

| File | Purpose |
|------|---------|
| `runway.py` | Entire application (engine + TUI) in one file |
| `runway.sh` | Shell wrapper: `cd`s to project dir, runs via venv |
| `scenarios.json` | Persisted scenario data (auto-created) |
| `AGENTS.md` | Agent-facing codebase overview |
| `SPEC.md` | This document |
