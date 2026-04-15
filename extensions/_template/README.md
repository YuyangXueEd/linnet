# _template extension

Starter template for building a new MyDailyUpdater extension.

## How to use this template

```bash
# 1. Copy the whole directory
cp -r extensions/_template extensions/my_source

# 2. Rename the class and fill in the three methods
#    Open extensions/my_source/__init__.py

# 3. Update this README to document your extension

# 4. Register and configure — see extensions/README.md for full steps
```

## What to fill in

| Method | Rules |
|---|---|
| `fetch()` | Pull raw data. No LLM calls. Read credentials from `os.environ` only. |
| `process()` | LLM scoring / summarising. Always check `self.config.get("dry_run")` first. |
| `render()` | Wrap items in `FeedSection`. No network or LLM calls. |

## Optional page assets

This template also includes two optional files you can keep, edit, or delete:

| File | When to use it |
|---|---|
| `head.html.j2` | Add per-extension CSS / JS / `<link>` / `<script>` tags when the section is present |
| `nav.md.j2` | Add extra links under the section in the daily quick-nav |

They are both safe to remove if your extension does not need them.

Useful template context in these files usually includes:
- `sec` — the current `FeedSection`
- `date` — current daily digest date
- `meta` — top-level pipeline metadata
- `generated_at` — render timestamp
- payload keys such as `papers`, `jobs`, `hacker_news`, depending on enabled sections

## Template README structure

Once your extension is working, update this README with:

- What it does (one paragraph)
- Pipeline diagram (`fetch → process → render`)
- Config table (sources.yaml + extensions/{name}.yaml keys, defaults, notes)
- Output item schema (field names and types)
- Underlying collectors / external APIs used
- Test command

See `extensions/arxiv/README.md` for a complete example.
