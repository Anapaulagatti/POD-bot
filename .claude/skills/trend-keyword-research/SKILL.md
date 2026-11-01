---
name: trend-keyword-research
description: Improve Google Trends RSS research, extract attributable keyword suggestions, and avoid mixing derived phrases with verified related queries.
---

# Trends Keyword Research for PODBot

When changing the Trends page or RSS parser:

1. Keep RSS as the default, lightweight Windows EXE option. Never require paid APIs, browser automation or a key merely to read an RSS feed.
2. Use the actual RSS `title`, `ht:approx_traffic`, `pubDate`, and `ht:news_item/ht:news_item_title` tags as source evidence. Limit response bytes, disallow entities/DTDs and enforce country allowlist.
3. Label generated n-grams from the topic and news headlines as **derived SEO suggestions**, never as real Google Related Queries or evidence of search volume.
4. Test missing news, malformed XML, duplicate terms, multiword Unicode topics, incomplete feeds, abusive source strings and rate limits.
5. User must opt in to copy/prefill design fields. A trend can be a person, brand, entertainment title or protected work. Check local blocklist, never automatically generate or publish merchandise.
6. If real `related_queries[top/rising]` are requested, evaluate [flack0x/trendspyg](https://github.com/flack0x/trendspyg) Explore as an optional, separate module. It uses Chrome and is rate-limit sensitive. Cache with observed timestamps, stop on 429 and never bypass Google access restrictions.
7. Do not default to [GeneralMills/pytrends](https://github.com/GeneralMills/pytrends): it was archived in April 2025. Do not claim topic candidates are current without successfully fetching live RSS.
