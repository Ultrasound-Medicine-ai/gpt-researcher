import { apiFetch } from '@/lib/apiFetch';
import { researchJobStorageKey } from '@/hooks/useResearchJob';
import { ChatBoxSettings, Data } from '@/types/data';

const PARENT_CHAT_KEY = (reportId: string) => `gptr_report_parent_chat:${reportId}`;

export function getReportParentChatId(reportId: string): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(PARENT_CHAT_KEY(reportId));
  } catch {
    return null;
  }
}

export function rememberReportParentChat(reportId: string, parentChatId: string | null | undefined) {
  if (typeof window === 'undefined' || !reportId || !parentChatId) return;
  try {
    if (reportId === parentChatId) return;
    localStorage.setItem(PARENT_CHAT_KEY(reportId), parentChatId);
  } catch {
    /* ignore */
  }
}

/** Ensure HttpOnly visitor cookie exists before creating a job. :-) */
export async function ensureVisitorCookie(): Promise<void> {
  try {
    await apiFetch('/api/auth/me');
  } catch {
    /* best-effort */
  }
}

type SaveResearchFn = (
  question: string,
  answer: string,
  orderedData: Data[]
) => Promise<string>;

export type IntentOption = {
  id: string;
  token?: string;
  domain?: string;
  label: string;
  resolved_task: string;
};

export type ResearchIntentResult = {
  action: 'proceed' | 'clarify';
  confidence?: string;
  task?: string;
  expanded_task?: string;
  planning_hint?: string;
  domain_preference?: string;
  clarification_question?: string;
  options?: IntentOption[];
  ambiguous_tokens?: string[];
};

export class ReportIntentClarification extends Error {
  payload: ResearchIntentResult;

  constructor(payload: ResearchIntentResult) {
    super(payload.clarification_question || 'needs_clarification');
    this.name = 'ReportIntentClarification';
    this.payload = payload;
  }
}

export type PendingReportClarification = {
  toolCall: { task?: string; knowledge_policy?: string };
  options: IntentOption[];
  question: string;
  originalTask: string;
};

/** Build recent chat lines for planning / intent from orderedData. :-) */
export function recentChatMessagesFromOrderedData(
  orderedData: Data[],
  limit = 12
): Array<{ role: string; content: string }> {
  const out: Array<{ role: string; content: string }> = [];
  for (const d of orderedData) {
    if (d.type === 'question' && typeof d.content === 'string' && d.content.trim()) {
      out.push({ role: 'user', content: d.content.trim() });
    } else if (d.type === 'chat' && typeof d.content === 'string' && d.content.trim()) {
      out.push({ role: 'assistant', content: d.content.trim() });
    }
  }
  return out.slice(-limit);
}

export async function resolveResearchIntent(opts: {
  task: string;
  parentChatId?: string | null;
  recentChatMessages?: Array<{ role: string; content: string }>;
  forceDomain?: string;
  forceSense?: string;
}): Promise<ResearchIntentResult> {
  await ensureVisitorCookie();
  const response = await apiFetch('/api/research/intent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task: opts.task,
      parent_chat_id: opts.parentChatId || undefined,
      recent_chat_messages: opts.recentChatMessages || [],
      force_domain: opts.forceDomain,
      force_sense: opts.forceSense,
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === 'object' ? data.detail?.message : data.detail;
    throw new Error(detail || data.message || data.error || '意图识别失败');
  }
  return data as ResearchIntentResult;
}

/** Match user reply "1" / label / resolved text to a clarify option. :-) */
export function matchClarificationReply(
  message: string,
  pending: PendingReportClarification
): IntentOption | null {
  const text = (message || '').trim();
  if (!text || !pending?.options?.length) return null;

  const num = text.match(/^([1-9]\d*)\s*[.、)）]?$/);
  if (num) {
    const idx = parseInt(num[1], 10) - 1;
    if (idx >= 0 && idx < pending.options.length) return pending.options[idx];
  }

  const lower = text.toLowerCase();
  for (const opt of pending.options) {
    if (lower === opt.label.toLowerCase()) return opt;
    if (lower.includes(opt.label.toLowerCase()) && opt.label.length >= 3) return opt;
    if (opt.domain === 'tech' && /server[- ]?sent|eventsource|流式|推送/i.test(text)) {
      return opt;
    }
    if (opt.domain === 'finance' && /上交所|上海证券|stock\s*exchange/i.test(text)) {
      return opt;
    }
  }
  return null;
}

/**
 * Create an independent report session + job from a chat tool call.
 *
 * UI contract (caller):
 * - Keep the current chat session / right panel unchanged
 * - Switch the left panel to this job's progress via observeJob
 * - Do NOT navigate away from the conversation page :-)
 *
 * Throws ReportIntentClarification when the user must pick a sense first.
 */
