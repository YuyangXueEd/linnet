# Roadmap: Migrate Setup Wizard into Astro

Branch: `migrate-setup`

## Why

The Setup Wizard (`astro/public/setup/index.html` and `zh/index.html`) are standalone
static HTML files dropped verbatim into the build. This causes three concrete problems:

1. **Duplicate design tokens** — ~80 lines of CSS variables in each file mirror `global.css`.
   Any colour or spacing change must be applied in three places.

2. **Broken theme sync** — The wizard uses `body[data-theme]`; Astro pages use
   `html[data-theme]`. The navbar's theme toggle (which writes to `html`) has no effect
   on the wizard. A user who switched to dark mode on the feed pages will see the wizard
   revert to light.

3. **Isolated navigation** — The wizard has its own hardcoded nav bar. Any change to
   links, branding, or layout must be replicated manually.

Migrating into proper Astro pages (`src/pages/setup/`) eliminates all three issues at
once: shared `global.css`, shared `Base.astro` layout (which owns the `html[data-theme]`
logic), and the `NavBar` component.

## Scope

| File | Action |
|---|---|
| `astro/public/setup/index.html` | → `astro/src/pages/setup/index.astro` |
| `astro/public/setup/zh/index.html` | → `astro/src/pages/setup/zh/index.astro` |
| `astro/public/setup/manual-config.md` | Keep as-is in `public/` (static download) |

## Plan

### Step 1 — Audit what each HTML file owns

Walk through `index.html` and identify three zones:
- **CSS** — everything inside `<style>` (will be deleted; replaced by `global.css` imports)
- **HTML body** — the wizard markup (keep, paste into Astro's `<slot>`)
- **JS block** — the ~1000-line wizard script starting at line 1023 (keep intact, move
  into an Astro `<script>` tag)

Do the same for `zh/index.html`. The two files are near-identical in structure; the
zh variant differs only in string labels and a few default values.

### Step 2 — Create the Astro pages

```
astro/src/pages/setup/index.astro      (English wizard)
astro/src/pages/setup/zh/index.astro   (Chinese wizard)
```

Each page wraps content in `<Base title="Setup Wizard">`. The layout already handles:
- Google Fonts import
- `global.css` (design tokens, dark/light vars, resets, utility classes)
- `html[data-theme]` initialisation script (no flash)
- `NavBar` with working theme toggle

### Step 3 — Adapt the wizard markup

Remove from the pasted HTML:
- The entire `<style>` block (all CSS variables and resets are now in `global.css`)
- The standalone `<nav>` / header (replaced by `NavBar`)
- The `loadTheme()` / `updateThemeButton()` functions and the theme toggle button inside
  the wizard (theme is now owned by `Base.astro` / `NavBar`)

Update the one theme reference in JS:
```js
// Before (wizard-internal)
document.body.dataset.theme = t;
// After (Astro convention)
document.documentElement.dataset.theme = t;  // already done by Base.astro; remove entirely
```

Map CSS variable names — the wizard used short names (`--bg`, `--text`, `--brand`);
`global.css` uses prefixed names (`--site-bg`, `--site-text`, `--site-brand`). Either:
- (a) Add aliases to `global.css` (one-liner each, backwards-compatible), or
- (b) Do a bulk rename in the pasted markup/style (scoped `<style>` in the Astro page)

Option (a) is safer and requires zero JS changes.

### Step 4 — CSS delta (scoped styles)

After removing the duplicated token block, the wizard still has layout-specific rules
(`.hero`, `.wizard`, `.shell`, `.preview`, step transitions, drag-and-drop styles, etc.)
that don't belong in `global.css`. Keep these in a `<style>` block scoped to the Astro
component.

### Step 5 — Delete the old public files

Remove `astro/public/setup/index.html` and `astro/public/setup/zh/index.html` once the
Astro pages are confirmed to build and render correctly. `manual-config.md` stays.

### Step 6 — Verify

- `npm run build` completes without errors
- `/Linnet/setup/` renders with correct NavBar and dark/light theme following the toggle
- `/Linnet/setup/zh/` same
- Config generation JS still produces valid YAML output (no regression)
- `manual-config.md` still downloadable at `/Linnet/setup/manual-config.md`

## Risk & mitigations

| Risk | Mitigation |
|---|---|
| 1000-line wizard JS breaks after selector changes | Keep JS intact; only remove the 3-line theme block. Test config generation end-to-end. |
| CSS variable rename introduces visual regressions | Use option (a) — add aliases to `global.css`, keep old names working. |
| zh variant diverges unexpectedly | Diff the two HTML files before starting; document any intentional differences. |
| `manual-config.md` link breaks | It remains in `public/`; Astro copies it verbatim. No change needed. |

## Definition of done

- [ ] Both setup pages are `.astro` files under `src/pages/setup/`
- [ ] No standalone `<style>` CSS token block remains in either page
- [ ] Theme toggle in the navbar works on all four pages (index, daily, setup EN, setup ZH)
- [ ] Old `public/setup/*.html` files deleted
- [ ] Build passes, pre-commit passes
- [ ] Deployed to `https://yuyangxueed.github.io/Linnet/setup/` and verified visually
