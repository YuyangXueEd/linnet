# MyDailyUpdater

自托管、可扩展的每日摘要流水线。每天自动从多个来源抓取论文、新闻、职位和热门仓库，通过 LLM 评分和摘要，最终发布为可搜索的静态网站（GitHub Pages）。

**[在线演示 →](https://yuyangxueed.github.io/MyDailyUpdater)**

---

## 功能概览

| 数据源 | 内容 |
|---|---|
| **arXiv** | 按类别和关键词筛选论文，LLM 相关性评分，摘要 + 图片预览 |
| **Hacker News** | 超过分数阈值的 AI/ML 热门文章 |
| **学术职位** | 来自 jobs.ac.uk、FindAPostDoc、EURAXESS 等的博士后和研究员职位 |
| **GitHub Trending** | 每日 AI/ML 热门仓库 |
| **导师页面监控** | 检测你关注的导师/实验室主页内容变化 |

通过 GitHub Actions 每天 UTC 午夜自动运行，输出提交回仓库并以 Jekyll 网站（Just the Docs 主题）形式发布。

---

## 快速开始

### 1. Fork 本仓库

在 GitHub 页面点击 **Fork**，所有 Actions 工作流和 Pages 配置已包含在内。

### 2. 添加 API 密钥

在你的 Fork 中：**Settings → Secrets and variables → Actions → New repository secret**

| Secret 名称 | 值 |
|---|---|
| `OPENROUTER_API_KEY` | 你的 [OpenRouter](https://openrouter.ai) API Key |

流水线使用 OpenRouter，可以在 `config/sources.yaml` 中自由切换模型。

### 3. 开启 GitHub Pages

**Settings → Pages → Source: Deploy from a branch → 分支选 `main` / `docs/`**

### 4. 配置你的兴趣方向

编辑 `config/keywords.yaml` 设置 arXiv 类别、关键词和评分阈值。  
编辑 `config/sources.yaml` 启用/禁用数据源、选择输出语言和 LLM 模型。

### 5. 触发首次运行

**Actions → Daily Digest → Run workflow** — 约 5 分钟后网站上线。

---

## 配置说明

### `config/sources.yaml`

```yaml
# 摘要输出语言。
# "en"（默认，英文）| "zh"（中文）| "fr" | "de" | "ja" | "ko" | "es" | "pt"
# 支持任意 BCP-47 语言代码 —— LLM 将直接以该语言输出，无需单独翻译步骤。
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

控制 arXiv 过滤条件、HN 关键词匹配、职位过滤和 LLM 评分阈值，详见文件内注释。

### `config/supervisors.yaml`

配置需要监控的导师/实验室主页：

```yaml
supervisors:
  - name: "张三"
    institution: "示例大学"
    url: "https://example.ac.uk/~zhangsan"
```

---

## 扩展系统

每个数据源都是一个独立的 **Extension**（`extensions/` 目录）。Extension 拥有完整的流水线：fetch（抓取）→ process（评分/总结）→ render（输出 `FeedSection`）。

### 添加新数据源

1. 创建 `extensions/my_source.py`：

```python
from extensions.base import BaseExtension, FeedSection

class MySourceExtension(BaseExtension):
    key = "my_source"       # 必须与 config/sources.yaml 中的键名一致
    title = "我的数据源"

    def fetch(self) -> list[dict]:
        # 从数据源拉取原始数据
        ...

    def process(self, items: list[dict]) -> list[dict]:
        # 可选：评分、过滤、摘要
        # self.llm    —— OpenAI 兼容的 LLM 客户端
        # self.config —— 该 Extension 的配置（含 language、模型名称等）
        return items

    def render(self, items: list[dict]) -> FeedSection:
        return FeedSection(key=self.key, title=self.title, items=items)
```

2. 在 `extensions/__init__.py` 中注册：

```python
from extensions.my_source import MySourceExtension

REGISTRY = [
    ...,
    MySourceExtension,
]
```

3. 在 `config/sources.yaml` 中添加配置块：

```yaml
my_source:
  enabled: true
  # 你的 Extension 专属配置
```

编排器会在下次流水线运行时自动调用 `ext.run()`。

---

## 本地运行

```bash
# 安装依赖
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 设置 API Key
export OPENROUTER_API_KEY=sk-or-...

# 运行每日流水线
python main.py --mode daily

# 周报 / 月报汇总
python main.py --mode weekly
python main.py --mode monthly

# 快速状态检查（供 Claude Code SessionStart hook 使用）
python main.py --check-today

# 运行测试
PYTHONPATH=. pytest tests/ -q
```

---

## 项目结构

```
MyDailyUpdater/
├── extensions/          # 可插拔数据源 Extension
│   ├── base.py          # BaseExtension + FeedSection 基类
│   ├── arxiv.py
│   ├── hacker_news.py
│   ├── jobs.py
│   ├── supervisor.py
│   └── github_trending.py
├── collectors/          # 底层抓取函数（供 Extension 调用）
├── pipeline/            # 评分、摘要、聚合、配置加载
├── publishers/          # JSON 写入 + Jinja2 → Markdown 渲染
├── templates/           # 日报/周报/月报 Jinja2 模板
├── config/
│   ├── sources.yaml     # 数据源开关、语言、LLM 模型
│   ├── keywords.yaml    # 过滤条件、阈值、类别
│   └── supervisors.yaml # 监控的导师页面
├── docs/                # 生成的网站（由 GitHub Pages 服务）
├── tests/
└── main.py              # CLI 入口 + 流水线编排器
```

---

## 定时工作流

| 工作流 | 触发时间 | 内容 |
|---|---|---|
| `daily.yml` | 每天 UTC 00:00 | 完整流水线，输出提交到 `docs/` |
| `weekly.yml` | 每周一 UTC 01:00 | 周度趋势汇总 |
| `monthly.yml` | 每月 1 日 UTC 02:00 | 月度全景概述 |

所有工作流均可通过 **Actions → Run workflow** 手动触发。

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE)。

欢迎贡献。如果你开发了新的 Extension，欢迎提 PR 或在 Issues 中分享。
