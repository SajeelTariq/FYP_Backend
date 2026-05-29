"""
TrackRival Load Test — Locust
Run: locust -f locustfile.py --headless -u 50 -r 5 -t 60s --host http://localhost:8000
"""
from locust import HttpUser, task, between

TOKEN = "3fd71b5cba8e12b145c8cf2457b26cd21776a7c8"
COMPETITOR_ID_1 = 4   # Apple Inc
COMPETITOR_ID_2 = 3   # Test Co


class DashboardUser(HttpUser):
    wait_time = between(1, 3)
    headers = {"Authorization": f"Token {TOKEN}"}

    # ── Overview ──────────────────────────────────────────────────────────────
    @task(5)
    def overview(self):
        self.client.get("/api/dashboard/overview/", headers=self.headers, name="Overview")

    @task(2)
    def scraping_health(self):
        self.client.get("/api/dashboard/scraping-health/", headers=self.headers, name="Scraping Health")

    # ── Website Changes ───────────────────────────────────────────────────────
    @task(4)
    def change_feed(self):
        self.client.get("/api/dashboard/website-changes/feed/", headers=self.headers, name="Change Feed")

    @task(3)
    def change_heatmap(self):
        self.client.get("/api/dashboard/website-changes/heatmap/", headers=self.headers, name="Change Heatmap")

    @task(2)
    def change_velocity(self):
        self.client.get("/api/dashboard/website-changes/velocity/", headers=self.headers, name="Change Velocity")

    @task(2)
    def significance_trend(self):
        self.client.get("/api/dashboard/website-changes/significance-trend/", headers=self.headers, name="Significance Trend")

    @task(1)
    def type_breakdown(self):
        self.client.get("/api/dashboard/website-changes/type-breakdown/", headers=self.headers, name="Type Breakdown")

    @task(1)
    def per_competitor(self):
        self.client.get("/api/dashboard/website-changes/per-competitor/", headers=self.headers, name="Changes Per Competitor")

    # ── Social Posts ──────────────────────────────────────────────────────────
    @task(3)
    def social_engagement(self):
        self.client.get("/api/dashboard/social-posts/engagement/", headers=self.headers, name="Social Engagement")

    @task(2)
    def top_posts(self):
        self.client.get("/api/dashboard/social-posts/top-posts/", headers=self.headers, name="Top Posts")

    @task(2)
    def volume_trend(self):
        self.client.get("/api/dashboard/social-posts/volume-trend/", headers=self.headers, name="Post Volume Trend")

    @task(1)
    def post_authors(self):
        self.client.get("/api/dashboard/social-posts/authors/", headers=self.headers, name="Post Authors")

    @task(1)
    def frequency_heatmap(self):
        self.client.get("/api/dashboard/social-posts/frequency-heatmap/", headers=self.headers, name="Frequency Heatmap")

    # ── Snapshots ─────────────────────────────────────────────────────────────
    @task(2)
    def platform_comparison(self):
        self.client.get("/api/dashboard/snapshots/platform-comparison/", headers=self.headers, name="Platform Comparison")

    @task(2)
    def growth_rate(self):
        self.client.get("/api/dashboard/snapshots/growth-rate/", headers=self.headers, name="Follower Growth Rate")

    @task(1)
    def follower_employee_ratio(self):
        self.client.get("/api/dashboard/snapshots/follower-employee-ratio/", headers=self.headers, name="Follower/Employee Ratio")

    # ── Hiring ────────────────────────────────────────────────────────────────
    @task(3)
    def active_openings(self):
        self.client.get("/api/dashboard/hiring/active-openings/", headers=self.headers, name="Active Openings")

    @task(2)
    def hiring_trend(self):
        self.client.get("/api/dashboard/hiring/trend/", headers=self.headers, name="Hiring Trend")

    @task(1)
    def function_breakdown(self):
        self.client.get("/api/dashboard/hiring/function-breakdown/", headers=self.headers, name="Function Breakdown")

    @task(1)
    def seniority(self):
        self.client.get("/api/dashboard/hiring/seniority/", headers=self.headers, name="Seniority Distribution")

    @task(1)
    def new_vs_closed(self):
        self.client.get("/api/dashboard/hiring/new-vs-closed/", headers=self.headers, name="New vs Closed Jobs")

    # ── Trends & Alerts ───────────────────────────────────────────────────────
    @task(3)
    def trend_alerts(self):
        self.client.get("/api/dashboard/trends/alerts/", headers=self.headers, name="Trend Alerts")

    @task(2)
    def direction_summary(self):
        self.client.get("/api/dashboard/trends/direction-summary/", headers=self.headers, name="Direction Summary")

    @task(1)
    def confidence_table(self):
        self.client.get("/api/dashboard/trends/confidence-table/", headers=self.headers, name="Confidence Table")

    # ── Financial (FMP cached) ────────────────────────────────────────────────
    @task(2)
    def financial_profile(self):
        self.client.get(f"/api/dashboard/financial-profile/{COMPETITOR_ID_1}/profile/",
                        headers=self.headers, name="Financial Profile")

    @task(1)
    def income_statement(self):
        self.client.get(f"/api/dashboard/financial-health/{COMPETITOR_ID_1}/income/",
                        headers=self.headers, name="Income Statement")

    @task(1)
    def financial_ratios(self):
        self.client.get(f"/api/dashboard/financial-health/{COMPETITOR_ID_1}/ratios/",
                        headers=self.headers, name="Financial Ratios")

    # ── Competitors list ──────────────────────────────────────────────────────
    @task(2)
    def competitors_list(self):
        self.client.get("/api/monitoring/competitors/", headers=self.headers, name="Competitors List")
