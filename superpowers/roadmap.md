# Linnet — Roadmap

This file tracks product direction, planned work, and known debt.

---

## Product direction (locked)

These decisions are settled and should guide all implementation choices.

### Positioning
- Primary audience: information-overloaded knowledge workers, not researchers first.
- Core promise: `your personal AI morning briefing`.
- Product framing: sell an elite-feeling daily briefing workflow, not an aggregator.
- Narrative frame: "your AI secretary prepares a quality briefing before you start the day" — not "a configurable content pipeline."
- Setup Wizard role: the main product entry point, not a helper page.

### Funnel stance
- Current GitHub-first setup is acceptable only as a short-term bridge.
- Near term: hide technical friction behind guided onboarding, strong demo output, and explicit hand-holding.
- Long term: move toward a lighter SaaS-like flow instead of `fork + secrets + Actions` as the main public funnel.
- Near-term bridge tactic: polished 1-2-3 visual guidance; leave room for a `1-minute setup` video.
- Conversion warning: `fork + add secret + run workflow` is a dead-end for mainstream users if shown as the primary journey.
- Setup Wizard success criterion: the first 30 seconds should create an "Aha" moment before users feel they are doing configuration work.

### Proof and packaging
- Use founder dogfooding as the first credibility source.
- Show polished real outputs before talking about architecture.
- Present only a few opinionated starter templates in the main flow (`venture brief`, `academic brief`, `daily industry brief`).
- Treat open source and deep customisation as trust/infrastructure, not the hero message.
- Practice "restrained openness" — hide extension, sink, and theme complexity behind advanced paths.

### Brand direction
- Desired feel: scholarly, calm, efficient, premium-minimal.
- Typography: serif for high-impact headlines and digest presentation; clean sans-serif for support text.
- Colour: paper/off-white background, slate-gray body text, restrained dark red or refined gold accent.
- Avoid: all-sans layouts, pure black/white, bright developer-tool blues as the dominant signal.

### Distribution hooks (P2)
- HN / Reddit / V2EX: anti-noise, self-hosted, open, data-in-your-control angle.
- Xiaohongshu / Jike: aesthetic, efficient, "AI secretary" angle with polished visual output.
- Channel rule: the story should change by platform even if the product stays the same.

---

## P1 — Content, proof, and polish

- [ ] Expand the proof section with concrete founder-run use cases and captions, not only screenshots.
- [ ] Reduce open-source and customisation complexity in the main public funnel.
- [ ] Introduce a small set of opinionated starter modes in copy and layout.
- [ ] Add direct links for any repos/snippets where code or UI was substantially adapted.

---

## Sink delivery ergonomics

- [ ] Add optional `delivery_mode: single | sectioned` config for sinks.
- [ ] For Slack: consider `sectioned` as default because Block Kit has field/block limits.
- [ ] For ServerChan: keep `single` as the conservative default.
- [ ] Add `max_jobs` config parity to the Slack sink.
- [ ] Add tests covering single vs multi-message delivery behaviour.

---

## LLM follow-ups

- [ ] Future follow-up if needed: add native Anthropic/Gemini adapters beyond OpenAI-compatible endpoints.

---

## Brand naming follow-ups

- [ ] Treat `Daily Digest` as a report/output label only, not the product name.

---

## P2 — Onboarding follow-ups

- [x] Ship the GitHub App + `setup-bridge` onboarding path as the default PAT-free bridge.

- [x] Default the Setup Wizard to a compact beginner mode with a few opinionated starter modes.

- [x] Move advanced source tuning, sinks, and theme controls behind progressive disclosure.

- [ ] Strengthen Step 6 success and failure states with clearer workflow links, policy troubleshooting, and Pages-delay messaging.

- [ ] Prepare the site for future non-GitHub onboarding.
  Write copy and structure that can survive a SaaS-like deployment flow without a full rewrite.

- [ ] Prepare copy and layout for a future lightweight web onboarding flow.
  Leave a clean path for `sign in → enter key → deploy/run` without rewriting the public narrative.

### Brief mode implementation note

The first compact beginner mode is now shipped in the Setup Wizard:

- Ship only two starter modes first:
  - `Academic Brief`
  - `Daily Personal Brief`
- Treat starter mode as a UI layer over the existing wizard state model, not as a separate product flow.
- Keep one-click GitHub App deploy as the default end state.

Current implementation details for `Academic Brief`:

