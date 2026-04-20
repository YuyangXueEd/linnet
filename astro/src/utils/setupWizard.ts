import enSource from '../setup-wizard/wizard/index.en.html?raw';
import zhSource from '../setup-wizard/wizard/index.zh.html?raw';

export type SetupWizardLocale = 'en' | 'zh';

interface SetupWizardAssets {
  bodyHtml: string;
  css: string;
  script: string;
}

const LEGACY_SOURCE: Record<SetupWizardLocale, string> = {
  en: enSource,
  zh: zhSource,
};

const CSS_STRIP_PATTERNS = [
  /:root\s*{[\s\S]*?}\s*/m,
  /body\[data-theme="dark"\]\s*{[\s\S]*?}\s*/m,
  /@media\s*\(prefers-color-scheme:\s*dark\)\s*{\s*body:not\(\[data-theme="light"\]\)\s*{[\s\S]*?}\s*}\s*/m,
  /html\s*{[\s\S]*?}\s*/m,
  /body\s*{[\s\S]*?}\s*/m,
  /a\s*{[\s\S]*?}\s*/m,
  /\.theme-toggle\s*{[\s\S]*?}\s*/m,
];

const THEME_BUTTON_PATTERN =
  /<button class="theme-toggle" id="theme-toggle" type="button" aria-live="polite">\s*[\s\S]*?<\/button>\s*/m;

const THEME_SCRIPT_PATTERN =
  /\s*const themeToggleEl = document\.getElementById\("theme-toggle"\);\n\n[\s\S]*?themeToggleEl\.addEventListener\("click", \(\) => \{[\s\S]*?\n\s*}\);\n\n/m;

export function loadSetupWizard(locale: SetupWizardLocale): SetupWizardAssets {
  const source = LEGACY_SOURCE[locale];

  return {
    bodyHtml: stripThemeControls(extractSection(source, '<body>', '<script>')).trim(),
    css: stripLegacyCss(extractSection(source, '<style>', '</style>')).trim(),
    script: stripThemeScript(extractSection(source, '<script>', '</script>')).trim(),
  };
}

function extractSection(source: string, startToken: string, endToken: string): string {
  const start = source.indexOf(startToken);
  if (start === -1) {
    throw new Error(`Missing token: ${startToken}`);
  }

  const contentStart = start + startToken.length;
  const end = source.indexOf(endToken, contentStart);
  if (end === -1) {
    throw new Error(`Missing token: ${endToken}`);
  }

  return source.slice(contentStart, end);
}

function stripThemeControls(bodyHtml: string): string {
  return bodyHtml.replace(THEME_BUTTON_PATTERN, '');
}

function stripLegacyCss(css: string): string {
  return CSS_STRIP_PATTERNS.reduce((cleanedCss, pattern) => cleanedCss.replace(pattern, ''), css);
}

function stripThemeScript(script: string): string {
  return script
    .replace(THEME_SCRIPT_PATTERN, '\n\n')
    .replace(/^\s*loadTheme\(\);\n/m, '');
}
