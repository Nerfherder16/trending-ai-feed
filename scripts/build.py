#!/usr/bin/env python3
"""Generate trending.md, dashboard.html, and feed.xml from trending.json.

Run from repo root: python3 scripts/build.py
"""
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
PAGES_URL = "https://nerfherder16.github.io/trending-ai-feed"
BUCKET_COLORS = {
    "LLM / GenAI": "#8b5cf6",
    "AI tooling": "#38bdf8",
    "Dev tools": "#34d399",
    "Infrastructure": "#f59e0b",
}
DEFAULT_COLOR = "#f472b6"


def fmt_stars(n: int) -> str:
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def build_markdown(data: dict) -> str:
    by_bucket: dict[str, list] = {}
    for r in data["repos"]:
        by_bucket.setdefault(r["bucket"], []).append(r)
    lines = [
        "# Trending AI / Dev / Infra Repos",
        "",
        f"Updated: {data['updated']} · {len(data['repos'])} repos · "
        f"rolling {data['window_days']}-day window",
        "",
        f"Live dashboard: {PAGES_URL}/ · RSS: {PAGES_URL}/feed.xml",
        "",
        "> For Claude: this is a discovery feed of recently-created, fast-rising",
        "> repos. Surface relevant ones when Tim starts related work.",
        "",
    ]
    for bucket in data["buckets"]:
        repos = by_bucket.get(bucket, [])
        if not repos:
            continue
        lines.append(f"## {bucket} ({len(repos)})")
        lines.append("")
        for r in sorted(repos, key=lambda x: -x["stars"]):
            lang = r["language"] or "—"
            lines.append(
                f"- [{r['full_name']}]({r['url']}) · {lang} · ★{fmt_stars(r['stars'])} · "
                f"new {r['first_seen']} — {r['description'] or 'No description.'}"
            )
        lines.append("")
    return "\n".join(lines)


