import { EXTENSION_LIST, REGISTRY, type SetupField } from '@/lib/registry';
import { ARXIV_PROFILES } from '@/lib/arxivProfiles';
import { createInitialState, DEFAULT_TOP_N, type WizardState } from './wizardState';
import { buildGitHubCallPreview, deployGeneratedConfig, parseRepoInput } from './githubDeploy.js';
import {
  listAccessibleRepositories,
  getCurrentUser,
  looksLikePat,
} from './githubAuth.js';

// ── Helpers ──────────────────────────────────────────────────────────────────

function unique<T>(arr: T[]): T[] {
  return [...new Set(arr)];
}

type QueryRoot = Element | Document | null | undefined;

function qs<T extends Element>(sel: string, root: QueryRoot = document): T | null {
  if (!root) return null;
  return root.querySelector<T>(sel);
}

function qsa<T extends Element>(sel: string, root: QueryRoot = document): T[] {
  if (!root) return [];
  return [...root.querySelectorAll<T>(sel)];
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function yamlStr(v: unknown): string {
  if (v === null || v === undefined) return '""';
  const s = String(v);
  if (/[:#\[\]{},\|>&\*!,'"?@`]/.test(s) || s.includes('\n') || s !== s.trim()) {
    return JSON.stringify(s);
  }
  return s || '""';
}

function pushYamlList(lines: string[], key: string, items: string[]): void {
  lines.push(`${key}:`);
  if (!items.length) { lines.push('  []'); return; }
  for (const item of items) lines.push(`  - ${yamlStr(item)}`);
}

function loadJson<T>(key: string): T | null {
  try {
    const raw = window.sessionStorage.getItem(key);
    return raw ? JSON.parse(raw) as T : null;
  } catch {
    return null;
  }
}

function saveJson(key: string, value: unknown): void {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage failures in private browsing or locked-down environments.
  }
}

function removeJson(key: string): void {
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // Ignore storage failures.
  }
}

interface OutputBlock {
  path: string;
  desc: string;
  body: string;
}

interface GitHubRepoOption {
  id: number;
  owner: string;
  repo: string;
  fullName: string;
  htmlUrl: string;
}

interface GitHubSession {
  token: string;
  repositories: GitHubRepoOption[];
  selectedRepo: string;
  user?: {
    login: string;
    avatarUrl: string;
    name?: string;
  };
}

type SetupMode = 'connect' | 'manual';

const GITHUB_AUTH_SESSION_KEY = 'linnet-github-auth-v1';
const WIZARD_SETUP_MODE_KEY = 'linnet-setup-mode-v1';

const DEFAULT_POSTDOC_TERMS = ['machine learning', 'computer vision', 'medical imaging'];
const DEFAULT_POSTDOC_EXCLUDE = ['chemistry', 'economics', 'social science', 'humanities'];
const OPENROUTER_DEFAULT_MODEL = 'google/gemini-2.5-flash-lite-preview-09-2025';
const LLM_PRESET_DEFAULTS = {
  openrouter: {
    provider: 'openrouter',
    baseUrl: 'https://openrouter.ai/api/v1',
    apiKeyEnv: 'OPENROUTER_API_KEY',
    scoringModel: OPENROUTER_DEFAULT_MODEL,
    summarizationModel: OPENROUTER_DEFAULT_MODEL,
  },
  openai: {
    provider: 'openai',
    baseUrl: 'https://api.openai.com/v1',
    apiKeyEnv: 'OPENAI_API_KEY',
    scoringModel: 'gpt-5-mini',
    summarizationModel: 'gpt-5-mini',
  },
  anthropic_compat: {
    provider: 'anthropic_compat',
    baseUrl: 'https://api.anthropic.com/v1/',
    apiKeyEnv: 'ANTHROPIC_API_KEY',
    scoringModel: 'claude-haiku-4-5',
    summarizationModel: 'claude-haiku-4-5',
  },
  google_compat: {
    provider: 'google_compat',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai/',
    apiKeyEnv: 'GEMINI_API_KEY',
    scoringModel: 'gemini-2.5-flash-lite',
    summarizationModel: 'gemini-2.5-flash-lite',
  },
  custom: {
    provider: 'custom',
    baseUrl: 'https://api.example.com/v1',
    apiKeyEnv: 'LLM_API_KEY',
    scoringModel: '',
    summarizationModel: '',
  },
} as const satisfies Record<string, WizardState['llm']>;
type LlmPresetKey = keyof typeof LLM_PRESET_DEFAULTS;

function getLlmPresetDefaults(provider: string): WizardState['llm'] {
  return provider in LLM_PRESET_DEFAULTS
    ? LLM_PRESET_DEFAULTS[provider as LlmPresetKey]
    : LLM_PRESET_DEFAULTS['openrouter'];
}

function pushYamlValue(lines: string[], key: string, value: unknown): void {
  if (Array.isArray(value)) {
    pushYamlList(lines, key, value.map(item => String(item)));
    return;
  }
  lines.push(`${key}: ${yamlStr(value)}`);
}

function resolveLlmConfig(state: WizardState): WizardState['llm'] {
  const provider = state.llm.provider.trim() || 'openrouter';
  const preset = getLlmPresetDefaults(provider);
  const allowBlankModels = provider === 'custom';
  const scoringModel = state.llm.scoringModel.trim()
    || preset.scoringModel
    || (allowBlankModels ? '' : OPENROUTER_DEFAULT_MODEL);
  const summarizationModel = state.llm.summarizationModel.trim()
    || preset.summarizationModel
    || scoringModel
    || (allowBlankModels ? '' : OPENROUTER_DEFAULT_MODEL);

  return {
    provider,
    baseUrl: state.llm.baseUrl.trim() || preset.baseUrl || LLM_PRESET_DEFAULTS['openrouter'].baseUrl,
    apiKeyEnv: state.llm.apiKeyEnv.trim() || preset.apiKeyEnv || LLM_PRESET_DEFAULTS['openrouter'].apiKeyEnv,
    scoringModel,
    summarizationModel,
  };
}

function hasSelectedSource(state: WizardState, key: string): boolean {
  return state.selectedKeys.includes(key);
}

function buildSimpleExtensionYaml(
  state: WizardState,
  extKey: string,
  options: { keyMap?: Record<string, string> } = {},
): string {
  const ext = REGISTRY[extKey];
  const config = state.config[extKey] ?? {};
  const lines = ['# Generated by Linnet Setup Wizard', ''];
  if (!ext) return lines.join('\n');

  for (const field of ext.setupFields) {
    const outputKey = options.keyMap?.[field.key] ?? field.key;
    const value = config[field.key] ?? field.default ?? (isListField(field) ? [] : '');
    pushYamlValue(lines, outputKey, value);
    lines.push('');
  }

  while (lines.at(-1) === '') lines.pop();
  return lines.join('\n');
}

function buildPostdocSources(terms: string[]): {
  rssSources: Array<{ url: string; name: string }>;
  jinaSources: Array<{ url: string; name: string; type: string }>;
} {
  const selectedTerms = (terms.length ? terms : DEFAULT_POSTDOC_TERMS).slice(0, 3);
  const rssSources = [
    { url: 'https://www.jobs.ac.uk/jobs/academic-or-research/?format=rss', name: 'jobs.ac.uk Research' },
    { url: 'https://www.jobs.ac.uk/jobs/computer-science/?format=rss', name: 'jobs.ac.uk CS' },
    { url: 'https://www.jobs.ac.uk/jobs/artificial-intelligence/?format=rss', name: 'jobs.ac.uk AI' },
    { url: 'https://www.jobs.ac.uk/jobs/mathematics/?format=rss', name: 'jobs.ac.uk Mathematics' },
  ];

  const jinaSources: Array<{ url: string; name: string; type: string }> = [];
  for (const term of selectedTerms) {
    const encoded = encodeURIComponent(term);
    jinaSources.push(
      {
        url: `https://www.findapostdoc.com/search/?Keywords=${encoded}`,
        name: `FindAPostDoc ${term}`,
        type: 'findapostdoc',
      },
      {
        url: `https://academicpositions.com/find-jobs?keywords=${encoded}`,
        name: `AcademicPositions ${term}`,
        type: 'academicpositions',
      },
    );
  }

  jinaSources.push({
    url: 'https://euraxess.ec.europa.eu/jobs/search?f%5B0%5D=offer_type%3Ajob_offer&f%5B1%5D=positions%3Apostdoc_positions',
    name: 'EURAXESS Postdoc',
    type: 'euraxess',
  });

  return { rssSources, jinaSources };
}

// ── YAML generators ──────────────────────────────────────────────────────────

