---
layout: home
title: Home
nav_order: 1
---

# MyDailyUpdater — Live Demo

This is a live example of what your own digest site looks like after forking [MyDailyUpdater](https://github.com/YuyangXueEd/MyDailyUpdater).

Every day at midnight UTC, GitHub Actions fetches new arXiv papers, Hacker News stories, and trending GitHub repos — filters them by topic, summarises them with AI, and commits the results here automatically.

**The topics shown here are just one person's config.** Fork the repo and swap in your own keywords to get a digest built around your research.

---

**Browse:**

- [Daily]({{ "/daily/" | relative_url }}) — today's papers, HN highlights, GitHub trending
- [Weekly]({{ "/weekly/" | relative_url }}) — weekly rollup
- [Monthly]({{ "/monthly/" | relative_url }}) — monthly overview

---

**Want your own?** → [github.com/YuyangXueEd/MyDailyUpdater](https://github.com/YuyangXueEd/MyDailyUpdater) — fork, add one API key, done.

Not sure how to configure it? Use the **[Setup Wizard]({{ "/setup/" | relative_url }})** to pick your topics and get your config files ready to copy in.
