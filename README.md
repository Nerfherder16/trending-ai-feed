# trending-ai-feed

A daily-refreshed discovery feed of recently-created, fast-rising GitHub repos
across **LLM / GenAI**, **AI tooling**, **Dev tools**, and **Infrastructure**.

- **Dashboard:** https://nerfherder16.github.io/trending-ai-feed/
- **RSS:** https://nerfherder16.github.io/trending-ai-feed/feed.xml (subscribe in any reader)

## How it works

A daily Claude Code cloud routine runs:

```bash
python3 scripts/fetch.py   # queries the GitHub Search API across topic buckets
python3 scripts/build.py   # regenerates dashboard.html, index.html, feed.xml, trending.md
```

`fetch.py` looks for repos **created in the last ~3 weeks** with a star floor,
sorted by stars (a "rising" proxy), records a `first_seen` date per repo, and
keeps a rolling 30-day window so the feed shows what is genuinely new. Set
`GITHUB_TOKEN` in the environment for a higher rate limit; it also runs
unauthenticated.

## Files

| File | What |
|------|------|
| `trending.json` | Source of truth. |
| `dashboard.html` / `index.html` | Visual dashboard (dark, bucket filters, search). Generated. |
| `feed.xml` | RSS 2.0 feed. Generated. |
| `trending.md` | Markdown list, grouped by bucket. Generated. |
| `scripts/fetch.py` | Pulls fresh data from GitHub. |
| `scripts/build.py` | Renders all outputs from `trending.json`. |

Tune buckets, window, and thresholds at the top of `scripts/fetch.py`.
