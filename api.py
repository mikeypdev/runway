"""Programmatic API for game financial runway modeling.

Provides a clean, agent-friendly interface to the mobile and web game
simulation engines. No TUI or Textual dependencies required.

Usage:
    from api import MobileGameAPI, WebGameAPI

    # Discover available models and parameters
    MobileGameAPI.list_models()
    MobileGameAPI.parameter_schema()

    # Run a simulation
    api = MobileGameAPI({"model_type": "f2p", "daily_ua_spend": 20.0})
    result = api.evaluate()

    # Compare scenarios
    for price in [0.99, 2.99, 4.99]:
        api = MobileGameAPI({"model_type": "premium", "game_price": price})
        print(price, api.evaluate()["summary"]["final_bank"])
"""

from __future__ import annotations

from typing import Any

import runway
import web_runway

# ---------------------------------------------------------------------------
# Mobile Game API
# ---------------------------------------------------------------------------

MOBILE_MODELS = [
    {
        "id": "f2p",
        "label": "F2P (IAP + Ads)",
        "description": (
            "Free-to-play with in-app purchases and rewarded video ads. "
            "Revenue = DAU × payer_conversion × ARPPU (net of platform fee) + "
            "DAU × ad_impressions × eCPM/1000 (net of ad mediation tax). "
            "Activity metric: DAU (daily active users)."
        ),
    },
    {
        "id": "premium",
        "label": "Premium (Buy Once)",
        "description": (
            "One-time purchase per install, no ads or recurring revenue. "
            "Revenue = new_installs × game_price × (1 - platform_fee). "
            "Activity metric: daily installs (each install is a sale)."
        ),
    },
    {
        "id": "remove_ads",
        "label": "F2P + Remove Ads IAP",
        "description": (
            "Free-to-play where users see ads unless they pay a one-time IAP "
            "to remove them. Revenue = (removal_conversion × removal_price) + "
            "(ad_viewing_DAU × ad_revenue_per_DAU). "
            "Activity metric: DAU."
        ),
    },
    {
        "id": "subscription",
        "label": "Subscription (No Ads)",
        "description": (
            "Monthly or annual recurring subscription, no ads. Subscribers are "
            "acquired from new installs at a conversion rate and decay at a "
            "daily-equivalent of monthly churn. Revenue = active_subscribers × "
            "daily_rate × (1 - platform_fee). "
            "Activity metric: active subscribers."
        ),
    },
]

