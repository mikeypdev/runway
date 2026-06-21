import datetime
import json
import math
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input, Label, TabbedContent, TabPane, DataTable, Select, Button

SCENARIOS_FILE = Path("scenarios.json")

MODEL_F2P = "f2p"
MODEL_PREMIUM = "premium"
MODEL_REMOVE_ADS = "remove_ads"

MODEL_OPTIONS = [
    ("F2P (IAP + Ads)", MODEL_F2P),
    ("Premium (Buy Once)", MODEL_PREMIUM),
    ("F2P + Remove Ads IAP", MODEL_REMOVE_ADS),
]

EXPOSED_PARAMS = [
    ("daily_ua_spend", "in_ua_spend", float),
    ("cpi", "in_cpi", float),
    ("cpi_saturation", "in_cpi_sat", float),
    ("influencer_installs", "in_influencer", float),
    ("organic_ratio", "in_organic", float),
    ("virality_k_factor", "in_kfactor", float),
    ("payer_pct", "in_payer_pct", float),
    ("whale_spend", "in_whale_spend", float),
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
    ("start_date", "in_start_date", str),
]

WIDGET_GROUPS = {
    "grp_iap": {"in_payer_pct", "in_whale_spend"},
    "grp_ads": {"in_video_ecpm", "in_video_impressions"},
    "grp_game_price": {"in_game_price"},
    "grp_ad_removal": {"in_ad_removal_price", "in_ad_removal_pct"},
}

