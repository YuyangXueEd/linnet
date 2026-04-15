---
title: Manual Configuration
nav_order: 2
parent: Setup
---

# Manual Configuration

Prefer to configure everything by hand? This page walks through every step.
If you'd rather use the interactive wizard, go to the [Setup Wizard](index.html) instead.

---

## Step 1 — Fork this repo

Click **Fork** at the top of the [GitHub page](https://github.com/YuyangXueEd/MyDailyUpdater).
GitHub will create your own copy with all the automation included.

---

## Step 2 — Add your API key

In your forked repo go to: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `OPENROUTER_API_KEY` | Your key from [openrouter.ai/keys](https://openrouter.ai/keys) — free tier works, starts with `sk-or-...` |

This is the only required credential. [OpenRouter](https://openrouter.ai) lets you call many AI models
(Gemini, GPT, Claude) with one key and switch between them any time.

---

## Step 3 — Enable GitHub Pages

Go to: **Settings → Pages → Source: Deploy from a branch → Branch: `main`, folder: `/docs`**

Click **Save**. Your site URL will appear there — it looks like `https://YOUR-USERNAME.github.io/MyDailyUpdater`.

---

## Step 4 — Pick your research topics

Open [config/extensions/arxiv.yaml](../../config/extensions/arxiv.yaml). It has four ready-made profiles —
uncomment the one closest to your work and edit the keywords freely:

```yaml
# PROFILE A: AI / ML / LLM (general)
# categories: [cs.AI, cs.LG, cs.CL, cs.CV, stat.ML]
# must_include:
#   - large language model
#   - foundation model

# PROFILE B: Robotics / Embodied AI
# PROFILE C: Medical AI / Clinical NLP
# PROFILE D: NLP / Text / Reasoning
```

Want summaries in a different language? Open [config/sources.yaml](../../config/sources.yaml) and
change `language: "en"` to `"zh"`, `"fr"`, `"de"`, `"ja"`, `"ko"`, `"es"`, or any other language code.

---

## Step 5 — Run it for the first time

Go to: **Actions → Daily Digest → Run workflow → Run workflow**

Your site will be live in about 5 minutes.

---

## Turn sources on and off

Open [config/sources.yaml](../../config/sources.yaml) and set `enabled: true` or `enabled: false`
for each source:

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

## Customise LLM prompts

Every summarisation and scoring prompt can be overridden in `config/sources.yaml` under the `llm.prompts:` block.
The commented-out defaults are already in that file — uncomment and edit any you want to change:

```yaml
llm:
  summarization_model: "google/gemini-2.5-flash-lite-preview-09-2025"
  # prompts:
  #   arxiv_summary: |
  #     Summarize the core method and contribution of the following paper
  #     {lang}, in 2-3 sentences (≤100 words):
  #     Title: {title}
  #     Abstract: {abstract}
  #   hacker_news_summary: |
  #     Summarize the core content of the following tech news story
  #     {lang}, in one sentence (≤50 words):
  #     Title: {title}
  #     URL: {url}
```

Available placeholders per prompt:

| Prompt key | Placeholders |
|---|---|
| `arxiv_score` | `{title}`, `{abstract}` |
| `arxiv_summary` | `{title}`, `{abstract}`, `{lang}` |
| `hacker_news_summary` | `{title}`, `{url}`, `{lang}` |
| `github_summary` | `{full_name}`, `{description}`, `{lang}` |

---

## Get your digest in Slack

In addition to the website, you can receive a daily Slack message:

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Left sidebar → **Features → Incoming Webhooks** → toggle **On**
3. Scroll down → **Add New Webhook to Workspace** → choose your channel → **Allow**
4. Copy the webhook URL (looks like `https://hooks.slack.com/services/T.../B.../...`)
5. Add it as a secret: **Settings → Secrets → New secret**, name it `SLACK_WEBHOOK_URL`
6. Enable it in [config/sources.yaml](../../config/sources.yaml):

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

## What runs automatically

| When | What happens |
|---|---|
| Every day at midnight UTC | Full digest — papers, HN, GitHub trending, weather, any extras you enabled |
| Every Monday at 1 AM UTC | Weekly summary of the past week |
| 1st of every month at 2 AM UTC | Monthly overview |

You can also trigger any of these by hand: **Actions → [workflow name] → Run workflow**.
