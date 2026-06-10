# runway

Interactive terminal UI for modeling a game's financial runway over 12 months.

## What it does

Simulates 365 days of game economics — user acquisition, retention, monetization, and operating costs — with a distinction between accrued revenue and actual cash settlement. Shows 90 days of daily projections plus monthly summaries for months 4–12.

Supports three business models:
- **F2P (IAP + Ads)** — tiered payer spending + rewarded video ad revenue
- **Premium (Buy Once)** — one-time purchase per install, no ads
- **F2P + Remove Ads IAP** — free users generate ad revenue, paying users remove ads via one-time IAP

Multiple named scenarios can be saved and compared side-by-side (peak DAU, total accrued revenue, break-even day, year-end bank balance).

## Quick start

```bash
./runway.sh
```

Requires a Python 3.14 virtualenv at `.venv/` with `textual` and `rich` installed.

## Parameters

| Section | Parameter | What it controls |
|---|---|---|
| **Launch Date** | Start Date | Day 1 of the simulation (defaults to today) |
| **Business Model** | Revenue Model | F2P, Premium, or Remove Ads — shows/hides relevant params |
| **Marketing Capital** | Daily UA Spend | Daily user acquisition budget |
| | Cost Per Install | Base cost per paid install |
| | CPI Saturation | How much CPI grows as cumulative installs increase (0 = off) |
| | Burst / Influencer Installs | Daily non-paid installs from campaigns |
| **Growth & Retention** | Organic Install Ratio | Free installs as a ratio of paid |
| | Viral K-Factor | Additional installs per user (recursive) |
| | D1 Retention | Day-1 retention percentage |
| | Retention Decay Rate | Power-law exponent for long-term retention |
| **IAP Monetization** *(F2P only)* | Payer Conversion Rate | Fraction of DAU that spends |
| | Avg Whale Daily Spend | Per-whale daily IAP spend |
| **Ad Revenue** *(F2P, Remove Ads)* | Video Ad eCPM | Revenue per 1000 ad impressions |
| | Ad Impressions / DAU / Day | Rewarded video ad frequency |
| **Premium Pricing** *(Premium only)* | Game Price | One-time purchase price |
| **Ad Removal IAP** *(Remove Ads only)* | Ad Removal Price | One-time IAP to disable ads |
| | Removal Conversion % | Fraction of new installs that buy removal |
| **Platform Fees** | Platform Fee | Store commission (0.30 = standard) |
| | Platform Payout Delay | Days before accrued revenue settles as cash |
| **Live-Ops OpEx** | Fixed Daily Overhead | Baseline daily operating cost |
| | Server Cost per 1k DAU | Infrastructure cost that scales with users |

## Key bindings

- `r` — Recalculate
- `q` — Quit
- `ESC` — Unfocus current input
- `↑` / `↓` — Navigate between input fields

All parameters auto-recalculate on every keystroke.

## Scenarios

Default scenarios ship with each business model:

- **F2P Base Case** — Moderate spend, standard metrics
- **Premium $4.99** — Buy-once model with higher CPI
- **F2P Remove Ads $2.99** — Hybrid ad + removal IAP

Scenarios are saved to `scenarios.json`. Delete that file to reset to defaults.

## How it works

The engine tracks each day's new installs as a cohort, applies a power-law retention curve to all historical cohorts to compute DAU, then calculates revenue and costs per model type:

- **F2P:** IAP revenue from spending tiers × payer % + ad revenue from eCPM × impressions
- **Premium:** New installs × game price, no recurring revenue
- **Remove Ads:** New installs split — removers pay once, rest generate ad revenue daily

Cash inflow lags accrued revenue by the payout delay. CPI increases logarithmically with cumulative paid installs. Viral installs compound recursively via geometric series.
