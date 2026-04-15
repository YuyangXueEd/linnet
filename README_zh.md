# MyDailyUpdater

[English](README.md)

**每天早上自动送来一份个性化的科研摘要——不用你动手。**

Fork 这个仓库，填入一个 API 密钥，然后每天早上就能收到一份按你的兴趣筛选、由 AI 摘要的 arXiv 论文、Hacker News 热文和 GitHub 趋势仓库，并发布为你专属的网站。

**[在线示例 →](https://yuyangxueed.github.io/MyDailyUpdater)** · **[配置向导 →](https://yuyangxueed.github.io/MyDailyUpdater/setup/)**

> **费用：** 使用 `gemini-2.5-flash-lite` 通过 OpenRouter，每天约 $0.01–$0.05（有免费额度）。

---

## 每天早上你会收到什么

| 来源 | 内容 |
|---|---|
| **arXiv** | 符合你关键词的新论文，每篇附 AI 摘要 |
| **Hacker News** | 超过你设定分数线的 AI/ML 热门文章 |
| **GitHub Trending** | 今天在你感兴趣领域最受关注的仓库 |
| **天气** | 你所在城市的今日天气 |
| **博士后职位** | 来自 jobs.ac.uk、FindAPostDoc、EURAXESS 的学术职位 |
| **导师主页监控** | 你关注的教授或实验室主页有更新时提醒你 |

所有内容通过 GitHub Actions 在 UTC 午夜自动运行，结果保存回仓库并发布为可搜索的静态网站。

---

## 5 步完成配置

### 第 1 步 — 把这个仓库复制到你的账号下

点击页面顶部的 **Fork**，GitHub 会在你的账号下创建一份副本，自动化流程已全部包含在内。

### 第 2 步 — 添加 API 密钥

在你 Fork 后的仓库中，进入：**Settings → Secrets and variables → Actions → New repository secret**

| 名称 | 值 |
|---|---|
| `OPENROUTER_API_KEY` | 你在 [openrouter.ai/keys](https://openrouter.ai/keys) 获取的密钥，以 `sk-or-...` 开头，有免费额度 |

这是你唯一需要填的凭据。[OpenRouter](https://openrouter.ai) 让你用一个密钥调用多种 AI 模型（Gemini、GPT、Claude），随时可以切换。

### 第 3 步 — 开启你的网站

进入：**Settings → Pages → Source: Deploy from a branch → 分支选 `main`，文件夹选 `/docs`**

点击 **Save**，你的网站地址会出现在那里，格式类似 `https://你的用户名.github.io/MyDailyUpdater`。

### 第 4 步 — 选择你的研究方向

打开 [config/extensions/arxiv.yaml](config/extensions/arxiv.yaml)，里面有四个现成的配置方案，找到最接近你研究方向的那个，去掉行首的 `#` 来启用它，然后按需修改关键词：

```yaml
# 方案 A：AI / ML / LLM（通用）
# categories: [cs.AI, cs.LG, cs.CL, cs.CV, stat.ML]
# must_include:
#   - large language model
#   - foundation model
#   ...

# 方案 B：机器人 / 具身智能
# 方案 C：医学 AI / 临床 NLP
# 方案 D：NLP / 文本 / 推理
```

想用中文摘要？打开 [config/sources.yaml](config/sources.yaml)，把 `language: "en"` 改成 `"zh"` 即可。也支持 `"fr"`、`"de"`、`"ja"`、`"ko"`、`"es"` 等任意语言代码。

### 第 5 步 — 触发第一次运行

进入：**Actions → Daily Digest → Run workflow → Run workflow**

约 5 分钟后网站即可访问。

---

## 开启或关闭各个来源

打开 [config/sources.yaml](config/sources.yaml)，对每个来源设置 `enabled: true` 或 `enabled: false`：

```yaml
arxiv:
  enabled: true          # arXiv 论文——主要来源

hacker_news:
  enabled: true          # Hacker News 热文

github_trending:
  enabled: true          # 今日 GitHub 趋势仓库
  max_repos: 15

weather:
  enabled: true
  city: "Edinburgh"      # 改成你的城市

postdoc_jobs:
  enabled: false         # 学术职位列表——需要的话改为 true

supervisor_updates:
  enabled: false         # 导师主页监控——需要的话改为 true
```

你也可以在这里切换 AI 模型，或限制每天抓取的论文数量。

---

## 把摘要发到 Slack

除了网站，你还可以每天收到一条 Slack 消息。配置大约需要 2 分钟：

1. 打开 [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. 左侧菜单 → **Features → Incoming Webhooks** → 开关拨到 **On**
3. 页面下方 → **Add New Webhook to Workspace** → 选择频道 → **Allow**
4. 复制 Webhook URL（格式类似 `https://hooks.slack.com/services/T.../B.../...`）
5. 在仓库里添加 Secret：**Settings → Secrets → New secret**，名称填 `SLACK_WEBHOOK_URL`
6. 在 [config/sources.yaml](config/sources.yaml) 中启用：

```yaml
sinks:
  slack:
    enabled: true
    max_papers: 5    # 推送几篇论文
    max_hn: 3        # 推送几条 HN 热文
    max_github: 3    # 推送几个 GitHub 趋势仓库
```

不配置 Slack 也完全没问题，网站照常更新。

---

## 自动运行计划

| 时间 | 内容 |
|---|---|
| 每天 UTC 00:00 | 完整摘要——论文、HN、GitHub 趋势、天气，以及你启用的其他来源 |
| 每周一 UTC 01:00 | 上周趋势汇总 |
| 每月 1 日 UTC 02:00 | 月度全景概述 |

也可以随时手动触发：**Actions → [工作流名称] → Run workflow**。

---

## 添加你自己的数据来源

每个来源都是 `extensions/` 目录下一个独立的文件夹。添加新来源的步骤：

**1. 复制模板：**
```bash
cp -r extensions/_template extensions/my_source
```

**2. 填入三个函数**，在 `extensions/my_source/__init__.py` 中：
- `fetch()` — 从任何地方抓取原始数据（网站、API、文件）
- `process()` — 可选：用内置 AI 客户端过滤或摘要
- `render()` — 把结果格式化为摘要中的一个板块

**3. 注册**，在 `extensions/__init__.py` 中：
```python
from extensions.my_source import MySourceExtension

REGISTRY = [..., MySourceExtension]
```

**4. 添加开关**，在 `config/sources.yaml` 中：
```yaml
my_source:
  enabled: true
```

完整指南和示例：[extensions/README.md](extensions/README.md)

---

## 在本地运行

```bash
# 安装依赖
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 设置 API 密钥
export OPENROUTER_API_KEY=sk-or-...

# 运行完整摘要
python main.py --mode daily

# 只抓取数据，不调用 AI（免费，用来测试配置是否正常）
python main.py --dry-run

# 周报或月报
python main.py --mode weekly
python main.py --mode monthly
```

运行测试：
```bash
PYTHONPATH=. pytest tests/ -q
```

---

## 项目结构

```
MyDailyUpdater/
├── extensions/             # 每个数据来源一个文件夹
│   ├── _template/          # 复制这个来新建数据来源
│   ├── arxiv/              # arXiv 论文
│   ├── github_trending/    # GitHub 趋势仓库
│   ├── hacker_news/        # Hacker News 热文
│   ├── postdoc_jobs/       # 学术职位列表
│   ├── supervisor_updates/ # 导师主页监控
│   ├── weather/            # 天气预报
│   └── base.py             # 所有来源共用的基类
├── sinks/                  # 推送渠道（如 Slack）
│   └── slack/
├── pipeline/               # 评分、摘要、组装摘要
├── publishers/             # 把结果写入 docs/ 网站文件
├── templates/              # 日报/周报/月报页面模板
├── config/
│   ├── sources.yaml        # 来源开关、输出语言、AI 模型
│   └── extensions/
│       ├── arxiv.yaml      # 你的研究关键词和 arXiv 分类
│       ├── hacker_news.yaml
│       ├── postdoc_jobs.yaml
│       └── supervisor_updates.yaml
├── docs/                   # 生成的网站（由 GitHub Pages 发布）
├── tests/
└── main.py                 # 入口
```

---

## 分享你的配置

做了什么有趣的配置，或者用这个工具追踪了一个冷门领域？欢迎在 [Discussions](https://github.com/YuyangXueEd/MyDailyUpdater/discussions) 里分享——有类似研究兴趣的人会很感激你。

发现 bug 或想添加新的来源？[提一个 issue](https://github.com/YuyangXueEd/MyDailyUpdater/issues)。

---

## 许可证

MIT — 详见 [LICENSE](LICENSE)。欢迎贡献。
