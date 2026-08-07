import { ChatBoxSettings } from '@/types/data';

export const DEFAULT_CHAT_BOX_SETTINGS: ChatBoxSettings = {
  report_type: 'research_report',
  report_source: 'web',
  tone: 'Objective',
  total_words: 1200,
  domains: [],
  defaultReportType: 'research_report',
  layoutType: 'copilot',
  mcp_enabled: false,
  mcp_configs: [],
  mcp_strategy: 'fast',
  report_language: 'chinese',
};

export function readChatBoxSettingsFromStorage(): ChatBoxSettings {
  if (typeof window === 'undefined') {
    return DEFAULT_CHAT_BOX_SETTINGS;
  }
  const savedSettings = localStorage.getItem('chatBoxSettings');
  if (!savedSettings) {
    return DEFAULT_CHAT_BOX_SETTINGS;
  }
  try {
    return normalizeChatBoxSettings({
      ...DEFAULT_CHAT_BOX_SETTINGS,
      ...JSON.parse(savedSettings),
    });
  } catch {
    return DEFAULT_CHAT_BOX_SETTINGS;
  }
}

export const ALLOWED_TONES = ['Objective', 'Formal', 'Analytical'] as const;

export const REPORT_LENGTH_OPTIONS = [
  { value: 600, label: 'Short (~600 words, faster)' },
  { value: 1200, label: 'Standard (~1200 words)' },
  { value: 2500, label: 'Long (~2500 words)' },
  { value: 4000, label: 'Extended (~4000 words, slower)' },
] as const;

export const ALLOWED_TOTAL_WORDS = REPORT_LENGTH_OPTIONS.map((option) => option.value);

export const ALLOWED_REPORT_SOURCES = ['web', 'local', 'hybrid'] as const;

export const REPORT_LANGUAGE_OPTIONS = [
  { value: 'chinese', label: 'Chinese (中文报告)' },
  { value: 'english', label: 'English (English report)' },
] as const;

export const ALLOWED_REPORT_LANGUAGES = REPORT_LANGUAGE_OPTIONS.map((option) => option.value);

const LEGACY_SOURCE_MAP: Record<string, string> = {
  scholar: 'web',
};

export function normalizeChatBoxSettings(
  settings: Partial<ChatBoxSettings>
): ChatBoxSettings {
  const tone = ALLOWED_TONES.includes(settings.tone as (typeof ALLOWED_TONES)[number])
    ? settings.tone!
    : 'Objective';

  let report_source = settings.report_source || 'web';
  if (LEGACY_SOURCE_MAP[report_source]) {
    report_source = LEGACY_SOURCE_MAP[report_source];
  }
  if (!ALLOWED_REPORT_SOURCES.includes(report_source as (typeof ALLOWED_REPORT_SOURCES)[number])) {
    report_source = 'web';
  }

  const parsedTotalWords = Number(settings.total_words);
  const total_words = ALLOWED_TOTAL_WORDS.includes(parsedTotalWords as (typeof ALLOWED_TOTAL_WORDS)[number])
    ? parsedTotalWords
    : DEFAULT_CHAT_BOX_SETTINGS.total_words;

  let layoutType = 'copilot';

  const report_language = ALLOWED_REPORT_LANGUAGES.includes(
    settings.report_language as (typeof ALLOWED_REPORT_LANGUAGES)[number]
  )
    ? (settings.report_language as (typeof ALLOWED_REPORT_LANGUAGES)[number])
    : DEFAULT_CHAT_BOX_SETTINGS.report_language;

  return {
    report_type: settings.report_type || 'research_report',
    report_source,
    tone,
    total_words,
    domains: settings.domains || [],
    defaultReportType: settings.defaultReportType || settings.report_type || 'research_report',
    layoutType,
    mcp_enabled: settings.mcp_enabled ?? false,
    mcp_configs: settings.mcp_configs || [],
    mcp_strategy: settings.mcp_strategy || 'fast',
    report_language,
  };
}