DEFAULT_SCENARIOS = {
    "F2P Base Case": {
        "model_type": MODEL_F2P,
        "daily_ua_spend": 10.00, "cpi": 0.26, "cpi_saturation": 0.30,
        "influencer_installs": 0.0,
        "organic_ratio": 0.10, "virality_k_factor": 0.05,
        "payer_pct": 0.03, "whale_spend": 10.00,
        "video_ecpm": 80.00, "video_impressions": 0.33, "platform_fee": 0.30,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 10.00, "server_cost_per_k_dau": 0.12,
        "day_1_retention": 40.0, "decay_exponent": 0.55,
        "game_price": 4.99, "ad_removal_price": 2.99, "ad_removal_pct": 0.05,
    },
    "Premium $4.99": {
        "model_type": MODEL_PREMIUM,
        "daily_ua_spend": 15.00, "cpi": 0.80, "cpi_saturation": 0.40,
        "influencer_installs": 10.0,
        "organic_ratio": 0.12, "virality_k_factor": 0.04,
        "payer_pct": 0.03, "whale_spend": 10.00,
        "video_ecpm": 0.0, "video_impressions": 0.0, "platform_fee": 0.30,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 10.00, "server_cost_per_k_dau": 0.12,
        "day_1_retention": 45.0, "decay_exponent": 0.50,
        "game_price": 4.99, "ad_removal_price": 2.99, "ad_removal_pct": 0.05,
    },
    "F2P Remove Ads $2.99": {
        "model_type": MODEL_REMOVE_ADS,
        "daily_ua_spend": 10.00, "cpi": 0.26, "cpi_saturation": 0.30,
        "influencer_installs": 0.0,
        "organic_ratio": 0.10, "virality_k_factor": 0.05,
        "payer_pct": 0.03, "whale_spend": 10.00,
        "video_ecpm": 80.00, "video_impressions": 0.33, "platform_fee": 0.30,
        "payout_delay_days": 30,
        "fixed_overhead_daily": 10.00, "server_cost_per_k_dau": 0.12,
        "day_1_retention": 40.0, "decay_exponent": 0.55,
        "game_price": 4.99, "ad_removal_price": 2.99, "ad_removal_pct": 0.05,
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

        self.payer_pct = 0.03
        self.platform_fee = 0.30
        self.video_ecpm = 80.00
        self.video_impressions = 0.33

        self.minnow_spend, self.minnow_pct = 0.10, 0.55
        self.tuna_spend, self.tuna_pct = 0.50, 0.27
        self.dolphin_spend, self.dolphin_pct = 2.00, 0.155
        self.whale_spend, self.whale_pct = 10.00, 0.025

        self.fixed_overhead_daily = 10.00
        self.server_cost_per_k_dau = 0.12
        self.support_cost_per_k_dau = 0.04
        self.ad_mediation_tax = 0.02

        self.day_1_retention = 40.0
        self.decay_exponent = 0.55

        self.payout_delay_days = 30

        self.game_price = 4.99
        self.ad_removal_price = 2.99
        self.ad_removal_pct = 0.05
        self.start_date = datetime.date.today().strftime("%Y-%m-%d")

    def apply_params(self, params: dict):
        if "model_type" in params:
            self.model_type = params["model_type"]
        start_date_input = datetime.date.today().strftime("%Y-%m-%d")
        for attr, widget_id, cast_fn in EXPOSED_PARAMS:
            if attr in params:
                setattr(self, attr, cast_fn(params[attr]))
        if "start_date" not in params:
            self.start_date = start_date_input

    def snapshot_params(self) -> dict:
        result = {"model_type": self.model_type}
        result.update({attr: getattr(self, attr) for attr, _, _ in EXPOSED_PARAMS})
        return result

    def calculate_daily_payer_arppu(self) -> float:
        return (
            (self.minnow_pct * self.minnow_spend) +
            (self.tuna_pct * self.tuna_spend) +
            (self.dolphin_pct * self.dolphin_spend) +
            (self.whale_pct * self.whale_spend)
        )

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
            return self.game_price * (1.0 - self.platform_fee)

        if self.model_type == MODEL_REMOVE_ADS:
            iap_ltv = self.ad_removal_pct * self.ad_removal_price * (1.0 - self.platform_fee)
            ad_ltv = (1.0 - self.ad_removal_pct) * ad_arpu_per_dau * lifetime * (1.0 - self.ad_mediation_tax)
            return iap_ltv + ad_ltv

        iap_arpu = self.payer_pct * daily_payer_spend
        net_iap = iap_arpu * (1.0 - self.platform_fee)
        net_ads = ad_arpu_per_dau * (1.0 - self.ad_mediation_tax)
        return (net_iap + net_ads) * lifetime

    def calculate_ltv_cpi_ratio(self) -> float:
        ltv = self.calculate_ltv()
        return ltv / self.cpi if self.cpi > 0 else float("inf")

    def calculate_timeline(self):
        all_days = []
        cumulative_bank_balance = 0.0
        cohort_history = {}
        accrued_revenue_history = {}
        cumulative_paid_installs = 0.0
        start_date = datetime.date.fromisoformat(self.start_date)

        daily_payer_spend = self.calculate_daily_payer_arppu()
        ad_arpu_per_dau = (self.video_ecpm * self.video_impressions) / 1000.0

        for day in range(365):
            current_date = start_date + datetime.timedelta(days=day)

            effective_cpi = self.cpi * (1 + self.cpi_saturation * math.log(1 + cumulative_paid_installs / 10000))
            paid_installs = self.daily_ua_spend / effective_cpi if effective_cpi > 0 else 0
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

            if self.model_type == MODEL_PREMIUM:
                gross_rev = total_new_installs * self.game_price
                net_rev = gross_rev * (1.0 - self.platform_fee)
                day_accrued_net_revenue = net_rev

            elif self.model_type == MODEL_REMOVE_ADS:
                ad_removers = total_new_installs * self.ad_removal_pct
                iap_rev = ad_removers * self.ad_removal_price
                ad_viewing_dau = dau * (1.0 - self.ad_removal_pct)
                gross_ads = ad_viewing_dau * ad_arpu_per_dau
                net_iap = iap_rev * (1.0 - self.platform_fee)
                net_ads = gross_ads * (1.0 - self.ad_mediation_tax)
                day_accrued_net_revenue = net_iap + net_ads

            else:
                gross_iap = dau * self.payer_pct * daily_payer_spend
                gross_ads = dau * ad_arpu_per_dau
                net_iap = gross_iap * (1.0 - self.platform_fee)
                net_ads = gross_ads * (1.0 - self.ad_mediation_tax)
                day_accrued_net_revenue = net_iap + net_ads

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
                self.daily_ua_spend
            )

            net_daily_cash_flow = day_settled_cash_inflow - total_ops_outflow
            cumulative_bank_balance += net_daily_cash_flow

            all_days.append({
                "date": current_date,
                "dau": int(dau),
                "accrued_rev": day_accrued_net_revenue,
                "cash_inflow": day_settled_cash_inflow,
                "ops_cost": total_ops_outflow,
                "cash_flow": net_daily_cash_flow,
                "bank_balance": cumulative_bank_balance
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
                    "accrued_rev": sum(r["accrued_rev"] for r in rows),
                    "cash_inflow": sum(r["cash_inflow"] for r in rows),
                    "ops_cost": sum(r["ops_cost"] for r in rows),
                    "cash_flow": sum(r["cash_flow"] for r in rows),
                    "bank_balance": rows[-1]["bank_balance"],
                })

        return timeline

    @staticmethod
    def summarize_timeline(timeline: list[dict]) -> dict:
        peak_dau = max(d["dau"] for d in timeline)
        total_accrued = sum(d["accrued_rev"] for d in timeline)
        final_bank = timeline[-1]["bank_balance"]
        break_even = next(
            (i for i, d in enumerate(timeline) if d["bank_balance"] >= 0), None
        )
        return {
            "peak_dau": peak_dau,
            "total_accrued": total_accrued,
            "final_bank": final_bank,
            "break_even_day": break_even,
        }


class BusinessModelTUI(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    #sidebar {
        width: 46;
        background: #1c1c1f;
        border-right: solid #2c2c2f;
        padding: 1;
        overflow-y: auto;
    }
    #main-content {
        width: 1fr;
    }
    .setting-group {
        background: #2a2a30;
        color: #ff9933;
        padding: 0 1;
        margin-top: 1;
        margin-bottom: 0;
        text-style: bold;
    }
    Label {
        margin-top: 1;
        color: #a0a0a8;
        text-style: dim;
    }
    Input {
        margin-bottom: 0;
        border: none;
        height: 1;
        width: 100%;
        background: #101012;
    }
    Input:focus {
        background: #2a2a30;
    }
    DataTable {
        height: 1fr;
        border: none;
    }
    Select {
        width: 100%;
        margin-bottom: 0;
    }
    Select:focus > .select--current {
        border: tall #ff9933;
    }
    #scenario-bar {
        height: 1;
        margin-bottom: 1;
    }
    .btn-sm {
        height: 1;
        min-width: 10;
        margin-right: 1;
        border: none;
    }
    #kpi_summary {
        padding: 0 1;
        height: 3;
        color: #a0a0a8;
        background: #1c1c1f;
        border-bottom: solid #2c2c2f;
    }
    .hidden {
        display: none;
    }
    """

    BINDINGS = [("q", "quit", "Exit"), ("r", "recalculate", "Refresh"), ("s", "toggle_panel", "Switch Panel"), ("escape", "unfocus", "Unfocus")]

    def action_toggle_panel(self) -> None:
        self._panel_on_sidebar = not self._panel_on_sidebar
        if self._panel_on_sidebar:
            for w in self.query_one("#sidebar").walk_children():
                if isinstance(w, Input):
                    w.focus()
                    return
        else:
            self.query_one("#timeline_table").focus()

    def action_unfocus(self) -> None:
        focused = self.focused
        if isinstance(focused, Input) and self._focus_original_value is not None:
            if focused.value != self._focus_original_value:
                focused.value = self._focus_original_value
        self._focus_original_value = None
        self.set_focus(None)

    def on_descendant_focus(self, event) -> None:
        if isinstance(event.widget, Input):
            self._focus_original_value = event.widget.value
        else:
            self._focus_original_value = None

    def __init__(self):
        super().__init__()
        self.store = ScenarioStore()
        self._loading_scenario = False
        self._focus_original_value: str | None = None
        self._panel_on_sidebar = True

    def labeled_input(
        self, label_text: str, input_id: str, value, *, type: str | None = "number"
    ) -> ComposeResult:
        # Always emit Label + Input as a pair. The label id is derived from
        # the input id (in_* -> lbl_*), so visibility toggles can find the
        # label for any input by convention instead of a lookup map.
        label_id = "lbl_" + input_id[len("in_"):]
        yield Label(label_text, id=label_id)
        if type is None:
            yield Input(value=str(value), id=input_id)
        else:
            yield Input(value=str(value), id=input_id, type=type)

    def compose(self) -> ComposeResult:
        self.engine = RevenueLagEngine()

        scenario_options = [(n, n) for n in self.store.list_names()]
        first_scenario = scenario_options[0][0] if scenario_options else None

        yield Header()
        with Vertical(id="sidebar"):
            yield Label("SCENARIO", classes="setting-group")
            yield Label("Active Scenario:")
            yield Select(scenario_options, value=first_scenario, id="scenario_select")
            yield Label("New Scenario Name:")
            yield Input(placeholder="Type name, then Save", id="in_scenario_name")
            with Horizontal(id="scenario-bar"):
                yield Button("Save", id="btn_save", variant="primary", classes="btn-sm")
                yield Button("Delete", id="btn_delete", variant="error", classes="btn-sm")

            yield Label("BUSINESS MODEL", classes="setting-group")
            yield Label("Revenue Model:")
            yield Select(MODEL_OPTIONS, value=MODEL_F2P, id="model_type_select")

            yield Label("LAUNCH DATE", classes="setting-group")
            yield from self.labeled_input(
                "Start Date (YYYY-MM-DD):", "in_start_date", self.engine.start_date, type=None
            )

            yield Label("MARKETING CAPITAL", classes="setting-group")
            yield from self.labeled_input(
                "Daily UA Spend ($):", "in_ua_spend", self.engine.daily_ua_spend
            )
            yield from self.labeled_input(
                "Cost Per Install ($):", "in_cpi", self.engine.cpi
            )
            yield from self.labeled_input(
                "CPI Saturation (compounds with scale):", "in_cpi_sat", self.engine.cpi_saturation
            )
            yield from self.labeled_input(
                "Burst / Influencer Installs per Day:", "in_influencer", self.engine.influencer_installs
            )

            yield Label("GROWTH & RETENTION", classes="setting-group")
            yield from self.labeled_input(
                "Organic Install Ratio (vs paid):", "in_organic", self.engine.organic_ratio
            )
            yield from self.labeled_input(
                "Viral K-Factor (installs/user):", "in_kfactor", self.engine.virality_k_factor
            )
            yield from self.labeled_input(
                "D1 Retention (%):", "in_d1_retention", self.engine.day_1_retention
            )
            yield from self.labeled_input(
                "Retention Decay Rate:", "in_decay", self.engine.decay_exponent
            )

            yield Label("IAP MONETIZATION", classes="setting-group", id="lbl_iap")
            yield from self.labeled_input(
                "Payer Conversion Rate (0.03 = 3%):", "in_payer_pct", self.engine.payer_pct
            )
            yield from self.labeled_input(
                "Avg Whale Daily Spend ($):", "in_whale_spend", self.engine.whale_spend
            )

            yield Label("AD REVENUE", classes="setting-group", id="lbl_ads")
            yield from self.labeled_input(
                "Video Ad eCPM ($):", "in_video_ecpm", self.engine.video_ecpm
            )
            yield from self.labeled_input(
                "Ad Impressions / DAU / Day:", "in_video_impressions", self.engine.video_impressions
            )

            yield Label("PREMIUM PRICING", classes="setting-group", id="lbl_premium")
            yield from self.labeled_input(
                "Game Price ($):", "in_game_price", self.engine.game_price
            )

            yield Label("AD REMOVAL IAP", classes="setting-group", id="lbl_remove_ads")
            yield from self.labeled_input(
                "Ad Removal Price ($):", "in_ad_removal_price", self.engine.ad_removal_price
            )
            yield from self.labeled_input(
                "Removal Conversion %:", "in_ad_removal_pct", self.engine.ad_removal_pct
            )

            yield Label("PLATFORM FEES", classes="setting-group")
            yield from self.labeled_input(
                "Platform Fee (0.30 = 30%):", "in_platform_fee", self.engine.platform_fee
            )
            yield from self.labeled_input(
                "Platform Payout Delay (Days):", "in_delay", self.engine.payout_delay_days, type="integer"
            )

            yield Label("LIVE-OPS OPEX", classes="setting-group")
            yield from self.labeled_input(
                "Fixed Daily Overhead ($):", "in_fixed_ops", self.engine.fixed_overhead_daily
            )
            yield from self.labeled_input(
                "Server Cost per 1k DAU ($):", "in_server_k", self.engine.server_cost_per_k_dau
            )

        with Vertical(id="main-content"):
            with TabbedContent():
                with TabPane("12-Month Runway", id="tab_timeline"):
                    yield Label(id="kpi_summary")
                    yield DataTable(id="timeline_table")
                with TabPane("Compare Scenarios", id="tab_compare"):
                    yield DataTable(id="compare_table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#timeline_table", DataTable)
        table.add_columns(
            "Date", "DAU", "Accrued Rev",
            "Cash In", "Expenses",
            "Bank Balance"
        )
        table.cursor_type = "row"

        cmp = self.query_one("#compare_table", DataTable)
        cmp.add_columns(
            "Scenario", "Model", "Peak DAU", "LTV", "LTV:CPI",
            "Break-even", "Year-End Bank"
        )
        cmp.cursor_type = "row"

        if self.store.list_names():
            self._load_scenario(self.store.list_names()[0])

        self.action_recalculate()
        self._refresh_compare()

    def _apply_model_visibility(self, model_type: str):
        show = {"grp_iap": False, "grp_ads": False, "grp_game_price": False, "grp_ad_removal": False}

        if model_type == MODEL_F2P:
            show["grp_iap"] = True
            show["grp_ads"] = True
        elif model_type == MODEL_PREMIUM:
            show["grp_game_price"] = True
        elif model_type == MODEL_REMOVE_ADS:
            show["grp_ads"] = True
            show["grp_ad_removal"] = True

        for group, widget_ids in WIDGET_GROUPS.items():
            visible = show[group]
            for wid in widget_ids:
                widget = self.query_one(f"#{wid}")
                widget.set_class(not visible, "hidden")
            header_id = {
                "grp_iap": "lbl_iap", "grp_ads": "lbl_ads",
                "grp_game_price": "lbl_premium", "grp_ad_removal": "lbl_remove_ads",
            }[group]
            header = self.query_one(f"#{header_id}")
            header.set_class(not visible, "hidden")
            for wid in widget_ids:
                label = self.query_one(f"#lbl_{wid[3:]}")
                label.set_class(not visible, "hidden")

    def _load_scenario(self, name: str):
        params = self.store.get(name)
        if not params:
            return
        self._loading_scenario = True
        try:
            self.engine.apply_params(params)
            model_type = params.get("model_type", MODEL_F2P)
            self.query_one("#model_type_select", Select).value = model_type
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

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "scenario_select" and event.value is not None:
            self._load_scenario(str(event.value))
            self.action_recalculate()
        elif event.select.id == "model_type_select" and event.value is not None:
            self.engine.model_type = str(event.value)
            self._apply_model_visibility(str(event.value))
            self.action_recalculate()

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
            current = self.query_one("#scenario_select", Select)
            if current.value:
                self.store.delete(str(current.value))
                self._refresh_select()
                names = self.store.list_names()
                if names:
                    self._load_scenario(names[0])
                    self.action_recalculate()
                self._refresh_compare()

    def action_recalculate(self) -> None:
        try:
            for attr, widget_id, cast_fn in EXPOSED_PARAMS:
                widget = self.query_one(f"#{widget_id}", Input)
                if widget.has_class("hidden"):
                    continue
                setattr(self.engine, attr, cast_fn(widget.value))
        except ValueError:
            return

        timeline_data = self.engine.calculate_timeline()

        ltv = self.engine.calculate_ltv()
        ratio = self.engine.calculate_ltv_cpi_ratio()
        ratio_color = "[green]" if ratio >= 3.0 else ("[yellow]" if ratio >= 1.0 else "[bold red]")
        peak_dau = max(d["dau"] for d in timeline_data)
        final_bank = timeline_data[-1]["bank_balance"]
        bank_color = "[green]" if final_bank >= 0 else "[bold red]"
        self.query_one("#kpi_summary", Label).update(
            f"LTV: [bold white]${ltv:.2f}[/]  ·  "
            f"CPI: [bold white]${self.engine.cpi:.2f}[/]  ·  "
            f"LTV:CPI: {ratio_color}[bold]{ratio:.2f}[/][/]  ·  "
            f"Peak DAU: [bold white]{peak_dau:,}[/]  ·  "
            f"Year-End: {bank_color}[bold]${final_bank:,.0f}[/][/]"
        )

        table = self.query_one("#timeline_table", DataTable)
        table.clear()

        for day in timeline_data:
            bank_color = "[green]" if day["bank_balance"] >= 0 else "[bold red]"

            table.add_row(
                day["date"],
                f"{day['dau']:,}",
                f"${day['accrued_rev']:.2f}",
                f"${day['cash_inflow']:.2f}",
                f"${day['ops_cost']:.2f}",
                f"{bank_color}${day['bank_balance']:.2f}[/]"
            )

    def _refresh_compare(self):
        cmp = self.query_one("#compare_table", DataTable)
        cmp.clear()
        for name in self.store.list_names():
            params = self.store.get(name)
            if not params:
                continue
            tmp_engine = RevenueLagEngine()
            tmp_engine.apply_params(params)
            timeline = tmp_engine.calculate_timeline()
            summary = RevenueLagEngine.summarize_timeline(timeline)
            be = str(summary["break_even_day"]) if summary["break_even_day"] is not None else "—"
            bank_color = "[green]" if summary["final_bank"] >= 0 else "[bold red]"
            ltv = tmp_engine.calculate_ltv()
            ratio = tmp_engine.calculate_ltv_cpi_ratio()
            ratio_color = "[green]" if ratio >= 3.0 else ("[yellow]" if ratio >= 1.0 else "[bold red]")
            model_label = {
                MODEL_F2P: "F2P", MODEL_PREMIUM: "Premium", MODEL_REMOVE_ADS: "RemAds",
            }.get(params.get("model_type", MODEL_F2P), "F2P")
            cmp.add_row(
                name,
                model_label,
                f"{summary['peak_dau']:,}",
                f"${ltv:.2f}",
                f"{ratio_color}{ratio:.2f}[/]",
                be,
                f"{bank_color}${summary['final_bank']:,.2f}[/]",
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "in_scenario_name":
            return
        if self._loading_scenario:
            return
        self.action_recalculate()


if __name__ == "__main__":
    BusinessModelTUI().run()
