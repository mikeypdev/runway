# Game Financial Runway API — Agent Guide

This document describes the programmatic API for modeling mobile, web, and PC game financial runways. All three simulators model 365 days of game economics — user acquisition, retention cohorts, monetization, and operating costs — and return structured data for analysis.

No TUI or terminal interaction required. All methods return plain dicts and lists.

## Crafting Effective Prompts

The quality of the analysis depends heavily on what the prompt specifies. The API can sweep uncertain variables and stress-test assumptions, but only if the prompt provides enough context and asks for robustness. A prompt that omits key details forces the agent to guess at assumptions, then require follow-up questions to validate them.

### Include these in the prompt

| Detail | Why it matters | Example |
|---|---|---|
| **Genre and mechanics** | Drives retention, virality, and IAP-fit estimates | "casual family strategy — chess board + card game elements" |
| **Quantified budget** | Anchors starting capital, overhead, and UA spend | "~$1,500 starting capital, ~$10/day available for UA, solo dev with $0 salary" |
| **Retention range, not sentiment** | "Optimistic" is uncalibratable; a range makes the sensitivity table the primary output | "assume D1 retention 25–45%, I don't have data yet" |
| **Sharing/social features** | Directly determines k-factor (0 if none exists) | "no built-in sharing features yet" or "has invite-a-friend" |
| **Target metric** | "Best revenue" is ambiguous — gross, net, or year-end bank rank differently | "maximize year-end bank balance" |
| **Robustness request** | Turns a point estimate into the sensitivity-driven analysis that actually de-risks the decision | "sweep the uncertain variables and show how robust the recommendation is" |

### Example prompt

> I have a new casual family strategy game (familiar chess board + simple card game mechanics). I can ship on web, mobile, or both. **Budget: ~$1,500 starting capital, ~$10/day for UA.** I don't have retention data yet — **assume a D1 range of 25–45% rather than a point estimate.** The game has **no built-in sharing or social features yet.** I'm a solo dev with **minimal overhead.**
>
> Which business model maximizes **year-end bank balance**, and **how robust is that recommendation across the uncertain assumptions** (retention, CPI, organic traffic)? Sweep the key variables and show the sensitivity. Follow AGENT_API.md.

### Anti-patterns to avoid

- **Vague budget terms** ("minimal budget") — the agent guesses; could be off by 10× in either direction.
- **Sentiment instead of ranges** ("optimistic retention") — uncalibratable; forces a single point estimate when a sweep is the right tool.
- **Asking for "the best model"** — implies one answer; the honest output is a robustness comparison, not a ranking by a single metric.
- **Omitting viral/social context** — the agent may assume virality (k-factor) that the game has no mechanic to earn.

## Quick Start

```python
from api import MobileGameAPI, WebGameAPI

# Mobile game — evaluate the default F2P scenario
api = MobileGameAPI(MobileGameAPI.default_scenario("f2p"))
result = api.evaluate()
print(result["diagnosis"]["message"])
print(f"Year-end bank: ${result['summary']['final_bank']:,.0f}")

# Web game — evaluate the default portal scenario
web = WebGameAPI(WebGameAPI.default_scenario("Web Portal"))
result = web.evaluate()
print(result["diagnosis"]["message"])
```

## Mobile Game API (`MobileGameAPI`)

### Models

| Model | ID | How revenue works | Activity metric |
|---|---|---|---|
| F2P (IAP + Ads) | `f2p` | DAU × payer% × ARPPU + DAU × ad impressions × eCPM | DAU |
| Premium (Buy Once) | `premium` | Each install × game price, one-time | Daily installs |
| F2P + Remove Ads | `remove_ads` | Some users pay to remove ads, rest see ads | DAU |
| Subscription | `subscription` | Active subscribers × daily rate, churned monthly | Active subscribers |

### Key Methods

```python
# Discover available models and parameters
MobileGameAPI.list_models()                          # → list of model dicts
MobileGameAPI.parameter_schema()                      # → all parameters
MobileGameAPI.parameter_schema("subscription")        # → params relevant to subscription
MobileGameAPI.default_scenario("f2p")                 # → default param dict
MobileGameAPI.list_default_scenarios()                # → all built-in scenarios

# Run a simulation
api = MobileGameAPI({"model_type": "subscription", "subscription_price": 2.99})
result = api.evaluate()   # → full results (see below)

### Parameter sweep

```python
api.sensitivity("daily_ua_spend", [5, 10, 20, 50])   # → list of summaries
```

If `values` is omitted, the API uses default multipliers on the current value: `[0.25, 0.5, 1.0, 2.0, 4.0, 8.0]` for mobile and `[0.25, 0.5, 1.0, 1.5, 2.0, 3.0]` for web. Each sweep temporarily forces `ua_scaling_mode = "manual"` (mobile) so results reflect the swept value directly.

# Goal-seeking (find what value achieves a target)
api.solve("cpi", "final_bank", 0.0, low=0.01, high=5.0)           # CPI for breakeven
api.solve("subscription_price", "ltv_cpi_ratio", 3.0, low=0.5, high=50)  # price for 3× ratio
```

