import { ChatBoxSettings } from '@/types/data';

export const DEFAULT_CHAT_BOX_SETTINGS: ChatBoxSettings = {
  report_type: 'research_report',
  report_source: 'web',
  tone: 'Objective',
  domains: [],
  defaultReportType: 'research_report',
  layoutType: 'copilot',
  mcp_enabled: false,
  mcp_configs: [],
  mcp_strategy: 'fast',
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

export const ALLOWED_REPORT_SOURCES = ['web', 'local', 'hybrid'] as const;

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

  let layoutType = 'copilot';

  return {
    report_type: settings.report_type || 'research_report',
    report_source,
    tone,
    domains: settings.domains || [],
    defaultReportType: settings.defaultReportType || settings.report_type || 'research_report',
    layoutType,
    mcp_enabled: settings.mcp_enabled ?? false,
    mcp_configs: settings.mcp_configs || [],
    mcp_strategy: settings.mcp_strategy || 'fast',
  };
}
