# Game Financial Runway API — Agent Guide

This document describes the programmatic API for modeling mobile and web game financial runways. Both simulators model 365 days of game economics — user acquisition, retention cohorts, monetization, and operating costs — and return structured data for analysis.

No TUI or terminal interaction required. All methods return plain dicts and lists.

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

## Batch Comparison

```python
from api import compare_mobile_scenarios, compare_web_scenarios

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
```

Each result dict has `name`, then a subset of summary fields (`ltv`, `total_revenue`, `final_bank`, `break_even_day`) and a `diagnosis` status string. Mobile results also include `model_type` and `ltv_cpi_ratio`; web results include `portal`.

## Common Patterns

### Find the breakeven CPI
```python
api = MobileGameAPI(params)
solved = api.solve("cpi", "final_bank", 0.0, low=0.01, high=5.0)
print(f"Breakeven CPI: ${solved['value']:.2f}")
```

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