def build_feed(data: dict) -> str:
    now = format_datetime(datetime.now(timezone.utc))
    items = []
    for r in data["repos"][:60]:
        try:
            fs = datetime.strptime(r["first_seen"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            pub = format_datetime(fs)
        except ValueError:
            pub = now
        lang = r["language"] or "—"
        desc = (
            f"[{r['bucket']}] {r['description'] or 'No description.'} "
            f"(★{fmt_stars(r['stars'])}, {lang}, created {r['created_at']})"
        )
        items.append(f"""    <item>
      <title>{escape(r['full_name'])} — ★{fmt_stars(r['stars'])}</title>
      <link>{escape(r['url'])}</link>
      <guid isPermaLink="true">{escape(r['url'])}</guid>
      <category>{escape(r['bucket'])}</category>
      <pubDate>{pub}</pubDate>
      <description>{escape(desc)}</description>
    </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Trending AI / Dev / Infra Repos</title>
    <link>{PAGES_URL}/</link>
    <description>Recently-created, fast-rising GitHub repos across LLM/GenAI, AI tooling, dev tools, and infrastructure. Refreshed daily.</description>
    <language>en</language>
    <lastBuildDate>{now}</lastBuildDate>
    <ttl>720</ttl>
{chr(10).join(items)}
  </channel>
</rss>
"""


def build_dashboard(data: dict) -> str:
    colors = {b: BUCKET_COLORS.get(b, DEFAULT_COLOR) for b in data["buckets"]}
    payload = json.dumps(
        {"updated": data["updated"], "window_days": data["window_days"],
         "repos": data["repos"], "buckets": data["buckets"], "colors": colors}
    ).replace("</", "<\\/")
    total_stars = sum(r["stars"] for r in data["repos"])
    return TEMPLATE \
        .replace("__DATA__", payload) \
        .replace("__UPDATED__", data["updated"]) \
        .replace("__GENERATED__", data.get("generated", "")) \
        .replace("__NREPOS__", str(len(data["repos"]))) \
        .replace("__WINDOW__", str(data["window_days"])) \
        .replace("__NSTARS__", fmt_stars(total_stars)) \
        .replace("__PAGES__", PAGES_URL)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trending AI / Dev / Infra Repos</title>
<link rel="alternate" type="application/rss+xml" title="Trending repos RSS" href="__PAGES__/feed.xml">
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root {
  --bg-page:#0f0d1a; --bg-card:#1e1b2e; --bg-elevated:#2d2a3e;
  --text-primary:#f1f5f9; --text-secondary:#94a3b8; --text-muted:#64748b;
  --border-visible:rgba(255,255,255,.10); --accent:#38bdf8;
  --font-display:'Space Grotesk',system-ui,sans-serif;
  --font-mono:'JetBrains Mono',ui-monospace,monospace;
}
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg-page); color:var(--text-primary); font-family:var(--font-display); min-height:100vh; }
.wrap { max-width:1280px; margin:0 auto; padding:2.5rem 1.5rem 4rem; }
header { display:flex; flex-wrap:wrap; align-items:flex-end; justify-content:space-between; gap:1.5rem; margin-bottom:1.75rem; }
h1 { font-size:1.6rem; font-weight:600; letter-spacing:-.01em; }
.sub { color:var(--text-muted); font-size:.85rem; margin-top:.35rem; }
.sub a { color:var(--accent); text-decoration:none; }
.sub a:hover { text-decoration:underline; }
.stats { display:flex; gap:.75rem; }
.stat { background:rgba(255,255,255,.04); border:1px solid var(--border-visible); border-radius:8px; padding:.6rem 1.1rem; min-width:6rem; }
.stat .label { font-size:.6rem; font-weight:600; text-transform:uppercase; letter-spacing:.08em; color:var(--text-muted); }
.stat .value { font-size:1.5rem; font-weight:300; margin-top:.15rem; }
.controls { display:flex; flex-direction:column; gap:.85rem; margin-bottom:1.5rem; }
#search { width:100%; max-width:26rem; background:rgba(255,255,255,.05); border:1px solid var(--border-visible); border-radius:8px; padding:.6rem .9rem; color:var(--text-primary); font-family:var(--font-display); font-size:.9rem; outline:none; transition:border-color .2s, box-shadow .2s; }
#search:focus { border-color:rgba(56,189,248,.5); box-shadow:0 0 0 2px rgba(56,189,248,.1); }
#search::placeholder { color:var(--text-muted); }
.chips { display:flex; flex-wrap:wrap; gap:.5rem; }
.chip { display:inline-flex; align-items:center; gap:.4rem; border-radius:999px; border:1px solid var(--border-visible); background:rgba(255,255,255,.04); color:var(--text-secondary); padding:.32rem .8rem; font-size:.78rem; font-weight:500; font-family:var(--font-display); cursor:pointer; transition:all .15s; }
.chip:hover { background:rgba(255,255,255,.08); color:var(--text-primary); }
.chip .count { font-family:var(--font-mono); font-size:.68rem; color:var(--text-muted); }
.chip.active { background:color-mix(in srgb, var(--chip-color, var(--accent)) 15%, transparent); border-color:color-mix(in srgb, var(--chip-color, var(--accent)) 45%, transparent); color:var(--chip-color, var(--accent)); }
.chip.active .count { color:inherit; opacity:.7; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:1rem; }
.card { display:flex; flex-direction:column; gap:.6rem; background:rgba(255,255,255,.045); border:1px solid var(--border-visible); border-left:3px solid var(--cat-color); border-radius:10px; padding:1.05rem 1.2rem; transition:transform .15s, background .15s, box-shadow .15s; }
.card:hover { transform:translateY(-2px); background:rgba(255,255,255,.07); box-shadow:0 8px 24px rgba(0,0,0,.35); }
.card-top { display:flex; align-items:flex-start; justify-content:space-between; gap:.6rem; }
.card a.name { color:var(--text-primary); font-weight:600; font-size:.95rem; text-decoration:none; word-break:break-word; }
.card a.name:hover { color:var(--cat-color); }
.badge { flex-shrink:0; border-radius:999px; padding:.18rem .6rem; font-size:.6rem; font-weight:600; background:color-mix(in srgb, var(--cat-color) 14%, transparent); color:var(--cat-color); white-space:nowrap; }
.desc { color:var(--text-secondary); font-size:.82rem; line-height:1.5; flex:1; }
.meta { display:flex; align-items:center; flex-wrap:wrap; gap:.9rem; font-family:var(--font-mono); font-size:.7rem; color:var(--text-muted); }
.new { color:var(--cat-color); }
.dot { display:inline-block; width:.5rem; height:.5rem; border-radius:50%; background:var(--cat-color); margin-right:.3rem; vertical-align:-1px; }
.empty { grid-column:1/-1; text-align:center; padding:4rem 1rem; color:var(--text-muted); }
footer { margin-top:3rem; text-align:center; color:var(--text-muted); font-size:.72rem; font-family:var(--font-mono); }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Trending Repos</h1>
      <div class="sub">rolling __WINDOW__-day window · updated __UPDATED__ · <a href="__PAGES__/feed.xml">RSS feed</a></div>
    </div>
    <div class="stats">
      <div class="stat"><div class="label">Repos</div><div class="value">__NREPOS__</div></div>
      <div class="stat"><div class="label">Combined ★</div><div class="value">__NSTARS__</div></div>
    </div>
  </header>
  <div class="controls">
    <input id="search" type="search" placeholder="Search name, description, or topic…" autocomplete="off">
    <div class="chips" id="chips"></div>
  </div>
  <div class="grid" id="grid"></div>
  <footer>generated __GENERATED__ · fetch.py + build.py · refreshed daily by Claude routine</footer>
</div>
<script>
const DATA = __DATA__;
let activeBucket = null, query = "";
const langOf = r => r.language || "—";
const fmtStars = n => n >= 1000 ? (n/1000).toFixed(1).replace(/\.0$/, "") + "k" : String(n);
const esc = s => (s||"").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function counts() { const m = {}; DATA.repos.forEach(r => m[r.bucket] = (m[r.bucket]||0)+1); return m; }
function renderChips() {
  const c = counts(); const el = document.getElementById("chips"); el.innerHTML = "";
  const all = document.createElement("button");
  all.className = "chip" + (activeBucket === null ? " active" : "");
  all.innerHTML = `All <span class="count">${DATA.repos.length}</span>`;
  all.onclick = () => { activeBucket = null; render(); };
  el.appendChild(all);
  DATA.buckets.forEach(b => {
    if (!c[b]) return;
    const btn = document.createElement("button");
    btn.className = "chip" + (activeBucket === b ? " active" : "");
    btn.style.setProperty("--chip-color", DATA.colors[b]);
    btn.innerHTML = `${esc(b)} <span class="count">${c[b]}</span>`;
    btn.onclick = () => { activeBucket = activeBucket === b ? null : b; render(); };
    el.appendChild(btn);
  });
}
function matches(r) {
  if (activeBucket && r.bucket !== activeBucket) return false;
  if (!query) return true;
  const hay = (r.full_name + " " + r.description + " " + r.bucket + " " +
    (r.topics||[]).join(" ") + " " + langOf(r)).toLowerCase();
  return query.toLowerCase().split(/\s+/).every(t => hay.includes(t));
}
function render() {
  renderChips();
  const grid = document.getElementById("grid");
  const repos = DATA.repos.filter(matches)
    .sort((a, b) => (a.first_seen < b.first_seen ? 1 : a.first_seen > b.first_seen ? -1 : b.stars - a.stars));
  grid.innerHTML = repos.length ? "" : '<div class="empty">No repos match.</div>';
  repos.forEach(r => {
    const card = document.createElement("div");
    card.className = "card";
    card.style.setProperty("--cat-color", DATA.colors[r.bucket] || "#f472b6");
    card.innerHTML = `
      <div class="card-top">
        <a class="name" href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.full_name)}</a>
        <span class="badge">${esc(r.bucket)}</span>
      </div>
      <div class="desc">${esc(r.description) || "No description."}</div>
      <div class="meta">
        <span><span class="dot"></span>${esc(langOf(r))}</span>
        <span>★ ${fmtStars(r.stars)}</span>
        <span class="new">new ${esc(r.first_seen)}</span>
      </div>`;
    grid.appendChild(card);
  });
}
document.getElementById("search").addEventListener("input", e => { query = e.target.value.trim(); render(); });
render();
</script>
</body>
</html>
"""


def main() -> None:
    data = json.loads((ROOT / "trending.json").read_text())
    (ROOT / "trending.md").write_text(build_markdown(data))
    (ROOT / "dashboard.html").write_text(build_dashboard(data))
    (ROOT / "index.html").write_text(build_dashboard(data))  # Pages entry point
    (ROOT / "feed.xml").write_text(build_feed(data))
    print(f"OK: {len(data['repos'])} repos -> trending.md, dashboard.html, index.html, feed.xml")


if __name__ == "__main__":
    main()