MOBILE_PARAMETERS = [
    # --- Model selection ---
    {
        "name": "model_type", "label": "Revenue Model", "type": "choice",
        "default": "f2p", "options": ["f2p", "premium", "remove_ads", "subscription"],
        "description": "How the game monetizes. Determines which other parameters are relevant.",
        "models": "all",
    },
    {
        "name": "billing_period", "label": "Billing Period", "type": "choice",
        "default": "monthly", "options": ["monthly", "annual"],
        "description": "Subscription billing cycle. Annual price is divided by 12 for monthly-equivalent LTV.",
        "models": ["subscription"],
    },
    {
        "name": "ua_scaling_mode", "label": "UA Scaling Mode", "type": "choice",
        "default": "manual", "options": ["manual", "auto"],
        "description": "Manual = fixed daily UA spend. Auto = adjusts spend weekly based on achieved ROI vs target.",
        "models": "all",
    },

    # --- Launch & capital ---
    {
        "name": "start_date", "label": "Start Date", "type": "date",
        "default": "today", "format": "YYYY-MM-DD",
        "description": "Day 1 of the simulation.",
        "models": "all",
    },
    {
        "name": "starting_capital", "label": "Starting Capital ($)", "type": "float",
        "default": 1000.0, "min": 0.0,
        "description": "Initial bank balance before day 1. Break-even is measured against this.",
        "models": "all",
    },

    # --- UA scaling ---
    {
        "name": "target_roi", "label": "Target LTV:CPI", "type": "float",
        "default": 3.0, "min": 0.1,
        "description": "Target return ratio for auto-scaling mode. Spend increases when achieved ROI exceeds this.",
        "models": "all",
    },
    {
        "name": "max_daily_budget", "label": "Max Daily Budget ($)", "type": "float",
        "default": 50.0, "min": 0.0,
        "description": "Ceiling on daily UA spend when auto-scaling.",
        "models": "all",
    },
    {
        "name": "scale_speed", "label": "Scale Speed", "type": "float",
        "default": 1.10, "min": 1.0, "max": 2.0,
        "description": "Multiplier applied to UA spend each week when auto-scaling (1.10 = 10% increase).",
        "models": "all",
    },

    # --- Marketing ---
    {
        "name": "daily_ua_spend", "label": "Daily UA Spend ($)", "type": "float",
        "default": 10.0, "min": 0.0,
        "description": "Daily user acquisition spend. In manual mode this is fixed; in auto mode it's the starting point.",
        "models": "all",
    },
    {
        "name": "cpi", "label": "Cost Per Install ($)", "type": "float",
        "default": 0.26, "min": 0.01,
        "description": "Base cost per install for paid UA. Increases logarithmically with cumulative spend via CPI saturation.",
        "models": "all",
    },
    {
        "name": "cpi_saturation", "label": "CPI Saturation", "type": "float",
        "default": 0.30, "min": 0.0,
        "description": "How fast CPI rises as paid installs accumulate. Formula: effective_cpi = base_cpi × (1 + saturation × ln(1 + cumulative_paid/10000)).",
        "models": "all",
    },
    {
        "name": "influencer_installs", "label": "Burst Installs/Day", "type": "float",
        "default": 0.0, "min": 0.0,
        "description": "Fixed daily installs from influencer/marketing bursts (not paid UA, no cost).",
        "models": "all",
    },

    # --- Growth & retention ---
    {
        "name": "organic_ratio", "label": "Organic Ratio", "type": "float",
        "default": 0.10, "min": 0.0,
        "description": "Organic installs as a fraction of paid+burst installs. 0.10 = 10% organic boost.",
        "models": "all",
    },
    {
        "name": "virality_k_factor", "label": "Viral K-Factor", "type": "float",
        "default": 0.05, "min": 0.0, "max": 0.99,
        "description": "Viral spread factor. Each install generates k/(1-k) additional installs recursively. 0.05 = ~5.3% boost.",
        "models": "all",
    },
    {
        "name": "day_1_retention", "label": "D1 Retention (%)", "type": "float",
        "default": 40.0, "min": 1.0, "max": 99.0,
        "description": "Percentage of new installs still active on day 1. Drives the power-law retention curve.",
        "models": "all",
    },
    {
        "name": "decay_exponent", "label": "Retention Decay", "type": "float",
        "default": 0.55, "min": 0.1, "max": 2.0,
        "description": "Power-law exponent for long-term retention. Higher = faster drop-off. retention(d) = D1% × d^(-exponent).",
        "models": "all",
    },

    # --- IAP monetization (F2P) ---
    {
        "name": "payer_pct", "label": "Payer Conversion (%)", "type": "float",
        "default": 3.0, "min": 0.0, "max": 100.0,
        "description": "F2P: fraction of DAU that makes IAP purchases daily. Subscription: fraction of new installs who subscribe.",
        "models": ["f2p", "subscription"],
    },
    {
        "name": "arppu", "label": "ARPPU ($)", "type": "float",
        "default": 5.0, "min": 0.0,
        "description": "Average revenue per paying user per day (F2P IAP).",
        "models": ["f2p"],
    },

    # --- Interstitial ads ---
    {
        "name": "interstitial_ecpm", "label": "Interstitial eCPM ($)", "type": "float",
        "default": 8.0, "min": 0.0,
        "description": "Effective cost per mille (revenue per 1000 impressions) for interstitial ads.",
        "models": ["f2p", "remove_ads"],
    },
    {
        "name": "interstitial_impressions", "label": "Interstitial Impressions/DAU/Day", "type": "float",
        "default": 5.0, "min": 0.0,
        "description": "Average interstitial ad impressions per daily active user per day.",
        "models": ["f2p", "remove_ads"],
    },

    # --- Rewarded video ---
    {
        "name": "rewarded_ecpm", "label": "Rewarded eCPM ($)", "type": "float",
        "default": 15.0, "min": 0.0,
        "description": "Effective cost per mille (revenue per 1000 views) for rewarded video ads.",
        "models": ["f2p", "remove_ads"],
    },
    {
        "name": "rewarded_views", "label": "Rewarded Views/DAU/Day", "type": "float",
        "default": 0.5, "min": 0.0,
        "description": "Average rewarded video views per daily active user per day.",
        "models": ["f2p", "remove_ads"],
    },

    # --- Premium pricing ---
    {
        "name": "game_price", "label": "Game Price ($)", "type": "float",
        "default": 4.99, "min": 0.49,
        "description": "One-time purchase price for the premium model.",
        "models": ["premium"],
    },

    # --- Ad removal IAP ---
    {
        "name": "ad_removal_price", "label": "Removal Price ($)", "type": "float",
        "default": 2.99, "min": 0.0,
        "description": "One-time IAP price to remove ads (Remove Ads model).",
        "models": ["remove_ads"],
    },
    {
        "name": "ad_removal_pct", "label": "Removal Conversion (%)", "type": "float",
        "default": 5.0, "min": 0.0, "max": 100.0,
        "description": "Fraction of new installs who buy ad removal.",
        "models": ["remove_ads"],
    },

    # --- Subscription pricing ---
    {
        "name": "subscription_price", "label": "Subscription Price ($)", "type": "float",
        "default": 0.99, "min": 0.49,
        "description": "Recurring charge per billing period (monthly or annual, set by billing_period).",
        "models": ["subscription"],
    },
    {
        "name": "monthly_churn", "label": "Monthly Churn (%)", "type": "float",
        "default": 8.0, "min": 0.1, "max": 100.0,
        "description": "Percentage of active subscribers who cancel each month. Determines average subscriber lifetime (100/churn months).",
        "models": ["subscription"],
    },

    # --- Platform & payout ---
    {
        "name": "platform_fee", "label": "Platform Fee (%)", "type": "float",
        "default": 30.0, "min": 0.0, "max": 100.0,
        "description": "Store commission on gross revenue (30% = standard Apple/Google).",
        "models": "all",
    },
    {
        "name": "payout_delay_days", "label": "Payout Delay (Days)", "type": "int",
        "default": 30, "min": 0,
        "description": "Days between revenue accruing and cash settling in the bank. Creates the cash-flow lag.",
        "models": "all",
    },

    # --- OpEx ---
    {
        "name": "fixed_overhead_daily", "label": "Fixed Daily Overhead ($)", "type": "float",
        "default": 10.0, "min": 0.0,
        "description": "Baseline daily operating cost (salaries, rent, etc.) regardless of user count.",
        "models": "all",
    },
    {
        "name": "server_cost_per_k_dau", "label": "Server Cost per 1k DAU ($)", "type": "float",
        "default": 0.12, "min": 0.0,
        "description": "Infrastructure cost that scales with daily active users.",
        "models": "all",
    },
]


