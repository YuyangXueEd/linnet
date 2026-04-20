/**
 * Extension registry — single source of truth for every Linnet extension.
 *
 * Used by:
 *   - SectionBlock.astro  → dispatch + layout
 *   - Setup wizard        → Step 1 picker + Step 2 config form
 *   - Future: agent skill endpoint, RSS meta, search index
 *
 * Component references live in SectionBlock.astro (Astro import constraint).
 */

// ── Primitives ──────────────────────────────────────────────────────────────

export type LayoutMode =
  | 'editorial'  // Tiered layout: lead → alternating fig → compact (Papers, Repos)
  | 'columns-2'  // Two-column grid (Hacker News — first item spans full width)
  | 'columns-3'  // Three-column grid (legacy, kept for fallback)
  | 'stack'      // Single-column list (Jobs, Supervisor)
  | 'single';    // Full-width block (Weather)

export type IconName =
  | 'paper' | 'flame' | 'repo' | 'post' | 'cloud'
  | 'feather' | 'book' | 'search' | 'arrow' | 'sun' | 'moon';

export type ExtensionCategory =
  | 'research'   // academic papers, preprints
  | 'tech'       // developer-facing feeds
  | 'career'     // job postings
  | 'local'      // location/personal context
  | 'custom';    // user-defined extensions

export type FieldType =
  | 'text'
  | 'number'
  | 'slider'
  | 'toggle'
  | 'select'
  | 'multiselect'  // predefined options, multiple allowed
  | 'tags'         // free-form add/remove string list (keywords, authors)
  | 'urls';        // add/remove URL list (supervisor pages, RSS feeds)

// ── Setup wizard field schema ────────────────────────────────────────────────

export interface FieldOption {
  value: string;
  label: string;
  description?: string;       // shown as hint on hover / in accordion
}

export interface SetupField {
  key: string;                // YAML config path, e.g. "max_results" or "keywords"
  label: string;
  labelZh?: string;
  type: FieldType;
  required?: boolean;
  default?: unknown;
  options?: FieldOption[];    // select / multiselect only
  min?: number;               // number / slider
  max?: number;
  step?: number;
  placeholder?: string;
  hint?: string;              // help text rendered below the field
  hintZh?: string;
}

// ── Extension metadata ───────────────────────────────────────────────────────

export interface ExtensionMeta {
  // Identity — must match the JSON section.key emitted by the Python extension
  key: string;

  // Digest display
  title: string;              // section heading: "From the Archive"
  subtitle: string;           // section sub-label: "arXiv preprints"
  icon: IconName;
  defaultOrder: number;       // suggested position in daily digest (1-based)

  // Feed rendering (component reference added in SectionBlock.astro)
  layout: LayoutMode;

  // Setup wizard — Step 1 extension picker
  displayName: string;        // "arXiv Papers"
  displayNameZh?: string;     // "arXiv 论文"
  description: string;        // one-line pitch shown on the picker card
  descriptionZh?: string;
  category: ExtensionCategory;
  tags: string[];             // full-text search terms for the Step 1 search box

  // Setup wizard — Step 2 per-extension config form
  setupFields: SetupField[];

  // Weekly / monthly aggregation defaults
  weeklyDefault?: boolean;
  monthlyDefault?: boolean;
  weeklyTopN?: number;
  monthlyTopN?: number;
}

// ── Registry ─────────────────────────────────────────────────────────────────

