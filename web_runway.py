#!/usr/bin/env python3
"""Web Games 12-Month Financial Runway Simulator.

Models a web game published on portals (Web Portal, Playable Ads,
Social/Messaging, Custom Web). Revenue is RPM-based (revenue per 1000
plays) with portal revenue shares.
"""

import datetime
import json
import math
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Input, Label, TabbedContent, TabPane,
    DataTable, Select, Button, Static, Collapsible,
)
from rich.text import Text

WEB_SCENARIOS_FILE = Path("web_scenarios.json")

PORTALS = {
    "Web Portal": {
        "rev_share": 50.0, "rpm": 2.00, "iap": False,
        "organic_plays": 3000, "min_plays": 0,
    },
    "Playable Ads": {
        "rev_share": 60.0, "rpm": 1.20, "iap": False,
        "organic_plays": 6000, "min_plays": 0,
    },
    "Social/Messaging": {
        "rev_share": 70.0, "rpm": 1.50, "iap": True,
        "organic_plays": 2000, "min_plays": 0,
    },
    "Custom Web": {
        "rev_share": 0.0, "rpm": 1.00, "iap": True,
        "organic_plays": 0, "min_plays": 0,
    },
}

PORTAL_OPTIONS = [(n, n) for n in PORTALS]

EXPOSED_PARAMS = [
    ("starting_capital", "in_starting_capital", float),
    ("organic_plays_per_day", "in_organic_plays", float),
    ("external_ua_spend", "in_ext_ua_spend", float),
    ("external_cpi", "in_ext_cpi", float),
    ("cpi_saturation", "in_cpi_saturation", float),
    ("viral_k", "in_viral_k", float),
    ("day_1_retention", "in_d1_retention", float),
    ("decay_exponent", "in_decay", float),
    ("sessions_per_day", "in_sessions_day", float),
    ("impressions_per_session", "in_imp_session", float),
    ("ad_fill_rate", "in_ad_fill_rate", float),
    ("base_rpm", "in_rpm", float),
    ("rpm_growth_rate", "in_rpm_growth", float),
    ("min_plays_per_day", "in_min_plays", float),
    ("iap_payer_pct", "in_iap_payer", float),
    ("iap_avg_purchase", "in_iap_avg", float),
    ("portal_rev_share", "in_portal_share", float),
    ("payout_delay_days", "in_delay", int),
    ("fixed_overhead_daily", "in_fixed_ops", float),
    ("server_cost_per_k_dau", "in_server_k", float),
    ("cdn_cost_per_k_plays", "in_cdn_k", float),
    ("start_date", "in_start_date", str),
]

DEFAULT_SCENARIOS = {
    "Portal Ad-Only": {
        "portal": "Web Portal",
        "starting_capital": 5000.0,
        "portal_rev_share": 50.0,
        "organic_plays_per_day": 3000, "min_plays_per_day": 0,
        "external_ua_spend": 0.0, "external_cpi": 0.30, "cpi_saturation": 0.3,
        "viral_k": 0.02,
        "day_1_retention": 18.0, "decay_exponent": 0.55,
        "sessions_per_day": 1.3,
        "impressions_per_session": 2.5,
        "ad_fill_rate": 80.0,
        "base_rpm": 2.00, "rpm_growth_rate": 0.0,
        "iap_payer_pct": 0.0, "iap_avg_purchase": 0.0,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 200.0,
        "server_cost_per_k_dau": 0.50, "cdn_cost_per_k_plays": 0.10,
    },
    "Playable Ads Reach": {
        "portal": "Playable Ads",
        "starting_capital": 5000.0,
        "portal_rev_share": 60.0,
        "organic_plays_per_day": 6000, "min_plays_per_day": 0,
        "external_ua_spend": 0.0, "external_cpi": 0.30, "cpi_saturation": 0.3,
        "viral_k": 0.015,
        "day_1_retention": 15.0, "decay_exponent": 0.60,
        "sessions_per_day": 1.1,
        "impressions_per_session": 2.0,
        "ad_fill_rate": 80.0,
        "base_rpm": 1.20, "rpm_growth_rate": 0.0,
        "iap_payer_pct": 0.0, "iap_avg_purchase": 0.0,
        "payout_delay_days": 45,
        "fixed_overhead_daily": 200.0,
        "server_cost_per_k_dau": 0.50, "cdn_cost_per_k_plays": 0.10,
    },
    "Social IAP Hybrid": {
        "portal": "Social/Messaging",
        "starting_capital": 5000.0,
        "portal_rev_share": 70.0,
        "organic_plays_per_day": 2000, "min_plays_per_day": 0,
        "external_ua_spend": 5.0, "external_cpi": 0.40, "cpi_saturation": 0.3,
        "viral_k": 0.03,
        "day_1_retention": 20.0, "decay_exponent": 0.50,
        "sessions_per_day": 1.5,
        "impressions_per_session": 2.5,
        "ad_fill_rate": 80.0,
        "base_rpm": 1.50, "rpm_growth_rate": 0.0,
        "iap_payer_pct": 1.0, "iap_avg_purchase": 1.99,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 200.0,
        "server_cost_per_k_dau": 0.50, "cdn_cost_per_k_plays": 0.10,
    },
    "Custom Web Direct": {
        "portal": "Custom Web",
        "starting_capital": 5000.0,
        "portal_rev_share": 0.0,
        "organic_plays_per_day": 0, "min_plays_per_day": 0,
        "external_ua_spend": 20.0, "external_cpi": 0.50, "cpi_saturation": 0.3,
        "viral_k": 0.025,
        "day_1_retention": 17.0, "decay_exponent": 0.55,
        "sessions_per_day": 1.3,
        "impressions_per_session": 3.0,
        "ad_fill_rate": 80.0,
        "base_rpm": 1.00, "rpm_growth_rate": 0.0,
        "iap_payer_pct": 1.5, "iap_avg_purchase": 2.99,
        "payout_delay_days": 15,
        "fixed_overhead_daily": 250.0,
        "server_cost_per_k_dau": 0.50, "cdn_cost_per_k_plays": 0.10,
    },
}


