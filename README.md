# runway

Interactive terminal UIs for modeling a game's 12-month financial runway.

The repo contains **two independent simulators** — one for mobile games, one for web games — sharing the same Textual TUI framework and overall architecture.

## What it does

Both simulators model 365 days of game economics — user acquisition, retention, monetization, and operating costs — with a distinction between accrued revenue and actual cash settlement. They show 90 days of daily projections plus monthly summaries for months 4–12.

### Mobile Game Simulator (`runway.py`)

Models free-to-play and premium mobile game economics. Supports three business models:
- **F2P (IAP + Ads)** — payer conversion × ARPPU + rewarded video ad revenue
- **Premium (Buy Once)** — one-time purchase per install, no ads; the timeline and metrics show **installs** instead of DAU since active-user engagement doesn't drive revenue
- **F2P + Remove Ads IAP** — free users generate ad revenue, paying users remove ads via one-time IAP
- **Subscription (No Ads)** — monthly or annual recurring subscription; the timeline and metrics show **active subscribers** instead of DAU since revenue depends on paying subscribers, not total active users

Multiple named scenarios can be saved and compared side-by-side (peak DAU, total accrued revenue, break-even day, year-end bank balance). A **health diagnosis** line under the KPI bar flags per-install profitability issues at a glance. Includes a **target solver** that finds the parameter values needed to hit specific financial goals (year-end breakeven, LTV:CPI ≥ 3.0) with a model-specific **LTV breakdown** showing how each revenue component contributes, and a **spend sensitivity analysis** that shows projected outcomes at different daily UA spend levels.

### Web Game Simulator (`web_runway.py`)

Models web games published on portals with RPM-based (revenue per 1000 plays) monetization. Supports four portal types:
- **Web Portal** — standard rev-share portal (50%, $2 RPM)
- **Playable Ads** — ad-driven discovery (60%, $1.20 RPM)
- **Social/Messaging** — higher engagement with IAP support (70%, $1.50 RPM)
- **Custom Web** — self-published, no rev share, IAP + ads ($1 RPM)

Includes a **portal comparison** tab that runs the same parameters across all four portals side-by-side, and a **target solver** that finds RPM, retention, or session values needed to hit goals.

## Quick start

```bash
./runway.sh        # mobile game simulator
./web_runway.sh    # web game simulator
```

Requires a Python 3.14 virtualenv at `.venv/` with `textual` and `rich` installed.

## Parameters

### Mobile Game (`runway.py`)

| Section | Parameter | What it controls |
|---|---|---|
| **Launch & Capital** | Start Date | Day 1 of the simulation (defaults to today) |
| | Starting Capital | Initial bank balance before day 1 |
| **Business Model** | Revenue Model | F2P, Premium, or Remove Ads — shows/hides relevant params |
| **UA Scaling** | Scaling Mode | Manual (fixed spend) or Auto-scale (ROI-based) |
| | Target ROI | Auto-scale target LTV:CPI ratio |
| | Max Daily Budget | Cap for auto-scaling spend |
| | Scale Speed | Multiplier for weekly spend adjustments |
| **Marketing Capital** | Daily UA Spend | Daily user acquisition budget |
| | Cost Per Install | Base cost per paid install |
| | CPI Saturation | How much CPI grows as cumulative installs increase (0 = off) |
| | Burst / Influencer Installs | Daily non-paid installs from campaigns |
| **Growth & Retention** | Organic Install Ratio | Free installs as a ratio of paid |
| | Viral K-Factor | Additional installs per user (recursive) |
| | D1 Retention | Day-1 retention percentage |
| | Retention Decay Rate | Power-law exponent for long-term retention |
| **IAP Monetization** *(F2P only)* | Payer Conversion Rate | Fraction of DAU that spends |
| | ARPPU ($) | Avg revenue per paying user per day |
| **Ad Revenue** *(F2P, Remove Ads)* | Video Ad eCPM | Revenue per 1000 ad impressions |
| | Ad Impressions / DAU / Day | Rewarded video ad frequency |
| **Premium Pricing** *(Premium only)* | Game Price | One-time purchase price |
| **Ad Removal IAP** *(Remove Ads only)* | Ad Removal Price | One-time IAP to disable ads |
| | Removal Conversion % | Fraction of new installs that buy removal |
| **Subscription Pricing** *(Subscription only)* | Billing Period | Monthly or Annual billing cycle |
| | Subscription Price | Recurring charge per billing period |
| | Monthly Churn (%) | % of active subscribers who cancel each month |
| | Subscriber Conversion (%) | Fraction of new installs who subscribe |
| **Platform Fees** | Platform Fee | Store commission (0.30 = standard) |
| | Platform Payout Delay | Days before accrued revenue settles as cash |
| **Live-Ops OpEx** | Fixed Daily Overhead | Baseline daily operating cost |
| | Server Cost per 1k DAU | Infrastructure cost that scales with users |

### Web Game (`web_runway.py`)

