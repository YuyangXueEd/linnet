![Linnet](assets/teaser.gif)

# Linnet

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Daily Digest](https://github.com/YuyangXueEd/linnet/actions/workflows/daily.yml/badge.svg)](https://github.com/YuyangXueEd/linnet/actions/workflows/daily.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/YuyangXueEd/linnet/pulls)

[English](README.md)

**你的个人 AI 早报。** arXiv 新论文、Hacker News 热帖、GitHub 趋势、天气，以及可选的其他来源，会在夜里自动抓取、筛选、摘要，并发布成你自己的可搜索 digest 站点。

![Linnet Hero](assets/hero.png)

当你用模板创建好自己的仓库后，第一步就该打开设置向导。它现在就是新的主入口：登录 GitHub、完成授权、填写配置、直接部署，都会在这里走完。当前自托管路径会在背后使用 GitHub Actions 和 Pages；你不用维护服务器，也不会被锁在某个 dashboard 里。

**[在线示例](https://yuyangxueed.github.io/Linnet)** · **[中文设置向导入口](https://yuyangxueed.github.io/Linnet/setup/zh/)** · **[English setup entry](https://yuyangxueed.github.io/Linnet/setup/)** · **[手动配置指南](dev_docs/manual-config.zh.md)**

> **克隆或从模板创建仓库后，先点这里**
> `setup` 页面现在就是新用户的主入口，登录、授权、配置和部署都在这里完成。
> 中文界面：<https://yuyangxueed.github.io/Linnet/setup/zh/>
> English UI: <https://yuyangxueed.github.io/Linnet/setup/>
> 第一次部署完成后，把你的 GitHub Pages 地址填到仓库的 **About -> Website** 里，这样仓库头部就会直接显示站点入口。

---

## 它是怎么工作的

![Linnet Workflow](assets/workflow.png)

Linnet 更像一个替你准备晨间材料的 AI 助手。它会检查你关心的来源，用 LLM 过滤噪音和提炼重点，然后在一天开始前留下一份整理好的 briefing。

---

## 先看成品

### 桌面仪表盘

![Linnet 首页截图](assets/homepage_screenshot.png)

### 每日编辑流

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

Linnet 会把生成的日、周、月归档保留在你的发布站点里，所以这些 briefing 可以持续搜索和回看，而不是变成另一个刷完就消失的信息流。

---

## 最快搭好你的简报

### 1. 用这个模板创建你自己的仓库

在 GitHub 上点击 **Use this template → Create a new repository**。

如果你只是想搭自己的 briefing 站点，优先使用 **Use this template**，不要用 **Fork**。Fork 当然也能跑，但更容易遇到 GitHub 对 Actions 和初始化流程的额外限制。

### 2. 把 Linnet Bridge GitHub App 安装到这个仓库

打开你刚创建的仓库，把 **Linnet Bridge** GitHub App 安装到目标仓库上。

这是现在推荐的新手路径。它让 Linnet 可以直接替你写入文件、GitHub Actions secrets、workflow 设置，以及 GitHub Pages 配置，而不需要你自己去生成 PAT。

### 3. 先打开设置向导

创建好仓库后，这里就是登录、授权和部署的主入口：

- 英文界面：<https://yuyangxueed.github.io/Linnet/setup/>
- 中文界面：<https://yuyangxueed.github.io/Linnet/setup/zh/>

现在已经不需要先把你自己仓库里的 `/setup/` 部署出来，才能开始配置。

### 4. 完成设置向导、授权 GitHub、并直接部署

在设置向导顶部：

- 如果还没安装过，先点 **安装 GitHub App**
- 然后点 **授权 GitHub**，让当前浏览器完成 setup 授权流程

然后照常完成向导里的内容：

- Step 1-2 里的简报模式、来源选择与详细来源配置
- Step 3 里的可选额外 secrets 和推送渠道
- Step 4 里的 LLM provider、API key、模型选择，以及主题设置

到了 Step 5，确认目标仓库后，点击 **部署到 GitHub**。

现在默认的一键部署路径走的是 Linnet Bridge GitHub App，不再是 PAT。部署成功后，Linnet 会在背后完成这些事：

- 以单次 commit 写入生成的配置文件
- 创建或更新所需的 GitHub Actions secrets
- 启用 `daily.yml`、`weekly.yml`、`monthly.yml`、`pages.yml`
- 配置 GitHub Pages 为 workflow 发布模式
- 触发第一次 `Daily Digest`

### 5. 运行第一次工作流

大多数用户在 Step 5 之后不需要再手动点任何按钮。你只要在仓库里观察这两个 workflow：

- **Daily Digest** — 生成第一期 digest，并提交发布数据
- **Deploy Astro Site to GitHub Pages** — 构建站点并发布到 Pages

几分钟后，你的站点应该就会出现在 `https://<你的用户名>.github.io/<仓库名>/`。

这个地址一旦可访问，就把它填到仓库主页的 **About -> Website** 里。这样你和其他访问者打开 GitHub 仓库时，就能立刻看到站点入口。

GitHub Pages 在全新仓库上有时会比 API 成功响应稍慢一点，所以第一次部署时请稍微等一会儿，再判断是否真的失败。如果组织策略阻止了 GitHub App、Actions 或 Pages，再回退到 [手动配置指南](dev_docs/manual-config.zh.md)。

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

## 进阶路径

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

GitHub Actions 的 cron 使用 UTC。如果你想改运行时间，直接在你自己的仓库里改这些 cron。

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

如果你主要是在帮别人配置自己的仓库或 digest 站点，先看：

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

[![Star History Chart](https://api.star-history.com/svg?repos=YuyangXueEd/linnet&type=Date)](https://star-history.com/#YuyangXueEd/linnet&Date)

---

## 许可证

MIT — 详见 [LICENSE](LICENSE)。欢迎贡献。
