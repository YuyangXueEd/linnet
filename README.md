# MyDailyUpdater

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Daily Digest](https://github.com/YuyangXueEd/MyDailyUpdater/actions/workflows/daily.yml/badge.svg)](https://github.com/YuyangXueEd/MyDailyUpdater/actions/workflows/daily.yml)

[中文文档](README_zh.md)

**Get a personalised research digest every morning — without lifting a finger.**

Fork this repo, add one API key, and wake up to a fresh digest of arXiv papers, Hacker News stories, and trending GitHub repos — automatically filtered for your interests, summarised by AI, and published as your own website.

**[See a live example →](https://yuyangxueed.github.io/MyDailyUpdater)** · **[Setup Wizard →](https://yuyangxueed.github.io/MyDailyUpdater/setup/)**

> **Cost:** about $0.01–$0.05 per day using `gemini-2.5-flash-lite` via OpenRouter (free tier available).

---

## What you get every morning

| Source | What it fetches |
|---|---|
| **arXiv** | New papers matching your keywords — each with an AI-written summary |
| **Hacker News** | Top AI/ML stories above a score you set |
| **GitHub Trending** | Today's most-starred repos in your area |
| **Weather** | Today's forecast for your city |
| **Postdoc jobs** | Research job listings from jobs.ac.uk, FindAPostDoc, and EURAXESS |
| **Supervisor monitor** | Alerts when a professor's or lab's webpage changes |

Everything runs automatically at midnight UTC via GitHub Actions. Results are saved back to your repo and published as a searchable website.

---

## Set it up in 5 steps

### Step 1 — Copy this repo to your account

Click **Fork** at the top of this page. GitHub will create your own copy. All the automation comes with it.

### Step 2 — Add your API key

In your forked repo, go to: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `OPENROUTER_API_KEY` | Your key from [openrouter.ai/keys](https://openrouter.ai/keys) — free tier works, starts with `sk-or-...` |

This is the only credential you need. [OpenRouter](https://openrouter.ai) lets you call many AI models (Gemini, GPT, Claude) with one key and switch between them any time.

### Step 3 — Turn on your website

Go to: **Settings → Pages → Source: Deploy from a branch → Branch: `main`, folder: `/docs`**

Click **Save**. Your site URL will appear there — it looks like `https://YOUR-USERNAME.github.io/MyDailyUpdater`.

### Step 4 — Pick your research topics

Open [config/extensions/arxiv.yaml](config/extensions/arxiv.yaml). It has four ready-made profiles — uncomment the one closest to your work and edit the keywords freely:

```yaml
# PROFILE A: AI / ML / LLM (general)
# categories: [cs.AI, cs.LG, cs.CL, cs.CV, stat.ML]
# must_include:
#   - large language model
#   - foundation model
#   ...

# PROFILE B: Robotics / Embodied AI
# PROFILE C: Medical AI / Clinical NLP
# PROFILE D: NLP / Text / Reasoning
```

Uncomment one profile by removing the `#` from each line, then edit as needed.

Want summaries in a different language? Open [config/sources.yaml](config/sources.yaml) and change `language: "en"` to `"zh"`, `"fr"`, `"de"`, `"ja"`, `"ko"`, `"es"`, or any other language code.

### Step 5 — Run it for the first time

Go to: **Actions → Daily Digest → Run workflow → Run workflow**

Your site will be live in about 5 minutes.

---

## Turn sources on and off

Open [config/sources.yaml](config/sources.yaml) and set `enabled: true` or `enabled: false` for each source:

```yaml
arxiv:
  enabled: true          # arXiv papers — the main event

hacker_news:
  enabled: true          # top Hacker News stories

github_trending:
  enabled: true          # today's trending GitHub repos
  max_repos: 15

weather:
  enabled: true
  city: "Edinburgh"      # change to your city

postdoc_jobs:
  enabled: false         # academic job listings — turn on if you want these

supervisor_updates:
  enabled: false         # professor/lab page monitor — turn on if you want these
```

You can also switch AI models here, or cap how many papers get fetched per day.

---

## Get your digest in Slack

In addition to the website, you can receive a daily Slack message. Setup takes about 2 minutes:

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Left sidebar → **Features → Incoming Webhooks** → toggle **On**
3. Scroll down → **Add New Webhook to Workspace** → choose your channel → **Allow**
4. Copy the webhook URL (looks like `https://hooks.slack.com/services/T.../B.../...`)
5. Add it as a secret in your repo: **Settings → Secrets → New secret**, name it `SLACK_WEBHOOK_URL`
6. Enable it in [config/sources.yaml](config/sources.yaml):

```yaml
sinks:
  slack:
    enabled: true
    max_papers: 5    # how many papers to include
    max_hn: 3        # how many HN stories to include
    max_github: 3    # how many trending repos to include
```

If you skip this step, nothing breaks — the website still updates as normal.

---

## What runs on its own

| When | What happens |
|---|---|
| Every day at midnight UTC | Full digest — papers, HN, GitHub trending, weather, any extras you enabled |
| Every Monday at 1 AM UTC | Weekly summary of the past week |
| 1st of every month at 2 AM UTC | Monthly overview |

You can also trigger any of these by hand: **Actions → [workflow name] → Run workflow**.

---

## Add your own data source

Every source is a self-contained folder inside `extensions/`. To add a new one:

**1. Copy the template:**
```bash
cp -r extensions/_template extensions/my_source
```

**2. Fill in three functions** in `extensions/my_source/__init__.py`:
- `fetch()` — grab raw data from anywhere (a website, an API, a file)
- `process()` — optional: filter or summarise using the built-in AI client
- `render()` — format the results for the digest

**3. Register it** in `extensions/__init__.py`:
```python
from extensions.my_source import MySourceExtension

REGISTRY = [..., MySourceExtension]
```

**4. Add an on/off switch** in `config/sources.yaml`:
```yaml
my_source:
  enabled: true
```

Full guide with a worked example: [extensions/README.md](extensions/README.md)

---

## Running on your own computer

```bash
# Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set your API key
export OPENROUTER_API_KEY=sk-or-...

# Run a full digest
python main.py --mode daily

# Test without any AI calls (free — good for checking your config works)
python main.py --dry-run

# Weekly or monthly summary
python main.py --mode weekly
python main.py --mode monthly
```

Run the test suite:
```bash
PYTHONPATH=. pytest tests/ -q
```

---

## Project layout

```
MyDailyUpdater/
├── extensions/             # one folder per data source
│   ├── _template/          # copy this to build your own source
│   ├── arxiv/              # arXiv papers
│   ├── github_trending/    # GitHub trending repos
│   ├── hacker_news/        # Hacker News stories
│   ├── postdoc_jobs/       # academic job listings
│   ├── supervisor_updates/ # professor/lab page monitor
│   ├── weather/            # weather forecast
│   └── base.py             # shared base class all extensions inherit from
├── sinks/                  # delivery channels (e.g. Slack)
│   └── slack/
├── pipeline/               # scoring, summarising, assembling the digest
├── publishers/             # writes the website files to docs/
├── templates/              # daily / weekly / monthly page layouts
├── config/
│   ├── sources.yaml        # turn sources on/off, set language & AI models
│   └── extensions/
│       ├── arxiv.yaml      # your research keywords & categories
│       ├── hacker_news.yaml
│       ├── postdoc_jobs.yaml
│       └── supervisor_updates.yaml
├── docs/                   # your generated website (served by GitHub Pages)
├── tests/
└── main.py                 # entry point
```

---

## Share your setup

Using this for an unusual research area? Set up a particularly useful config? Post it in [Discussions](https://github.com/YuyangXueEd/MyDailyUpdater/discussions) — others with similar interests will find it.

Have a bug or want a new source added? [Open an issue](https://github.com/YuyangXueEd/MyDailyUpdater/issues).

---

## License

MIT — see [LICENSE](LICENSE). Contributions welcome.
