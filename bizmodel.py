import datetime
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input, Label, TabbedContent, TabPane, DataTable

class RealisticScenarioEngine:
    def __init__(self):
        # Default Growth Inputs from your littlelike.me sheet
        self.influencer_installs = 0.0
        self.organic_ratio = 0.10     # 10%
        self.virality_factor = 0.05    # 5%
        self.cpi = 0.26                # $0.26
        self.daily_ua_spend = 10.00    # $10.00
        
        # Retention Setting (Now acts as actual Day 1 Retention %)
        self.day_1_retention = 40.0    # 40% (Corresponds to Curve Index 11)
        self.decay_exponent = 0.55     # Industry standard F2P decay curve power parameter
        
        # Monetization & LTV Tier Breakdowns from your sheet
        self.payer_pct = 0.03          # 3.00%
        
        # Blended Average Revenue Per Paying User (ARPPU) based on your tier weights:
        # Minnows (55% @ $0.99), Tuna (27% @ $4.98), Dolphins (15.5% @ $20), Whales (2.49% @ $100)
        self.avg_iap_per_payer = 5.48  
        
        # Ad Revenue Parameters from your sheet
        self.video_ecpm = 80.00        # $80.00
        self.video_impressions = 0.33  # 0.33 impressions per DAU
        self.ad_arpu_per_dau = (self.video_ecpm * self.video_impressions) / 1000.0

        # Fixed Operational Costs (Contractors $10 + Software Overhead)
        self.fixed_expenses_daily = 10.32 

    def get_retention_rate(self, days_alive: int) -> float:
        """
        Calculates user retention using a realistic F2P Power-Law Decay function.
        Replaces linear interpolation to reflect steep Day 2 drops and a flat long-tail.
        """
        if days_alive == 0:
            return 1.00
            
        d1_rate = self.day_1_retention / 100.0
        if days_alive == 1:
            return d1_rate

        # Power-law log decay equation
        retained_rate = d1_rate * (days_alive ** -self.decay_exponent)
        
        # Hard core-player floor: 12% of Day 1 users stay indefinitely
        core_floor = d1_rate * 0.12
        
        return max(retained_rate, core_floor)

    def calculate_90_days(self):
        timeline = []
        cumulative_profit = 0.0
        
        # Track historical cohorts. Key: day_index, Value: historical cohort install quantity
        cohort_history = {} 
        
        start_date = datetime.date(2024, 2, 1)

        for day in range(90):
            current_date = start_date + datetime.timedelta(days=day)
            
            # 1. Calculate Base Installs (Paid + Influencer)
            paid_installs = self.daily_ua_spend / self.cpi if self.cpi > 0 else 0
            base_installs = self.influencer_installs + paid_installs
            
            # 2. Iterate through all past cohorts to build today's baseline active users
            surviving_historical_users = 0.0
            for cohort_day, initial_installs in cohort_history.items():
                days_elapsed = day - cohort_day
                surviving_historical_users += initial_installs * self.get_retention_rate(days_elapsed)
            
            # 3. Apply virality/organics loops based on your active historical pool
            viral_installs = surviving_historical_users * self.virality_factor
            organic_installs = base_installs * self.organic_ratio
            
            total_new_installs = base_installs + organic_installs + viral_installs
            
            # Record current day's cohort into history
            cohort_history[day] = total_new_installs
            
            # Today's total DAU includes the brand new cohort + survivors from prior days
            dau = surviving_historical_users + total_new_installs
            
            # 4. Financial Calculations
            iap_revenue = dau * self.payer_pct * self.avg_iap_per_payer
            ad_revenue = dau * self.ad_arpu_per_dau
            total_revenue = iap_revenue + ad_revenue
            
            total_outflow = self.daily_ua_spend + self.fixed_expenses_daily
            net_cash_flow = total_revenue - total_outflow
            cumulative_profit += net_cash_flow
            
            timeline.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "dau": int(dau),
                "installs": int(total_new_installs),
                "iap": iap_revenue,
                "ads": ad_revenue,
                "cash_flow": net_cash_flow,
                "cum_profit": cumulative_profit
            })
            
        return timeline


