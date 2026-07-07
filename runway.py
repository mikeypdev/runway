import datetime
import json
import math
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input, Label, TabbedContent, TabPane, DataTable, Select, Button, Static, Collapsible
from rich.text import Text

SCENARIOS_FILE = Path("scenarios.json")

SCALING_OPTIONS = [
    ("Manual (fixed spend)", "manual"),
    ("Auto-scale (ROI-based)", "auto"),
]

MODEL_F2P = "f2p"
MODEL_PREMIUM = "premium"
MODEL_REMOVE_ADS = "remove_ads"
MODEL_SUBSCRIPTION = "subscription"

MODEL_OPTIONS = [
    ("F2P (IAP + Ads)", MODEL_F2P),
    ("Premium (Buy Once)", MODEL_PREMIUM),
    ("F2P + Remove Ads IAP", MODEL_REMOVE_ADS),
    ("Subscription (No Ads)", MODEL_SUBSCRIPTION),
]

BILLING_MONTHLY = "monthly"
BILLING_ANNUAL = "annual"

BILLING_OPTIONS = [
    ("Monthly", BILLING_MONTHLY),
    ("Annual", BILLING_ANNUAL),
]

EXPOSED_PARAMS = [
    ("daily_ua_spend", "in_ua_spend", float),
    ("target_roi", "in_target_roi", float),
    ("max_daily_budget", "in_max_budget", float),
    ("scale_speed", "in_scale_speed", float),
    ("cpi", "in_cpi", float),
    ("cpi_saturation", "in_cpi_sat", float),
    ("influencer_installs", "in_influencer", float),
    ("organic_ratio", "in_organic", float),
    ("virality_k_factor", "in_kfactor", float),
    ("payer_pct", "in_payer_pct", float),
    ("payer_pct", "in_sub_conversion", float),
    ("arppu", "in_arppu", float),
    ("video_ecpm", "in_video_ecpm", float),
    ("video_impressions", "in_video_impressions", float),
    ("platform_fee", "in_platform_fee", float),
    ("payout_delay_days", "in_delay", int),
    ("fixed_overhead_daily", "in_fixed_ops", float),
    ("server_cost_per_k_dau", "in_server_k", float),
    ("day_1_retention", "in_d1_retention", float),
    ("decay_exponent", "in_decay", float),
    ("game_price", "in_game_price", float),
    ("ad_removal_price", "in_ad_removal_price", float),
    ("ad_removal_pct", "in_ad_removal_pct", float),
    ("subscription_price", "in_sub_price", float),
    ("monthly_churn", "in_monthly_churn", float),
    ("start_date", "in_start_date", str),
    ("starting_capital", "in_starting_capital", float),
]

DEFAULT_SCENARIOS = {
    "F2P Base Case": {
        "model_type": MODEL_F2P,
        "starting_capital": 1000.0,
        "ua_scaling_mode": "manual", "target_roi": 3.0, "max_daily_budget": 50.0, "scale_speed": 1.10,
        "daily_ua_spend": 10.00, "cpi": 0.26, "cpi_saturation": 0.30,
        "influencer_installs": 0.0,
        "organic_ratio": 0.10, "virality_k_factor": 0.05,
        "payer_pct": 3.0, "arppu": 0.75,
        "video_ecpm": 80.00, "video_impressions": 0.33, "platform_fee": 30.0,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 10.00, "server_cost_per_k_dau": 0.12,
        "day_1_retention": 40.0, "decay_exponent": 0.55,
        "game_price": 4.99, "ad_removal_price": 2.99, "ad_removal_pct": 5.0,
        "subscription_price": 0.99, "monthly_churn": 8.0, "billing_period": BILLING_MONTHLY,
    },
    "Premium $4.99": {
        "model_type": MODEL_PREMIUM,
        "starting_capital": 1000.0,
        "ua_scaling_mode": "manual", "target_roi": 3.0, "max_daily_budget": 50.0, "scale_speed": 1.10,
        "daily_ua_spend": 15.00, "cpi": 0.80, "cpi_saturation": 0.40,
        "influencer_installs": 10.0,
        "organic_ratio": 0.12, "virality_k_factor": 0.04,
        "payer_pct": 3.0, "arppu": 0.75,
        "video_ecpm": 0.0, "video_impressions": 0.0, "platform_fee": 30.0,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 10.00, "server_cost_per_k_dau": 0.12,
        "day_1_retention": 45.0, "decay_exponent": 0.50,
        "game_price": 4.99, "ad_removal_price": 2.99, "ad_removal_pct": 5.0,
        "subscription_price": 0.99, "monthly_churn": 8.0, "billing_period": BILLING_MONTHLY,
    },
    "F2P Remove Ads $2.99": {
        "model_type": MODEL_REMOVE_ADS,
        "starting_capital": 1000.0,
        "ua_scaling_mode": "manual", "target_roi": 3.0, "max_daily_budget": 50.0, "scale_speed": 1.10,
        "daily_ua_spend": 10.00, "cpi": 0.26, "cpi_saturation": 0.30,
        "influencer_installs": 0.0,
        "organic_ratio": 0.10, "virality_k_factor": 0.05,
        "payer_pct": 3.0, "arppu": 0.75,
        "video_ecpm": 80.00, "video_impressions": 0.33, "platform_fee": 30.0,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 10.00, "server_cost_per_k_dau": 0.12,
        "day_1_retention": 40.0, "decay_exponent": 0.55,
        "game_price": 4.99, "ad_removal_price": 2.99, "ad_removal_pct": 5.0,
        "subscription_price": 0.99, "monthly_churn": 8.0, "billing_period": BILLING_MONTHLY,
    },
    "Subscription $0.99/mo": {
        "model_type": MODEL_SUBSCRIPTION,
        "starting_capital": 1000.0,
        "ua_scaling_mode": "manual", "target_roi": 3.0, "max_daily_budget": 50.0, "scale_speed": 1.10,
        "daily_ua_spend": 8.00, "cpi": 0.35, "cpi_saturation": 0.30,
        "influencer_installs": 0.0,
        "organic_ratio": 0.10, "virality_k_factor": 0.06,
        "payer_pct": 2.0, "arppu": 0.75,
        "video_ecpm": 0.0, "video_impressions": 0.0, "platform_fee": 30.0,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 10.00, "server_cost_per_k_dau": 0.12,
        "day_1_retention": 45.0, "decay_exponent": 0.50,
        "game_price": 4.99, "ad_removal_price": 2.99, "ad_removal_pct": 5.0,
        "subscription_price": 0.99, "monthly_churn": 8.0, "billing_period": BILLING_MONTHLY,
    },
}