- Ask for a single primary research domain before the rest of the wizard opens.
- Back that domain picker with the existing `ARXIV_PROFILES` presets in `astro/src/lib/arxivProfiles.ts`.
- Keep the first version opinionated and single-select, not multi-select.
- Offer an explicit advanced escape hatch for custom arXiv categories and keywords.

Recommended first domain set for `Academic Brief`:

- AI / ML
- Computer Vision
- NLP / Language Models
- Robotics
- Medical Imaging
- Biology / Bioinformatics
- Physics
- Chemistry / Materials
- Mathematics
- Astrophysics

Current implementation details for `Daily Personal Brief`:

- Default sources: weather, Hacker News, GitHub trending
- Ask only for language, city/timezone, LLM provider, and API key in the compact flow
- Hide sink/theme/source fine-tuning behind advanced controls

Compact-flow UX shape:

- Step 0: choose starter mode
- Step 0.5 for `Academic Brief`: choose one research domain
- Step 1+: show only the minimum fields needed to launch successfully
- Advanced controls remain available, but collapsed by default

Implementation stance that remains in place:

- Reuse the current wizard state and generated config pipeline
- Apply starter-mode defaults in controller code
- Do not fork the YAML schema or introduce a second export format
- Preserve the existing advanced manual path for power users

---

## Growth & Promotion

### Phase 0 — GitHub hygiene
- [ ] Add GitHub Topics: `arxiv`, `github-actions`, `llm`, `research-digest`, `ai-summary`, `personal-dashboard`, `openai`, `automation`, `python`, `github-pages`.

### Phase 1 — Written posts
- [ ] Show HN — `Show HN: Linnet – self-hosted AI research digest via GitHub Actions`.
- [ ] Reddit `r/selfhosted` — "I built a self-hosted daily research digest using GitHub Actions + LLM".
- [ ] Reddit `r/MachineLearning` or `r/LocalLLaMA` — arXiv + AI summary angle.
- [ ] dev.to or hashnode article — technical walkthrough.
- [ ] 知乎文章 — 面向中文学术圈。

### Phase 2 — Passive virality
- [ ] Showcase page (`docs/showcase.md`) listing forks with live sites.
- [ ] RSS output so users can subscribe via any RSS reader.

### Phase 3 — Community (when 50+ stars)
- [ ] Confirm GitHub Discussions is enabled.
- [ ] Pin one "Share your setup" discussion thread.

---

## Documentation IA

- [ ] Enable GitHub Wiki for newcomer-friendly onboarding and FAQs.
- [ ] Add first-wave Wiki pages: Home, Quick Start for Beginners, Glossary, Troubleshooting, Use Cases.
- [ ] Link the Wiki from `README.md`, `README_zh.md`, and setup surfaces.

---

## Feature backlog

### Email sink `[P0]`
- Use SendGrid, Mailgun, or SMTP (all have free tiers).
- Template: plain-text digest + HTML version.
- Config: `sinks.email.enabled`, `SENDGRID_API_KEY` / `SMTP_*` secrets.

### Discord sink `[P1]`
- Incoming webhook, same pattern as Slack sink.
- Rich embeds via Discord embed format.

### Telegram sink `[P1]`
- Bot API + `sendMessage` with Markdown.
- Requires `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.

### Generic RSS / RSSHub extension `[BACKLOG]`
```yaml
rss:
  enabled: true
  feeds:
    - name: "Newlearner Channel"
      url: "https://rsshub.app/telegram/channel/NewlearnerChannel"
  max_items_per_feed: 5
```
`feedparser` handles RSS/Atom/RDF transparently; LLM summarises each entry in `process()`.

---

## Performance

Implement after the visual redesign is stable.

- [ ] Add `astro-critters` for critical CSS inlining.
- [ ] Add `@playform/compress` for HTML/CSS/JS minification at build.
- [ ] Make Google Fonts non-blocking with the `media="print" onload` pattern.
- [ ] Add `font-display: swap` to all `@font-face` declarations.
- [ ] Preload the LCP hero image with `fetchpriority="high"`.
- [ ] Defer third-party scripts until user interaction when possible.

---

## Human decisions needed

- [ ] Approve the strongest real digest screenshots and proof examples for the homepage.
- [ ] Decide whether to record the `1-minute setup` video now or after the next homepage rewrite.
- [ ] Approve the first three opinionated starter templates to feature publicly.
- [ ] Decide when to prioritise the long-term SaaS-like onboarding path over GitHub-only setup.
