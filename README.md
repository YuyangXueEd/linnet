![Linnet](assets/logo-wide.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Daily Digest](https://github.com/YuyangXueEd/linnet/actions/workflows/daily.yml/badge.svg)](https://github.com/YuyangXueEd/linnet/actions/workflows/daily.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/YuyangXueEd/linnet/pulls)

[中文文档](README_zh.md)

**Your personal AI morning briefing.** arXiv papers, Hacker News stories, GitHub trends, weather, and optional extras are collected overnight, summarised for you, and published as your own searchable digest site.

![Linnet Hero](assets/hero.png)

Fork the repo, add one API key, and run it on GitHub Actions. No server, no subscription, no dashboard lock-in.

**[Live example](https://yuyangxueed.github.io/Linnet)** · **[Setup Wizard (EN)](https://yuyangxueed.github.io/Linnet/setup/)** · **[设置向导 (中文)](https://yuyangxueed.github.io/Linnet/setup/zh/)** · **[Manual config guide](dev_docs/manual-config.md)**

---

---

## How it works

![Linnet Workflow](assets/workflow.png)

Linnet is a modular pipeline designed to automate the knowledge-gathering habits of researchers and engineers. It scouts your preferred sources, uses an LLM to distill the signal from the noise, and delivers a polished briefing to your chosen sinks.

---

## See the product first

### Desktop Dashboard
![Linnet homepage screenshot](assets/homepage_screenshot.png)

### Daily Editorial Feed
![Linnet daily digest example](assets/daily.gif)

---

## What you get every morning

| Source | What it gives you |
|---|---|
| **arXiv** | New papers matching your keywords, with AI summaries |
| **Hacker News** | High-signal AI/ML stories above your score threshold |
| **GitHub Trending** | Trending repos in your area |
| **Weather** | Today's forecast for your city |

Optional sources such as postdoc jobs and supervisor-page monitoring live behind the extension system, but most users do not need them on day one.

The setup wizard also exposes language-specific tagline extensions:

- `hitokoto` for Chinese briefings, no key required
- `quote_of_day` for English briefings, requires `API_NINJAS_KEY`

Everything runs on GitHub Actions and publishes to GitHub Pages as your own site.

---

## Fastest path to your own digest

### 1. Create your own repo from this template

Use **Use this template → Create a new repository** on GitHub.

If you fork instead, GitHub disables Actions by default. Open the **Actions** tab in your new repo and click **"I understand my workflows, go ahead and enable them"** before you continue.

### 2. Pick an LLM provider and add its secret

If you use the wizard's manual path, add the secret in **Settings → Secrets and variables → Actions**.

| Provider preset | Default secret name | Notes |
|---|---|---|
| `OpenRouter` | `OPENROUTER_API_KEY` | Recommended fast path, one key for many models |
| `OpenAI` | `OPENAI_API_KEY` | Direct OpenAI endpoint |
| `Anthropic compat` | `ANTHROPIC_API_KEY` | OpenAI-compatible endpoint |
| `Gemini compat` | `GEMINI_API_KEY` | OpenAI-compatible endpoint |
| `Custom` | `LLM_API_KEY` | Any OpenAI-compatible gateway |

Step 3 of the wizard lets you change the secret name if you want a different convention. Step 6 will then use that same name for both the manual checklist and one-click deploy.

### 3. Enable GitHub Pages

Go to **Settings → Pages → Source: GitHub Actions**.

### 4. Open the setup wizard

Use the [Setup Wizard](https://yuyangxueed.github.io/Linnet/setup/) for the shortest path.

It handles:

- source selection and ordering
- LLM provider, API key, and model choices in Step 3
- theme and palette choices
- optional sinks
- generated files for your own fork
- optional `Connect GitHub` one-click deploy in Step 6

For the `Connect GitHub` one-click deploy path, you need a GitHub Personal Access Token with the right permissions:

**Fine-grained PAT (recommended)**

| Permission | Level |
|---|---|
| Actions | Read and write |
| Contents | Read and write |
| Metadata | Read-only (auto-selected) |
| Secrets | Read and write |

Set **Repository access** to **Only select repositories** and pick your fork — do not use "All repositories".

**Classic PAT** — check `repo` (all sub-scopes) and `workflow`.

The wizard's **Instructions** link walks through every field step by step.

> If the deploy step fails with `Resource not accessible by personal access token`, the token is missing one of the permissions above — regenerate it with the correct scopes.

### 5. Run the first workflow

Open **Actions → Daily Digest → Run workflow**.

Your site should be live a few minutes later.

---

## Config mental model

The repo stays simple if you remember four things:

1. `enabled: true/false` turns each source or sink on and off.
2. `display_order` controls the section order in the final digest.
3. `llm.provider`, `llm.base_url`, `llm.api_key_env`, and the two model IDs define how LLM calls are made.
4. Detailed per-source settings live in `config/extensions/<name>.yaml`.

Minimal example:

```yaml
display_order:
  - weather
  - arxiv
  - github_trending
  - hacker_news

weather:
  enabled: true

arxiv:
  enabled: true

github_trending:
  enabled: true

hacker_news:
  enabled: true

language: "en"

llm:
  provider: "openrouter"
  scoring_model: "google/gemini-2.5-flash-lite-preview-09-2025"
  summarization_model: "google/gemini-2.5-flash-lite-preview-09-2025"
  base_url: "https://openrouter.ai/api/v1"
  api_key_env: "OPENROUTER_API_KEY"
```

If you want to hand-edit everything, start from [`dev_docs/manual-config.md`](dev_docs/manual-config.md).

---

## Need more than the default setup?

### Extensions

- Built-in source plugins live in [`extensions/`](extensions/)
- Shared conventions live in [`extensions/README.md`](extensions/README.md)
- New extensions can start from [`extensions/_template/`](extensions/_template/)

### Sinks

- The website is the default output
- Optional delivery channels live in [`sinks/`](sinks/)
- Shared sink conventions live in [`sinks/README.md`](sinks/README.md)
- Secrets stay in GitHub Secrets or environment variables, not committed YAML

Example:

```yaml
sinks:
  slack:
    enabled: true
    max_papers: 5
    max_hn: 3
    max_github: 3
```

### Schedules and timezones

- [`.github/workflows/daily.yml`](.github/workflows/daily.yml)
- [`.github/workflows/weekly.yml`](.github/workflows/weekly.yml)
- [`.github/workflows/monthly.yml`](.github/workflows/monthly.yml)

GitHub Actions cron uses UTC. Edit those cron lines directly in your fork if you want different times.

---

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export OPENROUTER_API_KEY=sk-or-...   # or another env name that matches llm.api_key_env
python main.py --mode daily
python main.py --dry-run
python main.py --mode weekly
python main.py --mode monthly
```

Run tests:

```bash
PYTHONPATH=. pytest tests/ -q
```

---

## Contributing or using AI agents

This repo is friendly to both human contributors and AI coding agents.

If you are modifying repo code or docs, start with:

- [`llms.txt`](llms.txt)
- [`extensions/llms.txt`](extensions/llms.txt)
- [`sinks/llms.txt`](sinks/llms.txt)
- [`skills/linnet-contributor/SKILL.md`](skills/linnet-contributor/SKILL.md)

If you are mostly helping someone configure their own fork, start with:

- [`dev_docs/manual-config.md`](dev_docs/manual-config.md)
- [`skills/linnet-config-customization/SKILL.md`](skills/linnet-config-customization/SKILL.md)

Suggested prompt for agents:

```text
Please read llms.txt, extensions/llms.txt, sinks/llms.txt, and the relevant SKILL.md under skills/ before making changes or suggesting configuration edits.
```

---

## Share setups and ask for help

If you build an interesting setup, please share it in [Discussions](https://github.com/YuyangXueEd/linnet/discussions).

For implementation problems, config help, extension ideas, or sink requests, use the repo's issue templates.

---

## Support the project

If this repo saves you time, helps you track your field, or gives you a strong starting point for your own briefing workflow, you can support it here:

- [GitHub Sponsors](https://github.com/sponsors/yuyangxueed)
- [Ko-fi](https://ko-fi.com/guesswhat_moe)

Support is optional. Contributions, fixes, ideas, and new integrations are just as valuable.

---

## Acknowledgements

The public site is built with [Astro](https://astro.build/), which makes the GitHub Pages flow pleasantly simple.

This project also benefited from many open-source repositories, maintainers, and examples. If you notice a project that should be credited more explicitly, open an issue or PR and I will gladly add it.

[![Star History Chart](https://api.star-history.com/svg?repos=YuyangXueEd/linnet&type=Date)](https://star-history.com/#YuyangXueEd/linnet&Date)

---

## License

MIT — see [LICENSE](LICENSE). Contributions welcome.
