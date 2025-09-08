from .google_ads import (
    get_google_ads_campaigns,
    get_google_ads_daily,
    get_google_ads_daily_for_campaign,
    get_google_ads_overall,
)
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

google_search_console_tools = [
    get_search_console_overall,
    get_search_console_daily,
    get_search_console_countries,
    get_search_console_daily_for_country,
    get_search_console_keywords,
    get_search_console_daily_for_keyword,
]

google_ads_tools = [
    get_google_ads_overall,
    get_google_ads_daily,
    get_google_ads_campaigns,
    get_google_ads_daily_for_campaign,
]

# Combine all tools into one list for the agent
all_tools = utility_tools + google_analytics_tools + google_search_console_tools + google_ads_tools
