# extensions/

This directory contains all data source extensions. Each extension is a self-contained unit that owns its full pipeline:

```
fetch() → process() → render() → FeedSection
```

The orchestrator (`main.py`) calls `ext.run()` on every enabled extension and assembles the results into the daily payload.

---

## How an extension works

```
┌─────────────────────────────────────────────────────────┐
│  BaseExtension.run()                                    │
│                                                         │
│  1. fetch()   — pull raw items (no LLM)                 │
│  2. process() — score / filter / summarise (LLM ok)     │
│  3. render()  — package into FeedSection                │
└─────────────────────────────────────────────────────────┘
```

### FeedSection

The output every extension must produce:

```python
@dataclass
class FeedSection:
    key:         str        # snake_case, matches config/sources.yaml key
    title:       str        # display name shown in rendered output
    icon:        str        # marker shown in nav + heading
    payload_key: str | None # optional flat JSON key (defaults to key)
    items:       list[dict] # processed item dicts
    meta:        dict       # optional stats (counts, durations, etc.)
```

### What's injected into `self.config`

The orchestrator merges your `sources.yaml` block with `config/extensions/{name}.yaml` and injects:

| Key | Value |
|---|---|
| `enabled` | bool from sources.yaml |
| `language` | output language code (e.g. `"en"`) |
| `llm_scoring_model` | model name for scoring |
| `llm_summarization_model` | model name for summarisation |
| `dry_run` | `True` when `--dry-run` flag is set — **skip all LLM calls** |

---

## Quickstart: build a new extension

### 1. Copy the template package

```bash
cp -r extensions/_template extensions/my_source
```

### 2. Fill in the three methods

Open `extensions/my_source/__init__.py` and implement:

- **`fetch()`** — pull raw data. Return a list of dicts. No LLM calls here.
- **`process()`** — optional. Call `self.llm` to score or summarise. Respect `dry_run`.
- **`render()`** — wrap items in a `FeedSection`. No network calls here.

### 3. Register it

In `extensions/__init__.py`:

```python
from extensions.my_source import MySourceExtension

REGISTRY = [
    ...,
    MySourceExtension,   # add here
]
```

### 4. Add a template and config block

Create `extensions/my_source/template.md.j2`. This file owns the section's markdown rendering and receives the current section as `sec`.

```jinja2
{% if sec["items"] %}
<h2 id="{{ sec.key }}">{{ sec.icon }} {{ sec.title }} ({{ sec["items"]|length }})</h2>

{% for item in sec["items"] %}
- {{ item }}
{% endfor %}
{% endif %}
```

Then add it to `config/sources.yaml`:

```yaml
display_order:
  - my_source
```

```yaml
my_source:
  enabled: true
  # any source-level limits (e.g. max_items)
```

If your extension needs filter/keyword config, create `config/extensions/my_source.yaml`:

```yaml
# config/extensions/my_source.yaml
keywords:
  - AI
  - machine learning
llm_score_threshold: 7
```

### 5. Write a test

Add `tests/test_my_source.py`. At minimum, test your `fetch()` parsing logic with a fixture — no live network calls needed. See `tests/test_hn_collector.py` for a simple example.

---

## Testing

```bash
# Run all tests
PYTHONPATH=. pytest tests/ -q

# Run only your extension's tests
PYTHONPATH=. pytest tests/test_my_source.py -v

# Smoke test: fetch real data without LLM calls (no API cost)
python main.py --dry-run
```

`--dry-run` fetches live data from all enabled extensions but skips every LLM call, so you can verify your `fetch()` and parsing logic without spending any API credits.

---

## Built-in extensions

Each extension is a package (`extensions/<name>/`) containing `__init__.py` (the extension class), `template.md.j2` (its section template), and usually `README.md` (docs specific to that extension).

An extension may also provide optional page assets:

- `head.html.j2` — CSS/JS tags injected into the rendered page when that section is present
- `nav.md.j2` — extra navigation links for that section

| Package | Key | What it does |
|---|---|---|
| `arxiv/` | `arxiv` | Fetches arXiv papers, LLM-scores and summarises them — [docs](arxiv/README.md) |
| `hacker_news/` | `hacker_news` | Fetches top HN stories above a score threshold — [docs](hacker_news/README.md) |
| `github_trending/` | `github_trending` | Fetches daily trending GitHub repos — [docs](github_trending/README.md) |
| `postdoc_jobs/` | `postdoc_jobs` | Fetches and ranks research job postings — [docs](postdoc_jobs/README.md) |
| `supervisor_updates/` | `supervisor_updates` | Monitors supervisor / lab pages for changes — [docs](supervisor_updates/README.md) |
| `weather/` | `weather` | Fetches today's weather for a configured city — [docs](weather/README.md) |

---

## Extension checklist

Before opening a PR with a new extension:

- [ ] `key` is unique and matches `config/sources.yaml`
- [ ] `fetch()` makes no LLM calls
- [ ] `process()` checks `self.config.get("dry_run")` and skips LLM calls if set
- [ ] `render()` makes no network calls
- [ ] Credentials read from `os.environ` only — never from config files
- [ ] At least one test covering the parsing/filtering logic
- [ ] `PYTHONPATH=. pytest tests/ -q` passes
