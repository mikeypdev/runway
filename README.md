# bizmodel

Interactive terminal UI for modeling a free-to-play mobile game's financial runway over 12 months.

## What it does

Simulates 365 days of a F2P game's economics — user acquisition, retention, monetization (IAP + ads), and operating costs — with a distinction between accrued revenue and actual cash settlement. Shows 90 days of daily projections plus monthly summaries for months 4–12.

Supports multiple named scenarios with side-by-side comparison of key metrics (peak DAU, total accrued revenue, break-even day, year-end bank balance).

## Quick start

```bash
./model.sh
```

Requires a Python 3.14 virtualenv at `.venv/` with `textual` and `rich` installed.

## Parameters

| Section | Parameter | What it controls |
|---|---|---|
| **Marketing Capital** | Daily UA Spend | Daily user acquisition budget |
| | Cost Per Install | Base cost per paid install |
| | CPI Saturation | How much CPI grows as cumulative installs increase (0 = off) |
| | Burst / Influencer Installs | Daily non-paid installs from campaigns |
| **Growth & Retention** | Organic Install Ratio | Free installs as a ratio of paid |
| | Viral K-Factor | Additional installs per user (recursive) |
| | D1 Retention | Day-1 retention percentage |
| | Retention Decay Rate | Power-law exponent for long-term retention |
| **Monetization** | Payer Conversion Rate | Fraction of DAU that spends |
| | Avg Whale Daily Spend | Per-whale daily IAP spend |
| | Video Ad eCPM | Revenue per 1000 ad impressions |
| | Ad Impressions / DAU / Day | Rewarded video ad frequency |
| | Platform Fee | Store commission (30% = standard) |
| **Cash Timing** | Platform Payout Delay | Days before accrued revenue settles as cash |
| **Live-Ops OpEx** | Fixed Daily Overhead | Baseline daily operating cost |
| | Server Cost per 1k DAU | Infrastructure cost that scales with users |

## Key bindings

- `r` — Recalculate
- `q` — Quit

All parameters auto-recalculate on every keystroke.

## Scenarios

Three built-in scenarios ship by default:

- **Base Case** — Moderate spend, standard metrics
- **Conservative** — Low spend, weaker retention, longer payout delay
- **Aggressive** — High spend with influencer burst, better retention, lower platform fee (e.g., web shop)

Scenarios are saved to `scenarios.json`. Delete that file to reset to defaults.

## How it works

The engine tracks each day's new installs as a cohort, applies a power-law retention curve to all historical cohorts to compute DAU, then calculates revenue (IAP via spending tiers + ads via eCPM × impressions) and costs (fixed overhead + scaling server/support + UA spend). Cash inflow lags accrued revenue by the payout delay. CPI increases logarithmically with cumulative paid installs, and viral installs compound recursively via geometric series.