export const REGISTRY: Record<string, ExtensionMeta> = {

  weather: {
    key: 'weather',
    title: 'The Morning',
    subtitle: 'Local weather',
    icon: 'cloud',
    defaultOrder: 1,
    layout: 'single',
    displayName: 'Weather',
    displayNameZh: '天气',
    description: 'Temperature, conditions, and a short forecast for your city.',
    descriptionZh: '你所在城市的气温、天气状况和简短预报。',
    category: 'local',
    tags: ['weather', 'forecast', 'temperature', 'city', '天气', '预报'],
    setupFields: [
      {
        key: 'city',
        label: 'City',
        labelZh: '城市',
        type: 'text',
        required: true,
        placeholder: 'Edinburgh',
        hint: 'City name passed to the weather API.',
        hintZh: '传给天气 API 的城市名称。',
      },
      {
        key: 'timezone',
        label: 'Timezone',
        labelZh: '时区',
        type: 'select',
        default: 'Europe/London',
        options: [
          { value: 'Europe/London',    label: 'London (GMT/BST)' },
          { value: 'Europe/Paris',     label: 'Paris (CET)' },
          { value: 'America/New_York', label: 'New York (ET)' },
          { value: 'America/Chicago',  label: 'Chicago (CT)' },
          { value: 'America/Los_Angeles', label: 'Los Angeles (PT)' },
          { value: 'Asia/Shanghai',    label: 'Shanghai (CST)' },
          { value: 'Asia/Tokyo',       label: 'Tokyo (JST)' },
          { value: 'Asia/Kolkata',     label: 'India (IST)' },
          { value: 'Australia/Sydney', label: 'Sydney (AEST)' },
        ],
        hint: 'Used to align the briefing time with local sunrise.',
      },
    ],
    weeklyDefault: false,
    monthlyDefault: false,
  },

  arxiv: {
    key: 'arxiv',
    title: 'From the Archive',
    subtitle: 'arXiv preprints',
    icon: 'paper',
    defaultOrder: 2,
    layout: 'editorial',
    displayName: 'arXiv Papers',
    displayNameZh: 'arXiv 论文',
    description: 'Daily preprints ranked by your keyword and author preferences.',
    descriptionZh: '每日 arXiv 预印本，按你的关键词和作者偏好排序。',
    category: 'research',
    tags: ['arxiv', 'papers', 'research', 'academic', 'preprint', 'ml', 'ai', 'science', '论文', '学术'],
    setupFields: [
      {
        key: 'profiles',
        label: 'Research areas',
        labelZh: '研究方向',
        type: 'multiselect',
        hint: 'Sets the arXiv categories to monitor.',
        hintZh: '设置要监控的 arXiv 分类。',
        options: [
          { value: 'ai_ml',      label: 'AI / ML',           description: 'cs.LG, cs.AI, stat.ML' },
          { value: 'nlp',        label: 'NLP',               description: 'cs.CL' },
          { value: 'cv',         label: 'Computer Vision',   description: 'cs.CV' },
          { value: 'robotics',   label: 'Robotics',          description: 'cs.RO' },
          { value: 'medical_ai', label: 'Medical AI',        description: 'cs.AI + q-bio' },
          { value: 'hci',        label: 'HCI',               description: 'cs.HC' },
          { value: 'systems',    label: 'Systems',           description: 'cs.OS, cs.DC, cs.NI' },
          { value: 'theory',     label: 'Theory',            description: 'cs.CC, cs.DS, math.CO' },
        ],
      },
      {
        key: 'keywords',
        label: 'Keywords',
        labelZh: '关键词',
        type: 'tags',
        placeholder: 'e.g. diffusion model, RLHF, RAG',
        hint: 'Papers matching these keywords receive a higher relevance score.',
        hintZh: '命中这些关键词的论文会获得更高的相关性分数。',
      },
      {
        key: 'authors',
        label: 'Favourite authors',
        labelZh: '关注作者',
        type: 'tags',
        placeholder: 'e.g. Yann LeCun, Ilya Sutskever',
        hint: 'Papers by these authors are always surfaced.',
        hintZh: '这些作者的论文始终会被收录。',
      },
      {
        key: 'max_results',
        label: 'Max papers per day',
        labelZh: '每日最多论文数',
        type: 'slider',
        default: 10,
        min: 3,
        max: 30,
        step: 1,
      },
    ],
    weeklyDefault: true,
    monthlyDefault: true,
    weeklyTopN: 5,
    monthlyTopN: 10,
  },

  hacker_news: {
    key: 'hacker_news',
    title: 'The Town Square',
    subtitle: 'Hacker News',
    icon: 'flame',
    defaultOrder: 3,
    layout: 'columns-2',
    displayName: 'Hacker News',
    description: 'Top stories filtered by score threshold — signal without the scroll.',
    descriptionZh: '按分数阈值过滤的热门故事——去除噪音，只留信号。',
    category: 'tech',
    tags: ['hacker news', 'hn', 'tech', 'startups', 'programming', 'news', '科技', '新闻'],
    setupFields: [
      {
        key: 'min_score',
        label: 'Minimum score',
        labelZh: '最低分数',
        type: 'slider',
        default: 100,
        min: 20,
        max: 500,
        step: 10,
        hint: 'Stories below this score are filtered out.',
        hintZh: '低于此分数的故事将被过滤掉。',
      },
      {
        key: 'max_stories',
        label: 'Max stories',
        labelZh: '最多故事数',
        type: 'slider',
        default: 10,
        min: 3,
        max: 25,
        step: 1,
      },
    ],
    weeklyDefault: true,
    monthlyDefault: false,
    weeklyTopN: 5,
  },

  github_trending: {
    key: 'github_trending',
    title: 'Workshops',
    subtitle: 'GitHub Trending',
    icon: 'repo',
    defaultOrder: 4,
    layout: 'editorial',  // tiered: hero → mid cards → compact rows
    displayName: 'GitHub Trending',
    displayNameZh: 'GitHub 趋势',
    description: 'Repositories gaining momentum — what the community is building right now.',
    descriptionZh: '正在获得关注的仓库——了解社区现在在做什么。',
    category: 'tech',
    tags: ['github', 'trending', 'repositories', 'open source', 'code', '开源', '仓库'],
    setupFields: [
      {
        key: 'max_repos',
        label: 'Max repositories',
        labelZh: '最多仓库数',
        type: 'slider',
        default: 9,
        min: 3,
        max: 20,
        step: 1,
      },
      {
        key: 'language',
        label: 'Filter by language',
        labelZh: '按语言过滤',
        type: 'select',
        default: '',
        options: [
          { value: '',           label: 'All languages' },
          { value: 'python',     label: 'Python' },
          { value: 'typescript', label: 'TypeScript' },
          { value: 'javascript', label: 'JavaScript' },
          { value: 'rust',       label: 'Rust' },
          { value: 'go',         label: 'Go' },
          { value: 'julia',      label: 'Julia' },
          { value: 'cpp',        label: 'C++' },
        ],
        hint: 'Leave blank to track all languages.',
      },
    ],
    weeklyDefault: true,
    monthlyDefault: false,
    weeklyTopN: 5,
  },

  postdoc_jobs: {
    key: 'postdoc_jobs',
    title: 'Postings',
    subtitle: 'Academic positions',
    icon: 'post',
    defaultOrder: 5,
    layout: 'stack',
    displayName: 'Academic Jobs',
    displayNameZh: '学术职位',
    description: 'Postdoc and faculty postings surfaced automatically from job boards.',
    descriptionZh: '自动从招聘板块抓取的博后和教职职位。',
    category: 'career',
    tags: ['jobs', 'postdoc', 'faculty', 'academic', 'career', 'hiring', '职位', '招聘', '博后'],
    setupFields: [
      {
        key: 'keywords',
        label: 'Search terms',
        labelZh: '搜索词',
        type: 'tags',
        placeholder: 'e.g. machine learning, neuroscience',
        hint: 'Job titles or subject areas to match.',
        hintZh: '要匹配的职位名称或研究领域。',
      },
      {
        key: 'max_results',
        label: 'Max postings',
        labelZh: '最多职位数',
        type: 'slider',
        default: 5,
        min: 2,
        max: 15,
        step: 1,
      },
    ],
    weeklyDefault: true,
    monthlyDefault: true,
    weeklyTopN: 3,
    monthlyTopN: 5,
  },

  quote_of_day: {
    key: 'quote_of_day',
    title: 'Words for the Morning',
    subtitle: 'Quote of the day',
    icon: 'feather',
    defaultOrder: 0,
    layout: 'single',
    displayName: 'Quote of the Day',
    displayNameZh: '每日名言',
    description: 'A daily quote from API Ninjas — replaces the default tagline. Requires API_NINJAS_KEY secret.',
    descriptionZh: '来自 API Ninjas 的每日名言，替换默认 tagline。需要配置 API_NINJAS_KEY。',
    category: 'custom',
    tags: ['quote', 'inspiration', 'tagline', '名言', '每日'],
    setupFields: [
      {
        key: 'category',
        label: 'Quote category',
        labelZh: '名言类别',
        type: 'text',
        placeholder: 'morning, inspiration, life …',
        hint: 'Leave blank for a random category. See API Ninjas docs for all options.',
        hintZh: '留空则随机选取类别。',
      },
    ],
    weeklyDefault: false,
    monthlyDefault: false,
  },

  hitokoto: {
    key: 'hitokoto',
    title: '一言',
    subtitle: 'hitokoto.cn',
    icon: 'feather',
    defaultOrder: 0,
    layout: 'single',
    displayName: '一言',
    displayNameZh: '一言',
    description: '来自 hitokoto.cn 的每日一言，替换默认 tagline。无需 API key。',
    descriptionZh: '来自 hitokoto.cn 的每日一言，替换默认 tagline。无需 API key。',
    category: 'custom',
    tags: ['hitokoto', '一言', 'quote', 'chinese', '中文', '名言'],
    setupFields: [
      {
        key: 'type',
        label: 'Sentence type',
        labelZh: '句子类型',
        type: 'select',
        default: '',
        options: [
          { value: '', label: '随机 (all)' },
          { value: 'a', label: 'a — 动画' },
          { value: 'b', label: 'b — 漫画' },
          { value: 'c', label: 'c — 游戏' },
          { value: 'd', label: 'd — 文学' },
          { value: 'e', label: 'e — 原创' },
          { value: 'h', label: 'h — 影视' },
          { value: 'i', label: 'i — 诗词' },
          { value: 'k', label: 'k — 哲学' },
        ],
      },
    ],
    weeklyDefault: false,
    monthlyDefault: false,
  },

  supervisor_updates: {
    key: 'supervisor_updates',
    title: 'On My Radar',
    subtitle: 'Monitored pages',
    icon: 'feather',
    defaultOrder: 6,
    layout: 'stack',
    displayName: 'Page Monitor',
    displayNameZh: '页面监控',
    description: 'Tracks changes on any web pages you care about — lab sites, supervisor pages, deadlines.',
    descriptionZh: '监控任意网页的变化——导师主页、实验室公告、截止日期等。',
    category: 'custom',
    tags: ['monitor', 'supervisor', 'webpage', 'changes', 'tracking', '监控', '导师', '页面'],
    setupFields: [
      {
        key: 'urls',
        label: 'Pages to monitor',
        labelZh: '要监控的页面',
        type: 'urls',
        placeholder: 'https://example.com/lab',
        hint: 'Add one URL per line. Changes since the last run will be summarised.',
        hintZh: '每行一个 URL。自上次运行以来的变化将被自动摘要。',
      },
    ],
    weeklyDefault: false,
    monthlyDefault: false,
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

/** All extensions sorted by defaultOrder — use this for Setup Step 1 and digest index. */
export const EXTENSION_LIST: ExtensionMeta[] = Object.values(REGISTRY).sort(
  (a, b) => a.defaultOrder - b.defaultOrder,
);

/** Look up extension metadata by key. Returns undefined for unregistered extensions. */
export function getExtension(key: string): ExtensionMeta | undefined {
  return REGISTRY[key];
}

/** Extensions grouped by category — useful for Step 1 filter chips in Setup. */
export const EXTENSIONS_BY_CATEGORY: Record<ExtensionCategory, ExtensionMeta[]> = {
  research: [],
  tech:     [],
  career:   [],
  local:    [],
  custom:   [],
};
for (const ext of EXTENSION_LIST) {
  EXTENSIONS_BY_CATEGORY[ext.category].push(ext);
}