### Evaluate Result Structure

Numeric values below are **illustrative** — they shift as engine defaults evolve. Read them at runtime (`result["summary"][...]`) rather than hardcoding.

```python
{
    "summary": {
        "model_type": "f2p",
        "ltv": 0.86,              # Analytical lifetime value per install
        "realized_ltv": 0.52,     # Revenue per install over the actual 365-day timeline
        "blended_cpi": 0.30,      # Paid-only install-weighted CPI (with saturation)
        "effective_cpi": 0.24,    # CPI used for diagnosis (blends paid + organic + viral)
        "ltv_cpi_ratio": 3.6,     # Analytical LTV / effective CPI
        "realized_ltv_cpi_ratio": 2.2,  # Realized LTV / effective CPI (drives diagnosis)
        "margin_per_install": 0.56,     # Analytical LTV - CPI
        "realized_margin_per_install": 0.28,  # Realized LTV - CPI
        "fully_loaded_cpi": 1.61,     # Total cost per install (UA + overhead + server)
        "annual_net": 2968.0,        # Total revenue - total costs for the year
        "peak_dau": 797,          # "total_installs" for premium, "peak_subs" for subscription
        "total_revenue": 7200.0,  # 365-day accrued revenue
        "final_bank": -81.0,      # Year-end bank balance
        "break_even_day": None,   # Day bank balance first ≥ starting capital (None = never)
    },
    "diagnosis": {
        "status": "thin",         # "healthy" | "thin" | "losing"
        "message": "Thin — +$2,968/year margin, realized $2.00/install vs CPI $0.78 (fully-loaded $1.61/install)",
    },
    "breakdown": {
        "description": "Lifetime 21 days, 3% payers",
        "components": {           # keys vary by model (see below)
            "iap_revenue": 0.32,  # IAP contribution per install
            "ad_revenue": 0.53,   # Ad contribution per install
        },
        "total_ltv": 0.86,
        "blended_cpi": 0.30,
        "effective_cpi": 0.24,
        "margin_per_install": 0.62,
    },
    "timeline": [ ... ],  # 90 daily rows + 9 monthly summaries
}
```

#### Breakdown `components` keys by model

The `breakdown.components` dict uses different keys depending on `model_type`:

| Model | Component keys |
|---|---|
| `f2p` | `iap_revenue`, `ad_revenue` |
| `premium` | `game_price_net` |
| `remove_ads` | `removal_iap`, `ad_revenue` |
| `subscription` | `ltv_per_subscriber`, `conversion_rate`, `effective_per_install` |

## Web Game API (`WebGameAPI`)

### Portals

| Portal | Rev Share | RPM | IAP | Organic Plays | Notes |
|---|---|---|---|---|---|
| Web Portal | 50% | $2.00 | No | 3000/day | Standard rev-share |
| Playable Ads | 60% | $1.20 | No | 6000/day | Higher volume, lower RPM |
| Social App Mini Game | 50% | $1.50 | Yes | 2000/day | Mini games in social apps |
| Custom Web | 0% | $1.00 | Yes | 0/day | Self-published, needs paid UA |

### Portal Parameters

Portal-specific values are set automatically by `default_scenario()`. The portal table column names above map to these parameter names:

| Portal table column | Parameter name |
|---|---|
| Rev Share | `portal_rev_share` |
| RPM | `base_rpm` |
| Organic Plays | `organic_plays_per_day` |
| IAP | (no parameter — gated by the portal definition; configure via `iap_payer_pct` + `iap_avg_purchase`) |

**Always start from `default_scenario(portal)` and overlay changes.** Constructing a web params dict from scratch will silently omit portal-specific RPM, rev-share, and organic traffic — producing identical results across all portals.

### Key Methods

```python
WebGameAPI.list_portals()                    # → portal defaults
WebGameAPI.parameter_schema()                # → all web parameters
WebGameAPI.default_scenario("Custom Web")    # → default param dict

web = WebGameAPI({"portal": "Custom Web", "base_rpm": 1.50})
result = web.evaluate()
web.sensitivity("base_rpm", [0.50, 1.0, 2.0, 3.0])
```

