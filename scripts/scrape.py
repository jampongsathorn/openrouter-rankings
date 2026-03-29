#!/usr/bin/env python3
"""
OpenRouter Rankings Scraper
Fetches openrouter.ai/rankings and extracts all ranking sections from
the embedded Next.js RSC JSON payload — no fragile HTML parsing required.

Sections captured:
  models               – LLM leaderboard: weekly token usage + WoW change %
  market_share         – Token share by model author
  benchmarks           – AI Intelligence Index scores
  fastest              – Highest throughput (tok/s) + price per M tokens
  categories_programming – Top models for programming tasks
  languages_english    – Top models for English language
  programming_python   – Top models for Python
  context_length       – Top models by context-length bucket (requests)
  tool_calls           – Top models by tool-call volume
  images               – Top models by images processed
  apps                 – Top apps/agents by token usage
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

BASE_URL = "https://openrouter.ai"
RANKINGS_URL = f"{BASE_URL}/rankings"
HEADERS = {
    "User-Agent": "openrouter-rankings-scraper/1.0 (github.com/jampongsathorn/openrouter-rankings)",
    "Accept": "text/html,application/xhtml+xml",
}


# ── RSC payload extraction ────────────────────────────────────────────────────

def extract_rsc_blocks(html: str) -> list[Optional[str]]:
    """Return all decoded self.__next_f.push string payloads from HTML."""
    blocks = []
    for m in re.finditer(
        r'<script>self\.__next_f\.push\(\[\d+,([\s\S]*?)\]\)</script>', html
    ):
        try:
            decoded = json.loads(m.group(1))
            blocks.append(decoded if isinstance(decoded, str) else None)
        except Exception:
            blocks.append(None)
    return blocks


def extract_json_value(text: str, key: str) -> Any:
    """Extract the JSON value for `key` from a raw RSC string."""
    marker = f'"{key}":'
    idx = text.find(marker)
    if idx < 0:
        return None
    rest = text[idx + len(marker):]
    if not rest or rest[0] not in "[{":
        # scalar value
        scalar = rest.split(",")[0].split("]")[0].strip().strip('"')
        return scalar or None
    depth = 0
    for i, c in enumerate(rest):
        if c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(rest[: i + 1])
                except Exception:
                    return None
    return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_tokens(n: int) -> str:
    """Format raw token int as display string: 3_500_000_000_000 -> '3.5T'"""
    for suffix, div in [("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)]:
        if n >= div:
            val = n / div
            return f"{val:.3g}{suffix}"
    return str(n)


def compute_change(current: int, previous: int) -> dict:
    if not previous:
        return {"new": True}
    pct = round((current - previous) / previous * 100)
    return {"value": abs(pct), "direction": "up" if pct >= 0 else "down"}


def ys_to_ranked(ys: dict, prev_ys: dict = None, value_key: str = "tokens") -> list[dict]:
    """Convert {model_slug: value} dict to ranked list, excluding 'Others'."""
    items = [(k, v) for k, v in ys.items() if k.lower() != "others" and "/" in k]
    items.sort(key=lambda x: -x[1])
    total = sum(v for _, v in ys.items())
    result = []
    for rank, (slug, value) in enumerate(items, 1):
        parts = slug.split("/")
        author, model_slug = parts[0], "/".join(parts[1:])
        # strip variant suffix like ":free" for display URL
        clean_slug = model_slug.split(":")[0]
        int_value = round(value)
        entry = {
            "rank": rank,
            "model_id": slug,
            "name": slug,           # will be overwritten where name is known
            "author": author,
            "slug": model_slug,
            "url": f"{BASE_URL}/{author}/{clean_slug}",
            value_key: int_value,
            f"{value_key}_display": fmt_tokens(int_value) if int_value >= 1000 else str(int_value),
            "share_pct": round(value / total * 100, 1) if total else None,
        }
        if prev_ys is not None:
            entry["change"] = compute_change(int(value), int(prev_ys.get(slug, 0)))
        result.append(entry)
    return result


# ── Section parsers ───────────────────────────────────────────────────────────

def parse_timeseries_section(block: str, value_key: str = "tokens", with_change: bool = False) -> list[dict]:
    """Parse sections stored as [{x: date, ys: {model: value}}, ...] time series."""
    data = extract_json_value(block, "data")
    if not isinstance(data, list) or not data:
        return []
    latest = data[-1]
    if not isinstance(latest, dict) or "ys" not in latest:
        return []
    ys = latest["ys"]
    prev_ys = data[-2]["ys"] if with_change and len(data) >= 2 else None
    return ys_to_ranked(ys, prev_ys, value_key)


def parse_market_share(block: str) -> list[dict]:
    """Market share: per-author totals."""
    data = extract_json_value(block, "data")
    if not isinstance(data, list) or not data:
        return []
    ys = data[-1].get("ys", {})
    total = sum(ys.values())
    items = [(k, v) for k, v in ys.items() if k.lower() != "others"]
    items.sort(key=lambda x: -x[1])
    return [
        {
            "rank": i + 1,
            "author": author,
            "url": f"{BASE_URL}/{author}",
            "tokens": int(v),
            "tokens_display": fmt_tokens(int(v)),
            "share_pct": round(v / total * 100, 1) if total else None,
        }
        for i, (author, v) in enumerate(items)
    ]


def parse_benchmarks(block: str) -> list[dict]:
    """Intelligence Index benchmark scores."""
    intelligence = extract_json_value(block, "intelligence")
    if not isinstance(intelligence, list):
        return []
    results = []
    for i, item in enumerate(intelligence):
        slug = item.get("openrouter_slug") or item.get("permaslug", "")
        parts = slug.split("/") if "/" in slug else ["", slug]
        author = parts[0]
        model_slug = "/".join(parts[1:])
        results.append({
            "rank": i + 1,
            "model_id": slug,
            "name": item.get("aa_name", slug),
            "author": author,
            "slug": model_slug,
            "url": f"{BASE_URL}/{slug}",
            "score": item.get("score"),
        })
    return results


def parse_fastest(block: str) -> list[dict]:
    """Performance: sort by throughput (tok/s)."""
    data = extract_json_value(block, "data")
    if not isinstance(data, list):
        return []
    # Sort by p50_throughput descending
    data = sorted(data, key=lambda x: -(x.get("p50_throughput") or 0))
    results = []
    for i, item in enumerate(data[:30]):
        slug = item.get("id", item.get("slug", ""))
        parts = slug.split("/") if "/" in slug else ["", slug]
        author = parts[0]
        model_slug = "/".join(parts[1:])
        results.append({
            "rank": i + 1,
            "model_id": slug,
            "name": item.get("name", slug),
            "author": author,
            "slug": model_slug,
            "url": f"{BASE_URL}/{author}/{model_slug.split(':')[0]}",
            "fastest_provider": item.get("best_throughput_provider"),
            "throughput_tok_s": item.get("p50_throughput"),
            "latency_ms_p50": item.get("p50_latency"),
            "price_per_m_tokens": round(item.get("best_throughput_price") or 0, 4),
            "provider_count": item.get("provider_count"),
        })
    return results


def parse_apps(block: str) -> list[dict]:
    """Top apps from rankMap.day."""
    rank_map = extract_json_value(block, "rankMap")
    if not isinstance(rank_map, dict):
        return []
    day = rank_map.get("day", [])
    results = []
    for item in day:
        app = item.get("app", {})
        tokens = int(item.get("total_tokens", 0))
        results.append({
            "rank": item.get("rank", len(results) + 1),
            "name": app.get("title", ""),
            "description": app.get("description", ""),
            "url": app.get("origin_url", ""),
            "tokens": tokens,
            "tokens_display": fmt_tokens(tokens),
            "requests": item.get("total_requests", 0),
            "categories": app.get("categories", []),
        })
    results.sort(key=lambda x: x["rank"])
    # Re-number sequentially in case source has gaps (private/filtered apps)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


# ── Block finder ──────────────────────────────────────────────────────────────

def is_timeseries(block: Optional[str]) -> bool:
    """True if block is a {data: [{x, ys}]} time-series block."""
    if not block:
        return False
    data = extract_json_value(block, "data")
    if not isinstance(data, list) or not data:
        return False
    first = data[0]
    return isinstance(first, dict) and "x" in first and "ys" in first


def find_blocks(blocks: list) -> dict:
    """Identify the relevant RSC blocks by content."""
    result = {}

    # Benchmarks: contains "intelligence" key
    result["benchmarks"] = next(
        (b for b in blocks if b and '"intelligence":' in b and '"score":' in b), None
    )

    # Apps: contains "rankMap" key
    result["apps"] = next(
        (b for b in blocks if b and '"rankMap":' in b and '"day":' in b), None
    )

    # Performance / fastest: contains "p50_throughput"
    result["fastest"] = next(
        (b for b in blocks if b and '"p50_throughput":' in b), None
    )

    # Time-series blocks in page order:
    # leaderboard (model slugs with /), market_share (author names without /),
    # then categories, languages, programming, context, tools, images
    ts_blocks = [b for b in blocks if is_timeseries(b)]

    # Market share: ys keys have NO "/" (they are author names)
    def is_author_series(b):
        data = extract_json_value(b, "data")
        if not data:
            return False
        ys = data[-1].get("ys", {})
        keys = [k for k in ys if k.lower() != "others"]
        return keys and all("/" not in k for k in keys)

    # Leaderboard: ys keys have "/" (model slugs)
    def is_model_series(b):
        data = extract_json_value(b, "data")
        if not data:
            return False
        ys = data[-1].get("ys", {})
        keys = list(ys.keys())
        return keys and any("/" in k for k in keys)

    model_ts = [b for b in ts_blocks if is_model_series(b)]
    author_ts = [b for b in ts_blocks if is_author_series(b)]

    # The 6 model time-series blocks appear in page order:
    # leaderboard, categories_programming, languages_english,
    # programming_python, context_length, tool_calls, images
    section_names = [
        "models", "categories_programming", "languages_english",
        "programming_python", "context_length", "tool_calls", "images"
    ]
    for name, block in zip(section_names, model_ts):
        result[name] = block

    result["market_share_ts"] = author_ts[0] if author_ts else None

    return result


# ── Main scrape ───────────────────────────────────────────────────────────────

def scrape() -> dict:
    print(f"Fetching {RANKINGS_URL} ...")
    resp = requests.get(RANKINGS_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    blocks = extract_rsc_blocks(resp.text)
    fetched_at = datetime.now(timezone.utc).isoformat()
    print(f"  {len(blocks)} RSC blocks found")

    found = find_blocks(blocks)

    value_keys = {
        "models":                  ("tokens",   True),
        "categories_programming":  ("tokens",   False),
        "languages_english":       ("tokens",   False),
        "programming_python":      ("tokens",   False),
        "context_length":          ("requests", False),
        "tool_calls":              ("calls",    False),
        "images":                  ("images",   False),
    }

    data = {}

    for section, (vkey, with_chg) in value_keys.items():
        block = found.get(section)
        if block:
            rows = parse_timeseries_section(block, vkey, with_change=with_chg)
            data[section] = rows
            print(f"  [{section}] {len(rows)} entries")
        else:
            data[section] = []
            print(f"  [{section}] block not found", file=sys.stderr)

    # Market share
    ms_block = found.get("market_share_ts")
    data["market_share"] = parse_market_share(ms_block) if ms_block else []
    print(f"  [market_share] {len(data['market_share'])} entries")

    # Benchmarks
    data["benchmarks"] = parse_benchmarks(found.get("benchmarks") or "")
    print(f"  [benchmarks] {len(data['benchmarks'])} entries")

    # Fastest
    data["fastest"] = parse_fastest(found.get("fastest") or "")
    print(f"  [fastest] {len(data['fastest'])} entries")

    # Apps
    data["apps"] = parse_apps(found.get("apps") or "")
    print(f"  [apps] {len(data['apps'])} entries")

    return {
        "meta": {
            "source_url": RANKINGS_URL,
            "fetched_at": fetched_at,
            "counts": {k: len(v) for k, v in data.items()},
        },
        **data,
    }


def save(data: dict, out_dir: Path) -> Path:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_dir = out_dir / date
    day_dir.mkdir(parents=True, exist_ok=True)

    out_file = day_dir / "rankings.json"
    out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  -> Saved: {out_file}")

    latest = out_dir / "latest.json"
    latest.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  -> Updated: {latest}")
    return out_file


def main():
    repo_root = Path(__file__).parent.parent
    out_dir = repo_root / "data"

    try:
        data = scrape()
        save(data, out_dir)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nTop 10 models:")
    for m in data.get("models", [])[:10]:
        chg = m.get("change", {})
        chg_str = f"+{chg['value']}%" if chg.get("direction") == "up" else (f"-{chg['value']}%" if chg.get("direction") == "down" else "new" if chg.get("new") else "—")
        print(f"  #{m['rank']:2d} {m['model_id']:<52} {m['tokens_display']:>6} tokens  {chg_str}")

    print("\nTop 5 apps:")
    for a in data.get("apps", [])[:5]:
        print(f"  #{a['rank']} {a['name']:<25} {a['tokens_display']:>6} tokens  {a['description'][:40]}")


if __name__ == "__main__":
    main()