| Section | Parameter | What it controls |
|---|---|---|
| **Launch & Capital** | Start Date | Day 1 of the simulation (defaults to today) |
| | Starting Capital | Initial bank balance before day 1 |
| **Portal** | Publish Portal | Web Portal, Playable Ads, Social/Messaging, or Custom Web |
| **Traffic & Acquisition** | Organic Plays/Day | Free daily plays (portal-dependent) |
| | Min Guaranteed Plays | Floor on daily plays |
| | External UA Spend | Daily paid acquisition budget |
| | External CPI | Cost per acquired player |
| | CPI Saturation | How much CPI grows with cumulative spend |
| | Viral K-Factor | Additional plays per player (recursive) |
| **Engagement & Retention** | D1 Retention | Day-1 retention percentage |
| | Retention Decay | Power-law exponent for long-term retention |
| | Sessions per Day | Average sessions per daily active player |
| | Ad Impressions/Session | Ads shown per session |
| | Ad Fill Rate (%) | Percentage of ad requests that are filled |
| **Ad Monetization (RPM)** | Base RPM | Revenue per 1000 ad impressions |
| | RPM Growth Rate | Monthly RPM growth (for mature portals) |
| | Portal Rev Share | Portal's revenue share percentage |
| **IAP Monetization** | Payer Conversion (%) | Fraction of DAU that buys IAP |
| | Avg Purchase ($) | Average IAP transaction value |
| **Costs & Payout** | Fixed Daily Overhead | Baseline daily operating cost |
| | Server Cost per 1k DAU | Infrastructure cost scaling with users |
| | CDN Cost per 1k Plays | Bandwidth cost scaling with plays |
| | Payout Delay (Days) | Days before accrued revenue settles as cash |

## Key bindings

Both apps share the same bindings:

- `ctrl+r` — Recalculate / refresh
- `ctrl+q` — Quit
- `ctrl+t` — Switch tab
- `ctrl+s` — Switch panel (sidebar ↔ table)
- `ctrl+1` / `ctrl+2` / `ctrl+3` — Apply solver values (on Target Solver tab)
- `escape` — Revert current input / unfocus

## Tabs

### Mobile Game

- **12-Month Runway** — Timeline table with daily (90 days) + monthly summaries (shows installs instead of DAU for the Premium model)
- **Compare Scenarios** — Side-by-side summary metrics for saved scenarios
- **Spend Analysis** — Projected outcomes at different daily UA spend levels
- **Target Solver** — Find parameter values needed to meet financial goals, with a model-specific LTV breakdown showing how each revenue component contributes to per-install margin

### Web Game

- **12-Month Runway** — Timeline table with daily (90 days) + monthly summaries
- **Compare Scenarios** — Side-by-side summary metrics for saved scenarios
- **Portal Comparison** — Same parameters run across all four portal types
- **Target Solver** — Find RPM, D1 retention, or sessions/day needed to meet goals

## Scenarios

Default scenarios ship with each model:

**Mobile (`runway.py`):**
- **F2P Base Case** — Moderate spend, standard metrics
- **Premium $4.99** — Buy-once model with higher CPI
- **F2P Remove Ads $2.99** — Hybrid ad + removal IAP
- **Subscription $0.99/mo** — Low monthly subscription, no ads

**Web (`web_runway.py`):**
- **Portal Ad-Only** — Web Portal, ad revenue only
- **Playable Ads Reach** — Playable Ads portal, higher volume
- **Social IAP Hybrid** — Social/Messaging, ad + IAP revenue
- **Custom Web Direct** — Self-published, full IAP control

Scenarios are saved to `scenarios.json` (mobile) or `web_scenarios.json` (web). Delete the file to reset to defaults.

## How it works

Both engines track each day's new installs as a cohort, apply a power-law retention curve to all historical cohorts to compute DAU, then calculate revenue and costs per model type.

**Mobile (`runway.py`):**
- **F2P:** IAP revenue from payer conversion × ARPPU + ad revenue from eCPM × impressions
- **Premium:** New installs × game price, no recurring revenue. The timeline table, KPI bar, sensitivity, and compare tables show installs (daily new / total) instead of DAU, since each install is a one-time sale with no recurring monetization.
- **Remove Ads:** New installs split — removers pay once, rest generate ad revenue daily
- **Subscription:** Active subscribers × daily rate (price / billing cycle). Subscribers are acquired from new installs at the conversion rate and decay at the daily-equivalent monthly churn. The timeline and metrics show active subscribers (daily active / peak) instead of DAU, since revenue is tied to paying subscribers, not total active users.

Cash inflow lags accrued revenue by the payout delay. Break-even is measured against starting capital (the initial bank balance). CPI increases logarithmically with cumulative paid installs. Viral installs compound recursively via geometric series. When auto-scaling is enabled, daily UA spend is adjusted weekly based on achieved ROI versus the target.

**Web (`web_runway.py`):**
- **Ad revenue:** Sessions × impressions/session × fill rate × RPM, split by portal rev-share
- **IAP revenue:** DAU × payer conversion × avg purchase (available on Social and Custom portals)
- Portal type sets default rev-share, RPM, organic plays, and whether IAP is supported

CDN costs scale with plays; server costs scale with DAU. External UA drives paid installs alongside organic plays. Viral plays compound recursively via geometric series.