function buildSourcesYaml(state: WizardState): string {
  const order = state.selectedKeys;
  const llm = resolveLlmConfig(state);
  const lines: string[] = ['# Generated by Linnet Setup Wizard', ''];
  const includeArxiv = hasSelectedSource(state, 'arxiv');
  const includeHn = hasSelectedSource(state, 'hacker_news');
  const includeGithub = hasSelectedSource(state, 'github_trending');
  const includeJobs = hasSelectedSource(state, 'postdoc_jobs');

  lines.push('display_order:');
  for (const key of order) lines.push(`  - ${key}`);
  lines.push('');

  for (const ext of EXTENSION_LIST) {
    lines.push(`${ext.key}:`);
    lines.push(`  enabled: ${yamlStr(order.includes(ext.key))}`);
    lines.push('');
  }

  lines.push(`language: ${yamlStr(state.global.language)}`);
  lines.push('');
  lines.push('llm:');
  lines.push(`  provider: ${yamlStr(llm.provider)}`);
  lines.push(`  scoring_model: ${yamlStr(llm.scoringModel)}`);
  lines.push(`  summarization_model: ${yamlStr(llm.summarizationModel)}`);
  lines.push(`  base_url: ${yamlStr(llm.baseUrl)}`);
  lines.push(`  api_key_env: ${yamlStr(llm.apiKeyEnv)}`);
  lines.push('');
  lines.push('pages:');
  lines.push('  base_url: ""');
  lines.push('');

  // Theme
  const bg     = getThemeBg(state);
  const accent = getThemeAccent(state);
  const defaultBg     = '#f4ede0';
  const defaultAccent = '#c43d2a';
  if (bg !== defaultBg || accent !== defaultAccent) {
    lines.push('theme:');
    lines.push(`  bg: ${yamlStr(bg)}`);
    lines.push(`  accent: ${yamlStr(accent)}`);
    lines.push('');
  }
  const dBg     = getThemeDarkBg(state);
  const dAccent = getThemeDarkAccent(state);
  if (dBg !== '#1a1614' || dAccent !== defaultAccent) {
    lines.push('theme_dark:');
    lines.push(`  bg: ${yamlStr(dBg)}`);
    lines.push(`  accent: ${yamlStr(dAccent)}`);
    lines.push('');
  }

  // Weekly / monthly
  lines.push('weekly:');
  for (const key of order) {
    const prefs = state.schedule.weekly[key] ?? { enabled: false, top_n: DEFAULT_TOP_N[key] ?? 5 };
    lines.push(`  ${key}:`);
    lines.push(`    enabled: ${prefs.enabled}`);
    lines.push(`    top_n: ${prefs.top_n}`);
  }
  lines.push('');
  lines.push('monthly:');
  for (const key of order) {
    const prefs = state.schedule.monthly[key] ?? { enabled: false, top_n: DEFAULT_TOP_N[key] ?? 5 };
    lines.push(`  ${key}:`);
    lines.push(`    enabled: ${prefs.enabled}`);
    lines.push(`    top_n: ${prefs.top_n}`);
  }
  lines.push('');
  lines.push('sinks:');
  lines.push('  slack:');
  lines.push(`    enabled: ${state.sinks.slack.enabled}`);
  lines.push('    # Add SLACK_WEBHOOK_URL as a GitHub Actions secret');
  if (includeArxiv) lines.push(`    max_papers: ${state.sinks.slack.max_papers}`);
  if (includeHn) lines.push(`    max_hn: ${state.sinks.slack.max_hn}`);
  if (includeGithub) lines.push(`    max_github: ${state.sinks.slack.max_github}`);
  lines.push('  serverchan:');
  lines.push(`    enabled: ${state.sinks.serverchan.enabled}`);
  lines.push('    # Add SERVERCHAN_SENDKEY as a GitHub Actions secret');
  if (includeArxiv) lines.push(`    max_papers: ${state.sinks.serverchan.max_papers}`);
  if (includeHn) lines.push(`    max_hn: ${state.sinks.serverchan.max_hn}`);
  if (includeGithub) lines.push(`    max_github: ${state.sinks.serverchan.max_github}`);
  if (includeJobs) lines.push(`    max_jobs: ${state.sinks.serverchan.max_jobs}`);

  return lines.join('\n');
}

function buildArxivYaml(state: WizardState): string {
  const selectedProfiles = state.arxiv.presets.filter((key) => key in ARXIV_PROFILES);
  const categories: string[] = [];
  const mustInclude: string[] = [];
  const boostKws: string[] = [];

  for (const key of selectedProfiles) {
    const p = ARXIV_PROFILES[key];
    if (!p) continue;
    categories.push(...p.categories);
    mustInclude.push(...p.must_include);
    boostKws.push(...p.boost_keywords);
  }

  const allCats  = unique([...categories,  ...state.arxiv.customCategories]);
  const allKws   = unique([...mustInclude,  ...state.arxiv.customKeywords]);
  const allBoosts = unique([...boostKws,   ...state.arxiv.customBoosts]);
  const fallbackCategories = allCats.length ? [] : ARXIV_PROFILES['ai_ml'].categories;

  const lines = ['# Generated by Linnet Setup Wizard', ''];
  pushYamlList(lines, 'categories', allCats.length ? allCats : fallbackCategories);
  lines.push('');
  pushYamlList(lines, 'must_include', allKws);
  lines.push('');
  pushYamlList(lines, 'boost_keywords', allBoosts);
  lines.push('');
  lines.push(`llm_score_threshold: ${state.arxiv.threshold}`);
  lines.push(`max_papers_per_run: ${state.arxiv.maxPapers}`);
  return lines.join('\n');
}

function buildHackerNewsYaml(state: WizardState): string {
  return buildSimpleExtensionYaml(state, 'hacker_news');
}

function buildWeatherYaml(state: WizardState): string {
  return buildSimpleExtensionYaml(state, 'weather');
}

function buildGitHubTrendingYaml(state: WizardState): string {
  return buildSimpleExtensionYaml(state, 'github_trending');
}

function buildQuoteOfDayYaml(state: WizardState): string {
  return buildSimpleExtensionYaml(state, 'quote_of_day');
}

function buildHitokotoYaml(state: WizardState): string {
  return buildSimpleExtensionYaml(state, 'hitokoto');
}

function buildPostdocYaml(state: WizardState): string {
  const searchTerms = unique(
    (state.postdoc_jobs.search_terms.length ? state.postdoc_jobs.search_terms : DEFAULT_POSTDOC_TERMS)
      .map(term => term.trim())
      .filter(Boolean),
  );
  const { rssSources, jinaSources } = buildPostdocSources(searchTerms);
  const lines = ['# Generated by Linnet Setup Wizard', ''];

  lines.push('rss_sources:');
  for (const source of rssSources) {
    lines.push(`  - url: ${yamlStr(source.url)}`);
    lines.push(`    name: ${yamlStr(source.name)}`);
  }

  lines.push('');
  lines.push('jina_sources:');
  for (const source of jinaSources) {
    lines.push(`  - url: ${yamlStr(source.url)}`);
    lines.push(`    name: ${yamlStr(source.name)}`);
    lines.push(`    type: ${yamlStr(source.type)}`);
  }

  lines.push('');
  pushYamlList(lines, 'filter_keywords', unique([...searchTerms, 'postdoc', 'research associate', 'fellowship']));
  lines.push('');
  pushYamlList(lines, 'exclude_keywords', DEFAULT_POSTDOC_EXCLUDE);
  lines.push('');
  lines.push(`llm_score_threshold: ${state.postdoc_jobs.threshold}`);

  return lines.join('\n');
}

function buildSupervisorYaml(state: WizardState): string {
  const urls = state.supervisor_updates.urls;
  const lines = ['# Generated by Linnet Setup Wizard', ''];
  if (!urls.length) { lines.push('supervisors: []'); return lines.join('\n'); }
  lines.push('supervisors:');
  for (const url of urls) {
    lines.push(`  - url: ${yamlStr(url)}`);
    lines.push('    name: ""');
  }
  return lines.join('\n');
}

// ── Theme helpers ─────────────────────────────────────────────────────────────

const BG_MAP: Record<string, string> = {
  press: '#f4ede0', morning: '#F2E6CE', stone: '#E8E2D8', white: '#F9F5EE',
};
const ACCENT_MAP: Record<string, string> = {
  robin: '#c43d2a', burgundy: '#8f1d22', terracotta: '#b85a3c', teal: '#2a7a7a',
  indigo: '#3d4d8f', gold: '#9c7520', plum: '#6b3b5e',
};
const DARK_BG_MAP: Record<string, string> = {
  ink: '#1a1614', slate: '#141c22', charcoal: '#1e1e1e',
};

function getThemeBg(s: WizardState): string {
  return s.theme.bgPreset === 'custom' ? s.theme.customBg : (BG_MAP[s.theme.bgPreset] ?? BG_MAP['press']);
}
function getThemeAccent(s: WizardState): string {
  return s.theme.accentPreset === 'custom' ? s.theme.customAccent : (ACCENT_MAP[s.theme.accentPreset] ?? ACCENT_MAP['robin']);
}
function getThemeDarkBg(s: WizardState): string {
  return s.theme.darkBgPreset === 'custom' ? s.theme.customDarkBg : (DARK_BG_MAP[s.theme.darkBgPreset] ?? DARK_BG_MAP['ink']);
}
function getThemeDarkAccent(s: WizardState): string {
  return s.theme.darkAccentPreset === 'custom' ? s.theme.customDarkAccent : (ACCENT_MAP[s.theme.darkAccentPreset] ?? ACCENT_MAP['robin']);
}