### Diagnosis Modes

- **Paid UA** (external_ua_spend > 0): Uses **annual net** (total revenue − total operating costs) for status. The message shows per-install economics (realized LTV vs CPI vs fully-loaded CPI) to explain *why* the business is healthy, thin, or losing. When per-install economics are positive but the business still loses money, the message flags that overhead crushes the margin.
- **Organic-only** (external_ua_spend = 0): Uses daily revenue vs daily costs (overhead + server + CDN), since CPI is not applicable.

### Evaluate Result Structure

The web result shape differs from mobile. The `summary` adds `portal`, `total_plays`, `avg_daily_revenue`, and `avg_daily_costs`, and omits mobile's `ltv_cpi_ratio` / `margin_per_install`. The `breakdown` has no `description` and no `margin_per_install`. Numeric values are illustrative.

```python
{
    "summary": {
        "portal": "Web Portal",
        "ltv": 0.017,             # Analytical lifetime value per play
        "realized_ltv": 0.012,    # Revenue per install over the actual 365-day timeline
        "blended_cpi": None,      # paid-only CPI, null when organic-only
        "effective_cpi": None,    # diagnosis CPI (blends organic+viral+paid); null when organic-only
        "total_revenue": 31000.0, # 365-day accrued revenue
        "total_plays": 15500000,  # Cumulative plays
        "peak_dau": 47000,
        "final_bank": -48000.0,   # Year-end bank balance
        "break_even_day": None,
        "avg_daily_revenue": 18.7,  # First-30-day average
        "avg_daily_costs": 204.5,   # overhead + server + CDN
    },
    "diagnosis": {
        "status": "losing",       # "healthy" | "thin" | "losing"
        "message": "Daily burn: $205/day — revenue $19/day can't cover costs",
    },
    "breakdown": {
        "components": {
            "player_lifetime_days": 6.4,
            "sessions_per_day": 1.3,
            "impressions_per_session": 2.5,
            "ad_fill_rate": 0.8,
            "net_rpm_per_impression": 0.0008,
            "ad_revenue_per_install": 0.017,
            "iap_revenue_per_install": 0.0,  # only when IAP supported + payer% > 0
        },
        "total_ltv": 0.017,
        "effective_cpi": None,    # CPI used for margin (blends organic+viral+paid); null when organic-only
    },
    "timeline": [ ... ],  # 90 daily rows + 9 monthly summaries
}
```

> **Note:** `solve(..., "ltv_cpi_ratio", ...)` is meaningless for organic-only web scenarios where `effective_cpi` is null. Use `final_bank` as the target metric there.

## PC Game API (`PCGameAPI`)

Models PC games (Steam, itch.io, or dual-channel). Revenue is event-driven: launch wishlist conversions, decaying organic sales, periodic sale-event spikes (Steam sales), and optional DLC releases. There is no DAU/retention model — each sale is a one-time transaction.

### Platforms

| Platform | Fee | Payout Delay | Description |
|---|---|---|---|
| Steam | 30% | 30 days | Largest PC audience, seasonal sale events |
| itch.io | 10% | 15 days | Indie-friendly, smaller audience, fewer refunds |
| Both | ~27% (blended) | 30 days | Dual-channel release |

### Key Methods

```python
from api import PCGameAPI

PCGameAPI.list_platforms()                    # → [{"id": "Steam", "platform_fee": 30.0, ...}, ...]
PCGameAPI.parameter_schema()                  # → [{"name": "game_price", "type": "float", ...}, ...]
PCGameAPI.default_scenario("Steam")           # → full params dict
PCGameAPI.list_default_scenarios()            # → {"Steam Indie $14.99": {...}, ...}

api = PCGameAPI({"platform": "Steam", "game_price": 19.99})
api.evaluate()                                # → full simulation result
api.sensitivity("daily_marketing_spend")      # → sweep results
api.solve("game_price", "final_bank", 0.0)    # → breakeven price
```

### Evaluate Result Structure

