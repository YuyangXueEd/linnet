# Extension UI Guide

Adding a custom card for your extension takes four steps and about 10 minutes.
If you skip this step entirely, your extension will still appear in the digest
using the built-in `GenericCard` — no code required.

---

## Step 1 — Copy the card template

```bash
cp extensions/_template/ui/card.astro \
   astro/src/components/cards/{your_key}.astro
```

Replace `{your_key}` with the exact `key` your Python extension emits in the
JSON output (e.g. `rss_feed`, `reddit`, `lobsters`).

---

## Step 2 — Update the Props interface

Open the file and replace the placeholder fields with the actual fields your
extension emits. Check your extension's `collector.py` or `summarizer.py`
to see what ends up in the JSON.

---

## Step 3 — Register in `registry.ts`

Add one entry to `REGISTRY` in `astro/src/lib/registry.ts`:

```typescript
my_extension: {
  key: 'my_extension',
  title: 'My Section Title',        // shown as the section heading
  subtitle: 'Source description',   // sub-label below the heading
  icon: 'book',                     // one of the icon names listed below
  defaultOrder: 7,                  // position in the digest (after existing sections)
  layout: 'stack',                  // layout mode (see below)
  displayName: 'My Extension',      // shown in Setup wizard Step 1
  description: 'One-line pitch.',
  category: 'custom',
  tags: ['keyword1', 'keyword2'],   // used by Setup wizard search
  setupFields: [],                  // config fields shown in Setup wizard Step 2
},
```

---

## Step 4 — Add to SectionBlock

Open `astro/src/components/SectionBlock.astro` and add two lines:

```astro
---
// 1. Import your card (top of frontmatter, with the other imports)
import MyCard from './cards/my_extension.astro';

// 2. Add to COMPONENTS map
const COMPONENTS = {
  // ...existing entries...
  my_extension: MyCard,
};
---
```

---

## CSS Design Tokens

All colours, fonts, and spacing come from global CSS variables.
**Do not hardcode colours** — use these tokens so your card works in both
light and dark mode automatically.

### Typography

| Variable | Value | Use for |
|----------|-------|---------|
| `var(--font-display)` | Fraunces (serif) | Titles, headings, numbers |
| `var(--font-body)` | Source Serif 4 | Body text, abstracts |
| `var(--font-ui)` | Inter | Buttons, form controls |
| `var(--font-mono)` | JetBrains Mono | Tags, labels, metadata, scores |

### Colours

| Variable | Light | Dark | Use for |
|----------|-------|------|---------|
| `var(--ink)` | `#1a1814` | `#f0e7d4` | Main text, headings |
| `var(--ink-soft)` | `#3d372f` | `#d4c9b3` | Body text |
| `var(--ink-muted)` | `#7a7265` | `#8f8676` | Metadata, timestamps |
| `var(--accent)` | `#c43d2a` | `#ec6a50` | Tags, scores, highlights |
| `var(--gold)` | `#b8892a` | `#d9b05c` | Secondary accent |
| `var(--bg)` | `#f4ede0` | `#1c1611` | Page background |
| `var(--paper)` | `#fffdf7` | `#241d16` | Card/panel background |
| `var(--rule)` | `rgba(26,24,20,0.14)` | `rgba(240,231,212,0.14)` | Borders, dividers |

### Layout helpers

| Variable | Value | Use for |
|----------|-------|---------|
| `var(--rule-soft)` | lower opacity rule | subtle dividers |
| `var(--accent-soft)` | tinted accent | tag backgrounds |
| `var(--gold-soft)` | tinted gold | score backgrounds |

---

## Layout modes

Choose the layout that fits your content in `registry.ts`:

| Mode | Grid | Best for |
|------|------|----------|
| `stack` | 1 column | Jobs, long text items |
| `columns-2` | 2 columns | Stories, links |
| `columns-3` | 3 columns | Repos, cards with short content |
| `single` | Full width | Weather, dashboard widgets |
| `editorial` | Complex (reserved) | Papers with figures — internal use |

---

## Available icons

Pass one of these strings as the `icon` field in `registry.ts`:

`paper` · `flame` · `repo` · `post` · `cloud` · `feather` · `book` · `search` · `arrow` · `sun` · `moon`

---

## Astro-skills compatibility (optional)

If you want your extension to be discoverable by AI agents via the
[Agent Skills spec](https://agentskills.io/specification), add an
`agentCapabilities` array to your registry entry (currently a reserved field
— implementation pending):

```typescript
// agentCapabilities: ['read:rss', 'configure:feed'],
```
