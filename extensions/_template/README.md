# _template extension

Starter template for building a new MyDailyUpdater extension.  
Copy this package, fill in the blanks, and follow the checklist below.

---

## How to use this template

```bash
# 1. Copy the whole package directory
cp -r extensions/_template extensions/my_source

# 2. Rename the class and set key / title / icon
#    Open extensions/my_source/__init__.py

# 3. Implement fetch(), process(), render()
#    Put all HTTP logic in collector.py (keeps it unit-testable)

# 4. Update THIS README to document your extension (see required sections below)

# 5. Register and configure — follow extensions/README.md checklist
```

---

## Required sections for every extension README

Once your extension is working, replace this file with a README that covers
all six sections below.  Use `extensions/arxiv/README.md` as a reference.

### 1. What it does

One short paragraph: what data source does it connect to, what does it
produce, and why is it useful in the daily digest?

### 2. Pipeline

```
fetch()    — describe what is fetched and from where
           → mention any pre-filtering done here
process()  — describe scoring / summarisation (if any)
           → mention LLM calls and what fields they fill
render()   — describe sort order and output structure
```

### 3. Config

Document every config key your extension reads.  Split into two tables:

**`config/sources.yaml`** (source-level on/off and limits):

| Key | Default | Notes |
|---|---|---|
| `enabled` | `true` | Set to `false` to skip this extension entirely |
| `max_items` | `20` | Maximum items returned by fetch() |

**`config/extensions/my_source.yaml`** (filter and keyword config, if used):

| Key | Default | Notes |
|---|---|---|
| `keywords` | `[]` | At least one must match title or description |
| `llm_score_threshold` | `7` | Items scoring below this (0–10) are dropped |

If your extension uses no separate YAML file, remove the second table.

### 4. Output item schema

List every field the Jinja2 template can access on each item.  
Mark optional fields with `| None`.

```python
{
    "id":          str,          # unique identifier
    "title":       str,          # display title
    "url":         str,          # canonical link
    "description": str | None,   # raw text (pre-summarisation)
    "summary":     str | None,   # LLM-generated summary (set by process())
    "score":       float | None, # LLM relevance score 0–10 (set by process())
}
```

### 5. Credentials

List every environment variable / GitHub secret your extension reads.

| Variable | Required | How to get it |
|---|---|---|
| `MY_SOURCE_API_KEY` | Optional | Sign up at example.com → Settings → API Keys |

If the extension needs no credentials, write "None — no authentication required."

### 6. Tests

```bash
# Run extension-specific tests
PYTHONPATH=. pytest tests/test_my_source.py -v

# Smoke test: fetch real data, skip all LLM calls (no API cost)
python main.py --dry-run
```

---

## Optional page assets

Place these files in your extension package if needed:

| File | Purpose |
|---|---|
| `head.html.j2` | CSS/JS tags injected into the rendered page when this section is present (e.g. KaTeX for maths) |
| `nav.md.j2` | Extra navigation links rendered for this section |

---

## Extension checklist

Copy this to your PR description and tick each item before merging:

- [ ] `key` is unique and matches `config/sources.yaml` exactly
- [ ] `fetch()` makes no LLM calls
- [ ] `process()` checks `self.config.get("dry_run")` and skips LLM calls when set
- [ ] `render()` makes no network or LLM calls
- [ ] Credentials read from `os.environ` only — never from config files
- [ ] `config/sources.yaml` updated with `enabled:` block and `display_order` entry
- [ ] `config/extensions/my_source.yaml` created (if extension uses one)
- [ ] `extensions/__init__.py` updated with `REGISTRY` entry
- [ ] `tests/test_my_source.py` created — covers fetch parsing with a fixture
- [ ] `PYTHONPATH=. pytest tests/ -q` passes
- [ ] This README updated with all six sections above