```python
{
    "summary": {
        "platform": "Steam",
        "ltv": 9.2321,             # analytical net revenue per unit (incl. DLC)
        "realized_ltv": 9.1234,    # actual total_revenue / total_units from timeline
        "effective_cps": 1.5789,   # marketing cost per sale (blended across all units)
        "ltv_cps_ratio": 5.85,     # ltv / effective_cps (null if no marketing spend)
        "annual_net": 81234.50,    # total_revenue - total_ops
        "fully_loaded_cps": 2.10,  # total_ops / total_units
        "total_revenue": 117342.00,
        "total_units": 12746,
        "total_dlc_units": 0,
        "peak_daily_units": 832,
        "final_bank": 101475.00,
        "break_even_day": 30,      # first day bank >= starting_capital
    },
    "diagnosis": {
        "status": "healthy",       # "healthy" | "thin" | "losing"
        "message": "Healthy — ...",
    },
    "breakdown": {
        "components": {
            "game_price": 14.99,
            "regional_pricing_pct": 85.0,
            "vat_rate": 13.0,
            "platform_fee_pct": 30.0,
            "refund_rate": 12.0,
            "after_regional_pricing": 12.7415,
            "net_factor": 0.4634,   # regional / (1+vat) × (1-refund) × (1-fee)
            "base_revenue_per_unit": 6.9458,
            # when DLC is active:
            "dlc_count": 2,
            "dlc_price": 7.99,
            "dlc_attach_rate": 0.15,
            "dlc_revenue_per_unit": 1.1107,
        },
        "total_ltv": 8.0565,
        "effective_cps": 1.5789,
        "margin_per_unit": 7.6532,
    },
    "timeline": [ ... ],  # 90 daily rows + 9 monthly summaries
}
```

### Sales Curve Model

The PC engine uses an event-driven sales curve instead of cohort-based retention:

- **Launch spike** (days 0 to `launch_spike_duration`): wishlist conversions at `pre_launch_wishlists * launch_conversion_rate / launch_spike_duration`, multiplied by `launch_spike_multiplier`, plus base daily sales.
- **Decay tail**: `base_daily_sales * day^(-sales_decay_exponent)`, floored at 10% of base.
- **Sale events**: every `sale_event_frequency` days for `sale_event_duration` days. Units multiply by `sale_event_multiplier`, price discounts by `sale_discount_pct`.
- **DLC**: released at intervals of `dlc_release_interval` days. Each DLC sells to `cumulative_owners * dlc_attach_rate` over a decay curve.
- **Marketing**: `daily_marketing_spend / cost_per_sale` additional units per day (analogous to CPI-driven UA).

### Diagnosis Modes

The health diagnosis uses annual net revenue vs total costs:

- **Losing**: annual net < 0. Checks whether per-unit revenue covers marketing CPS or if overhead is the problem.
- **Thin**: annual net < 30% of total ops cost.
- **Healthy**: otherwise.

When `daily_marketing_spend` is 0, `ltv_cps_ratio` is null and `effective_cps` falls back to the raw `cost_per_sale` parameter.

## Batch Comparison

```python
from api import compare_mobile_scenarios, compare_web_scenarios, compare_pc_scenarios

# Mobile
mobile = {
    "Cheap CPI": {"model_type": "f2p", "cpi": 0.10, "daily_ua_spend": 20},
    "Standard": {"model_type": "f2p", "cpi": 0.26, "daily_ua_spend": 10},
    "Premium": {"model_type": "f2p", "cpi": 0.50, "daily_ua_spend": 10},
}
for r in compare_mobile_scenarios(mobile):
    print(f"{r['name']:12s}  bank=${r['final_bank']:>8,.0f}  {r['diagnosis']}")

# Web — same shape, plus a `portal` field and no `ltv_cpi_ratio`
web = {
    "Portal": {"portal": "Web Portal"},
    "Custom": {"portal": "Custom Web", "external_ua_spend": 20},
}
for r in compare_web_scenarios(web):
    print(f"{r['name']:12s}  bank=${r['final_bank']:>8,.0f}  {r['diagnosis']}")

# PC — includes `platform` and `total_units`
pc = {
    "Steam": {"platform": "Steam", "game_price": 14.99},
    "itch": {"platform": "itch.io", "game_price": 9.99},
}
for r in compare_pc_scenarios(pc):
    print(f"{r['name']:12s}  bank=${r['final_bank']:>8,.0f}  units={r['total_units']:>6,}  {r['diagnosis']}")
```

Each result dict has `name`, then a subset of summary fields (`ltv`, `total_revenue`, `final_bank`, `break_even_day`) and a `diagnosis` status string. Mobile results also include `model_type` and `ltv_cpi_ratio`; web results include `portal`; PC results include `platform` and `total_units`.

## Modeling Limitations

The engines are simplified financial models. Key limitations to flag when interpreting results:

| Not modeled | Impact | Mitigation |
|---|---|---|
| **Price elasticity** (mobile premium) | Raising `game_price` never reduces installs — revenue scales linearly with price | Manually discount installs when sweeping price; validate against real conversion data |
| **Organic traffic ramp-up** (web) | `organic_plays_per_day` is a flat constant from day 1 — new titles don't get full portal discovery immediately | Sensitivity-test at 0, 100, 500 plays/day for unproven titles |
| **k-factor mechanic requirement** | `virality_k_factor` applies blindly — it assumes an in-game sharing/invite loop exists | Set k=0 unless the game has an explicit viral feature |
| **Retention uncertainty** | D1 retention is a single point estimate with no confidence interval | Always sweep retention; the retention-robustness table matters more than the point estimate |
| **CPI saturation only** (no market competition) | CPI rises with your own spend, not with competitor bidding | Treat CPI as a lower bound in competitive markets |

When presenting results, disclose which of these apply to the scenario.

## Common Patterns

### Find the breakeven CPI
```python
api = MobileGameAPI(params)
solved = api.solve("cpi", "final_bank", 0.0, low=0.01, high=5.0)
print(f"Breakeven CPI: ${solved['value']:.2f}")
```

### Interpreting solve() results

`solve()` returns `None` when the target metric cannot be reached within `[low, high]`. The most common case: the model is profitable (or unprofitable) across the entire search range — e.g., Mobile Premium never reaches `final_bank = 0` at any CPI because organic + viral installs keep it above water. When this happens, run a sensitivity sweep to understand the shape of the curve rather than relying on the solver.

### Find minimum viable subscription price
```python
api = MobileGameAPI({"model_type": "subscription", "monthly_churn": 5.0, "payer_pct": 3.0})
solved = api.solve("subscription_price", "final_bank", 0.0, low=0.99, high=50.0)
print(f"Min viable price: ${solved['value']:.2f}/mo")
```

### Compare all mobile models at same traffic
```python
for model in ["f2p", "premium", "remove_ads", "subscription"]:
    api = MobileGameAPI(MobileGameAPI.default_scenario(model))
    r = api.evaluate()
    print(f"{model:14s}  LTV=${r['summary']['ltv']:.2f}  bank=${r['summary']['final_bank']:>8,.0f}  {r['diagnosis']['status']}")
```

### Compare all web portals
```python
for portal in ["Web Portal", "Playable Ads", "Social App Mini Game", "Custom Web"]:
    api = WebGameAPI(WebGameAPI.default_scenario(portal))
    r = api.evaluate()
    print(f"{portal:16s}  LTV=${r['summary']['ltv']:.2f}  bank=${r['summary']['final_bank']:>8,.0f}  {r['diagnosis']['status']}")
```

## Parameter Discovery

Every parameter has metadata: name, label, type, default, description, and which models it applies to. Use this to validate inputs or build dynamic UIs.

```python
for p in MobileGameAPI.parameter_schema("subscription"):
    print(f"  {p['name']:25s} {p['type']:6s} default={p['default']}  {p['description'][:60]}")
```

Parameters marked `"models": "all"` apply to every model. Others list specific model IDs.

## Timeline Data

The `timeline` field in evaluate results contains 90 daily rows followed by 9 monthly summaries. Each row is a dict with:

| Field | Type | Description |
|---|---|---|
| `date` | str | `YYYY-MM-DD` for daily, `YYYY-MM (month)` for monthly |
| `dau` | int | Daily active users (snapshot) |
| `accrued_rev` | float | Revenue accrued that day/month |
| `cash_inflow` | float | Cash actually received (lagged by payout delay) |
| `ops_cost` | float | Total operating costs |
| `cash_flow` | float | Net daily cash flow (cash_inflow - ops_cost) |
| `bank_balance` | float | Running bank balance |

Mobile timelines also include `installs` (daily new installs) and `active_subs` (for subscription). Web timelines include `plays` and `rpm`.

## Best Practices for Reliable Analysis

1. **Always start from `default_scenario()`** and overlay changes — never construct params dicts from scratch (portal-specific values will be silently dropped).
2. **Sweep every uncertain assumption.** The point estimate is always wrong; the sensitivity table is the answer. Priority sweeps: retention, CPI, organic traffic.
3. **Set k-factor to 0** unless the game has a confirmed viral/sharing mechanic.
4. **Discount web organic traffic** for new/unknown titles — portal defaults assume established discovery placement.
5. **Don't sweep price without elasticity.** The engine has no price-elasticity model; raising price naively increases revenue without reducing installs.
6. **Disclose all applied tuning** when presenting results, including which defaults were changed and why.
