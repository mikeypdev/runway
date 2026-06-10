import datetime
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input, Label, TabbedContent, TabPane, DataTable

class RevenueLagEngine:
    def __init__(self):
        # 1. Growth Pipeline Variables
        self.influencer_installs = 0.0
        self.organic_ratio = 0.10     
        self.virality_k_factor = 0.05  
        self.cpi = 0.26                
        self.daily_ua_spend = 10.00    
        
        # 2. Tunable Monetization Anchors
        self.payer_pct = 0.03          
        self.platform_fee = 0.30       
        self.video_ecpm = 80.00        
        self.video_impressions = 0.33  
        
        # Real-world F2P Daily Spending Tier Weights (Daily average per active payer)
        self.minnow_spend, self.minnow_pct = 0.10, 0.55
        self.tuna_spend, self.tuna_pct = 0.50, 0.27
        self.dolphin_spend, self.dolphin_pct = 2.00, 0.155
        self.whale_spend, self.whale_pct = 10.00, 0.025

        # 3. Scaling LiveOps OpEx
        self.fixed_overhead_daily = 10.00     
        self.server_cost_per_k_dau = 0.12     
        self.support_cost_per_k_dau = 0.04    
        self.ad_mediation_tax = 0.02          

        # 4. Power-Law Retention Parameters
        self.day_1_retention = 40.0    
        self.decay_exponent = 0.55     

        # Platform Payout Delay
        self.payout_delay_days = 30

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

    def calculate_90_days(self):
        timeline = []
        cumulative_bank_balance = 0.0
        cohort_history = {} 
        accrued_revenue_history = {} 
        start_date = datetime.date(2024, 2, 1)

        daily_payer_spend = self.calculate_daily_payer_arppu()
        ad_arpu_per_dau = (self.video_ecpm * self.video_impressions) / 1000.0

        for day in range(90):
            current_date = start_date + datetime.timedelta(days=day)
            
            # Growth Engine 
            paid_installs = self.daily_ua_spend / self.cpi if self.cpi > 0 else 0
            base_installs = self.influencer_installs + paid_installs
            
            surviving_historical_users = 0.0
            for cohort_day, initial_installs in cohort_history.items():
                days_elapsed = day - cohort_day
                surviving_historical_users += initial_installs * self.get_retention_rate(days_elapsed)
            
            organic_installs = base_installs * self.organic_ratio
            viral_installs = (base_installs + organic_installs) * self.virality_k_factor
            total_new_installs = base_installs + organic_installs + viral_installs
            cohort_history[day] = total_new_installs
            
            dau = surviving_historical_users + total_new_installs
            
            # Accrued Revenue calculations using updated values
            gross_iap = dau * self.payer_pct * daily_payer_spend
            gross_ads = dau * ad_arpu_per_dau
            
            net_iap = gross_iap * (1.0 - self.platform_fee)
            net_ads = gross_ads * (1.0 - self.ad_mediation_tax)
            day_accrued_net_revenue = net_iap + net_ads
            accrued_revenue_history[day] = day_accrued_net_revenue
            
            # Settled Cash Inflow
            day_settled_cash_inflow = 0.0
            payout_day_source = day - self.payout_delay_days
            if payout_day_source >= 0:
                day_settled_cash_inflow = accrued_revenue_history.get(payout_day_source, 0.0)
            
            # Cash Outflow
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
            
            timeline.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "dau": int(dau),
                "accrued_rev": day_accrued_net_revenue,
                "cash_inflow": day_settled_cash_inflow,
                "ops_cost": total_ops_outflow,
                "cash_flow": net_daily_cash_flow,
                "bank_balance": cumulative_bank_balance
            })
            
        return timeline