export async function submitChatReportJob(opts: {
  toolCall: { task?: string; knowledge_policy?: string };
  chatBoxSettings: ChatBoxSettings;
  saveResearch: SaveResearchFn;
  parentChatId?: string | null;
  recentChatMessages?: Array<{ role: string; content: string }>;
  forceDomain?: string;
  forceSense?: string;
  resolvedTask?: string;
  skipIntent?: boolean;
}): Promise<{ sessionId: string; jobId: string; task: string; tenantId?: string }> {
  const rawTask = String(opts.toolCall?.task || '').trim();
  if (!rawTask) throw new Error('Report task is missing');

  await ensureVisitorCookie();

  let expandedTask = opts.resolvedTask || rawTask;
  let forceDomain = opts.forceDomain;
  let forceSense = opts.forceSense;

  if (!opts.skipIntent) {
    const intent = await resolveResearchIntent({
      task: rawTask,
      parentChatId: opts.parentChatId,
      recentChatMessages: opts.recentChatMessages,
      forceDomain,
      forceSense,
    });

    if (intent.action === 'clarify') {
      throw new ReportIntentClarification(intent);
    }
    expandedTask = String(intent.expanded_task || rawTask);
    forceDomain = forceDomain || intent.domain_preference;
  }

  const displayTask = rawTask;
  const initialData = [
    { type: 'question', content: displayTask, contentAndType: 'report_topic-question' },
    {
      type: 'logs',
      content: 'job_queued',
      output: '报告任务已创建，正在生成…',
      contentAndType: 'job_queued-logs',
    },
  ] as unknown as Data[];

  const sessionId = await opts.saveResearch(displayTask, '', initialData);
  rememberReportParentChat(sessionId, opts.parentChatId);

  const domainFilters = JSON.parse(localStorage.getItem('domainFilters') || '[]');
  const queryDomains = Array.isArray(domainFilters)
    ? domainFilters.map((domain: { value: string }) => domain.value).filter(Boolean)
    : [];

  const response = await apiFetch('/api/jobs/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task: displayTask,
      expanded_task: expandedTask,
      force_domain: forceDomain,
      force_sense: forceSense,
      report_type: opts.chatBoxSettings.report_type,
      report_source: opts.chatBoxSettings.report_source,
      tone: opts.chatBoxSettings.tone,
      total_words: opts.chatBoxSettings.total_words || 1200,
      report_language: opts.chatBoxSettings.report_language || 'chinese',
      query_domains: queryDomains,
      mcp_enabled: opts.chatBoxSettings.mcp_enabled || false,
      mcp_strategy: opts.chatBoxSettings.mcp_strategy || 'fast',
      mcp_configs: opts.chatBoxSettings.mcp_configs || [],
      session_id: sessionId,
      research_id: sessionId,
      knowledge_policy: opts.toolCall?.knowledge_policy || 'local_first',
      idempotency_key: `chat-report:${sessionId}`,
      parent_chat_id: opts.parentChatId || undefined,
      recent_chat_messages: opts.recentChatMessages || [],
    }),
  });

  const result = await response.json();
  if (!response.ok || !result.job_id) {
    const detail = typeof result.detail === 'object' ? result.detail?.message : result.detail;
    throw new Error(detail || result.message || result.error || '创建报告任务失败');
  }

  localStorage.setItem(
    researchJobStorageKey(sessionId),
    JSON.stringify({
      jobId: result.job_id,
      sessionId,
      tenantId: result.tenant_id,
    })
  );

  return {
    sessionId,
    jobId: result.job_id,
    task: displayTask,
    tenantId: result.tenant_id,
  };
}

/** Prepare left panel for a new report while preserving right-side chat. :-) */
export function mergeChatWithReportTopic(prev: Data[], task: string): Data[] {
  const conversation = prev.filter((d) => {
    if (d.type === 'chat') return true;
    if (d.type === 'question') {
      return (
        (d as { contentAndType?: string }).contentAndType !== 'report_topic-question'
      );
    }
    return false;
  });
  return [
    {
      type: 'question',
      content: task,
      contentAndType: 'report_topic-question',
    } as Data,
    ...conversation,
    {
      type: 'logs',
      content: 'job_queued',
      output: `左侧已切换为新报告进度：${task}`,
      contentAndType: 'job_queued-logs',
    } as Data,
  ];
}

export function chatReportCreatedMessage(task: string): string {
  const title = (task || '').trim().replace(/\s+/g, ' ').slice(0, 40);
  const topic = title ? `「${title}${task.trim().length > 40 ? '…' : ''}」` : '新主题';
  return (
    `已开始生成独立报告${topic}。` +
    `左侧显示该报告进度；右侧对话保持不变，可继续提问或再请求生成报告。`
  );
}
