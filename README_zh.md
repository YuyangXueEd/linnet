# Linnet

[English](README.md)

**你的个人 AI 早报。** arXiv 新论文、Hacker News 热帖、GitHub 趋势、天气，以及可选的其他来源，会在夜里自动抓取、筛选、摘要，并发布成你自己的可搜索 digest 站点。

Fork 这个仓库，填入一个 API key，用 GitHub Actions 跑起来。不要服务器，不要订阅，也不会把内容锁死在某个平台里。

**[在线示例](https://yuyangxueed.github.io/Linnet)** · **[中文设置向导](https://yuyangxueed.github.io/Linnet/setup/zh/)** · **[Setup Wizard (EN)](https://yuyangxueed.github.io/Linnet/setup/)** · **[手动配置指南](dev_docs/manual-config.zh.md)**

---

## 先看成品

### 首页

![Linnet 首页截图](assets/homepage_screenshot.png)

### Daily digest 页面

![Linnet daily digest 示例](assets/daily.gif)

---

## 每天早上你会收到什么

| 来源 | 作用 |
|---|---|
| **arXiv** | 抓取与你关键词匹配的新论文，并附 AI 摘要 |
| **Hacker News** | 超过你设定分数线的 AI/ML 高信号内容 |
| **GitHub Trending** | 你关心方向的趋势仓库 |
| **天气** | 你所在城市的天气 |

博士后职位、导师主页监控这类来源也能接进来，但它们都放在扩展系统里，不会挤占默认上手路径。

设置向导还会按语言显示不同的每日 tagline 扩展：

- 中文默认可选 `hitokoto`，不需要 API key
- 英文默认可选 `quote_of_day`，需要 `API_NINJAS_KEY`

整个流程跑在 GitHub Actions 上，最后发布到 GitHub Pages，形成你自己的 digest 站点。

---

## 最快上手路径

### 1. 用这个模板创建你自己的仓库

在 GitHub 上点击 **Use this template → Create a new repository**。

如果你走 fork 路径，GitHub 会默认禁用 Actions。请先进入新仓库的 **Actions** 标签页，点击 **"I understand my workflows, go ahead and enable them"**。

如果你使用 Step 6 的 `自动启用 GitHub Actions 和 workflows` 开关，并且 PAT 额外包含 `Administration: Read and write`，设置向导也可以替你完成这一步。

### 2. 选一个 LLM provider，并准备它的 secret

如果你走 wizard 的手动部署路径，需要在 **Settings → Secrets and variables → Actions** 里添加对应 secret。

| Provider 预设 | 默认 secret 名称 | 说明 |
|---|---|---|
| `OpenRouter` | `OPENROUTER_API_KEY` | 默认推荐路径，一个 key 可切多个模型 |
| `OpenAI` | `OPENAI_API_KEY` | 直连 OpenAI |
| `Anthropic compat` | `ANTHROPIC_API_KEY` | 走 OpenAI-compatible endpoint |
| `Gemini compat` | `GEMINI_API_KEY` | 走 OpenAI-compatible endpoint |
| `Custom` | `LLM_API_KEY` | 任意 OpenAI-compatible gateway |

Step 3 里你也可以手动改 secret 名称；Step 6 的手动清单和一键部署会跟着用同一个名字。

### 3. 开启 GitHub Pages

进入 **Settings → Pages → Source: GitHub Actions**。

### 4. 打开设置向导

直接使用 [Setup Wizard](https://yuyangxueed.github.io/Linnet/setup/zh/) 是最短路径。

它会处理：

- 来源选择与顺序调整
- Step 3 里的 LLM provider、API key、模型选择
- 主题与配色
- 可选 sinks
- 适用于你自己 fork 的配置文件
- Step 6 的 `Connect GitHub` 一键部署

如果你想用浏览器里的 `Connect GitHub` 路径，需要先给 Astro 站点配置 `PUBLIC_GITHUB_APP_CLIENT_ID` 和 `PUBLIC_GITHUB_APP_CLIENT_SECRET`。这条路径现在仍然明确标成 experimental，因为这些值会暴露给前端。

### 5. 运行第一次工作流

如果你没有使用 Step 6 的自动启用功能，或者它提示 PAT / 仓库策略有问题，请先在目标仓库里手动启用 GitHub Actions / workflows。

进入 **Actions → Daily Digest → Run workflow**。

几分钟后，你的站点就会发布出来。

---

## 一眼读懂配置

先记住四件事就够了：

1. `enabled: true/false` 控制某个来源或 sink 是否启用。
2. `display_order` 控制最终 digest 里的显示顺序。
3. `llm.provider`、`llm.base_url`、`llm.api_key_env` 和两个 model ID 决定 LLM 请求怎么发。
4. 更细的来源参数在 `config/extensions/<name>.yaml`。

最小例子：

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

language: "zh"

llm:
  provider: "openrouter"
  scoring_model: "google/gemini-2.5-flash-lite-preview-09-2025"
  summarization_model: "google/gemini-2.5-flash-lite-preview-09-2025"
  base_url: "https://openrouter.ai/api/v1"
  api_key_env: "OPENROUTER_API_KEY"
```

如果你打算手改所有配置，直接从 [`dev_docs/manual-config.zh.md`](dev_docs/manual-config.zh.md) 开始。

---

## 默认路径之外还能做什么

### Extensions

- 内置来源插件都在 [`extensions/`](extensions/)
- 统一约定在 [`extensions/README.md`](extensions/README.md)
- 新扩展可以从 [`extensions/_template/`](extensions/_template/) 开始

### Sinks

- 网站是默认输出
- 可选投递渠道在 [`sinks/`](sinks/)
- 共享约定在 [`sinks/README.md`](sinks/README.md)
- secret 只放 GitHub Secrets 或环境变量，不放进提交的 YAML

例如：

```yaml
sinks:
  slack:
    enabled: true
    max_papers: 5
    max_hn: 3
    max_github: 3
```

### 定时任务和时区

- [`.github/workflows/daily.yml`](.github/workflows/daily.yml)
- [`.github/workflows/weekly.yml`](.github/workflows/weekly.yml)
- [`.github/workflows/monthly.yml`](.github/workflows/monthly.yml)

GitHub Actions 的 cron 使用 UTC。如果你想改运行时间，直接在你自己的 fork 里改这些 cron。

---

## 本地运行

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export OPENROUTER_API_KEY=sk-or-...   # 或者换成 llm.api_key_env 对应的名字
python main.py --mode daily
python main.py --dry-run
python main.py --mode weekly
python main.py --mode monthly
```

运行测试：

```bash
PYTHONPATH=. pytest tests/ -q
```

---

## 贡献代码，或让 AI agent 帮你做

这个仓库对人类贡献者和 AI coding agents 都很友好。

如果你要改仓库代码或文档，先看：

- [`llms.txt`](llms.txt)
- [`extensions/llms.txt`](extensions/llms.txt)
- [`sinks/llms.txt`](sinks/llms.txt)
- [`skills/linnet-contributor/SKILL.md`](skills/linnet-contributor/SKILL.md)

如果你主要是在帮别人配置自己的 fork，先看：

- [`dev_docs/manual-config.zh.md`](dev_docs/manual-config.zh.md)
- [`skills/linnet-config-customization/SKILL.md`](skills/linnet-config-customization/SKILL.md)

给 agent 的推荐提示词：

```text
Please read llms.txt, extensions/llms.txt, sinks/llms.txt, and the relevant SKILL.md under skills/ before making changes or suggesting configuration edits.
```

---

## 分享配置，或者来提问题

如果你做出了一个有趣的 setup，欢迎发到 [Discussions](https://github.com/YuyangXueEd/linnet/discussions)。

如果你遇到实现问题、配置问题，或者想提 extension / sink 请求，可以直接使用仓库里的 issue templates。

---

## 支持这个项目

如果这个仓库帮你节省了时间，或者给了你一个很好的个人 briefing workflow 起点，可以在这里支持项目：

- [GitHub Sponsors](https://github.com/sponsors/yuyangxueed)
- [Ko-fi](https://ko-fi.com/guesswhat_moe)

赞助完全自愿。代码贡献、修 bug、提想法、补新集成，同样很有价值。

---

## 致谢

公开站点使用 [Astro](https://astro.build/) 构建，这让 GitHub Pages 这条路径保持得很轻。

这个项目也受益于很多开源仓库、维护者和示例。如果你发现某个项目值得被更明确地致谢，欢迎提 issue 或 PR，我会补上。

---

## 许可证

MIT — 详见 [LICENSE](LICENSE)。欢迎贡献。
