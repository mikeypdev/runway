#!/usr/bin/env python3
"""PC Games 12-Month Financial Runway Simulator.

Models a PC game published on Steam and/or itch.io. Revenue is event-driven:
launch wishlist conversions, decaying organic sales, periodic sale-event
spikes, and optional DLC releases. Platform fees, refund rates, and
marketing spend are modeled.
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

PC_SCENARIOS_FILE = Path("pc_scenarios.json")

PLATFORMS = {
    "Steam": {
        "platform_fee": 30.0, "payout_delay": 30, "itch_share": 0.0,
    },
    "itch.io": {
        "platform_fee": 10.0, "payout_delay": 15, "itch_share": 0.0,
    },
    "Both": {
        "platform_fee": 27.0, "payout_delay": 30, "itch_share": 15.0,
    },
}

PLATFORM_OPTIONS = [(n, n) for n in PLATFORMS]

EXPOSED_PARAMS = [
    ("game_price", "in_game_price", float),
    ("vat_rate", "in_vat", float),
    ("regional_pricing_pct", "in_regional", float),
    ("itch_share_pct", "in_itch_share", float),
    ("pre_launch_wishlists", "in_wishlists", float),
    ("launch_conversion_rate", "in_launch_conv", float),
    ("launch_spike_duration", "in_launch_duration", int),
    ("launch_spike_multiplier", "in_launch_mult", float),
    ("base_daily_sales", "in_base_sales", float),
    ("sales_decay_exponent", "in_sales_decay", float),
    ("sale_event_frequency", "in_sale_freq", int),
    ("sale_event_duration", "in_sale_duration", int),
    ("sale_event_multiplier", "in_sale_mult", float),
    ("sale_discount_pct", "in_sale_discount", float),
    ("refund_rate", "in_refund_rate", float),
    ("daily_marketing_spend", "in_marketing", float),
    ("cost_per_sale", "in_cps", float),
    ("dlc_price", "in_dlc_price", float),
    ("dlc_count", "in_dlc_count", int),
    ("dlc_release_interval", "in_dlc_interval", int),
    ("dlc_attach_rate", "in_dlc_attach", float),
    ("platform_fee_pct", "in_platform_fee", float),
    ("fixed_overhead_daily", "in_fixed_ops", float),
    ("server_cost_per_k_players", "in_server_k", float),
    ("payout_delay_days", "in_delay", int),
    ("start_date", "in_start_date", str),
    ("starting_capital", "in_starting_capital", float),
]

DEFAULT_SCENARIOS = {
    "Steam Indie $14.99": {
        "platform": "Steam",
        "starting_capital": 5000.0,
        "game_price": 14.99, "platform_fee_pct": 30.0, "refund_rate": 12.0,
        "vat_rate": 13.0, "regional_pricing_pct": 85.0, "itch_share_pct": 0.0,
        "pre_launch_wishlists": 15000, "launch_conversion_rate": 20.0,
        "launch_spike_duration": 14, "launch_spike_multiplier": 3.0,
        "base_daily_sales": 25.0, "sales_decay_exponent": 0.45,
        "sale_event_frequency": 90, "sale_event_duration": 7,
        "sale_event_multiplier": 4.0, "sale_discount_pct": 35.0,
        "daily_marketing_spend": 20.0, "cost_per_sale": 3.00,
        "dlc_price": 0.0, "dlc_count": 0, "dlc_release_interval": 120, "dlc_attach_rate": 0.0,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 30.0, "server_cost_per_k_players": 0.05,
    },
    "itch.io Solo Dev $9.99": {
        "platform": "itch.io",
        "starting_capital": 2000.0,
        "game_price": 9.99, "platform_fee_pct": 10.0, "refund_rate": 5.0,
        "vat_rate": 13.0, "regional_pricing_pct": 85.0, "itch_share_pct": 0.0,
        "pre_launch_wishlists": 3000, "launch_conversion_rate": 15.0,
        "launch_spike_duration": 7, "launch_spike_multiplier": 2.5,
        "base_daily_sales": 8.0, "sales_decay_exponent": 0.50,
        "sale_event_frequency": 0, "sale_event_duration": 0,
        "sale_event_multiplier": 1.0, "sale_discount_pct": 0.0,
        "daily_marketing_spend": 5.0, "cost_per_sale": 2.00,
        "dlc_price": 0.0, "dlc_count": 0, "dlc_release_interval": 120, "dlc_attach_rate": 0.0,
        "payout_delay_days": 15,
        "fixed_overhead_daily": 20.0, "server_cost_per_k_players": 0.05,
    },
    "Steam Premium + DLC": {
        "platform": "Steam",
        "starting_capital": 10000.0,
        "game_price": 19.99, "platform_fee_pct": 30.0, "refund_rate": 10.0,
        "vat_rate": 13.0, "regional_pricing_pct": 85.0, "itch_share_pct": 0.0,
        "pre_launch_wishlists": 20000, "launch_conversion_rate": 22.0,
        "launch_spike_duration": 14, "launch_spike_multiplier": 3.0,
        "base_daily_sales": 30.0, "sales_decay_exponent": 0.40,
        "sale_event_frequency": 90, "sale_event_duration": 7,
        "sale_event_multiplier": 4.0, "sale_discount_pct": 30.0,
        "daily_marketing_spend": 30.0, "cost_per_sale": 3.50,
        "dlc_price": 7.99, "dlc_count": 2, "dlc_release_interval": 120, "dlc_attach_rate": 15.0,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 40.0, "server_cost_per_k_players": 0.05,
    },
    "Dual Channel": {
        "platform": "Both",
        "starting_capital": 5000.0,
        "game_price": 14.99, "platform_fee_pct": 27.0, "refund_rate": 12.0,
        "vat_rate": 13.0, "regional_pricing_pct": 85.0, "itch_share_pct": 15.0,
        "pre_launch_wishlists": 15000, "launch_conversion_rate": 20.0,
        "launch_spike_duration": 14, "launch_spike_multiplier": 3.0,
        "base_daily_sales": 25.0, "sales_decay_exponent": 0.45,
        "sale_event_frequency": 90, "sale_event_duration": 7,
        "sale_event_multiplier": 4.0, "sale_discount_pct": 35.0,
        "daily_marketing_spend": 20.0, "cost_per_sale": 3.00,
        "dlc_price": 0.0, "dlc_count": 0, "dlc_release_interval": 120, "dlc_attach_rate": 0.0,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 30.0, "server_cost_per_k_players": 0.05,
    },
}


class ScenarioStore:
    def __init__(self):
        self.scenarios: dict[str, dict] = {}
        self._load()

    def _load(self):
        if PC_SCENARIOS_FILE.exists():
            try:
                self.scenarios = json.loads(PC_SCENARIOS_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                self.scenarios = {}
        if not self.scenarios:
            self.scenarios = dict(DEFAULT_SCENARIOS)
            self.save()

    def save(self):
        PC_SCENARIOS_FILE.write_text(json.dumps(self.scenarios, indent=2) + "\n")

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


class PCGameEngine:
    def __init__(self):
        self.platform = "Steam"
        self.game_price = 14.99
        self.platform_fee_pct = 30.0
        self.refund_rate = 12.0
        self.vat_rate = 13.0
        self.regional_pricing_pct = 85.0
        self.itch_share_pct = 0.0

        self.pre_launch_wishlists = 15000.0
        self.launch_conversion_rate = 20.0
        self.launch_spike_duration = 14
        self.launch_spike_multiplier = 3.0

        self.base_daily_sales = 25.0
        self.sales_decay_exponent = 0.45

        self.sale_event_frequency = 90
        self.sale_event_duration = 7
        self.sale_event_multiplier = 4.0
        self.sale_discount_pct = 35.0

        self.daily_marketing_spend = 20.0
        self.cost_per_sale = 3.00

        self.dlc_price = 0.0
        self.dlc_count = 0
        self.dlc_release_interval = 120
        self.dlc_attach_rate = 0.0

        self.fixed_overhead_daily = 30.0
        self.server_cost_per_k_players = 0.05

        self.payout_delay_days = 30
        self.start_date = datetime.date.today().strftime("%Y-%m-%d")
        self.starting_capital = 5000.0
        self._cached_blended_cpi: float | None = None
        self._cached_all_user_cpi: float | None = None
        self._cached_realized_ltv: float | None = None

    def _clear_caches(self):
        self._cached_blended_cpi = None
        self._cached_all_user_cpi = None
        self._cached_realized_ltv = None

    def apply_params(self, params: dict):
        if "platform" in params:
            self.platform = params["platform"]
        for attr, widget_id, cast_fn in EXPOSED_PARAMS:
            if attr in params:
                setattr(self, attr, cast_fn(params[attr]))
        if "start_date" not in params:
            self.start_date = datetime.date.today().strftime("%Y-%m-%d")

    def snapshot_params(self) -> dict:
        result = {"platform": self.platform}
        result.update({attr: getattr(self, attr) for attr, _, _ in EXPOSED_PARAMS})
        return result

    def _daily_organic_units(self, day: int) -> float:
        """Organic (non-marketing) base game units for a given day."""
        if self.launch_spike_duration > 0 and day < self.launch_spike_duration:
            launch_units = (
                self.pre_launch_wishlists * self.launch_conversion_rate / 100.0
                / self.launch_spike_duration
            )
            decay_units = self.base_daily_sales * max(day + 1, 1) ** (-self.sales_decay_exponent)
            organic = launch_units + decay_units * self.launch_spike_multiplier
        else:
            organic = self.base_daily_sales * max(day + 1, 1) ** (-self.sales_decay_exponent)
            organic = max(organic, self.base_daily_sales * 0.10)

        if (self.sale_event_frequency > 0 and self.sale_event_duration > 0
                and day >= self.launch_spike_duration):
            if day % self.sale_event_frequency < self.sale_event_duration:
                organic *= self.sale_event_multiplier

        return max(organic, 0.0)

    def _is_on_sale(self, day: int) -> bool:
        return (
            self.sale_event_frequency > 0
            and self.sale_event_duration > 0
            and day >= self.launch_spike_duration
            and day % self.sale_event_frequency < self.sale_event_duration
        )

    def _net_revenue_factor(self) -> float:
        """Combined multiplier from list price to actual net revenue per unit.

        Deduction order matches Steam's actual reporting:
        regional pricing → VAT (inclusive) → refunds → platform fee.
        """
        return (
            (self.regional_pricing_pct / 100.0)
            / (1.0 + self.vat_rate / 100.0)
            * (1.0 - self.refund_rate / 100.0)
            * (1.0 - self.platform_fee_pct / 100.0)
        )

    def calculate_ltv(self) -> float:
        """Analytical net revenue per base game unit sold, including DLC."""
        net_factor = self._net_revenue_factor()
        base_ltv = self.game_price * net_factor
        dlc_ltv = 0.0
        if self.dlc_count > 0 and self.dlc_price > 0 and self.dlc_attach_rate > 0:
            dlc_ltv = self.dlc_count * self.dlc_price * (self.dlc_attach_rate / 100.0) * net_factor
        return base_ltv + dlc_ltv

    def _compute_blended_cpi(self, days: int = 365) -> float:
        """Marketing cost per marketing-driven sale (no saturation in PC model)."""
        if self._cached_blended_cpi is not None:
            return self._cached_blended_cpi
        return max(self.cost_per_sale, 0.01)

    def _compute_all_user_cpi(self, days: int = 365) -> float:
        """Marketing cost spread across ALL sales (organic + marketing-driven)."""
        if self._cached_all_user_cpi is not None:
            return self._cached_all_user_cpi
        if self.daily_marketing_spend <= 0:
            return 0.0
        total_marketing = self.daily_marketing_spend * days
        total_units = 0.0
        for day in range(days):
            organic = self._daily_organic_units(day)
            paid = self.daily_marketing_spend / max(self.cost_per_sale, 0.01)
            total_units += organic + paid
        if total_units <= 0:
            return 0.0
        return total_marketing / total_units

    def calculate_ltv_cpi_ratio(self) -> float:
        ltv = self.calculate_ltv()
        effective_cpi = self._compute_effective_cpi_for_diagnosis()
        return ltv / effective_cpi if effective_cpi > 0 else float("inf")

    def _compute_effective_cpi_for_diagnosis(self) -> float:
        """Blended cost per sale across all users when marketing is active;
        falls back to cost_per_sale otherwise."""
        if self.daily_marketing_spend > 0:
            all_user_cpi = self._compute_all_user_cpi()
            if all_user_cpi > 0:
                return all_user_cpi
        return max(self.cost_per_sale, 0.01)

    def ltv_breakdown_lines(self) -> list[str]:
        """Per-unit revenue decomposition as Rich markup lines for display."""
        effective_cpi = self._compute_effective_cpi_for_diagnosis()
        ltv = self.calculate_ltv()
        net_factor = self._net_revenue_factor()
        after_regional = self.game_price * (self.regional_pricing_pct / 100.0)
        after_vat = after_regional / (1.0 + self.vat_rate / 100.0)
        after_refunds = after_vat * (1.0 - self.refund_rate / 100.0)
        after_platform = after_refunds * (1.0 - self.platform_fee_pct / 100.0)

        lines: list[str] = []
        lines.append(f"  Game price:           ${self.game_price:.2f}")
        lines.append(f"  Regional pricing:     {self.regional_pricing_pct:.0f}% of list -> ${after_regional:.2f}")
        lines.append(f"  VAT/sales tax:        {self.vat_rate:.0f}% -> ${after_vat:.2f}")
        lines.append(f"  Refund rate:          {self.refund_rate:.0f}% -> ${after_refunds:.2f}")
        lines.append(f"  Platform fee:         {self.platform_fee_pct:.0f}% -> ${after_platform:.2f}")
        lines.append(f"  Net/unit:             ${after_platform:.2f} ({net_factor*100:.0f}% of list)")

        if self.dlc_count > 0 and self.dlc_price > 0 and self.dlc_attach_rate > 0:
            dlc_net = self.dlc_count * self.dlc_price * (self.dlc_attach_rate / 100.0) * net_factor
            lines.append(f"  DLC ({self.dlc_count} × ${self.dlc_price:.2f}):")
            lines.append(f"    Attach rate:        {self.dlc_attach_rate:.0f}%")
            lines.append(f"    Net DLC/unit:       ${dlc_net:.2f}")

        timeline = self.calculate_timeline()
        avg_units = sum(d["units"] for d in timeline[:30]) / 30 if timeline else 0
        avg_rev = sum(d["accrued_rev"] for d in timeline[:30]) / 30 if timeline else 0
        avg_cost = sum(d["ops_cost"] for d in timeline[:30]) / 30 if timeline else 0
        lines.append(f"  Avg units/day (mo 1): {avg_units:,.0f}")
        lines.append(f"  Daily revenue:        ${avg_rev:.2f}")
        if self.daily_marketing_spend > 0:
            lines.append(f"  Marketing:            ${self.daily_marketing_spend:.2f}/day (${self.cost_per_sale:.2f}/sale)")
        lines.append(f"  Fixed overhead:       ${self.fixed_overhead_daily:.2f}/day")
        lines.append(f"  [bold]Daily margin: ${avg_rev - avg_cost:+.2f}/day (rev ${avg_rev:.0f} - costs ${avg_cost:.0f})[/]")
        lines.append(f"  [bold]LTV/unit: ${ltv:.2f}  ·  CPS: ${effective_cpi:.2f}  ·  Margin: ${ltv - effective_cpi:+.2f}/unit[/]")
        return lines

    def _compute_day_revenue(self, base_units: float, dlc_units: float, effective_price: float) -> float:
        net_factor = self._net_revenue_factor()
        base_rev = base_units * effective_price * net_factor
        dlc_rev = dlc_units * self.dlc_price * net_factor
        return base_rev + dlc_rev

    def calculate_timeline(self):
        self._clear_caches()
        all_days = []
        cumulative_bank_balance = self.starting_capital
        accrued_revenue_history: dict[int, float] = {}
        cumulative_owners = 0.0
        total_marketing_cost = 0.0
        total_paid_units_acc = 0.0
        total_all_units_acc = 0.0
        total_revenue_acc = 0.0
        dlc_releases: list[tuple[int, float, float]] = []
        start_date = datetime.date.fromisoformat(self.start_date)

        for day in range(365):
            current_date = start_date + datetime.timedelta(days=day)

            organic_units = self._daily_organic_units(day)
            paid_units = (
                self.daily_marketing_spend / max(self.cost_per_sale, 0.01)
                if self.daily_marketing_spend > 0 else 0.0
            )
            base_units = organic_units + paid_units
            if self.itch_share_pct > 0:
                base_units *= (1.0 + self.itch_share_pct / 100.0)
            total_marketing_cost += self.daily_marketing_spend
            total_paid_units_acc += paid_units
            cumulative_owners += base_units
            total_all_units_acc += base_units

            next_dlc_day = (len(dlc_releases) + 1) * self.dlc_release_interval
            if (len(dlc_releases) < self.dlc_count
                    and self.dlc_release_interval > 0
                    and day == next_dlc_day):
                remaining_days = 365 - day
                decay_sum = sum(
                    (n + 1) ** (-self.sales_decay_exponent) for n in range(remaining_days)
                )
                intended_total = cumulative_owners * (self.dlc_attach_rate / 100.0)
                dlc_day1 = intended_total / decay_sum if decay_sum > 0 else 0.0
                dlc_releases.append((day, cumulative_owners, dlc_day1))

            dlc_units = 0.0
            for rel_day, _owners, d1 in dlc_releases:
                dlc_age = day - rel_day
                if dlc_age == 0:
                    dlc_units += d1
                else:
                    dlc_units += d1 * (dlc_age + 1) ** (-self.sales_decay_exponent)
            dlc_units = max(dlc_units, 0.0)

            effective_price = self.game_price
            if self._is_on_sale(day):
                effective_price = self.game_price * (1.0 - self.sale_discount_pct / 100.0)

            day_accrued_net_revenue = self._compute_day_revenue(base_units, dlc_units, effective_price)
            accrued_revenue_history[day] = day_accrued_net_revenue
            total_revenue_acc += day_accrued_net_revenue

            day_settled_cash_inflow = 0.0
            payout_day_source = day - self.payout_delay_days
            if payout_day_source >= 0:
                day_settled_cash_inflow = accrued_revenue_history.get(payout_day_source, 0.0)

            scaling_server = (base_units / 1000.0) * self.server_cost_per_k_players
            total_ops_outflow = (
                self.fixed_overhead_daily
                + self.daily_marketing_spend
                + scaling_server
            )

            net_daily_cash_flow = day_settled_cash_inflow - total_ops_outflow
            cumulative_bank_balance += net_daily_cash_flow

            all_days.append({
                "date": current_date,
                "units": int(base_units),
                "dlc_units": int(dlc_units),
                "cumulative_owners": int(cumulative_owners),
                "accrued_rev": day_accrued_net_revenue,
                "cash_inflow": day_settled_cash_inflow,
                "ops_cost": total_ops_outflow,
                "cash_flow": net_daily_cash_flow,
                "bank_balance": cumulative_bank_balance,
            })

        if total_paid_units_acc > 0:
            self._cached_blended_cpi = total_marketing_cost / total_paid_units_acc
        if total_all_units_acc > 0 and total_marketing_cost > 0:
            self._cached_all_user_cpi = total_marketing_cost / total_all_units_acc
        if total_all_units_acc > 0:
            self._cached_realized_ltv = total_revenue_acc / total_all_units_acc

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
                    "units": sum(r["units"] for r in rows),
                    "dlc_units": sum(r["dlc_units"] for r in rows),
                    "cumulative_owners": rows[-1]["cumulative_owners"],
                    "accrued_rev": sum(r["accrued_rev"] for r in rows),
                    "cash_inflow": sum(r["cash_inflow"] for r in rows),
                    "ops_cost": sum(r["ops_cost"] for r in rows),
                    "cash_flow": sum(r["cash_flow"] for r in rows),
                    "bank_balance": rows[-1]["bank_balance"],
                })

        return timeline

    @staticmethod
    def summarize_timeline(timeline: list[dict], starting_capital: float = 0.0) -> dict:
        total_units = sum(d["units"] for d in timeline)
        total_dlc_units = sum(d["dlc_units"] for d in timeline)
        peak_daily_units = max(d["units"] for d in timeline)
        total_accrued = sum(d["accrued_rev"] for d in timeline)
        final_bank = timeline[-1]["bank_balance"]
        break_even = None
        for i, d in enumerate(timeline):
            if d["bank_balance"] >= starting_capital:
                break_even = i if i < 90 else 90 + (i - 90) * 30
                break
        return {
            "total_units": total_units,
            "total_dlc_units": total_dlc_units,
            "peak_daily_units": peak_daily_units,
            "total_accrued": total_accrued,
            "final_bank": final_bank,
            "break_even_day": break_even,
        }

    def get_final_bank(self) -> float:
        timeline = self.calculate_timeline()
        return timeline[-1]["bank_balance"]

    def get_ltv_cpi(self) -> float:
        return self.calculate_ltv_cpi_ratio()

    def get_realized_ltv(self) -> float:
        if self._cached_realized_ltv is not None:
            return self._cached_realized_ltv
        self.calculate_timeline()
        return self._cached_realized_ltv if self._cached_realized_ltv is not None else self.calculate_ltv()

    def solve_parameter(self, param_name: str, target_fn, target_val: float, low: float, high: float, max_iters: int = 10) -> float | None:
        orig = getattr(self, param_name)
        try:
            setattr(self, param_name, low)
            self._clear_caches()
            val_low = target_fn()

            setattr(self, param_name, high)
            self._clear_caches()
            val_high = target_fn()

            min_val = min(val_low, val_high)
            max_val = max(val_low, val_high)
            if not (min_val <= target_val <= max_val):
                return None

            increasing = val_high > val_low

            for _ in range(max_iters):
                mid = (low + high) / 2.0
                setattr(self, param_name, mid)
                self._clear_caches()
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
            base = self.daily_marketing_spend
            spend_levels = [max(0.0, base * m) for m in [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]]

        results = []
        orig_spend = self.daily_marketing_spend
        try:
            for spend in spend_levels:
                self.daily_marketing_spend = spend
                timeline = self.calculate_timeline()
                summary = self.summarize_timeline(timeline, self.starting_capital)
                ltv = self.calculate_ltv()
                ratio = self.calculate_ltv_cpi_ratio()
                results.append({
                    "spend": spend,
                    "total_units": summary["total_units"],
                    "peak_daily_units": summary["peak_daily_units"],
                    "total_accrued": summary["total_accrued"],
                    "final_bank": summary["final_bank"],
                    "ltv": ltv,
                    "ratio": ratio,
                    "break_even": summary["break_even_day"],
                })
        finally:
            self.daily_marketing_spend = orig_spend
        return results


class PCGameTUI(App):
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
        height: 1fr;
        padding: 0 1;
    }
    TabbedContent {
        height: 1fr;
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
        ("ctrl+1", "apply_1", "Apply Price"),
        ("ctrl+2", "apply_2", "Apply Conv%"),
        ("ctrl+3", "apply_3", "Apply CPS"),
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
            self.query_one("#platform_select", Select).focus()
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
        self.title = "PC Runway"
        self.sub_title = "12-Month PC Game Financial Runway Simulator"
        self.store = ScenarioStore()
        self.engine = PCGameEngine()
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
        self.engine = PCGameEngine()

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

                    yield Label("PLATFORM", classes="setting-group")
                    yield Label("Publish Platform:")
                    yield Select(PLATFORM_OPTIONS, value="Steam", id="platform_select")

                with Vertical(id="params-scroll"):
                    yield from self.section(
                        "Launch & Capital",
                        self.labeled_input("Start Date (YYYY-MM-DD):", "in_start_date", self.engine.start_date, type=None),
                        self.labeled_input("Starting Capital ($):", "in_starting_capital", self.engine.starting_capital),
                        self.labeled_input("Game Price ($):", "in_game_price", self.engine.game_price),
                        self.labeled_input("Platform Fee (%):", "in_platform_fee", self.engine.platform_fee_pct),
                        self.labeled_input("Refund Rate (%):", "in_refund_rate", self.engine.refund_rate),
                        self.labeled_input("VAT / Sales Tax (%):", "in_vat", self.engine.vat_rate),
                        self.labeled_input("Regional Pricing (% of list):", "in_regional", self.engine.regional_pricing_pct),
                        self.labeled_input("itch.io Share (%):", "in_itch_share", self.engine.itch_share_pct),
                        collapsed=False,
                    )
                    yield from self.section(
                        "Wishlist & Launch",
                        self.labeled_input("Pre-Launch Wishlists:", "in_wishlists", self.engine.pre_launch_wishlists),
                        self.labeled_input("Launch Conversion (%):", "in_launch_conv", self.engine.launch_conversion_rate),
                        self.labeled_input("Launch Spike Duration (days):", "in_launch_duration", self.engine.launch_spike_duration, type="integer"),
                        self.labeled_input("Launch Spike Multiplier:", "in_launch_mult", self.engine.launch_spike_multiplier),
                        collapsed=False,
                    )
                    yield from self.section(
                        "Sales Pattern",
                        self.labeled_input("Base Daily Sales:", "in_base_sales", self.engine.base_daily_sales),
                        self.labeled_input("Sales Decay Exponent:", "in_sales_decay", self.engine.sales_decay_exponent),
                        self.labeled_input("Sale Event Frequency (days):", "in_sale_freq", self.engine.sale_event_frequency, type="integer"),
                        self.labeled_input("Sale Event Duration (days):", "in_sale_duration", self.engine.sale_event_duration, type="integer"),
                        self.labeled_input("Sale Event Multiplier:", "in_sale_mult", self.engine.sale_event_multiplier),
                        self.labeled_input("Sale Discount (%):", "in_sale_discount", self.engine.sale_discount_pct),
                    )
                    yield from self.section(
                        "DLC",
                        self.labeled_input("DLC Price ($):", "in_dlc_price", self.engine.dlc_price),
                        self.labeled_input("DLC Count:", "in_dlc_count", self.engine.dlc_count, type="integer"),
                        self.labeled_input("DLC Release Interval (days):", "in_dlc_interval", self.engine.dlc_release_interval, type="integer"),
                        self.labeled_input("DLC Attach Rate (%):", "in_dlc_attach", self.engine.dlc_attach_rate),
                        section_id="sec_dlc",
                    )
                    yield from self.section(
                        "Marketing",
                        self.labeled_input("Daily Marketing Spend ($):", "in_marketing", self.engine.daily_marketing_spend),
                        self.labeled_input("Cost Per Sale ($):", "in_cps", self.engine.cost_per_sale),
                    )
                    yield from self.section(
                        "Costs & Payout",
                        self.labeled_input("Fixed Daily Overhead ($):", "in_fixed_ops", self.engine.fixed_overhead_daily),
                        self.labeled_input("Server Cost per 1k Players:", "in_server_k", self.engine.server_cost_per_k_players),
                        self.labeled_input("Payout Delay (Days):", "in_delay", self.engine.payout_delay_days, type="integer"),
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
                    with TabPane("Platform Comparison", id="tab_platform"):
                        yield Static(
                            "[dim]Same game parameters applied to each platform. Press ctrl+r to refresh.[/]",
                            id="platform_instructions",
                        )
                        yield DataTable(id="platform_table")
                    with TabPane("Target Solver", id="tab_solver"):
                        yield Label("Apply Goal:", classes="setting-group")
                        yield Select(
                            [("Breakeven (bank >= $0)", "breakeven"), ("LTV:CPS >= 3.0", "ltv_cps")],
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
                "platform_table": "Platform Comparison",
                "solver_output": "Solver Output (read-only)",
                "kpi_summary": "KPI Summary (read-only)",
                "platform_select": "Platform",
                "scenario_select": "Active Scenario",
                "in_scenario_name": "Scenario Name",
                "btn_save": "Save Button",
                "btn_delete": "Delete Button",
                "in_start_date": "Start Date",
                "in_starting_capital": "Starting Capital",
                "in_game_price": "Game Price",
                "in_platform_fee": "Platform Fee",
                "in_refund_rate": "Refund Rate",
                "in_vat": "VAT / Sales Tax",
                "in_regional": "Regional Pricing",
                "in_itch_share": "itch.io Share",
                "in_wishlists": "Pre-Launch Wishlists",
                "in_launch_conv": "Launch Conversion",
                "in_launch_duration": "Launch Spike Duration",
                "in_launch_mult": "Launch Spike Multiplier",
                "in_base_sales": "Base Daily Sales",
                "in_sales_decay": "Sales Decay Exponent",
                "in_sale_freq": "Sale Event Frequency",
                "in_sale_duration": "Sale Event Duration",
                "in_sale_mult": "Sale Event Multiplier",
                "in_sale_discount": "Sale Discount",
                "in_dlc_price": "DLC Price",
                "in_dlc_count": "DLC Count",
                "in_dlc_interval": "DLC Release Interval",
                "in_dlc_attach": "DLC Attach Rate",
                "in_marketing": "Daily Marketing Spend",
                "in_cps": "Cost Per Sale",
                "in_fixed_ops": "Fixed Daily Overhead",
                "in_server_k": "Server Cost/1k Players",
                "in_delay": "Payout Delay",
            }.get(widget_id, widget_id or widget_type)
            side = "sidebar" if (self._last_sidebar_focus == widget_id) else "right panel"
            indicator.update(f"[dim]Focus: [b]{friendly}[/] ({side})[/]")
        except Exception:
            pass

    def on_mount(self) -> None:
        table = self.query_one("#timeline_table", DataTable)
        table.add_columns(
            "Date", "Units", "DLC", "Cumulative",
            "Accrued Rev", "Cash In", "Expenses",
            "Bank Balance",
        )
        table.cursor_type = "row"

        cmp = self.query_one("#compare_table", DataTable)
        cmp.add_columns(
            "Scenario", "Platform", "Total Units",
            "LTV/Unit", "Break-even", "Year-End Bank",
        )
        cmp.cursor_type = "row"

        platform_tbl = self.query_one("#platform_table", DataTable)
        platform_tbl.add_columns(
            "Platform", "Fee", "Total Units", "Total Rev",
            "LTV/Unit", "Break-even", "Year-End Bank",
        )
        platform_tbl.cursor_type = "row"

        if self.store.list_names():
            self._load_scenario(self.store.list_names()[0])

        self.action_recalculate()
        self._refresh_compare()

    def _apply_dlc_visibility(self):
        dlc_active = self.engine.dlc_count > 0
        section = self.query_one("#sec_dlc", Collapsible)
        section.set_class(not dlc_active, "hidden")
        section.visible = dlc_active
        for widget in section.walk_children():
            if isinstance(widget, Input):
                widget.disabled = not dlc_active

    def _load_scenario(self, name: str):
        params = self.store.get(name)
        if not params:
            return
        self._loading_scenario = True
        try:
            self.engine.apply_params(params)
            platform = params.get("platform", "Steam")
            self.query_one("#platform_select", Select).value = platform
            self._apply_dlc_visibility()
            for attr, widget_id, cast_fn in EXPOSED_PARAMS:
                self.query_one(f"#{widget_id}", Input).value = str(getattr(self.engine, attr))
        finally:
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

        self._apply_dlc_visibility()

        timeline_data = self.engine.calculate_timeline()

        ltv = self.engine.calculate_ltv()
        realized_ltv = self.engine.get_realized_ltv()
        total_units = sum(d["units"] for d in timeline_data)
        final_bank = timeline_data[-1]["bank_balance"]
        bank_color = "green" if final_bank >= 0 else "bold red"
        effective_cps = self.engine._compute_effective_cpi_for_diagnosis()
        cps_color = "green" if ltv / effective_cps >= 3.0 else ("yellow" if ltv / effective_cps >= 1.0 else "bold red")

        self.query_one("#kpi_summary", Static).update(
            f" [dim]LTV/Unit[/] [bold white]${ltv:.2f}[/]  ·  "
            f"[dim]CPS[/] [{cps_color} bold]${effective_cps:.2f}[/]  ·  "
            f"[dim]Total Units[/] [bold white]{total_units:,}[/]  ·  "
            f"[dim]Year-End[/] [{bank_color} bold]${final_bank:,.0f}[/]"
        )

        total_revenue = sum(d["accrued_rev"] for d in timeline_data)
        total_ops = sum(d["ops_cost"] for d in timeline_data)
        annual_net = total_revenue - total_ops
        fully_loaded_cps = total_ops / total_units if total_units > 0 else float("inf")
        if annual_net < 0:
            if realized_ltv < effective_cps:
                diagnosis = (
                    f" [bold red]! Losing ${-annual_net:,.0f}/year "
                    f"-- realized ${realized_ltv:.2f}/unit can't cover CPS ${effective_cps:.2f}[/]"
                )
            else:
                diagnosis = (
                    f" [bold red]! Losing ${-annual_net:,.0f}/year "
                    f"-- ${realized_ltv:.2f}/unit beats CPS ${effective_cps:.2f} but overhead crushes the margin "
                    f"(fully-loaded ${fully_loaded_cps:.2f}/unit)[/]"
                )
        elif annual_net < total_ops * 0.3:
            diagnosis = (
                f" [yellow]Thin -- ${annual_net:+,.0f}/year margin, realized ${realized_ltv:.2f}/unit "
                f"vs CPS ${effective_cps:.2f} (fully-loaded ${fully_loaded_cps:.2f}/unit)[/]"
            )
        else:
            diagnosis = (
                f" [green]+ Healthy -- ${annual_net:+,.0f}/year margin, realized ${realized_ltv:.2f}/unit "
                f"vs CPS ${effective_cps:.2f} (fully-loaded ${fully_loaded_cps:.2f}/unit)[/]"
            )
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
            table.add_row(
                date_text,
                f"{day['units']:,}",
                f"{day['dlc_units']:,}",
                f"{day['cumulative_owners']:,}",
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

        if pane_id == "tab_platform":
            self._refresh_platform_comparison()
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
        pane_ids = ["tab_timeline", "tab_compare", "tab_platform", "tab_solver"]
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
        self._set_input_value("in_game_price", self._solver_results.get("price"))

    def action_apply_2(self) -> None:
        if not hasattr(self, "_solver_results") or not self._solver_results:
            return
        tabs = self.query_one(TabbedContent)
        if not isinstance(tabs.active, str) or tabs.active != "tab_solver":
            return
        self._set_input_value("in_launch_conv", self._solver_results.get("conv"))

    def action_apply_3(self) -> None:
        if not hasattr(self, "_solver_results") or not self._solver_results:
            return
        tabs = self.query_one(TabbedContent)
        if not isinstance(tabs.active, str) or tabs.active != "tab_solver":
            return
        self._set_input_value("in_cps", self._solver_results.get("cps"))

    def _refresh_solver_tab_if_active(self):
        try:
            tabs = self.query_one(TabbedContent)
            pane_id = tabs.active if isinstance(tabs.active, str) else None
        except Exception:
            return
        if pane_id == "tab_solver":
            self._refresh_solver_table()
        elif pane_id == "tab_platform":
            self._refresh_platform_comparison()

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
            tmp_engine = PCGameEngine()
            tmp_engine.apply_params(params)
            self._add_compare_row(cmp, name, tmp_engine)

    def _add_compare_row(self, cmp, name, engine):
        timeline = engine.calculate_timeline()
        summary = PCGameEngine.summarize_timeline(timeline, engine.starting_capital)
        be = str(summary["break_even_day"]) if summary["break_even_day"] is not None else "-"
        ltv = engine.calculate_ltv()
        bank_text = Text(f"${summary['final_bank']:,.2f}")
        bank_text.stylize("green" if summary["final_bank"] >= 0 else "bold red")
        cmp.add_row(
            name,
            engine.platform,
            f"{summary['total_units']:,}",
            f"${ltv:.2f}",
            be,
            bank_text,
        )

    def _refresh_platform_comparison(self):
        table = self.query_one("#platform_table", DataTable)
        table.clear()

        current_snapshot = self.engine.snapshot_params()

        for platform_name, defaults in PLATFORMS.items():
            tmp = PCGameEngine()
            tmp.apply_params(current_snapshot)
            tmp.platform = platform_name
            tmp.platform_fee_pct = defaults["platform_fee"]
            tmp.payout_delay_days = defaults["payout_delay"]
            tmp.itch_share_pct = defaults["itch_share"]

            tl = tmp.calculate_timeline()
            summary = PCGameEngine.summarize_timeline(tl, tmp.starting_capital)
            ltv = tmp.calculate_ltv()

            be = str(summary["break_even_day"]) if summary["break_even_day"] is not None else "-"
            bank_text = Text(f"${summary['final_bank']:,.0f}")
            bank_text.stylize("green" if summary["final_bank"] >= 0 else "bold red")
            is_current = platform_name == self.engine.platform
            platform_label = platform_name + (" *" if is_current else "")

            table.add_row(
                platform_label,
                f"{defaults['platform_fee']:.0f}%",
                f"{summary['total_units']:,}",
                f"${summary['total_accrued']:,.0f}",
                f"${ltv:.2f}",
                be,
                bank_text,
            )

    def _refresh_solver_table(self):
        output = self.query_one("#solver_output", Static)

        price_be = self.engine.solve_parameter("game_price", self.engine.get_final_bank, 0.0, 0.99, 100.0)
        price_ltv = self.engine.solve_parameter("game_price", self.engine.get_ltv_cpi, 3.0, 0.99, 100.0)

        conv_be = self.engine.solve_parameter("launch_conversion_rate", self.engine.get_final_bank, 0.0, 0.1, 99.0)
        conv_ltv = self.engine.solve_parameter("launch_conversion_rate", self.engine.get_ltv_cpi, 3.0, 0.1, 99.0)

        cps_be = self.engine.solve_parameter("cost_per_sale", self.engine.get_final_bank, 0.0, 0.10, 50.0)
        cps_ltv = self.engine.solve_parameter("cost_per_sale", self.engine.get_ltv_cpi, 3.0, 0.10, 50.0)

        current_bank = self.engine.get_final_bank()
        current_ratio = self.engine.calculate_ltv_cpi_ratio()

        def fmt_price(val, current_metric, target):
            if val is None:
                return "[dim yellow]already met ✓[/]" if current_metric >= target else "[dim red]unachievable[/]"
            return f"[bold green]${val:.2f}[/]"

        def fmt_pct(val, current_metric, target):
            if val is None:
                return "[dim yellow]already met ✓[/]" if current_metric >= target else "[dim red]unachievable[/]"
            return f"[bold green]{val:.1f}%[/]"

        breakdown = self.engine.ltv_breakdown_lines()

        if self._solver_goal == "breakeven":
            lines = [
                "",
                "[bold cyan]Goal: Year-End Breakeven (bank >= $0 at 12 months)[/]",
                "",
                "[bold]LTV Breakdown[/]",
                *breakdown,
                "",
                "[bold]Parameter Targets[/]",
                f"  Game Price must be >= {fmt_price(price_be, current_bank, 0.0)}     (current: ${self.engine.game_price:.2f})",
                f"  Launch Conv must be >= {fmt_pct(conv_be, current_bank, 0.0)}  (current: {self.engine.launch_conversion_rate:.1f}%)",
                f"  Cost/Sale must be <= {fmt_price(cps_be, current_bank, 0.0)}    (current: ${self.engine.cost_per_sale:.2f})",
                "",
                "[dim]Press [ctrl+1] Price, [ctrl+2] Conv%, [ctrl+3] CPS to apply. Press [ctrl+t] to switch tabs.[/]",
            ]
            self._solver_results = {
                "price": price_be,
                "conv": conv_be,
                "cps": cps_be,
            }
        else:
            lines = [
                "",
                "[bold cyan]Goal: LTV:CPS >= 3.0[/]",
                "",
                "[bold]LTV Breakdown[/]",
                *breakdown,
                "",
                "[bold]Parameter Targets[/]",
                f"  Game Price must be >= {fmt_price(price_ltv, current_ratio, 3.0)}     (current: ${self.engine.game_price:.2f})",
                f"  Launch Conv must be >= {fmt_pct(conv_ltv, current_ratio, 3.0)}  (current: {self.engine.launch_conversion_rate:.1f}%)",
                f"  Cost/Sale must be <= {fmt_price(cps_ltv, current_ratio, 3.0)}    (current: ${self.engine.cost_per_sale:.2f})",
                "",
                "[dim]Press [ctrl+1] Price, [ctrl+2] Conv%, [ctrl+3] CPS to apply. Press [ctrl+t] to switch tabs.[/]",
            ]
            self._solver_results = {
                "price": price_ltv,
                "conv": conv_ltv,
                "cps": cps_ltv,
            }

        sensitivity = self.engine.calculate_sensitivity()
        lines.append("")
        lines.append("[bold]Marketing Spend Sensitivity[/]")
        lines.append(f"  {'Spend':>8}  {'Units':>10}  {'Total Rev':>12}  {'LTV:CPS':>8}  {'Year-End':>12}  {'Break-even':>10}")
        for r in sensitivity:
            be_str = str(r["break_even"]) if r["break_even"] is not None else "-"
            is_cur = abs(r["spend"] - self.engine.daily_marketing_spend) < 0.01
            marker = "*" if is_cur else " "
            ratio_str = f"{r['ratio']:.2f}" if r["spend"] > 0 else "N/A"
            lines.append(
                f"  ${r['spend']:>6.2f}{marker}  "
                f"{r['total_units']:>9,}  "
                f"${r['total_accrued']:>10,.0f}  "
                f"{ratio_str:>8}  "
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
        elif event.select.id == "platform_select" and event.value is not None:
            if event.value == self.engine.platform:
                return
            if self._loading_scenario:
                return
            self._loading_scenario = True
            try:
                self.engine.platform = str(event.value)
                defaults = PLATFORMS.get(str(event.value), {})
                self.engine.platform_fee_pct = defaults.get("platform_fee", 30.0)
                self.engine.payout_delay_days = defaults.get("payout_delay", 30)
                self.engine.itch_share_pct = defaults.get("itch_share", 0.0)
                self.query_one("#in_platform_fee", Input).value = str(self.engine.platform_fee_pct)
                self.query_one("#in_delay", Input).value = str(self.engine.payout_delay_days)
                self.query_one("#in_itch_share", Input).value = str(self.engine.itch_share_pct)
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
    PCGameTUI().run()
