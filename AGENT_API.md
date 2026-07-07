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

# Parameter sweep
api.sensitivity("daily_ua_spend", [5, 10, 20, 50])   # → list of summaries

# Goal-seeking (find what value achieves a target)
api.solve("cpi", "final_bank", 0.0, low=0.01, high=5.0)           # CPI for breakeven
api.solve("subscription_price", "ltv_cpi_ratio", 3.0, low=0.5, high=50)  # price for 3× ratio
```

### Evaluate Result Structure

```python
{
    "summary": {
        "model_type": "f2p",
        "ltv": 0.8572,            # Lifetime value per install
        "blended_cpi": 0.3019,    # Install-weighted avg CPI (with saturation)
        "ltv_cpi_ratio": 2.84,    # LTV / blended CPI
        "margin_per_install": 0.56,  # LTV - CPI
        "peak_dau": 797,          # or "total_installs" for premium, "peak_subs" for subscription
        "total_revenue": 5200.50, # 365-day accrued revenue
        "final_bank": -81.23,     # Year-end bank balance
        "break_even_day": None,   # Day bank balance first ≥ starting capital (None = never)
    },
    "diagnosis": {
        "status": "thin",         # "healthy" | "thin" | "losing"
        "message": "Profitable but thin — $0.56/install margin (LTV 2.8× CPI)",
    },
    "breakdown": {
        "description": "Lifetime 21 days, 3% payers",
        "components": {
            "iap_revenue": 0.32,   # IAP contribution per install
            "ad_revenue": 0.53,    # Ad contribution per install
        },
        "total_ltv": 0.86,
        "blended_cpi": 0.30,
        "margin_per_install": 0.56,
    },
    "timeline": [ ... ],  # 90 daily rows + 9 monthly summaries
}
```

## Web Game API (`WebGameAPI`)

### Portals

| Portal | Rev Share | RPM | IAP | Organic Plays | Notes |
|---|---|---|---|---|---|
| Web Portal | 50% | $2.00 | No | 3000/day | Standard rev-share |
| Playable Ads | 60% | $1.20 | No | 6000/day | Higher volume, lower RPM |
| Social/Messaging | 70% | $1.50 | Yes | 2000/day | Higher engagement |
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

- **Paid UA** (external_ua_spend > 0): Uses LTV vs CPI margin, same as mobile.
- **Organic-only** (external_ua_spend = 0): Uses daily revenue vs daily costs (overhead + server + CDN), since CPI is not applicable.

## Batch Comparison

```python
from api import compare_mobile_scenarios

scenarios = {
    "Cheap CPI": {"model_type": "f2p", "cpi": 0.10, "daily_ua_spend": 20},
    "Standard": {"model_type": "f2p", "cpi": 0.26, "daily_ua_spend": 10},
    "Premium": {"model_type": "f2p", "cpi": 0.50, "daily_ua_spend": 10},
}
results = compare_mobile_scenarios(scenarios)
for r in results:
    print(f"{r['name']:12s}  bank=${r['final_bank']:>8,.0f}  {r['diagnosis']}")
```

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
for portal in ["Web Portal", "Playable Ads", "Social/Messaging", "Custom Web"]:
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
