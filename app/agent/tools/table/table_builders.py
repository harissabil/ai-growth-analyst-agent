import json
from typing import Any, Dict, List, Optional

from app.schemas.response import TableSpec


# helpers
def _safe_parse(payload: str) -> Any:
    try:
        return json.loads(payload)
    except Exception:
        return None


def _rows_from_dicts(dicts: List[Dict], keys: List[str]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    for d in dicts:
        rows.append([d.get(k) for k in keys])
    return rows


def _build_table(name: str, data: Any, keys: List[str], headers: Optional[List[str]] = None) -> List[TableSpec]:
    """
    keys: JSON keys to pull from each row (order matters).
    headers: optional display headers; if None, headers == keys.
    """
    if isinstance(data, list) and data:
        cols = headers or keys
        return [TableSpec(name=name, columns=cols, rows=_rows_from_dicts(data, keys))]
    if isinstance(data, dict):
        cols = headers or keys
        return [TableSpec(name=name, columns=cols, rows=[[data.get(k) for k in keys]])]
    return []


# GSC builders
def build_gsc_keywords_table(payload: str) -> List[TableSpec]:
    data = _safe_parse(payload)
    keys = ["keyword", "clicks", "impressions", "ctr_percent", "average_position"]
    return _build_table("Top Keywords (GSC)", data, keys)


def build_gsc_countries_table(payload: str) -> List[TableSpec]:
    data = _safe_parse(payload)
    keys = ["country", "clicks", "impressions", "ctr_percent", "average_position"]
    return _build_table("Top Countries (GSC)", data, keys)


def build_gsc_overall_table(payload: str) -> List[TableSpec]:
    data = _safe_parse(payload)
    keys = ["clicks", "impressions", "ctr_percent", "average_position"]
    return _build_table("Overall (GSC)", data, keys)


def build_gsc_daily_table(payload: str) -> List[TableSpec]:
    data = _safe_parse(payload)
    keys = ["date", "clicks", "impressions", "ctr_percent", "average_position"]
    return _build_table("Daily (GSC)", data, keys)


def build_gsc_daily_for_country_table(payload: str) -> List[TableSpec]:
    # same shape as daily
    return build_gsc_daily_table(payload)


def build_gsc_daily_for_keyword_table(payload: str) -> List[TableSpec]:
    # same shape as daily
    return build_gsc_daily_table(payload)


# GA builders
# NOTE: Your GA models emit snake_case keys due to model_dump(by_alias=False default):
# sessions, screen_page_views, bounce_rate_percent, average_session_duration_seconds, active_users
GA_METRIC_KEYS = [
    "sessions",
    "active_users",
    "screen_page_views",
    "bounce_rate_percent",
    "average_session_duration_seconds",
]


def build_ga_overall_table(payload: str) -> List[TableSpec]:
    data = _safe_parse(payload)
    return _build_table("Overall (GA4)", data, GA_METRIC_KEYS)


def build_ga_daily_table(payload: str) -> List[TableSpec]:
    data = _safe_parse(payload)
    keys = ["date"] + GA_METRIC_KEYS
    return _build_table("Daily (GA4)", data, keys)


def build_ga_countries_table(payload: str) -> List[TableSpec]:
    data = _safe_parse(payload)
    keys = ["country"] + GA_METRIC_KEYS
    return _build_table("Top Countries (GA4)", data, keys)


def build_ga_daily_for_country_table(payload: str) -> List[TableSpec]:
    # same shape as daily
    return build_ga_daily_table(payload)


def build_ga_pages_table(payload: str) -> List[TableSpec]:
    data = _safe_parse(payload)
    # PageAnalyticsData has: page, title + GA_METRIC_KEYS
    keys = ["page", "title"] + GA_METRIC_KEYS
    return _build_table("Top Pages (GA4)", data, keys)


def build_ga_daily_for_page_table(payload: str) -> List[TableSpec]:
    # same shape as daily
    return build_ga_daily_table(payload)


# Ads builders
ADS_BASE_KEYS = [
    "impressions",
    "currency",
    "spend",
    "conversion_rate_percent",
    "ctr_percent",
    "roi_percent",
]


def build_ads_overall_table(payload: str) -> List[TableSpec]:
    data = _safe_parse(payload)
    return _build_table("Overall (Ads)", data, ADS_BASE_KEYS)


def build_ads_daily_table(payload: str) -> List[TableSpec]:
    data = _safe_parse(payload)
    keys = ["date"] + ADS_BASE_KEYS
    return _build_table("Daily (Ads)", data, keys)


def build_ads_campaigns_table(payload: str) -> List[TableSpec]:
    data = _safe_parse(payload)
    # CampaignSummaryData uses id, name, status (not campaign_id)
    keys = ["id", "name", "status"] + ADS_BASE_KEYS
    return _build_table("Campaigns (Ads)", data, keys)


def build_ads_daily_for_campaign_table(payload: str) -> List[TableSpec]:
    # same as daily
    return build_ads_daily_table(payload)


# Tool -> builder map
TOOL_TABLE_BUILDERS = {
    # GA
    "get_google_analytics_overall_traffic": build_ga_overall_table,
    "get_google_analytics_daily_traffic": build_ga_daily_table,
    "get_google_analytics_traffic_by_countries": build_ga_countries_table,
    "get_google_analytics_daily_traffic_for_country": build_ga_daily_for_country_table,
    "get_google_analytics_traffic_by_pages": build_ga_pages_table,
    "get_google_analytics_daily_traffic_for_page": build_ga_daily_for_page_table,
    # GSC
    "get_search_console_overall": build_gsc_overall_table,
    "get_search_console_daily": build_gsc_daily_table,
    "get_search_console_keywords": build_gsc_keywords_table,
    "get_search_console_countries": build_gsc_countries_table,
    "get_search_console_daily_for_country": build_gsc_daily_for_country_table,
    "get_search_console_daily_for_keyword": build_gsc_daily_for_keyword_table,
    # Ads
    "get_google_ads_overall": build_ads_overall_table,
    "get_google_ads_daily": build_ads_daily_table,
    "get_google_ads_campaigns": build_ads_campaigns_table,
    "get_google_ads_daily_for_campaign": build_ads_daily_for_campaign_table,
}


def build_tables_from_messages(messages) -> List[TableSpec]:
    """
    Legacy convenience (if you still use it anywhere).
    Prefer using attach_tables_to_assistant_turns() workflow you already added.
    """
    out: List[TableSpec] = []
    for m in messages:
        typ = getattr(m, "type", None) or getattr(m, "role", None) or m.__class__.__name__.lower()
        if typ == "tool":
            tool_name = getattr(m, "name", None)
            payload = getattr(m, "content", "")
            if not isinstance(payload, str) or payload.strip().lower().startswith("error:"):
                continue
            builder = TOOL_TABLE_BUILDERS.get(tool_name)
            if builder:
                out.extend(builder(payload))
    return out