function normalizeHexColor(value: string, fallback: string): string {
  return /^#[0-9a-fA-F]{6}$/.test(value.trim()) ? value.trim() : fallback;
}

function hexToRgb(value: string): [number, number, number] {
  const normalized = normalizeHexColor(value, '#000000').slice(1);
  return [
    Number.parseInt(normalized.slice(0, 2), 16),
    Number.parseInt(normalized.slice(2, 4), 16),
    Number.parseInt(normalized.slice(4, 6), 16),
  ];
}

function mixHexColors(a: string, b: string, ratio: number): string {
  const [ar, ag, ab] = hexToRgb(a);
  const [br, bg, bb] = hexToRgb(b);
  const blend = (from: number, to: number) => Math.round(from + ((to - from) * ratio));
  return `#${[blend(ar, br), blend(ag, bg), blend(ab, bb)]
    .map((channel) => channel.toString(16).padStart(2, '0'))
    .join('')}`;
}

function rgbaFromHex(value: string, alpha: number): string {
  const [r, g, b] = hexToRgb(value);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// ── DOM state readers ─────────────────────────────────────────────────────────

function isListField(field: SetupField): boolean {
  return field.type === 'multiselect' || field.type === 'tags' || field.type === 'urls';
}

function getFieldVal<T>(extKey: string, fieldKey: string): T | undefined {
  const el = qs<HTMLInputElement | HTMLSelectElement>(
    `[data-config-for="${extKey}"][data-field="${fieldKey}"], [data-config-for="${extKey}"] [name="${fieldKey}"]`
  );
  if (!el) return undefined;
  if (el instanceof HTMLInputElement && el.type === 'range') return Number(el.value) as unknown as T;
  if (el instanceof HTMLInputElement && el.type === 'number') return Number(el.value) as unknown as T;
  return el.value as unknown as T;
}

function getListVal(container: Element | null): string[] {
  if (!container) return [];
  const raw = (container as HTMLElement).dataset['tags'] ?? (container as HTMLElement).dataset['urls'] ?? '[]';
  try { return JSON.parse(raw) as string[]; } catch { return []; }
}

function readFieldValue(extKey: string, field: SetupField): unknown {
  if (field.type === 'tags' || field.type === 'urls') {
    return getListVal(qs(`[data-config-for="${extKey}"][data-field="${field.key}"]`));
  }

  if (field.type === 'multiselect') {
    return qsa<HTMLInputElement>(
      `[data-config-for="${extKey}"][data-field="${field.key}"] input[type="checkbox"]:checked`,
    ).map(el => el.value);
  }

  return getFieldVal(extKey, field.key);
}

function readRegistryConfig(state: WizardState): void {
  const config: Record<string, Record<string, unknown>> = {};

  for (const key of state.selectedKeys) {
    const ext = REGISTRY[key];
    if (!ext || key === 'arxiv') continue;
    config[key] = {};
    for (const field of ext.setupFields) {
      config[key][field.key] = readFieldValue(key, field);
    }
  }

  state.config = config;
}

function readState(state: WizardState): void {
  // Language
  const langEl = qs<HTMLSelectElement>('[data-global-language]');
  if (langEl) state.global.language = langEl.value;

  // LLM
  const llmProviderEl = qs<HTMLSelectElement>('[data-llm-provider]');
  const llmBaseUrlEl = qs<HTMLInputElement>('[data-llm-base-url]');
  const llmSecretNameEl = qs<HTMLInputElement>('[data-llm-secret-name]');
  const llmScoringModelEl = qs<HTMLInputElement>('[data-llm-scoring-model]');
  const llmSummarizationModelEl = qs<HTMLInputElement>('[data-llm-summarization-model]');
  if (llmProviderEl) state.llm.provider = llmProviderEl.value;
  if (llmBaseUrlEl) state.llm.baseUrl = llmBaseUrlEl.value.trim();
  if (llmSecretNameEl) state.llm.apiKeyEnv = llmSecretNameEl.value.trim();
  if (llmScoringModelEl) state.llm.scoringModel = llmScoringModelEl.value.trim();
  if (llmSummarizationModelEl) state.llm.summarizationModel = llmSummarizationModelEl.value.trim();

  // arXiv
  const arxivPanel = qs('[data-config-for="arxiv"]');
  if (arxivPanel) {
    state.arxiv.presets = qsa<HTMLInputElement>('[name="arxiv_preset"]:checked', arxivPanel).map(el => el.value);
    const threshEl = qs<HTMLInputElement>('[data-arxiv-threshold]');
    if (threshEl) state.arxiv.threshold = Number(threshEl.value);
    const maxEl = qs<HTMLInputElement>('[data-arxiv-max-papers]');
    if (maxEl) state.arxiv.maxPapers = Number(maxEl.value);
    state.arxiv.customKeywords   = getListVal(qs('[data-arxiv-custom-keywords]'));
    state.arxiv.customCategories = getListVal(qs('[data-arxiv-custom-categories]'));
    state.arxiv.customBoosts     = getListVal(qs('[data-arxiv-custom-boosts]'));
  }

  readRegistryConfig(state);

  state.hacker_news.min_score = Number(state.config['hacker_news']?.['min_score']) || 100;
  state.hacker_news.max_items = Number(state.config['hacker_news']?.['max_items']) || 10;
  state.postdoc_jobs.search_terms = Array.isArray(state.config['postdoc_jobs']?.['keywords'])
    ? state.config['postdoc_jobs']?.['keywords'] as string[]
    : [];
  state.postdoc_jobs.threshold = Number(state.config['postdoc_jobs']?.['llm_score_threshold']) || 7;
  state.supervisor_updates.urls = Array.isArray(state.config['supervisor_updates']?.['urls'])
    ? state.config['supervisor_updates']?.['urls'] as string[]
    : [];

  // Schedule
  for (const key of state.selectedKeys) {
    const wEnabled = qs<HTMLInputElement>(`[data-schedule-weekly-enabled="${key}"]`);
    const wTopN    = qs<HTMLInputElement>(`[data-schedule-weekly-topn="${key}"]`);
    const mEnabled = qs<HTMLInputElement>(`[data-schedule-monthly-enabled="${key}"]`);
    const mTopN    = qs<HTMLInputElement>(`[data-schedule-monthly-topn="${key}"]`);
    state.schedule.weekly[key]  = { enabled: !!wEnabled?.checked, top_n: Number(wTopN?.value) || DEFAULT_TOP_N[key] || 5 };
    state.schedule.monthly[key] = { enabled: !!mEnabled?.checked, top_n: Number(mTopN?.value) || DEFAULT_TOP_N[key] || 5 };
  }

  // Sinks
  const slackEnabled = qs<HTMLInputElement>('[data-sink-slack-enabled]');
  state.sinks.slack.enabled    = !!slackEnabled?.checked;
  state.sinks.slack.max_papers = Number(qs<HTMLInputElement>('[data-sink-slack-max-papers]')?.value) || 5;
  state.sinks.slack.max_hn     = Number(qs<HTMLInputElement>('[data-sink-slack-max-hn]')?.value) || 3;
  state.sinks.slack.max_github = Number(qs<HTMLInputElement>('[data-sink-slack-max-github]')?.value) || 3;

  const scEnabled = qs<HTMLInputElement>('[data-sink-sc-enabled]');
  state.sinks.serverchan.enabled    = !!scEnabled?.checked;
  state.sinks.serverchan.max_papers = Number(qs<HTMLInputElement>('[data-sink-sc-max-papers]')?.value) || 5;
  state.sinks.serverchan.max_hn     = Number(qs<HTMLInputElement>('[data-sink-sc-max-hn]')?.value) || 3;
  state.sinks.serverchan.max_github = Number(qs<HTMLInputElement>('[data-sink-sc-max-github]')?.value) || 3;
  state.sinks.serverchan.max_jobs   = Number(qs<HTMLInputElement>('[data-sink-sc-max-jobs]')?.value) || 3;

  // Theme
  state.theme.bgPreset     = qs<HTMLElement>('[data-bg-preset][aria-pressed="true"]')?.dataset['bgPreset'] ?? 'press';
  state.theme.accentPreset = qs<HTMLElement>('[data-accent-preset][aria-pressed="true"]')?.dataset['accentPreset'] ?? 'robin';
  state.theme.customBg     = (qs<HTMLInputElement>('[data-custom-bg]')?.value) ?? '';
  state.theme.customAccent = (qs<HTMLInputElement>('[data-custom-accent]')?.value) ?? '';
  state.theme.customDark   = true;
  state.theme.darkBgPreset     = qs<HTMLElement>('[data-dark-bg-preset][aria-pressed="true"]')?.dataset['darkBgPreset'] ?? 'ink';
  state.theme.darkAccentPreset = qs<HTMLElement>('[data-dark-accent-preset][aria-pressed="true"]')?.dataset['darkAccentPreset'] ?? 'robin';
  state.theme.customDarkBg     = (qs<HTMLInputElement>('[data-custom-dark-bg]')?.value) ?? '';
  state.theme.customDarkAccent = (qs<HTMLInputElement>('[data-custom-dark-accent]')?.value) ?? '';
}

// ── Tags/URLs widget ──────────────────────────────────────────────────────────

function initTagsWidget(container: Element): void {
  const list    = qs<HTMLElement>('[data-tags-list], [data-urls-list]', container);
  const input   = qs<HTMLInputElement>('.wz-tags__input, .wz-urls__input', container);
  const addBtn  = qs<HTMLButtonElement>('[data-tags-add], [data-urls-add]', container);
  const emptyEl = qs<HTMLElement>('.wz-tags__empty, .wz-urls__empty', container);
  if (!list || !input || !addBtn) return;
  const listEl = list;
  const inputEl = input;
  const addButton = addBtn;

  function currentTags(): string[] {
    const raw = (container as HTMLElement).dataset['tags'] ?? (container as HTMLElement).dataset['urls'] ?? '[]';
    try { return JSON.parse(raw) as string[]; } catch { return []; }
  }

  function saveTags(tags: string[]): void {
    const isUrls = container.classList.contains('wz-urls');
    if (isUrls) (container as HTMLElement).dataset['urls'] = JSON.stringify(tags);
    else        (container as HTMLElement).dataset['tags']  = JSON.stringify(tags);
  }

  function renderTags(tags: string[]): void {
    if (emptyEl) emptyEl.hidden = tags.length > 0;
    const tagEls = qsa<HTMLElement>('.wz-tag, .wz-url-item', listEl);
    tagEls.forEach(el => el.remove());
    for (const tag of tags) {
      const el = document.createElement('span');
      el.className = container.classList.contains('wz-urls') ? 'wz-url-item' : 'wz-tag';
      el.textContent = tag;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = container.classList.contains('wz-urls') ? 'wz-url-item__remove' : 'wz-tag__remove';
      btn.textContent = '×';
      btn.addEventListener('click', () => {
        const cur = currentTags().filter(t => t !== tag);
        saveTags(cur);
        renderTags(cur);
      });
      el.appendChild(btn);
      listEl.insertBefore(el, emptyEl ?? null);
    }
  }

  function addTag(): void {
    const val = inputEl.value.trim();
    if (!val) return;
    const tags = currentTags();
    if (!tags.includes(val)) {
      tags.push(val);
      saveTags(tags);
      renderTags(tags);
    }
    inputEl.value = '';
    inputEl.focus();
  }

  addButton.addEventListener('click', addTag);
  inputEl.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); addTag(); }
  });

  renderTags(currentTags());
}

