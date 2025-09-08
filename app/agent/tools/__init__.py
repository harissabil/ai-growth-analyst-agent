from .google_analytics import (
    get_google_analytics_daily_traffic,
    get_google_analytics_daily_traffic_for_country,
    get_google_analytics_daily_traffic_for_page,
    get_google_analytics_overall_traffic,
    get_google_analytics_traffic_by_countries,
    get_google_analytics_traffic_by_pages,
)
from .google_search_console import (
    get_search_console_countries,
    get_search_console_daily,
    get_search_console_daily_for_country,
    get_search_console_daily_for_keyword,
    get_search_console_keywords,
    get_search_console_overall,
)
from .utils import get_current_datetime

# --- When you add more tools, just import them and add them to this list ---
# from .search_console import get_search_console_clicks
# from .admob import get_admob_revenue

utility_tools = [
    get_current_datetime,
]

google_analytics_tools = [
    get_google_analytics_overall_traffic,
    get_google_analytics_daily_traffic,
    get_google_analytics_traffic_by_countries,
    get_google_analytics_daily_traffic_for_country,
    get_google_analytics_traffic_by_pages,
    get_google_analytics_daily_traffic_for_page,
]

search_console_tools = [
    get_search_console_overall,
    get_search_console_daily,
    get_search_console_countries,
    get_search_console_daily_for_country,
    get_search_console_keywords,
    get_search_console_daily_for_keyword,
]

# Combine all tools into one list for the agent
all_tools = utility_tools + google_analytics_tools + search_console_tools  # + admob_tools
