from django.urls import path

from apps.dashboard.views.overview import overview, scraping_health
from apps.dashboard.views.financial import (
    financial_profile, market_cap, employee_count, executives,
    income_statement, financial_growth, financial_ratios,
    financial_rating, revenue_per_employee,
)
from apps.dashboard.views.website import (
    change_heatmap, change_type_breakdown, significance_trend,
    changes_per_competitor, change_feed, change_velocity,
)
from apps.dashboard.views.social import (
    engagement_per_competitor, post_volume_trend, post_type_distribution,
    top_posts, posting_frequency_heatmap, author_leaderboard,
    follower_growth, follower_growth_rate, platform_comparison,
    follower_employee_ratio,
)
from apps.dashboard.views.news import news_correlation
from apps.dashboard.views.search import search_symbol
from apps.dashboard.views.hiring import (
    active_openings, hiring_trend, function_breakdown, seniority_distribution,
    top_locations, new_vs_closed, employment_type,
)
from apps.dashboard.views.trends import (
    direction_summary, metric_series, confidence_table,
    high_confidence_alerts, trend_coverage,
)

urlpatterns = [
    # ── Symbol Search (used by Add Competitor modal) ──────────────────────────
    path('search-symbol/', search_symbol, name='search-symbol'),

    # ── Overview ──────────────────────────────────────────────────────────────
    path('overview/', overview, name='dashboard-overview'),
    path('scraping-health/', scraping_health, name='dashboard-scraping-health'),

    # ── Section 1 — Financial Profile ─────────────────────────────────────────
    path('financial-profile/<int:competitor_id>/profile/', financial_profile, name='financial-profile'),
    path('financial-profile/<int:competitor_id>/market-cap/', market_cap, name='market-cap'),
    path('financial-profile/<int:competitor_id>/employee-count/', employee_count, name='employee-count'),
    path('financial-profile/<int:competitor_id>/executives/', executives, name='executives'),

    # ── Section 2 — Financial Health ──────────────────────────────────────────
    path('financial-health/<int:competitor_id>/income/', income_statement, name='income-statement'),
    path('financial-health/<int:competitor_id>/growth/', financial_growth, name='financial-growth'),
    path('financial-health/<int:competitor_id>/ratios/', financial_ratios, name='financial-ratios'),
    path('financial-health/<int:competitor_id>/rating/', financial_rating, name='financial-rating'),
    path('financial-health/<int:competitor_id>/revenue-per-employee/', revenue_per_employee, name='revenue-per-employee'),

    # ── Section 3 — Website Changes ───────────────────────────────────────────
    path('website-changes/heatmap/', change_heatmap, name='change-heatmap'),
    path('website-changes/type-breakdown/', change_type_breakdown, name='change-type-breakdown'),
    path('website-changes/significance-trend/', significance_trend, name='significance-trend'),
    path('website-changes/per-competitor/', changes_per_competitor, name='changes-per-competitor'),
    path('website-changes/feed/', change_feed, name='change-feed'),
    path('website-changes/velocity/', change_velocity, name='change-velocity'),

    # ── Section 4 — Social Media Posts ────────────────────────────────────────
    path('social-posts/engagement/', engagement_per_competitor, name='social-engagement'),
    path('social-posts/volume-trend/', post_volume_trend, name='post-volume-trend'),
    path('social-posts/type-distribution/', post_type_distribution, name='post-type-distribution'),
    path('social-posts/top-posts/', top_posts, name='top-posts'),
    path('social-posts/frequency-heatmap/', posting_frequency_heatmap, name='posting-frequency-heatmap'),
    path('social-posts/authors/', author_leaderboard, name='author-leaderboard'),

    # ── Section 5 — Snapshots ─────────────────────────────────────────────────
    path('snapshots/follower-growth/', follower_growth, name='follower-growth'),
    path('snapshots/growth-rate/', follower_growth_rate, name='follower-growth-rate'),
    path('snapshots/platform-comparison/', platform_comparison, name='platform-comparison'),
    path('snapshots/follower-employee-ratio/', follower_employee_ratio, name='follower-employee-ratio'),

    # ── Section 6 — News Correlation ──────────────────────────────────────────
    path('news/<int:competitor_id>/correlation/', news_correlation, name='news-correlation'),

    # ── Section 7 — Hiring ────────────────────────────────────────────────────
    path('hiring/active-openings/', active_openings, name='active-openings'),
    path('hiring/trend/', hiring_trend, name='hiring-trend'),
    path('hiring/function-breakdown/', function_breakdown, name='function-breakdown'),
    path('hiring/seniority/', seniority_distribution, name='seniority-distribution'),
    path('hiring/locations/', top_locations, name='top-locations'),
    path('hiring/new-vs-closed/', new_vs_closed, name='new-vs-closed'),
    path('hiring/employment-type/', employment_type, name='employment-type'),

    # ── Section 8 — Trends ────────────────────────────────────────────────────
    path('trends/direction-summary/', direction_summary, name='direction-summary'),
    path('trends/metric-series/', metric_series, name='metric-series'),
    path('trends/confidence-table/', confidence_table, name='confidence-table'),
    path('trends/alerts/', high_confidence_alerts, name='high-confidence-alerts'),
    path('trends/coverage/', trend_coverage, name='trend-coverage'),
]