class ScenarioStore:
    def __init__(self):
        self.scenarios: dict[str, dict] = {}
        self._load()

    def _load(self):
        if SCENARIOS_FILE.exists():
            try:
                self.scenarios = json.loads(SCENARIOS_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                self.scenarios = {}
        if not self.scenarios:
            self.scenarios = dict(DEFAULT_SCENARIOS)
            self.save()

    def save(self):
        SCENARIOS_FILE.write_text(json.dumps(self.scenarios, indent=2) + "\n")

    def list_names(self) -> list[str]:
        return list(self.scenarios.keys())

    def get(self, name: str) -> dict | None:
        return self.scenarios.get(name)

    def put(self, name: str, params: dict):
        self.scenarios[name] = params
        self.save()

    def delete(self, name: str):
        self.scenarios.pop(name, None)
        self.save()


class RevenueLagEngine:
    def __init__(self):
        self.model_type = MODEL_F2P
        self.influencer_installs = 0.0
        self.organic_ratio = 0.10
        self.virality_k_factor = 0.05
        self.cpi = 0.26
        self.cpi_saturation = 0.30
        self.daily_ua_spend = 10.00

        self.ua_scaling_mode = "manual"
        self.target_roi = 3.0
        self.max_daily_budget = 50.0
        self.scale_speed = 1.10

        self.payer_pct = 3.0
        self.arppu = 0.75
        self.platform_fee = 30.0
        self.video_ecpm = 80.00
        self.video_impressions = 0.33

        self.fixed_overhead_daily = 10.00
        self.server_cost_per_k_dau = 0.12
        self.support_cost_per_k_dau = 0.04
        self.ad_mediation_tax = 0.02

        self.day_1_retention = 40.0
        self.decay_exponent = 0.55

        self.payout_delay_days = 30

        self.game_price = 4.99
        self.ad_removal_price = 2.99
        self.ad_removal_pct = 5.0
        self.subscription_price = 0.99
        self.monthly_churn = 8.0
        self.billing_period = BILLING_MONTHLY
        self.start_date = datetime.date.today().strftime("%Y-%m-%d")
        self.starting_capital = 1000.0

    def apply_params(self, params: dict):
        if "model_type" in params:
            self.model_type = params["model_type"]
        if "ua_scaling_mode" in params:
            self.ua_scaling_mode = params["ua_scaling_mode"]
        if "billing_period" in params:
            self.billing_period = params["billing_period"]
        start_date_input = datetime.date.today().strftime("%Y-%m-%d")
        for attr, widget_id, cast_fn in EXPOSED_PARAMS:
            if attr in params:
                setattr(self, attr, cast_fn(params[attr]))
        if "start_date" not in params:
            self.start_date = start_date_input

    def snapshot_params(self) -> dict:
        result = {"model_type": self.model_type, "ua_scaling_mode": self.ua_scaling_mode, "billing_period": self.billing_period}
        result.update({attr: getattr(self, attr) for attr, _, _ in EXPOSED_PARAMS})
        return result

    def calculate_daily_payer_arppu(self) -> float:
        return self.arppu

    def get_retention_rate(self, days_alive: int) -> float:
        if days_alive == 0:
            return 1.00
        d1_rate = self.day_1_retention / 100.0
        if days_alive == 1:
            return d1_rate
        retained_rate = d1_rate * (days_alive ** -self.decay_exponent)
        return max(retained_rate, d1_rate * 0.12)

    def calculate_lifetime(self, max_days: int = 365) -> float:
        return sum(self.get_retention_rate(d) for d in range(max_days))

    def calculate_ltv(self) -> float:
        lifetime = self.calculate_lifetime()
        daily_payer_spend = self.calculate_daily_payer_arppu()
        ad_arpu_per_dau = (self.video_ecpm * self.video_impressions) / 1000.0

        if self.model_type == MODEL_PREMIUM:
            return self.game_price * (1.0 - self.platform_fee / 100.0)

        if self.model_type == MODEL_REMOVE_ADS:
            iap_ltv = (self.ad_removal_pct / 100.0) * self.ad_removal_price * (1.0 - self.platform_fee / 100.0)
            ad_ltv = (1.0 - self.ad_removal_pct / 100.0) * ad_arpu_per_dau * lifetime * (1.0 - self.ad_mediation_tax)
            return iap_ltv + ad_ltv

        if self.model_type == MODEL_SUBSCRIPTION:
            lifetime_months = 100.0 / self.monthly_churn if self.monthly_churn > 0 else float("inf")
            monthly_revenue = self.subscription_price if self.billing_period == BILLING_MONTHLY else self.subscription_price / 12.0
            ltv_per_sub = monthly_revenue * lifetime_months * (1.0 - self.platform_fee / 100.0)
            return (self.payer_pct / 100.0) * ltv_per_sub

        iap_arpu = (self.payer_pct / 100.0) * daily_payer_spend
        net_iap = iap_arpu * (1.0 - self.platform_fee / 100.0)
        net_ads = ad_arpu_per_dau * (1.0 - self.ad_mediation_tax)
        return (net_iap + net_ads) * lifetime

    def _compute_blended_cpi(self, days: int = 365) -> float:
        """Install-weighted average effective CPI over the simulation period,
        accounting for CPI saturation as cumulative paid installs grow."""
        if self.daily_ua_spend <= 0 or self.cpi <= 0:
            return max(self.cpi, 0.01)
        cumulative_paid = 0.0
        total_cost = 0.0
        total_installs = 0.0
        for _ in range(days):
            effective_cpi = self.cpi * (1 + self.cpi_saturation * math.log(1 + cumulative_paid / 10000))
            installs = self.daily_ua_spend / effective_cpi if effective_cpi > 0 else 0
            total_cost += self.daily_ua_spend
            total_installs += installs
            cumulative_paid += installs
        if total_installs <= 0:
            return max(self.cpi, 0.01)
        return total_cost / total_installs

    def calculate_ltv_cpi_ratio(self) -> float:
        ltv = self.calculate_ltv()
        effective_cpi = max(self._compute_blended_cpi(), 0.01)
        return ltv / effective_cpi if effective_cpi > 0 else float("inf")

    def ltv_breakdown_lines(self) -> list[str]:
        """Model-specific LTV decomposition as Rich markup lines for display."""
        blended_cpi = self._compute_blended_cpi()
        ltv = self.calculate_ltv()
        lifetime = self.calculate_lifetime()
        lines: list[str] = []

        if self.model_type == MODEL_PREMIUM:
            lines.append(f"  Game price:           ${self.game_price:.2f}")
            lines.append(f"  Platform fee:         {self.platform_fee:.0f}%")
        elif self.model_type == MODEL_REMOVE_ADS:
            ad_arpu_per_dau = (self.video_ecpm * self.video_impressions) / 1000.0
            removal_ltv = (self.ad_removal_pct / 100.0) * self.ad_removal_price * (1.0 - self.platform_fee / 100.0)
            ad_ltv = (1.0 - self.ad_removal_pct / 100.0) * ad_arpu_per_dau * lifetime * (1.0 - self.ad_mediation_tax)
            lines.append(f"  Removal IAP:          ${removal_ltv:.2f} ({self.ad_removal_pct:.0f}% × ${self.ad_removal_price:.2f}, net)")
            lines.append(f"  Ad revenue:           ${ad_ltv:.2f} ({100 - self.ad_removal_pct:.0f}% view ads × {lifetime:.0f}d)")
        elif self.model_type == MODEL_SUBSCRIPTION:
            lifetime_months = 100.0 / self.monthly_churn if self.monthly_churn > 0 else float("inf")
            monthly_revenue = self.subscription_price if self.billing_period == BILLING_MONTHLY else self.subscription_price / 12.0
            net_monthly = monthly_revenue * (1.0 - self.platform_fee / 100.0)
            ltv_per_sub = net_monthly * lifetime_months
            lines.append(f"  Subscriber lifetime:  {lifetime_months:.1f} months ({self.monthly_churn:.0f}% churn)")
            lines.append(f"  Net revenue per sub:  ${ltv_per_sub:.2f} (${net_monthly:.2f}/mo after fees)")
            lines.append(f"  Conversion:           {self.payer_pct:.1f}% of installs subscribe")
            lines.append(f"  Effective per install: ${ltv_per_sub * (self.payer_pct / 100.0):.2f}")
        else:
            daily_payer_spend = self.calculate_daily_payer_arppu()
            ad_arpu_per_dau = (self.video_ecpm * self.video_impressions) / 1000.0
            iap_component = (self.payer_pct / 100.0) * daily_payer_spend * (1.0 - self.platform_fee / 100.0) * lifetime
            ad_component = ad_arpu_per_dau * (1.0 - self.ad_mediation_tax) * lifetime
            lines.append(f"  Player lifetime:      {lifetime:.0f} days ({self.day_1_retention:.0f}% D1, {self.decay_exponent:.2f} decay)")
            lines.append(f"  IAP per install:      ${iap_component:.2f} ({self.payer_pct:.0f}% × ${daily_payer_spend:.2f}/day)")
            lines.append(f"  Ad revenue per install: ${ad_component:.2f} (${ad_arpu_per_dau:.3f}/DAU/day)")

        lines.append(f"  [bold]LTV: ${ltv:.2f}[/]  ·  [bold]CPI: ${blended_cpi:.2f}[/]  ·  [bold]Margin: ${ltv - blended_cpi:+.2f}/install[/]")
        return lines

    def _compute_day_revenue(self, dau: float, total_new_installs: float, ad_arpu_per_dau: float, daily_payer_spend: float, active_subscribers: float = 0.0) -> float:
        if self.model_type == MODEL_PREMIUM:
            gross_rev = total_new_installs * self.game_price
            return gross_rev * (1.0 - self.platform_fee / 100.0)
        elif self.model_type == MODEL_REMOVE_ADS:
            ad_removers = total_new_installs * (self.ad_removal_pct / 100.0)
            iap_rev = ad_removers * self.ad_removal_price
            ad_viewing_dau = dau * (1.0 - self.ad_removal_pct / 100.0)
            gross_ads = ad_viewing_dau * ad_arpu_per_dau
            net_iap = iap_rev * (1.0 - self.platform_fee / 100.0)
            net_ads = gross_ads * (1.0 - self.ad_mediation_tax)
            return net_iap + net_ads
        elif self.model_type == MODEL_SUBSCRIPTION:
            billing_days = 30 if self.billing_period == BILLING_MONTHLY else 365
            daily_rate = self.subscription_price / billing_days
            return active_subscribers * daily_rate * (1.0 - self.platform_fee / 100.0)
        else:
            gross_iap = dau * (self.payer_pct / 100.0) * daily_payer_spend
            gross_ads = dau * ad_arpu_per_dau
            net_iap = gross_iap * (1.0 - self.platform_fee / 100.0)
            net_ads = gross_ads * (1.0 - self.ad_mediation_tax)
            return net_iap + net_ads

    def calculate_timeline(self):
        all_days = []
        cumulative_bank_balance = self.starting_capital
        cohort_history = {}
        accrued_revenue_history = {}
        cumulative_paid_installs = 0.0
        start_date = datetime.date.fromisoformat(self.start_date)

        daily_payer_spend = self.calculate_daily_payer_arppu()
        ad_arpu_per_dau = (self.video_ecpm * self.video_impressions) / 1000.0
        current_spend = self.daily_ua_spend

        active_subscribers = 0.0
        daily_churn = 1.0 - (1.0 - self.monthly_churn / 100.0) ** (1.0 / 30.0)

        for day in range(365):
            current_date = start_date + datetime.timedelta(days=day)

            effective_cpi = self.cpi * (1 + self.cpi_saturation * math.log(1 + cumulative_paid_installs / 10000))
            paid_installs = current_spend / effective_cpi if effective_cpi > 0 else 0
            cumulative_paid_installs += paid_installs
            base_installs = self.influencer_installs + paid_installs

            surviving_historical_users = 0.0
            for cohort_day, initial_installs in cohort_history.items():
                days_elapsed = day - cohort_day
                surviving_historical_users += initial_installs * self.get_retention_rate(days_elapsed)

            organic_installs = base_installs * self.organic_ratio
            first_wave = (base_installs + organic_installs) * self.virality_k_factor
            viral_installs = first_wave / (1 - self.virality_k_factor) if self.virality_k_factor < 1.0 else first_wave * 10
            total_new_installs = base_installs + organic_installs + viral_installs
            cohort_history[day] = total_new_installs

            dau = surviving_historical_users + total_new_installs

            new_subscribers = total_new_installs * (self.payer_pct / 100.0)
            active_subscribers = active_subscribers * (1.0 - daily_churn) + new_subscribers

            day_accrued_net_revenue = self._compute_day_revenue(dau, total_new_installs, ad_arpu_per_dau, daily_payer_spend, active_subscribers)
            accrued_revenue_history[day] = day_accrued_net_revenue

            day_settled_cash_inflow = 0.0
            payout_day_source = day - self.payout_delay_days
            if payout_day_source >= 0:
                day_settled_cash_inflow = accrued_revenue_history.get(payout_day_source, 0.0)

            scaling_server_expense = (dau / 1000.0) * self.server_cost_per_k_dau
            scaling_support_expense = (dau / 1000.0) * self.support_cost_per_k_dau
            total_ops_outflow = (
                self.fixed_overhead_daily +
                scaling_server_expense +
                scaling_support_expense +
                current_spend
            )

            net_daily_cash_flow = day_settled_cash_inflow - total_ops_outflow
            cumulative_bank_balance += net_daily_cash_flow

            all_days.append({
                "date": current_date,
                "dau": int(dau),
                "installs": int(total_new_installs),
                "active_subs": int(active_subscribers),
                "accrued_rev": day_accrued_net_revenue,
                "cash_inflow": day_settled_cash_inflow,
                "ops_cost": total_ops_outflow,
                "cash_flow": net_daily_cash_flow,
                "bank_balance": cumulative_bank_balance
            })

            if self.ua_scaling_mode == "auto" and day > 0 and day % 7 == 0:
                recent_days = all_days[-7:]
                avg_cash_in = sum(d["cash_inflow"] for d in recent_days) / 7.0
                avg_spend = sum(d.get("ua_spend", current_spend) for d in recent_days) / 7.0 if any("ua_spend" in d for d in recent_days) else current_spend

                if avg_spend > 0:
                    implied_ltv_per_install = avg_cash_in / (avg_spend / effective_cpi) if effective_cpi > 0 else 0
                    current_ratio = implied_ltv_per_install / effective_cpi if effective_cpi > 0 else 0

                    if current_ratio > self.target_roi * 1.5:
                        current_spend = min(current_spend * self.scale_speed * 1.3, self.max_daily_budget)
                    elif current_ratio > self.target_roi:
                        current_spend = min(current_spend * self.scale_speed, self.max_daily_budget)
                    elif current_ratio > self.target_roi * 0.8:
                        pass
                    else:
                        current_spend = max(current_spend / self.scale_speed, self.daily_ua_spend * 0.1)

            all_days[-1]["ua_spend"] = current_spend

        timeline = []
        for d in all_days[:90]:
            timeline.append({**d, "date": d["date"].strftime("%Y-%m-%d")})

        remaining = all_days[90:]
        if remaining:
            months: dict[str, list] = {}
            for d in remaining:
                key = d["date"].strftime("%Y-%m")
                months.setdefault(key, []).append(d)
            for key in sorted(months.keys()):
                rows = months[key]
                timeline.append({
                    "date": f"{key} (month)",
                    "dau": rows[-1]["dau"],
                    "installs": sum(r["installs"] for r in rows),
                    "active_subs": rows[-1]["active_subs"],
                    "accrued_rev": sum(r["accrued_rev"] for r in rows),
                    "cash_inflow": sum(r["cash_inflow"] for r in rows),
                    "ops_cost": sum(r["ops_cost"] for r in rows),
                    "cash_flow": sum(r["cash_flow"] for r in rows),
                    "bank_balance": rows[-1]["bank_balance"],
                })

        return timeline

    @staticmethod
    def summarize_timeline(timeline: list[dict], starting_capital: float = 0.0) -> dict:
        peak_dau = max(d["dau"] for d in timeline)
        total_installs = sum(d["installs"] for d in timeline)
        peak_subs = max(d["active_subs"] for d in timeline)
        total_accrued = sum(d["accrued_rev"] for d in timeline)
        final_bank = timeline[-1]["bank_balance"]
        break_even = next(
            (i for i, d in enumerate(timeline) if d["bank_balance"] >= starting_capital), None
        )
        return {
            "peak_dau": peak_dau,
            "total_installs": total_installs,
            "peak_subs": peak_subs,
            "total_accrued": total_accrued,
            "final_bank": final_bank,
            "break_even_day": break_even,
        }

    def get_final_bank(self) -> float:
        timeline = self.calculate_timeline()
        return timeline[-1]["bank_balance"]

    def get_ltv_cpi(self) -> float:
        return self.calculate_ltv_cpi_ratio()

    def solve_parameter(self, param_name: str, target_fn, target_val: float, low: float, high: float, max_iters: int = 10) -> float | None:
        orig = getattr(self, param_name)
        try:
            setattr(self, param_name, low)
            val_low = target_fn()

            setattr(self, param_name, high)
            val_high = target_fn()

            min_val = min(val_low, val_high)
            max_val = max(val_low, val_high)
            if not (min_val <= target_val <= max_val):
                return None

            increasing = val_high > val_low

            for _ in range(max_iters):
                mid = (low + high) / 2.0
                setattr(self, param_name, mid)
                val_mid = target_fn()

                if (val_mid > target_val if increasing else val_mid < target_val):
                    high = mid
                else:
                    low = mid
            return (low + high) / 2.0
        except Exception:
            return None
        finally:
            setattr(self, param_name, orig)

    def calculate_sensitivity(self, spend_levels: list[float] | None = None) -> list[dict]:
        if spend_levels is None:
            base = self.daily_ua_spend
            spend_levels = [max(1.0, base * m) for m in [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]]

        results = []
        orig_spend = self.daily_ua_spend
        orig_scaling = self.ua_scaling_mode
        try:
            self.ua_scaling_mode = "manual"
            for spend in spend_levels:
                self.daily_ua_spend = spend
                timeline = self.calculate_timeline()
                summary = self.summarize_timeline(timeline, self.starting_capital)
                ltv = self.calculate_ltv()
                ratio = self.calculate_ltv_cpi_ratio()
                results.append({
                    "spend": spend,
                    "peak_dau": summary["peak_dau"],
                    "total_installs": summary["total_installs"],
                    "peak_subs": summary["peak_subs"],
                    "total_accrued": summary["total_accrued"],
                    "final_bank": summary["final_bank"],
                    "ltv": ltv,
                    "ratio": ratio,
                    "break_even": summary["break_even_day"],
                })
        finally:
            self.daily_ua_spend = orig_spend
            self.ua_scaling_mode = orig_scaling
        return results


class BusinessModelTUI(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    #app-body {
        layout: horizontal;
        height: 1fr;
    }
    #sidebar {
        width: 42;
        background: $surface;
        border-right: solid $primary-darken-2;
        padding: 1;
        scrollbar-gutter: stable;
        overflow-y: auto;
    }
    #sidebar-fixed {
        height: auto;
        border-bottom: solid $primary-darken-1;
        margin-bottom: 0;
        padding-bottom: 1;
    }
    #params-scroll {
        height: 1fr;
        overflow-y: auto;
        padding-right: 1;
    }
    #main-content {
        width: 1fr;
        padding: 0 1;
    }
    .param-section {
        margin-top: 0;
        margin-bottom: 1;
        padding: 0;
        border: none;
    }
    .param-section.hidden {
        display: none;
    }
    .setting-group {
        background: $primary-darken-2;
        color: $warning;
        padding: 0 1;
        margin-top: 1;
        margin-bottom: 0;
        text-style: bold;
    }
    Label {
        margin-top: 1;
        color: $text-muted;
        text-style: dim;
    }
    .field-label {
        margin-top: 0;
        margin-bottom: 0;
        height: 1;
        color: $text-muted;
        text-style: dim;
    }
    Input {
        margin-bottom: 0;
        border: none;
        height: 1;
        width: 100%;
        background: $surface-darken-1;
        text-align: right;
        padding: 0 1;
    }
    Input:focus {
        background: $primary-darken-2;
    }
    Input.--invalid {
        border: tall $error;
    }
    DataTable {
        height: 1fr;
        border: none;
    }
    DataTable:focus {
        border: tall $accent;
    }
    #focus_indicator {
        color: $text;
        background: $primary-darken-3;
        padding: 0 1;
        height: 1;
        margin-bottom: 0;
        text-style: bold;
    }
    DataTable > .datatable--header {
        background: $primary-darken-2;
        color: $text;
        text-style: bold;
    }
    Select {
        width: 100%;
        margin-bottom: 0;
    }
    Select:focus > .select--current {
        border: tall $warning;
    }
    #scenario-bar {
        height: auto;
        margin-bottom: 1;
    }
    .btn-sm {
        height: 1;
        min-width: 10;
        margin-right: 1;
        border: none;
    }
    #kpi_summary {
        height: auto;
        margin-bottom: 0;
        padding: 0 1;
        background: $surface;
        width: 1fr;
    }
    #kpi_diagnosis {
        height: auto;
        margin-bottom: 0;
        padding: 0 1;
        background: $surface-darken-1;
        width: 1fr;
    }
    .solver-status {
        color: $text-muted;
        text-style: italic;
        height: 1;
        padding: 0 1;
        margin-bottom: 0;
    }
    #validation_status {
        color: $error;
        height: auto;
        margin-top: 0;
        margin-bottom: 1;
    }
    #solver_instructions {
        color: $text-muted;
        background: $surface;
        padding: 1;
        height: auto;
        margin-bottom: 1;
        text-style: italic;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Exit"), 
        ("ctrl+r", "refresh_solver", "Refresh"), 
        ("ctrl+t", "next_tab", "Next Tab"),
        ("ctrl+s", "toggle_panel", "Switch Panel"),
        ("ctrl+1", "apply_1", "Apply CPI"),
        ("ctrl+2", "apply_2", "Apply D1 Ret"),
        ("ctrl+3", "apply_3", "Apply Monetiz"),
        ("escape", "unfocus", "Revert")
    ]

    _panel_on_sidebar: bool = True
    _last_sidebar_focus: str | None = None
    _last_right_focus: str | None = None

    def action_toggle_panel(self) -> None:
        self._panel_on_sidebar = not self._panel_on_sidebar
        if self._panel_on_sidebar:
            if self._last_sidebar_focus:
                try:
                    self.query_one(f"#{self._last_sidebar_focus}").focus()
                    return
                except Exception:
                    pass
            self.query_one("#model_type_select", Select).focus()
        else:
            if self._last_right_focus:
                try:
                    self.query_one(f"#{self._last_right_focus}").focus()
                    return
                except Exception:
                    pass
            self.query_one("#timeline_table").focus()

    def action_unfocus(self) -> None:
        focused = self.focused
        if isinstance(focused, Input):
            original = self._focus_original_values.get(focused.id, focused.value)
            if focused.value != original:
                focused.value = original
                self._focus_original_values[focused.id] = original
                self.action_recalculate()
            else:
                self.set_focus(None)
        else:
            self.set_focus(None)

    def _is_sidebar_widget(self, widget) -> bool:
        """Check if a widget lives inside the sidebar."""
        try:
            self.query_one(f"#sidebar #{widget.id}")
            return True
        except Exception:
            return False

    def on_descendant_focus(self, event) -> None:
        widget = event.widget
        if isinstance(widget, Input):
            self._focus_original_values.setdefault(widget.id, widget.value)
        widget_id = getattr(widget, 'id', None)
        if widget_id:
            if self._is_sidebar_widget(widget):
                self._last_sidebar_focus = widget_id
            else:
                self._last_right_focus = widget_id
            self._update_focus_indicator(widget)

    def __init__(self):
        super().__init__()
        self.title = "Runway"
        self.sub_title = "12-Month Financial Runway Simulator"
        self.store = ScenarioStore()
        self.engine = RevenueLagEngine()
        self._loading_scenario = False
        self._focus_original_values: dict[str, str | None] = {}
        self._pending_delete = False
        self._solver_goal = "breakeven"
        self._timeline_activity_col_key = None
        self._sens_activity_col_key = None
        self._compare_activity_col_key = None

    def labeled_input(
        self, label_text: str, input_id: str, value, *, type: str | None = "number"
    ) -> ComposeResult:
        label_id = "lbl_" + input_id[len("in_"):]
        yield Label(label_text, id=label_id, classes="field-label")
        if type is None:
            yield Input(value=str(value), id=input_id, classes="field-input")
        else:
            yield Input(value=str(value), id=input_id, type=type, classes="field-input")

    def _scaling_inputs(self):
        yield Label("Scaling Mode:")
        yield Select(SCALING_OPTIONS, value=self.engine.ua_scaling_mode, id="in_scaling_mode")

    def _subscription_inputs(self):
        yield Label("Billing Period:")
        yield Select(BILLING_OPTIONS, value=self.engine.billing_period, id="in_billing_period")

    def section(self, title: str, *children, collapsed: bool = True, section_id: str | None = None):
        with Collapsible(title=title, collapsed=collapsed, classes="param-section", id=section_id):
            for child in children:
                yield from child

    def compose(self) -> ComposeResult:
        self.engine = RevenueLagEngine()

        scenario_options = [(n, n) for n in self.store.list_names()]
        first_scenario = scenario_options[0][0] if scenario_options else None

        yield Header()
        with Horizontal(id="app-body"):
            with Vertical(id="sidebar"):
                with Vertical(id="sidebar-fixed"):
                    yield Label("SCENARIO", classes="setting-group")
                    yield Label("Active Scenario:")
                    yield Select(scenario_options, value=first_scenario, id="scenario_select")
                    yield Label("New Scenario Name:")
                    yield Input(placeholder="Type name, then Save", id="in_scenario_name")
                    with Horizontal(id="scenario-bar"):
                        yield Button("Save", id="btn_save", variant="primary", classes="btn-sm")
                        yield Button("Delete", id="btn_delete", variant="error", classes="btn-sm")

                    yield Label("", id="validation_status", classes="hidden")

                    yield Label("BUSINESS MODEL", classes="setting-group")
                    yield Label("Revenue Model:")
                    yield Select(MODEL_OPTIONS, value=MODEL_F2P, id="model_type_select")

                with Vertical(id="params-scroll"):
                    yield from self.section(
                        "Launch & Capital",
                        self.labeled_input("Start Date (YYYY-MM-DD):", "in_start_date", self.engine.start_date, type=None),
                        self.labeled_input("Starting Capital ($):", "in_starting_capital", self.engine.starting_capital),
                        collapsed=False,
                    )
                    yield from self.section(
                        "UA Scaling",
                        self._scaling_inputs(),
                        self.labeled_input("Target LTV:CPI:", "in_target_roi", self.engine.target_roi),
                        self.labeled_input("Max Daily Budget ($):", "in_max_budget", self.engine.max_daily_budget),
                        self.labeled_input("Scale Speed:", "in_scale_speed", self.engine.scale_speed),
                        section_id="sec_scaling",
                    )
                    yield from self.section(
                        "Marketing Capital",
                        self.labeled_input("Daily UA Spend ($):", "in_ua_spend", self.engine.daily_ua_spend),
                        self.labeled_input("Cost Per Install ($):", "in_cpi", self.engine.cpi),
                        self.labeled_input("CPI Saturation:", "in_cpi_sat", self.engine.cpi_saturation),
                        self.labeled_input("Burst Installs/Day:", "in_influencer", self.engine.influencer_installs),
                        collapsed=False,
                    )
                    yield from self.section(
                        "Growth & Retention",
                        self.labeled_input("Organic Ratio:", "in_organic", self.engine.organic_ratio),
                        self.labeled_input("Viral K-Factor:", "in_kfactor", self.engine.virality_k_factor),
                        self.labeled_input("D1 Retention (%):", "in_d1_retention", self.engine.day_1_retention),
                        self.labeled_input("Retention Decay:", "in_decay", self.engine.decay_exponent),
                    )
                    yield from self.section(
                        "IAP Monetization",
                        self.labeled_input("Payer Conversion (%):", "in_payer_pct", self.engine.payer_pct),
                        self.labeled_input("ARPPU ($):", "in_arppu", self.engine.arppu),
                        section_id="sec_iap",
                    )
                    yield from self.section(
                        "Ad Revenue",
                        self.labeled_input("Video eCPM ($):", "in_video_ecpm", self.engine.video_ecpm),
                        self.labeled_input("Impressions/DAU/Day:", "in_video_impressions", self.engine.video_impressions),
                        section_id="sec_ads",
                    )
                    yield from self.section(
                        "Premium Pricing",
                        self.labeled_input("Game Price ($):", "in_game_price", self.engine.game_price),
                        section_id="sec_premium",
                    )
                    yield from self.section(
                        "Ad Removal IAP",
                        self.labeled_input("Removal Price ($):", "in_ad_removal_price", self.engine.ad_removal_price),
                        self.labeled_input("Removal Conversion (%):", "in_ad_removal_pct", self.engine.ad_removal_pct),
                        section_id="sec_remove_ads",
                    )
                    yield from self.section(
                        "Subscription Pricing",
                        self._subscription_inputs(),
                        self.labeled_input("Subscription Price ($):", "in_sub_price", self.engine.subscription_price),
                        self.labeled_input("Monthly Churn (%):", "in_monthly_churn", self.engine.monthly_churn),
                        self.labeled_input("Subscriber Conversion (%):", "in_sub_conversion", self.engine.payer_pct),
                        section_id="sec_subscription",
                    )
                    yield from self.section(
                        "Platform Fees",
                        self.labeled_input("Platform Fee (%):", "in_platform_fee", self.engine.platform_fee),
                        self.labeled_input("Payout Delay (Days):", "in_delay", self.engine.payout_delay_days, type="integer"),
                    )
                    yield from self.section(
                        "Live-Ops OpEx",
                        self.labeled_input("Fixed Daily Overhead ($):", "in_fixed_ops", self.engine.fixed_overhead_daily),
                        self.labeled_input("Server Cost per 1k DAU:", "in_server_k", self.engine.server_cost_per_k_dau),
                    )

            with Vertical(id="main-content"):
                yield Static("[dim]Focus: --[/]", id="focus_indicator")
                yield Static(id="kpi_summary")
                yield Static("", id="kpi_diagnosis")
                with TabbedContent():
                    with TabPane("12-Month Runway", id="tab_timeline"):
                        yield DataTable(id="timeline_table")
                    with TabPane("Compare Scenarios", id="tab_compare"):
                        yield DataTable(id="compare_table")
                    with TabPane("Spend Analysis", id="tab_sensitivity"):
                        yield Static("[dim]Projected outcomes at different daily UA spend levels. Press ctrl+r to refresh.[/]", id="sensitivity_instructions")
                        yield DataTable(id="sensitivity_table")
                    with TabPane("Target Solver", id="tab_solver"):
                        yield Label("Apply Goal:", classes="setting-group")
                        yield Select(
                            [("Breakeven (bank ≥ $0)", "breakeven"), ("LTV:CPI ≥ 3.0", "ltv_cpi")],
                            value="breakeven",
                            id="solver_goal_select",
                        )
                        yield Static("[bold]Parameter Targets[/]\n[dim]Shows what parameter values you need. Press ctrl+1, ctrl+2, or ctrl+3 to apply.[/]", id="solver_instructions")
                        yield Static("", id="solver_status", classes="solver-status")
                        yield Static("", id="solver_output")
        yield Footer()

    def _update_focus_indicator(self, widget) -> None:
        """Show current focus in focus indicator widget."""
        try:
            indicator = self.query_one("#focus_indicator", Static)
            widget_id = getattr(widget, 'id', None) or ''
            widget_type = type(widget).__name__
            friendly = {
                'timeline_table': 'Timeline Table',
                'compare_table': 'Compare Table',
                'solver_output': 'Solver Output (read-only)',
                'kpi_summary': 'KPI Summary (read-only)',
                'model_type_select': 'Model Type',
                'scenario_select': 'Active Scenario',
                'in_scenario_name': 'Scenario Name',
                'btn_save': 'Save Button',
                'btn_delete': 'Delete Button',
                'in_start_date': 'Start Date',
                'in_ua_spend': 'Daily UA Spend',
                'in_cpi': 'Cost Per Install',
                'in_cpi_sat': 'CPI Saturation',
                'in_influencer': 'Burst Installs/Day',
                'in_organic': 'Organic Ratio',
                'in_kfactor': 'Viral K-Factor',
                'in_d1_retention': 'D1 Retention',
                'in_decay': 'Retention Decay',
                'in_payer_pct': 'Payer Conversion',
                'in_arppu': 'ARPPU',
                'in_video_ecpm': 'Video eCPM',
                'in_video_impressions': 'Impressions/DAU/Day',
                'in_game_price': 'Game Price',
                'in_ad_removal_price': 'Removal Price',
                'in_ad_removal_pct': 'Removal Conversion',
                'in_sub_price': 'Subscription Price',
                'in_monthly_churn': 'Monthly Churn',
                'in_sub_conversion': 'Subscriber Conversion',
                'in_platform_fee': 'Platform Fee',
                'in_delay': 'Payout Delay',
                'in_fixed_ops': 'Fixed Daily Overhead',
                'in_server_k': 'Server Cost per 1k DAU',
            }.get(widget_id, widget_id or widget_type)
            side = "sidebar" if (self._last_sidebar_focus == widget_id) else "right panel"
            indicator.update(f"[dim]Focus: [b]{friendly}[/] ({side})[/]")
        except Exception:
            pass

    def on_mount(self) -> None:
        table = self.query_one("#timeline_table", DataTable)
        col_keys = table.add_columns(
            "Date", "DAU", "Accrued Rev",
            "Cash In", "Expenses",
            "Bank Balance"
        )
        self._timeline_activity_col_key = col_keys[1]
        table.cursor_type = "row"

        cmp = self.query_one("#compare_table", DataTable)
        cmp_keys = cmp.add_columns(
            "Scenario", "Model", "Peak DAU", "LTV", "LTV:CPI",
            "Break-even", "Year-End Bank"
        )
        self._compare_activity_col_key = cmp_keys[2]
        cmp.cursor_type = "row"

        sens = self.query_one("#sensitivity_table", DataTable)
        sens_keys = sens.add_columns(
            "Daily Spend", "Peak DAU", "Total Revenue",
            "LTV:CPI", "Break-even", "Year-End Bank"
        )
        self._sens_activity_col_key = sens_keys[1]
        sens.cursor_type = "row"

        if self.store.list_names():
            self._load_scenario(self.store.list_names()[0])

        self.action_recalculate()
        self._refresh_compare()

    def _update_activity_labels(self):
        """Relabel DAU/Installs/Subs columns based on current model type."""
        if self.engine.model_type == MODEL_PREMIUM:
            timeline_label = "Installs"
            summary_label = "Total Installs"
        elif self.engine.model_type == MODEL_SUBSCRIPTION:
            timeline_label = "Active Subs"
            summary_label = "Peak Subs"
        else:
            timeline_label = "DAU"
            summary_label = "Peak DAU"
        try:
            self.query_one("#timeline_table", DataTable).columns[
                self._timeline_activity_col_key
            ].label = Text(timeline_label)
            self.query_one("#sensitivity_table", DataTable).columns[
                self._sens_activity_col_key
            ].label = Text(summary_label)
            self.query_one("#compare_table", DataTable).columns[
                self._compare_activity_col_key
            ].label = Text(summary_label)
        except Exception:
            pass

    def _apply_model_visibility(self, model_type: str):
        show = {"sec_iap": False, "sec_ads": False, "sec_premium": False, "sec_remove_ads": False, "sec_subscription": False}

        if model_type == MODEL_F2P:
            show["sec_iap"] = True
            show["sec_ads"] = True
        elif model_type == MODEL_PREMIUM:
            show["sec_premium"] = True
        elif model_type == MODEL_REMOVE_ADS:
            show["sec_ads"] = True
            show["sec_remove_ads"] = True
        elif model_type == MODEL_SUBSCRIPTION:
            show["sec_subscription"] = True

        for section_id, visible in show.items():
            section = self.query_one(f"#{section_id}", Collapsible)
            section.set_class(not visible, "hidden")
            section.visible = visible
            for widget in section.walk_children():
                if isinstance(widget, Input):
                    widget.disabled = not visible

        self._update_activity_labels()

    def _load_scenario(self, name: str):
        params = self.store.get(name)
        if not params:
            return
        self._loading_scenario = True
        try:
            self.engine.apply_params(params)
            model_type = params.get("model_type", MODEL_F2P)
            self.query_one("#model_type_select", Select).value = model_type
            scaling_mode = params.get("ua_scaling_mode", "manual")
            self.query_one("#in_scaling_mode", Select).value = scaling_mode
            billing_period = params.get("billing_period", BILLING_MONTHLY)
            self.query_one("#in_billing_period", Select).value = billing_period
            self._apply_model_visibility(model_type)
            for attr, widget_id, cast_fn in EXPOSED_PARAMS:
                self.query_one(f"#{widget_id}", Input).value = str(getattr(self.engine, attr))
        finally:
            self._loading_scenario = False

    def _refresh_select(self, active_name: str | None = None):
        select = self.query_one("#scenario_select", Select)
        names = self.store.list_names()
        select.set_options([(n, n) for n in names])
        if active_name and active_name in names:
            select.value = active_name
        elif names:
            select.value = names[0]

    def _confirm_delete(self) -> None:
        """Show delete confirmation with Yes/No buttons."""
        self.query_one("#validation_status", Label).update(
            "[bold yellow]Delete this scenario? Press Delete again to confirm, or Escape to cancel.[/]"
        )
        self.query_one("#validation_status").set_class(False, "hidden")
        self._pending_delete = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            name = self.query_one("#in_scenario_name", Input).value.strip()
            if not name:
                current = self.query_one("#scenario_select", Select)
                name = str(current.value) if current.value else None
            if not name:
                return
            self.store.put(name, self.engine.snapshot_params())
            self._refresh_select(name)
            self._refresh_compare()

        elif event.button.id == "btn_delete":
            if getattr(self, "_pending_delete", False):
                self._pending_delete = False
                current = self.query_one("#scenario_select", Select)
                if current.value:
                    self.store.delete(str(current.value))
                    self._refresh_select()
                    names = self.store.list_names()
                    if names:
                        self._load_scenario(names[0])
                        self.action_recalculate()
                    self._refresh_compare()
                self.query_one("#validation_status", Label).update("")
                self.query_one("#validation_status").set_class(True, "hidden")
            else:
                self._confirm_delete()

    def action_recalculate(self) -> None:
        for attr, widget_id, cast_fn in EXPOSED_PARAMS:
            widget = self.query_one(f"#{widget_id}", Input)
            if widget.disabled or not widget.display:
                continue
            try:
                setattr(self.engine, attr, cast_fn(widget.value))
            except ValueError:
                self.query_one("#validation_status", Label).update(
                    f"[bold red]Invalid value for {widget_id}[/]"
                )
                self.query_one("#validation_status").set_class(False, "hidden")
                return

        try:
            datetime.date.fromisoformat(self.engine.start_date)
        except (ValueError, TypeError):
            self.query_one("#validation_status", Label).update(
                "[bold red]Invalid date format (use YYYY-MM-DD)[/]"
            )
            self.query_one("#validation_status").set_class(False, "hidden")
            return

        self.query_one("#validation_status", Label).update("")
        self.query_one("#validation_status").set_class(True, "hidden")

        timeline_data = self.engine.calculate_timeline()

        ltv = self.engine.calculate_ltv()
        ratio = self.engine.calculate_ltv_cpi_ratio()
        ratio_color = "green" if ratio >= 3.0 else ("yellow" if ratio >= 1.0 else "bold red")
        peak_dau = max(d["dau"] for d in timeline_data)
        total_installs = sum(d["installs"] for d in timeline_data)
        peak_subs = max(d["active_subs"] for d in timeline_data)
        final_bank = timeline_data[-1]["bank_balance"]
        bank_color = "green" if final_bank >= 0 else "bold red"

        model = self.engine.model_type
        if model == MODEL_PREMIUM:
            activity_label = "Total Installs"
            activity_val = total_installs
        elif model == MODEL_SUBSCRIPTION:
            activity_label = "Peak Subs"
            activity_val = peak_subs
        else:
            activity_label = "Peak DAU"
            activity_val = peak_dau

        self.query_one("#kpi_summary", Static).update(
            f" [dim]LTV[/] [bold white]${ltv:.2f}[/]  ·  "
            f"[dim]CPI[/] [bold white]${self.engine.cpi:.2f}[/]  ·  "
            f"[dim]LTV:CPI[/] [{ratio_color} bold]{ratio:.2f}[/]  ·  "
            f"[dim]{activity_label}[/] [bold white]{activity_val:,}[/]  ·  "
            f"[dim]Year-End[/] [{bank_color} bold]${final_bank:,.0f}[/]"
        )

        blended_cpi = self.engine._compute_blended_cpi()
        margin = ltv - blended_cpi
        if ratio < 1.0:
            diagnosis = (
                f" [bold red]⚠ Losing ${-margin:.2f}/install "
                f"— effective ${ltv:.2f} can't cover CPI ${blended_cpi:.2f}[/]"
            )
        elif ratio < 3.0:
            diagnosis = (
                f" [yellow]Profitable but thin — ${margin:.2f}/install "
                f"margin over CPI ${blended_cpi:.2f} (LTV {ratio:.1f}×)[/]"
            )
        else:
            diagnosis = f" [green]✓ Healthy — ${margin:.2f}/install margin (LTV {ratio:.1f}× CPI)[/]"
        self.query_one("#kpi_diagnosis", Static).update(diagnosis)

        table = self.query_one("#timeline_table", DataTable)
        table.clear()

        for day in timeline_data:
            bank_text = Text(f"${day['bank_balance']:.2f}")
            bank_text.stylize("green" if day["bank_balance"] >= 0 else "bold red")
            is_monthly = day["date"].endswith("(month)")
            date_text = Text(day["date"])
            if is_monthly:
                date_text.stylize("bold cyan")
            if model == MODEL_PREMIUM:
                activity_col = f"{day['installs']:,}"
            elif model == MODEL_SUBSCRIPTION:
                activity_col = f"{day['active_subs']:,}"
            else:
                activity_col = f"{day['dau']:,}"
            table.add_row(
                date_text,
                activity_col,
                f"${day['accrued_rev']:.2f}",
                f"${day['cash_inflow']:.2f}",
                f"${day['ops_cost']:.2f}",
                bank_text,
            )

        self._refresh_compare()


    def action_refresh_solver(self) -> None:
        """Refresh the active tab's computation."""
        try:
            tabs = self.query_one(TabbedContent)
            pane_id = tabs.active if isinstance(tabs.active, str) else None
        except Exception:
            pane_id = None

        if pane_id == "tab_sensitivity":
            self._refresh_sensitivity()
            return

        try:
            self.query_one("#solver_status", Static).update("[dim]Solving...[/]")
        except Exception:
            pass
        self._refresh_solver_table()
        try:
            self.query_one("#solver_status", Static).update("")
        except Exception:
            pass

    def action_next_tab(self) -> None:
        """Switch to the next tab."""
        tabs = self.query_one("TabbedContent")
        pane_ids = ["tab_timeline", "tab_compare", "tab_sensitivity", "tab_solver"]
        current = tabs.active
        if isinstance(current, str) and current in pane_ids:
            idx = pane_ids.index(current)
            tabs.active = pane_ids[(idx + 1) % len(pane_ids)]

    def _set_input_value(self, widget_id: str, raw_val: float | None):
        """Apply a solved parameter value to the sidebar input field."""
        if raw_val is None:
            self.query_one("#validation_status", Label).update("[red]Value infeasible for current model")
            self.query_one("#validation_status").set_class(False, "hidden")
            return
        try:
            widget = self.query_one(f"#{widget_id}", Input)
            widget.value = f"{raw_val}"
            self.action_recalculate()
            self._refresh_solver_tab_if_active()
        except Exception:
            pass

    def action_apply_1(self) -> None:
        """Apply CPI value from solver."""
        if not hasattr(self, '_solver_results') or not self._solver_results:
            return
        tabs = self.query_one(TabbedContent)
        if not isinstance(tabs.active, str) or tabs.active != "tab_solver":
            return
        self._set_input_value("in_cpi", self._solver_results.get("cpi"))

    def action_apply_2(self) -> None:
        """Apply D1 Retention value from solver."""
        if not hasattr(self, '_solver_results') or not self._solver_results:
            return
        tabs = self.query_one(TabbedContent)
        if not isinstance(tabs.active, str) or tabs.active != "tab_solver":
            return
        self._set_input_value("in_d1_retention", self._solver_results.get("d1"))

    def action_apply_3(self) -> None:
        """Apply monetization value from solver."""
        if not hasattr(self, '_solver_results') or not self._solver_results:
            return
        tabs = self.query_one(TabbedContent)
        if not isinstance(tabs.active, str) or tabs.active != "tab_solver":
            return
        r = self._solver_results
        self._set_input_value(r["mon_id"], r.get("mon"))

    def _refresh_solver_tab_if_active(self):
        """Refresh solver or sensitivity when tab is visible."""
        try:
            tabs = self.query_one(TabbedContent)
            pane_id = tabs.active if isinstance(tabs.active, str) else None
        except Exception:
            return
        if pane_id == "tab_solver":
            self._refresh_solver_table()
        elif pane_id == "tab_sensitivity":
            self._refresh_sensitivity()

    def _refresh_compare(self):
        cmp = self.query_one("#compare_table", DataTable)
        cmp.clear()
        self._add_compare_row(cmp, "(Current)", self.engine)
        current_snapshot = self.engine.snapshot_params()
        for name in self.store.list_names():
            params = self.store.get(name)
            if not params:
                continue
            if params == current_snapshot:
                continue
            tmp_engine = RevenueLagEngine()
            tmp_engine.apply_params(params)
            self._add_compare_row(cmp, name, tmp_engine)

    def _add_compare_row(self, cmp, name, engine):
        timeline = engine.calculate_timeline()
        summary = RevenueLagEngine.summarize_timeline(timeline, engine.starting_capital)
        be = str(summary["break_even_day"]) if summary["break_even_day"] is not None else "—"
        ltv = engine.calculate_ltv()
        ratio = engine.calculate_ltv_cpi_ratio()
        ratio_text = Text(f"{ratio:.2f}")
        ratio_text.stylize("green" if ratio >= 3.0 else ("yellow" if ratio >= 1.0 else "bold red"))
        bank_text = Text(f"${summary['final_bank']:,.2f}")
        bank_text.stylize("green" if summary["final_bank"] >= 0 else "bold red")
        model_label = {
            MODEL_F2P: "F2P", MODEL_PREMIUM: "Premium", MODEL_REMOVE_ADS: "RemAds", MODEL_SUBSCRIPTION: "Sub",
        }.get(engine.model_type, "F2P")
        if self.engine.model_type == MODEL_PREMIUM:
            activity = summary["total_installs"]
        elif self.engine.model_type == MODEL_SUBSCRIPTION:
            activity = summary["peak_subs"]
        else:
            activity = summary["peak_dau"]
        cmp.add_row(
            name,
            model_label,
            f"{activity:,}",
            f"${ltv:.2f}",
            ratio_text,
            be,
            bank_text,
        )

    def _refresh_solver_table(self):
        """Compute and display solver results as Rich markup in the Static widget."""
        output = self.query_one("#solver_output", Static)

        cpi_be = self.engine.solve_parameter("cpi", self.engine.get_final_bank, 0.0, 0.01, 20.0)
        cpi_ltv_val = self.engine.calculate_ltv()
        cpi_ltv = cpi_ltv_val / 3.0 if cpi_ltv_val > 0 else None

        d1_be = self.engine.solve_parameter("day_1_retention", self.engine.get_final_bank, 0.0, 1.0, 99.0)
        d1_ltv = self.engine.solve_parameter("day_1_retention", self.engine.get_ltv_cpi, 3.0, 1.0, 99.0)

        if self.engine.model_type == MODEL_PREMIUM:
            mon_label = "Game Price"
            mon_id = "in_game_price"
            mon_curr_raw = self.engine.game_price
            mon_curr_disp = f"${mon_curr_raw:.2f}"
            mon_be = self.engine.solve_parameter("game_price", self.engine.get_final_bank, 0.0, 0.49, 100.0)
            mon_ltv = self.engine.solve_parameter("game_price", self.engine.get_ltv_cpi, 3.0, 0.49, 100.0)
            mon_is_pct = False
            mon_is_currency = True
        elif self.engine.model_type == MODEL_REMOVE_ADS:
            mon_label = "Ad Removal Conv"
            mon_id = "in_ad_removal_pct"
            mon_curr_raw = self.engine.ad_removal_pct
            mon_curr_disp = f"{mon_curr_raw:.1f}%"
            mon_be = self.engine.solve_parameter("ad_removal_pct", self.engine.get_final_bank, 0.0, 0.0, 100.0)
            mon_ltv = self.engine.solve_parameter("ad_removal_pct", self.engine.get_ltv_cpi, 3.0, 0.0, 100.0)
            mon_is_pct = True
            mon_is_currency = False
        elif self.engine.model_type == MODEL_SUBSCRIPTION:
            mon_label = "Sub Price"
            mon_id = "in_sub_price"
            mon_curr_raw = self.engine.subscription_price
            mon_curr_disp = f"${mon_curr_raw:.2f}"
            mon_be = self.engine.solve_parameter("subscription_price", self.engine.get_final_bank, 0.0, 0.49, 100.0)
            mon_ltv = self.engine.solve_parameter("subscription_price", self.engine.get_ltv_cpi, 3.0, 0.49, 100.0)
            mon_is_pct = False
            mon_is_currency = True
        else:
            mon_label = "ARPPU"
            mon_id = "in_arppu"
            mon_curr_raw = self.engine.arppu
            mon_curr_disp = f"${mon_curr_raw:.2f}"
            mon_be = self.engine.solve_parameter("arppu", self.engine.get_final_bank, 0.0, 0.01, 50.0)
            mon_ltv = self.engine.solve_parameter("arppu", self.engine.get_ltv_cpi, 3.0, 0.01, 50.0)
            mon_is_pct = False
            mon_is_currency = True

        def fmt_target(val, is_pct, is_currency, current_metric, target):
            """Format solver result with status indicator."""
            if val is None:
                # Solver couldn't find a solution
                if current_metric >= target:
                    return "[dim yellow]already met ✓[/]"
                else:
                    return "[dim red]unachievable[/]"
            v = val
            return f"[bold green]${v:.2f}[/]" if is_currency else f"[bold green]{v:.1f}%[/]"

        # Get current metrics for status checking
        current_bank = self.engine.get_final_bank()
        current_ratio = self.engine.calculate_ltv_cpi_ratio()

        cpi_be_s = fmt_target(cpi_be, False, True, current_bank, 0.0)
        cpi_ltv_s = fmt_target(cpi_ltv, False, True, current_ratio, 3.0)
        d1_be_s = fmt_target(d1_be, False, False, current_bank, 0.0)
        d1_ltv_s = fmt_target(d1_ltv, False, False, current_ratio, 3.0)
        mon_be_s = fmt_target(mon_be, mon_is_pct, mon_is_currency, current_bank, 0.0)
        mon_ltv_s = fmt_target(mon_ltv, mon_is_pct, mon_is_currency, current_ratio, 3.0)

        breakdown = self.engine.ltv_breakdown_lines()

        if self._solver_goal == "breakeven":
            lines = [
                "",
                f"[bold cyan]Goal: Year-End Breakeven (bank ≥ $0 at 12 months)[/]",
                "",
                f"[bold]LTV Breakdown[/]",
                *breakdown,
                "",
                f"[bold]Parameter Targets[/]",
                f"  CPI must be ≤ {cpi_be_s}          (current: ${self.engine.cpi:.2f})",
                f"  D1 Retention must be ≥ {d1_be_s}  (current: {self.engine.day_1_retention:.1f}%)",
                f"  {mon_label} must be ≥ {mon_be_s}  (current: {mon_curr_disp})",
                "",
                f"[dim]Press [ctrl+1] CPI, [ctrl+2] D1 Ret, [ctrl+3] {mon_label} to apply. Press [ctrl+t] to switch tabs.[/]",
            ]
            self._solver_results = {
                "cpi": cpi_be,
                "d1": d1_be,
                "mon_id": mon_id,
                "mon": mon_be,
                "mon_is_pct": mon_is_pct,
            }
        else:
            lines = [
                "",
                f"[bold cyan]Goal: LTV:CPI ≥ 3.0[/]",
                "",
                f"[bold]LTV Breakdown[/]",
                *breakdown,
                "",
                f"[bold]Parameter Targets[/]",
                f"  CPI must be ≤ {cpi_ltv_s}          (current: ${self.engine.cpi:.2f})",
                f"  D1 Retention must be ≥ {d1_ltv_s}  (current: {self.engine.day_1_retention:.1f}%)",
                f"  {mon_label} must be ≥ {mon_ltv_s}  (current: {mon_curr_disp})",
                "",
                f"[dim]Press [ctrl+1] CPI, [ctrl+2] D1 Ret, [ctrl+3] {mon_label} to apply. Press [ctrl+t] to switch tabs.[/]",
            ]
            self._solver_results = {
                "cpi": cpi_ltv,
                "d1": d1_ltv,
                "mon_id": mon_id,
                "mon": mon_ltv,
                "mon_is_pct": mon_is_pct,
            }
        output.update("\n".join(lines))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "in_scenario_name":
            return
        if self._loading_scenario:
            return
        event.input.add_class("pending")
        self.action_recalculate()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.remove_class("pending")
        self._focus_original_values[event.input.id] = event.input.value
        self.action_recalculate()
        self._refresh_solver_tab_if_active()

    def on_blur(self, event: Input.Blur) -> None:
        event.input.remove_class("pending")
        self._focus_original_values[event.input.id] = event.input.value
        self.action_recalculate()
        self._refresh_solver_tab_if_active()

    def _refresh_sensitivity(self):
        """Compute and display spend sensitivity analysis."""
        table = self.query_one("#sensitivity_table", DataTable)
        table.clear()
        results = self.engine.calculate_sensitivity()
        for r in results:
            ratio_color = "green" if r["ratio"] >= 3.0 else ("yellow" if r["ratio"] >= 1.0 else "bold red")
            bank_text = Text(f"${r['final_bank']:,.0f}")
            bank_text.stylize("green" if r["final_bank"] >= 0 else "bold red")
            be = str(r["break_even"]) if r["break_even"] is not None else "—"
            ratio_text = Text(f"{r['ratio']:.2f}")
            ratio_text.stylize(ratio_color)
            is_current = abs(r["spend"] - self.engine.daily_ua_spend) < 0.01
            spend_label = f"${r['spend']:.2f}" + (" *" if is_current else "")
            if self.engine.model_type == MODEL_PREMIUM:
                activity = r["total_installs"]
            elif self.engine.model_type == MODEL_SUBSCRIPTION:
                activity = r["peak_subs"]
            else:
                activity = r["peak_dau"]
            table.add_row(
                spend_label,
                f"{activity:,}",
                f"${r['total_accrued']:,.0f}",
                ratio_text,
                be,
                bank_text,
            )

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "scenario_select" and event.value is not None:
            self._load_scenario(str(event.value))
            self.action_recalculate()
            self._refresh_solver_tab_if_active()
        elif event.select.id == "model_type_select" and event.value is not None:
            self.engine.model_type = str(event.value)
            self._apply_model_visibility(str(event.value))
            self.action_recalculate()
            self._refresh_solver_tab_if_active()
        elif event.select.id == "in_scaling_mode" and event.value is not None:
            self.engine.ua_scaling_mode = str(event.value)
            self.action_recalculate()
            self._refresh_solver_tab_if_active()
        elif event.select.id == "in_billing_period" and event.value is not None:
            self.engine.billing_period = str(event.value)
            self.action_recalculate()
            self._refresh_solver_tab_if_active()
        elif event.select.id == "solver_goal_select" and event.value is not None:
            self._solver_goal = str(event.value)
            self._refresh_solver_tab_if_active()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self._refresh_solver_tab_if_active()


if __name__ == "__main__":
    BusinessModelTUI().run()
