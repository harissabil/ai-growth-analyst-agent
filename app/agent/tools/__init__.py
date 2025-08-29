from .google_analytics import (
    get_google_analytics_daily_traffic,
    get_google_analytics_daily_traffic_for_country,
    get_google_analytics_daily_traffic_for_page,
    get_google_analytics_overall_traffic,
    get_google_analytics_traffic_by_countries,
    get_google_analytics_traffic_by_pages,
)

# --- When you add more tools, just import them and add them to this list ---
# from .search_console import get_search_console_clicks
# from .admob import get_admob_revenue

google_analytics_tools = [
    get_google_analytics_overall_traffic,
    get_google_analytics_daily_traffic,
    get_google_analytics_traffic_by_countries,
    get_google_analytics_daily_traffic_for_country,
    get_google_analytics_traffic_by_pages,
    get_google_analytics_daily_traffic_for_page,
]

# search_console_tools = [get_search_console_clicks, ...]

# Combine all tools into one list for the agent
all_tools = google_analytics_tools  # + search_console_tools + admob_tools