class MobileGameAPI:
    """Agent-friendly API for the mobile game financial simulator."""

    ENGINE = runway.RevenueLagEngine
    DEFAULT_SCENARIOS = runway.DEFAULT_SCENARIOS
    MODELS = MOBILE_MODELS
    PARAMETERS = MOBILE_PARAMETERS

    def __init__(self, params: dict | None = None):
        """Create a simulation from a parameter dict.

        Missing parameters use engine defaults. Call parameter_schema()
        or list_models() to discover available parameters.
        """
        self.engine = runway.RevenueLagEngine()
        if params:
            self.engine.apply_params(params)

    @classmethod
    def list_models(cls) -> list[dict]:
        """Return available business models with descriptions."""
        return cls.MODELS.copy()

    @classmethod
    def parameter_schema(cls, model_type: str | None = None) -> list[dict]:
        """Return parameter metadata. If model_type is given, filter to applicable params."""
        params = []
        for p in cls.PARAMETERS:
            if model_type is None:
                params.append(p)
            else:
                models = p.get("models", "all")
                if models == "all" or model_type in models:
                    params.append(p)
        return params

    @classmethod
    def default_scenario(cls, model_type: str = "f2p") -> dict:
        """Return a default parameter dict for the given model type."""
        for scenario in cls.DEFAULT_SCENARIOS.values():
            if scenario.get("model_type") == model_type:
                return dict(scenario)
        return {"model_type": model_type}

    @classmethod
    def list_default_scenarios(cls) -> dict[str, dict]:
        """Return all built-in default scenarios."""
        return dict(cls.DEFAULT_SCENARIOS)

    def evaluate(self) -> dict:
        """Run the full 365-day simulation and return structured results.

        Returns a dict with:
            summary: key metrics (ltv, cpi, ratio, margin, revenue, bank, etc.)
            diagnosis: health status and human-readable message
            breakdown: structured LTV decomposition by component
            timeline: 90 daily rows + 9 monthly summaries
        """
        timeline = self.engine.calculate_timeline()
        summary_raw = self.engine.summarize_timeline(timeline, self.engine.starting_capital)

        ltv = self.engine.calculate_ltv()
        realized_ltv = self.engine.get_realized_ltv()
        blended_cpi = self.engine._compute_blended_cpi()
        effective_cpi = self.engine._compute_effective_cpi_for_diagnosis()
        ratio = self.engine.calculate_ltv_cpi_ratio()
        margin = ltv - effective_cpi
        realized_ratio = realized_ltv / effective_cpi if effective_cpi > 0 else float("inf")
        realized_margin = realized_ltv - effective_cpi

        model = self.engine.model_type
        if model == "premium":
            activity_label = "total_installs"
            activity_val = summary_raw["total_installs"]
        elif model == "subscription":
            activity_label = "peak_subs"
            activity_val = summary_raw["peak_subs"]
        else:
            activity_label = "peak_dau"
            activity_val = summary_raw["peak_dau"]

        if realized_ratio < 1.0:
            status, message = "losing", f"Losing ${-realized_margin:.2f}/install — realized ${realized_ltv:.2f} can't cover CPI ${effective_cpi:.2f}"
        elif realized_ratio < 3.0:
            status, message = "thin", f"Profitable but thin — ${realized_margin:.2f}/install margin (realized {realized_ratio:.1f}× CPI)"
        else:
            status, message = "healthy", f"Healthy — ${realized_margin:.2f}/install margin (realized {realized_ratio:.1f}× CPI)"

        return {
            "summary": {
                "model_type": model,
                "ltv": round(ltv, 4),
                "realized_ltv": round(realized_ltv, 4),
                "blended_cpi": round(blended_cpi, 4),
                "effective_cpi": round(effective_cpi, 4),
                "ltv_cpi_ratio": round(ratio, 4),
                "realized_ltv_cpi_ratio": round(realized_ratio, 4),
                "margin_per_install": round(margin, 4),
                "realized_margin_per_install": round(realized_margin, 4),
                activity_label: activity_val,
                "total_revenue": round(summary_raw["total_accrued"], 2),
                "final_bank": round(summary_raw["final_bank"], 2),
                "break_even_day": summary_raw["break_even_day"],
            },
            "diagnosis": {
                "status": status,
                "message": message,
            },
            "breakdown": self._structured_breakdown(ltv, effective_cpi),
            "timeline": timeline,
        }

    def _structured_breakdown(self, ltv: float, cpi: float) -> dict:
        """Return structured LTV decomposition (not markup)."""
        lifetime = self.engine.calculate_lifetime()
        model = self.engine.model_type
        components: dict[str, float] = {}
        description: str = ""

        if model == "premium":
            components["game_price_net"] = round(ltv, 4)
            description = f"Net price after {self.engine.platform_fee:.0f}% platform fee"
        elif model == "remove_ads":
            ad_arpu = (self.engine.interstitial_ecpm * self.engine.interstitial_impressions + self.engine.rewarded_ecpm * self.engine.rewarded_views) / 1000.0
            removal = (self.engine.ad_removal_pct / 100.0) * self.engine.ad_removal_price * (1.0 - self.engine.platform_fee / 100.0)
            ad = (1.0 - self.engine.ad_removal_pct / 100.0) * ad_arpu * lifetime * (1.0 - self.engine.ad_mediation_tax)
            components["removal_iap"] = round(removal, 4)
            components["ad_revenue"] = round(ad, 4)
            description = f"Lifetime {lifetime:.0f} days, {self.engine.ad_removal_pct:.0f}% buy removal"
        elif model == "subscription":
            lifetime_months = 100.0 / self.engine.monthly_churn
            monthly_rev = self.engine.subscription_price if self.engine.billing_period == "monthly" else self.engine.subscription_price / 12.0
            net_monthly = monthly_rev * (1.0 - self.engine.platform_fee / 100.0)
            ltv_per_sub = net_monthly * lifetime_months
            components["ltv_per_subscriber"] = round(ltv_per_sub, 4)
            components["conversion_rate"] = self.engine.payer_pct / 100.0
            components["effective_per_install"] = round(ltv, 4)
            description = f"{lifetime_months:.1f} month avg lifetime, {self.engine.payer_pct:.1f}% conversion"
        else:
            daily_payer = self.engine.calculate_daily_payer_arppu()
            ad_arpu = (self.engine.interstitial_ecpm * self.engine.interstitial_impressions + self.engine.rewarded_ecpm * self.engine.rewarded_views) / 1000.0
            iap = (self.engine.payer_pct / 100.0) * daily_payer * (1.0 - self.engine.platform_fee / 100.0) * lifetime
            ads = ad_arpu * (1.0 - self.engine.ad_mediation_tax) * lifetime
            components["iap_revenue"] = round(iap, 4)
            components["ad_revenue"] = round(ads, 4)
            description = f"Lifetime {lifetime:.0f} days, {self.engine.payer_pct:.0f}% payers"

        return {
            "description": description,
            "components": components,
            "total_ltv": round(ltv, 4),
            "blended_cpi": round(self.engine._compute_blended_cpi(), 4),
            "effective_cpi": round(cpi, 4),
            "margin_per_install": round(ltv - cpi, 4),
        }

    def sensitivity(self, param: str, values: list[float] | None = None) -> list[dict]:
        """Sweep a parameter across multiple values and return summaries.

        If values is None, uses default multipliers [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
        applied to the current value.
        """
        orig = getattr(self.engine, param)
        if values is None:
            values = [max(0.01, orig * m) for m in [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]]

        results = []
        orig_scaling = self.engine.ua_scaling_mode
        self.engine.ua_scaling_mode = "manual"
        try:
            for v in values:
                setattr(self.engine, param, v)
                timeline = self.engine.calculate_timeline()
                summary = self.engine.summarize_timeline(timeline, self.engine.starting_capital)
                ltv = self.engine.calculate_ltv()
                ratio = self.engine.calculate_ltv_cpi_ratio()
                results.append({
                    param: v,
                    "ltv": round(ltv, 4),
                    "ltv_cpi_ratio": round(ratio, 4),
                    "total_revenue": round(summary["total_accrued"], 2),
                    "final_bank": round(summary["final_bank"], 2),
                    "break_even_day": summary["break_even_day"],
                })
        finally:
            setattr(self.engine, param, orig)
            self.engine.ua_scaling_mode = orig_scaling
        return results

    def solve(self, param: str, target_metric: str, target_value: float,
              low: float = 0.01, high: float = 100.0) -> dict | None:
        """Find the value of param that achieves target_value for target_metric.

        Args:
            param: Parameter name to solve for (e.g. "cpi", "subscription_price").
            target_metric: One of "final_bank" or "ltv_cpi_ratio".
            target_value: The target value for the metric.
            low, high: Search bounds for the parameter.

        Returns dict with the solved value, or None if infeasible.
        """
        target_fn = {
            "final_bank": self.engine.get_final_bank,
            "ltv_cpi_ratio": self.engine.get_ltv_cpi,
        }.get(target_metric)

        if target_fn is None:
            raise ValueError(f"Unknown target_metric '{target_metric}'. Use 'final_bank' or 'ltv_cpi_ratio'.")

        result = self.engine.solve_parameter(param, target_fn, target_value, low, high)
        if result is None:
            return None
        return {"param": param, "value": result, "target_metric": target_metric, "target_value": target_value}