class BusinessModelTUI(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    #sidebar {
        width: 38;
        background: #1e1e1e;
        border-right: solid #333333;
        padding: 1;
    }
    #main-content {
        width: 1fr;
    }
    .setting-group {
        background: #2d2d2d;
        color: #00ff00;
        padding: 0 1;
        margin-top: 1;
        margin-bottom: 1;
        text-style: bold;
    }
    Label {
        margin-top: 1;
        color: #cccccc;
    }
    Input {
        margin-bottom: 0;
        border: solid #444444;
        height: 3;
        background: #111111;
    }
    Input:focus {
        border: solid #00ff00;
    }
    DataTable {
        height: 1fr;
        border: none;
    }
    """
    
    BINDINGS = [("q", "quit", "Quit Model"), ("r", "recalculate", "Force Refresh")]

    def compose(self) -> ComposeResult:
        self.engine = RealisticScenarioEngine()
        
        yield Header()
        with Vertical(id="sidebar"):
            yield Label("GROWTH CONFIG", classes="setting-group")
            yield Label("Daily UA Marketing Spend ($):")
            yield Input(value=str(self.engine.daily_ua_spend), id="in_ua_spend")
            yield Label("Target Cost Per Install / CPI ($):")
            yield Input(value=str(self.engine.cpi), id="in_cpi")
            yield Label("Virality K-Factor (%):")
            yield Input(value=str(self.engine.virality_factor), id="in_virality")
            
            yield Label("RETENTION (REALISTIC DECAY)", classes="setting-group")
            yield Label("Expected Day 1 Retention (%):")
            yield Input(value=str(self.engine.day_1_retention), id="in_d1")
            
            yield Label("MONETIZATION MATRICES", classes="setting-group")
            yield Label("Conversion to Payer Ratio (%):")
            yield Input(value=str(self.engine.payer_pct), id="in_payer_pct")
            
        with Vertical(id="main-content"):
            with TabbedContent():
                with TabPane("Realistic 90-Day Financial Grid", id="tab_timeline"):
                    yield DataTable(id="timeline_table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#timeline_table", DataTable)
        table.add_columns("Date", "Daily Installs", "Active DAU", "IAP Gross", "Ad Gross", "Net Cash Flow", "Cumulative Profit")
        table.cursor_type = "row"
        self.action_recalculate()

    def action_recalculate(self) -> None:
        try:
            # Parse settings safely out of input UI widgets 
            self.engine.daily_ua_spend = float(self.query_one("#in_ua_spend", Input).value)
            self.engine.cpi = float(self.query_one("#in_cpi", Input).value)
            self.engine.virality_factor = float(self.query_one("#in_virality", Input).value)
            self.engine.day_1_retention = float(self.query_one("#in_d1", Input).value)
            self.engine.payer_pct = float(self.query_one("#in_payer_pct", Input).value)
        except ValueError:
            return # Protect engine loop from partial string processing while typing
            
        timeline_data = self.engine.calculate_90_days()
        table = self.query_one("#timeline_table", DataTable)
        table.clear()
        
        for idx, day in enumerate(timeline_data):
            # Highlight cash-flow status
            cf_color = "[green]" if day["cash_flow"] >= 0 else "[span style=reverse] "
            profit_color = "[green]" if day["cum_profit"] >= 0 else "[red]"
            
            table.add_row(
                day["date"],
                str(day["installs"]),
                f"[bold cyan]{day['dau']}[/]",
                f"${day['iap']:.2f}",
                f"${day['ads']:.2f}",
                f"{cf_color}${day['cash_flow']:.2f}[/]",
                f"{profit_color}${day['cum_profit']:.2f}[/]"
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        # Re-runs data processing loops dynamically on keystroke modifications
        self.action_recalculate()

if __name__ == "__main__":
    BusinessModelTUI().run()