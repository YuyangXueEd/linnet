# Linnet

[English](README.md)

**你的个人 AI 早报——arXiv 新论文、HN 热帖、GitHub 趋势，过夜自动摘要，醒来就能读。**

Fork 这个仓库，填入一个 API 密钥，5 分钟内拥有属于你自己的可搜索摘要站点。无需服务器，无需订阅，无需手动筛选。

**[在线示例 →](https://yuyangxueed.github.io/Linnet)** · **[中文设置入口 →](https://yuyangxueed.github.io/Linnet/setup/zh/)** · **[手动配置指南 →](astro/public/setup/manual-config.md)**

> **重要说明：**公开的 Setup Wizard 只是给你自己的 fork 生成配置，不会修改这个演示站点，也不会改动本仓库。当前仍然是“生成后复制粘贴”的模式，浏览器端一键部署还没有启用。
>
> **默认 LLM 路径：**最快的上手方式是 OpenRouter `OPENROUTER_API_KEY`。如果你想进一步尝试别的 OpenAI-compatible gateway/provider，可以在 `config/sources.yaml` 里调整模型和 `llm.base_url`，再配合手动配置文档使用。

---

## 每天早上你会收到什么

| 核心来源 | 作用 |
|---|---|
| **arXiv** | 按你的关键词抓取新论文，并附 AI 摘要 |
| **Hacker News** | 超过你设定分数线的 AI/ML 热门内容 |
| **GitHub Trending** | 你关注方向的趋势仓库 |
| **天气** | 你所在城市的天气 |

像博士后职位、导师主页监控这类来源，都属于扩展系统里的可选项；大多数用户并不需要默认启用它们。

所有内容通过 GitHub Actions 自动运行，并发布到 GitHub Pages，形成你自己的可搜索站点。

---

## 5 步快速上手

### 1. Fork 这个仓库

点击 GitHub 页面上的 **Fork**，这样生成出来的配置和站点都会属于你自己。

### 2. 添加 API 密钥

进入你 fork 后仓库的 **Settings → Secrets and variables → Actions → New repository secret**。

| 名称 | 值 |
|---|---|
| `OPENROUTER_API_KEY` | 你在 [openrouter.ai/keys](https://openrouter.ai/keys) 获取的密钥 |

OpenRouter 是默认推荐路径，因为一个 key 就能切换多个模型。如果你后续想尝试别的 OpenAI-compatible gateway/provider，可以从[手动配置文档](astro/public/setup/manual-config.md)开始。

### 3. 开启 GitHub Pages

进入 **Settings → Pages → Source: GitHub Actions**（不是 "Deploy from a branch"）。

### 4. 打开 Wizard 生成配置

推荐直接用 [Setup Wizard](https://yuyangxueed.github.io/Linnet/setup/zh/)。它会帮你完成来源选择、顺序调整、sinks 选择，以及生成适用于**你自己 fork** 的配置文件。

如果你更喜欢手动编辑，请直接看 [`astro/public/setup/manual-config.md`](astro/public/setup/manual-config.md)。

### 5. 运行第一次工作流

进入 **Actions → Daily Digest → Run workflow**。

几分钟后，你的站点就会发布出来。

---

## 一眼读懂配置

理解 `sources.yaml` 的最小例子通常就够了：

```yaml
display_order:
  - weather
  - arxiv
  - github_trending
  - hacker_news

weather:
  enabled: true
  city: "Edinburgh"
  timezone: "auto"

arxiv:
  enabled: true

github_trending:
  enabled: true
  max_repos: 15

hacker_news:
  enabled: true

language: "en"

llm:
  scoring_model: "google/gemini-2.5-flash-lite-preview-09-2025"
  summarization_model: "google/gemini-2.5-flash-lite-preview-09-2025"
  base_url: "https://openrouter.ai/api/v1"
```

你只需要先记住两件事：

- `enabled: true/false` 控制某个来源或 sink 是否启用
- `display_order` 也会影响这些模块在最终页面里的显示顺序

README 只负责给你一个整体心智模型。更细的参数说明，请看各自的 extension / sink 文档。

---

## Extensions：把你自己的来源接进来

这个项目的核心是扩展系统。

- 内置示例都在 [`extensions/`](extensions/)
- 统一约定写在 [`extensions/README.md`](extensions/README.md)
- 每个 extension 自己的细节配置，写在各自目录下的 `README.md`
- 新扩展可以直接复制 [`extensions/_template/`](extensions/_template/)

所以你完全不需要启用所有内置来源。只用 papers、HN、GitHub Trending 和 weather，也是非常正常的用法。

---

## Sinks：可选的投递渠道

网站是默认输出。Sinks 是额外的可选投递渠道。

当前内置的 sinks 包括：

- `slack`
- `serverchan`

关于 sink 的说明请看：

- [`sinks/README.md`](sinks/README.md) —— 共享的 sink 设计和约定
- `sinks/<name>/README.md` —— 每个 sink 自己的配置说明

现在的 sinks 已经是标准化的模式：

- 非敏感配置放在 `sources.yaml`
- 凭据放在 GitHub Secrets 或环境变量里
- 新 sink 可以通过复制 [`sinks/_template/`](sinks/_template/) 开始

例如：

```yaml
sinks:
  slack:
    enabled: true
    max_papers: 5
    max_hn: 3
    max_github: 3
```

和 extensions 一样，后续也欢迎继续增加更多 sinks。

---

## 定时任务和时区

默认的自动运行计划写在：

- [`.github/workflows/daily.yml`](.github/workflows/daily.yml)
- [`.github/workflows/weekly.yml`](.github/workflows/weekly.yml)
- [`.github/workflows/monthly.yml`](.github/workflows/monthly.yml)

GitHub Actions 的 cron 使用的是 **UTC**。如果你想改执行时间，直接在你自己的 fork 里编辑这些 cron 表达式即可。

像 weather 这种来源本身的时区设置，则在 `config/sources.yaml` 里配置。

---

## 在本地运行

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export OPENROUTER_API_KEY=sk-or-...
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

## 项目结构

```text
Linnet/
├── extensions/   # 数据来源插件
├── sinks/        # 可选投递渠道
├── config/       # sources.yaml 和各 extension 配置
├── publishers/   # 写入 JSON 输出到 docs/data/
├── docs/data/    # 流水线写入的 JSON 数据（非站点源码）
├── astro/        # Astro v5 静态站点 → 部署到 GitHub Pages
├── skills/       # 面向贡献者和用户的公开 prompt / skill 文件
├── dev_docs/     # 面向维护者的文档
└── main.py       # CLI 入口
```

---

## 用 AI coding agents 参与贡献和配置

这个项目欢迎大家用 AI agent 来扩展 extensions、增加 sinks，或者帮自己做配置与定制。

打包好的 skill 目录现在放在 [`skills/`](skills/) 里：

- [`skills/dailyreport-contributor/SKILL.md`](skills/dailyreport-contributor/SKILL.md)
- [`skills/dailyreport-config-customization/SKILL.md`](skills/dailyreport-config-customization/SKILL.md)

在让 AI agent 动手之前，建议先让它读这些仓库说明：

- [`llms.txt`](llms.txt)
- [`extensions/llms.txt`](extensions/llms.txt)
- [`sinks/llms.txt`](sinks/llms.txt)
- [`extensions/README.md`](extensions/README.md)
- [`sinks/README.md`](sinks/README.md)
- [`skills/`](skills/) 里对应的打包 skill

推荐提示词：

```text
Please read llms.txt, extensions/llms.txt, sinks/llms.txt, extensions/README.md,
sinks/README.md, and the relevant SKILL.md under skills/ before making changes or suggesting configuration edits.
```

---

## 分享你的配置和想法

如果你做出了一个有趣的 setup，欢迎发到 [Discussions](https://github.com/YuyangXueEd/linnet/discussions) 里。

如果你遇到实现问题、配置问题，或者想提 extension / sink 请求，可以直接使用仓库里的 issue templates。

---

## 支持这个项目

如果这个仓库帮你节省了时间、帮助你持续跟踪研究方向，或者给了你一个很好的个人科研仪表盘起点，可以在这里支持项目：

- [GitHub Sponsors](https://github.com/sponsors/yuyangxueed)
- [Ko-fi](https://ko-fi.com/guesswhat_moe)

赞助完全是自愿的。我当然很感谢捐助，但相比金钱，我更看重贡献代码、修复问题、提出想法和补充新集成。

---

## 致谢

公开站点使用 [Astro](https://astro.build/) 构建 —— 现代高性能静态站点生成器，对 GitHub Pages 支持优秀。

同时，也感谢许多开源仓库、维护者和贡献者；这个项目在设计思路、实现方式和结构组织上，都受到了他们的启发。

如果你发现某个项目或仓库值得被更明确地致谢，欢迎提 issue 或 PR，我会很乐意补上。

---

## 许可证

MIT — 详见 [LICENSE](LICENSE)。欢迎贡献。