# ---------------------------------------------------------------------------
# Web Game API
# ---------------------------------------------------------------------------

WEB_PORTALS = [
    {"id": "Web Portal", "rev_share": 50.0, "rpm": 2.00, "iap": False,
     "organic_plays": 3000, "description": "Standard rev-share portal. 50% portal cut, $2 RPM, no IAP support."},
    {"id": "Playable Ads", "rev_share": 60.0, "rpm": 1.20, "iap": False,
     "organic_plays": 6000, "description": "Ad-driven discovery portal. 60% cut, lower $1.20 RPM, higher organic volume."},
    {"id": "Social App Mini Game", "rev_share": 50.0, "rpm": 1.50, "iap": True,
     "organic_plays": 2000, "description": "Mini games inside social/messaging apps. 50% cut, $1.50 RPM, IAP + ads."},
    {"id": "Custom Web", "rev_share": 0.0, "rpm": 1.00, "iap": True,
     "organic_plays": 0, "description": "Self-published, no rev share, $1 RPM, IAP + ads. Requires paid UA."},
]

WEB_PARAMETERS = [
    # --- Portal ---
    {
        "name": "portal", "label": "Publish Portal", "type": "choice",
        "default": "Web Portal", "options": ["Web Portal", "Playable Ads", "Social App Mini Game", "Custom Web"],
        "description": "Distribution portal. Sets default rev-share, RPM, organic plays, and IAP availability.",
        "models": "all",
    },

    # --- Launch & capital ---
    {
        "name": "start_date", "label": "Start Date", "type": "date",
        "default": "today", "format": "YYYY-MM-DD",
        "description": "Day 1 of the simulation.",
        "models": "all",
    },
    {
        "name": "starting_capital", "label": "Starting Capital ($)", "type": "float",
        "default": 5000.0, "min": 0.0,
        "description": "Initial bank balance before day 1.",
        "models": "all",
    },

    # --- Traffic & acquisition ---
    {
        "name": "organic_plays_per_day", "label": "Organic Plays/Day", "type": "float",
        "default": 3000.0, "min": 0.0,
        "description": "Free daily plays from portal traffic. Grows with cumulative plays (traction factor).",
        "models": "all",
    },
    {
        "name": "min_plays_per_day", "label": "Min Guaranteed Plays", "type": "float",
        "default": 0.0, "min": 0.0,
        "description": "Floor on daily organic plays (portal guarantee).",
        "models": "all",
    },
    {
        "name": "external_ua_spend", "label": "External UA Spend ($)", "type": "float",
        "default": 0.0, "min": 0.0,
        "description": "Daily paid acquisition budget. Zero = organic-only traffic.",
        "models": "all",
    },
    {
        "name": "external_cpi", "label": "External CPI ($)", "type": "float",
        "default": 0.30, "min": 0.01,
        "description": "Cost per acquired player for external UA.",
        "models": "all",
    },
    {
        "name": "cpi_saturation", "label": "CPI Saturation", "type": "float",
        "default": 0.3, "min": 0.0,
        "description": "How much CPI grows with cumulative paid installs.",
        "models": "all",
    },
    {
        "name": "viral_k", "label": "Viral K-Factor", "type": "float",
        "default": 0.02, "min": 0.0, "max": 0.99,
        "description": "Viral spread. Each play generates k/(1-k) additional plays recursively.",
        "models": "all",
    },

    # --- Engagement & retention ---
    {
        "name": "day_1_retention", "label": "D1 Retention (%)", "type": "float",
        "default": 18.0, "min": 1.0, "max": 99.0,
        "description": "Percentage of players returning on day 1. Web games typically have lower retention than mobile.",
        "models": "all",
    },
    {
        "name": "decay_exponent", "label": "Retention Decay", "type": "float",
        "default": 0.55, "min": 0.1, "max": 2.0,
        "description": "Power-law exponent for retention curve drop-off.",
        "models": "all",
    },
    {
        "name": "sessions_per_day", "label": "Sessions per Day", "type": "float",
        "default": 1.3, "min": 0.1,
        "description": "Average sessions per daily active player.",
        "models": "all",
    },
    {
        "name": "impressions_per_session", "label": "Ad Impressions/Session", "type": "float",
        "default": 2.5, "min": 0.0,
        "description": "Ad impressions shown per session.",
        "models": "all",
    },
    {
        "name": "ad_fill_rate", "label": "Ad Fill Rate (%)", "type": "float",
        "default": 80.0, "min": 0.0, "max": 100.0,
        "description": "Percentage of ad requests that are filled with actual ads.",
        "models": "all",
    },

    # --- Monetization ---
    {
        "name": "base_rpm", "label": "Base RPM ($)", "type": "float",
        "default": 2.00, "min": 0.0,
        "description": "Revenue per 1000 ad impressions, before portal rev-share.",
        "models": "all",
    },
    {
        "name": "rpm_growth_rate", "label": "RPM Growth Rate", "type": "float",
        "default": 0.0, "min": 0.0,
        "description": "RPM growth over time. RPM(d) = base_rpm × (1 + growth_rate × ln(1+d)).",
        "models": "all",
    },
    {
        "name": "portal_rev_share", "label": "Portal Rev Share (%)", "type": "float",
        "default": 50.0, "min": 0.0, "max": 100.0,
        "description": "Portal's cut of gross revenue.",
        "models": "all",
    },
    {
        "name": "iap_payer_pct", "label": "IAP Payer (%)", "type": "float",
        "default": 0.0, "min": 0.0, "max": 100.0,
        "description": "Fraction of new players who make an IAP purchase. Only available on Social App Mini Game and Custom portals.",
        "models": ["Social App Mini Game", "Custom Web"],
    },
    {
        "name": "iap_avg_purchase", "label": "IAP Avg Purchase ($)", "type": "float",
        "default": 0.0, "min": 0.0,
        "description": "Average one-time IAP purchase amount.",
        "models": ["Social App Mini Game", "Custom Web"],
    },

    # --- Costs ---
    {
        "name": "payout_delay_days", "label": "Payout Delay (Days)", "type": "int",
        "default": 30, "min": 0,
        "description": "Days between revenue accruing and cash settling.",
        "models": "all",
    },
    {
        "name": "fixed_overhead_daily", "label": "Fixed Daily Overhead ($)", "type": "float",
        "default": 200.0, "min": 0.0,
        "description": "Baseline daily operating cost.",
        "models": "all",
    },
    {
        "name": "server_cost_per_k_dau", "label": "Server Cost per 1k DAU ($)", "type": "float",
        "default": 0.50, "min": 0.0,
        "description": "Infrastructure cost scaling with daily active users.",
        "models": "all",
    },
    {
        "name": "cdn_cost_per_k_plays", "label": "CDN Cost per 1k Plays ($)", "type": "float",
        "default": 0.10, "min": 0.0,
        "description": "Content delivery cost scaling with plays.",
        "models": "all",
    },
]