class BusinessModelTUI(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    #sidebar {
        width: 44;
        background: #1c1c1f;
        border-right: solid #2c2c2f;
        padding: 1;
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
        border: solid #3a3a40;
        height: 3;
        background: #101012;
    }
    Input:focus {
        border: solid #ff9933;
    }
    DataTable {
        height: 1fr;
        border: none;
    }
    """
    
    BINDINGS = [("q", "quit", "Exit Tool"), ("r", "recalculate", "Refresh")]

    def compose(self) -> ComposeResult:
        self.engine = RevenueLagEngine()
        
        yield Header()
        with Vertical(id="sidebar"):
            yield Label("MARKETING CAPITAL", classes="setting-group")
            yield Label("Daily UA Spend ($):")
            yield Input(value=str(self.engine.daily_ua_spend), id="in_ua_spend")
            yield Label("Target CPI ($):")
            yield Input(value=str(self.engine.cpi), id="in_cpi")
            
            yield Label("TUNABLE MONETIZATION", classes="setting-group")
            yield Label("Payer Conversion Rate (0.03 = 3%):")
            yield Input(value=str(self.engine.payer_pct), id="in_payer_pct")
            yield Label("Whale Tier Daily Spend ($):")
            yield Input(value=str(self.engine.whale_spend), id="in_whale_spend")
            yield Label("Video Ad eCPM ($):")
            yield Input(value=str(self.engine.video_ecpm), id="in_video_ecpm")
            
            yield Label("FINANCIAL RUNWAY DELAY", classes="setting-group")
            yield Label("Platform Payout Delay (Days):")
            yield Input(value=str(self.engine.payout_delay_days), id="in_delay")
            
            yield Label("LIVE-OPS OPEX TIERING", classes="setting-group")
            yield Label("Fixed Daily Base Staff ($):")
            yield Input(value=str(self.engine.fixed_overhead_daily), id="in_fixed_ops")
            yield Label("Server Cost per 1k DAU ($):")
            yield Input(value=str(self.engine.server_cost_per_k_dau), id="in_server_k")
            
        with Vertical(id="main-content"):
            with TabbedContent():
                with TabPane("Launch Cash Flow Runway Analyzer", id="tab_timeline"):
                    yield DataTable(id="timeline_table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#timeline_table", DataTable)
        table.add_columns(
            "Date", "Active DAU", "Accrued (Paper) Rev", 
            "Settled Cash Inflow", "Real-time Expenses", 
            "Net Cash Flow", "Cumulative Bank Account"
        )
        table.cursor_type = "row"
        self.action_recalculate()

    def action_recalculate(self) -> None:
        try:
            # Parse Growth & Operations inputs
            self.engine.daily_ua_spend = float(self.query_one("#in_ua_spend", Input).value)
            self.engine.cpi = float(self.query_one("#in_cpi", Input).value)
            self.engine.payout_delay_days = int(self.query_one("#in_delay", Input).value)
            self.engine.fixed_overhead_daily = float(self.query_one("#in_fixed_ops", Input).value)
            self.engine.server_cost_per_k_dau = float(self.query_one("#in_server_k", Input).value)
            
            # Parse newly exposed Monetization parameters
            self.engine.payer_pct = float(self.query_one("#in_payer_pct", Input).value)
            self.engine.whale_spend = float(self.query_one("#in_whale_spend", Input).value)
            self.engine.video_ecpm = float(self.query_one("#in_video_ecpm", Input).value)
        except ValueError:
            # Don't break if the user is in the middle of typing a decimal point
            return 
            
        timeline_data = self.engine.calculate_90_days()
        table = self.query_one("#timeline_table", DataTable)
        table.clear()
        
        for day in timeline_data:
            cf_color = "[green]" if day["cash_flow"] >= 0 else "[span style=reverse] "
            bank_color = "[green]" if day["bank_balance"] >= 0 else "[bold red]"
            
            table.add_row(
                day["date"],
                f"{day['dau']:,}",
                f"${day['accrued_rev']:.2f}",
                f"${day['cash_inflow']:.2f}",
                f"${day['ops_cost']:.2f}",
                f"{cf_color}${day['cash_flow']:.2f}[/]",
                f"{bank_color}${day['bank_balance']:.2f}[/]"
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        self.action_recalculate()

if __name__ == "__main__":
    BusinessModelTUI().run()