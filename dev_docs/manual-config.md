# Manual Configuration Guide

> 🌐 **Language / 语言**: **English** · [中文](manual-config.zh.md)

Prefer to configure everything by hand? This page walks through every step.
If you'd rather use the interactive wizard, open the [Setup Wizard](https://yuyangxueed.github.io/Linnet/setup/) instead.

---

## Step 1 — Fork this repo

Click **Fork** at the top of the [GitHub page](https://github.com/YuyangXueEd/Linnet).
GitHub will create your own copy with all the automation included.

### Optional: one-click deploy via the Setup Wizard

The [Setup Wizard](https://yuyangxueed.github.io/Linnet/setup/) can write config files and secrets directly into your fork. For that you need a GitHub Personal Access Token (PAT) with the following permissions:

**Fine-grained PAT (recommended)**

| Permission | Level |
|---|---|
| Actions | Read and write |
| Administration | Read and write only if you want Step 6 to auto-enable Actions / workflows |
| Contents | Read and write |
| Metadata | Read-only (auto-selected) |
| Secrets | Read and write |

Set **Repository access** to **Only select repositories** and pick your fork — do not choose "All repositories".

**Classic PAT** — check `repo` (all sub-scopes) and `workflow`.

If you turn on the Step 6 `Auto-enable GitHub Actions and workflows` switch in the Setup Wizard, the PAT also needs `Administration: Read and write`. If you skip that switch, you will enable Actions manually below.

> If the deploy step fails with `Resource not accessible by personal access token`, the token is missing one of the permissions above — regenerate it with the correct scopes.

---

## Step 2 — Add your API key

In your forked repo go to: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `OPENROUTER_API_KEY` | Your key from [openrouter.ai/keys](https://openrouter.ai/keys) — free tier works, starts with `sk-or-...` |

This is the default fast-path credential. [OpenRouter](https://openrouter.ai) lets you call many AI models
(Gemini, GPT, Claude) with one key and switch between them any time.

> 💰 **Cost estimate**: With the default model (`google/gemini-2.5-flash-lite`), **one full daily digest run costs roughly $0.1 USD**. At one run per day, that's **under $3 USD / month**. Actual spend varies with the sources you enable, how many papers get fetched, and the summary language — you can watch per-call costs live on the [OpenRouter dashboard](https://openrouter.ai/activity). If you want to spend less, swap `scoring_model` / `summarization_model` in `config/sources.yaml` for a cheaper model, or lower the daily paper cap in `config/extensions/arxiv.yaml`.

If you prefer a different OpenAI-compatible provider, set these fields in [`config/sources.yaml`](../config/sources.yaml):

```yaml
llm:
  provider: "openai"
  base_url: "https://api.openai.com/v1"
  api_key_env: "OPENAI_API_KEY"
  scoring_model: "gpt-5-mini"
  summarization_model: "gpt-5-mini"
```

Then export or store the matching secret name instead:

```bash
export OPENAI_API_KEY=sk-...
```

---

## Step 3 — Enable GitHub Pages

Go to: **Settings → Pages → Source: GitHub Actions**

Click **Save**. Your site URL will appear there — it looks like `https://YOUR-USERNAME.github.io/Linnet`.

---

## Step 4 — Pick your research topics

Open [`config/extensions/arxiv.yaml`](../config/extensions/arxiv.yaml). It has four ready-made profiles —
uncomment the one closest to your work and edit the keywords freely:

```yaml
# PROFILE A: AI / ML / LLM (general)
# categories: [cs.AI, cs.LG, cs.CL, cs.CV, stat.ML]
# must_include:
#   - large language model
#   - foundation model

# PROFILE B: Astrophysics / Space Science
# PROFILE C: Chemistry / Materials Science
# PROFILE D: Computational Biology / Bioinformatics
```

Want summaries in a different language? Open [`config/sources.yaml`](../config/sources.yaml) and
change `language: "en"` to `"zh"`, `"fr"`, `"de"`, `"ja"`, `"ko"`, `"es"`, or any other language code.

---

## Step 5 — Run it for the first time

If this is a fork, or if GitHub Actions / workflows are currently disabled, enable them manually in the repo first unless you already used the Setup Wizard’s Step 6 auto-enable option successfully.

You need to manually trigger **two** workflows in order:

1. **Generate the digest content**: Go to **Actions → Daily Digest → Run workflow → Run workflow** and wait for it to finish (about 3–5 minutes). This calls the LLM, builds today's digest, and commits it into `docs/`.
2. **Deploy the site to GitHub Pages**: Go to **Actions → Deploy Astro Site to GitHub Pages → Run workflow → Run workflow** and wait for it to finish (about 1–2 minutes). This builds the Astro site and publishes it.

> 💡 From then on, `Daily Digest` runs automatically every day and auto-triggers the deploy on success — so you only need to click these two buttons **the first time**.

Once both are green, your site is live at `https://<your-username>.github.io/<repo-name>/`.

---

## Turn sources on and off

Open [`config/sources.yaml`](../config/sources.yaml) and set `enabled: true` or `enabled: false`
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

quote_of_day:
  enabled: false         # daily quote as briefing tagline (English, requires API_NINJAS_KEY)

hitokoto:
  enabled: false         # 一言 daily quote as briefing tagline (Chinese, no key needed)
```

You can also switch AI models here, set `llm.provider`, point `llm.base_url` at another OpenAI-compatible provider, change `llm.api_key_env`, or cap how many papers get fetched per day.

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

## Get your digest in ServerChan

If you want a lighter notification path, especially for Chinese-language workflows, ServerChan is a good fit:

1. Open [sct.ftqq.com/sendkey](https://sct.ftqq.com/sendkey)
2. Copy your SendKey
3. Add it as a secret: **Settings → Secrets and variables → Actions → New repository secret**, name it `SERVERCHAN_SENDKEY`
4. Enable it in [`config/sources.yaml`](../config/sources.yaml):

```yaml
sinks:
  serverchan:
    enabled: true
    max_papers: 5
    max_hn: 3
    max_github: 3
    max_jobs: 3
```

This keeps the key out of YAML and out of version control.

---

## Get your digest in Slack

In addition to the website, you can receive a daily Slack message:

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Left sidebar → **Features → Incoming Webhooks** → toggle **On**
3. Scroll down → **Add New Webhook to Workspace** → choose your channel → **Allow**
4. Copy the webhook URL (looks like `https://hooks.slack.com/services/T.../B.../...`)
5. Add it as a secret: **Settings → Secrets and variables → Actions → New repository secret**, name it `SLACK_WEBHOOK_URL`
6. Enable it in [`config/sources.yaml`](../config/sources.yaml):

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