class WebGameAPI:
    """Agent-friendly API for the web game financial simulator."""

    ENGINE = web_runway.WebGameEngine
    DEFAULT_SCENARIOS = web_runway.DEFAULT_SCENARIOS
    PORTALS = WEB_PORTALS
    PARAMETERS = WEB_PARAMETERS

    def __init__(self, params: dict | None = None):
        """Create a simulation from a parameter dict."""
        self.engine = web_runway.WebGameEngine()
        if params:
            self.engine.apply_params(params)

    @classmethod
    def list_portals(cls) -> list[dict]:
        """Return available web game portals with their default economics."""
        return cls.PORTALS.copy()

    @classmethod
    def parameter_schema(cls) -> list[dict]:
        """Return parameter metadata for all web game parameters."""
        return cls.PARAMETERS.copy()

    @classmethod
    def default_scenario(cls, portal: str = "Web Portal") -> dict:
        """Return a default parameter dict for the given portal."""
        for scenario in cls.DEFAULT_SCENARIOS.values():
            if scenario.get("portal") == portal:
                return dict(scenario)
        return {"portal": portal}

    @classmethod
    def list_default_scenarios(cls) -> dict[str, dict]:
        """Return all built-in default scenarios."""
        return dict(cls.DEFAULT_SCENARIOS)

    def evaluate(self) -> dict:
        """Run the full 365-day simulation and return structured results.

        For paid UA scenarios, the diagnosis uses LTV vs CPI margin.
        For organic-only scenarios, it uses daily revenue vs daily costs.
        """
        timeline = self.engine.calculate_timeline()
        summary_raw = self.engine.summarize_timeline(timeline, self.engine.starting_capital)

        ltv = self.engine.calculate_ltv()
        realized_ltv = self.engine.get_realized_ltv()
        blended_cpi = self.engine._compute_blended_cpi()
        effective_cpi = self.engine._compute_effective_cpi_for_diagnosis()

        daily_rows = timeline[:30]
        avg_daily_rev = sum(d["accrued_rev"] for d in daily_rows) / len(daily_rows)
        avg_daily_cost = sum(d["ops_cost"] for d in daily_rows) / len(daily_rows)

        if self.engine.external_ua_spend > 0:
            realized_ratio = realized_ltv / effective_cpi if effective_cpi > 0 else float("inf")
            realized_margin = realized_ltv - effective_cpi
            if realized_ratio < 1.0:
                status, message = "losing", f"Losing ${-realized_margin:.2f}/install — realized ${realized_ltv:.2f} can't cover CPI ${effective_cpi:.2f}"
            elif realized_ratio < 3.0:
                status, message = "thin", f"Profitable but thin — ${realized_margin:.2f}/install margin (realized {realized_ratio:.1f}× CPI)"
            else:
                status, message = "healthy", f"Healthy — ${realized_margin:.2f}/install margin (realized {realized_ratio:.1f}× CPI)"
        else:
            daily_margin = avg_daily_rev - avg_daily_cost
            if daily_margin < 0:
                status, message = "losing", f"Daily burn: ${avg_daily_cost:.0f}/day — revenue ${avg_daily_rev:.0f}/day can't cover costs"
            elif daily_margin < avg_daily_cost * 0.3:
                status, message = "thin", f"Thin — revenue ${avg_daily_rev:.0f}/day vs costs ${avg_daily_cost:.0f}/day (${daily_margin:+.0f}/day)"
            else:
                status, message = "healthy", f"Revenue ${avg_daily_rev:.0f}/day covers costs ${avg_daily_cost:.0f}/day (margin ${daily_margin:+.0f}/day)"

        return {
            "summary": {
                "portal": self.engine.portal,
                "ltv": round(ltv, 4),
                "realized_ltv": round(realized_ltv, 4),
                "blended_cpi": round(blended_cpi, 4) if self.engine.external_ua_spend > 0 else None,
                "effective_cpi": round(effective_cpi, 4) if self.engine.external_ua_spend > 0 else None,
                "total_revenue": round(summary_raw["total_accrued"], 2),
                "total_plays": summary_raw["total_plays"],
                "peak_dau": summary_raw["peak_dau"],
                "final_bank": round(summary_raw["final_bank"], 2),
                "break_even_day": summary_raw["break_even_day"],
                "avg_daily_revenue": round(avg_daily_rev, 2),
                "avg_daily_costs": round(avg_daily_cost, 2),
            },
            "diagnosis": {
                "status": status,
                "message": message,
            },
            "breakdown": self._structured_breakdown(ltv, effective_cpi),
            "timeline": timeline,
        }

    def _structured_breakdown(self, ltv: float, cpi: float) -> dict:
        """Return structured LTV decomposition."""
        lifetime = self.engine.calculate_lifetime()
        net_rpm_per_imp = (self.engine.base_rpm / 1000.0) * (1.0 - self.engine.portal_rev_share / 100.0) * (self.engine.ad_fill_rate / 100.0)
        ad_ltv = lifetime * self.engine.sessions_per_day * self.engine.impressions_per_session * net_rpm_per_imp

        components: dict[str, Any] = {
            "player_lifetime_days": round(lifetime, 1),
            "sessions_per_day": self.engine.sessions_per_day,
            "impressions_per_session": self.engine.impressions_per_session,
            "ad_fill_rate": self.engine.ad_fill_rate / 100.0,
            "net_rpm_per_impression": round(net_rpm_per_imp, 6),
            "ad_revenue_per_install": round(ad_ltv, 4),
        }

        if self.engine._is_iap_supported() and self.engine.iap_payer_pct > 0:
            iap_ltv = (self.engine.iap_payer_pct / 100.0) * self.engine.iap_avg_purchase * (1.0 - self.engine.portal_rev_share / 100.0)
            components["iap_revenue_per_install"] = round(iap_ltv, 4)

        return {
            "components": components,
            "total_ltv": round(ltv, 4),
            "effective_cpi": round(cpi, 4) if self.engine.external_ua_spend > 0 else None,
        }

    def sensitivity(self, param: str, values: list[float] | None = None) -> list[dict]:
        """Sweep a parameter across multiple values and return summaries."""
        orig = getattr(self.engine, param)
        if values is None:
            values = [max(0.01, orig * m) for m in [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]]

        results = []
        try:
            for v in values:
                setattr(self.engine, param, v)
                timeline = self.engine.calculate_timeline()
                summary = self.engine.summarize_timeline(timeline, self.engine.starting_capital)
                ltv = self.engine.calculate_ltv()
                results.append({
                    param: v,
                    "ltv": round(ltv, 4),
                    "total_revenue": round(summary["total_accrued"], 2),
                    "final_bank": round(summary["final_bank"], 2),
                    "break_even_day": summary["break_even_day"],
                })
        finally:
            setattr(self.engine, param, orig)
        return results

    def solve(self, param: str, target_metric: str, target_value: float,
              low: float = 0.01, high: float = 100.0) -> dict | None:
        """Find the value of param that achieves target_value for target_metric.

        target_metric can be "final_bank" or "ltv_cpi_ratio".
        """
        target_fn = {
            "final_bank": self.engine.get_final_bank,
            "ltv_cpi_ratio": self.engine.get_ltv_cpi,
        }.get(target_metric)

        if target_fn is None:
            raise ValueError(f"Unknown target_metric '{target_metric}'. Use 'final_bank' or 'ltv_cpi_ratio'.")

        result = self.engine.solve_parameter(param, target_fn, target_value, low, high)
        if result is None:
            return None
        return {"param": param, "value": result, "target_metric": target_metric, "target_value": target_value}


