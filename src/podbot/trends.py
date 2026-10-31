"""Attributable, user-initiated Google Trends RSS research (not product approval)."""

from __future__ import annotations

import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

COUNTRIES = {"US", "GB", "CA", "AU", "DE", "FR", "JP", "KR", "BR", "IN"}
NAMESPACE = {"ht": "https://trends.google.com/trending/rss"}
MAX_BYTES = 524_288


@dataclass(frozen=True)
class Trend:
    title: str
    approx_traffic: str
    published: str
    country: str
    source_url: str


def trend_url(country: str) -> str:
    if country not in COUNTRIES:
        raise ValueError("Unsupported country. Allowed: " + ", ".join(sorted(COUNTRIES)))
    return f"https://trends.google.com/trending/rss?geo={country}"


def parse_trends(xml: str, country: str = "US", limit: int = 10) -> list[Trend]:
    source = trend_url(country)
    if not 1 <= limit <= 50:
        raise ValueError("Trends limit must be between 1 and 50.")
    if len(xml.encode("utf-8")) > MAX_BYTES:
        raise ValueError("RSS response exceeded size limit.")
    if re.search(r"<!\s*(DOCTYPE|ENTITY)\b", xml, flags=re.IGNORECASE):
        raise ValueError("DOCTYPE/ENTITY declarations not permitted in RSS.")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError("Invalid Google Trends RSS response.") from exc
    results: list[Trend] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        results.append(Trend(
            title=title[:180],
            approx_traffic=(item.findtext("ht:approx_traffic", default="", namespaces=NAMESPACE) or "").strip(),
            published=(item.findtext("pubDate") or "").strip(),
            country=country,
            source_url=source,
        ))
        if len(results) >= limit:
            break
    return results


def read_trends(country: str = "US", limit: int = 10) -> list[Trend]:
    """Fetch public RSS on demand; never crawl or retry on rate limits."""
    url = trend_url(country)
    request = urllib.request.Request(url, headers={
        "User-Agent": "PODBotStudio/1.0-preview.1 (+https://github.com/Anapaulagatti/POD-bot)",
        "Accept": "application/rss+xml, application/xml",
    })
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read(MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Google Trends RSS is unavailable; try later.") from exc
    if len(raw) > MAX_BYTES:
        raise ValueError("RSS response exceeded size limit.")
    return parse_trends(raw.decode("utf-8-sig"), country, limit)
