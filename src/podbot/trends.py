"""Attributable, user-initiated Google Trends RSS and local keyword suggestions."""

from __future__ import annotations

import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

COUNTRIES = {"US", "GB", "CA", "AU", "DE", "FR", "JP", "KR", "BR", "IN"}
NAMESPACE = {"ht": "https://trends.google.com/trending/rss"}
MAX_BYTES = 524_288
KEYWORD_SOURCE = "RSS topic + news headline phrases (suggestions, not Google related queries)"
COMMON_WORDS = {
    "news", "breaking", "latest", "about", "with", "this", "that", "what", "when",
    "from", "have", "will", "are", "was", "the", "for", "and", "now", "how",
    "why", "who", "more", "your", "its", "into", "after", "before", "says",
    "a", "an", "to", "of", "in", "on", "at", "by", "as", "or", "is", "be",
    "up", "out", "off", "than", "over", "under", "via", "per", "not",
}


@dataclass(frozen=True)
class Trend:
    title: str
    approx_traffic: str
    published: str
    country: str
    source_url: str
    keywords: tuple[str, ...] = ()
    news_titles: tuple[str, ...] = ()
    keyword_source: str = KEYWORD_SOURCE


def keyword_suggestions(topic: str, headlines: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Suggest phrases copied from source text, not Google Related Queries."""
    title_tokens = re.findall(r"[\w]+(?:[-'][\w]+)*", topic, re.UNICODE)
    anchor = {
        token.casefold() for token in title_tokens
        if len(token) >= 3 and token.casefold() not in COMMON_WORDS
    }
    if not anchor:
        return ()
    candidates: list[str] = []
    seen: set[str] = set()

    def add(phrase: str) -> None:
        value = " ".join(phrase.split()).strip(" -.,:;!?")
        key = value.casefold()
        words = re.findall(r"[\w]+(?:[-'][\w]+)*", value, re.UNICODE)
        if not words:
            return
        if words[0].casefold() in COMMON_WORDS or words[-1].casefold() in COMMON_WORDS:
            return
        if 3 <= len(value) <= 90 and key not in seen:
            seen.add(key)
            candidates.append(value)

    add(topic)
    for source in (topic, *headlines[:3]):
        words = re.findall(r"[\w]+(?:[-'][\w]+)*", source, re.UNICODE)[:25]
        for count in (3, 2):
            for index in range(len(words) - count + 1):
                window = words[index:index + count]
                meaningful = [
                    part.casefold() for part in window
                    if len(part) >= 3 and part.casefold() not in COMMON_WORDS
                ]
                if meaningful and any(part in anchor for part in meaningful):
                    add(" ".join(window))
                    if len(candidates) >= 10:
                        return tuple(candidates)
    return tuple(candidates)


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
        news_titles = tuple(
            headline[:180] for element in item.findall("ht:news_item", NAMESPACE)
            if (headline := (element.findtext(
                "ht:news_item_title", default="", namespaces=NAMESPACE
            ) or "").strip())
        )[:3]
        results.append(Trend(
            title=title[:180],
            approx_traffic=(item.findtext(
                "ht:approx_traffic", default="", namespaces=NAMESPACE
            ) or "").strip(),
            published=(item.findtext("pubDate") or "").strip(),
            country=country,
            source_url=source,
            keywords=keyword_suggestions(title[:180], news_titles),
            news_titles=news_titles,
        ))
        if len(results) >= limit:
            break
    return results


def read_trends(country: str = "US", limit: int = 10) -> list[Trend]:
    """Fetch public RSS on demand; never crawl or retry on rate limits."""
    url = trend_url(country)
    request = urllib.request.Request(url, headers={
        "User-Agent": "PODBotStudio/1.0-preview.3 (+https://github.com/Anapaulagatti/POD-bot)",
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
