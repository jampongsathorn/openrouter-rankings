# openrouter-rankings

[![Daily Snapshot](https://github.com/jampongsathorn/openrouter-rankings/actions/workflows/daily.yml/badge.svg)](https://github.com/jampongsathorn/openrouter-rankings/actions/workflows/daily.yml)

**Daily auto-updated snapshots of every section on [OpenRouter Rankings](https://openrouter.ai/rankings)** — the real-world LLM usage leaderboard powered by millions of API calls.

No API key needed. Just fetch JSON.

---

## What's inside

Every snapshot captures **11 sections** of the rankings page:

| Section | Description | Metric |
|---|---|---|
| `models` | LLM leaderboard — weekly token usage | tokens + WoW change % |
| `market_share` | Token share by model author | tokens + share % |
| `benchmarks` | AI Intelligence Index scores | score (0–100) |
| `fastest` | Highest throughput models | tok/s + price/M tokens |
| `categories_programming` | Top models for coding tasks | tokens + share % |
| `languages_english` | Top models for English | tokens + share % |
| `programming_python` | Top models for Python specifically | tokens + share % |
| `context_length` | Top models by prompt length bucket | requests + share % |
| `tool_calls` | Top models by tool-call volume | calls + share % |
| `images` | Top models by images processed | images + share % |
| `apps` | Top apps/agents using OpenRouter | tokens + request count |

---

## Quick start

```bash
# Get today's snapshot date
curl https://raw.githubusercontent.com/jampongsathorn/openrouter-rankings/main/data/latest.json

# Fetch the full snapshot
curl https://raw.githubusercontent.com/jampongsathorn/openrouter-rankings/main/data/2026-03-28/rankings.json
```

### Python

```python
import requests

# Step 1: find the latest date
latest = requests.get(
    "https://raw.githubusercontent.com/jampongsathorn/openrouter-rankings/main/data/latest.json"
).json()

# Step 2: fetch the full snapshot
data = requests.get(
    f"https://raw.githubusercontent.com/jampongsathorn/openrouter-rankings/main/data/{latest['date']}/rankings.json"
).json()

# Top 10 models by weekly token usage
for m in data["models"][:10]:
    chg = m["change"]
    direction = f"+{chg['value']}%" if chg.get("direction") == "up" else f"-{chg['value']}%" if chg.get("direction") == "down" else "new"
    print(f"#{m['rank']:2d} {m['model_id']:<52} {m['tokens_display']:>6}  {direction}")
```

Output:
```
# 1 xiaomi/mimo-v2-pro-20260318                           3.12T  +109%
# 2 stepfun/step-3.5-flash:free                           1.25T  -16%
# 3 minimax/minimax-m2.7-20260318                          1.1T  new
# 4 deepseek/deepseek-v3.2-20251201                       1.02T  -10%
# 5 anthropic/claude-4.6-sonnet-20260217                   887B  -15%
...
```

### JavaScript / Node

```js
const latest = await fetch(
  "https://raw.githubusercontent.com/jampongsathorn/openrouter-rankings/main/data/latest.json"
).then(r => r.json());

const data = await fetch(
  `https://raw.githubusercontent.com/jampongsathorn/openrouter-rankings/main/data/${latest.date}/rankings.json`
).then(r => r.json());

// Top apps
data.apps.slice(0, 5).forEach(a =>
  console.log(`#${a.rank} ${a.name.padEnd(20)} ${a.tokens_display.padStart(6)} tokens  ${a.description}`)
);
```

Output:
```
#1 OpenClaw               803B tokens  The AI that actually does things
#2 Kilo Code              259B tokens  AI coding agent for VS Code
#3 Claude Code           97.6B tokens  The AI for problem solvers
#4 Cline                   81B tokens  Autonomous coding agent right in your IDE
#5 Descript              40.6B tokens  AI Video & Podcast Editor
```

---

## File structure

```
data/
  latest.json            ← always points to the newest date
  2026-03-28/
    rankings.json        ← full snapshot for that day
  2026-03-27/
    rankings.json
  ...
```

`latest.json` shape:
```json
{ "date": "2026-03-28", "path": "2026-03-28/rankings.json" }
```

---

## Full snapshot schema

```json
{
  "meta": {
    "source_url": "https://openrouter.ai/rankings",
    "fetched_at": "2026-03-28T06:00:00+00:00",
    "counts": {
      "models": 9,
      "market_share": 9,
      "benchmarks": 20,
      "fastest": 30,
      "categories_programming": 9,
      "languages_english": 9,
      "programming_python": 9,
      "context_length": 9,
      "tool_calls": 9,
      "images": 9,
      "apps": 20
    }
  },

  "models": [
    {
      "rank": 1,
      "model_id": "xiaomi/mimo-v2-pro-20260318",
      "author": "xiaomi",
      "slug": "mimo-v2-pro-20260318",
      "url": "https://openrouter.ai/xiaomi/mimo-v2-pro-20260318",
      "tokens": 3122586458443,
      "tokens_display": "3.12T",
      "share_pct": 16.4,
      "change": { "value": 109, "direction": "up" }
    }
  ],

  "market_share": [
    {
      "rank": 1,
      "author": "xiaomi",
      "url": "https://openrouter.ai/xiaomi",
      "tokens": 4261458516476,
      "tokens_display": "4.26T",
      "share_pct": 19.6
    }
  ],

  "benchmarks": [
    {
      "rank": 1,
      "model_id": "google/gemini-3.1-pro-preview",
      "name": "Gemini 3.1 Pro Preview",
      "author": "google",
      "slug": "gemini-3.1-pro-preview",
      "url": "https://openrouter.ai/google/gemini-3.1-pro-preview",
      "score": 57.2
    }
  ],

  "fastest": [
    {
      "rank": 1,
      "model_id": "openai/gpt-oss-safeguard-20b",
      "name": "OpenAI: gpt-oss-safeguard-20b",
      "author": "openai",
      "slug": "gpt-oss-safeguard-20b",
      "url": "https://openrouter.ai/openai/gpt-oss-safeguard-20b",
      "fastest_provider": "Groq",
      "throughput_tok_s": 838,
      "latency_ms_p50": 156,
      "price_per_m_tokens": 0.075,
      "provider_count": 1
    }
  ],

  "categories_programming": [ ... ],
  "languages_english":       [ ... ],
  "programming_python":      [ ... ],
  "context_length":          [ ... ],
  "tool_calls":              [ ... ],
  "images":                  [ ... ],

  "apps": [
    {
      "rank": 1,
      "name": "OpenClaw",
      "description": "The AI that actually does things",
      "url": "https://openclaw.ai/",
      "tokens": 802957283969,
      "tokens_display": "803B",
      "requests": 13620750,
      "categories": ["personal-agent"]
    }
  ]
}
```

The `categories_programming`, `languages_english`, `programming_python`, `context_length`, `tool_calls`, and `images` sections all share this shape:

```json
{
  "rank": 1,
  "model_id": "xiaomi/mimo-v2-pro-20260318",
  "author": "xiaomi",
  "slug": "mimo-v2-pro-20260318",
  "url": "https://openrouter.ai/xiaomi/mimo-v2-pro-20260318",
  "tokens": 2300000000000,
  "tokens_display": "2.3T",
  "share_pct": 31.9
}
```

---

## Historical analysis example

Track how a model's weekly token usage has changed over time:

```python
import requests
from datetime import date, timedelta

BASE = "https://raw.githubusercontent.com/jampongsathorn/openrouter-rankings/main/data"
MODEL = "anthropic/claude-4.6-sonnet-20260217"

history = []
d = date(2026, 3, 1)
while d <= date.today():
    try:
        snap = requests.get(f"{BASE}/{d}/rankings.json", timeout=5).json()
        entry = next((m for m in snap["models"] if m["model_id"] == MODEL), None)
        if entry:
            history.append((str(d), entry["tokens_display"], entry["rank"]))
    except:
        pass
    d += timedelta(days=1)

for date_str, tokens, rank in history:
    print(f"{date_str}  rank #{rank}  {tokens}")
```

---

## Run locally

```bash
git clone https://github.com/jampongsathorn/openrouter-rankings
cd openrouter-rankings
pip install requests beautifulsoup4
python scripts/scrape.py
```

The snapshot is saved to `data/YYYY-MM-DD/rankings.json` and `data/latest.json` is updated.

---

## How it works

1. **GitHub Actions** runs `scripts/scrape.py` every day at **06:00 UTC**
2. The script fetches `openrouter.ai/rankings` and extracts all ranking data from the **embedded Next.js RSC JSON payload** (no HTML parsing, no JS execution needed)
3. Data is saved as a dated JSON snapshot in `data/`
4. `data/latest.json` is updated to point to the newest date
5. Changes are committed and pushed automatically

The scraper reads the RSC payload directly from the HTML response — robust to layout changes since it targets the structured data, not the visual HTML.

---

## Notes

- **OpenRouter has no public rankings API** — this project bridges that gap
- Token counts reflect **weekly usage** aggregated across all providers
- `change` values are **week-over-week** percentage movement
- `{ "new": true }` means the model appeared on the leaderboard for the first time
- Data is captured once per day; the live page may show slightly different numbers for the in-progress current week
- Inspired by [oolong-tea-2026/arena-ai-leaderboards](https://github.com/oolong-tea-2026/arena-ai-leaderboards)
