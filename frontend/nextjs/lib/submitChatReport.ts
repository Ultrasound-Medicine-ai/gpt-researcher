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

/**
 * Create an independent report session + job from a chat tool call.
 *
 * UI contract (caller):
 * - Keep the current chat session / right panel unchanged
 * - Switch the left panel to this job's progress via observeJob
 * - Do NOT navigate away from the conversation page :-)
 */
export async function submitChatReportJob(opts: {
  toolCall: { task?: string; knowledge_policy?: string };
  chatBoxSettings: ChatBoxSettings;
  saveResearch: SaveResearchFn;
  parentChatId?: string | null;
}): Promise<{ sessionId: string; jobId: string; task: string; tenantId?: string }> {
  const task = String(opts.toolCall?.task || '').trim();
  if (!task) throw new Error('Report task is missing');

  await ensureVisitorCookie();

  const initialData = [
    { type: 'question', content: task, contentAndType: 'report_topic-question' },
    {
      type: 'logs',
      content: 'job_queued',
      output: '报告任务已创建，正在生成…',
      contentAndType: 'job_queued-logs',
    },
  ] as unknown as Data[];

  const sessionId = await opts.saveResearch(task, '', initialData);
  rememberReportParentChat(sessionId, opts.parentChatId);

  const domainFilters = JSON.parse(localStorage.getItem('domainFilters') || '[]');
  const queryDomains = Array.isArray(domainFilters)
    ? domainFilters.map((domain: { value: string }) => domain.value).filter(Boolean)
    : [];

  const response = await apiFetch('/api/jobs/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task,
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
    task,
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
