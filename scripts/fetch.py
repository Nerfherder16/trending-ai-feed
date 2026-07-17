#!/usr/bin/env python3
"""Fetch rising GitHub repos across topic buckets into trending.json.

Uses the public GitHub Search API. Sends a token from GITHUB_TOKEN/GH_TOKEN if
present (higher rate limit), otherwise runs unauthenticated. Preserves each
repo's first_seen date across runs and keeps a rolling window so the feed shows
what is genuinely new.

Run from repo root: python3 scripts/fetch.py
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WINDOW_DAYS = 30          # only surface repos created within this many days
CREATED_DAYS = 21         # search window for "rising" repos
PER_QUERY = 12            # results per topic query
MIN_STARS = 30            # floor to cut noise
THROTTLE_S = 2.5          # be polite to the search API

# bucket -> list of topics to probe
BUCKETS = {
    "LLM / GenAI": ["llm", "generative-ai", "rag", "llm-agents", "prompt-engineering"],
    "AI tooling": ["ai", "mlops", "inference", "vector-database", "fine-tuning"],
    "Dev tools": ["developer-tools", "cli", "coding-assistant", "devtools"],
    "Infrastructure": ["self-hosted", "kubernetes", "observability", "homelab"],
}


def gh_search(query: str) -> list[dict]:
    params = urllib.parse.urlencode(
        {"q": query, "sort": "stars", "order": "desc", "per_page": PER_QUERY}
    )
    url = f"https://api.github.com/search/repositories?{params}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "trending-ai-feed",
        "Accept": "application/vnd.github+json",
    })
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()).get("items", [])
    except urllib.error.HTTPError as e:
        print(f"  ! {e.code} on query: {query}", file=sys.stderr)
        if e.code in (403, 429):
            time.sleep(30)
        return []
    except Exception as e:  # noqa: BLE001
        print(f"  ! {e} on query: {query}", file=sys.stderr)
        return []


def main() -> None:
    today = date.today()
    created_after = (today - timedelta(days=CREATED_DAYS)).isoformat()

    existing_path = ROOT / "trending.json"
    first_seen: dict[str, str] = {}
    if existing_path.exists():
        prev = json.loads(existing_path.read_text())
        for r in prev.get("repos", []):
            first_seen[r["full_name"]] = r.get("first_seen", str(today))

    found: dict[str, dict] = {}
    for bucket, topics in BUCKETS.items():
        for topic in topics:
            q = f"topic:{topic} created:>={created_after} stars:>={MIN_STARS}"
            items = gh_search(q)
            print(f"{bucket} / {topic}: {len(items)}")
            for it in items:
                name = it["full_name"]
                if name in found:
                    continue  # first bucket wins
                found[name] = {
                    "full_name": name,
                    "url": it["html_url"],
                    "description": (it.get("description") or "").strip(),
                    "language": it.get("language"),
                    "stars": it.get("stargazers_count", 0),
                    "topics": it.get("topics", [])[:8],
                    "bucket": bucket,
                    "created_at": (it.get("created_at") or "")[:10],
                    "pushed_at": (it.get("pushed_at") or "")[:10],
                    "first_seen": first_seen.get(name, str(today)),
                }
            time.sleep(THROTTLE_S)

    # rolling window: drop anything first seen longer ago than WINDOW_DAYS
    cutoff = today - timedelta(days=WINDOW_DAYS)
    repos = [
        r for r in found.values()
        if datetime.strptime(r["first_seen"], "%Y-%m-%d").date() >= cutoff
    ]
    repos.sort(key=lambda r: (r["first_seen"], r["stars"]), reverse=True)

    out = {
        "updated": str(today),
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "window_days": WINDOW_DAYS,
        "buckets": list(BUCKETS.keys()),
        "repos": repos,
    }
    existing_path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"OK: {len(repos)} repos across {len(BUCKETS)} buckets")


if __name__ == "__main__":
    main()