class ScenarioStore:
    def __init__(self):
        self.scenarios: dict[str, dict] = {}
        self._load()

    def _load(self):
        if WEB_SCENARIOS_FILE.exists():
            try:
                self.scenarios = json.loads(WEB_SCENARIOS_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                self.scenarios = {}
        if not self.scenarios:
            self.scenarios = dict(DEFAULT_SCENARIOS)
            self.save()

    def save(self):
        WEB_SCENARIOS_FILE.write_text(json.dumps(self.scenarios, indent=2) + "\n")

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


class WebGameEngine:
    def __init__(self):
        self.portal = "Web Portal"
        self.portal_rev_share = 50.0
        self.base_rpm = 2.00
        self.rpm_growth_rate = 0.0
        self.min_plays_per_day = 0.0

        self.starting_capital = 5000.0
        self.organic_plays_per_day = 3000.0
        self.external_ua_spend = 0.0
        self.external_cpi = 0.30
        self.cpi_saturation = 0.3
        self.viral_k = 0.02

        self.day_1_retention = 18.0
        self.decay_exponent = 0.55
        self.sessions_per_day = 1.3
        self.impressions_per_session = 2.5
        self.ad_fill_rate = 80.0

        self.iap_payer_pct = 0.0
        self.iap_avg_purchase = 0.0

        self.fixed_overhead_daily = 200.0
        self.server_cost_per_k_dau = 0.50
        self.cdn_cost_per_k_plays = 0.10

        self.payout_delay_days = 30
        self.start_date = datetime.date.today().strftime("%Y-%m-%d")

    def apply_params(self, params: dict):
        if "portal" in params:
            self.portal = params["portal"]
        for attr, widget_id, cast_fn in EXPOSED_PARAMS:
            if attr in params:
                setattr(self, attr, cast_fn(params[attr]))
        if "start_date" not in params:
            self.start_date = datetime.date.today().strftime("%Y-%m-%d")

    def snapshot_params(self) -> dict:
        result = {"portal": self.portal}
        result.update({attr: getattr(self, attr) for attr, _, _ in EXPOSED_PARAMS})
        return result

    def _is_iap_supported(self) -> bool:
        return PORTALS.get(self.portal, {}).get("iap", False)

    def get_retention_rate(self, days_alive: int) -> float:
        if days_alive == 0:
            return 1.00
        d1_rate = self.day_1_retention / 100.0
        if days_alive == 1:
            return d1_rate
        retained_rate = d1_rate * (days_alive ** -self.decay_exponent)
        return max(retained_rate, d1_rate * 0.04)

    def calculate_lifetime(self, max_days: int = 365) -> float:
        return sum(self.get_retention_rate(d) for d in range(max_days))

    def calculate_ltv(self) -> float:
        total_retention = 0.0
        weighted_rpm = 0.0
        for d in range(365):
            ret = self.get_retention_rate(d)
            total_retention += ret
            current_rpm = max(self.base_rpm * (1.0 + self.rpm_growth_rate * math.log(1 + d)), 0.0)
            weighted_rpm += ret * current_rpm

        avg_rpm = weighted_rpm / total_retention if total_retention > 0 else self.base_rpm
        net_rpm_per_impression = (avg_rpm / 1000.0) * (1.0 - self.portal_rev_share / 100.0) * (self.ad_fill_rate / 100.0)
        ltv_rpm = total_retention * self.sessions_per_day * self.impressions_per_session * net_rpm_per_impression

        iap_ltv = 0.0
        if self._is_iap_supported() and self.iap_payer_pct > 0:
            iap_ltv = (self.iap_payer_pct / 100.0) * self.iap_avg_purchase * (1.0 - self.portal_rev_share / 100.0)

        return ltv_rpm + iap_ltv

    def _compute_blended_cpi(self, days: int = 365) -> float:
        """Install-weighted average effective CPI over the simulation period,
        accounting for CPI saturation as cumulative paid installs grow."""
        if self.external_ua_spend <= 0 or self.external_cpi <= 0:
            return max(self.external_cpi, 0.01)
        cumulative_paid = 0.0
        total_cost = 0.0
        total_installs = 0.0
        for _ in range(days):
            effective_cpi = self.external_cpi
            if self.cpi_saturation > 0:
                saturation_factor = 1.0 + self.cpi_saturation * math.log(1 + cumulative_paid / 10000)
                effective_cpi = self.external_cpi * saturation_factor
            installs = self.external_ua_spend / effective_cpi
            total_cost += self.external_ua_spend
            total_installs += installs
            cumulative_paid += installs
        if total_installs <= 0:
            return max(self.external_cpi, 0.01)
        return total_cost / total_installs

    def calculate_ltv_cpi_ratio(self) -> float:
        ltv = self.calculate_ltv()
        effective_cpi = max(self._compute_blended_cpi(), 0.01)
        return ltv / effective_cpi if effective_cpi > 0 else float("inf")

    def _compute_day_revenue(self, dau: float, plays: float, current_rpm: float, new_users: float = 0.0) -> float:
        total_impressions = plays * self.impressions_per_session * (self.ad_fill_rate / 100.0)
        gross_rpm = (total_impressions / 1000.0) * current_rpm
        net_rpm = gross_rpm * (1.0 - self.portal_rev_share / 100.0)

        # IAP is modeled as a one-time first purchase by a fraction of each
        # day's NEW users — consistent with calculate_ltv(), which treats IAP
        # as a single lifetime event rather than a recurring daily charge.
        iap_rev = 0.0
        if self._is_iap_supported() and self.iap_payer_pct > 0:
            iap_rev = new_users * (self.iap_payer_pct / 100.0) * self.iap_avg_purchase * (1.0 - self.portal_rev_share / 100.0)

        return net_rpm + iap_rev

    def calculate_timeline(self):
        all_days = []
        cumulative_bank_balance = self.starting_capital
        cohort_history: dict[int, float] = {}
        accrued_revenue_history: dict[int, float] = {}
        cumulative_plays = 0.0
        cumulative_paid_installs = 0.0
        start_date = datetime.date.fromisoformat(self.start_date)

        for day in range(365):
            current_date = start_date + datetime.timedelta(days=day)

            surviving_historical_users = 0.0
            for cohort_day, initial_players in cohort_history.items():
                days_elapsed = day - cohort_day
                surviving_historical_users += initial_players * self.get_retention_rate(days_elapsed)

            ext_players = 0.0
            effective_cpi = self.external_cpi
            if self.external_ua_spend > 0 and self.external_cpi > 0:
                if self.cpi_saturation > 0:
                    saturation_factor = 1.0 + self.cpi_saturation * math.log(1 + cumulative_paid_installs / 10000)
                    effective_cpi = self.external_cpi * saturation_factor
                ext_players = self.external_ua_spend / effective_cpi
                cumulative_paid_installs += ext_players

            traction = min(cumulative_plays / 500_000, 1.5)
            effective_organic = self.organic_plays_per_day * (1.0 + traction)
            effective_organic = max(effective_organic, self.min_plays_per_day)

            base_new = effective_organic + ext_players
            viral_installs = (
                base_new * self.viral_k / (1 - self.viral_k)
                if self.viral_k < 1.0
                else base_new * 10
            )
            total_new = base_new + viral_installs
            cohort_history[day] = total_new

            dau = surviving_historical_users + total_new
            plays = dau * self.sessions_per_day
            cumulative_plays += plays

            current_rpm = max(self.base_rpm * (1.0 + self.rpm_growth_rate * math.log(1 + day)), 0.0)

            day_accrued_net_revenue = self._compute_day_revenue(dau, plays, current_rpm, total_new)
            accrued_revenue_history[day] = day_accrued_net_revenue

            day_settled_cash_inflow = 0.0
            payout_day_source = day - self.payout_delay_days
            if payout_day_source >= 0:
                day_settled_cash_inflow = accrued_revenue_history.get(payout_day_source, 0.0)

            scaling_server_expense = (dau / 1000.0) * self.server_cost_per_k_dau
            scaling_cdn_expense = (plays / 1000.0) * self.cdn_cost_per_k_plays
            total_ops_outflow = (
                self.fixed_overhead_daily
                + scaling_server_expense
                + scaling_cdn_expense
                + self.external_ua_spend
            )

            net_daily_cash_flow = day_settled_cash_inflow - total_ops_outflow
            cumulative_bank_balance += net_daily_cash_flow

            all_days.append({
                "date": current_date,
                "dau": int(dau),
                "plays": int(plays),
                "rpm": current_rpm,
                "accrued_rev": day_accrued_net_revenue,
                "cash_inflow": day_settled_cash_inflow,
                "ops_cost": total_ops_outflow,
                "cash_flow": net_daily_cash_flow,
                "bank_balance": cumulative_bank_balance,
            })

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
                    "plays": sum(r["plays"] for r in rows),
                    "rpm": rows[-1]["rpm"],
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
        total_accrued = sum(d["accrued_rev"] for d in timeline)
        total_plays = sum(d["plays"] for d in timeline)
        final_bank = timeline[-1]["bank_balance"]
        break_even = next(
            (i for i, d in enumerate(timeline) if d["bank_balance"] >= starting_capital), None
        )
        return {
            "peak_dau": peak_dau,
            "total_accrued": total_accrued,
            "total_plays": total_plays,
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

    def calculate_sensitivity(self, rpm_levels: list[float] | None = None) -> list[dict]:
        if rpm_levels is None:
            base = self.base_rpm
            rpm_levels = [max(0.50, base * m) for m in [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]]

        results = []
        orig_rpm = self.base_rpm
        try:
            for rpm in rpm_levels:
                self.base_rpm = rpm
                timeline = self.calculate_timeline()
                summary = self.summarize_timeline(timeline, self.starting_capital)
                ltv = self.calculate_ltv()
                results.append({
                    "rpm": rpm,
                    "peak_dau": summary["peak_dau"],
                    "total_accrued": summary["total_accrued"],
                    "final_bank": summary["final_bank"],
                    "ltv": ltv,
                    "break_even": summary["break_even_day"],
                    "total_plays": summary["total_plays"],
                })
        finally:
            self.base_rpm = orig_rpm
        return results


class WebGameTUI(App):
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
        ("ctrl+1", "apply_1", "Apply RPM"),
        ("ctrl+2", "apply_2", "Apply D1 Ret"),
        ("ctrl+3", "apply_3", "Apply Sessions"),
        ("escape", "unfocus", "Revert"),
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
            self.query_one("#portal_select", Select).focus()
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
        try:
            self.query_one(f"#sidebar #{widget.id}")
            return True
        except Exception:
            return False

    def on_descendant_focus(self, event) -> None:
        widget = event.widget
        if isinstance(widget, Input):
            self._focus_original_values.setdefault(widget.id, widget.value)
        widget_id = getattr(widget, "id", None)
        if widget_id:
            if self._is_sidebar_widget(widget):
                self._last_sidebar_focus = widget_id
            else:
                self._last_right_focus = widget_id
            self._update_focus_indicator(widget)

    def __init__(self):
        super().__init__()
        self.title = "Web Runway"
        self.sub_title = "12-Month Web Game Financial Runway Simulator"
        self.store = ScenarioStore()
        self.engine = WebGameEngine()
        self._loading_scenario = False
        self._focus_original_values: dict[str, str | None] = {}
        self._pending_delete = False
        self._solver_goal = "breakeven"

    def labeled_input(
        self, label_text: str, input_id: str, value, *, type: str | None = "number"
    ) -> ComposeResult:
        label_id = "lbl_" + input_id[len("in_"):]
        yield Label(label_text, id=label_id, classes="field-label")
        if type is None:
            yield Input(value=str(value), id=input_id, classes="field-input")
        else:
            yield Input(value=str(value), id=input_id, type=type, classes="field-input")

    def section(self, title: str, *children, collapsed: bool = True, section_id: str | None = None):
        with Collapsible(title=title, collapsed=collapsed, classes="param-section", id=section_id):
            for child in children:
                yield from child

    def compose(self) -> ComposeResult:
        self.engine = WebGameEngine()

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

                    yield Label("PORTAL", classes="setting-group")
                    yield Label("Publish Portal:")
                    yield Select(PORTAL_OPTIONS, value="Web Portal", id="portal_select")

                with Vertical(id="params-scroll"):
                    yield from self.section(
                        "Launch & Capital",
                        self.labeled_input("Start Date (YYYY-MM-DD):", "in_start_date", self.engine.start_date, type=None),
                        self.labeled_input("Starting Capital ($):", "in_starting_capital", self.engine.starting_capital),
                        collapsed=False,
                    )
                    yield from self.section(
                        "Traffic & Acquisition",
                        self.labeled_input("Organic Plays/Day:", "in_organic_plays", self.engine.organic_plays_per_day),
                        self.labeled_input("Min Guaranteed Plays:", "in_min_plays", self.engine.min_plays_per_day),
                        self.labeled_input("External UA Spend ($):", "in_ext_ua_spend", self.engine.external_ua_spend),
                        self.labeled_input("External CPI ($):", "in_ext_cpi", self.engine.external_cpi),
                        self.labeled_input("CPI Saturation:", "in_cpi_saturation", self.engine.cpi_saturation),
                        self.labeled_input("Viral K-Factor:", "in_viral_k", self.engine.viral_k),
                        collapsed=False,
                    )
                    yield from self.section(
                        "Engagement & Retention",
                        self.labeled_input("D1 Retention (%):", "in_d1_retention", self.engine.day_1_retention),
                        self.labeled_input("Retention Decay:", "in_decay", self.engine.decay_exponent),
                        self.labeled_input("Sessions per Day:", "in_sessions_day", self.engine.sessions_per_day),
                        self.labeled_input("Ad Impressions/Session:", "in_imp_session", self.engine.impressions_per_session),
                        self.labeled_input("Ad Fill Rate (%):", "in_ad_fill_rate", self.engine.ad_fill_rate),
                        collapsed=False,
                    )
                    yield from self.section(
                        "Ad Monetization (RPM)",
                        self.labeled_input("Base RPM ($):", "in_rpm", self.engine.base_rpm),
                        self.labeled_input("RPM Growth Rate:", "in_rpm_growth", self.engine.rpm_growth_rate),
                        self.labeled_input("Portal Rev Share (%):", "in_portal_share", self.engine.portal_rev_share),
                        collapsed=False,
                    )
                    yield from self.section(
                        "IAP Monetization",
                        self.labeled_input("Payer Conversion (%):", "in_iap_payer", self.engine.iap_payer_pct),
                        self.labeled_input("Avg Purchase ($):", "in_iap_avg", self.engine.iap_avg_purchase),
                        section_id="sec_iap",
                    )
                    yield from self.section(
                        "Costs & Payout",
                        self.labeled_input("Fixed Daily Overhead ($):", "in_fixed_ops", self.engine.fixed_overhead_daily),
                        self.labeled_input("Server Cost per 1k DAU:", "in_server_k", self.engine.server_cost_per_k_dau),
                        self.labeled_input("CDN Cost per 1k Plays:", "in_cdn_k", self.engine.cdn_cost_per_k_plays),
                        self.labeled_input("Payout Delay (Days):", "in_delay", self.engine.payout_delay_days, type="integer"),
                    )

            with Vertical(id="main-content"):
                yield Static("[dim]Focus: --[/]", id="focus_indicator")
                yield Static(id="kpi_summary")
                with TabbedContent():
                    with TabPane("12-Month Runway", id="tab_timeline"):
                        yield DataTable(id="timeline_table")
                    with TabPane("Compare Scenarios", id="tab_compare"):
                        yield DataTable(id="compare_table")
                    with TabPane("Portal Comparison", id="tab_portal"):
                        yield Static(
                            "[dim]Same game parameters applied to each portal. Press ctrl+r to refresh.[/]",
                            id="portal_instructions",
                        )
                        yield DataTable(id="portal_table")
                    with TabPane("Target Solver", id="tab_solver"):
                        yield Label("Apply Goal:", classes="setting-group")
                        yield Select(
                            [("Breakeven (bank >= $0)", "breakeven"), ("LTV:CPI >= 3.0", "ltv_cpi")],
                            value="breakeven",
                            id="solver_goal_select",
                        )
                        yield Static(
                            "[bold]Parameter Targets[/]\n[dim]Shows what parameter values you need. "
                            "Press ctrl+1, ctrl+2, or ctrl+3 to apply.[/]",
                            id="solver_instructions",
                        )
                        yield Static("", id="solver_status", classes="solver-status")
                        yield Static("", id="solver_output")
        yield Footer()

    def _update_focus_indicator(self, widget) -> None:
        try:
            indicator = self.query_one("#focus_indicator", Static)
            widget_id = getattr(widget, "id", None) or ""
            widget_type = type(widget).__name__
            friendly = {
                "timeline_table": "Timeline Table",
                "compare_table": "Compare Table",
                "portal_table": "Portal Comparison",
                "solver_output": "Solver Output (read-only)",
                "kpi_summary": "KPI Summary (read-only)",
                "portal_select": "Portal",
                "scenario_select": "Active Scenario",
                "in_scenario_name": "Scenario Name",
                "btn_save": "Save Button",
                "btn_delete": "Delete Button",
                "in_start_date": "Start Date",
                "in_organic_plays": "Organic Plays/Day",
                "in_min_plays": "Min Guaranteed Plays",
                "in_ext_ua_spend": "External UA Spend",
                "in_ext_cpi": "External CPI",
                "in_viral_k": "Viral K-Factor",
                "in_d1_retention": "D1 Retention",
                "in_decay": "Retention Decay",
                "in_sessions_day": "Sessions/Day",
                "in_imp_session": "Impressions/Session",
                "in_rpm": "Base RPM",
                "in_rpm_growth": "RPM Growth Rate",
                "in_portal_share": "Portal Rev Share",
                "in_iap_payer": "IAP Payer %",
                "in_iap_avg": "IAP Avg Purchase",
                "in_delay": "Payout Delay",
                "in_fixed_ops": "Fixed Overhead",
                "in_server_k": "Server Cost/1k DAU",
                "in_cdn_k": "CDN Cost/1k Plays",
            }.get(widget_id, widget_id or widget_type)
            side = "sidebar" if (self._last_sidebar_focus == widget_id) else "right panel"
            indicator.update(f"[dim]Focus: [b]{friendly}[/] ({side})[/]")
        except Exception:
            pass

    def on_mount(self) -> None:
        table = self.query_one("#timeline_table", DataTable)
        table.add_columns(
            "Date", "DAU", "Plays", "RPM",
            "Accrued Rev", "Cash In", "Expenses",
            "Bank Balance",
        )
        table.cursor_type = "row"

        cmp = self.query_one("#compare_table", DataTable)
        cmp.add_columns(
            "Scenario", "Portal", "Peak DAU",
            "LTV", "Break-even", "Year-End Bank",
        )
        cmp.cursor_type = "row"

        portal_tbl = self.query_one("#portal_table", DataTable)
        portal_tbl.add_columns(
            "Portal", "Rev Share", "RPM",
            "Peak DAU", "Total Rev", "LTV",
            "Break-even", "Year-End Bank",
        )
        portal_tbl.cursor_type = "row"

        if self.store.list_names():
            self._load_scenario(self.store.list_names()[0])

        self.action_recalculate()
        self._refresh_compare()

    def _apply_portal_iap_visibility(self):
        iap_supported = self.engine._is_iap_supported()
        section = self.query_one("#sec_iap", Collapsible)
        section.set_class(not iap_supported, "hidden")
        section.visible = iap_supported
        for widget in section.walk_children():
            if isinstance(widget, Input):
                widget.disabled = not iap_supported

    def _load_scenario(self, name: str):
        params = self.store.get(name)
        if not params:
            return
        self._loading_scenario = True
        try:
            self.engine.apply_params(params)
            portal = params.get("portal", "Web Portal")
            self.query_one("#portal_select", Select).value = portal
            self._apply_portal_iap_visibility()
            for attr, widget_id, cast_fn in EXPOSED_PARAMS:
                self.query_one(f"#{widget_id}", Input).value = str(getattr(self.engine, attr))
        finally:
            # Clear synchronously. Re-entrancy from the queued portal
            # Select.Changed is handled idempotently in on_select_changed
            # (it no-ops when the value already matches engine.portal), so
            # we don't need a deferred timer to keep the guard alive.
            # NOTE: the previous set_timer(0, ...) approach silently crashed
            # on Python 3.14 (ZeroDivisionError in Textual's timer), which
            # left _loading_scenario stuck True and broke ALL input edits.
            self._loading_scenario = False
        self.action_recalculate()

    def _refresh_select(self, active_name: str | None = None):
        select = self.query_one("#scenario_select", Select)
        names = self.store.list_names()
        select.set_options([(n, n) for n in names])
        if active_name and active_name in names:
            select.value = active_name
        elif names:
            select.value = names[0]

    def _confirm_delete(self) -> None:
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
        current_rpm = self.engine.base_rpm
        net_rpm = current_rpm * (1.0 - self.engine.portal_rev_share / 100.0)
        peak_dau = max(d["dau"] for d in timeline_data)
        final_bank = timeline_data[-1]["bank_balance"]
        bank_color = "green" if final_bank >= 0 else "bold red"

        self.query_one("#kpi_summary", Static).update(
            f" [dim]LTV[/] [bold white]${ltv:.2f}[/]  ·  "
            f"[dim]Net RPM[/] [bold white]${net_rpm:.2f}[/]  ·  "
            f"[dim]Peak DAU[/] [bold white]{peak_dau:,}[/]  ·  "
            f"[dim]Year-End[/] [{bank_color} bold]${final_bank:,.0f}[/]"
        )

        table = self.query_one("#timeline_table", DataTable)
        table.clear()

        for day in timeline_data:
            bank_text = Text(f"${day['bank_balance']:.2f}")
            bank_text.stylize("green" if day["bank_balance"] >= 0 else "bold red")
            is_monthly = day["date"].endswith("(month)")
            date_text = Text(day["date"])
            if is_monthly:
                date_text.stylize("bold cyan")
            table.add_row(
                date_text,
                f"{day['dau']:,}",
                f"{day['plays']:,}",
                f"${day['rpm']:.2f}",
                f"${day['accrued_rev']:.2f}",
                f"${day['cash_inflow']:.2f}",
                f"${day['ops_cost']:.2f}",
                bank_text,
            )

        self._refresh_compare()

    def action_refresh_solver(self) -> None:
        try:
            tabs = self.query_one(TabbedContent)
            pane_id = tabs.active if isinstance(tabs.active, str) else None
        except Exception:
            pane_id = None

        if pane_id == "tab_portal":
            self._refresh_portal_comparison()
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
        tabs = self.query_one("TabbedContent")
        pane_ids = ["tab_timeline", "tab_compare", "tab_portal", "tab_solver"]
        current = tabs.active
        if isinstance(current, str) and current in pane_ids:
            idx = pane_ids.index(current)
            tabs.active = pane_ids[(idx + 1) % len(pane_ids)]

    def _set_input_value(self, widget_id: str, raw_val: float | None):
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
        if not hasattr(self, "_solver_results") or not self._solver_results:
            return
        tabs = self.query_one(TabbedContent)
        if not isinstance(tabs.active, str) or tabs.active != "tab_solver":
            return
        self._set_input_value("in_rpm", self._solver_results.get("rpm"))

    def action_apply_2(self) -> None:
        if not hasattr(self, "_solver_results") or not self._solver_results:
            return
        tabs = self.query_one(TabbedContent)
        if not isinstance(tabs.active, str) or tabs.active != "tab_solver":
            return
        self._set_input_value("in_d1_retention", self._solver_results.get("d1"))

    def action_apply_3(self) -> None:
        if not hasattr(self, "_solver_results") or not self._solver_results:
            return
        tabs = self.query_one(TabbedContent)
        if not isinstance(tabs.active, str) or tabs.active != "tab_solver":
            return
        self._set_input_value("in_sessions_day", self._solver_results.get("sessions"))

    def _refresh_solver_tab_if_active(self):
        try:
            tabs = self.query_one(TabbedContent)
            pane_id = tabs.active if isinstance(tabs.active, str) else None
        except Exception:
            return
        if pane_id == "tab_solver":
            self._refresh_solver_table()
        elif pane_id == "tab_portal":
            self._refresh_portal_comparison()

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
            tmp_engine = WebGameEngine()
            tmp_engine.apply_params(params)
            self._add_compare_row(cmp, name, tmp_engine)

    def _add_compare_row(self, cmp, name, engine):
        timeline = engine.calculate_timeline()
        summary = WebGameEngine.summarize_timeline(timeline, engine.starting_capital)
        be = str(summary["break_even_day"]) if summary["break_even_day"] is not None else "—"
        ltv = engine.calculate_ltv()
        bank_text = Text(f"${summary['final_bank']:,.2f}")
        bank_text.stylize("green" if summary["final_bank"] >= 0 else "bold red")
        cmp.add_row(
            name,
            engine.portal,
            f"{summary['peak_dau']:,}",
            f"${ltv:.2f}",
            be,
            bank_text,
        )

    def _refresh_portal_comparison(self):
        table = self.query_one("#portal_table", DataTable)
        table.clear()

        current_snapshot = self.engine.snapshot_params()

        for portal_name, defaults in PORTALS.items():
            tmp = WebGameEngine()
            tmp.apply_params(current_snapshot)
            tmp.portal = portal_name
            tmp.portal_rev_share = defaults["rev_share"]
            tmp.base_rpm = defaults["rpm"]
            tmp.organic_plays_per_day = defaults["organic_plays"]
            tmp.min_plays_per_day = defaults["min_plays"]

            tl = tmp.calculate_timeline()
            summary = WebGameEngine.summarize_timeline(tl, tmp.starting_capital)
            ltv = tmp.calculate_ltv()

            be = str(summary["break_even_day"]) if summary["break_even_day"] is not None else "—"
            bank_text = Text(f"${summary['final_bank']:,.0f}")
            bank_text.stylize("green" if summary["final_bank"] >= 0 else "bold red")
            is_current = portal_name == self.engine.portal
            portal_label = portal_name + (" *" if is_current else "")

            table.add_row(
                portal_label,
                f"{defaults['rev_share']*100:.0f}%",
                f"${defaults['rpm']:.2f}",
                f"{summary['peak_dau']:,}",
                f"${summary['total_accrued']:,.0f}",
                f"${ltv:.2f}",
                be,
                bank_text,
            )

    def _refresh_solver_table(self):
        output = self.query_one("#solver_output", Static)

        rpm_be = self.engine.solve_parameter("base_rpm", self.engine.get_final_bank, 0.0, 0.10, 30.0)
        rpm_ltv = self.engine.solve_parameter("base_rpm", self.engine.get_ltv_cpi, 3.0, 0.10, 30.0)

        d1_be = self.engine.solve_parameter("day_1_retention", self.engine.get_final_bank, 0.0, 1.0, 99.0)
        d1_ltv = self.engine.solve_parameter("day_1_retention", self.engine.get_ltv_cpi, 3.0, 1.0, 99.0)

        sess_be = self.engine.solve_parameter("sessions_per_day", self.engine.get_final_bank, 0.0, 0.1, 15.0)
        sess_ltv = self.engine.solve_parameter("sessions_per_day", self.engine.get_ltv_cpi, 3.0, 0.1, 15.0)

        current_bank = self.engine.get_final_bank()
        current_ratio = self.engine.calculate_ltv_cpi_ratio()

        def fmt_target_rpm(val, current_val, target):
            if val is None:
                return "[dim yellow]already met ✓[/]" if current_val >= target else "[dim red]unachievable[/]"
            return f"[bold green]${val:.2f}[/]"

        def fmt_target_pct(val, current_val, target):
            if val is None:
                return "[dim yellow]already met ✓[/]" if current_val >= target else "[dim red]unachievable[/]"
            return f"[bold green]{val:.1f}%[/]"

        def fmt_target_num(val, current_val, target):
            if val is None:
                return "[dim yellow]already met ✓[/]" if current_val >= target else "[dim red]unachievable[/]"
            return f"[bold green]{val:.2f}[/]"

        if self._solver_goal == "breakeven":
            lines = [
                "",
                "[bold cyan]Goal: Year-End Breakeven (bank >= $0 at 12 months)[/]",
                "",
                f"  RPM must be >= {fmt_target_rpm(rpm_be, current_bank, 0.0)}      (current: ${self.engine.base_rpm:.2f})",
                f"  D1 Retention must be >= {fmt_target_pct(d1_be, current_bank, 0.0)}  (current: {self.engine.day_1_retention:.1f}%)",
                f"  Sessions/Day must be >= {fmt_target_num(sess_be, current_bank, 0.0)}  (current: {self.engine.sessions_per_day:.2f})",
                "",
                "[dim]Press [ctrl+1] RPM, [ctrl+2] D1 Ret, [ctrl+3] Sessions to apply. Press [ctrl+t] to switch tabs.[/]",
            ]
            self._solver_results = {
                "rpm": rpm_be,
                "d1": d1_be,
                "sessions": sess_be,
            }
        else:
            lines = [
                "",
                "[bold cyan]Goal: LTV:CPI >= 3.0[/]",
                "",
                f"  RPM must be >= {fmt_target_rpm(rpm_ltv, current_ratio, 3.0)}      (current: ${self.engine.base_rpm:.2f})",
                f"  D1 Retention must be >= {fmt_target_pct(d1_ltv, current_ratio, 3.0)}  (current: {self.engine.day_1_retention:.1f}%)",
                f"  Sessions/Day must be >= {fmt_target_num(sess_ltv, current_ratio, 3.0)}  (current: {self.engine.sessions_per_day:.2f})",
                "",
                "[dim]Press [ctrl+1] RPM, [ctrl+2] D1 Ret, [ctrl+3] Sessions to apply. Press [ctrl+t] to switch tabs.[/]",
            ]
            self._solver_results = {
                "rpm": rpm_ltv,
                "d1": d1_ltv,
                "sessions": sess_ltv,
            }

        sensitivity = self.engine.calculate_sensitivity()
        lines.append("")
        lines.append("[bold]RPM Sensitivity[/]")
        lines.append(f"  {'RPM':>8}  {'Total Rev':>12}  {'Year-End':>12}  {'Break-even':>10}")
        for r in sensitivity:
            be_str = str(r["break_even"]) if r["break_even"] is not None else "—"
            is_cur = abs(r["rpm"] - self.engine.base_rpm) < 0.01
            marker = "*" if is_cur else " "
            lines.append(
                f"  {r['rpm']:>7.2f}{marker}  "
                f"${r['total_accrued']:>10,.0f}  "
                f"${r['final_bank']:>10,.0f}  "
                f"{be_str:>10}"
            )

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

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "scenario_select" and event.value is not None:
            self._load_scenario(str(event.value))
            self.action_recalculate()
            self._refresh_solver_tab_if_active()
        elif event.select.id == "portal_select" and event.value is not None:
            # Idempotent guard: ignore re-entrant/echoed Changed events that
            # don't actually change the engine's portal (e.g. fired by our own
            # programmatic .value assignment during scenario load). This makes
            # the handler safe to clear _loading_scenario synchronously.
            if event.value == self.engine.portal:
                return
            if self._loading_scenario:
                return
            self._loading_scenario = True
            try:
                self.engine.portal = str(event.value)
                defaults = PORTALS.get(str(event.value), {})
                self.engine.portal_rev_share = defaults.get("rev_share", 50.0)
                self.engine.base_rpm = defaults.get("rpm", 2.00)
                self.engine.organic_plays_per_day = float(defaults.get("organic_plays", 3000))
                self.engine.min_plays_per_day = float(defaults.get("min_plays", 0))
                self.query_one("#in_portal_share", Input).value = str(self.engine.portal_rev_share)
                self.query_one("#in_rpm", Input).value = str(self.engine.base_rpm)
                self.query_one("#in_organic_plays", Input).value = str(self.engine.organic_plays_per_day)
                self.query_one("#in_min_plays", Input).value = str(self.engine.min_plays_per_day)
                self._apply_portal_iap_visibility()
            finally:
                self._loading_scenario = False
            self.action_recalculate()
            self._refresh_solver_tab_if_active()
        elif event.select.id == "solver_goal_select" and event.value is not None:
            self._solver_goal = str(event.value)
            self._refresh_solver_tab_if_active()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self._refresh_solver_tab_if_active()


if __name__ == "__main__":
    WebGameTUI().run()