// ── Drag-to-reorder (order list, step 1) ─────────────────────────────────────

function initDragReorder(list: HTMLElement, onReorder: (keys: string[]) => void): void {
  let dragKey = '';

  list.addEventListener('dragstart', (e: DragEvent) => {
    const item = (e.target as HTMLElement).closest<HTMLElement>('.wz-order-item');
    if (!item) return;
    dragKey = item.dataset['key'] ?? '';
    (e.dataTransfer as DataTransfer).effectAllowed = 'move';
  });

  list.addEventListener('dragover', (e: DragEvent) => {
    e.preventDefault();
    (e.dataTransfer as DataTransfer).dropEffect = 'move';
    const item = (e.target as HTMLElement).closest<HTMLElement>('.wz-order-item');
    qsa<HTMLElement>('.wz-order-item--drag-over', list).forEach(el => el.classList.remove('wz-order-item--drag-over'));
    if (item && item.dataset['key'] !== dragKey) item.classList.add('wz-order-item--drag-over');
  });

  list.addEventListener('drop', (e: DragEvent) => {
    e.preventDefault();
    const target = (e.target as HTMLElement).closest<HTMLElement>('.wz-order-item');
    if (!target || target.dataset['key'] === dragKey) return;
    const items  = qsa<HTMLElement>('.wz-order-item', list);
    const keys   = items.map(el => el.dataset['key'] ?? '');
    const fromI  = keys.indexOf(dragKey);
    const toI    = keys.indexOf(target.dataset['key'] ?? '');
    if (fromI < 0 || toI < 0) return;
    keys.splice(fromI, 1);
    keys.splice(toI, 0, dragKey);
    onReorder(keys);
  });

  list.addEventListener('dragend', () => {
    qsa<HTMLElement>('.wz-order-item--drag-over', list).forEach(el => el.classList.remove('wz-order-item--drag-over'));
  });
}

// ── Main wizard controller ────────────────────────────────────────────────────

