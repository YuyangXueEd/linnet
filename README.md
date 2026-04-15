# MyDailyUpdater

A self-hosted, extensible daily digest pipeline. Every day it fetches papers, news, jobs, and trending repos from multiple sources, scores and summarises them with an LLM, and publishes a searchable static site via GitHub Pages.

**[Live demo →](https://yuyangxueed.github.io/MyDailyUpdater)**

---

## What it does

| Source | What you get |
|---|---|
| **arXiv** | Papers filtered by category and keyword, LLM-scored for relevance, summarised with figure previews |
| **Hacker News** | Top AI/ML stories above a configurable score threshold |
| **Academic Jobs** | Postdoc and research positions from jobs.ac.uk, FindAPostDoc, EURAXESS, and more |
| **GitHub Trending** | Daily trending AI/ML repositories |
| **Supervisor Watcher** | Change-detection on advisor / lab pages you care about |

Runs automatically at midnight UTC via GitHub Actions. Output is committed back to the repo and served as a Jekyll site (Just the Docs theme).

---

## Quick start

### 1. Fork this repo

Click **Fork** on GitHub. All GitHub Actions workflows and Pages config are included.

### 2. Add your API key

In your fork: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `OPENROUTER_API_KEY` | Your [OpenRouter](https://openrouter.ai) API key |

The pipeline uses OpenRouter so you can swap models freely in `config/sources.yaml`.

### 3. Enable GitHub Pages

**Settings → Pages → Source: Deploy from a branch → Branch: `main` / `docs/`**

### 4. Customise your interests

Edit `config/keywords.yaml` to set your arXiv categories, keywords, and score thresholds.  
Edit `config/sources.yaml` to enable/disable sources, choose a language, and pick LLM models.

### 5. Trigger the first run

**Actions → Daily Digest → Run workflow** — the site will be live within ~5 minutes.

---

## Configuration

### `config/sources.yaml`

```yaml
# Output language for all summaries.
# "en" (default) | "zh" | "fr" | "de" | "ja" | "ko" | "es" | "pt"
# Any BCP-47 language code works — the LLM responds in that language directly.
language: "en"

arxiv:
  enabled: true
  max_papers_per_run: 300

hacker_news:
  enabled: true

jobs:
  enabled: true

supervisor_monitoring:
  enabled: true

github_trending:
  enabled: true
  max_repos: 15

llm:
  scoring_model: "google/gemini-2.5-flash-lite-preview-09-2025"
  summarization_model: "google/gemini-2.5-flash-lite-preview-09-2025"
  base_url: "https://openrouter.ai/api/v1"
```

### `config/keywords.yaml`

Controls arXiv filters, HN keyword matching, job filters, and LLM score thresholds. See the file for the full schema with inline comments.

### `config/supervisors.yaml`

List of supervisor / lab pages to watch for changes:

```yaml
supervisors:
  - name: "Ada Lovelace"
    institution: "University of Example"
    url: "https://example.ac.uk/~lovelace"
```

---

## Extension system

Every data source is a self-contained **extension** (`extensions/`). An extension owns its full pipeline: fetch → process (score + summarise) → render a `FeedSection`.

### Adding a new source

1. Create `extensions/my_source.py`:

```python
from extensions.base import BaseExtension, FeedSection

class MySourceExtension(BaseExtension):
    key = "my_source"       # must match your config/sources.yaml key
    title = "My Source"

    def fetch(self) -> list[dict]:
        # pull raw items from your data source
        ...

    def process(self, items: list[dict]) -> list[dict]:
        # optional: score, filter, summarise
        # self.llm   — OpenAI-compatible LLM client
        # self.config — your config slice (includes language, model names)
        return items

    def render(self, items: list[dict]) -> FeedSection:
        return FeedSection(key=self.key, title=self.title, items=items)
```

2. Register it in `extensions/__init__.py`:

```python
from extensions.my_source import MySourceExtension

REGISTRY = [
    ...,
    MySourceExtension,
]
```

3. Add a config block in `config/sources.yaml`:

```yaml
my_source:
  enabled: true
  # your extension-specific options here
```

The orchestrator will call `ext.run()` automatically on the next pipeline run.

---

## Running locally

```bash
# Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set your API key
export OPENROUTER_API_KEY=sk-or-...

# Run the daily pipeline
python main.py --mode daily

# Weekly / monthly rollup
python main.py --mode weekly
python main.py --mode monthly

# Quick status check (used by the Claude Code SessionStart hook)
python main.py --check-today

# Run tests
PYTHONPATH=. pytest tests/ -q
```

---

## Project structure

```
MyDailyUpdater/
├── extensions/          # pluggable data source extensions
│   ├── base.py          # BaseExtension + FeedSection
│   ├── arxiv.py
│   ├── hacker_news.py
│   ├── jobs.py
│   ├── supervisor.py
│   └── github_trending.py
├── collectors/          # low-level fetch functions (used by extensions)
├── pipeline/            # scorer, summariser, aggregator, config loader
├── publishers/          # JSON writer + Jinja2 → Markdown renderer
├── templates/           # daily / weekly / monthly Jinja2 templates
├── config/
│   ├── sources.yaml     # enable/disable sources, language, LLM models
│   ├── keywords.yaml    # filters, thresholds, categories
│   └── supervisors.yaml # supervisor pages to watch
├── docs/                # generated site (served by GitHub Pages)
├── tests/
└── main.py              # CLI entry point + pipeline orchestrator
```

---

## Scheduled workflows

| Workflow | Schedule | What it does |
|---|---|---|
| `daily.yml` | UTC 00:00 daily | Full pipeline, commits output to `docs/` |
| `weekly.yml` | UTC 01:00 Monday | Weekly rollup summary |
| `monthly.yml` | UTC 02:00 1st of month | Monthly trend overview |

All workflows can also be triggered manually via **Actions → Run workflow**.

---

## License

MIT License — see [LICENSE](LICENSE).

Contributions welcome. If you build a new extension, feel free to open a PR or share it in Issues.