# ---------------------------------------------------------------------------
# Convenience: compare multiple scenarios
# ---------------------------------------------------------------------------

def compare_mobile_scenarios(scenarios: dict[str, dict]) -> list[dict]:
    """Run multiple mobile game scenarios and return a comparison table.

    Args:
        scenarios: Dict of {name: params_dict}

    Returns list of {name, ltv, ratio, revenue, final_bank, break_even, diagnosis}.
    """
    results = []
    for name, params in scenarios.items():
        api = MobileGameAPI(params)
        eval_result = api.evaluate()
        results.append({
            "name": name,
            "model_type": eval_result["summary"]["model_type"],
            "ltv": eval_result["summary"]["ltv"],
            "realized_ltv": eval_result["summary"]["realized_ltv"],
            "ltv_cpi_ratio": eval_result["summary"]["ltv_cpi_ratio"],
            "realized_ltv_cpi_ratio": eval_result["summary"]["realized_ltv_cpi_ratio"],
            "total_revenue": eval_result["summary"]["total_revenue"],
            "final_bank": eval_result["summary"]["final_bank"],
            "break_even_day": eval_result["summary"]["break_even_day"],
            "diagnosis": eval_result["diagnosis"]["status"],
        })
    return results


def compare_web_scenarios(scenarios: dict[str, dict]) -> list[dict]:
    """Run multiple web game scenarios and return a comparison table."""
    results = []
    for name, params in scenarios.items():
        api = WebGameAPI(params)
        eval_result = api.evaluate()
        results.append({
            "name": name,
            "portal": eval_result["summary"]["portal"],
            "ltv": eval_result["summary"]["ltv"],
            "realized_ltv": eval_result["summary"]["realized_ltv"],
            "total_revenue": eval_result["summary"]["total_revenue"],
            "final_bank": eval_result["summary"]["final_bank"],
            "break_even_day": eval_result["summary"]["break_even_day"],
            "diagnosis": eval_result["diagnosis"]["status"],
        })
    return results