export function initWizard(): void {
  const shell = qs<HTMLElement>('[data-wizard]');
  if (!shell) return;

  const locale = (shell.dataset['locale'] ?? 'en') as 'en' | 'zh';
  const state  = createInitialState();
  if (locale === 'zh') state.global.language = 'zh';
  const TOTAL_STEPS = 6;

  const blurbsRaw = shell.dataset['stepBlurbs'] ?? '[]';
  let blurbs: string[] = [];
  try {
    blurbs = JSON.parse(blurbsRaw) as string[];
  } catch {
    blurbs = [];
  }

  // DOM refs
  const backBtn  = qs<HTMLButtonElement>('[data-wizard-back]', shell);
  const nextBtn  = qs<HTMLButtonElement>('[data-wizard-next]', shell);
  const pillEl   = qs('[data-step-pill]',   shell);
  const blurbEl  = qs('[data-step-blurb]',  shell);
  const fillEl   = qs<HTMLElement>('[data-progress-fill]', shell);
  const orderList = qs<HTMLElement>('[data-order-list]', shell);
  const llmProviderSelect = qs<HTMLSelectElement>('[data-llm-provider]', shell);
  const llmBaseUrlInput = qs<HTMLInputElement>('[data-llm-base-url]', shell);
  const llmSecretNameInput = qs<HTMLInputElement>('[data-llm-secret-name]', shell);
  const llmApiKeyInput = qs<HTMLInputElement>('[data-llm-api-key]', shell);
  const llmApiKeyMirrorInput = qs<HTMLInputElement>('[data-llm-api-key-mirror]', shell);
  const llmApiKeyHintEl = qs<HTMLElement>('[data-llm-api-key-hint]', shell);
  const llmApiKeyStep6HintEl = qs<HTMLElement>('[data-llm-api-key-step6-hint]', shell);
  const llmScoringModelInput = qs<HTMLInputElement>('[data-llm-scoring-model]', shell);
  const llmSummarizationModelInput = qs<HTMLInputElement>('[data-llm-summarization-model]', shell);
  const llmModelOptionsEl = qs<HTMLDataListElement>('[data-llm-model-options]', shell);
  const llmProviderNoteEl = qs<HTMLElement>('[data-llm-provider-note]', shell);
  const deployRepoInput = qs<HTMLInputElement>('[data-deploy-repo]', shell);
  const deployTokenInput = qs<HTMLInputElement>('[data-deploy-token]', shell);
  const deploySubmitBtn = qs<HTMLButtonElement>('[data-deploy-submit]', shell);
  const deployPreviewEl = qs<HTMLElement>('[data-deploy-preview]', shell);
  const deployStatusEl = qs<HTMLElement>('[data-deploy-status]', shell);
  const deploySuccessEl = qs<HTMLElement>('[data-deploy-success]', shell);
  const modeButtons = qsa<HTMLButtonElement>('[data-setup-mode-btn]', shell);
  const modePanels = qsa<HTMLElement>('[data-setup-mode-panel]', shell);
  const connectBtn = qs<HTMLButtonElement>('[data-github-connect-btn]', shell);
  const disconnectBtn = qs<HTMLButtonElement>('[data-github-disconnect-btn]', shell);
  const patInput = qs<HTMLInputElement>('[data-github-pat-input]', shell);
  const authStatusEl = qs<HTMLElement>('[data-github-auth-status]', shell);
  const authSummaryEl = qs<HTMLElement>('[data-github-auth-summary]', shell);
  const repoOptionsEl = qs<HTMLDataListElement>('[data-deploy-repo-options]', shell);
  const connectedNoticeEl = qs<HTMLElement>('[data-github-connected-notice]', shell);
  const connectRequiredEl = qs<HTMLElement>('[data-github-connect-required]', shell);
  const connectDeployCardEl = qs<HTMLElement>('[data-connect-deploy-card]', shell);
  const manualNextStepsEl = qs<HTMLElement>('[data-manual-next-steps]', shell);
  const connectNextStepsEl = qs<HTMLElement>('[data-connect-next-steps]', shell);
  const manualLlmSecretNameEls = qsa<HTMLElement>('[data-manual-llm-secret-name]', shell);
  const llmSecretCodeEls = qsa<HTMLElement>('[data-llm-secret-code]', shell);
  let latestOutputs: OutputBlock[] = [];
  let setupMode: SetupMode = loadJson<SetupMode>(WIZARD_SETUP_MODE_KEY) ?? 'connect';
  let githubSession = loadJson<GitHubSession>(GITHUB_AUTH_SESSION_KEY);

  // ── Navigation ──────────────────────────────────────────────

  function showStep(n: number): void {
    qsa<HTMLElement>('.wz-step', shell).forEach(el => {
      const step = Number(el.dataset['step']);
      el.setAttribute('aria-hidden', step === n ? 'false' : 'true');
    });
    qsa<HTMLElement>('[data-step-btn]', shell).forEach(btn => {
      const step = Number(btn.dataset['stepBtn']);
      btn.setAttribute('aria-current', step === n ? 'step' : 'false');
      btn.dataset['complete'] = step < n ? 'true' : 'false';
    });
    if (fillEl) fillEl.style.width = `${((n - 1) / (TOTAL_STEPS - 1)) * 100}%`;
    if (pillEl) pillEl.textContent = locale === 'zh' ? `第 ${n} 步 / 共 ${TOTAL_STEPS} 步` : `Step ${n} of ${TOTAL_STEPS}`;
    if (blurbEl && blurbs[n - 1]) blurbEl.textContent = blurbs[n - 1];
    if (backBtn) backBtn.disabled = n === 1;
    if (nextBtn) nextBtn.textContent = n === TOTAL_STEPS
      ? (locale === 'zh' ? '重新开始' : 'Start over')
      : (locale === 'zh' ? '下一步' : 'Next');
  }

  function setDeployStatus(kind: 'info' | 'warn' | 'success', message: string): void {
    if (!deployStatusEl) return;
    deployStatusEl.hidden = false;
    deployStatusEl.className = `wz-notice wz-notice--${kind}`;
    deployStatusEl.textContent = message;
  }

  function clearDeployStatus(): void {
    if (deployStatusEl) {
      deployStatusEl.hidden = true;
      deployStatusEl.textContent = '';
      deployStatusEl.className = 'wz-notice wz-notice--info';
    }
    if (deploySuccessEl) deploySuccessEl.hidden = true;
  }

  function setAuthStatus(kind: 'info' | 'warn' | 'success', message: string): void {
    if (!authStatusEl) return;
    authStatusEl.className = `wz-notice wz-notice--${kind}`;
    authStatusEl.textContent = message;
  }

  function saveSetupMode(mode: SetupMode): void {
    setupMode = mode;
    saveJson(WIZARD_SETUP_MODE_KEY, mode);
  }

  function saveGitHubSession(session: GitHubSession | null): void {
    githubSession = session;
    if (session) saveJson(GITHUB_AUTH_SESSION_KEY, session);
    else removeJson(GITHUB_AUTH_SESSION_KEY);
  }

  function getSelectedLlmProviderOption(): HTMLOptionElement | null {
    return llmProviderSelect?.selectedOptions?.[0] ?? null;
  }

  function getSuggestedLlmModels(option: HTMLOptionElement | null): string[] {
    if (!option?.dataset['models']) return [];
    try {
      return JSON.parse(option.dataset['models']) as string[];
    } catch {
      return [];
    }
  }

  function currentLlmSecretName(): string {
    return llmSecretNameInput?.value.trim()
      || getSelectedLlmProviderOption()?.dataset['secretName']
      || 'OPENROUTER_API_KEY';
  }

  function syncLlmSecretLabels(): void {
    const secretName = currentLlmSecretName();
    manualLlmSecretNameEls.forEach((el) => {
      el.textContent = secretName;
    });
    llmSecretCodeEls.forEach((el) => {
      el.textContent = secretName;
    });
    if (llmApiKeyHintEl) {
      llmApiKeyHintEl.textContent = locale === 'zh'
        ? `这个值只会在部署时作为 ${secretName} 写入 GitHub Actions Secrets，不会写进 YAML。`
        : `This value is written as ${secretName} during deploy and is never stored in YAML.`;
    }
    if (llmApiKeyStep6HintEl) {
      llmApiKeyStep6HintEl.textContent = locale === 'zh'
        ? `这和 Step 3 里的 ${secretName} 是同一个值；如果前面没填，这里也可以补上。`
        : `This is the same ${secretName} value from Step 3. If you skipped it earlier, you can fill it here as well.`;
    }
  }

  function currentLlmApiKeyValue(): string {
    return llmApiKeyInput?.value.trim()
      || llmApiKeyMirrorInput?.value.trim()
      || '';
  }

  function syncLlmApiKeyInputs(source?: HTMLInputElement | null): void {
    const value = source?.value ?? currentLlmApiKeyValue();
    if (llmApiKeyInput && llmApiKeyInput !== source) llmApiKeyInput.value = value;
    if (llmApiKeyMirrorInput && llmApiKeyMirrorInput !== source) llmApiKeyMirrorInput.value = value;
  }

  function renderLlmModelOptions(models: string[]): void {
    if (!llmModelOptionsEl) return;
    llmModelOptionsEl.innerHTML = models
      .map((model) => `<option value="${escapeHtml(model)}"></option>`)
      .join('');
  }

  function applyLlmProviderPreset(resetModels: boolean): void {
    const option = getSelectedLlmProviderOption();
    if (!option) return;

    if (llmBaseUrlInput) llmBaseUrlInput.value = option.dataset['baseUrl'] ?? '';
    if (llmSecretNameInput) llmSecretNameInput.value = option.dataset['secretName'] ?? 'LLM_API_KEY';
    if (resetModels || !llmScoringModelInput?.value.trim()) {
      if (llmScoringModelInput) llmScoringModelInput.value = option.dataset['scoringModel'] ?? '';
    }
    if (resetModels || !llmSummarizationModelInput?.value.trim()) {
      if (llmSummarizationModelInput) {
        llmSummarizationModelInput.value = option.dataset['summarizationModel'] ?? '';
      }
    }

    renderLlmModelOptions(getSuggestedLlmModels(option));
    if (llmProviderNoteEl) llmProviderNoteEl.textContent = option.dataset['note'] ?? '';
    syncLlmSecretLabels();
  }

  function guessCurrentRepository(
    repositories: GitHubRepoOption[],
    userLogin?: string,
  ): string {
    const pathParts = window.location.pathname
      .split('/')
      .map((part) => part.trim())
      .filter(Boolean);

    const repoName = pathParts.find((part) =>
      repositories.some((repo) => repo.repo.toLowerCase() === part.toLowerCase()),
    );
    if (!repoName) return '';

    const preferredOwner = userLogin?.toLowerCase();
    const exactMatch = repositories.find((repo) =>
      repo.repo.toLowerCase() === repoName.toLowerCase()
      && (!preferredOwner || repo.owner.toLowerCase() === preferredOwner),
    );
    if (exactMatch) return exactMatch.fullName;

    return repositories.find((repo) => repo.repo.toLowerCase() === repoName.toLowerCase())?.fullName ?? '';
  }

  function updateRepoSuggestions(): void {
    if (!repoOptionsEl) return;
    repoOptionsEl.innerHTML = '';
    for (const repo of githubSession?.repositories ?? []) {
      const option = document.createElement('option');
      option.value = repo.fullName;
      option.label = repo.htmlUrl;
      repoOptionsEl.appendChild(option);
    }

    if (!deployRepoInput || !githubSession) return;

    const availableRepos = new Set(githubSession.repositories.map((repo) => repo.fullName));
    const guessedRepo = guessCurrentRepository(githubSession.repositories, githubSession.user?.login);
    if (
      (!githubSession.selectedRepo || !availableRepos.has(githubSession.selectedRepo))
      && guessedRepo
    ) {
      githubSession.selectedRepo = guessedRepo;
      saveGitHubSession(githubSession);
    }

    const oldVal = deployRepoInput.value;
    if (!deployRepoInput.value.trim()) {
      deployRepoInput.value = githubSession.selectedRepo
        || guessedRepo
        || githubSession.repositories[0]?.fullName
        || '';
    }
    if (deployRepoInput.value !== oldVal) {
      renderDeployPreview();
    }
  }

  function renderSetupMode(): void {
    modeButtons.forEach((button) => {
      const mode = (button.dataset['setupModeBtn'] ?? 'manual') as SetupMode;
      button.setAttribute('aria-pressed', String(mode === setupMode));
    });

    modePanels.forEach((panel) => {
      const mode = (panel.dataset['setupModePanel'] ?? 'manual') as SetupMode;
      panel.hidden = mode !== setupMode;
    });

    if (connectDeployCardEl) connectDeployCardEl.hidden = setupMode !== 'connect';
    if (manualNextStepsEl) manualNextStepsEl.hidden = setupMode !== 'manual';
    if (connectNextStepsEl) connectNextStepsEl.hidden = setupMode !== 'connect';
  }

  function renderGitHubSession(): void {
    const connected = Boolean(githubSession?.token);
    if (disconnectBtn) disconnectBtn.hidden = !connected;
    if (connectedNoticeEl) connectedNoticeEl.hidden = !connected;
    if (connectRequiredEl) connectRequiredEl.hidden = connected || setupMode !== 'connect';
    if (deploySubmitBtn) deploySubmitBtn.disabled = setupMode === 'connect' && !connected;

    // Update Connect chip status
    const connectChip = qs<HTMLElement>('[data-setup-mode-btn="connect"]', shell);
    if (connectChip) {
      const meta = qs<HTMLElement>('.wz-entry-chip__meta', connectChip);
      if (meta) {
        if (connected) {
          meta.textContent = locale === 'zh' ? '● 已连接' : '● Connected';
          meta.style.color = 'var(--accent)';
        } else {
          meta.textContent = locale === 'zh' ? '浏览器授权 + 仓库直写' : 'Browser auth + direct repo write';
          meta.style.color = '';
        }
      }
    }

    if (connected && authSummaryEl && githubSession) {
      const count = githubSession.repositories.length;
      const userName = githubSession.user?.name || githubSession.user?.login || '';
      const userHtml = githubSession.user ? `
        <div class="wz-user-badge">
          <img src="${githubSession.user.avatarUrl}" alt="${githubSession.user.login}" class="wz-user-badge__avatar" />
          <div class="wz-user-badge__info">
            <div class="wz-user-badge__name">${userName}</div>
            <div class="wz-user-badge__meta">@${githubSession.user.login} · ${count} ${locale === 'zh' ? '个仓库' : 'repositories'}</div>
          </div>
        </div>
      ` : '';

      authSummaryEl.innerHTML = `
        ${userHtml}
        <p style="margin-top:12px">
          ${locale === 'zh'
            ? `已连接 GitHub。当前会话可访问 ${count} 个仓库；到第 6 步时只需要选择其中一个目标仓库即可。`
            : `GitHub connected. This browser session can access ${count} repositories; at Step 6 you only need to choose the target repository.`}
        </p>
      `;
      setAuthStatus(
        'success',
        locale === 'zh'
          ? 'GitHub 授权已完成。现在可以放心继续填写向导，最后一步直接部署。'
          : 'GitHub authorization completed. You can continue the wizard and deploy directly at the end.',
      );
    } else if (authSummaryEl) {
      authSummaryEl.textContent = locale === 'zh'
        ? '未连接时，你仍然可以完成向导并导出配置，但需要自己提交文件和 secrets。'
        : 'You can still complete the wizard without connecting, but you will commit files and secrets yourself.';
      setAuthStatus(
        'info',
        locale === 'zh'
          ? '粘贴一个 fine-grained Personal Access Token 即可启用一键部署。Token 只保存在当前浏览器标签的 sessionStorage 中。'
          : 'Paste a fine-grained Personal Access Token to enable one-click deploy. The token is kept only in this tab\u2019s sessionStorage.',
      );
    }

    updateRepoSuggestions();
    renderDeployPreview();
  }

  async function connectWithPat(token: string): Promise<void> {
    const trimmed = token.trim();
    if (!trimmed) {
      setAuthStatus(
        'warn',
        locale === 'zh' ? '请先粘贴 Personal Access Token。' : 'Please paste a Personal Access Token first.',
      );
      return;
    }
    if (!looksLikePat(trimmed)) {
      setAuthStatus(
        'warn',
        locale === 'zh'
          ? 'Token 格式不像 GitHub PAT（应以 github_pat_ 或 ghp_ 开头）。'
          : 'Token does not look like a GitHub PAT (should start with github_pat_ or ghp_).',
      );
      return;
    }
    setAuthStatus(
      'info',
      locale === 'zh' ? '正在校验 token 并读取仓库列表…' : 'Verifying token and loading repositories…',
    );
    try {
      const user = await getCurrentUser({ token: trimmed });
      const repositories = await listAccessibleRepositories({ token: trimmed });
      const selectedRepo = guessCurrentRepository(repositories, user.login) || repositories[0]?.fullName || '';
      saveGitHubSession({
        token: trimmed,
        repositories,
        selectedRepo,
        user,
      });
      if (patInput) patInput.value = '';
      renderGitHubSession();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setAuthStatus(
        'warn',
        (locale === 'zh' ? 'Token 校验失败：' : 'Token verification failed: ') + message,
      );
      saveGitHubSession(null);
    }
  }

  function requiredDeploySecretNames(): string[] {
    readState(state);
    const names = [resolveLlmConfig(state).apiKeyEnv];
    if (state.selectedKeys.includes('quote_of_day')) names.push('API_NINJAS_KEY');
    if (state.sinks.slack.enabled) names.push('SLACK_WEBHOOK_URL');
    if (state.sinks.serverchan.enabled) names.push('SERVERCHAN_SENDKEY');
    return unique(names);
  }

  function syncDeploySecretRows(): void {
    const required = new Set(requiredDeploySecretNames());
    qsa<HTMLElement>('[data-deploy-secret-row]', shell).forEach((row) => {
      const secretName = row.dataset['deploySecretRow'] ?? '';
      row.hidden = !required.has(secretName);
    });
  }

  function buildDeploySecrets(): Array<{ name: string; value: string }> {
    readState(state);
    const llmSecretName = resolveLlmConfig(state).apiKeyEnv;
    const secrets = [{
      name: llmSecretName,
      value: currentLlmApiKeyValue(),
    }];

    for (const name of requiredDeploySecretNames()) {
      if (name === llmSecretName) continue;
      const input = qs<HTMLInputElement>(`[data-deploy-secret="${name}"]`, shell);
      secrets.push({ name, value: input?.value.trim() ?? '' });
    }

    return secrets;
  }

  function renderDeployPreview(): void {
    if (!deployPreviewEl) return;
    const repo = parseRepoInput(deployRepoInput?.value ?? '') ?? { owner: 'OWNER', repo: 'REPO' };
    const preview = buildGitHubCallPreview({
      owner: repo.owner,
      repo: repo.repo,
      files: latestOutputs.map(({ path, body }) => ({ path, body })),
      secrets: buildDeploySecrets().map(({ name, value }) => ({ name, value })),
    });
    deployPreviewEl.textContent = preview.join('\n');
  }

  modeButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const nextMode = (button.dataset['setupModeBtn'] ?? 'manual') as SetupMode;
      saveSetupMode(nextMode);
      renderSetupMode();
      renderGitHubSession();
    });
  });

  connectBtn?.addEventListener('click', async () => {
    await connectWithPat(patInput?.value ?? '');
  });

  patInput?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      void connectWithPat(patInput.value);
    }
  });

  disconnectBtn?.addEventListener('click', () => {
    saveGitHubSession(null);
    renderGitHubSession();
    clearDeployStatus();
  });

  nextBtn?.addEventListener('click', () => {
    if (state.currentStep === TOTAL_STEPS) {
      state.currentStep = 1;
      showStep(1);
      return;
    }
    if (state.currentStep === TOTAL_STEPS - 1) {
      readState(state);
      renderOutputs(state);
    }
    state.currentStep = Math.min(state.currentStep + 1, TOTAL_STEPS);
    if (state.currentStep === 2) syncConfigPanels();
    if (state.currentStep === 3) syncScheduleRows();
    showStep(state.currentStep);
  });

  backBtn?.addEventListener('click', () => {
    state.currentStep = Math.max(state.currentStep - 1, 1);
    showStep(state.currentStep);
  });

  qsa<HTMLElement>('[data-step-btn]', shell).forEach(btn => {
    btn.addEventListener('click', () => {
      const target = Number(btn.dataset['stepBtn']);
      if (target < state.currentStep) {
        state.currentStep = target;
        showStep(target);
      }
    });
  });

  // ── Step 1: Extension picker ─────────────────────────────────

  function renderOrderList(): void {
    if (!orderList) return;
    orderList.innerHTML = '';
    for (const key of state.selectedKeys) {
      const ext = REGISTRY[key];
      const name = locale === 'zh' ? (ext?.displayNameZh ?? ext?.displayName ?? key) : (ext?.displayName ?? key);
      const item = document.createElement('div');
      item.className  = 'wz-order-item';
      item.draggable  = true;
      item.dataset['key'] = key;
      item.innerHTML = `<span class="wz-order-item__handle">⠿</span><span class="wz-order-item__name">${escapeHtml(name)}</span>`;
      orderList.appendChild(item);
    }
  }

  // Mark pre-rendered cards selected/deselected
  function syncCards(): void {
    qsa<HTMLElement>('[data-ext-key]', shell).forEach(card => {
      const key = card.dataset['extKey'] ?? '';
      const selected = state.selectedKeys.includes(key);
      card.setAttribute('aria-pressed', String(selected));
    });
  }

  // Card click: toggle selection
  qsa<HTMLElement>('[data-ext-key]', shell).forEach(card => {
    card.addEventListener('click', () => {
      const key = card.dataset['extKey'] ?? '';
      if (state.selectedKeys.includes(key)) {
        state.selectedKeys = state.selectedKeys.filter(k => k !== key);
      } else {
        state.selectedKeys.push(key);
      }
      syncCards();
      renderOrderList();
      syncConfigPanels();
      syncScheduleRows();
      syncSinkSourceFields();
    });
  });

  // Search
  qs<HTMLInputElement>('[data-ext-search]', shell)?.addEventListener('input', (e) => {
    const q = (e.target as HTMLInputElement).value.toLowerCase();
    let visible = 0;
    qsa<HTMLElement>('[data-ext-key]', shell).forEach(card => {
      const tags = card.dataset['extTags'] ?? '';
      const name = card.querySelector('.wz-ext-card__name')?.textContent?.toLowerCase() ?? '';
      const show = !q || name.includes(q) || tags.includes(q);
      (card as HTMLElement).hidden = !show;
      if (show) visible++;
    });
    const emptyEl = qs('[data-ext-empty]', shell);
    if (emptyEl) (emptyEl as HTMLElement).hidden = visible > 0;
  });

  // Category filter
  qsa<HTMLElement>('[data-cat]', shell).forEach(chip => {
    chip.addEventListener('click', () => {
      const cat = chip.dataset['cat'] ?? 'all';
      qsa<HTMLElement>('[data-cat]', shell).forEach(c => {
        c.setAttribute('aria-pressed', 'false');
        c.classList.remove('wz-chip--active');
      });
      chip.setAttribute('aria-pressed', 'true');
      chip.classList.add('wz-chip--active');
      qsa<HTMLElement>('[data-ext-key]', shell).forEach(card => {
        (card as HTMLElement).hidden = cat !== 'all' && card.dataset['extCat'] !== cat;
      });
    });
  });

  if (orderList) {
    initDragReorder(orderList, (keys) => {
      state.selectedKeys = keys;
      renderOrderList();
      syncConfigPanels();
      syncScheduleRows();
      syncSinkSourceFields();
    });
  }

  // ── Step 2: Config panel sync ────────────────────────────────

  function syncConfigPanels(): void {
    qsa<HTMLElement>('.wz-config-panel', shell).forEach(panel => {
      const key = panel.dataset['configFor'] ?? '';
      panel.hidden = !state.selectedKeys.includes(key);
    });
  }

  // ── Step 3: Schedule row sync ────────────────────────────────

  function syncScheduleRows(): void {
    qsa<HTMLElement>('[data-schedule-for]', shell).forEach(row => {
      const key = row.dataset['scheduleFor'] ?? '';
      row.hidden = !state.selectedKeys.includes(key);
    });
  }

  // Ensure schedule state initialized for selected keys
  function ensureScheduleState(): void {
    for (const key of state.selectedKeys) {
      if (!state.schedule.weekly[key]) {
        const ext = REGISTRY[key];
        state.schedule.weekly[key]  = { enabled: ext?.weeklyDefault ?? false, top_n: ext?.weeklyTopN ?? DEFAULT_TOP_N[key] ?? 5 };
        state.schedule.monthly[key] = { enabled: ext?.monthlyDefault ?? false, top_n: ext?.monthlyTopN ?? DEFAULT_TOP_N[key] ?? 5 };
      }
    }
  }

  // ── Step 4: Sink field visibility ────────────────────────────

  function initSinkToggles(): void {
    const slackCheck = qs<HTMLInputElement>('[data-sink-slack-enabled]');
    const slackFields = qs<HTMLElement>('[data-sink-slack-fields]');
    const scCheck    = qs<HTMLInputElement>('[data-sink-sc-enabled]');
    const scFields   = qs<HTMLElement>('[data-sink-sc-fields]');

    function toggle(check: HTMLInputElement | null, fields: HTMLElement | null): void {
      if (!check || !fields) return;
      fields.hidden = !check.checked;
      check.addEventListener('change', () => { fields.hidden = !check.checked; });
    }

    toggle(slackCheck, slackFields);
    toggle(scCheck, scFields);
  }

  function syncSinkSourceFields(): void {
    qsa<HTMLElement>('[data-sink-limit-for]', shell).forEach((field) => {
      const key = field.dataset['sinkLimitFor'] ?? '';
      field.hidden = !hasSelectedSource(state, key);
    });
  }

  // ── Step 5: Theme preset toggles ────────────────────────────

  function renderThemePreview(): void {
    readState(state);

    const applyPreview = (
      selector: string,
      palette: { bg: string; paper: string; ink: string; soft: string; accent: string; rule: string; glow: string },
    ): void => {
      const preview = qs<HTMLElement>(selector, shell);
      if (!preview) return;
      preview.style.setProperty('--preview-bg', palette.bg);
      preview.style.setProperty('--preview-paper', palette.paper);
      preview.style.setProperty('--preview-ink', palette.ink);
      preview.style.setProperty('--preview-soft', palette.soft);
      preview.style.setProperty('--preview-accent', palette.accent);
      preview.style.setProperty('--preview-rule', palette.rule);
      preview.style.setProperty('--preview-glow', palette.glow);
    };

    const lightBg = normalizeHexColor(getThemeBg(state), BG_MAP['press']);
    const lightAccent = normalizeHexColor(getThemeAccent(state), ACCENT_MAP['robin']);
    applyPreview('[data-theme-preview="light"]', {
      bg: lightBg,
      paper: mixHexColors(lightBg, '#ffffff', 0.7),
      ink: '#1a1814',
      soft: '#4c4439',
      accent: lightAccent,
      rule: rgbaFromHex('#1a1814', 0.12),
      glow: rgbaFromHex(lightAccent, 0.18),
    });

    const darkBg = normalizeHexColor(getThemeDarkBg(state), DARK_BG_MAP['ink']);
    const darkAccent = normalizeHexColor(getThemeDarkAccent(state), ACCENT_MAP['robin']);
    applyPreview('[data-theme-preview="dark"]', {
      bg: darkBg,
      paper: mixHexColors(darkBg, '#ffffff', 0.1),
      ink: '#f0e7d4',
      soft: '#d4c9b3',
      accent: darkAccent,
      rule: rgbaFromHex('#f0e7d4', 0.14),
      glow: rgbaFromHex(darkAccent, 0.24),
    });
  }

  function initThemePresets(): void {
    function setupPresetGroup(selector: string, customRowSel: string): void {
      qsa<HTMLElement>(selector, shell).forEach(btn => {
        btn.addEventListener('click', () => {
          qsa<HTMLElement>(selector, shell).forEach(b => b.setAttribute('aria-pressed', 'false'));
          btn.setAttribute('aria-pressed', 'true');
          const isCustom = btn.dataset['bgPreset'] === 'custom'
            || btn.dataset['accentPreset'] === 'custom'
            || btn.dataset['darkBgPreset'] === 'custom'
            || btn.dataset['darkAccentPreset'] === 'custom';
          const row = qs<HTMLElement>(customRowSel, shell);
          if (row) row.hidden = !isCustom;
          renderThemePreview();
        });
      });
    }

    setupPresetGroup('[data-bg-preset]',          '[data-custom-bg-row]');
    setupPresetGroup('[data-accent-preset]',       '[data-custom-accent-row]');
    setupPresetGroup('[data-dark-bg-preset]',      '[data-custom-dark-bg-row]');
    setupPresetGroup('[data-dark-accent-preset]',  '[data-custom-dark-accent-row]');

    // Sync color pickers ↔ text inputs
    function syncColorPair(pickerSel: string, textSel: string): void {
      const picker = qs<HTMLInputElement>(pickerSel, shell);
      const text   = qs<HTMLInputElement>(textSel, shell);
      if (!picker || !text) return;
      picker.addEventListener('input', () => {
        text.value = picker.value;
        renderThemePreview();
      });
      text.addEventListener('input', () => {
        if (/^#[0-9a-fA-F]{6}$/.test(text.value)) picker.value = text.value;
        renderThemePreview();
      });
    }
    syncColorPair('[data-custom-bg-picker]',          '[data-custom-bg]');
    syncColorPair('[data-custom-accent-picker]',      '[data-custom-accent]');
    syncColorPair('[data-custom-dark-bg-picker]',     '[data-custom-dark-bg]');
    syncColorPair('[data-custom-dark-accent-picker]', '[data-custom-dark-accent]');

    renderThemePreview();
  }

  // ── Step 6: YAML output ──────────────────────────────────────

  function renderOutputs(s: WizardState): void {
    ensureScheduleState();

    const outputs: OutputBlock[] = [
      {
        path: 'config/sources.yaml',
        desc: locale === 'zh' ? '主要开关、显示顺序、语言、汇总偏好和推送配置。' : 'Main switches, display order, language, rollup preferences, and sink config.',
        body: buildSourcesYaml(s),
      },
    ];

    if (s.selectedKeys.includes('arxiv')) outputs.push({
      path: 'config/extensions/arxiv.yaml',
      desc: locale === 'zh' ? 'arXiv 分类、关键词和评分阈值。' : 'arXiv categories, keywords, and score threshold.',
      body: buildArxivYaml(s),
    });
    if (s.selectedKeys.includes('weather')) outputs.push({
      path: 'config/extensions/weather.yaml',
      desc: locale === 'zh' ? '天气城市与时区配置。' : 'Weather city and timezone settings.',
      body: buildWeatherYaml(s),
    });
    if (s.selectedKeys.includes('hacker_news')) outputs.push({
      path: 'config/extensions/hacker_news.yaml',
      desc: locale === 'zh' ? 'HN 分数阈值和最多条目数。' : 'HN score threshold and max stories.',
      body: buildHackerNewsYaml(s),
    });
    if (s.selectedKeys.includes('github_trending')) outputs.push({
      path: 'config/extensions/github_trending.yaml',
      desc: locale === 'zh' ? 'GitHub 趋势仓库数量与语言过滤。' : 'GitHub Trending repo count and language filter.',
      body: buildGitHubTrendingYaml(s),
    });
    if (s.selectedKeys.includes('postdoc_jobs')) outputs.push({
      path: 'config/extensions/postdoc_jobs.yaml',
      desc: locale === 'zh' ? '职位来源、过滤关键词与相关性阈值。' : 'Job sources, filter keywords, and relevance threshold.',
      body: buildPostdocYaml(s),
    });
    if (s.selectedKeys.includes('quote_of_day')) outputs.push({
      path: 'config/extensions/quote_of_day.yaml',
      desc: locale === 'zh' ? 'Quote of the Day 的类别过滤。' : 'Quote of the Day category filter.',
      body: buildQuoteOfDayYaml(s),
    });
    if (s.selectedKeys.includes('hitokoto')) outputs.push({
      path: 'config/extensions/hitokoto.yaml',
      desc: locale === 'zh' ? '一言句子类型过滤。' : 'Hitokoto sentence type filter.',
      body: buildHitokotoYaml(s),
    });
    if (s.selectedKeys.includes('supervisor_updates')) outputs.push({
      path: 'config/extensions/supervisor_updates.yaml',
      desc: locale === 'zh' ? '要监控的页面 URL 列表。' : 'List of page URLs to monitor.',
      body: buildSupervisorYaml(s),
    });
    latestOutputs = outputs;

    const listEl = qs<HTMLElement>('[data-output-list]', shell);
    if (listEl) {
      listEl.innerHTML = outputs.map((out, i) => `
        <div class="wz-output-card">
          <div class="wz-output-card__header">
            <div>
              <div class="wz-output-card__path">${escapeHtml(out.path)}</div>
              <div class="wz-output-card__desc">${escapeHtml(out.desc)}</div>
            </div>
            <button type="button" class="wz-output-card__copy" data-copy-idx="${i}">
              ${locale === 'zh' ? '复制' : 'Copy'}
            </button>
          </div>
          <pre>${escapeHtml(out.body)}</pre>
        </div>
      `).join('');

      qsa<HTMLButtonElement>('[data-copy-idx]', listEl).forEach(btn => {
        btn.addEventListener('click', async () => {
          const idx = Number(btn.dataset['copyIdx']);
          await navigator.clipboard.writeText(outputs[idx].body);
          const prev = btn.textContent ?? '';
          btn.textContent = locale === 'zh' ? '已复制' : 'Copied';
          setTimeout(() => { btn.textContent = prev; }, 1800);
        });
      });
    }

    // Sink reminders
    const scReminder    = qs<HTMLElement>('[data-sink-reminder-sc]', shell);
    const slackReminder = qs<HTMLElement>('[data-sink-reminder-slack]', shell);
    if (scReminder)    scReminder.hidden    = !s.sinks.serverchan.enabled;
    if (slackReminder) slackReminder.hidden = !s.sinks.slack.enabled;
    syncLlmSecretLabels();
    syncDeploySecretRows();
    renderDeployPreview();
  }

  // ── Slider value display ──────────────────────────────────────

  function initSliders(): void {
    qsa<HTMLInputElement>('input[type="range"]', shell).forEach(slider => {
      const valId  = slider.dataset['sliderVal'] ?? slider.id;
      const valEl  = qs<HTMLElement>(`[data-slider-val="${valId}"]`, shell);
      function update(): void { if (valEl) valEl.textContent = slider.value; }
      slider.addEventListener('input', update);
      update();
    });
  }

  // ── Init ─────────────────────────────────────────────────────

  // Initialize all tags/urls widgets
  qsa('.wz-tags, .wz-urls', shell).forEach(initTagsWidget);

  // Initialize slider value displays
  initSliders();

  // Initialize sink toggles
  initSinkToggles();

  // Initialize theme preset interactions
  initThemePresets();

  applyLlmProviderPreset(false);
  llmProviderSelect?.addEventListener('change', () => {
    applyLlmProviderPreset(true);
    renderDeployPreview();
  });
  llmSecretNameInput?.addEventListener('input', () => {
    syncLlmSecretLabels();
    renderDeployPreview();
  });
  llmApiKeyInput?.addEventListener('input', () => {
    syncLlmApiKeyInputs(llmApiKeyInput);
    renderDeployPreview();
  });
  llmApiKeyMirrorInput?.addEventListener('input', () => {
    syncLlmApiKeyInputs(llmApiKeyMirrorInput);
    renderDeployPreview();
  });

  deployRepoInput?.addEventListener('input', renderDeployPreview);
  deployRepoInput?.addEventListener('change', () => {
    if (githubSession && deployRepoInput) {
      githubSession.selectedRepo = deployRepoInput.value.trim();
      saveGitHubSession(githubSession);
    }
    renderDeployPreview();
  });
  qsa<HTMLInputElement>('[data-deploy-secret]', shell).forEach((input) => {
    input.addEventListener('input', renderDeployPreview);
  });

  deploySubmitBtn?.addEventListener('click', async () => {
    readState(state);
    renderOutputs(state);
    clearDeployStatus();

    const repo = parseRepoInput(deployRepoInput?.value ?? '');
    if (!repo) {
      setDeployStatus(
        'warn',
        locale === 'zh' ? '请先填写正确的 GitHub 仓库（owner/repo 或仓库 URL）。' : 'Enter a valid GitHub repository first (owner/repo or repository URL).',
      );
      return;
    }

    const token = githubSession?.token ?? deployTokenInput?.value.trim() ?? '';
    if (!token) {
      setDeployStatus(
        'warn',
        locale === 'zh'
          ? '请先在页面顶部连接 GitHub。'
          : 'Connect GitHub at the top of the page first.',
      );
      return;
    }

    const secrets = buildDeploySecrets();
    const missingSecret = secrets.find((secret) => !secret.value);
    if (missingSecret) {
      setDeployStatus(
        'warn',
        locale === 'zh'
          ? `缺少必填 secret：${missingSecret.name}`
          : `Missing required secret: ${missingSecret.name}`,
      );
      return;
    }

    const originalLabel = deploySubmitBtn.textContent ?? '';
    deploySubmitBtn.disabled = true;
    deploySubmitBtn.textContent = locale === 'zh' ? '部署中...' : 'Deploying...';
    setDeployStatus(
      'info',
      locale === 'zh' ? '正在写入配置文件和 GitHub Secrets...' : 'Writing config files and GitHub secrets...',
    );

    try {
      const result = await deployGeneratedConfig({
        owner: repo.owner,
        repo: repo.repo,
        token,
        files: latestOutputs.map(({ path, body }) => ({ path, body })),
        secrets,
      });

      if (deploySuccessEl) deploySuccessEl.hidden = false;
      setDeployStatus(
        'success',
        locale === 'zh'
          ? `已写入 ${result.committedPaths.length} 个文件，并更新 ${result.writtenSecrets.length} 个 secret。目标分支：${result.defaultBranch}`
          : `Wrote ${result.committedPaths.length} files and updated ${result.writtenSecrets.length} secrets on ${result.defaultBranch}.`,
      );
      if (connectNextStepsEl) connectNextStepsEl.hidden = false;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setDeployStatus('warn', message);
    } finally {
      deploySubmitBtn.disabled = false;
      deploySubmitBtn.textContent = originalLabel;
    }
  });

  // Sync initial state to DOM
  syncCards();
  renderOrderList();
  ensureScheduleState();
  renderSetupMode();
  syncConfigPanels();
  syncScheduleRows();
  syncSinkSourceFields();
  syncLlmSecretLabels();
  syncLlmApiKeyInputs();
  syncDeploySecretRows();
  renderGitHubSession();
  // PAT flow: no OAuth callback to process
  renderDeployPreview();
  showStep(1);
}
